"""
PyClean Pro v2.4 - Módulo de Optimización del Sistema y Ajuste de Red (sys_optimizer.py)
Provee herramientas avanzadas de tuning de rendimiento para Windows:
- Desbloqueo y activación del plan oculto 'Ultimate Performance'
- Auto-tuning de la pila de red TCP/IP
- Reindexación profunda y reparación de Windows Search
- Consulta y compresión transparente del sistema con Compact OS
"""

from __future__ import annotations

import sys
import os
import subprocess
import logging
import re
from typing import Any, Optional

import cleaner

# Importación condicional de winreg para Windows
try:
    import winreg
except ImportError:
    winreg = None

logger = logging.getLogger("pyclean.optimizer")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# GUID canónico del esquema Ultimate Performance de Windows
ULTIMATE_PERF_GUID = "e9a42b02-d5df-448d-aa00-03f14749eb61"


def _get_startupinfo():
    """Genera una estructura STARTUPINFO segura para ocultar ventanas en Windows."""
    if sys.platform == "win32" and hasattr(subprocess, "STARTUPINFO"):
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None


def unlock_ultimate_performance_plan() -> dict[str, Any]:
    """
    Desbloquea y activa el plan de energía oculto 'Ultimate Performance' (Máximo Rendimiento)
    mediante powercfg.
    Requiere privilegios de Administrador en Windows.
    """
    if sys.platform != "win32" or not cleaner.is_admin():
        return {
            "success": False,
            "message": "Requiere privilegios de Administrador en Windows",
            "guid": ""
        }

    si = _get_startupinfo()
    target_guid = ULTIMATE_PERF_GUID

    try:
        # 1. Comprobar esquemas disponibles actualmente
        list_res = subprocess.run(
            ["powercfg", "/list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            startupinfo=si
        )
        stdout_lower = (list_res.stdout or "").lower()

        guid_to_activate = target_guid
        # Si el GUID o nombre no está presente en la lista, duplicarlo
        if target_guid.lower() not in stdout_lower and "ultimate performance" not in stdout_lower and "rendimiento máximo" not in stdout_lower:
            dup_res = subprocess.run(
                ["powercfg", "/duplicatescheme", target_guid],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
                startupinfo=si
            )
            # Extraer el nuevo GUID generado si powercfg lo reporta
            m = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", dup_res.stdout or "")
            if m:
                guid_to_activate = m.group(1).lower()

        # 2. Activar el esquema seleccionado
        set_res = subprocess.run(
            ["powercfg", "/setactive", guid_to_activate],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            startupinfo=si
        )

        success = (set_res.returncode == 0)
        msg = "Plan de Máximo Rendimiento activado con éxito" if success else (set_res.stderr or set_res.stdout or "").strip()
        return {
            "success": success,
            "message": msg,
            "guid": guid_to_activate
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error al configurar plan de energía: {e}",
            "guid": target_guid
        }


def tune_tcp_network(enable_autotuning: bool = True) -> dict[str, Any]:
    """
    Ajusta y optimiza los parámetros de la pila TCP/IP global mediante netsh.
    Requiere privilegios de Administrador en Windows.
    """
    if sys.platform != "win32" or not cleaner.is_admin():
        return {
            "success": False,
            "message": "Requiere privilegios de Administrador en Windows",
            "autotuning": ""
        }

    si = _get_startupinfo()
    level = "normal" if enable_autotuning else "disabled"

    try:
        # Configurar nivel de autotuning
        res = subprocess.run(
            ["netsh", "int", "tcp", "set", "global", f"autotuninglevel={level}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            startupinfo=si
        )

        if res.returncode == 0 and enable_autotuning:
            # Optimizaciones complementarias: ECN y RSS (Receive-Side Scaling)
            try:
                subprocess.run(
                    ["netsh", "int", "tcp", "set", "global", "ecncapability=enabled"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                    startupinfo=si
                )
                subprocess.run(
                    ["netsh", "int", "tcp", "set", "global", "rss=enabled"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                    startupinfo=si
                )
            except Exception:
                pass

        success = (res.returncode == 0)
        msg = "Pila de red TCP optimizada correctamente" if success else (res.stderr or res.stdout or "").strip()
        return {
            "success": success,
            "message": msg,
            "autotuning": level
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error al configurar TCP: {e}",
            "autotuning": level
        }


def reindex_windows_search() -> dict[str, Any]:
    """
    Detiene el servicio WSearch, reinicia el flag de configuración en el Registro
    para purgar la base de datos Windows.edb y reinicia el servicio.
    Requiere privilegios de Administrador en Windows.
    """
    if sys.platform != "win32" or not cleaner.is_admin():
        return {
            "success": False,
            "message": "Requiere privilegios de Administrador en Windows"
        }

    si = _get_startupinfo()

    try:
        # 1. Detener el servicio WSearch
        subprocess.run(
            ["net", "stop", "WSearch"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            startupinfo=si
        )

        # 2. Modificar el registro para forzar reconstrucción de índice
        if winreg is not None:
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Windows Search",
                    0,
                    winreg.KEY_SET_VALUE
                )
                winreg.SetValueEx(key, "SetupCompletedSuccessfully", 0, winreg.REG_DWORD, 0)
                winreg.CloseKey(key)
            except Exception as reg_err:
                logger.warning(f"Aviso al modificar clave de registro de Windows Search: {reg_err}")

        # 3. Iniciar el servicio WSearch
        subprocess.run(
            ["net", "start", "WSearch"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            startupinfo=si
        )

        return {
            "success": True,
            "message": "Servicio de búsqueda reiniciado y reconstrucción de índice solicitada exitosamente"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error al reindexar Windows Search: {e}"
        }


def get_compact_os_status() -> dict[str, Any]:
    """
    Consulta el estado actual de compresión del sistema operativo Compact OS mediante compact.exe.
    Soporta análisis de respuestas tanto en inglés como en español.
    """
    if sys.platform != "win32":
        return {
            "success": False,
            "is_compact": False,
            "raw_output": "Compact OS solo está disponible en Windows"
        }

    si = _get_startupinfo()

    try:
        res = subprocess.run(
            ["compact.exe", "/compactos:query"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            startupinfo=si
        )

        raw_output = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
        raw_output_clean = raw_output.strip()
        lower_out = raw_output_clean.lower()

        # Detección del estado compacto
        is_compact = False
        if "is in the compact state" in lower_out or "está en el estado compacto" in lower_out or "está en estado compacto" in lower_out:
            if "not in the compact state" not in lower_out and "no está en" not in lower_out:
                is_compact = True

        return {
            "success": (res.returncode == 0),
            "is_compact": is_compact,
            "raw_output": raw_output_clean
        }
    except Exception as e:
        return {
            "success": False,
            "is_compact": False,
            "raw_output": str(e)
        }


def toggle_compact_os(enable: bool) -> dict[str, Any]:
    """
    Activa o desactiva la compresión transparente de archivos de sistema Compact OS.
    Requiere privilegios de Administrador en Windows.
    """
    if sys.platform != "win32" or not cleaner.is_admin():
        return {
            "success": False,
            "is_compact": False,
            "message": "Requiere privilegios de Administrador en Windows"
        }

    si = _get_startupinfo()
    flag = "/compactos:always" if enable else "/compactos:never"

    try:
        res = subprocess.run(
            ["compact.exe", flag],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=600,
            startupinfo=si
        )

        success = (res.returncode == 0)
        msg = "Estado de Compact OS actualizado correctamente" if success else (res.stderr or res.stdout or "").strip()
        return {
            "success": success,
            "is_compact": enable if success else False,
            "message": msg
        }
    except Exception as e:
        return {
            "success": False,
            "is_compact": False,
            "message": f"Error al modificar Compact OS: {e}"
        }
