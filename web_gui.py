"""
PyClean Pro v2.1 - Interfaz Gráfica Web Moderna (PyWebView + GSAP)
Provee la API de comunicación entre el frontend Web (HTML/CSS/JS + GSAP)
y el motor de limpieza en Python (cleaner.py).
"""

from __future__ import annotations

import os
import sys
import threading
import subprocess
import json
from pathlib import Path
import cleaner

try:
    import webview
except ImportError:
    webview = None


class PyCleanAPI:
    def __init__(self):
        self._window = None
        self._is_busy = False

    def set_window(self, window):
        self._window = window

    def log(self, message: str, tag: str = "dim"):
        """Envía un mensaje de log al frontend."""
        if self._window:
            safe_msg = json.dumps(message)
            safe_tag = json.dumps(tag)
            try:
                self._window.evaluate_js(f"window.onPyLog && window.onPyLog({safe_msg}, {safe_tag});")
            except Exception:
                pass

    def get_initial_state(self, drive: str = "C:\\"):
        """Retorna el estado completo del sistema para inicializar la UI."""
        drives = cleaner.get_system_drives()
        stats = cleaner.get_system_stats(drive=drive)
        is_admin = cleaner.is_admin()
        config = cleaner.load_config()
        categories = cleaner.get_target_categories()
        locked_apps = cleaner.get_running_locked_apps()

        cat_list = []
        for key, info in categories.items():
            cat_list.append({
                "key": key,
                "name": info.get("name", key),
                "desc": info.get("desc", ""),
                "requires_admin": info.get("requires_admin", False),
                "is_recycle_bin": info.get("is_recycle_bin", False),
                "supports_age_filter": info.get("supports_age_filter", False)
            })

        return {
            "drives": drives,
            "stats": stats,
            "is_admin": is_admin,
            "config": config,
            "categories": cat_list,
            "locked_apps": locked_apps
        }

    def get_system_stats(self, drive: str = "C:\\"):
        """Actualiza las estadísticas de disco y RAM."""
        return {
            "stats": cleaner.get_system_stats(drive=drive),
            "drives": cleaner.get_system_drives()
        }

    def get_locked_apps(self):
        """Detecta aplicaciones en ejecución que interfieren con la limpieza de caché."""
        return cleaner.get_running_locked_apps()

    def scan_category(self, cat_key: str, min_age_hours: int = 24, exclusions: list = None):
        """Escanea una categoría específica y retorna sus resultados."""
        categories = cleaner.get_target_categories()
        cat_info = categories.get(cat_key)
        if not cat_info:
            return {"size": 0, "count": 0, "size_formatted": "0 B", "items": []}

        exclusions = exclusions or []
        size, count, items = cleaner.scan_category(
            cat_key, cat_info, min_age_hours=min_age_hours, exclusions=exclusions
        )
        return {
            "key": cat_key,
            "size": size,
            "count": count,
            "size_formatted": cleaner.format_size(size),
            "items": items[:100]  # Limitar a los 100 más pesados para rendimiento
        }

    def clean_category(self, cat_key: str, min_age_hours: int = 24, exclusions: list = None):
        """Limpia una categoría específica y retorna resultados."""
        categories = cleaner.get_target_categories()
        cat_info = categories.get(cat_key)
        if not cat_info:
            return {"freed": 0, "deleted": 0, "skipped": 0, "freed_formatted": "0 B"}

        exclusions = exclusions or []
        freed, deleted, skipped = cleaner.clean_category(
            cat_key, cat_info, min_age_hours=min_age_hours, exclusions=exclusions
        )
        return {
            "key": cat_key,
            "freed": freed,
            "deleted": deleted,
            "skipped": skipped,
            "freed_formatted": cleaner.format_size(freed)
        }

    def optimize_ram(self):
        """Optimiza memoria RAM reduciendo el conjunto de trabajo de procesos."""
        freed_procs = cleaner.optimize_ram()
        stats = cleaner.get_system_stats()
        return {
            "freed_processes": freed_procs,
            "stats": stats
        }

    def flush_dns(self):
        """Vacía la caché del cliente DNS de Windows."""
        success, msg = cleaner.flush_dns()
        return {
            "success": success,
            "message": msg
        }

    def get_startup_programs(self):
        """Obtiene la lista de programas de inicio automático."""
        return cleaner.get_startup_programs()

    def toggle_startup_program(self, prog_data: dict):
        """Habilita o deshabilita un programa de inicio."""
        success, msg = cleaner.toggle_startup_program(prog_data)
        return {
            "success": success,
            "message": msg
        }

    def save_config(self, cfg: dict):
        """Guarda la configuración en disco."""
        ok = cleaner.save_config(cfg)
        return {"success": ok}

    def request_admin(self):
        """Relanza el programa solicitando privilegios de administrador (UAC)."""
        cleaner.request_admin_elevation()
        return {"success": True}

    def shred_file(self, file_path: str, passes: int = 1):
        """Tritura un archivo de forma segura."""
        ok, msg = cleaner.shred_file(file_path, passes=passes)
        return {"success": ok, "message": msg}

    def find_duplicates(self, target_folder: str, min_size_kb: int = 1):
        """Busca archivos duplicados en la carpeta seleccionada."""
        min_bytes = max(512, int(min_size_kb) * 1024)
        duplicates = cleaner.find_duplicate_files(target_folder, min_size_bytes=min_bytes)
        return {"duplicates": duplicates}

    def export_report(self, report_data: dict, format_type: str = "json"):
        """Exporta un reporte de escaneo o limpieza al Escritorio o Descargas."""
        desktop = os.path.join(str(Path.home()), "Desktop")
        if not os.path.exists(desktop):
            desktop = os.path.join(str(Path.home()), "Descargas")
        if not os.path.exists(desktop):
            desktop = os.path.dirname(os.path.abspath(__file__))

        ext = "json" if format_type.lower() == "json" else "txt"
        filename = f"PyClean_Reporte_{int(cleaner.time.time())}.{ext}"
        filepath = os.path.join(desktop, filename)

        ok, msg = cleaner.export_report(report_data, filepath, format_type=format_type)
        return {"success": ok, "message": msg, "filepath": filepath}

    def pick_folder(self):
        """Abre un diálogo nativo para seleccionar una carpeta."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder = filedialog.askdirectory(title="Seleccionar carpeta")
            root.destroy()
            return {"folder": folder if folder else ""}
        except Exception:
            return {"folder": ""}

    def pick_file(self):
        """Abre un diálogo nativo para seleccionar un archivo."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            filepath = filedialog.askopenfilename(title="Seleccionar archivo para triturar")
            root.destroy()
            return {"file": filepath if filepath else ""}
        except Exception:
            return {"file": ""}

    def open_folder(self, path: str):
        """Abre la carpeta en el Explorador de Archivos de Windows de forma segura."""
        try:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                if sys.platform == "win32":
                    if os.path.isfile(abs_path):
                        subprocess.Popen(["explorer", f"/select,{abs_path}"])
                    else:
                        subprocess.Popen(["explorer", abs_path])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", "-R" if os.path.isfile(abs_path) else "", abs_path])
                else:
                    target_dir = os.path.dirname(abs_path) if os.path.isfile(abs_path) else abs_path
                    subprocess.Popen(["xdg-open", target_dir])
                return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Ruta no encontrada"}


def run_web_gui():
    """Lanza la interfaz moderna PyWebView + GSAP."""
    if webview is None:
        raise ImportError("pywebview no está instalado.")

    api = PyCleanAPI()
    web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
    index_file = os.path.join(web_dir, "index.html")

    window = webview.create_window(
        title="PyClean Pro v2.1 - Suite de Optimización, Limpieza y Privacidad",
        url=f"file:///{index_file.replace(os.sep, '/')}",
        js_api=api,
        width=1200,
        height=850,
        min_size=(980, 700),
        background_color="#0F111A"
    )
    api.set_window(window)
    webview.start(debug=False)


if __name__ == "__main__":
    run_web_gui()
