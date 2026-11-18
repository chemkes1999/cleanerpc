"""
PyClean Pro v2.4 - Salud de Hardware (SSD S.M.A.R.T., TRIM y Batería)
Inspecciona el estado físico de los discos en Windows, ejecuta optimización TRIM
para SSDs y analiza el desgaste real de la batería en portátiles.
"""

from __future__ import annotations

import os
import re
import sys
import json
import tempfile
import subprocess
import xml.etree.ElementTree as ET
import cleaner

try:
    import psutil
except ImportError:
    psutil = None


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

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    disks = []
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=12,
            startupinfo=startupinfo,
        )
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

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    ps_cmd = f"Optimize-Volume -DriveLetter {cleaned} -ReTrim"
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=60,
            startupinfo=startupinfo,
        )
        if res.returncode == 0:
            return True, f"Optimización TRIM ejecutada correctamente en la unidad {cleaned}:\\."
        err = (res.stderr or res.stdout or "").strip()
        return False, f"No se pudo ejecutar TRIM en {cleaned}:\\ (requiere Administrador): {err[:180]}"
    except Exception as e:
        return False, f"Error ejecutando TRIM: {e}"


def parse_battery_report_xml(xml_content: str) -> dict:
    """
    Parsea el contenido XML generado por `powercfg /batteryreport /xml`
    y extrae capacidad de diseño, capacidad actual de carga completa y ciclos.
    """
    result = {
        "design_capacity_mwh": 0,
        "full_charge_capacity_mwh": 0,
        "cycle_count": 0,
        "health_percent": None,
        "wear_percent": None,
    }
    try:
        root = ET.fromstring(xml_content)
        # Ignorar namespaces XML buscando por sufijo de etiqueta
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            text = (elem.text or "").strip()
            if not text.isdigit():
                continue
            val = int(text)
            if tag == "DesignCapacity" and val > 0 and result["design_capacity_mwh"] == 0:
                result["design_capacity_mwh"] = val
            elif tag == "FullChargeCapacity" and val > 0 and result["full_charge_capacity_mwh"] == 0:
                result["full_charge_capacity_mwh"] = val
            elif tag == "CycleCount" and val >= 0 and result["cycle_count"] == 0:
                result["cycle_count"] = val

        design = result["design_capacity_mwh"]
        full = result["full_charge_capacity_mwh"]
        if design > 0 and full > 0:
            health = round(min(100.0, (full / design) * 100.0), 1)
            result["health_percent"] = health
            result["wear_percent"] = round(max(0.0, 100.0 - health), 1)
    except Exception:
        pass

    return result


def get_battery_health() -> dict:
    """
    Retorna el estado actual de la batería y su salud/desgaste (para laptops).
    Si es un equipo de escritorio sin batería, retorna has_battery=False.
    """
    info = {
        "has_battery": False,
        "percent": None,
        "power_plugged": None,
        "design_capacity_mwh": 0,
        "full_charge_capacity_mwh": 0,
        "cycle_count": 0,
        "health_percent": None,
        "wear_percent": None,
    }

    if psutil is not None:
        try:
            batt = psutil.sensors_battery()
            if batt is None:
                return info
            info["has_battery"] = True
            info["percent"] = round(batt.percent, 1)
            info["power_plugged"] = bool(batt.power_plugged)
        except Exception:
            return info

    if sys.platform == "win32" and info["has_battery"]:
        tmp_path = os.path.join(tempfile.gettempdir(), f"pyclean_batt_{os.getpid()}.xml")
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        try:
            res = subprocess.run(
                ["powercfg", "/batteryreport", "/xml", "/output", tmp_path],
                capture_output=True,
                text=True,
                timeout=15,
                startupinfo=startupinfo,
            )
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

    return info
