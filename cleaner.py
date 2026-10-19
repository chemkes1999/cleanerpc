"""
PyClean Pro - Motor de Limpieza y Optimización para Windows
Módulo seguro de escaneo, eliminación de temporales y optimización del sistema.
"""

import os
import shutil
import subprocess
import ctypes
from ctypes import wintypes
import glob
from pathlib import Path

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


def is_admin() -> bool:
    """Verifica si el script se está ejecutando con privilegios de Administrador."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def request_admin_elevation():
    """Relanza la aplicación actual solicitando elevación de Administrador (UAC)."""
    import sys
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
    """Convierte un tamaño en bytes a formato legible (B, KB, MB, GB)."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"


def get_system_stats():
    """Obtiene estadísticas de uso de disco y memoria RAM del sistema."""
    stats = {
        "disk_total": 0,
        "disk_used": 0,
        "disk_free": 0,
        "disk_percent": 0.0,
        "ram_load": 0,
        "ram_total": 0,
        "ram_avail": 0,
        "ram_used": 0,
    }
    # Disco C:\
    try:
        total, used, free = shutil.disk_usage("C:\\")
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


def get_target_categories():
    """
    Define y resuelve las rutas seguras para limpieza en el sistema del usuario actual.
    """
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")
    user_temp = os.environ.get("TEMP", os.path.join(local_app_data, "Temp"))
    system_root = os.environ.get("SystemRoot", r"C:\Windows")

    categories = {
        "user_temp": {
            "name": "Temporales de Usuario",
            "desc": "Archivos residuales en %TEMP% y carpetas temporales de aplicaciones",
            "requires_admin": False,
            "paths": [user_temp],
            "is_recycle_bin": False
        },
        "system_temp": {
            "name": "Temporales de Windows",
            "desc": "Archivos temporales del sistema en C:\\Windows\\Temp",
            "requires_admin": True,
            "paths": [os.path.join(system_root, "Temp")],
            "is_recycle_bin": False
        },
        "recycle_bin": {
            "name": "Papelera de Reciclaje",
            "desc": "Archivos eliminados que aún ocupan espacio en el disco",
            "requires_admin": False,
            "paths": [],
            "is_recycle_bin": True
        },
        "browser_chrome": {
            "name": "Caché de Google Chrome",
            "desc": "Archivos temporales de navegación y caché multimedia de Chrome",
            "requires_admin": False,
            "paths": [
                os.path.join(local_app_data, r"Google\Chrome\User Data\Default\Cache"),
                os.path.join(local_app_data, r"Google\Chrome\User Data\Default\Code Cache"),
                os.path.join(local_app_data, r"Google\Chrome\User Data\ShaderCache"),
            ],
            "is_recycle_bin": False
        },
        "browser_edge": {
            "name": "Caché de Microsoft Edge",
            "desc": "Caché web y de sombreadores de Microsoft Edge",
            "requires_admin": False,
            "paths": [
                os.path.join(local_app_data, r"Microsoft\Edge\User Data\Default\Cache"),
                os.path.join(local_app_data, r"Microsoft\Edge\User Data\Default\Code Cache"),
            ],
            "is_recycle_bin": False
        },
        "browser_brave": {
            "name": "Caché de Brave Browser",
            "desc": "Caché temporal de navegación de Brave",
            "requires_admin": False,
            "paths": [
                os.path.join(local_app_data, r"BraveSoftware\Brave-Browser\User Data\Default\Cache"),
                os.path.join(local_app_data, r"BraveSoftware\Brave-Browser\User Data\Default\Code Cache"),
            ],
            "is_recycle_bin": False
        },
        "browser_firefox": {
            "name": "Caché de Mozilla Firefox",
            "desc": "Caché de perfiles de Firefox",
            "requires_admin": False,
            "paths": glob.glob(os.path.join(local_app_data, r"Mozilla\Firefox\Profiles\*\cache2")),
            "is_recycle_bin": False
        },
        "crash_dumps": {
            "name": "Volcados de Error y WER",
            "desc": "Reportes de bloqueo y volcados de memoria por cierres inesperados",
            "requires_admin": False,
            "paths": [
                os.path.join(local_app_data, "CrashDumps"),
                os.path.join(local_app_data, r"Microsoft\Windows\WER\ReportArchive"),
                os.path.join(local_app_data, r"Microsoft\Windows\WER\ReportQueue"),
            ],
            "is_recycle_bin": False
        },
        "thumbnail_cache": {
            "name": "Caché de Miniaturas",
            "desc": "Miniaturas de imágenes y explorador de Windows (.db/.tmp)",
            "requires_admin": False,
            "paths": [
                os.path.join(local_app_data, r"Microsoft\Windows\Explorer")
            ],
            "filter_patterns": ["thumbcache_*.db", "iconcache_*.db"],
            "is_recycle_bin": False
        },
        "windows_update_cache": {
            "name": "Caché de Windows Update",
            "desc": "Paquetes de instalación descargados de actualizaciones pasadas",
            "requires_admin": True,
            "paths": [os.path.join(system_root, r"SoftwareDistribution\Download")],
            "is_recycle_bin": False
        },
        "prefetch": {
            "name": "Archivos Prefetch de Windows",
            "desc": "Registros de precarga de aplicaciones antiguas",
            "requires_admin": True,
            "paths": [os.path.join(system_root, "Prefetch")],
            "is_recycle_bin": False
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


def scan_category(cat_key: str, cat_info: dict, on_progress=None):
    """
    Escanea una categoría y calcula el espacio y número de archivos recuperables.
    No elimina nada.
    """
    total_size = 0
    total_files = 0
    items = []

    if cat_info.get("is_recycle_bin"):
        size, num_items = get_recycle_bin_stats()
        return size, num_items, []

    paths = cat_info.get("paths", [])
    filter_patterns = cat_info.get("filter_patterns", None)

    for base_path in paths:
        if not os.path.exists(base_path):
            continue

        try:
            if filter_patterns:
                for pattern in filter_patterns:
                    for file_path in glob.glob(os.path.join(base_path, pattern)):
                        try:
                            if os.path.isfile(file_path):
                                fsize = os.path.getsize(file_path)
                                total_size += fsize
                                total_files += 1
                                items.append(file_path)
                                if on_progress:
                                    on_progress(file_path)
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
            else:
                for root, dirs, files in os.walk(base_path, topdown=True):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            fsize = os.path.getsize(file_path)
                            total_size += fsize
                            total_files += 1
                            items.append(file_path)
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
        # Flags: SHERB_NOCONFIRMATION (0x1) | SHERB_NOPROGRESSUI (0x2) | SHERB_NOSOUND (0x4)
        flags = 0x00000001 | 0x00000002 | 0x00000004
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        return result == 0
    except Exception:
        return False


def clean_category(cat_key: str, cat_info: dict, on_item_cleaned=None):
    """
    Elimina archivos de una categoría de forma segura.
    Omite archivos bloqueados por el sistema sin fallar.
    Retorna (bytes_liberados, archivos_eliminados, archivos_omitidos).
    """
    freed_bytes = 0
    deleted_count = 0
    skipped_count = 0

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

    for base_path in paths:
        if not os.path.exists(base_path):
            continue

        if filter_patterns:
            for pattern in filter_patterns:
                for file_path in glob.glob(os.path.join(base_path, pattern)):
                    try:
                        if os.path.isfile(file_path):
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
            # Recorrido inverso para borrar archivos y luego carpetas vacías
            for root, dirs, files in os.walk(base_path, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
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

                # Intentar eliminar subdirectorios vacíos
                for directory in dirs:
                    dir_path = os.path.join(root, directory)
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
        # Enumerar procesos vía Win32 API
        import ctypes.wintypes
        
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_SET_QUOTA = 0x0100
        
        # Buffer para hasta 2048 PIDs
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
                    continue  # Saltar procesos del núcleo y System Idle
                h_proc = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA,
                    False,
                    pid
                )
                if h_proc:
                    try:
                        # Vaciado del working set (pasa memoria inactiva a standby/liberada)
                        if ctypes.windll.psapi.EmptyWorkingSet(h_proc):
                            freed_procs += 1
                    finally:
                        ctypes.windll.kernel32.CloseHandle(h_proc)
    except Exception:
        pass

    return freed_procs
