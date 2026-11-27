"""
PyClean Pro - Script de Compilación e Instalador para macOS (.app + .dmg)
Compila la aplicación nativa PyCleanPro.app con PyInstaller, aplica firma ad-hoc profunda
con entitlements para Apple Silicon y Hardened Runtime, e incluye un asistente interactivo
de desbloqueo Gatekeeper dentro de la imagen de disco PyCleanPro-macOS.dmg.
"""

import os
import sys
import shutil
import tempfile
import subprocess
import plistlib

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
    entitlements_path = os.path.join(base_dir, "entitlements.plist")
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

    if os.path.exists(entitlements_path):
        cmd.append(f"--osx-entitlements-file={entitlements_path}")

    cmd.append(main_script)

    print(f"\n[+] Compilando PyCleanPro.app:\n{' '.join(cmd)}\n")
    res = subprocess.run(cmd, cwd=base_dir)
    if res.returncode != 0 or not os.path.isdir(app_bundle):
        print(f"\n[!] Error al compilar PyCleanPro.app (código {res.returncode}).")
        sys.exit(res.returncode or 1)

    print(f"[+] Bundle creado correctamente: {app_bundle}")

    # Enriquecer Info.plist con metadatos oficiales y capacidades de Dark Mode
    plist_file = os.path.join(app_bundle, "Contents", "Info.plist")
    if os.path.exists(plist_file):
        try:
            print("[+] Configurando Info.plist con metadatos v2.9.0...")
            with open(plist_file, "rb") as f:
                pl = plistlib.load(f)
            pl["CFBundleShortVersionString"] = "2.9.0"
            pl["CFBundleVersion"] = "2.9.0"
            pl["CFBundleDisplayName"] = "PyClean Pro"
            pl["NSHumanReadableCopyright"] = "Copyright © 2026 chemkes1999. Open Source."
            pl["NSHighResolutionCapable"] = True
            pl["NSRequiresAquaSystemAppearance"] = False
            with open(plist_file, "wb") as f:
                plistlib.dump(pl, f)
        except Exception as e:
            print(f"[!] Advertencia actualizando Info.plist: {e}")

    # Limpiar atributos extendidos antes de firmar
    subprocess.run(["xattr", "-cr", app_bundle], check=False)

    # Firma Ad-hoc profunda con Hardened Runtime y Entitlements
    print(f"\n[+] Aplicando firma de código Ad-hoc a {app_bundle}...")
    codesign_args = ["codesign", "--force", "--deep", "--sign", "-"]
    if os.path.exists(entitlements_path):
        codesign_args.extend(["--entitlements", entitlements_path, "--options", "runtime"])
    codesign_args.append(app_bundle)

    codesign_res = subprocess.run(codesign_args, check=False)
    if codesign_res.returncode == 0:
        print("[+] Firma Ad-hoc aplicada con éxito.")
    else:
        print("[!] Advertencia: codesign no completó con éxito (se continuará empaquetando).")

    # Preparar carpeta staging para el .dmg
    if os.path.exists(dmg_path):
        os.remove(dmg_path)

    with tempfile.TemporaryDirectory(prefix="pyclean_dmg_") as staging_dir:
        staged_app = os.path.join(staging_dir, "PyCleanPro.app")
        shutil.copytree(app_bundle, staged_app, symlinks=True)

        # Limpiar atributos y re-firmar en staging
        subprocess.run(["xattr", "-cr", staged_app], check=False)
        staging_codesign = ["codesign", "--force", "--deep", "--sign", "-"]
        if os.path.exists(entitlements_path):
            staging_codesign.extend(["--entitlements", entitlements_path, "--options", "runtime"])
        staging_codesign.append(staged_app)
        subprocess.run(staging_codesign, check=False)

        # Enlace simbolico a /Applications
        os.symlink("/Applications", os.path.join(staging_dir, "Applications"))

        # Script interactivo de 1-clic para desbloquear Gatekeeper si el usuario lo necesita
        helper_script = os.path.join(staging_dir, "Abrir PyClean Pro (Desbloquear Gatekeeper).command")
        script_content = """#!/bin/bash
clear
echo "=========================================================="
echo "   ⚡ PyClean Pro - Asistente de Desbloqueo macOS"
echo "=========================================================="
echo ""
echo "Eliminando bandera de cuarentena (Apple Gatekeeper)..."

APP_PATH="/Applications/PyCleanPro.app"
LOCAL_APP="$(cd "$(dirname "$0")" && pwd)/PyCleanPro.app"

if [ -d "$APP_PATH" ]; then
    xattr -cr "$APP_PATH" 2>/dev/null
    echo "[✓] Permisos desbloqueados con éxito en /Applications/PyCleanPro.app"
    echo "[+] Iniciando PyClean Pro..."
    open "$APP_PATH"
elif [ -d "$LOCAL_APP" ]; then
    xattr -cr "$LOCAL_APP" 2>/dev/null
    echo "[✓] Permisos desbloqueados con éxito en $LOCAL_APP"
    echo "[+] Iniciando PyClean Pro..."
    open "$LOCAL_APP"
else
    echo "[!] Por favor arrastra PyCleanPro.app a la carpeta Aplicaciones primero."
fi
echo ""
echo "Listo. Puedes cerrar esta ventana."
"""
        with open(helper_script, "w", encoding="utf-8") as f:
            f.write(script_content)
        os.chmod(helper_script, 0o755)

        # Archivo informativo de bienvenida en la imagen DMG
        readme_dmg = os.path.join(staging_dir, "Instrucciones de Instalación.txt")
        with open(readme_dmg, "w", encoding="utf-8") as f:
            f.write(
                "⚡ PyClean Pro v2.9.0 para macOS\n\n"
                "Instalación:\n"
                "1. Arrastra 'PyCleanPro.app' a la carpeta 'Applications'.\n"
                "2. Si macOS Gatekeeper bloquea la apertura indicando desarrollador no identificado:\n"
                "   - Simplemente haz doble clic en 'Abrir PyClean Pro (Desbloquear Gatekeeper).command'.\n"
                "   - O en la app Terminal ejecuta: xattr -cr /Applications/PyCleanPro.app\n"
            )

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
        print(f"\n[+] Empaquetando instalador .dmg con asistente Gatekeeper:\n{' '.join(hdiutil_cmd)}\n")
        dmg_res = subprocess.run(hdiutil_cmd, cwd=base_dir)
        if dmg_res.returncode != 0 or not os.path.isfile(dmg_path):
            print(f"\n[!] Error al crear el .dmg (código {dmg_res.returncode}).")
            sys.exit(dmg_res.returncode or 1)

        # Firma del DMG
        subprocess.run(["codesign", "--force", "--sign", "-", dmg_path], check=False)

    size_mb = os.path.getsize(dmg_path) / (1024 * 1024)
    print("\n" + "=" * 60)
    print("Compilacion e instalador macOS exitosos!")
    print(f"Instalador DMG: {dmg_path} ({size_mb:.1f} MB)")
    print("=" * 60)


if __name__ == "__main__":
    build_macos()
