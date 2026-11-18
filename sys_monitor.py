"""
PyClean Pro v2.4 - Monitor de Procesos y Red en Tiempo Real
Provee listado de procesos con consumo de CPU/RAM, terminación segura,
gestión rápida de servidores DNS en Windows y pruebas de latencia (ping).
"""

from __future__ import annotations

import os
import re
import sys
import subprocess
import cleaner

try:
    import psutil
except ImportError:
    psutil = None


# Procesos críticos del sistema operativo protegidos contra terminación accidental
CRITICAL_PROCESSES = {
    "system",
    "system idle process",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "lsaiso.exe",
    "winlogon.exe",
    "svchost.exe",
    "dwm.exe",
    "explorer.exe",
    "fontdrvhost.exe",
    "memory compression",
    "ntoskrnl.exe",
    "init",
    "systemd",
}

DNS_PRESETS = {
    "auto": {"name": "Automático (DHCP)", "primary": None, "secondary": None},
    "cloudflare": {"name": "Cloudflare (Rápido / Privado)", "primary": "1.1.1.1", "secondary": "1.0.0.1"},
    "google": {"name": "Google Public DNS", "primary": "8.8.8.8", "secondary": "8.8.4.4"},
    "adguard": {"name": "AdGuard (Bloqueo de Anuncios)", "primary": "94.140.14.14", "secondary": "94.140.15.15"},
}


def is_critical_process(name: str, pid: int) -> bool:
    """Retorna True si el proceso es crítico para la estabilidad del sistema operativo."""
    if pid in (0, 1, 4):
        return True
    if not name:
        return True
    return name.strip().lower() in CRITICAL_PROCESSES


def get_top_processes(sort_by: str = "memory", limit: int = 35) -> list[dict]:
    """
    Obtiene los procesos con mayor consumo de RAM o CPU usando psutil.
    Retorna una lista de diccionarios ordenada descendentemente.
    """
    if psutil is None:
        return []

    procs = []
    my_pid = os.getpid()

    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
        try:
            info = proc.info
            pid = info.get("pid", 0)
            name = info.get("name") or f"PID {pid}"
            mem_info = info.get("memory_info")
            mem_bytes = mem_info.rss if mem_info else 0
            cpu_pct = round(float(info.get("cpu_percent") or 0.0), 1)
            critical = is_critical_process(name, pid) or (pid == my_pid)

            procs.append({
                "pid": pid,
                "name": name,
                "cpu_percent": cpu_pct,
                "memory_bytes": mem_bytes,
                "memory_formatted": cleaner.format_size(mem_bytes),
                "status": info.get("status") or "running",
                "is_critical": critical,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    key_fn = (lambda p: p["cpu_percent"]) if sort_by == "cpu" else (lambda p: p["memory_bytes"])
    procs.sort(key=key_fn, reverse=True)
    return procs[: max(1, limit)]


def terminate_process(pid: int) -> tuple[bool, str]:
    """Termina de forma segura un proceso por PID, bloqueando procesos críticos del SO."""
    if psutil is None:
        return False, "psutil no está disponible en este entorno."

    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return False, "PID inválido."

    if pid_int == os.getpid():
        return False, "No puedes finalizar la propia aplicación PyClean Pro."

    try:
        proc = psutil.Process(pid_int)
        name = proc.name()
        if is_critical_process(name, pid_int):
            return False, f"Proceso protegido del sistema ({name}). No se permite finalizarlo."

        proc.terminate()
        try:
            proc.wait(timeout=3)
        except psutil.TimeoutExpired:
            proc.kill()
        return True, f"Proceso '{name}' (PID {pid_int}) finalizado correctamente."
    except psutil.NoSuchProcess:
        return False, f"El proceso con PID {pid_int} ya no existe."
    except psutil.AccessDenied:
        return False, f"Acceso denegado para finalizar PID {pid_int}. Ejecuta como Administrador."
    except Exception as e:
        return False, f"Error finalizando proceso: {e}"


def get_network_interfaces() -> list[dict]:
    """Obtiene los adaptadores de red activos con su IP local y contadores de tráfico."""
    if psutil is None:
        return []

    interfaces = []
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        io_counters = psutil.net_io_counters(pernic=True)

        for iface_name, addr_list in addrs.items():
            st = stats.get(iface_name)
            is_up = bool(st.isup) if st else False
            if not is_up:
                continue

            ipv4 = ""
            for addr in addr_list:
                # AF_INET = 2
                if getattr(addr.family, "name", "") == "AF_INET" or addr.family == 2:
                    if not addr.address.startswith("127."):
                        ipv4 = addr.address
                        break

            if not ipv4:
                continue

            io = io_counters.get(iface_name)
            sent = io.bytes_sent if io else 0
            recv = io.bytes_recv if io else 0

            interfaces.append({
                "name": iface_name,
                "ip": ipv4,
                "speed_mbps": st.speed if st else 0,
                "bytes_sent": sent,
                "bytes_recv": recv,
                "sent_formatted": cleaner.format_size(sent),
                "recv_formatted": cleaner.format_size(recv),
            })
    except Exception:
        pass

    return interfaces


def set_dns_preset(adapter_name: str, preset: str) -> tuple[bool, str]:
    """
    Aplica un perfil DNS preconfigurado a un adaptador de red en Windows mediante netsh.
    Requiere privilegios de Administrador.
    """
    if preset not in DNS_PRESETS:
        return False, f"Perfil DNS desconocido: {preset}"

    if not adapter_name or not adapter_name.strip():
        return False, "Debes seleccionar un adaptador de red válido."

    if sys.platform != "win32":
        return False, "El cambio de DNS mediante netsh solo está disponible en Windows."

    safe_adapter = adapter_name.strip()
    cfg = DNS_PRESETS[preset]

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        if preset == "auto":
            cmd = ["netsh", "interface", "ip", "set", "dns", f"name={safe_adapter}", "source=dhcp"]
            res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
            if res.returncode != 0:
                err = (res.stderr or res.stdout or "").strip()
                return False, f"No se pudo cambiar a DHCP (¿ejecutaste como Admin?): {err}"
            cleaner.flush_dns()
            return True, f"DNS de '{safe_adapter}' restaurado a Automático (DHCP)."

        primary = cfg["primary"]
        secondary = cfg["secondary"]

        cmd1 = ["netsh", "interface", "ip", "set", "dns", f"name={safe_adapter}", "static", primary]
        res1 = subprocess.run(cmd1, capture_output=True, text=True, startupinfo=startupinfo)
        if res1.returncode != 0:
            err = (res1.stderr or res1.stdout or "").strip()
            return False, f"Fallo al configurar DNS primario (requiere Admin): {err}"

        if secondary:
            cmd2 = ["netsh", "interface", "ip", "add", "dns", f"name={safe_adapter}", secondary, "index=2"]
            subprocess.run(cmd2, capture_output=True, text=True, startupinfo=startupinfo)

        cleaner.flush_dns()
        return True, f"DNS de '{safe_adapter}' cambiado a {cfg['name']} ({primary} / {secondary})."
    except Exception as e:
        return False, f"Error aplicando perfil DNS: {e}"


def run_ping_test(targets: list[str] = None) -> list[dict]:
    """Ejecuta una prueba rápida de latencia (ping) a servidores de referencia."""
    targets = targets or [
        {"label": "Cloudflare DNS", "host": "1.1.1.1"},
        {"label": "Google DNS", "host": "8.8.8.8"},
        {"label": "GitHub", "host": "github.com"},
    ]

    results = []
    is_win = sys.platform == "win32"

    for t in targets:
        if isinstance(t, str):
            label, host = t, t
        else:
            label = t.get("label", t.get("host", ""))
            host = t.get("host", "")

        # Validar host para seguridad
        if not re.match(r"^[a-zA-Z0-9.\-]+$", host):
            continue

        cmd = ["ping", "-n", "2", "-w", "1500", host] if is_win else ["ping", "-c", "2", "-W", "2", host]
        kwargs = {"capture_output": True, "text": True, "timeout": 6}
        if is_win:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs["startupinfo"] = si

        latency_ms = None
        reachable = False
        try:
            res = subprocess.run(cmd, **kwargs)
            out = res.stdout or ""
            # Buscar tiempos en formato Windows (tiempo=12ms / time=12ms / time<1ms) o Linux (time=12.3 ms)
            matches = re.findall(r"(?:time|tiempo)[=<]\s*([\d.]+)\s*ms", out, flags=re.IGNORECASE)
            if matches:
                vals = [float(m) for m in matches]
                latency_ms = round(sum(vals) / len(vals), 1)
                reachable = True
            elif res.returncode == 0:
                reachable = True
                latency_ms = 1.0
        except Exception:
            reachable = False

        results.append({
            "label": label,
            "host": host,
            "reachable": reachable,
            "latency_ms": latency_ms,
        })

    return results
