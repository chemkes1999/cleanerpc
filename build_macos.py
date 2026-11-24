"""
PyClean Pro - Script de Compilación e Instalador para macOS (.app + .dmg)
Compila la aplicación nativa PyCleanPro.app con PyInstaller y la empaqueta
en una imagen de disco profesional PyCleanPro-macOS.dmg con acceso directo a /Applications.
"""

import os
import sys
import shutil
import tempfile
import subprocess

try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def build_macos():
    print("=" * 60)
    print("   PyClean Pro - Compilador macOS (.app + .dmg)")
    print("=" * 60)

    if sys.platform != "darwin":
        print("[!] Este script debe ejecutarse en macOS (darwin).")
        sys.exit(1)

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[!] PyInstaller no está instalado. Instalándolo...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(base_dir, "main.py")
    web_dir = os.path.join(base_dir, "web")
    icon_path = os.path.join(base_dir, "assets", "pyclean_icon.icns")
    dist_dir = os.path.join(base_dir, "dist")
    app_bundle = os.path.join(dist_dir, "PyCleanPro.app")
    dmg_path = os.path.join(dist_dir, "PyCleanPro-macOS.dmg")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=PyCleanPro",
        "--onedir",
        "--windowed",
        f"--add-data={web_dir}:web",
        "--osx-bundle-identifier=com.chemkes1999.pycleanpro",
        "--noconfirm",
        "--clean",
    ]

    if os.path.exists(icon_path):
        cmd.append(f"--icon={icon_path}")

    cmd.append(main_script)

    print(f"\n[+] Compilando PyCleanPro.app:\n{' '.join(cmd)}\n")
    res = subprocess.run(cmd, cwd=base_dir)
    if res.returncode != 0 or not os.path.isdir(app_bundle):
        print(f"\n[!] Error al compilar PyCleanPro.app (código {res.returncode}).")
        sys.exit(res.returncode or 1)

    print(f"[+] Bundle creado correctamente: {app_bundle}")

    # Firma Ad-hoc profunda para evitar fallos de integridad en Apple Silicon (ARM64) e Intel
    print(f"\n[+] Aplicando firma de código Ad-hoc a {app_bundle}...")
    codesign_res = subprocess.run(["codesign", "--force", "--deep", "--sign", "-", app_bundle], check=False)
    if codesign_res.returncode == 0:
        print("[+] Firma Ad-hoc aplicada con éxito.")
    else:
        print("[!] Advertencia: codesign no completó con éxito (se continuará empaquetando).")

    # Preparar carpeta temporal para crear el .dmg con enlace a /Applications
    if os.path.exists(dmg_path):
        os.remove(dmg_path)

    with tempfile.TemporaryDirectory(prefix="pyclean_dmg_") as staging_dir:
        staged_app = os.path.join(staging_dir, "PyCleanPro.app")
        shutil.copytree(app_bundle, staged_app, symlinks=True)
        # Re-firmar en staging para asegurar sellado de symlinks
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", staged_app], check=False)
        os.symlink("/Applications", os.path.join(staging_dir, "Applications"))

        hdiutil_cmd = [
            "hdiutil",
            "create",
            "-volname",
            "PyClean Pro",
            "-srcfolder",
            staging_dir,
            "-ov",
            "-format",
            "UDZO",
            dmg_path,
        ]
        print(f"\n[+] Empaquetando instalador .dmg:\n{' '.join(hdiutil_cmd)}\n")
        dmg_res = subprocess.run(hdiutil_cmd, cwd=base_dir)
        if dmg_res.returncode != 0 or not os.path.isfile(dmg_path):
            print(f"\n[!] Error al crear el .dmg (código {dmg_res.returncode}).")
            sys.exit(dmg_res.returncode or 1)

    size_mb = os.path.getsize(dmg_path) / (1024 * 1024)
    print("\n" + "=" * 60)
    print("Compilacion e instalador macOS exitosos!")
    print(f"Instalador DMG: {dmg_path} ({size_mb:.1f} MB)")
    print("=" * 60)


if __name__ == "__main__":
    build_macos()
