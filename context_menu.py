"""
PyClean Pro v2.4 - Gestor del Menú Contextual de Windows ("Clic Derecho")
Audita y permite desactivar/reactivar entradas del menú contextual del Explorador
de forma 100% reversible usando el valor oficial LegacyDisable (sin borrar claves).
"""

from __future__ import annotations

import sys

try:
    import winreg
except ImportError:
    winreg = None


# Entradas críticas nativas de Windows protegidas para evitar dañar el Explorador
PROTECTED_CONTEXT_KEYS = {
    "open",
    "opennew",
    "opennewprocess",
    "opennewtab",
    "explore",
    "find",
    "edit",
    "print",
    "printto",
    "runas",
    "runasuser",
    "cmd",
    "powershell",
    "pintohome",
    "properties",
}

CONTEXT_SCOPES = [
    ("HKCU", r"Software\Classes\*\shell", "Archivos (Usuario)"),
    ("HKCU", r"Software\Classes\Directory\shell", "Carpetas (Usuario)"),
    ("HKCU", r"Software\Classes\Directory\Background\shell", "Fondo de Carpeta (Usuario)"),
    ("HKCR", r"*\shell", "Archivos (Sistema)"),
    ("HKCR", r"Directory\shell", "Carpetas (Sistema)"),
    ("HKCR", r"Directory\Background\shell", "Fondo de Carpeta (Sistema)"),
]


def is_protected_context_key(key_name: str) -> bool:
    """Retorna True si la clave pertenece a acciones nativas críticas de Windows."""
    return (key_name or "").strip().lower() in PROTECTED_CONTEXT_KEYS


def _get_hive_handle(hive_name: str):
    if not winreg:
        return None
    mapping = {
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKCR": winreg.HKEY_CLASSES_ROOT,
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
    }
    return mapping.get(hive_name)


def get_context_menu_items() -> list[dict]:
    """
    Escanea el Registro de Windows para listar las entradas del menú contextual
    de archivos, carpetas y fondo del Explorador.
    """
    if sys.platform != "win32" or winreg is None:
        return []

    items = []
    seen = set()

    for hive_name, base_path, scope_label in CONTEXT_SCOPES:
        hive = _get_hive_handle(hive_name)
        if hive is None:
            continue
        try:
            with winreg.OpenKey(hive, base_path, 0, winreg.KEY_READ) as root_key:
                idx = 0
                while True:
                    try:
                        sub_name = winreg.EnumKey(root_key, idx)
                        idx += 1
                    except OSError:
                        break

                    full_subkey = f"{base_path}\\{sub_name}"
                    uid = f"{hive_name}\\{full_subkey}".lower()
                    if uid in seen:
                        continue
                    seen.add(uid)

                    label = sub_name
                    command = ""
                    disabled = False

                    try:
                        with winreg.OpenKey(hive, full_subkey, 0, winreg.KEY_READ) as item_key:
                            try:
                                val, _ = winreg.QueryValueEx(item_key, "")
                                if val and isinstance(val, str):
                                    label = val.replace("&", "").strip()
                            except FileNotFoundError:
                                pass

                            try:
                                muiverb, _ = winreg.QueryValueEx(item_key, "MUIVerb")
                                if muiverb and isinstance(muiverb, str) and not muiverb.startswith("@"):
                                    label = muiverb.replace("&", "").strip()
                            except FileNotFoundError:
                                pass

                            try:
                                winreg.QueryValueEx(item_key, "LegacyDisable")
                                disabled = True
                            except FileNotFoundError:
                                disabled = False

                            try:
                                with winreg.OpenKey(item_key, "command", 0, winreg.KEY_READ) as cmd_key:
                                    cmd_val, _ = winreg.QueryValueEx(cmd_key, "")
                                    if isinstance(cmd_val, str):
                                        command = cmd_val
                            except OSError:
                                pass
                    except OSError:
                        continue

                    items.append({
                        "hive": hive_name,
                        "subkey": full_subkey,
                        "key_name": sub_name,
                        "label": label or sub_name,
                        "scope": scope_label,
                        "command": command,
                        "enabled": not disabled,
                        "is_protected": is_protected_context_key(sub_name),
                    })
        except OSError:
            continue

    items.sort(key=lambda x: (x["is_protected"], x["label"].lower()))
    return items


def toggle_context_menu_item(hive_name: str, subkey: str, enable: bool) -> tuple[bool, str]:
    """
    Habilita o deshabilita una entrada del menú contextual de forma reversible
    mediante el valor LegacyDisable.
    """
    if sys.platform != "win32" or winreg is None:
        return False, "La gestión del menú contextual solo está disponible en Windows."

    key_leaf = subkey.rsplit("\\", 1)[-1] if subkey else ""
    if is_protected_context_key(key_leaf):
        return False, f"La entrada '{key_leaf}' está protegida por ser una acción nativa de Windows."

    hive = _get_hive_handle(hive_name)
    if hive is None:
        return False, f"Rama de registro inválida: {hive_name}"

    try:
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                try:
                    winreg.DeleteValue(key, "LegacyDisable")
                except FileNotFoundError:
                    pass
                return True, f"Entrada '{key_leaf}' reactivada en el menú contextual."
            else:
                winreg.SetValueEx(key, "LegacyDisable", 0, winreg.REG_SZ, "")
                return True, f"Entrada '{key_leaf}' ocultada del menú contextual (reversible)."
    except PermissionError:
        return False, "Permiso denegado. Ejecuta PyClean Pro como Administrador para modificar entradas del sistema."
    except OSError as e:
        return False, f"Error modificando el Registro: {e}"
