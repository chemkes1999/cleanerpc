"""
PyClean Pro - Motor de Limpieza y Optimización para Windows
Módulo seguro de escaneo, eliminación de temporales y optimización del sistema.
"""

import os
import sys
import shutil
import subprocess
import ctypes
from ctypes import wintypes
import glob
import time
import json
from pathlib import Path
import winreg

# Ruta de archivo de configuración local
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cleaner_config.json")

# Definición de estructuras ctypes para memoria en Windows
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
        except Exception:
            pass
    return default_cfg


def save_config(cfg: dict) -> bool:
    """Guarda la configuración persistente en disco."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


def is_admin() -> bool:
    """Verifica si el script se está ejecutando con privilegios de Administrador."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def request_admin_elevation():
    """Relanza la aplicación actual solicitando elevación de Administrador (UAC)."""
    try:
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        sys.exit(0)
    except Exception as e:
        return False, str(e)


def format_size(size_bytes: int) -> str:
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


def get_system_drives():
    """
    Detecta todas las unidades fijas y extraíbles del sistema con su espacio.
    Retorna lista de diccionarios: [{'letter': 'C:\\', 'type': 'fixed', ...}]
    """
    drives = []
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
        try:
            total, used, free = shutil.disk_usage("C:\\")
            drives.append({
                "letter": "C:\\",
                "type": "Fijo",
                "total": total,
                "used": used,
                "free": free,
                "percent": round((used / total) * 100, 1) if total > 0 else 0.0
            })
        except Exception:
            pass

    return drives


def get_system_stats(drive: str = "C:\\"):
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
    # Disco seleccionado
    try:
        target_drive = drive if os.path.exists(drive) else "C:\\"
        total, used, free = shutil.disk_usage(target_drive)
        stats["disk_total"] = total
        stats["disk_used"] = used
        stats["disk_free"] = free
        stats["disk_percent"] = round((used / total) * 100, 1) if total > 0 else 0.0
    except Exception:
        pass

    # Memoria RAM vía Win32 API
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


def _get_chromium_cache_paths(user_data_path: str):
    """Resuelve rutas de caché para todos los perfiles de Chromium (Default, Profile 1, etc.)."""
    paths = []
    if not os.path.isdir(user_data_path):
        return paths

    # Caché de sombreadores global
    shader = os.path.join(user_data_path, "ShaderCache")
    if os.path.exists(shader):
        paths.append(shader)

    # Iterar carpetas de perfiles
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


def get_target_categories():
    """
    Define y resuelve las rutas seguras para limpieza en el sistema del usuario actual.
    Incluye multi-perfil y soporte ampliado para navegadores y herramientas de desarrollo.
    """
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")
    user_temp = os.environ.get("TEMP", os.path.join(local_app_data, "Temp"))
    system_root = os.environ.get("SystemRoot", r"C:\Windows")

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

    categories = {
        "user_temp": {
            "name": "Temporales de Usuario",
            "desc": "Archivos residuales en %TEMP% y carpetas temporales de aplicaciones",
            "requires_admin": False,
            "paths": [user_temp],
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
        "crash_dumps": {
            "name": "Volcados de Error y WER",
            "desc": "Reportes de bloqueo y volcados de memoria por caídas de software",
            "requires_admin": False,
            "paths": [
                os.path.join(local_app_data, "CrashDumps"),
                os.path.join(local_app_data, r"Microsoft\Windows\WER\ReportArchive"),
                os.path.join(local_app_data, r"Microsoft\Windows\WER\ReportQueue"),
            ],
            "is_recycle_bin": False,
            "supports_age_filter": False
        },
        "thumbnail_cache": {
            "name": "Caché de Miniaturas",
            "desc": "Miniaturas obsoletas del explorador de Windows (.db/.tmp)",
            "requires_admin": False,
            "paths": [
                os.path.join(local_app_data, r"Microsoft\Windows\Explorer")
            ],
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


def get_recycle_bin_stats():
    """Obtiene el tamaño y cantidad de elementos de la papelera de reciclaje."""
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
    Si se creó o modificó hace menos de min_age_hours, se ignora para no dañar instaladores activos.
    """
    if not supports_age_filter or min_age_hours <= 0:
        return True
    try:
        stat = os.stat(file_path)
        last_touch = max(stat.st_mtime, stat.st_ctime)
        age_hours = (time.time() - last_touch) / 3600.0
        return age_hours >= min_age_hours
    except Exception:
        return False


def scan_category(cat_key: str, cat_info: dict, min_age_hours: int = 24, exclusions: list = None, on_progress=None):
    """
    Escanea una categoría y calcula el espacio y número de archivos recuperables.
    Aplica filtro de antigüedad y lista de exclusiones.
    Retorna (total_size, total_files, items_list).
    items_list contiene diccionarios con: {'path', 'size', 'mtime'} para el visor.
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
        if not os.path.exists(base_path):
            continue

        try:
            if filter_patterns:
                for pattern in filter_patterns:
                    for file_path in glob.glob(os.path.join(base_path, pattern)):
                        try:
                            if os.path.isfile(file_path) and not os.path.islink(file_path):
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
                    dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]

                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            if os.path.isfile(file_path) and not os.path.islink(file_path):
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


def empty_recycle_bin():
    """Vacía la papelera de reciclaje silenciosamente."""
    try:
        flags = 0x00000001 | 0x00000002 | 0x00000004
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        return result == 0
    except Exception:
        return False


def clean_category(cat_key: str, cat_info: dict, min_age_hours: int = 24, exclusions: list = None, on_item_cleaned=None):
    """
    Elimina archivos de una categoría de forma segura.
    Omite archivos bloqueados por el sistema sin fallar y respeta el filtro de seguridad.
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
        if not os.path.exists(base_path):
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
                        if os.path.isfile(file_path) and not os.path.islink(file_path):
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
                        if os.path.isfile(file_path) and not os.path.islink(file_path):
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
                    if not is_path_excluded(dir_path, exclusions) and not os.path.islink(dir_path):
                        try:
                            os.rmdir(dir_path)
                        except (PermissionError, OSError):
                            pass

    return freed_bytes, deleted_count, skipped_count


def flush_dns():
    """Limpia la caché de resolución DNS del sistema de Windows."""
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


def optimize_ram():
    """
    Optimiza el uso de memoria RAM liberando páginas inactivas
    y reduciendo el Working Set de los procesos del usuario.
    """
    freed_procs = 0
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

STARTUP_REG_PATHS = [
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Usuario Actual"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "Todo el Sistema (HKLM)"),
]

def get_startup_programs():
    """
    Obtiene la lista de programas configurados para iniciar automáticamente con Windows.
    Retorna lista de dicts: [{'name', 'command', 'scope', 'root_key', 'sub_key', 'enabled'}]
    """
    programs = []

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
