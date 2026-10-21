"""
PyClean Pro v2.0 - Punto de Entrada Principal
Permite ejecutar en Modo Gráfico (GUI) o Modo Consola (CLI) con soporte para automatización y JSON.
"""

import sys
import argparse
import json
import cleaner

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
    target_drive = args.drive.upper() if args.drive else "C:\\"
    if not target_drive.endswith("\\"):
        target_drive += "\\"

    if args.json:
        # Salida estructurada JSON para automatización
        result = {
            "is_admin": cleaner.is_admin(),
            "stats": cleaner.get_system_stats(drive=target_drive),
            "drives": cleaner.get_system_drives(),
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

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Salida estándar legible para humanos
    print("=" * 65)
    print("           ⚡ PyClean Pro v2.0 - Modo Consola (CLI)")
    print("=" * 65)

    admin_status = "Administrador" if cleaner.is_admin() else "Usuario Estándar (limitado)"
    print(f"Privilegios actuales: {admin_status}")
    print(f"Filtro de seguridad: Archivos temporales < {min_age}h serán conservados.\n")

    stats = cleaner.get_system_stats(drive=target_drive)
    free_gb = stats["disk_free"] / (1024 ** 3)
    total_gb = stats["disk_total"] / (1024 ** 3)
    print(f"Disco {target_drive[:2]} {free_gb:.1f} GB libres de {total_gb:.1f} GB ({stats['disk_percent']}% en uso)")
    print(f"Memoria RAM en uso: {stats['ram_load']}%\n")

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

    if args.scan or args.dry_run:
        print("[+] Escaneando archivos basura...")
        total_size = 0
        total_files = 0
        for cat_key, cat_data in categories.items():
            size, count, _ = cleaner.scan_category(cat_key, cat_data, min_age_hours=min_age, exclusions=exclusions)
            total_size += size
            total_files += count
            if size > 0:
                print(f"    • {cat_data['name']:<40}: {cleaner.format_size(size):>10} ({count:,} archivos)")
        print(f"\nTotal recuperable: {cleaner.format_size(total_size)} en {total_files:,} archivos.\n")

    if args.clean or args.all:
        print("[+] Limpiando archivos basura...")
        total_freed = 0
        total_deleted = 0
        total_skipped = 0
        for cat_key, cat_data in categories.items():
            freed, deleted, skipped = cleaner.clean_category(cat_key, cat_data, min_age_hours=min_age, exclusions=exclusions)
            total_freed += freed
            total_deleted += deleted
            total_skipped += skipped
            if freed > 0 or deleted > 0:
                print(f"    ✔ {cat_data['name']:<40}: {cleaner.format_size(freed):>10} ({deleted} eliminados, {skipped} protegidos)")
        print(f"\n✨ Limpieza finalizada: {cleaner.format_size(total_freed)} liberados.")
        print(f"   Archivos eliminados: {total_deleted:,} | Omitidos (bloqueados o recientes): {total_skipped:,}\n")


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
    import tkinter as tk
    from gui import PyCleanGUI

    root = tk.Tk()
    app = PyCleanGUI(root)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(
        description="PyClean Pro v2.0 - Suite de limpieza y optimización para Windows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ejemplos:\n"
               "  python main.py              (Abre la interfaz moderna animada con GSAP)\n"
               "  python main.py --legacy-gui (Abre la interfaz gráfica clásica de Tkinter)\n"
               "  python main.py --scan       (Analiza el espacio basura sin borrar nada)\n"
               "  python main.py --clean      (Limpia los archivos basura directamente)\n"
               "  python main.py --startup    (Lista los programas de inicio en consola)\n"
               "  python main.py --json --scan(Genera un informe estructurado en formato JSON)\n"
               "  python main.py --ram        (Optimiza y libera memoria RAM)\n"
               "  python main.py --dns        (Vacía la caché DNS)\n"
               "  python main.py --all        (Optimiza RAM, DNS y limpia todo)"
    )
    parser.add_argument("--scan", action="store_true", help="Escanear y mostrar espacio recuperable")
    parser.add_argument("--clean", action="store_true", help="Eliminar archivos basura")
    parser.add_argument("--dry-run", action="store_true", help="Simular limpieza mostrando qué se eliminaría")
    parser.add_argument("--ram", action="store_true", help="Liberar y optimizar memoria RAM")
    parser.add_argument("--dns", action="store_true", help="Vaciar caché de resolución DNS")
    parser.add_argument("--startup", action="store_true", help="Listar programas de inicio automático de Windows")
    parser.add_argument("--drive", type=str, default="C:\\", help="Unidad de disco a analizar (ej. C:\\ o D:\\)")
    parser.add_argument("--json", action="store_true", help="Emitir resultados en formato JSON estructurado")
    parser.add_argument("--all", action="store_true", help="Ejecutar escaneo, limpieza, optimización de RAM y DNS")
    parser.add_argument("--cli", action="store_true", help="Forzar modo consola interactivo")
    parser.add_argument("--legacy-gui", action="store_true", help="Abrir la interfaz clásica basada en Tkinter")

    args = parser.parse_args()

    if args.legacy_gui:
        run_gui()
    elif args.scan or args.clean or args.dry_run or args.ram or args.dns or args.startup or args.all or args.cli or args.json:
        run_cli(args)
    else:
        run_modern_gui()


if __name__ == "__main__":
    main()
