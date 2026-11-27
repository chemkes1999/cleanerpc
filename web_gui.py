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
import socket
import http.server
import urllib.parse
import secrets
import base64
import time
from pathlib import Path

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None

import cleaner
import sys_monitor
import hardware_health
import context_menu
import vault
import sys_optimizer

try:
    import webview
except ImportError:
    webview = None


def get_lan_ip() -> str:
    """Detecta la dirección IP en la red local (LAN) usando una sonda UDP sin tráfico real."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except Exception:
            s.connect(("8.8.8.8", 1))
            ip = s.getsockname()[0]
        finally:
            s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "127.0.0.1"


class _RunningStatus:
    def __init__(self, check_fn):
        self._check_fn = check_fn

    def __call__(self) -> bool:
        return self._check_fn()

    def __bool__(self) -> bool:
        return self._check_fn()

    def __eq__(self, other) -> bool:
        return self._check_fn() == other


class _SyncThreadingHTTPServer(http.server.ThreadingHTTPServer):
    request_queue_size = 128
    daemon_threads = True
    allow_reuse_address = True


class VaultSyncServer:
    """
    Servidor HTTP en segundo plano (LAN) para sincronización segura Zero-Knowledge
    con la aplicación web móvil compañera (PWA) de PyClean Pro.
    """

    def __init__(
        self,
        vault_instance: vault.PasswordVault,
        host: str = "0.0.0.0",
        port: int = 8765,
        default_port: int | None = None,
        token_ttl: int = 300,
    ):
        self.vault = vault_instance
        self.host = host
        self.port = default_port if default_port is not None else port
        self.default_port = self.port
        self.token_ttl = token_ttl
        self.server: http.server.ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.token: str | None = None
        self.token_created_at: float = 0.0
        self.token_expires_at: float = 0.0
        self.clients_connected: int = 0
        self.last_sync: int = 0
        self._lock = threading.RLock()

    def _check_running(self) -> bool:
        with self._lock:
            return self.server is not None and self.thread is not None and self.thread.is_alive()

    @property
    def is_running(self) -> bool:
        return self._check_running()

    def get_is_running(self) -> bool:
        return self._check_running()

    def generate_pairing_token(self, ttl_seconds: int = 300) -> str:
        with self._lock:
            self.token = secrets.token_urlsafe(24)
            self.token_created_at = time.time()
            self.token_ttl = ttl_seconds
            self.token_expires_at = self.token_created_at + ttl_seconds
            return self.token

    def is_token_valid(self, candidate_token: str) -> bool:
        with self._lock:
            if not self.token or not candidate_token:
                return False
            now = time.time()
            if self.token_expires_at > 0 and now > self.token_expires_at:
                return False
            if (now - self.token_created_at) > self.token_ttl:
                return False
            return secrets.compare_digest(self.token, candidate_token)

    def start(self, port: int | None = None) -> dict:
        with self._lock:
            if self.server is not None and self.thread is not None and self.thread.is_alive():
                ip = get_lan_ip()
                return {
                    "status": "ok",
                    "running": True,
                    "url": f"http://{ip}:{self.port}/mobile/?token={self.token}",
                    "token": self.token,
                    "ip": ip,
                    "port": self.port,
                }

            target_port = self.port if port is None else port
            if not self.token:
                self.generate_pairing_token(ttl_seconds=self.token_ttl)
            handler_factory = self._build_handler()

            try:
                self.server = _SyncThreadingHTTPServer((self.host, target_port), handler_factory)
                self.port = self.server.server_address[1]
            except OSError:
                self.server = _SyncThreadingHTTPServer((self.host, 0), handler_factory)
                self.port = self.server.server_address[1]

            self.server.daemon_threads = True
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()

            ip = get_lan_ip()
            return {
                "status": "ok",
                "running": True,
                "url": f"http://{ip}:{self.port}/mobile/?token={self.token}",
                "token": self.token,
                "ip": ip,
                "port": self.port,
            }

    def stop(self) -> dict:
        with self._lock:
            if self.server:
                try:
                    self.server.shutdown()
                    self.server.server_close()
                except Exception:
                    pass
                self.server = None
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=1.0)
                self.thread = None
            self.token = None
            return {"status": "ok", "running": False}

    def get_status(self) -> dict:
        with self._lock:
            running = self.server is not None and self.thread is not None and self.thread.is_alive()
            return {
                "running": running,
                "clients_connected": self.clients_connected,
                "last_sync": self.last_sync,
                "port": self.port if running else 0,
                "ip": get_lan_ip() if running else "",
            }

    def _build_handler(self):
        sync_server = self

        class SyncHTTPHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def _send_cors_headers(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

            def _send_json(self, status_code: int, data: dict):
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(body)
                try:
                    self.wfile.flush()
                except Exception:
                    pass
                self.close_connection = True

            def do_OPTIONS(self):
                self.send_response(200)
                self._send_cors_headers()
                self.end_headers()

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                req_path = parsed.path
                params = urllib.parse.parse_qs(parsed.query)
                token = params.get("token", [""])[0]

                # Rutas estáticas móviles: /mobile/* o /
                if req_path == "/" or req_path.startswith("/mobile"):
                    self._serve_mobile(req_path)
                    return

                # Endpoints de API protegidos con token
                if not sync_server.is_token_valid(token):
                    self._send_json(401, {"status": "error", "message": "Unauthorized: invalid or expired pairing token"})
                    return

                if req_path == "/api/sync/info":
                    if not sync_server.vault.exists():
                        self._send_json(404, {"status": "error", "message": "Bóveda no encontrada."})
                        return
                    try:
                        container = sync_server.vault.export_vault_sync_payload()
                        with sync_server._lock:
                            sync_server.clients_connected += 1
                        self._send_json(200, {
                            "status": "ok",
                            "vault_name": "PyClean Pro",
                            "version": container.get("version", 1),
                            "kdf": container.get("kdf", "pbkdf2-sha256"),
                            "iterations": container.get("iterations", 600000),
                            "salt": container.get("salt", ""),
                        })
                    except Exception as e:
                        self._send_json(500, {"status": "error", "message": str(e)})
                    return

                if req_path == "/api/sync/vault":
                    if not sync_server.vault.exists():
                        self._send_json(404, {"status": "error", "message": "Bóveda no encontrada."})
                        return
                    try:
                        container = sync_server.vault.export_vault_sync_payload()
                        with sync_server._lock:
                            sync_server.clients_connected += 1
                        data = dict(container)
                        data["status"] = "ok"
                        self._send_json(200, data)
                    except Exception as e:
                        self._send_json(500, {"status": "error", "message": str(e)})
                    return

                self._send_json(404, {"status": "error", "message": "Endpoint no encontrado"})

            def do_POST(self):
                parsed = urllib.parse.urlparse(self.path)
                req_path = parsed.path
                params = urllib.parse.parse_qs(parsed.query)
                token = params.get("token", [""])[0]

                if not sync_server.is_token_valid(token):
                    self._send_json(401, {"status": "error", "message": "Unauthorized: invalid or expired pairing token"})
                    return

                if req_path == "/api/sync/vault":
                    try:
                        content_len = int(self.headers.get("Content-Length", 0))
                        raw_body = self.rfile.read(content_len)
                        payload = json.loads(raw_body.decode("utf-8"))
                    except Exception as e:
                        self._send_json(400, {"status": "error", "message": f"JSON inválido: {e}"})
                        return

                    if not isinstance(payload, dict):
                        self._send_json(400, {"status": "error", "message": "JSON body must be an object."})
                        return

                    # Caso A: Array de credenciales descifradas ("entries")
                    if "entries" in payload:
                        try:
                            if not sync_server.vault.is_unlocked():
                                self._send_json(400, {
                                    "status": "error",
                                    "message": "La bóveda en el PC debe estar desbloqueada para fusionar credenciales.",
                                })
                                return
                            with sync_server.vault._lock:
                                merged, total = sync_server.vault.merge_entries(payload["entries"])
                            with sync_server._lock:
                                sync_server.last_sync = int(time.time())
                                sync_server.clients_connected += 1
                            self._send_json(200, {"status": "ok", "merged": merged, "total": total})
                        except Exception as e:
                            self._send_json(500, {"status": "error", "message": str(e)})
                        return

                    # Caso B: Contenedor cifrado entrante ("ciphertext", etc.)
                    envelope = payload.get("vault") if "vault" in payload else payload
                    if "ciphertext" in envelope and "nonce" in envelope:
                        if not sync_server.vault.is_unlocked():
                            self._send_json(400, {
                                "status": "error",
                                "message": "La bóveda en el PC debe estar desbloqueada para procesar el contenedor cifrado.",
                            })
                            return
                        try:
                            incoming_salt = base64.b64decode(envelope["salt"])
                            incoming_nonce = base64.b64decode(envelope["nonce"])
                            incoming_ct = base64.b64decode(envelope["ciphertext"])

                            with sync_server.vault._lock:
                                if incoming_salt == sync_server.vault._salt and sync_server.vault._key:
                                    if AESGCM is None:
                                        self._send_json(500, {"status": "error", "message": "AESGCM no disponible"})
                                        return
                                    aesgcm = AESGCM(sync_server.vault._key)
                                    pt = aesgcm.decrypt(incoming_nonce, incoming_ct, vault.VAULT_AAD)
                                    inc_dict = json.loads(pt.decode("utf-8"))
                                    merged, total = sync_server.vault.merge_entries(inc_dict.get("entries", []))
                                else:
                                    self._send_json(400, {
                                        "status": "error",
                                        "message": "El salt del contenedor entrante no coincide con la bóveda local.",
                                    })
                                    return
                            with sync_server._lock:
                                sync_server.last_sync = int(time.time())
                                sync_server.clients_connected += 1
                            self._send_json(200, {"status": "ok", "merged": merged, "total": total})
                            return
                        except Exception as e:
                            self._send_json(400, {"status": "error", "message": f"Error descifrando contenedor: {e}"})
                            return

                    self._send_json(400, {"status": "error", "message": "Payload no reconocido (se requiere 'entries' o 'ciphertext')."})
                    return

                self._send_json(404, {"status": "error", "message": "Endpoint no encontrado"})

            def _serve_mobile(self, req_path: str):
                rel = req_path.lstrip("/")
                if rel.startswith("mobile"):
                    rel = rel[len("mobile"):].lstrip("/")
                if not rel or rel == "/":
                    rel = "index.html"

                base_dir = Path(__file__).resolve().parent / "web" / "mobile"
                target = (base_dir / rel).resolve()

                try:
                    target.relative_to(base_dir)
                except ValueError:
                    self._send_json(403, {"status": "error", "message": "Acceso denegado"})
                    return

                if target.is_file():
                    ext = target.suffix.lower()
                    mime_types = {
                        ".html": "text/html; charset=utf-8",
                        ".js": "application/javascript; charset=utf-8",
                        ".css": "text/css; charset=utf-8",
                        ".json": "application/json; charset=utf-8",
                        ".webmanifest": "application/manifest+json; charset=utf-8",
                        ".svg": "image/svg+xml",
                        ".png": "image/png",
                        ".jpg": "image/jpeg",
                        ".ico": "image/x-icon",
                    }
                    ctype = mime_types.get(ext, "application/octet-stream")
                    try:
                        content = target.read_bytes()
                        self.send_response(200)
                        self.send_header("Content-Type", ctype)
                        self.send_header("Content-Length", str(len(content)))
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(content)
                        return
                    except Exception:
                        pass

                placeholder = (
                    "<!DOCTYPE html>\n"
                    "<html lang='es'>\n"
                    "<head><meta charset='utf-8'><title>PyClean Pro Mobile Companion</title></head>\n"
                    "<body style='font-family:system-ui,sans-serif;background:#0F111A;color:#F8FAFC;padding:2rem;'>\n"
                    "<h2>📱 PyClean Pro Companion</h2>\n"
                    "<p>El servidor de sincronización está activo y listo para transferir credenciales.</p>\n"
                    "</body></html>"
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(placeholder)))
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(placeholder)

        return SyncHTTPHandler


class PyCleanAPI:
    def __init__(self):
        self._window = None
        self._is_busy = False
        self._vault = vault.PasswordVault()
        self._clipboard_timer = None
        self._sync_server = VaultSyncServer(self._vault)

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

    def run_battery_energy_audit(self, duration_sec: int = 10):
        return hardware_health.run_battery_energy_audit(duration_sec)

    def optimize_battery_performance(self, profile: str = "autonomy"):
        return hardware_health.optimize_battery_performance(profile)

    def restore_battery_power_backup(self):
        return hardware_health.restore_battery_power_backup()

    def repair_battery_driver(self):
        return hardware_health.repair_battery_driver()

    def start_battery_calibration(self):
        return hardware_health.start_battery_calibration()

    def finish_battery_calibration(self):
        return hardware_health.finish_battery_calibration()

    def export_battery_report_html(self):
        return hardware_health.export_battery_report_html()

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

    def vault_get_qr_payload(self, entry_id: str, use_pin: bool = False, pin: str = ""):
        try:
            if use_pin and not pin:
                pin = f"{secrets.randbelow(900000) + 100000:06d}"
            payload = self._vault.generate_credential_qr_payload(entry_id, use_pin=use_pin, pin=pin)
            return {"status": "ok", "payload": payload, "pin": pin}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def vault_start_mobile_sync(self, port: int = 8765):
        try:
            self._sync_server.vault = self._vault
            res = self._sync_server.start(port=port)
            token = res["token"]
            ip = res["ip"]
            assigned_port = res["port"]
            qr_payload = json.dumps({
                "v": 1,
                "type": "pair",
                "url": f"http://{ip}:{assigned_port}",
                "token": token,
                "ip": ip,
                "port": assigned_port,
            }, separators=(",", ":"))
            return {
                "status": "ok",
                "url": res["url"],
                "token": token,
                "qr_payload": qr_payload,
                "ip": ip,
                "port": assigned_port,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def vault_stop_mobile_sync(self):
        try:
            self._sync_server.stop()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def vault_get_mobile_sync_status(self):
        try:
            return self._sync_server.get_status()
        except Exception as e:
            return {"running": False, "clients_connected": 0, "last_sync": 0, "error": str(e)}

    # System Optimization & Deep Cleaner API
    def clean_dism(self, reset_base: bool = False):
        """Ejecuta la limpieza del almacén de componentes DISM WinSxS."""
        try:
            return cleaner.run_dism_component_cleanup(reset_base=reset_base)
        except Exception as e:
            return {"success": False, "output": "", "reset_base": reset_base, "error": str(e)}

    def clean_vss_shadows(self):
        """Purga las instantáneas de restauración VSS más antiguas."""
        try:
            return cleaner.clean_vss_old_shadows()
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    def prune_docker(self):
        """Ejecuta docker system prune -f."""
        try:
            return cleaner.clean_docker_system()
        except Exception as e:
            return {"success": False, "output": "", "space_reclaimed": "0 B", "error": str(e)}

    def scan_stale_node_modules(self, path: str = "", inactive_days: int = 90):
        """Escanea proyectos en busca de carpetas node_modules inactivas."""
        try:
            return cleaner.find_stale_node_modules(root_dir=path, inactive_days=inactive_days)
        except Exception as e:
            return []

    def delete_selected_node_modules(self, paths: list):
        """Elimina las carpetas node_modules seleccionadas de forma segura."""
        try:
            return cleaner.delete_selected_node_modules(paths=paths)
        except Exception as e:
            return {
                "success": False,
                "deleted_count": 0,
                "freed_bytes": 0,
                "freed_formatted": "0 B",
                "errors": [str(e)]
            }

    def set_ultimate_performance(self):
        """Desbloquea y activa el plan de energía Ultimate Performance."""
        try:
            return sys_optimizer.unlock_ultimate_performance_plan()
        except Exception as e:
            return {"success": False, "message": str(e), "guid": ""}

    def optimize_tcp_stack(self, enable_autotuning: bool = True):
        """Ajusta y optimiza los parámetros TCP/IP del sistema."""
        try:
            return sys_optimizer.tune_tcp_network(enable_autotuning=enable_autotuning)
        except Exception as e:
            return {"success": False, "message": str(e), "autotuning": ""}

    def repair_search_indexer(self):
        """Restablece y reindexa el servicio de búsqueda de Windows."""
        try:
            return sys_optimizer.reindex_windows_search()
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_compact_os_status(self):
        """Consulta el estado actual de compresión Compact OS."""
        try:
            return sys_optimizer.get_compact_os_status()
        except Exception as e:
            return {"success": False, "is_compact": False, "raw_output": str(e)}

    def toggle_compact_os(self, enable: bool):
        """Activa o desactiva la compresión del sistema Compact OS."""
        try:
            return sys_optimizer.toggle_compact_os(enable=enable)
        except Exception as e:
            return {"success": False, "is_compact": False, "message": str(e)}


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
