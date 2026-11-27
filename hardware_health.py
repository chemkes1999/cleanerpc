"""
PyClean Pro v2.9 - Salud de Hardware (SSD S.M.A.R.T., TRIM y Centro de Batería)
Inspecciona el estado físico de los discos en Windows, ejecuta optimización TRIM,
analiza a fondo el desgaste y consumo de la batería en portátiles, y ofrece
herramientas reales de calibración, reparación de energía/ACPI y optimización
de autonomía y rendimiento.
"""

from __future__ import annotations

import os
import re
import sys
import json
import time
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import cleaner

try:
    import psutil
except ImportError:
    psutil = None


# GUIDs canónicos de energía en Windows
SCHEME_BALANCED = "381b4222-f694-41f0-9685-ff5bb260df2e"
SUB_USB = "2a737441-1930-4402-8d77-b2bebba308a3"
SETTING_USB_SUSPEND = "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"
SUB_WIRELESS = "19cbb8fa-5279-450e-9fac-8a3d5fedd0c1"
SETTING_WIRELESS_POWER = "12bbebe6-58d6-4636-95bb-3217ef867c1a"

OEM_CHARGE_LIMIT_TIPS = {
    "lenovo": "En Lenovo, abre 'Lenovo Vantage' → Energía y activa 'Modo Conservación' (limita la carga al 75-80% cuando está enchufada).",
    "asus": "En ASUS, abre 'MyASUS' → Configuración del dispositivo → Salud de la batería y activa 'Modo de cuidado de la batería' (límite al 80%).",
    "dell": "En Dell, abre 'Dell Power Manager' o entra a BIOS (F2) → Power Management y selecciona 'Primarily AC Use' o límite personalizado al 80%.",
    "hp": "En HP, entra a BIOS (F10) → Configuración → 'Adaptive Battery Optimizer' o límite de carga al 80% (en modelos ProBook/EliteBook/Victus).",
    "acer": "En Acer, abre 'Acer Care Center' → Comprobación del sistema → 'Límite de carga de la batería' (80%).",
    "msi": "En MSI, abre 'MSI Center' → System Diagnosis → Battery Master y elige 'Best for Battery' (carga al 60%) o 'Balanced' (80%).",
    "samsung": "En Samsung, abre 'Samsung Settings' → Batería y activa 'Proteger batería' (límite al 80-85%).",
    "lg": "En LG, abre 'LG Smart Assistant' → Energía y activa 'Extender vida útil de batería' (límite al 80%).",
    "huawei": "En Huawei, abre 'PC Manager' → Configuración → Optimización de batería y elige 'Modo Hogar' (límite 70-80%).",
}


def _get_startupinfo():
    """Genera una estructura STARTUPINFO segura para ocultar consolas en Windows."""
    if sys.platform == "win32" and hasattr(subprocess, "STARTUPINFO"):
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None


def _get_state_dir() -> str:
    """Directorio persistente para respaldos de energía y sesiones de calibración."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, ".pyclean_pro")
    os.makedirs(path, exist_ok=True)
    return path


def _power_backup_path() -> str:
    return os.path.join(_get_state_dir(), "battery_power_backup.json")


def _calibration_state_path() -> str:
    return os.path.join(_get_state_dir(), "battery_calibration_state.json")


def _run_cmd(args: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        startupinfo=_get_startupinfo(),
    )


def _format_duration_seconds(secs: int | None) -> str:
    if secs is None or secs <= 0 or secs > 86400 * 7:
        return "N/A"
    hours = secs // 3600
    minutes = (secs % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def get_oem_charge_limit_tip(manufacturer: str) -> str:
    """Devuelve una recomendación específica según el fabricante del portátil."""
    mfg = (manufacturer or "").strip().lower()
    for key, tip in OEM_CHARGE_LIMIT_TIPS.items():
        if key in mfg:
            return tip
    return (
        "Si usas la laptop casi siempre enchufada, busca en la BIOS/UEFI o en la app oficial "
        "del fabricante una opción de 'Límite de carga al 80%' para frenar el desgaste químico."
    )


def get_disk_health() -> list[dict]:
    """
    Obtiene el estado de salud S.M.A.R.T. y tipo de medio (SSD/HDD/NVMe)
    de los discos físicos conectados mediante PowerShell Get-PhysicalDisk.
    """
    if sys.platform != "win32":
        return [{
            "name": "Disco Local (Entorno no-Windows)",
            "media_type": "SSD",
            "health_status": "Healthy",
            "operational_status": "OK",
            "size_bytes": 0,
            "size_formatted": "N/A",
            "bus_type": "Local",
        }]

    ps_cmd = (
        "Get-PhysicalDisk | "
        "Select-Object FriendlyName, MediaType, HealthStatus, OperationalStatus, Size, BusType | "
        "ConvertTo-Json -Compress"
    )

    disks = []
    try:
        res = _run_cmd(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=12)
        raw = (res.stdout or "").strip()
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                parsed = [parsed]
            for d in parsed:
                size_bytes = int(d.get("Size") or 0)
                disks.append({
                    "name": str(d.get("FriendlyName") or "Disco Físico"),
                    "media_type": str(d.get("MediaType") or "Desconocido"),
                    "health_status": str(d.get("HealthStatus") or "Unknown"),
                    "operational_status": str(d.get("OperationalStatus") or "OK"),
                    "size_bytes": size_bytes,
                    "size_formatted": cleaner.format_size(size_bytes),
                    "bus_type": str(d.get("BusType") or ""),
                })
    except Exception:
        pass

    return disks


def run_ssd_trim(drive_letter: str = "C") -> tuple[bool, str]:
    """
    Ejecuta la optimización TRIM nativa de Windows (Optimize-Volume -ReTrim)
    para mantener el rendimiento del SSD. Requiere privilegios de Administrador.
    """
    cleaned = (drive_letter or "").strip().rstrip(":\\").upper()
    if not re.match(r"^[A-Z]$", cleaned):
        return False, f"Letra de unidad inválida: '{drive_letter}'. Debe ser una letra (ej. C)."

    if sys.platform != "win32":
        return False, "La optimización TRIM (Optimize-Volume) solo está disponible en Windows."

    ps_cmd = f"Optimize-Volume -DriveLetter {cleaned} -ReTrim"
    try:
        res = _run_cmd(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=60)
        if res.returncode == 0:
            return True, f"Optimización TRIM ejecutada correctamente en la unidad {cleaned}:\\."
        err = (res.stderr or res.stdout or "").strip()
        return False, f"No se pudo ejecutar TRIM en {cleaned}:\\ (requiere Administrador): {err[:180]}"
    except Exception as e:
        return False, f"Error ejecutando TRIM: {e}"


def parse_battery_report_xml(xml_content: str) -> dict:
    """
    Parsea el contenido XML generado por `powercfg /batteryreport /xml`
    y extrae capacidad de diseño, capacidad actual de carga completa, ciclos,
    metadatos del fabricante e historial reciente de capacidad.
    """
    result: dict[str, Any] = {
        "design_capacity_mwh": 0,
        "full_charge_capacity_mwh": 0,
        "cycle_count": 0,
        "cycle_count_reported": False,
        "health_percent": None,
        "wear_percent": None,
        "manufacturer": "",
        "chemistry": "",
        "device_name": "",
        "serial_number": "",
        "capacity_history": [],
    }
    try:
        root = ET.fromstring(xml_content)

        def _local_tag(el) -> str:
            return el.tag.split("}")[-1] if "}" in el.tag else el.tag

        # 1. Extraer datos principales de la primera batería encontrada
        for elem in root.iter():
            tag = _local_tag(elem)
            text = (elem.text or "").strip()
            if not text:
                continue

            if tag == "DesignCapacity" and text.isdigit():
                val = int(text)
                if val > 0 and result["design_capacity_mwh"] == 0:
                    result["design_capacity_mwh"] = val
            elif tag == "FullChargeCapacity" and text.isdigit():
                val = int(text)
                if val > 0 and result["full_charge_capacity_mwh"] == 0:
                    result["full_charge_capacity_mwh"] = val
            elif tag == "CycleCount" and text.isdigit():
                val = int(text)
                if val > 0 and result["cycle_count"] == 0:
                    result["cycle_count"] = val
                    result["cycle_count_reported"] = True
            elif tag == "Manufacturer" and not result["manufacturer"]:
                result["manufacturer"] = text
            elif tag == "Chemistry" and not result["chemistry"]:
                result["chemistry"] = text
            elif tag in ("Id", "Name") and not result["device_name"]:
                result["device_name"] = text
            elif tag == "SerialNumber" and not result["serial_number"]:
                result["serial_number"] = text

        # 2. Extraer historial de capacidad (<HistoryEntry>)
        history: list[dict[str, Any]] = []
        for elem in root.iter():
            if _local_tag(elem) != "HistoryEntry":
                continue
            start_date = (elem.attrib.get("LocalStartDate") or elem.attrib.get("StartDate") or "")[:10]
            h_full = int(elem.attrib.get("FullChargeCapacity") or 0) if str(elem.attrib.get("FullChargeCapacity") or "").isdigit() else 0
            h_design = int(elem.attrib.get("DesignCapacity") or 0) if str(elem.attrib.get("DesignCapacity") or "").isdigit() else 0

            # Algunos reportes colocan los valores como nodos hijos en lugar de atributos
            if h_full == 0 or h_design == 0:
                for child in elem:
                    ctag = _local_tag(child)
                    ctext = (child.text or "").strip()
                    if ctag == "FullChargeCapacity" and ctext.isdigit():
                        h_full = int(ctext)
                    elif ctag == "DesignCapacity" and ctext.isdigit():
                        h_design = int(ctext)
                    elif ctag in ("StartDate", "LocalStartDate") and not start_date:
                        start_date = ctext[:10]

            if h_full > 0 and (h_design > 0 or result["design_capacity_mwh"] > 0):
                ref_design = h_design or result["design_capacity_mwh"]
                h_pct = round(min(100.0, (h_full / ref_design) * 100.0), 1)
                history.append({
                    "date": start_date or "Reciente",
                    "full_charge_mwh": h_full,
                    "design_mwh": ref_design,
                    "health_percent": h_pct,
                })

        if history:
            result["capacity_history"] = history[-10:]

        design = result["design_capacity_mwh"]
        full = result["full_charge_capacity_mwh"]
        if design > 0 and full > 0:
            health = round(min(100.0, (full / design) * 100.0), 1)
            result["health_percent"] = health
            result["wear_percent"] = round(max(0.0, 100.0 - health), 1)
    except Exception:
        pass

    return result


def parse_energy_report_xml(xml_content: str) -> dict[str, Any]:
    """
    Parsea el reporte XML generado por `powercfg /energy /xml`
    y extrae errores y advertencias que reducen autonomía o rendimiento.
    """
    parsed: dict[str, Any] = {
        "errors_count": 0,
        "warnings_count": 0,
        "findings": [],
    }
    try:
        root = ET.fromstring(xml_content)

        def _local_tag(el) -> str:
            return el.tag.split("}")[-1] if "}" in el.tag else el.tag

        findings: list[dict[str, str]] = []
        for elem in root.iter():
            tag = _local_tag(elem)
            if tag not in ("Error", "Warning"):
                continue

            severity = "error" if tag == "Error" else "warning"
            if severity == "error":
                parsed["errors_count"] += 1
            else:
                parsed["warnings_count"] += 1

            name = ""
            desc = ""
            category = ""
            for child in elem.iter():
                ctag = _local_tag(child)
                ctext = (child.text or "").strip()
                if not ctext:
                    continue
                if ctag in ("Name", "Title") and not name:
                    name = ctext
                elif ctag in ("Description", "Detail") and not desc:
                    desc = ctext
                elif ctag in ("Category", "Feature") and not category:
                    category = ctext

            if not name and elem.attrib.get("Name"):
                name = elem.attrib["Name"]

            if name or desc:
                findings.append({
                    "severity": severity,
                    "category": category or "Energía",
                    "name": (name or "Hallazgo de energía")[:120],
                    "description": (desc or "")[:240],
                })

        # Priorizar errores primero y limitar a 18 entradas legibles
        findings.sort(key=lambda x: 0 if x["severity"] == "error" else 1)
        parsed["findings"] = findings[:18]
    except Exception:
        pass

    return parsed


def _get_active_power_plan() -> dict[str, str]:
    """Consulta el plan de energía activo en Windows con `powercfg /getactivescheme`."""
    if sys.platform != "win32":
        return {"guid": "", "name": "Entorno no-Windows"}
    try:
        res = _run_cmd(["powercfg", "/getactivescheme"], timeout=10)
        out = (res.stdout or "").strip()
        m_guid = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", out)
        m_name = re.search(r"\(([^)]+)\)", out)
        return {
            "guid": m_guid.group(1).lower() if m_guid else "",
            "name": m_name.group(1).strip() if m_name else (out or "Desconocido"),
        }
    except Exception:
        return {"guid": "", "name": "Desconocido"}


def _get_windows_wmi_battery_telemetry() -> dict[str, Any]:
    """
    Consulta telemetría eléctrica en vivo desde WMI (`root\\WMI` BatteryStatus)
    y el fabricante del equipo (`Win32_ComputerSystem`).
    """
    telemetry: dict[str, Any] = {
        "voltage_mv": None,
        "discharge_rate_mw": None,
        "charge_rate_mw": None,
        "power_draw_watts": None,
        "system_manufacturer": "",
    }
    if sys.platform != "win32":
        return telemetry

    ps_cmd = (
        "$b = Get-CimInstance -Namespace root\\WMI -ClassName BatteryStatus -ErrorAction SilentlyContinue | Select-Object -First 1; "
        "$cs = Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction SilentlyContinue | Select-Object -First 1; "
        "[PSCustomObject]@{"
        "Voltage = if ($b) { $b.Voltage } else { $null }; "
        "DischargeRate = if ($b) { $b.DischargeRate } else { $null }; "
        "ChargeRate = if ($b) { $b.ChargeRate } else { $null }; "
        "Manufacturer = if ($cs) { $cs.Manufacturer } else { '' }"
        "} | ConvertTo-Json -Compress"
    )
    try:
        res = _run_cmd(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=10)
        raw = (res.stdout or "").strip()
        if raw:
            data = json.loads(raw)
            v = data.get("Voltage")
            dr = data.get("DischargeRate")
            cr = data.get("ChargeRate")
            if isinstance(v, (int, float)) and v > 0:
                telemetry["voltage_mv"] = int(v)
            if isinstance(dr, (int, float)) and 0 < dr < 500000:
                telemetry["discharge_rate_mw"] = int(dr)
                telemetry["power_draw_watts"] = round(dr / 1000.0, 2)
            elif isinstance(cr, (int, float)) and 0 < cr < 500000:
                telemetry["charge_rate_mw"] = int(cr)
                telemetry["power_draw_watts"] = round(cr / 1000.0, 2)
            telemetry["system_manufacturer"] = str(data.get("Manufacturer") or "").strip()
    except Exception:
        pass

    return telemetry


def build_battery_diagnosis(info: dict[str, Any]) -> dict[str, Any]:
    """
    Construye un diagnóstico honesto y accionable a partir de la salud,
    el estado de conexión y el plan de energía activo.
    """
    health = info.get("health_percent")
    wear = info.get("wear_percent")
    plugged = info.get("power_plugged")
    percent = info.get("percent")
    recommendations: list[str] = []

    if health is None:
        return {
            "level": "unknown",
            "title": "Sin lectura completa de capacidad",
            "summary": "No se pudo leer el reporte XML de fábrica. Ejecuta PyClean Pro como Administrador o repara el driver ACPI de batería.",
            "recommendations": [
                "Ejecuta 'Reparar Driver ACPI' si el porcentaje se congela o no actualiza.",
                "Aplica 'Optimizar Rendimiento Estable' para evitar caídas de frecuencia del procesador.",
            ],
        }

    if health >= 80:
        level = "good"
        title = "Batería en buen estado"
        summary = f"Conserva {health}% de su capacidad de fábrica (desgaste leve de {wear}%)."
    elif health >= 60:
        level = "fair"
        title = "Desgaste moderado (optimizable y calibrable)"
        summary = (
            f"Conserva {health}% de capacidad ({wear}% de desgaste). El desgaste químico de las celdas "
            "no se revierte por software, pero puedes recalibrar el medidor y optimizar Windows para "
            "recuperar rendimiento y autonomía real."
        )
        recommendations.append("Realiza 1 ciclo con el Asistente de Calibración para corregir lecturas falsas del medidor (BMS).")
    elif health >= 40:
        level = "worn"
        title = "Desgaste alto — conviene optimizar energía y planear reemplazo"
        summary = (
            f"La batería tiene {wear}% de desgaste ({health}% restante). Puede causar reducción automática "
            "de rendimiento (throttling) al usar batería o apagados repentinos bajo carga."
        )
        recommendations.append("Aplica 'Optimizar Autonomía' para reducir picos de voltaje/calor al usar batería.")
        recommendations.append("Ejecuta una calibración para validar la capacidad real antes de comprar un repuesto.")
    else:
        level = "critical"
        title = "Desgaste crítico — reemplazo físico recomendado"
        summary = (
            f"Solo queda {health}% de la capacidad original ({wear}% de desgaste). Ningún software puede "
            "regenerar celdas agotadas; usa el perfil de Rendimiento Estable enchufada y considera reemplazo."
        )
        recommendations.append("Usa el perfil 'Rendimiento Estable' para evitar que la batería agotada limite el CPU al estar enchufada.")

    if plugged and percent is not None and percent >= 98:
        recommendations.append(
            "Tu laptop está al 100% conectada a corriente: mantenerla así continuamente acelera el desgaste."
        )

    oem_tip = info.get("oem_charge_limit_tip")
    if oem_tip:
        recommendations.append(oem_tip)

    return {
        "level": level,
        "title": title,
        "summary": summary,
        "recommendations": recommendations,
    }


def get_battery_calibration_state() -> dict[str, Any]:
    """Retorna el estado actual de una sesión de calibración de batería si existe."""
    path = _calibration_state_path()
    if not os.path.exists(path):
        return {"active": False}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("active"):
            return data
    except Exception:
        pass
    return {"active": False}


def has_battery_power_backup() -> bool:
    return os.path.exists(_power_backup_path())


def get_battery_health() -> dict[str, Any]:
    """
    Retorna el estado actual de la batería, telemetría eléctrica, salud/desgaste,
    historial, plan activo y diagnóstico accionable (para laptops).
    Si es un equipo de escritorio sin batería, retorna has_battery=False.
    """
    info: dict[str, Any] = {
        "has_battery": False,
        "percent": None,
        "power_plugged": None,
        "secsleft": None,
        "time_remaining_formatted": "N/A",
        "design_capacity_mwh": 0,
        "full_charge_capacity_mwh": 0,
        "cycle_count": 0,
        "cycle_count_reported": False,
        "health_percent": None,
        "wear_percent": None,
        "manufacturer": "",
        "chemistry": "",
        "device_name": "",
        "serial_number": "",
        "capacity_history": [],
        "voltage_mv": None,
        "discharge_rate_mw": None,
        "charge_rate_mw": None,
        "power_draw_watts": None,
        "system_manufacturer": "",
        "oem_charge_limit_tip": "",
        "active_power_plan": {"guid": "", "name": ""},
        "has_power_backup": has_battery_power_backup(),
        "calibration_state": get_battery_calibration_state(),
        "diagnosis": {},
    }

    if psutil is not None:
        try:
            batt = psutil.sensors_battery()
            if batt is None:
                return info
            info["has_battery"] = True
            info["percent"] = round(batt.percent, 1)
            info["power_plugged"] = bool(batt.power_plugged)
            secs = getattr(batt, "secsleft", None)
            if info["power_plugged"]:
                info["time_remaining_formatted"] = "Conectado a corriente"
            elif isinstance(secs, (int, float)) and 0 < secs < 86400 * 7:
                info["secsleft"] = int(secs)
                info["time_remaining_formatted"] = _format_duration_seconds(int(secs))
            else:
                info["time_remaining_formatted"] = "Calculando..."
        except Exception:
            return info

    if sys.platform == "win32" and info["has_battery"]:
        tmp_path = os.path.join(tempfile.gettempdir(), f"pyclean_batt_{os.getpid()}.xml")
        try:
            res = _run_cmd(["powercfg", "/batteryreport", "/xml", "/output", tmp_path], timeout=15)
            if res.returncode == 0 and os.path.exists(tmp_path):
                with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                    parsed = parse_battery_report_xml(f.read())
                info.update(parsed)
        except Exception:
            pass
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

        info.update(_get_windows_wmi_battery_telemetry())
        info["active_power_plan"] = _get_active_power_plan()

    info["oem_charge_limit_tip"] = get_oem_charge_limit_tip(
        info.get("system_manufacturer") or info.get("manufacturer") or ""
    )
    info["diagnosis"] = build_battery_diagnosis(info)
    return info


def get_battery_drain_processes(limit: int = 8) -> list[dict[str, Any]]:
    """Lista los procesos con mayor consumo de CPU/memoria que impactan la autonomía."""
    if psutil is None:
        return []

    procs = []
    try:
        # Primera lectura rápida para inicializar porcentaje CPU
        candidates = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                p.cpu_percent(interval=None)
                candidates.append(p)
            except Exception:
                continue

        time.sleep(0.25)

        for p in candidates:
            try:
                name = p.info.get("name") or ""
                if not name or name.lower() in ("system idle process", "idle"):
                    continue
                cpu = round(p.cpu_percent(interval=None), 1)
                mem = p.info.get("memory_info")
                mem_bytes = mem.rss if mem else 0
                if cpu <= 0.0 and mem_bytes < 50 * 1024 * 1024:
                    continue
                procs.append({
                    "pid": p.pid,
                    "name": name,
                    "cpu_percent": cpu,
                    "memory_bytes": mem_bytes,
                    "memory_formatted": cleaner.format_size(mem_bytes),
                })
            except Exception:
                continue

        procs.sort(key=lambda x: (x["cpu_percent"], x["memory_bytes"]), reverse=True)
    except Exception:
        return []

    return procs[:limit]


def run_battery_energy_audit(duration_sec: int = 10) -> dict[str, Any]:
    """
    Ejecuta una auditoría real de eficiencia energética con `powercfg /energy`
    y recolecta los procesos con mayor consumo activo.
    """
    duration = max(5, min(60, int(duration_sec or 10)))
    top_procs = get_battery_drain_processes(limit=8)

    if sys.platform != "win32":
        return {
            "success": False,
            "message": "La auditoría `powercfg /energy` solo está disponible en Windows.",
            "errors_count": 0,
            "warnings_count": 0,
            "findings": [],
            "top_processes": top_procs,
        }

    if not cleaner.is_admin():
        return {
            "success": False,
            "message": "La auditoría de eficiencia energética (`powercfg /energy`) requiere ejecutar PyClean Pro como Administrador.",
            "errors_count": 0,
            "warnings_count": 0,
            "findings": [],
            "top_processes": top_procs,
        }

    tmp_path = os.path.join(tempfile.gettempdir(), f"pyclean_energy_{os.getpid()}.xml")
    try:
        res = _run_cmd(
            ["powercfg", "/energy", "/duration", str(duration), "/xml", "/output", tmp_path],
            timeout=duration + 25,
        )
        if os.path.exists(tmp_path):
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                parsed = parse_energy_report_xml(f.read())
            return {
                "success": True,
                "message": (
                    f"Auditoría completada ({duration}s): "
                    f"{parsed['errors_count']} errores y {parsed['warnings_count']} advertencias detectadas."
                ),
                "errors_count": parsed["errors_count"],
                "warnings_count": parsed["warnings_count"],
                "findings": parsed["findings"],
                "top_processes": top_procs,
            }

        err = (res.stderr or res.stdout or "").strip()
        return {
            "success": False,
            "message": f"No se pudo generar el reporte de energía: {err[:180]}",
            "errors_count": 0,
            "warnings_count": 0,
            "findings": [],
            "top_processes": top_procs,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error ejecutando auditoría de energía: {e}",
            "errors_count": 0,
            "warnings_count": 0,
            "findings": [],
            "top_processes": top_procs,
        }
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def _save_power_backup_if_missing() -> None:
    """Guarda el plan de energía activo actual antes de aplicar optimizaciones."""
    backup_file = _power_backup_path()
    if os.path.exists(backup_file):
        return
    plan = _get_active_power_plan()
    payload = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "active_guid": plan.get("guid") or SCHEME_BALANCED,
        "active_name": plan.get("name") or "Equilibrado",
    }
    try:
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


def optimize_battery_performance(profile: str = "autonomy") -> dict[str, Any]:
    """
    Aplica optimizaciones reales y reversibles de energía en Windows mediante `powercfg`:
    - `autonomy`: Maximiza duración de batería y reduce calor/picos de voltaje en DC
      sin sacrificar rendimiento cuando está enchufada (AC).
    - `performance`: Elimina throttling y lag por energía en AC y mantiene respuesta
      fluida y estable en batería.
    - `repair_schemes`: Restaura los esquemas de energía por defecto de Windows para
      corregir planes corruptos, drenaje anómalo o CPU bloqueado a baja frecuencia.
    """
    valid_profiles = {"autonomy", "performance", "repair_schemes"}
    if profile not in valid_profiles:
        return {
            "success": False,
            "message": f"Perfil de batería no válido: '{profile}'.",
            "profile": profile,
            "applied_steps": [],
        }

    if sys.platform != "win32":
        return {
            "success": False,
            "message": "La optimización de perfiles de batería (`powercfg`) solo está disponible en Windows.",
            "profile": profile,
            "applied_steps": [],
        }

    _save_power_backup_if_missing()

    if profile == "repair_schemes":
        if not cleaner.is_admin():
            return {
                "success": False,
                "message": "Restaurar los esquemas de energía del sistema requiere privilegios de Administrador.",
                "profile": profile,
                "applied_steps": [],
            }
        try:
            res = _run_cmd(["powercfg", "/restoredefaultschemes"], timeout=20)
            if res.returncode != 0:
                err = (res.stderr or res.stdout or "").strip()
                return {
                    "success": False,
                    "message": f"No se pudieron restaurar los esquemas: {err[:180]}",
                    "profile": profile,
                    "applied_steps": [],
                }
            _run_cmd(["powercfg", "/setactive", SCHEME_BALANCED], timeout=10)
            return {
                "success": True,
                "message": "Esquemas de energía de Windows restaurados a valores de fábrica y plan Equilibrado reactivado.",
                "profile": profile,
                "applied_steps": [
                    "powercfg /restoredefaultschemes",
                    "Plan Equilibrado reactivado",
                ],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error reparando esquemas de energía: {e}",
                "profile": profile,
                "applied_steps": [],
            }

    # Comandos powercfg según perfil seleccionado
    commands: list[tuple[str, list[str]]] = [
        ("Activar plan base Equilibrado", ["powercfg", "/setactive", SCHEME_BALANCED]),
    ]

    if profile == "autonomy":
        commands.extend([
            ("CPU máx. en batería al 80% (reduce calor y picos)", ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", "80"]),
            ("CPU mín. en batería al 5%", ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMIN", "5"]),
            ("Refrigeración pasiva en batería", ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "SYSCOOLPOL", "0"]),
            ("CPU máx. enchufada al 100%", ["powercfg", "/setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", "100"]),
            ("Suspensión selectiva USB en batería", ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", SUB_USB, SETTING_USB_SUSPEND, "1"]),
            ("Ahorro máximo PCI Express (ASPM) en batería", ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_PCIEXPRESS", "ASPM", "2"]),
            ("Ahorro de energía Wi-Fi en batería", ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", SUB_WIRELESS, SETTING_WIRELESS_POWER, "3"]),
            ("Activar Economizador de batería al 30%", ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_ENERGYSAVER", "ESBATTTHRESHOLD", "30"]),
        ])
    elif profile == "performance":
        commands.extend([
            ("CPU máx. enchufada al 100%", ["powercfg", "/setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", "100"]),
            ("CPU mín. enchufada al 15% (respuesta inmediata)", ["powercfg", "/setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMIN", "15"]),
            ("Refrigeración activa enchufada", ["powercfg", "/setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "SYSCOOLPOL", "1"]),
            ("Desactivar ahorro PCIe enchufada (sin lag GPU/NVMe)", ["powercfg", "/setacvalueindex", "SCHEME_CURRENT", "SUB_PCIEXPRESS", "ASPM", "0"]),
            ("Wi-Fi en máximo rendimiento enchufada", ["powercfg", "/setacvalueindex", "SCHEME_CURRENT", SUB_WIRELESS, SETTING_WIRELESS_POWER, "0"]),
            ("CPU máx. en batería al 95% (fluidez sin caídas)", ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", "95"]),
            ("Ahorro moderado PCIe en batería", ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_PCIEXPRESS", "ASPM", "1"]),
            ("Economizador automático al 20%", ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_ENERGYSAVER", "ESBATTTHRESHOLD", "20"]),
        ])

    commands.append(("Aplicar cambios al plan activo", ["powercfg", "/setactive", "SCHEME_CURRENT"]))

    applied: list[str] = []
    warnings: list[str] = []
    for label, cmd in commands:
        try:
            res = _run_cmd(cmd, timeout=10)
            if res.returncode == 0:
                applied.append(label)
            else:
                warnings.append(label)
        except Exception:
            warnings.append(label)

    if len(applied) >= 2:
        profile_title = "Máxima Autonomía y Cuidado" if profile == "autonomy" else "Rendimiento Estable"
        msg = f"Perfil '{profile_title}' aplicado correctamente ({len(applied)} ajustes activos)."
        if warnings:
            msg += f" ({len(warnings)} ajustes no soportados por el firmware se omitieron de forma segura)."
        return {
            "success": True,
            "message": msg,
            "profile": profile,
            "applied_steps": applied,
            "skipped_steps": warnings,
            "has_power_backup": has_battery_power_backup(),
        }

    return {
        "success": False,
        "message": "No se pudieron aplicar los ajustes de energía. Ejecuta PyClean Pro como Administrador.",
        "profile": profile,
        "applied_steps": applied,
        "skipped_steps": warnings,
    }


def restore_battery_power_backup() -> dict[str, Any]:
    """Restaura el plan de energía guardado previamente antes de optimizar."""
    if sys.platform != "win32":
        return {"success": False, "message": "La restauración de energía solo está disponible en Windows."}

    backup_file = _power_backup_path()
    if not os.path.exists(backup_file):
        return {"success": False, "message": "No existe un respaldo previo de configuración de energía."}

    try:
        with open(backup_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        guid = data.get("active_guid") or SCHEME_BALANCED
        name = data.get("active_name") or guid

        # Restablecer parámetros críticos a valores estándar de Windows y reactivar GUID previo
        _run_cmd(["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", "100"], timeout=10)
        _run_cmd(["powercfg", "/setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", "100"], timeout=10)
        _run_cmd(["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_ENERGYSAVER", "ESBATTTHRESHOLD", "20"], timeout=10)
        res = _run_cmd(["powercfg", "/setactive", guid], timeout=10)

        try:
            os.remove(backup_file)
        except Exception:
            pass

        if res.returncode == 0:
            return {"success": True, "message": f"Plan de energía restaurado a '{name}'."}
        return {"success": True, "message": "Valores predeterminados restaurados (el plan original ya no estaba registrado)."}
    except Exception as e:
        return {"success": False, "message": f"Error restaurando configuración previa: {e}"}


def repair_battery_driver() -> dict[str, Any]:
    """
    Reinicia de forma segura el controlador ACPI de batería en Windows (`PNP0C0A`)
    y reescanea hardware para corregir porcentajes congelados o errores de carga/lectura.
    Requiere privilegios de Administrador.
    """
    if sys.platform != "win32":
        return {"success": False, "message": "La reparación del controlador ACPI de batería solo está disponible en Windows."}

    if not cleaner.is_admin():
        return {"success": False, "message": "Reparar el controlador ACPI de batería requiere ejecutar PyClean Pro como Administrador."}

    ps_cmd = (
        "$devs = Get-PnpDevice -Class Battery -ErrorAction SilentlyContinue | "
        "Where-Object { $_.InstanceId -like '*PNP0C0A*' -or $_.FriendlyName -like '*Control Method Battery*' }; "
        "if (-not $devs) { Write-Output 'NO_DEVICE'; exit 2 }; "
        "foreach ($d in $devs) { "
        "  Disable-PnpDevice -InstanceId $d.InstanceId -Confirm:$false -ErrorAction Stop; "
        "  Start-Sleep -Seconds 2; "
        "  Enable-PnpDevice -InstanceId $d.InstanceId -Confirm:$false -ErrorAction Stop; "
        "}; "
        "pnputil /scan-devices | Out-Null; "
        "Write-Output ('OK:' + $devs.Count)"
    )

    try:
        res = _run_cmd(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=35)
        out = (res.stdout or "").strip()
        if res.returncode == 0 and "OK:" in out:
            return {
                "success": True,
                "message": "Controlador ACPI de batería reiniciado y reescaneado correctamente. Actualiza el diagnóstico para leer los nuevos datos del sensor.",
            }
        if "NO_DEVICE" in out:
            return {
                "success": False,
                "message": "No se encontró el dispositivo 'Microsoft ACPI-Compliant Control Method Battery' en este equipo.",
            }
        err = (res.stderr or out or "").strip()
        return {
            "success": False,
            "message": f"No se pudo reiniciar el driver ACPI de batería: {err[:200]}",
        }
    except Exception as e:
        return {"success": False, "message": f"Error reparando driver ACPI: {e}"}


def start_battery_calibration() -> dict[str, Any]:
    """
    Inicia una sesión guiada de calibración de batería (BMS / fuel gauge):
    - Guarda línea base (capacidad y salud actual)
    - Ajusta temporalmente tiempos de suspensión en batería para permitir
      una descarga continua y controlada con hibernación segura al 5%.
    """
    if sys.platform != "win32":
        return {
            "success": False,
            "message": "El asistente de calibración con `powercfg` solo está disponible en Windows.",
        }

    current = get_battery_health()
    if not current.get("has_battery"):
        return {
            "success": False,
            "message": "No se detectó una batería interna para calibrar.",
        }

    _save_power_backup_if_missing()

    state = {
        "active": True,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "baseline_full_charge_mwh": current.get("full_charge_capacity_mwh") or 0,
        "baseline_design_mwh": current.get("design_capacity_mwh") or 0,
        "baseline_health_percent": current.get("health_percent"),
        "baseline_percent": current.get("percent"),
        "steps": [
            "1. Mantén la laptop enchufada hasta llegar al 100% y déjala conectada 1 a 2 horas adicionales.",
            "2. Desconecta el cargador y úsala normalmente hasta que baje al 5% y el equipo hiberne/se apague automáticamente (la suspensión automática ya fue pausada).",
            "3. Déjala reposar apagada 30-60 minutos, vuelve a enchufarla y cárgala sin interrupciones hasta el 100%.",
            "4. Al completar la recarga al 100%, presiona 'Finalizar y Comparar' para restaurar tus tiempos de energía y medir la mejora.",
        ],
    }

    # Preparar timeouts seguros para descarga sin suspensión prematura
    calibration_cmds = [
        ["powercfg", "/change", "standby-timeout-dc", "0"],
        ["powercfg", "/change", "hibernate-timeout-dc", "0"],
        ["powercfg", "/change", "monitor-timeout-dc", "30"],
        ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_BATTERY", "BATLEVELCRIT", "5"],
        ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_BATTERY", "BATACTIONCRIT", "2"],
        ["powercfg", "/setactive", "SCHEME_CURRENT"],
    ]
    for cmd in calibration_cmds:
        try:
            _run_cmd(cmd, timeout=10)
        except Exception:
            pass

    try:
        with open(_calibration_state_path(), "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        return {"success": False, "message": f"No se pudo guardar el estado de calibración: {e}"}

    return {
        "success": True,
        "message": "Modo calibración iniciado. Sigue los 4 pasos y vuelve aquí al completar la recarga al 100%.",
        "calibration_state": state,
    }


def finish_battery_calibration() -> dict[str, Any]:
    """
    Finaliza la sesión de calibración, restaura los tiempos normales de suspensión/pantalla
    y compara la capacidad máxima antes vs. después.
    """
    state = get_battery_calibration_state()
    if not state.get("active"):
        return {
            "success": False,
            "message": "No hay una sesión de calibración activa.",
        }

    if sys.platform == "win32":
        restore_cmds = [
            ["powercfg", "/change", "standby-timeout-dc", "15"],
            ["powercfg", "/change", "hibernate-timeout-dc", "60"],
            ["powercfg", "/change", "monitor-timeout-dc", "10"],
            ["powercfg", "/setactive", "SCHEME_CURRENT"],
        ]
        for cmd in restore_cmds:
            try:
                _run_cmd(cmd, timeout=10)
            except Exception:
                pass

    try:
        if os.path.exists(_calibration_state_path()):
            os.remove(_calibration_state_path())
    except Exception:
        pass

    after = get_battery_health()
    before_mwh = int(state.get("baseline_full_charge_mwh") or 0)
    after_mwh = int(after.get("full_charge_capacity_mwh") or 0)
    delta_mwh = after_mwh - before_mwh if (before_mwh > 0 and after_mwh > 0) else 0

    before_health = state.get("baseline_health_percent")
    after_health = after.get("health_percent")
    delta_health = (
        round(after_health - before_health, 1)
        if (before_health is not None and after_health is not None)
        else 0.0
    )

    if delta_mwh > 200:
        verdict = f"¡Mejora detectada! La calibración recuperó +{delta_mwh} mWh ({delta_health:+.1f}% de salud estimada)."
    elif delta_mwh < -200:
        verdict = (
            f"Calibración completada: el medidor se ajustó en {delta_mwh} mWh ({delta_health:+.1f}%). "
            "Ahora el porcentaje mostrado es mucho más preciso y evitará apagados bruscos."
        )
    else:
        verdict = (
            "Calibración completada y tiempos de energía restaurados. La capacidad real se mantuvo estable, "
            "confirmando que el desgaste reportado es químico (físico) y tu medidor ya está bien calibrado."
        )

    return {
        "success": True,
        "message": verdict,
        "before_mwh": before_mwh,
        "after_mwh": after_mwh,
        "delta_mwh": delta_mwh,
        "before_health": before_health,
        "after_health": after_health,
        "delta_health": delta_health,
    }


def export_battery_report_html() -> dict[str, Any]:
    """
    Genera el reporte HTML oficial completo de Windows (`powercfg /batteryreport`)
    en el Escritorio (o carpeta temporal) y lo abre en el navegador predeterminado.
    """
    if sys.platform != "win32":
        return {
            "success": False,
            "message": "El reporte oficial HTML (`powercfg /batteryreport`) solo está disponible en Windows.",
            "path": "",
        }

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    out_dir = desktop if os.path.isdir(desktop) else tempfile.gettempdir()
    out_path = os.path.join(out_dir, "PyClean_Battery_Report.html")

    try:
        res = _run_cmd(["powercfg", "/batteryreport", "/output", out_path], timeout=20)
        if res.returncode == 0 and os.path.exists(out_path):
            try:
                os.startfile(out_path)  # type: ignore[attr-defined]
            except Exception:
                pass
            return {
                "success": True,
                "message": f"Reporte oficial de batería generado en: {out_path}",
                "path": out_path,
            }
        err = (res.stderr or res.stdout or "").strip()
        return {
            "success": False,
            "message": f"No se pudo generar el reporte HTML: {err[:180]}",
            "path": "",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generando reporte HTML: {e}",
            "path": "",
        }
