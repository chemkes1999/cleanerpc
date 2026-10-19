"""
PyClean Pro - Punto de Entrada Principal
Permite ejecutar en Modo Gráfico (GUI) o Modo Consola (CLI).
"""

import sys
import argparse
import cleaner

# Configurar salida de terminal en UTF-8 para Windows
try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def run_cli(args):
    """Ejecuta operaciones directamente desde la terminal."""
    print("=" * 60)
    print("           PyClean Pro - Modo Consola (CLI)")
    print("=" * 60)

    admin_status = "Administrador" if cleaner.is_admin() else "Usuario Estándar (limitado)"
    print(f"Privilegios actuales: {admin_status}\n")

    stats = cleaner.get_system_stats()
    free_gb = stats["disk_free"] / (1024 ** 3)
    total_gb = stats["disk_total"] / (1024 ** 3)
    print(f"Disco C: {free_gb:.1f} GB libres de {total_gb:.1f} GB ({stats['disk_percent']}% en uso)")
    print(f"Memoria RAM en uso: {stats['ram_load']}%\n")

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

    if args.scan:
        print("[+] Escaneando archivos basura...")
        total_size = 0
        total_files = 0
        for cat_key, cat_data in categories.items():
            size, count, _ = cleaner.scan_category(cat_key, cat_data)
            total_size += size
            total_files += count
            if size > 0:
                print(f"    • {cat_data['name']:<30}: {cleaner.format_size(size):>10} ({count:,} archivos)")
        print(f"\nTotal recuperable: {cleaner.format_size(total_size)} en {total_files:,} archivos.\n")

    if args.clean or args.all:
        print("[+] Limpiando archivos basura...")
        total_freed = 0
        total_deleted = 0
        total_skipped = 0
        for cat_key, cat_data in categories.items():
            freed, deleted, skipped = cleaner.clean_category(cat_key, cat_data)
            total_freed += freed
            total_deleted += deleted
            total_skipped += skipped
            if freed > 0 or deleted > 0:
                print(f"    ✔ {cat_data['name']:<30}: {cleaner.format_size(freed):>10} ({deleted} eliminados, {skipped} en uso)")
        print(f"\n✨ Limpieza finalizada: {cleaner.format_size(total_freed)} liberados.")
        print(f"   Archivos eliminados: {total_deleted:,} | Omitidos (bloqueados): {total_skipped:,}\n")


def run_gui():
    """Lanza la interfaz gráfica moderna."""
    import tkinter as tk
    from gui import PyCleanGUI

    root = tk.Tk()
    app = PyCleanGUI(root)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(
        description="PyClean Pro - Limpiador y optimizador de archivos basura para Windows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ejemplos:\n"
               "  python main.py              (Abre la interfaz gráfica moderna)\n"
               "  python main.py --scan       (Analiza el espacio basura sin borrar nada)\n"
               "  python main.py --clean      (Limpia los archivos basura directamente)\n"
               "  python main.py --ram        (Optimiza y libera memoria RAM)\n"
               "  python main.py --dns        (Vacía la caché DNS)\n"
               "  python main.py --all        (Optimiza RAM, DNS y limpia todo)"
    )
    parser.add_argument("--scan", action="store_true", help="Escanear y mostrar espacio recuperable")
    parser.add_argument("--clean", action="store_true", help="Eliminar archivos basura")
    parser.add_argument("--ram", action="store_true", help="Liberar y optimizar memoria RAM")
    parser.add_argument("--dns", action="store_true", help="Vaciar caché de resolución DNS")
    parser.add_argument("--all", action="store_true", help="Ejecutar escaneo, limpieza, optimización de RAM y DNS")
    parser.add_argument("--cli", action="store_true", help="Forzar modo consola interactivo")

    args = parser.parse_args()

    # Si se pasó algún flag CLI, ejecutar en consola
    if args.scan or args.clean or args.ram or args.dns or args.all or args.cli:
        run_cli(args)
    else:
        # Por defecto, abrir la interfaz gráfica
        run_gui()


if __name__ == "__main__":
    main()
