"""
Unit tests for Cleaner Engine Expansion:
- Deep clean categories (gpu_driver_caches, directx_shaders, game_caches, windows_recent_history)
- DISM WinSxS component store cleanup
- VSS shadow copy cleanup
- Docker system prune
- Stale node_modules detection and safe deletion
"""

from __future__ import annotations

import sys
import os
import shutil
import subprocess
import time
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import cleaner


class TestDeepCleanCategories:
    def test_new_categories_registered(self, monkeypatch):
        """Verifica que las 4 nuevas categorías existan en get_target_categories en plataformas Windows."""
        monkeypatch.setattr(sys, "platform", "win32")
        categories = cleaner.get_target_categories()

        expected_keys = [
            "gpu_driver_caches",
            "directx_shaders",
            "game_caches",
            "windows_recent_history"
        ]

        for key in expected_keys:
            assert key in categories, f"La categoría {key} debe estar presente en get_target_categories"
            cat = categories[key]
            assert "name" in cat and isinstance(cat["name"], str)
            assert "desc" in cat and isinstance(cat["desc"], str)
            assert "requires_admin" in cat and isinstance(cat["requires_admin"], bool)
            assert "paths" in cat and isinstance(cat["paths"], list)
            assert cat.get("is_recycle_bin") is False
            assert cat.get("supports_age_filter") is False

        # gpu_driver_caches debe requerir privilegios de administrador
        assert categories["gpu_driver_caches"]["requires_admin"] is True
        # las otras 3 son accesibles por usuario
        assert categories["directx_shaders"]["requires_admin"] is False
        assert categories["game_caches"]["requires_admin"] is False
        assert categories["windows_recent_history"]["requires_admin"] is False

    def test_category_paths_populated_from_env(self, monkeypatch):
        """Verifica que las rutas de las categorías se expandan correctamente con variables de entorno."""
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\TestUser\AppData\Local")
        monkeypatch.setenv("APPDATA", r"C:\Users\TestUser\AppData\Roaming")
        monkeypatch.setenv("ProgramData", r"C:\ProgramData")
        monkeypatch.setenv("ProgramFiles(x86)", r"C:\Program Files (x86)")
        monkeypatch.setenv("SystemDrive", "C:")

        categories = cleaner.get_target_categories()

        assert any("D3DSCache" in p for p in categories["directx_shaders"]["paths"])
        assert any("NVIDIA" in p for p in categories["gpu_driver_caches"]["paths"])
        assert any("Steam" in p for p in categories["game_caches"]["paths"])
        assert any("Recent" in p for p in categories["windows_recent_history"]["paths"])

    def test_category_scan_compatibility(self, tmp_path):
        """Verifica que scan_category procese sin errores una de las nuevas categorías."""
        cache_dir = tmp_path / "mock_shaders"
        cache_dir.mkdir()
        (cache_dir / "shader.bin").write_bytes(b"\x00" * 2048)

        mock_category = {
            "name": "Caché de Prueba",
            "desc": "Prueba",
            "requires_admin": False,
            "paths": [str(cache_dir)],
            "is_recycle_bin": False,
            "supports_age_filter": False
        }

        size, count, items = cleaner.scan_category("directx_shaders", mock_category)
        assert size == 2048
        assert count == 1
        assert len(items) == 1
        assert items[0]["size"] == 2048


class TestDismCleanup:
    def test_dism_non_windows_fallback(self, monkeypatch):
        """En sistemas no-Windows debe devolver fallo y mensaje descriptivo sin llamar subprocess."""
        monkeypatch.setattr(sys, "platform", "linux")
        res = cleaner.run_dism_component_cleanup(reset_base=False)
        assert res["success"] is False
        assert "Requiere privilegios de Administrador en Windows" in res["error"]
        assert res["reset_base"] is False

    def test_dism_non_admin_fallback(self, mock_win32_nonadmin):
        """En Windows sin privilegios de admin debe denegar la ejecución."""
        res = cleaner.run_dism_component_cleanup(reset_base=True)
        assert res["success"] is False
        assert "Requiere privilegios de Administrador en Windows" in res["error"]
        assert res["reset_base"] is True

    def test_dism_admin_execution_standard(self, mock_win32_admin, monkeypatch):
        """En Windows con admin ejecuta el comando estándar de DISM sin /resetbase."""
        recorded_cmd = []

        def mock_run(cmd, **kwargs):
            recorded_cmd.extend(cmd)
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "Operación completada correctamente."
            mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)

        progress_msgs = []
        res = cleaner.run_dism_component_cleanup(reset_base=False, on_progress=progress_msgs.append)

        assert res["success"] is True
        assert res["reset_base"] is False
        assert "Operación completada" in res["output"]
        assert res["error"] is None
        assert "dism.exe" in recorded_cmd
        assert "/startcomponentcleanup" in recorded_cmd
        assert "/resetbase" not in recorded_cmd
        assert len(progress_msgs) >= 1

    def test_dism_admin_execution_with_resetbase(self, mock_win32_admin, monkeypatch):
        """Cuando reset_base=True, agrega /resetbase a los argumentos."""
        recorded_cmd = []

        def mock_run(cmd, **kwargs):
            recorded_cmd.extend(cmd)
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "Limpieza con ResetBase completada."
            mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)

        res = cleaner.run_dism_component_cleanup(reset_base=True)
        assert res["success"] is True
        assert res["reset_base"] is True
        assert "/resetbase" in recorded_cmd

    def test_dism_timeout_handling(self, mock_win32_admin, monkeypatch):
        """Manejo seguro de TimeoutExpired en DISM."""
        def mock_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=600)

        monkeypatch.setattr(subprocess, "run", mock_run)

        res = cleaner.run_dism_component_cleanup(reset_base=False)
        assert res["success"] is False
        assert "agotado" in res["error"].lower()


class TestVssCleanup:
    def test_vss_non_windows_fallback(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        res = cleaner.clean_vss_old_shadows()
        assert res["success"] is False
        assert "Requiere privilegios de Administrador" in res["error"]

    def test_vss_non_admin_fallback(self, mock_win32_nonadmin):
        res = cleaner.clean_vss_old_shadows()
        assert res["success"] is False
        assert "Requiere privilegios de Administrador" in res["error"]

    def test_vss_success_execution(self, mock_win32_admin, monkeypatch):
        recorded_cmd = []

        def mock_run(cmd, **kwargs):
            recorded_cmd.extend(cmd)
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "Se eliminaron 1 instantáneas correctamente."
            mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)

        res = cleaner.clean_vss_old_shadows()
        assert res["success"] is True
        assert "vssadmin.exe" in recorded_cmd
        assert "/quiet" in recorded_cmd
        assert "/oldest" in recorded_cmd
        assert res["error"] is None

    def test_vss_no_items_found_handled_as_success(self, mock_win32_admin, monkeypatch):
        """vssadmin reportando 'No items found' debe considerarse éxito sin error."""
        def mock_run(cmd, **kwargs):
            mock_res = MagicMock()
            mock_res.returncode = 2
            mock_res.stdout = "No items found that satisfy the query."
            mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)

        res = cleaner.clean_vss_old_shadows()
        assert res["success"] is True
        assert res["error"] is None


class TestDockerCleanup:
    def test_docker_not_installed(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda cmd: None)
        res = cleaner.clean_docker_system()
        assert res["success"] is False
        assert "no está instalado" in res["error"]
        assert res["space_reclaimed"] == "0 B"

    def test_docker_daemon_not_running(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/docker")

        def mock_run(cmd, **kwargs):
            mock_res = MagicMock()
            if cmd == ["docker", "info"]:
                mock_res.returncode = 1
                mock_res.stdout = ""
                mock_res.stderr = "Cannot connect to the Docker daemon"
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)

        res = cleaner.clean_docker_system()
        assert res["success"] is False
        assert "demonio de Docker" in res["error"]

    def test_docker_prune_success(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/docker")

        def mock_run(cmd, **kwargs):
            mock_res = MagicMock()
            if cmd == ["docker", "info"]:
                mock_res.returncode = 0
                mock_res.stdout = "Server Version: 24.0.5"
                mock_res.stderr = ""
            elif cmd == ["docker", "system", "prune", "-f"]:
                mock_res.returncode = 0
                mock_res.stdout = "Deleted Containers:\n12345\n\nTotal reclaimed space: 1.45GB\n"
                mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)

        res = cleaner.clean_docker_system()
        assert res["success"] is True
        assert res["space_reclaimed"] == "1.45GB"
        assert res["error"] is None


class TestNodeModulesScannerAndCleaner:
    def test_scan_and_delete_stale_node_modules(self, tmp_path):
        """Prueba completa con carpetas reales: escaneo de proyectos inactivos y eliminación segura."""
        now = time.time()
        past_100_days = now - (100 * 86400)
        recent_10_days = now - (10 * 86400)

        # 1. Proyecto Stale (>90 días)
        p_stale = tmp_path / "project_stale"
        p_stale.mkdir()
        pkg_stale = p_stale / "package.json"
        pkg_stale.write_text('{"name": "stale-proj"}')
        os.utime(str(pkg_stale), (past_100_days, past_100_days))
        os.utime(str(p_stale), (past_100_days, past_100_days))

        nm_stale = p_stale / "node_modules"
        nm_stale.mkdir()
        lib_stale = nm_stale / "dummy_lib"
        lib_stale.mkdir()
        dummy_file = lib_stale / "index.js"
        dummy_file.write_bytes(b"x" * 4096)

        # Nested node_modules para verificar que la recursión se poda
        nested_nm = lib_stale / "node_modules"
        nested_nm.mkdir()
        (nested_nm / "sub.js").write_bytes(b"nested")

        # 2. Proyecto Activo (<90 días)
        p_active = tmp_path / "project_active"
        p_active.mkdir()
        pkg_active = p_active / "package.json"
        pkg_active.write_text('{"name": "active-proj"}')
        os.utime(str(pkg_active), (recent_10_days, recent_10_days))
        os.utime(str(p_active), (recent_10_days, recent_10_days))

        nm_active = p_active / "node_modules"
        nm_active.mkdir()
        (nm_active / "active.js").write_bytes(b"active")

        # Ejecutar escáner con umbral de 90 días
        stale_list = cleaner.find_stale_node_modules(str(tmp_path), inactive_days=90)

        # Debe encontrar únicamente project_stale/node_modules
        assert len(stale_list) == 1
        found = stale_list[0]
        assert found["project_name"] == "project_stale"
        assert found["days_inactive"] >= 90
        assert found["size_bytes"] >= 4096
        assert os.path.normpath(found["path"]) == os.path.normpath(str(nm_stale))

        # Verificar borrado seguro
        del_res = cleaner.delete_selected_node_modules([found["path"]])
        assert del_res["success"] is True
        assert del_res["deleted_count"] == 1
        assert del_res["freed_bytes"] >= 4096
        assert not os.path.exists(str(nm_stale))

    def test_delete_node_modules_safety_checks(self, tmp_path):
        """Verifica rechazo de rutas que no se llamen 'node_modules' o enlaces simbólicos."""
        # 1. Ruta que no es node_modules
        fake_dir = tmp_path / "not_node_modules"
        fake_dir.mkdir()
        res1 = cleaner.delete_selected_node_modules([str(fake_dir)])
        assert res1["success"] is False
        assert any("no es node_modules" in err for err in res1["errors"])
        assert os.path.exists(str(fake_dir))

        # 2. Enlace simbólico con nombre node_modules
        target_dir = tmp_path / "real_target"
        target_dir.mkdir()
        (target_dir / "keep.txt").write_text("keep me")
        symlink_nm = tmp_path / "node_modules"
        try:
            os.symlink(str(target_dir), str(symlink_nm))
            res2 = cleaner.delete_selected_node_modules([str(symlink_nm)])
            assert res2["success"] is False
            assert any("enlace simbólico" in err for err in res2["errors"])
            assert os.path.exists(str(target_dir / "keep.txt"))
        except OSError:
            # En caso de entornos con permisos restringidos de symlink
            pass
