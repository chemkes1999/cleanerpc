"""
PyClean Pro - Interfaz Gráfica Web Moderna (PyWebView + GSAP)
Provee la API de comunicación entre el frontend Web (HTML/CSS/JS + GSAP)
y el motor de limpieza en Python (cleaner.py).
"""

import os
import sys
import threading
import subprocess
import json
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
            "categories": cat_list
        }

    def get_system_stats(self, drive: str = "C:\\"):
        """Actualiza las estadísticas de disco y RAM."""
        return {
            "stats": cleaner.get_system_stats(drive=drive),
            "drives": cleaner.get_system_drives()
        }

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

    def pick_folder(self):
        """Abre un diálogo nativo para seleccionar una carpeta para exclusión."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder = filedialog.askdirectory(title="Seleccionar carpeta a excluir")
            root.destroy()
            return {"folder": folder if folder else ""}
        except Exception:
            return {"folder": ""}

    def open_folder(self, path: str):
        """Abre la carpeta en el Explorador de Archivos de Windows."""
        try:
            if os.path.exists(path):
                if os.path.isfile(path):
                    subprocess.Popen(f'explorer /select,"{os.path.abspath(path)}"')
                else:
                    os.startfile(os.path.abspath(path))
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
        title="PyClean Pro v2.0 - Suite de Optimización y Limpieza",
        url=f"file:///{index_file.replace(os.sep, '/')}",
        js_api=api,
        width=1180,
        height=820,
        min_size=(960, 680),
        background_color="#0F111A"
    )
    api.set_window(window)
    webview.start(debug=False)


if __name__ == "__main__":
    run_web_gui()
