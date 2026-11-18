"""
PyClean Pro - Script de Compilación a Ejecutable (.exe)
Empaqueta toda la suite (incluyendo assets web y GSAP) en un único binario ejecutable portable.
"""

import os
import sys
import subprocess
import shutil

try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def build():
    print("=" * 60)
    print("      PyClean Pro - Compilador PyInstaller a .exe")
    print("=" * 60)

    try:
        import PyInstaller
    except ImportError:
        print("[!] PyInstaller no está instalado. Instalándolo en el entorno...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(base_dir, "main.py")
    web_dir = os.path.join(base_dir, "web")
    icon_path = os.path.join(base_dir, "assets", "pyclean_icon.ico")
    version_file = os.path.join(base_dir, "version_info.txt")

    # Separador de add-data según sistema operativo (; en Windows, : en Unix)
    sep = ";" if sys.platform == "win32" else ":"
    data_arg = f"{web_dir}{sep}web"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=PyCleanPro",
        "--onefile",
        "--windowed",
        f"--add-data={data_arg}",
        "--clean",
    ]

    if os.path.exists(icon_path):
        cmd.append(f"--icon={icon_path}")

    if sys.platform == "win32" and os.path.exists(version_file):
        cmd.append(f"--version-file={version_file}")

    cmd.append(main_script)

    print(f"\n[+] Ejecutando comando de compilación:\n{' '.join(cmd)}\n")
    res = subprocess.run(cmd)

    if res.returncode == 0:
        exe_ext = ".exe" if sys.platform == "win32" else ""
        dist_path = os.path.join(base_dir, "dist", f"PyCleanPro{exe_ext}")
        print("\n" + "=" * 60)
        print("¡Compilación exitosa!")
        print(f"Ejecutable disponible en: {dist_path}")
        print("=" * 60)
    else:
        print(f"\nError durante la compilación (código {res.returncode}).")
        sys.exit(res.returncode)

if __name__ == "__main__":
    build()
