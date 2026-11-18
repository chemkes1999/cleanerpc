"""
PyClean Pro v2.1 - Motor de Limpieza, Seguridad y Optimización para Windows
Módulo seguro de escaneo, eliminación de temporales, triturador seguro,
buscador de duplicados, auditor de bloqueos y optimización del sistema.
"""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
import ctypes
import hashlib
import glob
import time
import json
import logging
from pathlib import Path

# Configurar logger local
logger = logging.getLogger("pyclean")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Importaciones condicionales para Windows (permitiendo ejecución multiplataforma y tests)
try:
    from ctypes import wintypes
except (ImportError, ValueError):
    wintypes = None

try:
    import winreg
except ImportError:
    winreg = None

# Ruta de archivo de configuración local
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cleaner_config.json")

# Definición de estructuras ctypes para memoria en Windows
if wintypes:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ('dwLength', wintypes.DWORD),
            ('dwMemoryLoad', wintypes.DWORD),
            ('ullTotalPhys', ctypes.c_ulonglong),
            ('ullAvailPhys', ctypes.c_ulonglong),
            ('ullTotalPageFile', ctypes.c_ulonglong),
            ('ullAvailPageFile', ctypes.c_ulonglong),
            ('ullTotalVirtual', ctypes.c_ulonglong),
            ('ullAvailVirtual', ctypes.c_ulonglong),
            ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
        ]
else:
    MEMORYSTATUSEX = None


# Mapeo de procesos que bloquean la limpieza de caché
LOCKED_APPS_MAP = {
    "Google Chrome": ["chrome.exe"],
    "Microsoft Edge": ["msedge.exe"],
    "Brave Browser": ["brave.exe"],
    "Mozilla Firefox": ["firefox.exe"],
    "Opera / Opera GX": ["opera.exe", "opera_gx.exe"],
    "Vivaldi": ["vivaldi.exe"],
    "Discord": ["Discord.exe"],
    "Spotify": ["Spotify.exe"],
    "Visual Studio Code": ["Code.exe"],
}


def load_config() -> dict:
    """Carga la configuración de usuario (exclusiones, antigüedad mínima, etc.)."""
    default_cfg = {
        "min_age_hours": 24,       # Por seguridad: ignorar temporales creados hace menos de 24h
        "exclusions": [],           # Rutas o patrones a omitir siempre
        "auto_ram_on_clean": False
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_cfg.update(data)
        except Exception as e:
            logger.warning("Error leyendo cleaner_config.json: %s", e)
    return default_cfg


def save_config(cfg: dict) -> bool:
    """Guarda la configuración persistente en disco."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error("Error guardando cleaner_config.json: %s", e)
        return False


def is_admin() -> bool:
    """Verifica si el script se está ejecutando con privilegios de Administrador."""
    if sys.platform != "win32" or not hasattr(ctypes, "windll"):
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def request_admin_elevation():
    """Relanza la aplicación actual solicitando elevación de Administrador (UAC)."""
    if sys.platform != "win32" or not hasattr(ctypes, "windll"):
        return False, "La elevación UAC sólo está disponible en Windows."
    try:
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        sys.exit(0)
    except Exception as e:
        return False, str(e)


def format_size(size_bytes: int | float) -> str:
    """Convierte un tamaño en bytes a formato legible (B, KB, MB, GB, TB)."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"


def is_safe_link_or_junction(path: str) -> bool:
    """
    Verifica si una ruta es un enlace simbólico o un punto de unión (Directory Junction) en Windows.
    Previene atravesar o borrar carpetas redirigidas que apunten a datos personales o externos.
    """
    try:
        if os.path.islink(path):
            return True
        if hasattr(os.path, "isjunction") and os.path.isjunction(path):
            return True
    except (OSError, ValueError):
        return True  # Por seguridad, si falla la inspección se trata como inseguro
    return False


def get_running_locked_apps() -> list[dict]:
    """
    Detecta aplicaciones comunes en ejecución que mantienen bloqueados archivos de caché.
    Retorna lista de diccionarios: [{'name': 'Google Chrome', 'process': 'chrome.exe'}, ...]
    """
    running = []
    if sys.platform != "win32":
        return running

    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        res = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            check=False,
            encoding="utf-8",
            errors="ignore"
        )
        if res.returncode == 0:
            active_exes = set()
            for line in res.stdout.splitlines():
                if line.strip():
                    parts = line.split('","')
                    if parts:
                        exe = parts[0].strip('"').lower()
                        active_exes.add(exe)

            for app_name, exes in LOCKED_APPS_MAP.items():
                for exe in exes:
                    if exe.lower() in active_exes:
                        running.append({"name": app_name, "process": exe})
                        break
    except Exception as e:
        logger.debug("Error detectando procesos bloqueados: %s", e)

    return running


def get_system_drives() -> list[dict]:
    """
    Detecta todas las unidades fijas y extraíbles del sistema con su espacio.
    Retorna lista de diccionarios: [{'letter': 'C:\\', 'type': 'fixed', ...}]
    """
    drives = []
    if sys.platform == "win32" and hasattr(ctypes, "windll"):
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter_idx in range(26):
                if bitmask & (1 << letter_idx):
                    drive_letter = f"{chr(65 + letter_idx)}:\\"
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_letter)
                    # DRIVE_REMOVABLE = 2, DRIVE_FIXED = 3
                    if drive_type in (2, 3):
                        try:
                            total, used, free = shutil.disk_usage(drive_letter)
                            pct = round((used / total) * 100, 1) if total > 0 else 0.0
                            drives.append({
                                "letter": drive_letter,
                                "type": "Fijo" if drive_type == 3 else "Extraíble",
                                "total": total,
                                "used": used,
                                "free": free,
                                "percent": pct
                            })
                        except Exception:
                            pass
        except Exception:
            pass

    if not drives:
        root_path = "C:\\" if sys.platform == "win32" else "/"
        try:
            total, used, free = shutil.disk_usage(root_path)
            drives.append({
                "letter": root_path,
                "type": "Fijo",
                "total": total,
                "used": used,
                "free": free,
                "percent": round((used / total) * 100, 1) if total > 0 else 0.0
            })
        except Exception:
            pass

    return drives


def get_system_stats(drive: str = "C:\\") -> dict:
    """Obtiene estadísticas de uso de disco y memoria RAM del sistema."""
    stats = {
        "drive": drive,
        "disk_total": 0,
        "disk_used": 0,
        "disk_free": 0,
        "disk_percent": 0.0,
        "ram_load": 0,
        "ram_total": 0,
        "ram_avail": 0,
        "ram_used": 0,
    }
    try:
        target_drive = drive if os.path.exists(drive) else ("C:\\" if sys.platform == "win32" else "/")
        total, used, free = shutil.disk_usage(target_drive)
        stats["disk_total"] = total
        stats["disk_used"] = used
        stats["disk_free"] = free
        stats["disk_percent"] = round((used / total) * 100, 1) if total > 0 else 0.0
    except Exception:
        pass

    if sys.platform == "win32" and hasattr(ctypes, "windll") and MEMORYSTATUSEX:
        try:
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
                stats["ram_load"] = mem.dwMemoryLoad
                stats["ram_total"] = mem.ullTotalPhys
                stats["ram_avail"] = mem.ullAvailPhys
                stats["ram_used"] = mem.ullTotalPhys - mem.ullAvailPhys
        except Exception:
            pass

    return stats


def _get_chromium_cache_paths(user_data_path: str) -> list[str]:
    """Resuelve rutas de caché para todos los perfiles de Chromium (Default, Profile 1, etc.)."""
    paths = []
    if not os.path.isdir(user_data_path):
        return paths

    shader = os.path.join(user_data_path, "ShaderCache")
    if os.path.exists(shader):
        paths.append(shader)

    try:
        for entry in os.listdir(user_data_path):
            full_entry = os.path.join(user_data_path, entry)
            if os.path.isdir(full_entry) and (
                entry == "Default" or entry.startswith("Profile ") or entry == "Guest Profile"
            ):
                for sub in ["Cache", "Code Cache", "GPUCache"]:
                    c_path = os.path.join(full_entry, sub)
                    if os.path.exists(c_path):
                        paths.append(c_path)
    except Exception:
        pass

    return paths


def get_target_categories() -> dict:
    """
    Define y resuelve las rutas seguras para limpieza en el sistema del usuario actual.
    Incluye multi-perfil, herramientas de desarrollo y soporte ampliado.
    """
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")
    user_temp = os.environ.get("TEMP", os.path.join(local_app_data, "Temp") if local_app_data else "")
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    user_home = str(Path.home())

    # Chromium multi-profile paths
    chrome_paths = _get_chromium_cache_paths(os.path.join(local_app_data, r"Google\Chrome\User Data"))
    edge_paths = _get_chromium_cache_paths(os.path.join(local_app_data, r"Microsoft\Edge\User Data"))
    brave_paths = _get_chromium_cache_paths(os.path.join(local_app_data, r"BraveSoftware\Brave-Browser\User Data"))
    vivaldi_paths = _get_chromium_cache_paths(os.path.join(local_app_data, r"Vivaldi\User Data"))

    # Opera / Opera GX paths
    opera_paths = []
    for op in [r"Opera Software\Opera Stable", r"Opera Software\Opera GX Stable"]:
        base_op = os.path.join(app_data, op)
        if os.path.exists(base_op):
            opera_paths.extend(_get_chromium_cache_paths(base_op))

    # Firefox profiles
    firefox_paths = glob.glob(os.path.join(local_app_data, r"Mozilla\Firefox\Profiles\*\cache2"))

    # Development & Apps
    vscode_paths = [
        os.path.join(app_data, r"Code\Cache"),
        os.path.join(app_data, r"Code\CachedData"),
        os.path.join(app_data, r"Code\CachedExtensionVSIXs"),
    ]
    discord_paths = [
        os.path.join(app_data, r"discord\Cache"),
        os.path.join(app_data, r"discord\Code Cache"),
        os.path.join(app_data, r"discord\GPUCache"),
    ]
    spotify_paths = [
        os.path.join(local_app_data, r"Spotify\Storage")
    ]

    # Caches de desarrollo (Pip, NPM, PNPM, Yarn, Cargo)
    dev_paths = [
        os.path.join(local_app_data, r"pip\cache"),
        os.path.join(app_data, r"npm-cache"),
        os.path.join(local_app_data, r"pnpm\store"),
        os.path.join(local_app_data, r"Yarn\Cache"),
        os.path.join(user_home, r".cargo\registry\cache")
    ]

    # Componentes Web de Windows (INetCache)
    inet_paths = [
        os.path.join(local_app_data, r"Microsoft\Windows\INetCache")
    ]

    categories = {
        "user_temp": {
            "name": "Temporales de Usuario",
            "desc": "Archivos residuales en %TEMP% y carpetas temporales de aplicaciones",
            "requires_admin": False,
            "paths": [user_temp] if user_temp else [],
            "is_recycle_bin": False,
            "supports_age_filter": True
        },
        "system_temp": {
            "name": "Temporales de Windows",
            "desc": "Archivos temporales del sistema en C:\\Windows\\Temp",
            "requires_admin": True,
            "paths": [os.path.join(system_root, "Temp")],
            "is_recycle_bin": False,
            "supports_age_filter": True
        },
        "recycle_bin": {
            "name": "Papelera de Reciclaje",
            "desc": "Archivos eliminados que aún ocupan espacio en el disco",
            "requires_admin": False,
            "paths": [],
            "is_recycle_bin": True,
            "supports_age_filter": False
        },
        "browser_chrome": {
            "name": "Caché de Google Chrome (Todos los perfiles)",
            "desc": "Archivos temporales de navegación y caché multimedia de Chrome",
            "requires_admin": False,
            "paths": chrome_paths,
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "browser_edge": {
            "name": "Caché de Microsoft Edge (Todos los perfiles)",
            "desc": "Caché web y sombreadores de Microsoft Edge",
            "requires_admin": False,
            "paths": edge_paths,
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "browser_brave": {
            "name": "Caché de Brave Browser",
            "desc": "Caché temporal de navegación de Brave",
            "requires_admin": False,
            "paths": brave_paths,
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "browser_firefox": {
            "name": "Caché de Mozilla Firefox",
            "desc": "Caché de todos los perfiles de Firefox",
            "requires_admin": False,
            "paths": firefox_paths,
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "browser_opera": {
            "name": "Caché de Opera / Opera GX",
            "desc": "Caché y datos temporales de navegación de Opera y Opera GX",
            "requires_admin": False,
            "paths": opera_paths,
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "browser_vivaldi": {
            "name": "Caché de Vivaldi",
            "desc": "Caché temporal de navegación de Vivaldi Browser",
            "requires_admin": False,
            "paths": vivaldi_paths,
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "dev_tools": {
            "name": "Caché de Desarrollo (Pip, Node, Yarn, Cargo)",
            "desc": "Caché de paquetes y compilaciones descargadas por Pip, NPM, PNPM, Yarn y Cargo",
            "requires_admin": False,
            "paths": dev_paths,
            "is_recycle_bin": False,
            "supports_age_filter": True
        },
        "app_discord": {
            "name": "Caché de Discord",
            "desc": "Imágenes, gifs y datos en caché de la aplicación Discord",
            "requires_admin": False,
            "paths": discord_paths,
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "app_spotify": {
            "name": "Caché de Spotify",
            "desc": "Caché local de canciones e imágenes descargadas por Spotify",
            "requires_admin": False,
            "paths": spotify_paths,
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "app_vscode": {
            "name": "Caché de Visual Studio Code",
            "desc": "Caché de datos y extensiones de VS Code",
            "requires_admin": False,
            "paths": vscode_paths,
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "windows_inet_cache": {
            "name": "Caché Web de Windows (INetCache)",
            "desc": "Archivos web temporales y caché del sistema de Windows",
            "requires_admin": False,
            "paths": inet_paths,
            "is_recycle_bin": False,
            "supports_age_filter": True
        },
        "crash_dumps": {
            "name": "Volcados de Error y WER",
            "desc": "Reportes de bloqueo y volcados de memoria por caídas de software",
            "requires_admin": False,
            "paths": [
                os.path.join(local_app_data, "CrashDumps"),
                os.path.join(local_app_data, r"Microsoft\Windows\WER\ReportArchive"),
                os.path.join(local_app_data, r"Microsoft\Windows\WER\ReportQueue"),
            ] if local_app_data else [],
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "thumbnail_cache": {
            "name": "Caché de Miniaturas",
            "desc": "Miniaturas obsoletas del explorador de Windows (.db/.tmp)",
            "requires_admin": False,
            "paths": [
                os.path.join(local_app_data, r"Microsoft\Windows\Explorer")
            ] if local_app_data else [],
            "filter_patterns": ["thumbcache_*.db", "iconcache_*.db"],
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "windows_update_cache": {
            "name": "Caché de Windows Update",
            "desc": "Paquetes de instalación descargados de actualizaciones pasadas",
            "requires_admin": True,
            "paths": [os.path.join(system_root, r"SoftwareDistribution\Download")],
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "windows_delivery_opt": {
            "name": "Optimización de Distribución Windows",
            "desc": "Archivos compartidos y descargados de Delivery Optimization",
            "requires_admin": True,
            "paths": [os.path.join(system_root, r"SoftwareDistribution\DeliveryOptimization")],
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "windows_logs": {
            "name": "Archivos de Registro (Logs de Windows)",
            "desc": "Logs antiguos generados por el sistema y componentes CBS",
            "requires_admin": True,
            "paths": [
                os.path.join(system_root, "Logs"),
                os.path.join(system_root, r"Panther")
            ],
            "is_recycle_bin": False,
            "supports_age_filter": True
        },
        "prefetch": {
            "name": "Archivos Prefetch de Windows",
            "desc": "Registros de precarga de aplicaciones antiguas",
            "requires_admin": True,
            "paths": [os.path.join(system_root, "Prefetch")],
            "is_recycle_bin": False,
            "supports_age_filter": False
        }
    }
    return categories


def get_recycle_bin_stats() -> tuple[int, int]:
    """Obtiene el tamaño y cantidad de elementos de la papelera de reciclaje."""
    if sys.platform != "win32" or not hasattr(ctypes, "windll") or not wintypes:
        return 0, 0
    try:
        class SHQUERYRBINFO(ctypes.Structure):
            _fields_ = [
                ('cbSize', wintypes.DWORD),
                ('i64Size', ctypes.c_int64),
                ('i64NumItems', ctypes.c_int64),
            ]
        rb_info = SHQUERYRBINFO()
        rb_info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
        result = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(rb_info))
        if result == 0:
            return rb_info.i64Size, rb_info.i64NumItems
    except Exception:
        pass
    return 0, 0


def is_path_excluded(file_path: str, exclusions: list) -> bool:
    """Verifica si una ruta está en la lista de exclusiones del usuario."""
    if not exclusions:
        return False
    norm_target = os.path.normcase(os.path.abspath(file_path))
    for excl in exclusions:
        if not excl.strip():
            continue
        norm_excl = os.path.normcase(os.path.abspath(excl.strip()))
        if norm_target == norm_excl or norm_target.startswith(norm_excl + os.sep):
            return True
    return False


def is_file_safe_to_clean(file_path: str, supports_age_filter: bool, min_age_hours: int = 24) -> bool:
    """
    Comprueba si un archivo es seguro de eliminar según la regla de antigüedad (Retention filter).
    Si se modificó o creó hace menos de min_age_hours, se ignora para no dañar instaladores activos.
    """
    if not supports_age_filter or min_age_hours <= 0:
        return True
    try:
        stat = os.stat(file_path)
        if sys.platform == "win32":
            last_touch = max(stat.st_mtime, stat.st_ctime)
        else:
            last_touch = stat.st_mtime
        age_hours = (time.time() - last_touch) / 3600.0
        return age_hours >= min_age_hours
    except Exception:
        return False


def scan_category(cat_key: str, cat_info: dict, min_age_hours: int = 24, exclusions: list = None, on_progress=None):
    """
    Escanea una categoría y calcula el espacio y número de archivos recuperables.
    Aplica filtro de antigüedad, exclusiones y protección de junctions.
    Retorna (total_size, total_files, items_list).
    """
    total_size = 0
    total_files = 0
    items = []
    exclusions = exclusions or []

    if cat_info.get("is_recycle_bin"):
        size, num_items = get_recycle_bin_stats()
        return size, num_items, []

    paths = cat_info.get("paths", [])
    filter_patterns = cat_info.get("filter_patterns", None)
    supports_age = cat_info.get("supports_age_filter", False)

    for base_path in paths:
        if not base_path or not os.path.exists(base_path):
            continue

        try:
            if filter_patterns:
                for pattern in filter_patterns:
                    for file_path in glob.glob(os.path.join(base_path, pattern)):
                        try:
                            if os.path.isfile(file_path) and not is_safe_link_or_junction(file_path):
                                if is_path_excluded(file_path, exclusions):
                                    continue
                                if not is_file_safe_to_clean(file_path, supports_age, min_age_hours):
                                    continue
                                fsize = os.path.getsize(file_path)
                                total_size += fsize
                                total_files += 1
                                items.append({"path": file_path, "size": fsize, "mtime": os.path.getmtime(file_path)})
                                if on_progress:
                                    on_progress(file_path)
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
            else:
                for root, dirs, files in os.walk(base_path, topdown=True):
                    # Proteger contra carpetas que sean symlinks o junctions
                    dirs[:] = [d for d in dirs if not is_safe_link_or_junction(os.path.join(root, d))]

                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            if os.path.isfile(file_path) and not is_safe_link_or_junction(file_path):
                                if is_path_excluded(file_path, exclusions):
                                    continue
                                if not is_file_safe_to_clean(file_path, supports_age, min_age_hours):
                                    continue
                                fsize = os.path.getsize(file_path)
                                total_size += fsize
                                total_files += 1
                                items.append({"path": file_path, "size": fsize, "mtime": os.path.getmtime(file_path)})
                                if on_progress:
                                    on_progress(file_path)
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
        except (PermissionError, OSError):
            continue

    return total_size, total_files, items


def empty_recycle_bin() -> bool:
    """Vacía la papelera de reciclaje silenciosamente."""
    if sys.platform != "win32" or not hasattr(ctypes, "windll"):
        return False
    try:
        flags = 0x00000001 | 0x00000002 | 0x00000004
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        return result == 0
    except Exception:
        return False


def clean_category(cat_key: str, cat_info: dict, min_age_hours: int = 24, exclusions: list = None, on_item_cleaned=None):
    """
    Elimina archivos de una categoría de forma segura.
    Omite archivos bloqueados por el sistema sin fallar y respeta el filtro de seguridad y junctions.
    Retorna (bytes_liberados, archivos_eliminados, archivos_omitidos).
    """
    freed_bytes = 0
    deleted_count = 0
    skipped_count = 0
    exclusions = exclusions or []

    if cat_info.get("is_recycle_bin"):
        size_before, items_before = get_recycle_bin_stats()
        success = empty_recycle_bin()
        if success:
            if on_item_cleaned:
                on_item_cleaned("Papelera de Reciclaje vaciada con éxito", True)
            return size_before, items_before, 0
        else:
            return 0, 0, items_before

    paths = cat_info.get("paths", [])
    filter_patterns = cat_info.get("filter_patterns", None)
    supports_age = cat_info.get("supports_age_filter", False)

    for base_path in paths:
        if not base_path or not os.path.exists(base_path):
            continue

        if filter_patterns:
            for pattern in filter_patterns:
                for file_path in glob.glob(os.path.join(base_path, pattern)):
                    if is_path_excluded(file_path, exclusions):
                        skipped_count += 1
                        continue
                    if not is_file_safe_to_clean(file_path, supports_age, min_age_hours):
                        skipped_count += 1
                        continue
                    try:
                        if os.path.isfile(file_path) and not is_safe_link_or_junction(file_path):
                            fsize = os.path.getsize(file_path)
                            os.remove(file_path)
                            freed_bytes += fsize
                            deleted_count += 1
                            if on_item_cleaned:
                                on_item_cleaned(f"Eliminado: {file_path}", True)
                    except (PermissionError, OSError):
                        skipped_count += 1
                        if on_item_cleaned:
                            on_item_cleaned(f"Omitido (en uso): {file_path}", False)
        else:
            for root, dirs, files in os.walk(base_path, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    if is_path_excluded(file_path, exclusions):
                        skipped_count += 1
                        continue
                    if not is_file_safe_to_clean(file_path, supports_age, min_age_hours):
                        skipped_count += 1
                        continue
                    try:
                        if os.path.isfile(file_path) and not is_safe_link_or_junction(file_path):
                            fsize = os.path.getsize(file_path)
                            os.remove(file_path)
                            freed_bytes += fsize
                            deleted_count += 1
                            if on_item_cleaned:
                                on_item_cleaned(f"Eliminado: {file_path}", True)
                    except (PermissionError, OSError):
                        skipped_count += 1
                        if on_item_cleaned:
                            on_item_cleaned(f"Omitido (bloqueado): {file_path}", False)

                for directory in dirs:
                    dir_path = os.path.join(root, directory)
                    if not is_path_excluded(dir_path, exclusions) and not is_safe_link_or_junction(dir_path):
                        try:
                            os.rmdir(dir_path)
                        except (PermissionError, OSError):
                            pass

    return freed_bytes, deleted_count, skipped_count


def shred_file(file_path: str, passes: int = 1) -> tuple[bool, str]:
    """
    Tritura y elimina un archivo de forma segura sobrescribiendo su contenido
    con bytes aleatorios y ceros antes de desenlazarlo del sistema de archivos.
    """
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return False, "El archivo especificado no existe o es un directorio."

    if is_safe_link_or_junction(file_path):
        return False, "No se permite triturar enlaces simbólicos o junctions."

    try:
        file_size = os.path.getsize(file_path)
        if file_size > 0:
            with open(file_path, "ba+", buffering=0) as f:
                for p in range(max(1, passes)):
                    f.seek(0)
                    remaining = file_size
                    chunk_size = 64 * 1024
                    while remaining > 0:
                        to_write = min(remaining, chunk_size)
                        f.write(os.urandom(to_write))
                        remaining -= to_write
                    f.flush()
                    os.fsync(f.fileno())

                # Pasada final de ceros
                f.seek(0)
                remaining = file_size
                zero_chunk = b"\x00" * min(file_size, 64 * 1024)
                while remaining > 0:
                    to_write = min(remaining, len(zero_chunk))
                    f.write(zero_chunk[:to_write])
                    remaining -= to_write
                f.flush()
                os.fsync(f.fileno())

        # Ofuscar nombre temporalmente en la tabla de archivos antes de borrar
        parent_dir = os.path.dirname(file_path)
        dummy_name = os.path.join(parent_dir, f"__tmp_shred_{int(time.time()*1000)}.tmp")
        try:
            os.rename(file_path, dummy_name)
            os.remove(dummy_name)
        except OSError:
            os.remove(file_path)

        return True, "Archivo triturado y destruido con éxito de forma irrecuperable."
    except Exception as e:
        return False, f"Error al triturar el archivo: {e}"


def find_duplicate_files(target_dir: str, min_size_bytes: int = 1024, max_results: int = 100) -> list[dict]:
    """
    Busca archivos duplicados en un directorio objetivo comparando tamaño y hash SHA-256 por bloques.
    Retorna lista de grupos de duplicados ordenados por espacio desperdiciado.
    """
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return []

    size_map: dict[int, list[str]] = {}

    # 1. Agrupar por tamaño
    try:
        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if not is_safe_link_or_junction(os.path.join(root, d))]
            for f in files:
                f_path = os.path.join(root, f)
                if is_safe_link_or_junction(f_path):
                    continue
                try:
                    sz = os.path.getsize(f_path)
                    if sz >= min_size_bytes:
                        size_map.setdefault(sz, []).append(f_path)
                except (OSError, PermissionError):
                    continue
    except Exception:
        return []

    # 2. Para tamaños con más de 1 archivo, calcular hash SHA-256
    duplicates = []
    for sz, paths in size_map.items():
        if len(paths) < 2:
            continue

        hash_map: dict[str, list[str]] = {}
        for path in paths:
            try:
                hasher = hashlib.sha256()
                with open(path, "rb") as f:
                    while chunk := f.read(65536):
                        hasher.update(chunk)
                file_hash = hasher.hexdigest()
                hash_map.setdefault(file_hash, []).append(path)
            except (OSError, PermissionError):
                continue

        for f_hash, dup_paths in hash_map.items():
            if len(dup_paths) > 1:
                wasted = sz * (len(dup_paths) - 1)
                duplicates.append({
                    "hash": f_hash,
                    "size": sz,
                    "size_formatted": format_size(sz),
                    "wasted_bytes": wasted,
                    "wasted_formatted": format_size(wasted),
                    "files": dup_paths
                })
                if len(duplicates) >= max_results:
                    break

    duplicates.sort(key=lambda x: x["wasted_bytes"], reverse=True)
    return duplicates


def export_report(report_data: dict, file_path: str, format_type: str = "json") -> tuple[bool, str]:
    """Exporta el reporte de escaneo o limpieza en formato JSON o Texto estructurado."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            if format_type.lower() == "json":
                json.dump(report_data, f, indent=4, ensure_ascii=False)
            else:
                f.write("=" * 65 + "\n")
                f.write("      ⚡ PyClean Pro - Reporte de Análisis y Limpieza\n")
                f.write("=" * 65 + "\n\n")
                f.write(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                if "total_freed_formatted" in report_data:
                    f.write(f"Espacio total liberado: {report_data.get('total_freed_formatted')}\n")
                    f.write(f"Archivos eliminados: {report_data.get('total_deleted', 0):,}\n")
                    f.write(f"Archivos protegidos/omitidos: {report_data.get('total_skipped', 0):,}\n\n")
                elif "total_formatted" in report_data:
                    f.write(f"Espacio total recuperable: {report_data.get('total_formatted')}\n")
                    f.write(f"Archivos detectados: {report_data.get('total_files', 0):,}\n\n")

                cats = report_data.get("categories", {})
                if cats:
                    f.write("Detalle por categoría:\n")
                    f.write("-" * 65 + "\n")
                    for k, v in cats.items():
                        name = v.get("name", k)
                        sz = v.get("size_formatted") or v.get("freed_formatted", "0 B")
                        f.write(f"  • {name:<45}: {sz}\n")
        return True, f"Reporte guardado con éxito en: {file_path}"
    except Exception as e:
        return False, str(e)


def flush_dns() -> tuple[bool, str]:
    """Limpia la caché de resolución DNS del sistema de Windows."""
    if sys.platform != "win32":
        return False, "ipconfig /flushdns sólo está disponible en Windows."
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        res = subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            check=False
        )
        return res.returncode == 0, res.stdout.strip()
    except Exception as e:
        return False, str(e)


def optimize_ram() -> int:
    """
    Optimiza el uso de memoria RAM liberando páginas inactivas
    y reduciendo el Working Set de los procesos del usuario.
    """
    freed_procs = 0
    if sys.platform != "win32" or not hasattr(ctypes, "windll") or not wintypes:
        return 0

    try:
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_SET_QUOTA = 0x0100

        pids = (wintypes.DWORD * 2048)()
        cb_needed = wintypes.DWORD()

        if ctypes.windll.psapi.EnumProcesses(
            ctypes.byref(pids),
            ctypes.sizeof(pids),
            ctypes.byref(cb_needed)
        ):
            num_procs = cb_needed.value // ctypes.sizeof(wintypes.DWORD)
            for i in range(num_procs):
                pid = pids[i]
                if pid <= 4:
                    continue
                h_proc = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA,
                    False,
                    pid
                )
                if h_proc:
                    try:
                        if ctypes.windll.psapi.EmptyWorkingSet(h_proc):
                            freed_procs += 1
                    finally:
                        ctypes.windll.kernel32.CloseHandle(h_proc)
    except Exception:
        pass

    return freed_procs


# --- Gestor de Programas de Inicio de Windows ---

if winreg:
    STARTUP_REG_PATHS = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Usuario Actual"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "Todo el Sistema (HKLM)"),
    ]
else:
    STARTUP_REG_PATHS = []


def get_startup_programs() -> list[dict]:
    """
    Obtiene la lista de programas configurados para iniciar automáticamente con Windows.
    Retorna lista de dicts: [{'name', 'command', 'scope', 'root_key', 'sub_key', 'enabled'}]
    """
    programs = []
    if not winreg:
        return programs

    for root_key, sub_key, scope in STARTUP_REG_PATHS:
        try:
            with winreg.OpenKey(root_key, sub_key, 0, winreg.KEY_READ) as key:
                idx = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(key, idx)
                        programs.append({
                            "name": name,
                            "command": val,
                            "scope": scope,
                            "root_key": root_key,
                            "sub_key": sub_key,
                            "enabled": True
                        })
                        idx += 1
                    except OSError:
                        break
        except Exception:
            pass

        disabled_sub_key = sub_key + "Disabled"
        try:
            with winreg.OpenKey(root_key, disabled_sub_key, 0, winreg.KEY_READ) as key:
                idx = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(key, idx)
                        programs.append({
                            "name": name,
                            "command": val,
                            "scope": f"{scope} (Deshabilitado)",
                            "root_key": root_key,
                            "sub_key": disabled_sub_key,
                            "enabled": False
                        })
                        idx += 1
                    except OSError:
                        break
        except Exception:
            pass

    return programs


def toggle_startup_program(prog: dict) -> tuple[bool, str]:
    """
    Habilita o deshabilita un programa de inicio moviéndolo entre 'Run' y 'RunDisabled'.
    """
    if not winreg:
        return False, "La gestión de programas de inicio sólo está soportada en Windows."

    root_key = prog["root_key"]
    name = prog["name"]
    command = prog["command"]
    is_currently_enabled = prog["enabled"]

    source_sub_key = r"Software\Microsoft\Windows\CurrentVersion\Run" if is_currently_enabled else r"Software\Microsoft\Windows\CurrentVersion\RunDisabled"
    dest_sub_key = r"Software\Microsoft\Windows\CurrentVersion\RunDisabled" if is_currently_enabled else r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        dest_key = winreg.CreateKeyEx(root_key, dest_sub_key, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(dest_key, name, 0, winreg.REG_SZ, command)
        winreg.CloseKey(dest_key)

        source_key = winreg.OpenKey(root_key, source_sub_key, 0, winreg.KEY_WRITE)
        winreg.DeleteValue(source_key, name)
        winreg.CloseKey(source_key)

        new_state = "deshabilitado" if is_currently_enabled else "habilitado"
        return True, f"'{name}' ha sido {new_state} con éxito."
    except PermissionError:
        return False, "Se requieren permisos de Administrador para modificar este programa."
    except Exception as e:
        return False, str(e)


# ==============================================================================
# PyClean Pro v2.2 - Desinstalador, Programador, Telemetría y Auditor de Descargas
# ==============================================================================

UNINSTALL_REG_KEYS = [
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
] if winreg else []

def get_installed_apps() -> list[dict]:
    """
    Obtiene la lista de programas instalados en Windows desde el Registro.
    Retorna lista de dicts: [{'name', 'version', 'publisher', 'install_date', 'size_bytes', 'size_formatted', 'uninstall_string', 'quiet_uninstall_string'}]
    """
    apps = []
    if not winreg:
        return apps

    seen_names = set()
    for root_key, sub_key in UNINSTALL_REG_KEYS:
        try:
            with winreg.OpenKey(root_key, sub_key, 0, winreg.KEY_READ) as key:
                num_subkeys, _, _ = winreg.QueryInfoKey(key)
                for i in range(num_subkeys):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name, 0, winreg.KEY_READ) as app_key:
                            def get_val(val_name, default=""):
                                try:
                                    v, _ = winreg.QueryValueEx(app_key, val_name)
                                    return v
                                except OSError:
                                    return default

                            name = str(get_val("DisplayName", "")).strip()
                            if not name:
                                continue

                            system_component = get_val("SystemComponent", 0)
                            parent_key = get_val("ParentKeyName", "")
                            if system_component == 1 or parent_key:
                                continue

                            if name.lower() in seen_names:
                                continue
                            seen_names.add(name.lower())

                            version = str(get_val("DisplayVersion", ""))
                            publisher = str(get_val("Publisher", ""))
                            install_date = str(get_val("InstallDate", ""))
                            size_kb = get_val("EstimatedSize", 0)
                            uninstall_str = str(get_val("UninstallString", ""))
                            quiet_uninstall = str(get_val("QuietUninstallString", ""))

                            size_bytes = (size_kb * 1024) if isinstance(size_kb, int) and size_kb > 0 else 0

                            apps.append({
                                "name": name,
                                "version": version,
                                "publisher": publisher,
                                "install_date": install_date,
                                "size_bytes": size_bytes,
                                "size_formatted": format_size(size_bytes) if size_bytes > 0 else "Desconocido",
                                "uninstall_string": uninstall_str,
                                "quiet_uninstall_string": quiet_uninstall
                            })
                    except (OSError, PermissionError):
                        continue
        except Exception:
            pass

    apps.sort(key=lambda x: x["name"].lower())
    return apps


def run_uninstaller(uninstall_string: str) -> tuple[bool, str]:
    """Ejecuta el comando oficial de desinstalación de un programa."""
    if not uninstall_string.strip():
        return False, "Comando de desinstalación vacío o no disponible."
    if sys.platform != "win32":
        return False, "La desinstalación sólo está soportada en Windows."

    try:
        subprocess.Popen(uninstall_string, shell=True)
        return True, "Asistente de desinstalación iniciado."
    except Exception as e:
        return False, f"Error iniciando desinstalador: {e}"


def find_app_leftovers(app_name: str) -> list[str]:
    """
    Busca carpetas residuales huérfanas en AppData y ProgramData relacionadas con el nombre de la app.
    """
    if not app_name or len(app_name.strip()) < 3:
        return []

    clean_name = "".join(c for c in app_name.lower() if c.isalnum() or c in (" ", "-", "_")).strip()
    leftovers = []

    candidates_dirs = [
        os.environ.get("LOCALAPPDATA", ""),
        os.environ.get("APPDATA", ""),
        os.environ.get("ProgramData", r"C:\ProgramData"),
    ]

    protected_names = {"microsoft", "windows", "temp", "programs", "packages", "system", "temp", "common"}

    for base in candidates_dirs:
        if not base or not os.path.exists(base):
            continue
        try:
            for item in os.listdir(base):
                item_path = os.path.join(base, item)
                if os.path.isdir(item_path) and not is_safe_link_or_junction(item_path):
                    item_clean = "".join(c for c in item.lower() if c.isalnum() or c in (" ", "-", "_")).strip()
                    if item.lower() in protected_names:
                        continue
                    if clean_name == item_clean or (len(clean_name) >= 4 and clean_name in item_clean):
                        leftovers.append(item_path)
        except (PermissionError, OSError):
            continue

    return leftovers


TASK_NAME = "PyCleanPro_AutoClean"

def get_scheduled_task_status() -> dict:
    """Consulta si la tarea de mantenimiento automático está programada en Windows."""
    if sys.platform != "win32":
        return {"exists": False, "enabled": False, "task_name": TASK_NAME, "message": "Solo disponible en Windows."}

    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        res = subprocess.run(
            ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "CSV", "/nh"],
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            check=False,
            encoding="utf-8",
            errors="ignore"
        )
        if res.returncode == 0 and TASK_NAME.lower() in res.stdout.lower():
            return {"exists": True, "enabled": True, "task_name": TASK_NAME}
        return {"exists": False, "enabled": False, "task_name": TASK_NAME}
    except Exception as e:
        return {"exists": False, "enabled": False, "error": str(e)}


def set_scheduled_task(enabled: bool, frequency: str = "weekly") -> tuple[bool, str]:
    """Habilita o deshabilita la tarea automática de limpieza en Windows Task Scheduler."""
    if sys.platform != "win32":
        return False, "El Programador de Tareas sólo está disponible en Windows."

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    if not enabled:
        try:
            res = subprocess.run(
                ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
                capture_output=True,
                text=True,
                startupinfo=startupinfo,
                check=False
            )
            return True, "Tarea de mantenimiento automático eliminada con éxito."
        except Exception as e:
            return False, f"Error al eliminar la tarea: {e}"

    if getattr(sys, "frozen", False):
        exe_path = f'"{sys.executable}"'
        task_action = f'{exe_path} --clean --all'
    else:
        script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
        task_action = f'"{sys.executable}" "{script}" --clean --all'

    sc_flag = "weekly" if frequency == "weekly" else "daily"
    cmd = [
        "schtasks", "/create",
        "/tn", TASK_NAME,
        "/tr", task_action,
        "/sc", sc_flag,
        "/st", "03:00",
        "/f",
        "/rl", "HIGHEST"
    ]
    if sc_flag == "weekly":
        cmd.extend(["/d", "SUN"])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, check=False)
        if res.returncode == 0:
            freq_label = "cada domingo a las 03:00 AM" if sc_flag == "weekly" else "diariamente a las 03:00 AM"
            return True, f"Tarea programada configurada con éxito ({freq_label})."
        return False, res.stderr.strip() or res.stdout.strip()
    except Exception as e:
        return False, str(e)


TELEMETRY_SERVICES = [
    ("DiagTrack", "Experiencias de telemetría y diagnósticos de Windows"),
    ("dmwappushservice", "Servicio de enrutamiento WAP Push"),
    ("WerSvc", "Servicio de Informes de Errores de Windows (WER)"),
]

def get_telemetry_status() -> dict:
    """Verifica el estado de los servicios de telemetría y recolección de diagnósticos."""
    services_info = []
    telemetry_disabled = False

    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        for srv_name, desc in TELEMETRY_SERVICES:
            try:
                res = subprocess.run(
                    ["sc", "query", srv_name],
                    capture_output=True,
                    text=True,
                    startupinfo=startupinfo,
                    check=False
                )
                running = "RUNNING" in res.stdout
                services_info.append({"service": srv_name, "desc": desc, "running": running})
            except Exception:
                services_info.append({"service": srv_name, "desc": desc, "running": False})

        if winreg:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", 0, winreg.KEY_READ) as k:
                    val, _ = winreg.QueryValueEx(k, "AllowTelemetry")
                    if val == 0:
                        telemetry_disabled = True
            except Exception:
                pass
    else:
        services_info = [{"service": s, "desc": d, "running": False} for s, d in TELEMETRY_SERVICES]

    return {
        "services": services_info,
        "policy_disabled": telemetry_disabled
    }


def toggle_telemetry(disable: bool) -> tuple[bool, str]:
    """Desactiva o restaura los servicios de telemetría y la política de recolección de datos."""
    if sys.platform != "win32":
        return False, "La optimización de telemetría sólo está disponible en Windows."

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    for srv_name, _ in TELEMETRY_SERVICES:
        start_type = "disabled" if disable else "auto"
        action = "stop" if disable else "start"
        try:
            subprocess.run(["sc", "config", srv_name, f"start={start_type}"], startupinfo=startupinfo, check=False)
            subprocess.run(["sc", action, srv_name], startupinfo=startupinfo, check=False)
        except Exception:
            pass

    if winreg:
        try:
            key_path = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_WRITE) as k:
                val = 0 if disable else 1
                winreg.SetValueEx(k, "AllowTelemetry", 0, winreg.REG_DWORD, val)
        except PermissionError:
            return False, "Se requieren permisos de Administrador para modificar las políticas de telemetría."
        except Exception:
            pass

    msg = "Telemetría y servicios de rastreo mitigados con éxito." if disable else "Servicios de telemetría restablecidos a valores por defecto."
    return True, msg


DOWNLOAD_EXTENSIONS = {".exe", ".msi", ".iso", ".zip", ".rar", ".7z", ".tar.gz", ".dmg", ".pkg"}

def audit_old_downloads(min_age_days: int = 30) -> list[dict]:
    """
    Busca archivos pesados de instalación y archivos comprimidos en la carpeta de Descargas
    cuya última modificación sea superior a min_age_days días.
    """
    user_home = Path.home()
    downloads_path = os.path.join(str(user_home), "Downloads")
    if not os.path.exists(downloads_path):
        downloads_path = os.path.join(str(user_home), "Descargas")
    if not os.path.exists(downloads_path):
        return []

    old_items = []
    min_age_seconds = max(1, min_age_days) * 86400
    now = time.time()

    try:
        for entry in os.listdir(downloads_path):
            file_path = os.path.join(downloads_path, entry)
            if os.path.isfile(file_path) and not is_safe_link_or_junction(file_path):
                ext = Path(entry).suffix.lower()
                if ext in DOWNLOAD_EXTENSIONS or entry.lower().endswith(".tar.gz"):
                    try:
                        stat = os.stat(file_path)
                        age_sec = now - stat.st_mtime
                        if age_sec >= min_age_seconds:
                            size = stat.st_size
                            old_items.append({
                                "name": entry,
                                "path": file_path,
                                "size": size,
                                "size_formatted": format_size(size),
                                "days_old": int(age_sec // 86400),
                                "mtime": stat.st_mtime
                            })
                    except (PermissionError, OSError):
                        continue
    except Exception as e:
        logger.debug("Error auditando descargas: %s", e)

    old_items.sort(key=lambda x: x["size"], reverse=True)
    return old_items


# --- v2.3: Analizador Visual de Almacenamiento, Particiones y Treemap ---

FILE_CATEGORIES = {
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Imágenes": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".psd", ".raw"},
    "Comprimidos e ISOs": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".vmdk", ".vhdx", ".img"},
    "Ejecutables e Instaladores": {".exe", ".msi", ".dll", ".sys", ".bat", ".cmd", ".ps1", ".vbs"},
    "Documentos": {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".csv", ".rtf", ".epub"},
    "Desarrollo y Código": {".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".java", ".cpp", ".c", ".h", ".cs", ".php", ".go", ".rs", ".sql"}
}


def get_partitions_detailed() -> list[dict]:
    """
    Retorna información enriquecida sobre todas las particiones del sistema:
    etiqueta de volumen, tipo de sistema de archivos (NTFS, FAT32), capacidad total,
    espacio usado/libre y porcentaje.
    """
    partitions = []
    if sys.platform == "win32" and hasattr(ctypes, "windll"):
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i in range(26):
                if bitmask & (1 << i):
                    drive_letter = f"{chr(65 + i)}:\\"
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_letter)
                    # 2: Removable, 3: Fixed, 4: Remote/Network, 5: CD-ROM, 6: RAMDisk
                    type_labels = {
                        2: "Extraíble (USB)",
                        3: "Disco Local",
                        4: "Unidad de Red",
                        5: "Unidad Óptica (CD/DVD)",
                        6: "RAMDisk"
                    }
                    type_str = type_labels.get(drive_type, "Desconocido")

                    vol_name = ctypes.create_unicode_buffer(261)
                    fs_name = ctypes.create_unicode_buffer(261)
                    serial = ctypes.c_ulong()
                    max_len = ctypes.c_ulong()
                    flags = ctypes.c_ulong()

                    has_vol_info = ctypes.windll.kernel32.GetVolumeInformationW(
                        drive_letter,
                        vol_name,
                        ctypes.sizeof(vol_name),
                        ctypes.byref(serial),
                        ctypes.byref(max_len),
                        ctypes.byref(flags),
                        fs_name,
                        ctypes.sizeof(fs_name)
                    )

                    label = vol_name.value if has_vol_info and vol_name.value else "Disco Local"
                    fs = fs_name.value if has_vol_info and fs_name.value else "NTFS"

                    try:
                        total, used, free = shutil.disk_usage(drive_letter)
                        pct = round((used / total) * 100, 1) if total > 0 else 0.0
                        partitions.append({
                            "letter": drive_letter,
                            "label": label,
                            "fs": fs,
                            "type": type_str,
                            "total": total,
                            "used": used,
                            "free": free,
                            "total_formatted": format_size(total),
                            "used_formatted": format_size(used),
                            "free_formatted": format_size(free),
                            "percent": pct
                        })
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("Error obteniendo particiones detalladas: %s", e)

    if not partitions:
        root_path = "C:\\" if sys.platform == "win32" else "/"
        try:
            total, used, free = shutil.disk_usage(root_path)
            pct = round((used / total) * 100, 1) if total > 0 else 0.0
            partitions.append({
                "letter": root_path,
                "label": "Sistema Principal",
                "fs": "NTFS" if sys.platform == "win32" else "ext4",
                "type": "Disco Local",
                "total": total,
                "used": used,
                "free": free,
                "total_formatted": format_size(total),
                "used_formatted": format_size(used),
                "free_formatted": format_size(free),
                "percent": pct
            })
        except Exception:
            pass

    return partitions


def _get_dir_size_fast(path: str, max_depth: int = 3, max_files: int = 5000) -> tuple[int, int]:
    """Calcula el tamaño de una carpeta de forma rápida y segura sin bucles infinitos."""
    total_size = 0
    file_count = 0
    stack = [(path, 0)]

    while stack and file_count < max_files:
        current_dir, depth = stack.pop()
        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    try:
                        if is_safe_link_or_junction(entry.path):
                            continue
                        if entry.is_file(follow_symlinks=False):
                            total_size += entry.stat(follow_symlinks=False).st_size
                            file_count += 1
                        elif entry.is_dir(follow_symlinks=False) and depth < max_depth:
                            stack.append((entry.path, depth + 1))
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            continue

    return total_size, file_count


def scan_folder_treemap(target_path: str) -> dict:
    """
    Analiza una carpeta o unidad para generar un mapa jerárquico de carpetas y archivos,
    calculando pesos relativos y categorías para el visualizador Treemap.
    """
    target = os.path.abspath(target_path)
    if not os.path.exists(target):
        return {"error": f"La ruta no existe: {target}", "items": [], "categories": []}

    items = []
    cat_sizes = {cat: 0 for cat in FILE_CATEGORIES}
    cat_sizes["Otros"] = 0
    total_folder_size = 0

    parent_path = os.path.dirname(target) if os.path.dirname(target) != target else None

    try:
        with os.scandir(target) as entries:
            for entry in entries:
                try:
                    if is_safe_link_or_junction(entry.path):
                        continue

                    if entry.is_dir(follow_symlinks=False):
                        dir_size, dir_files = _get_dir_size_fast(entry.path)
                        total_folder_size += dir_size
                        items.append({
                            "name": entry.name,
                            "path": entry.path,
                            "is_dir": True,
                            "size": dir_size,
                            "size_formatted": format_size(dir_size),
                            "count": dir_files,
                            "type": "Carpeta"
                        })
                    elif entry.is_file(follow_symlinks=False):
                        stat = entry.stat(follow_symlinks=False)
                        f_size = stat.st_size
                        total_folder_size += f_size
                        ext = Path(entry.name).suffix.lower()

                        matched_cat = "Otros"
                        for cat_name, ext_set in FILE_CATEGORIES.items():
                            if ext in ext_set:
                                matched_cat = cat_name
                                break
                        cat_sizes[matched_cat] += f_size

                        items.append({
                            "name": entry.name,
                            "path": entry.path,
                            "is_dir": False,
                            "size": f_size,
                            "size_formatted": format_size(f_size),
                            "count": 1,
                            "type": matched_cat,
                            "ext": ext
                        })
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError) as e:
        return {"error": f"Acceso denegado a {target}: {e}", "items": [], "categories": []}

    items.sort(key=lambda x: x["size"], reverse=True)
    for item in items:
        item["percent"] = round((item["size"] / total_folder_size * 100), 1) if total_folder_size > 0 else 0.0

    formatted_cats = []
    for cat_name, cat_bytes in cat_sizes.items():
        if cat_bytes > 0:
            pct = round((cat_bytes / total_folder_size * 100), 1) if total_folder_size > 0 else 0.0
            formatted_cats.append({
                "category": cat_name,
                "size": cat_bytes,
                "size_formatted": format_size(cat_bytes),
                "percent": pct
            })
    formatted_cats.sort(key=lambda x: x["size"], reverse=True)

    return {
        "current_path": target,
        "parent_path": parent_path,
        "name": os.path.basename(target) or target,
        "total_size": total_folder_size,
        "total_size_formatted": format_size(total_folder_size),
        "items": items,
        "categories": formatted_cats
    }


def find_largest_files(target_path: str, min_size_mb: int = 100, limit: int = 50) -> list[dict]:
    """
    Escanea recursivamente una ruta en busca de los archivos más pesados del sistema (>= min_size_mb).
    Retorna el top N de archivos gigantes ordenados por tamaño.
    """
    target = os.path.abspath(target_path)
    if not os.path.exists(target):
        return []

    min_bytes = max(1, min_size_mb) * 1024 * 1024
    largest_files = []

    try:
        for root, dirs, files in os.walk(target, topdown=True, followlinks=False):
            dirs[:] = [d for d in dirs if not is_safe_link_or_junction(os.path.join(root, d))]

            for file_name in files:
                file_path = os.path.join(root, file_name)
                try:
                    if is_safe_link_or_junction(file_path):
                        continue
                    stat = os.stat(file_path, follow_symlinks=False)
                    if stat.st_size >= min_bytes:
                        ext = Path(file_name).suffix.lower()
                        largest_files.append({
                            "name": file_name,
                            "path": file_path,
                            "dir": root,
                            "size": stat.st_size,
                            "size_formatted": format_size(stat.st_size),
                            "ext": ext,
                            "mtime": stat.st_mtime
                        })
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass

    largest_files.sort(key=lambda x: x["size"], reverse=True)
    return largest_files[:limit]


def open_in_explorer(target_path: str) -> bool:
    """Abre la ruta o selecciona el archivo en el Explorador de archivos nativo del SO."""
    if not os.path.exists(target_path):
        return False

    abs_path = os.path.abspath(target_path)
    if sys.platform == "win32":
        try:
            if os.path.isfile(abs_path):
                subprocess.Popen(["explorer.exe", f"/select,{abs_path}"])
            else:
                subprocess.Popen(["explorer.exe", abs_path])
            return True
        except Exception:
            return False
    elif sys.platform == "darwin":
        try:
            cmd = ["open", "-R", abs_path] if os.path.isfile(abs_path) else ["open", abs_path]
            subprocess.Popen(cmd)
            return True
        except Exception:
            return False
    else:
        try:
            folder = os.path.dirname(abs_path) if os.path.isfile(abs_path) else abs_path
            subprocess.Popen(["xdg-open", folder])
            return True
        except Exception:
            return False
