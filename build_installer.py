"""
PyClean Pro v2.3 - Compilador de Instalador Windows (.exe)
Automatiza la creación de PyCleanPro-Setup.exe utilizando Inno Setup (ISCC).
"""

import os
import sys
import shutil
import subprocess

def find_iscc():
    """Busca el ejecutable de Inno Setup Compiler (ISCC.exe)."""
    # 1. En PATH
    iscc_path = shutil.which("iscc") or shutil.which("ISCC")
    if iscc_path:
        return iscc_path

    # 2. Rutas estándares en Windows
    common_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\ProgramData\chocolatey\bin\iscc.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe")
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p

    return None

def build_installer():
    print("=" * 65)
    print("      📦 PyClean Pro - Creador de Instalador de Windows")
    print("=" * 65)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    exe_name = "PyCleanPro.exe" if sys.platform == "win32" else "PyCleanPro"
    exe_path = os.path.join(dist_dir, exe_name)
    iss_script = os.path.join(base_dir, "installer.iss")

    # 1. Verificar si el ejecutable portable existe, de lo contrario compilarlo
    if not os.path.exists(exe_path):
        print(f"\n[!] No se encontró '{exe_name}' en 'dist/'. Compilándolo primero con PyInstaller...\n")
        build_exe_script = os.path.join(base_dir, "build_exe.py")
        res = subprocess.run([sys.executable, build_exe_script])
        if res.returncode != 0:
            print(f"\n❌ Error al compilar el ejecutable principal. Código: {res.returncode}")
            return False

    # 2. Buscar ISCC
    iscc = find_iscc()
    if not iscc:
        print("\n" + "!" * 65)
        print("⚠️  AVISO: Inno Setup Compiler (ISCC.exe) no está instalado en este equipo.")
        print("!" * 65)
        print("\nPara generar el instalador 'PyCleanPro-Setup.exe' en Windows:")
        print("1. Descarga e instala Inno Setup gratis desde:")
        print("   https://jrsoftware.org/isdl.php")
        print("   (O ejecuta en PowerShell: 'choco install innosetup' / 'winget install JRSoftware.InnoSetup')")
        print("2. Vuelve a ejecutar este script o compila directamente haciendo clic derecho en 'installer.iss' -> 'Compile'.")
        print("\nNota: El flujo de GitHub Actions (.github/workflows/build-release.yml) compilará")
        print("tanto el portable como el instalador Setup automáticamente al hacer un release.\n")
        return False

    print(f"\n[+] Inno Setup detectado en: {iscc}")
    print(f"[+] Compilando instalador desde: {iss_script}\n")

    cmd = [iscc, iss_script]
    res = subprocess.run(cmd)

    if res.returncode == 0:
        setup_path = os.path.join(dist_dir, "PyCleanPro-Setup.exe")
        print("\n" + "=" * 65)
        print("✨ ¡Instalador para Windows generado con éxito!")
        print(f"📦 Instalador listo en: {setup_path}")
        print("=" * 65)
        return True
    else:
        print(f"\n❌ Error durante la generación del instalador (código {res.returncode}).")
        return False

if __name__ == "__main__":
    success = build_installer()
    if not success and sys.platform == "win32":
        input("\nPresiona Enter para continuar...")
