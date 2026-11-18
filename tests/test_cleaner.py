"""
Suite de pruebas unitarias para PyClean Pro
Verifica la seguridad del motor, filtros de exclusión, triturador, duplicados y exportación.
"""

import os
import sys
import tempfile
import time
import pytest

# Asegurar que el directorio raíz está en sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import cleaner


def test_format_size():
    assert cleaner.format_size(0) == "0 B"
    assert cleaner.format_size(-100) == "0 B"
    assert cleaner.format_size(500) == "500.00 B"
    assert cleaner.format_size(1024) == "1.00 KB"
    assert cleaner.format_size(1024 * 1024) == "1.00 MB"
    assert cleaner.format_size(1024 * 1024 * 1024) == "1.00 GB"


def test_is_path_excluded():
    exclusions = ["/tmp/safe_dir", "/tmp/another/file.txt"]
    assert cleaner.is_path_excluded("/tmp/safe_dir", exclusions) is True
    assert cleaner.is_path_excluded("/tmp/safe_dir/subfile.tmp", exclusions) is True
    assert cleaner.is_path_excluded("/tmp/another/file.txt", exclusions) is True
    assert cleaner.is_path_excluded("/tmp/other_dir/file.txt", exclusions) is False
    assert cleaner.is_path_excluded("/tmp/safe_dir_not_really", exclusions) is False


def test_is_file_safe_to_clean():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test data")
        temp_path = f.name

    try:
        # Archivo recién creado (< 24h) con filtro activo -> no seguro
        assert cleaner.is_file_safe_to_clean(temp_path, supports_age_filter=True, min_age_hours=24) is False
        # Con filtro desactivado -> seguro
        assert cleaner.is_file_safe_to_clean(temp_path, supports_age_filter=False, min_age_hours=24) is True
        # Con min_age_hours = 0 -> seguro
        assert cleaner.is_file_safe_to_clean(temp_path, supports_age_filter=True, min_age_hours=0) is True

        # Modificar mtime para simular archivo antiguo (hace 48 horas)
        two_days_ago = time.time() - (48 * 3600)
        os.utime(temp_path, (two_days_ago, two_days_ago))
        assert cleaner.is_file_safe_to_clean(temp_path, supports_age_filter=True, min_age_hours=24) is True
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_is_safe_link_or_junction():
    with tempfile.TemporaryDirectory() as temp_dir:
        real_file = os.path.join(temp_dir, "real.txt")
        with open(real_file, "w") as f:
            f.write("content")

        symlink_file = os.path.join(temp_dir, "link.txt")
        try:
            os.symlink(real_file, symlink_file)
            assert cleaner.is_safe_link_or_junction(real_file) is False
            assert cleaner.is_safe_link_or_junction(symlink_file) is True
        except (OSError, NotImplementedError):
            pass


def test_shred_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"Extremely Confidential Password 12345")
        shred_path = f.name

    assert os.path.exists(shred_path)
    ok, msg = cleaner.shred_file(shred_path, passes=2)
    assert ok is True
    assert not os.path.exists(shred_path)


def test_find_duplicate_files():
    with tempfile.TemporaryDirectory() as temp_dir:
        f1 = os.path.join(temp_dir, "file1.bin")
        f2 = os.path.join(temp_dir, "file2.bin")
        f3 = os.path.join(temp_dir, "file3.bin")

        data = b"Duplicate Content String " * 50  # > 1024 bytes
        with open(f1, "wb") as f:
            f.write(data)
        with open(f2, "wb") as f:
            f.write(data)
        with open(f3, "wb") as f:
            f.write(b"Unique Content String " * 50)

        dups = cleaner.find_duplicate_files(temp_dir, min_size_bytes=512)
        assert len(dups) == 1
        assert len(dups[0]["files"]) == 2
        assert f1 in dups[0]["files"]
        assert f2 in dups[0]["files"]
        assert f3 not in dups[0]["files"]


def test_export_report():
    report_data = {
        "total_freed_formatted": "150.00 MB",
        "total_deleted": 42,
        "total_skipped": 5,
        "categories": {
            "user_temp": {"name": "Temporales", "freed_formatted": "100.00 MB"}
        }
    }
    with tempfile.TemporaryDirectory() as temp_dir:
        json_file = os.path.join(temp_dir, "report.json")
        txt_file = os.path.join(temp_dir, "report.txt")

        ok_json, _ = cleaner.export_report(report_data, json_file, format_type="json")
        assert ok_json is True
        assert os.path.exists(json_file)

        ok_txt, _ = cleaner.export_report(report_data, txt_file, format_type="txt")
        assert ok_txt is True
        assert os.path.exists(txt_file)
        with open(txt_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "PyClean Pro" in content
            assert "150.00 MB" in content


def test_audit_old_downloads(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Simular carpeta Downloads
        monkeypatch.setattr(cleaner.Path, "home", lambda: temp_dir)
        downloads_dir = os.path.join(temp_dir, "Downloads")
        os.makedirs(downloads_dir)

        old_iso = os.path.join(downloads_dir, "ubuntu-22.04.iso")
        new_msi = os.path.join(downloads_dir, "installer_new.msi")
        old_txt = os.path.join(downloads_dir, "notes.txt")

        with open(old_iso, "wb") as f:
            f.write(b"0" * 1024)
        with open(new_msi, "wb") as f:
            f.write(b"0" * 1024)
        with open(old_txt, "wb") as f:
            f.write(b"0" * 1024)

        # Modificar mtime del archivo viejo a hace 40 días
        old_time = time.time() - (40 * 86400)
        os.utime(old_iso, (old_time, old_time))
        os.utime(old_txt, (old_time, old_time))

        results = cleaner.audit_old_downloads(min_age_days=30)
        # Debe incluir old_iso, pero no new_msi (<30 días) ni old_txt (no es instalador)
        assert len(results) == 1
        assert results[0]["name"] == "ubuntu-22.04.iso"
        assert results[0]["days_old"] >= 39


def test_find_app_leftovers(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock de variables de entorno para AppData
        local_app = os.path.join(temp_dir, "Local")
        roaming_app = os.path.join(temp_dir, "Roaming")
        os.makedirs(local_app)
        os.makedirs(roaming_app)

        monkeypatch.setenv("LOCALAPPDATA", local_app)
        monkeypatch.setenv("APPDATA", roaming_app)

        # Crear carpetas de prueba
        target_leftover = os.path.join(local_app, "SpotifyOldApp")
        generic_folder = os.path.join(local_app, "Microsoft")
        other_folder = os.path.join(roaming_app, "Discord")
        os.makedirs(target_leftover)
        os.makedirs(generic_folder)
        os.makedirs(other_folder)

        found = cleaner.find_app_leftovers("Spotify")
        assert target_leftover in found
        assert generic_folder not in found
        assert other_folder not in found


def test_v22_fallbacks():
    # En entornos no Windows, las llamadas retornan estados seguros en lugar de crashear
    task_stat = cleaner.get_scheduled_task_status()
    assert isinstance(task_stat, dict)
    assert "enabled" in task_stat

    tel_stat = cleaner.get_telemetry_status()
    assert isinstance(tel_stat, dict)
    assert "services" in tel_stat

    apps = cleaner.get_installed_apps()
    assert isinstance(apps, list)
