"""
PyClean Pro v2.1 - Punto de Entrada Principal
Permite ejecutar en Modo Gráfico (GUI) o Modo Consola (CLI) con soporte para
automatización, exportación de reportes, triturador seguro y buscador de duplicados.
"""

from __future__ import annotations

import os
import sys
import argparse
import json
import cleaner
import sys_monitor
import hardware_health
import context_menu

# Configurar salida de terminal en UTF-8 para Windows
try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def run_cli(args):
    """Ejecuta operaciones directamente desde la terminal."""
    config = cleaner.load_config()
    min_age = config.get("min_age_hours", 24)
    exclusions = config.get("exclusions", [])
    target_drive = args.drive.upper() if args.drive else ("C:\\" if sys.platform == "win32" else "/")
    if sys.platform == "win32" and not target_drive.endswith("\\"):
        target_drive += "\\"

    # Operación independiente: Triturar archivo
    if args.shred:
        passes = max(1, args.shred_passes) if hasattr(args, "shred_passes") and args.shred_passes else 1
        print(f"[!] Triturando de forma segura: {args.shred} ({passes} pasada(s))...")
        ok, msg = cleaner.shred_file(args.shred, passes=passes)
        if ok:
            print(f"    ✔ {msg}\n")
        else:
            print(f"    ❌ {msg}\n")
        return

    # Operación independiente: Buscador de duplicados
    if args.duplicates:
        print(f"[+] Buscando archivos duplicados en: {args.duplicates}...")
        dups = cleaner.find_duplicate_files(args.duplicates, min_size_bytes=1024)
        if not dups:
            print("    ✔ No se encontraron archivos duplicados.\n")
        else:
            total_wasted = sum(d["wasted_bytes"] for d in dups)
            print(f"    Encontrados {len(dups)} grupos de duplicados. Espacio desperdiciado: {cleaner.format_size(total_wasted)}.\n")
            for i, group in enumerate(dups[:20], 1):
                print(f"    [{i}] Hash: {group['hash'][:10]}... | Tamaño c/u: {group['size_formatted']} | Desperdicio: {group['wasted_formatted']}")
                for f in group["files"]:
                    print(f"        • {f}")
            if len(dups) > 20:
                print(f"\n    ... y {len(dups) - 20} grupos más.")
            print()
        return

    # Operación independiente: Listar aplicaciones instaladas
    if args.apps:
        print("[+] Listando aplicaciones instaladas en el sistema:")
        apps = cleaner.get_installed_apps()
        if not apps:
            print("    (No se encontraron aplicaciones o la plataforma no es Windows).\n")
        else:
            for a in apps:
                ver_str = f"v{a['version']}" if a['version'] else ""
                size_str = f"[{a['size_formatted']}]" if a['size_bytes'] > 0 else ""
                print(f"    • {a['name']:<40} {ver_str:<15} {size_str}")
            print(f"\nTotal: {len(apps)} aplicaciones encontradas.\n")
        return

    # Operación independiente: Auditor de descargas antiguas
    if args.downloads_audit is not None:
        days = args.downloads_audit if args.downloads_audit > 0 else 30
        print(f"[+] Auditando instaladores y archivos pesados en Descargas (> {days} días):")
        old_downloads = cleaner.audit_old_downloads(min_age_days=days)
        if not old_downloads:
            print(f"    ✔ No se encontraron instaladores de más de {days} días.\n")
        else:
            total_size = sum(d["size"] for d in old_downloads)
            print(f"    Encontrados {len(old_downloads)} archivos ocupando {cleaner.format_size(total_size)}:")
            for d in old_downloads:
                print(f"    • [{d['size_formatted']:>10}] ({d['days_old']} días) {d['name']}")
            print()
        return

    # Operación independiente: Programador de mantenimiento
    if args.schedule:
        state_bool = args.schedule.lower() in ("on", "true", "enable", "habilitar", "1")
        ok, msg = cleaner.set_scheduled_task(state_bool, frequency="weekly")
        status_tag = "✔" if ok else "❌"
        print(f"[{status_tag}] Tarea Programada: {msg}\n")
        return

    # Operación independiente: Optimizar telemetría
    if args.privacy:
        disable_bool = args.privacy.lower() in ("on", "true", "disable", "mitigar", "1")
        ok, msg = cleaner.toggle_telemetry(disable_bool)
        status_tag = "✔" if ok else "❌"
        print(f"[{status_tag}] Privacidad y Telemetría: {msg}\n")
        return

    # Salida estructurada JSON para automatización
    if args.json:
        result = {
            "is_admin": cleaner.is_admin(),
            "stats": cleaner.get_system_stats(drive=target_drive),
            "drives": cleaner.get_system_drives(),
            "locked_apps": cleaner.get_running_locked_apps(),
            "actions": {}
        }
        categories = cleaner.get_target_categories()

        if args.ram or args.all:
            result["actions"]["ram_freed_processes"] = cleaner.optimize_ram()

        if args.dns or args.all:
            ok, msg = cleaner.flush_dns()
            result["actions"]["dns_flushed"] = ok
            result["actions"]["dns_message"] = msg

        if args.scan or args.dry_run:
            scan_results = {}
            total_size = 0
            total_files = 0
            for k, data in categories.items():
                sz, cnt, _ = cleaner.scan_category(k, data, min_age_hours=min_age, exclusions=exclusions)
                total_size += sz
                total_files += cnt
                if sz > 0:
                    scan_results[k] = {"name": data["name"], "size_bytes": sz, "size_formatted": cleaner.format_size(sz), "files": cnt}
            result["actions"]["scan"] = {
                "total_bytes": total_size,
                "total_formatted": cleaner.format_size(total_size),
                "total_files": total_files,
                "categories": scan_results
            }

        if args.clean or args.all:
            clean_results = {}
            total_freed = 0
            total_del = 0
            total_skip = 0
            for k, data in categories.items():
                freed, deleted, skipped = cleaner.clean_category(k, data, min_age_hours=min_age, exclusions=exclusions)
                total_freed += freed
                total_del += deleted
                total_skip += skipped
                if freed > 0 or deleted > 0:
                    clean_results[k] = {"freed_bytes": freed, "freed_formatted": cleaner.format_size(freed), "deleted": deleted, "skipped": skipped}
            result["actions"]["clean"] = {
                "total_freed_bytes": total_freed,
                "total_freed_formatted": cleaner.format_size(total_freed),
                "total_deleted": total_del,
                "total_skipped": total_skip,
                "categories": clean_results
            }

        if args.startup:
            result["actions"]["startup_programs"] = cleaner.get_startup_programs()

        if args.partitions:
            result["actions"]["partitions"] = cleaner.get_partitions_detailed()

        if args.largest is not None:
            target_dir = args.largest if os.path.exists(args.largest) else ("C:\\" if sys.platform == "win32" else "/")
            result["actions"]["largest_files"] = cleaner.find_largest_files(target_dir, min_size_mb=100, limit=50)

        if args.processes:
            result["actions"]["processes"] = sys_monitor.get_top_processes(sort_by="memory", limit=25)

        if args.hardware:
            result["actions"]["hardware"] = {
                "disks": hardware_health.get_disk_health(),
                "battery": hardware_health.get_battery_health(),
            }

        if args.context_menu:
            result["actions"]["context_menu"] = context_menu.get_context_menu_items()

        if args.export:
            cleaner.export_report(result, args.export, format_type="json")

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Salida estándar legible para humanos
    print("=" * 65)
    print("           ⚡ PyClean Pro v2.4 - Modo Consola (CLI)")
    print("=" * 65)

    admin_status = "Administrador" if cleaner.is_admin() else "Usuario Estándar (limitado)"
    print(f"Privilegios actuales: {admin_status}")
    print(f"Filtro de seguridad: Archivos temporales < {min_age}h serán conservados.\n")

    # Auditoría de procesos que bloquean limpieza
    locked = cleaner.get_running_locked_apps()
    if locked:
        print("[!] Advertencia: Las siguientes aplicaciones están en ejecución y bloquean archivos de caché:")
        for app in locked:
            print(f"    ⚠️ {app['name']} ({app['process']})")
        print("    (Para una limpieza 100% efectiva de navegadores, ciérralos antes de limpiar).\n")

    stats = cleaner.get_system_stats(drive=target_drive)
    free_gb = stats["disk_free"] / (1024 ** 3)
    total_gb = stats["disk_total"] / (1024 ** 3)
    drive_label = target_drive[:2] if len(target_drive) >= 2 else target_drive
    print(f"Disco {drive_label}: {free_gb:.1f} GB libres de {total_gb:.1f} GB ({stats['disk_percent']}% en uso)")
    print(f"Memoria RAM en uso: {stats['ram_load']}%\n")

    if args.partitions:
        parts = cleaner.get_partitions_detailed()
        print("[+] Particiones y unidades de disco detectadas:")
        for p in parts:
            print(f"    • [{p['letter']}] {p['label']:<18} | {p['fs']:<6} | {p['type']:<15} | Libre: {p['free_formatted']:>9} ({p['percent']}% en uso)")
        print()

    if args.largest is not None:
        target_dir = args.largest if os.path.exists(args.largest) else ("C:\\" if sys.platform == "win32" else "/")
        print(f"[+] Buscando archivos gigantes en {target_dir}...")
        files = cleaner.find_largest_files(target_dir, min_size_mb=100, limit=20)
        if not files:
            print("    ✔ No se encontraron archivos superiores a 100 MB.\n")
        else:
            for f in files:
                print(f"    • {f['size_formatted']:>10} | {f['name']}")
                print(f"      {f['path']}")
            print()

    if args.processes:
        procs = sys_monitor.get_top_processes(sort_by="memory", limit=20)
        print("[+] Top 20 Procesos por consumo de RAM:")
        for pr in procs:
            tag = "[SO]" if pr["is_critical"] else "    "
            print(f"    {tag} PID {pr['pid']:<6} | {pr['memory_formatted']:>10} | CPU {pr['cpu_percent']:>5}% | {pr['name']}")
        print()

    if args.hardware:
        disks = hardware_health.get_disk_health()
        batt = hardware_health.get_battery_health()
        print("[+] Salud de Discos Físicos (S.M.A.R.T.):")
        for d in disks:
            print(f"    • {d['name']} ({d['media_type']}) -> Salud: {d['health_status']} | {d['size_formatted']}")
        if batt.get("has_battery"):
            hp = batt.get("health_percent")
            hp_str = f"{hp}% (desgaste {batt.get('wear_percent')}%)" if hp is not None else "N/A"
            print(f"\n[+] Batería: {batt.get('percent')}% | Salud real: {hp_str} | Ciclos: {batt.get('cycle_count', 0)}\n")
        else:
            print("\n[+] Batería: Equipo de escritorio (sin batería).\n")

    if args.context_menu:
        cm_items = context_menu.get_context_menu_items()
        print(f"[+] Entradas del Menú Contextual ({len(cm_items)} detectadas):")
        for c in cm_items[:30]:
            st = "✔ Activo" if c["enabled"] else "❌ Oculto"
            print(f"    • [{st}] {c['label']:<30} ({c['scope']})")
        print()

    if args.startup:
        print("[+] Programas configurados para iniciar con Windows:")
        progs = cleaner.get_startup_programs()
        for p in progs:
            status = "✔ Habilitado" if p["enabled"] else "❌ Deshabilitado"
            print(f"    • [{status}] {p['name']:<25} ({p['scope']}) -> {p['command'][:50]}")
        print(f"\nTotal: {len(progs)} entradas encontradas.\n")

    categories = cleaner.get_target_categories()

    if args.ram or args.all:
        print("[+] Optimizando memoria RAM...")
        procs = cleaner.optimize_ram()
        print(f"    ✔ Memoria compactada en {procs} procesos.\n")

    if args.dns or args.all:
        print("[+] Limpiando caché DNS...")
        success, msg = cleaner.flush_dns()
        if success:
            print("    ✔ Caché DNS vaciada con éxito.\n")
        else:
            print(f"    ⚠️ Aviso DNS: {msg}\n")

    action_report = {}

    if args.scan or args.dry_run:
        print("[+] Escaneando archivos basura...")
        total_size = 0
        total_files = 0
        cat_report = {}
        for cat_key, cat_data in categories.items():
            size, count, _ = cleaner.scan_category(cat_key, cat_data, min_age_hours=min_age, exclusions=exclusions)
            total_size += size
            total_files += count
            if size > 0:
                print(f"    • {cat_data['name']:<45}: {cleaner.format_size(size):>10} ({count:,} archivos)")
                cat_report[cat_key] = {"name": cat_data["name"], "size_formatted": cleaner.format_size(size), "count": count}
        print(f"\nTotal recuperable: {cleaner.format_size(total_size)} en {total_files:,} archivos.\n")
        action_report = {
            "total_formatted": cleaner.format_size(total_size),
            "total_files": total_files,
            "categories": cat_report
        }

    if args.clean or args.all:
        print("[+] Limpiando archivos basura...")
        total_freed = 0
        total_deleted = 0
        total_skipped = 0
        cat_clean_report = {}
        for cat_key, cat_data in categories.items():
            freed, deleted, skipped = cleaner.clean_category(cat_key, cat_data, min_age_hours=min_age, exclusions=exclusions)
            total_freed += freed
            total_deleted += deleted
            total_skipped += skipped
            if freed > 0 or deleted > 0:
                print(f"    ✔ {cat_data['name']:<45}: {cleaner.format_size(freed):>10} ({deleted} eliminados, {skipped} protegidos)")
                cat_clean_report[cat_key] = {"name": cat_data["name"], "freed_formatted": cleaner.format_size(freed), "deleted": deleted, "skipped": skipped}
        print(f"\n✨ Limpieza finalizada: {cleaner.format_size(total_freed)} liberados.")
        print(f"   Archivos eliminados: {total_deleted:,} | Omitidos (bloqueados o recientes): {total_skipped:,}\n")
        action_report = {
            "total_freed_formatted": cleaner.format_size(total_freed),
            "total_deleted": total_deleted,
            "total_skipped": total_skipped,
            "categories": cat_clean_report
        }

    if args.export and action_report:
        ext = "txt" if args.export.endswith(".txt") else "json"
        cleaner.export_report(action_report, args.export, format_type=ext)
        print(f"📄 Reporte exportado a: {args.export}\n")


def run_modern_gui():
    """Lanza la interfaz gráfica moderna impulsada por PyWebView + GSAP."""
    try:
        from web_gui import run_web_gui
        run_web_gui()
    except Exception as e:
        print(f"[!] Aviso: No se pudo iniciar la interfaz web GSAP ({e}). Iniciando interfaz clásica Tkinter...")
        run_gui()


def run_gui():
    """Lanza la interfaz gráfica clásica en Tkinter."""
    try:
        import tkinter as tk
        from gui import PyCleanGUI

        root = tk.Tk()
        app = PyCleanGUI(root)
        root.mainloop()
    except Exception as e:
        print(f"[!] No se pudo iniciar Tkinter ({e}). Ejecuta en modo CLI con --scan o --clean.")


def main():
    parser = argparse.ArgumentParser(
        description="PyClean Pro v2.1 - Suite de limpieza, optimización y privacidad para Windows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ejemplos:\n"
               "  python main.py                     (Abre la interfaz moderna animada con GSAP)\n"
               "  python main.py --scan              (Analiza el espacio basura sin borrar nada)\n"
               "  python main.py --clean             (Limpia los archivos basura directamente)\n"
               "  python main.py --shred archivo.txt (Tritura un archivo confidencial de forma irrecuperable)\n"
               "  python main.py --duplicates D:\\Docs(Busca archivos duplicados por contenido SHA-256)\n"
               "  python main.py --export rep.txt    (Exporta el resultado a archivo de texto o json)\n"
               "  python main.py --ram --dns         (Optimiza memoria RAM y vacía DNS)\n"
               "  python main.py --all               (Optimiza RAM, DNS y limpia todo)"
    )
    parser.add_argument("--scan", action="store_true", help="Escanear y mostrar espacio recuperable")
    parser.add_argument("--clean", action="store_true", help="Eliminar archivos basura")
    parser.add_argument("--dry-run", action="store_true", help="Simular limpieza mostrando qué se eliminaría")
    parser.add_argument("--ram", action="store_true", help="Liberar y optimizar memoria RAM")
    parser.add_argument("--dns", action="store_true", help="Vaciar caché de resolución DNS")
    parser.add_argument("--startup", action="store_true", help="Listar programas de inicio automático de Windows")
    parser.add_argument("--drive", type=str, default="C:\\", help="Unidad de disco a analizar (ej. C:\\ o D:\\)")
    parser.add_argument("--shred", type=str, metavar="FILE", help="Triturar y destruir un archivo de forma segura")
    parser.add_argument("--shred-passes", type=int, default=1, help="Número de pasadas de sobreescritura al triturar (default: 1)")
    parser.add_argument("--duplicates", type=str, metavar="DIR", help="Buscar archivos duplicados en el directorio especificado")
    parser.add_argument("--apps", action="store_true", help="Listar programas y aplicaciones instaladas en Windows")
    parser.add_argument("--downloads-audit", type=int, nargs="?", const=30, metavar="DAYS", help="Auditar instaladores pesados en Descargas con más de X días (default: 30)")
    parser.add_argument("--schedule", type=str, choices=["on", "off"], metavar="STATE", help="Activar o desactivar tarea semanal de mantenimiento automático (on/off)")
    parser.add_argument("--privacy", type=str, choices=["on", "off"], metavar="STATE", help="Mitigar o restaurar telemetría y diagnósticos de Windows (on/off)")
    parser.add_argument("--partitions", action="store_true", help="Mostrar información detallada de particiones y unidades de disco")
    parser.add_argument("--largest", type=str, nargs="?", const="C:\\", metavar="DIR", help="Buscar archivos gigantes en el directorio o unidad (ej. --largest D:\\)")
    parser.add_argument("--processes", action="store_true", help="Listar los procesos que más memoria RAM y CPU consumen")
    parser.add_argument("--hardware", action="store_true", help="Mostrar salud S.M.A.R.T. de discos SSD/HDD y estado de batería")
    parser.add_argument("--context-menu", action="store_true", help="Listar entradas del menú contextual (clic derecho) de Windows")
    parser.add_argument("--export", type=str, metavar="PATH", help="Ruta donde exportar el informe de resultados (.json o .txt)")
    parser.add_argument("--json", action="store_true", help="Emitir resultados en formato JSON estructurado")
    parser.add_argument("--all", action="store_true", help="Ejecutar escaneo, limpieza, optimización de RAM y DNS")
    parser.add_argument("--cli", action="store_true", help="Forzar modo consola interactivo")
    parser.add_argument("--legacy-gui", action="store_true", help="Abrir la interfaz clásica basada en Tkinter")

    args = parser.parse_args()

    if args.legacy_gui:
        run_gui()
    elif (
        args.scan
        or args.clean
        or args.dry_run
        or args.ram
        or args.dns
        or args.startup
        or args.all
        or args.cli
        or args.json
        or args.shred
        or args.duplicates
        or args.apps
        or (args.downloads_audit is not None)
        or args.schedule
        or args.privacy
        or args.partitions
        or (args.largest is not None)
        or args.processes
        or args.hardware
        or args.context_menu
    ):
        run_cli(args)
    else:
        run_modern_gui()


if __name__ == "__main__":
    main()
