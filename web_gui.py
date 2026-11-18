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
import sys_monitor
import hardware_health
import context_menu
import vault

try:
    import webview
except ImportError:
    webview = None


class PyCleanAPI:
    def __init__(self):
        self._window = None
        self._is_busy = False
        self._vault = vault.PasswordVault()
        self._clipboard_timer = None

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

    # --- v2.2: Desinstalador Limpio de Aplicaciones ---
    def get_installed_apps(self):
        """Obtiene la lista de programas instalados."""
        return cleaner.get_installed_apps()

    def run_uninstaller(self, uninstall_cmd: str):
        """Ejecuta el desinstalador de una aplicación."""
        ok, msg = cleaner.run_uninstaller(uninstall_cmd)
        return {"success": ok, "message": msg}

    def find_app_leftovers(self, app_name: str):
        """Busca carpetas residuales huérfanas tras desinstalar."""
        leftovers = cleaner.find_app_leftovers(app_name)
        return {"leftovers": leftovers}

    def delete_leftovers(self, paths: list):
        """Elimina carpetas residuales huérfanas confirmadas."""
        deleted = []
        failed = []
        for p in paths:
            try:
                if os.path.exists(p) and os.path.isdir(p) and not cleaner.is_safe_link_or_junction(p):
                    cleaner.shutil.rmtree(p, ignore_errors=True)
                    deleted.append(p)
                else:
                    failed.append(p)
            except Exception:
                failed.append(p)
        return {"deleted": deleted, "failed": failed}

    # --- v2.2: Programador de Tareas Automático ---
    def get_scheduled_task_status(self):
        """Consulta el estado de la tarea programada."""
        return cleaner.get_scheduled_task_status()

    def set_scheduled_task(self, enabled: bool, frequency: str = "weekly"):
        """Configura la tarea programada en Windows."""
        ok, msg = cleaner.set_scheduled_task(enabled, frequency=frequency)
        return {"success": ok, "message": msg}

    # --- v2.2: Optimizador de Telemetría y Privacidad ---
    def get_telemetry_status(self):
        """Obtiene el estado de los servicios de telemetría."""
        return cleaner.get_telemetry_status()

    def toggle_telemetry(self, disable: bool):
        """Activa o mitiga la telemetría."""
        ok, msg = cleaner.toggle_telemetry(disable)
        return {"success": ok, "message": msg}

    # --- v2.2: Auditor de Descargas Antiguas ---
    def audit_old_downloads(self, days: int = 30):
        """Audita archivos pesados y antiguos en la carpeta de Descargas."""
        items = cleaner.audit_old_downloads(min_age_days=days)
        return {"downloads": items}

    def delete_download_file(self, file_path: str):
        """Elimina un archivo de descarga antiguo."""
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                os.remove(file_path)
                return {"success": True, "message": "Archivo de descarga eliminado."}
        except Exception as e:
            return {"success": False, "message": str(e)}
        return {"success": False, "message": "Archivo no encontrado."}

    # --- v2.3: Analizador de Almacenamiento, Particiones y Treemap ---
    def get_partitions_detailed(self):
        """Retorna información detallada de todas las particiones del sistema."""
        return cleaner.get_partitions_detailed()

    def scan_folder_treemap(self, target_path: str):
        """Escanea una carpeta o unidad para generar la jerarquía Treemap."""
        return cleaner.scan_folder_treemap(target_path)

    def find_largest_files(self, target_path: str, min_size_mb: int = 100, limit: int = 50):
        """Busca los archivos más pesados en la unidad o carpeta."""
        return cleaner.find_largest_files(target_path, min_size_mb=min_size_mb, limit=limit)

    def open_in_explorer(self, target_path: str):
        """Abre la carpeta o selecciona el archivo en el Explorador de Windows."""
        ok = cleaner.open_in_explorer(target_path)
        return {"success": ok}

    def delete_or_shred_file(self, file_path: str, shred: bool = False):
        """Elimina o tritura de forma segura un archivo pesado."""
        try:
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return {"success": False, "message": "El archivo especificado no existe."}

            if shred:
                ok, msg = cleaner.shred_file(file_path, passes=3)
                return {"success": ok, "message": msg}
            else:
                os.remove(file_path)
                return {"success": True, "message": "Archivo eliminado correctamente."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # --- v2.4: Monitor de Procesos y Red ---
    def get_top_processes(self, sort_by: str = "memory", limit: int = 35):
        return sys_monitor.get_top_processes(sort_by=sort_by, limit=limit)

    def terminate_process(self, pid: int):
        ok, msg = sys_monitor.terminate_process(pid)
        return {"success": ok, "message": msg}

    def get_network_interfaces(self):
        return sys_monitor.get_network_interfaces()

    def set_dns_preset(self, adapter_name: str, preset: str):
        ok, msg = sys_monitor.set_dns_preset(adapter_name, preset)
        return {"success": ok, "message": msg}

    def run_ping_test(self):
        return sys_monitor.run_ping_test()

    # --- v2.4: Salud de Hardware (SSD S.M.A.R.T., TRIM y Batería) ---
    def get_disk_health(self):
        return hardware_health.get_disk_health()

    def run_ssd_trim(self, drive_letter: str = "C"):
        ok, msg = hardware_health.run_ssd_trim(drive_letter)
        return {"success": ok, "message": msg}

    def get_battery_health(self):
        return hardware_health.get_battery_health()

    # --- v2.4: Gestor del Menú Contextual ---
    def get_context_menu_items(self):
        return context_menu.get_context_menu_items()

    def toggle_context_menu_item(self, hive: str, subkey: str, enable: bool):
        ok, msg = context_menu.toggle_context_menu_item(hive, subkey, enable)
        return {"success": ok, "message": msg}

    # --- v2.4: Bóveda Local de Contraseñas (AES-256-GCM) ---
    def vault_status(self):
        return self._vault.status()

    def vault_create(self, master_password: str):
        ok, msg = self._vault.create(master_password)
        return {"success": ok, "message": msg, "status": self._vault.status()}

    def vault_unlock(self, master_password: str):
        ok, msg = self._vault.unlock(master_password)
        return {"success": ok, "message": msg, "status": self._vault.status()}

    def vault_lock(self):
        self._vault.lock()
        return {"success": True, "status": self._vault.status()}

    def vault_get_entries(self):
        return {"unlocked": self._vault.is_unlocked(), "entries": self._vault.list_entries()}

    def vault_save_entry(
        self,
        title: str,
        username: str,
        password: str,
        url: str = "",
        category: str = "General",
        notes: str = "",
        entry_id: str = None,
    ):
        ok, result = self._vault.save_entry(
            title=title,
            username=username,
            password=password,
            url=url,
            category=category,
            notes=notes,
            entry_id=entry_id,
        )
        if ok:
            return {"success": True, "entry": result, "message": "Credencial guardada y cifrada."}
        return {"success": False, "message": str(result)}

    def vault_delete_entry(self, entry_id: str):
        ok, msg = self._vault.delete_entry(entry_id)
        return {"success": ok, "message": msg}

    def vault_generate_password(
        self,
        length: int = 18,
        use_upper: bool = True,
        use_lower: bool = True,
        use_digits: bool = True,
        use_symbols: bool = True,
    ):
        pwd = vault.generate_password(
            length=length,
            use_upper=use_upper,
            use_lower=use_lower,
            use_digits=use_digits,
            use_symbols=use_symbols,
        )
        return {"password": pwd, "strength": vault.evaluate_password_strength(pwd)}

    def vault_evaluate_strength(self, password: str):
        return vault.evaluate_password_strength(password)

    def _set_system_clipboard(self, text: str) -> bool:
        try:
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(["clip"], input=text.encode("utf-16le"), check=True, startupinfo=si)
                return True
            elif sys.platform == "darwin":
                subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
                return True
        except Exception:
            pass
        return False

    def vault_copy_secret(self, secret_text: str, clear_after_seconds: int = 30):
        """Copia un secreto al portapapeles del sistema y lo limpia automáticamente tras N segundos."""
        copied = self._set_system_clipboard(secret_text or "")
        if self._clipboard_timer:
            try:
                self._clipboard_timer.cancel()
            except Exception:
                pass
        if copied and clear_after_seconds > 0:
            self._clipboard_timer = threading.Timer(clear_after_seconds, self._set_system_clipboard, args=[""])
            self._clipboard_timer.daemon = True
            self._clipboard_timer.start()
        return {"success": copied, "clear_after": clear_after_seconds}

    def vault_export_backup(self):
        if not self._window or not webview:
            return {"success": False, "message": "Diálogo no disponible."}
        dest = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename="pyclean_vault_backup.vault",
            file_types=("Bóveda Cifrada (*.vault)", "Todos (*.*)"),
        )
        if not dest:
            return {"success": False, "message": "Exportación cancelada."}
        target = dest[0] if isinstance(dest, (list, tuple)) else dest
        ok, msg = self._vault.export_encrypted_backup(target)
        return {"success": ok, "message": msg}

    def vault_import_backup(self):
        if not self._window or not webview:
            return {"success": False, "message": "Diálogo no disponible."}
        src = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("Bóveda Cifrada (*.vault;*.enc)", "Todos (*.*)"),
        )
        if not src:
            return {"success": False, "message": "Importación cancelada."}
        target = src[0] if isinstance(src, (list, tuple)) else src
        ok, msg = self._vault.import_encrypted_backup(target)
        return {"success": ok, "message": msg, "status": self._vault.status()}


def run_web_gui():
    """Lanza la interfaz moderna PyWebView + GSAP."""
    if webview is None:
        raise ImportError("pywebview no está instalado.")

    api = PyCleanAPI()
    web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
    index_file = os.path.join(web_dir, "index.html")

    window = webview.create_window(
        title="PyClean Pro v2.4 - Suite de Optimización, Hardware y Privacidad",
        url=f"file:///{index_file.replace(os.sep, '/')}",
        js_api=api,
        width=1240,
        height=860,
        min_size=(980, 700),
        background_color="#0F111A"
    )
    api.set_window(window)
    webview.start(debug=False)


if __name__ == "__main__":
    run_web_gui()
