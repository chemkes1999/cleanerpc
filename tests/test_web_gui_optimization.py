"""
Unit tests for PyCleanAPI Web Interface Bridge (web_gui.py):
- Tests 10 new API methods exposing deep cleaning and system tuning
- Tests exception containment and JSON-serializable structured responses
- Tests category presence in get_initial_state
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
import cleaner
import sys_optimizer
from web_gui import PyCleanAPI


@pytest.fixture
def api():
    return PyCleanAPI()


class TestPyCleanAPIOptimizationMethods:
    def test_get_initial_state_includes_new_categories(self, api, monkeypatch):
        """get_initial_state debe incluir las 4 nuevas categorías en la lista devuelta al frontend."""
        monkeypatch.setattr(sys, "platform", "win32")
        state = api.get_initial_state()
        assert "categories" in state
        cat_keys = [c["key"] for c in state["categories"]]

        for expected in ["gpu_driver_caches", "directx_shaders", "game_caches", "windows_recent_history"]:
            assert expected in cat_keys, f"Categoría {expected} debe estar en el estado inicial del frontend"

    def test_clean_dism_api(self, api, monkeypatch):
        mock_fn = MagicMock(return_value={"success": True, "output": "DISM OK", "reset_base": True, "error": None})
        monkeypatch.setattr(cleaner, "run_dism_component_cleanup", mock_fn)

        res = api.clean_dism(reset_base=True)
        assert res["success"] is True
        assert res["output"] == "DISM OK"
        mock_fn.assert_called_once_with(reset_base=True)

    def test_clean_vss_shadows_api(self, api, monkeypatch):
        mock_fn = MagicMock(return_value={"success": True, "output": "VSS OK", "error": None})
        monkeypatch.setattr(cleaner, "clean_vss_old_shadows", mock_fn)

        res = api.clean_vss_shadows()
        assert res["success"] is True
        assert res["output"] == "VSS OK"
        mock_fn.assert_called_once()

    def test_prune_docker_api(self, api, monkeypatch):
        mock_fn = MagicMock(return_value={"success": True, "output": "Docker pruned", "space_reclaimed": "500 MB", "error": None})
        monkeypatch.setattr(cleaner, "clean_docker_system", mock_fn)

        res = api.prune_docker()
        assert res["success"] is True
        assert res["space_reclaimed"] == "500 MB"
        mock_fn.assert_called_once()

    def test_scan_stale_node_modules_api(self, api, monkeypatch):
        mock_fn = MagicMock(return_value=[{"project_name": "app1", "size_bytes": 1024}])
        monkeypatch.setattr(cleaner, "find_stale_node_modules", mock_fn)

        res = api.scan_stale_node_modules(path="/projects", inactive_days=60)
        assert len(res) == 1
        assert res[0]["project_name"] == "app1"
        mock_fn.assert_called_once_with(root_dir="/projects", inactive_days=60)

    def test_delete_selected_node_modules_api(self, api, monkeypatch):
        mock_fn = MagicMock(return_value={"success": True, "deleted_count": 2, "freed_bytes": 2048, "freed_formatted": "2.00 KB", "errors": []})
        monkeypatch.setattr(cleaner, "delete_selected_node_modules", mock_fn)

        res = api.delete_selected_node_modules(paths=["/p1/node_modules", "/p2/node_modules"])
        assert res["success"] is True
        assert res["deleted_count"] == 2
        mock_fn.assert_called_once_with(paths=["/p1/node_modules", "/p2/node_modules"])

    def test_set_ultimate_performance_api(self, api, monkeypatch):
        mock_fn = MagicMock(return_value={"success": True, "message": "Plan activado", "guid": "e9a42b02-d5df-448d-aa00-03f14749eb61"})
        monkeypatch.setattr(sys_optimizer, "unlock_ultimate_performance_plan", mock_fn)

        res = api.set_ultimate_performance()
        assert res["success"] is True
        assert res["guid"] == "e9a42b02-d5df-448d-aa00-03f14749eb61"
        mock_fn.assert_called_once()

    def test_optimize_tcp_stack_api(self, api, monkeypatch):
        mock_fn = MagicMock(return_value={"success": True, "message": "TCP tuned", "autotuning": "normal"})
        monkeypatch.setattr(sys_optimizer, "tune_tcp_network", mock_fn)

        res = api.optimize_tcp_stack(enable_autotuning=True)
        assert res["success"] is True
        assert res["autotuning"] == "normal"
        mock_fn.assert_called_once_with(enable_autotuning=True)

    def test_repair_search_indexer_api(self, api, monkeypatch):
        mock_fn = MagicMock(return_value={"success": True, "message": "Index reset"})
        monkeypatch.setattr(sys_optimizer, "reindex_windows_search", mock_fn)

        res = api.repair_search_indexer()
        assert res["success"] is True
        mock_fn.assert_called_once()

    def test_get_compact_os_status_api(self, api, monkeypatch):
        mock_fn = MagicMock(return_value={"success": True, "is_compact": True, "raw_output": "Compact"})
        monkeypatch.setattr(sys_optimizer, "get_compact_os_status", mock_fn)

        res = api.get_compact_os_status()
        assert res["success"] is True
        assert res["is_compact"] is True
        mock_fn.assert_called_once()

    def test_toggle_compact_os_api(self, api, monkeypatch):
        mock_fn = MagicMock(return_value={"success": True, "is_compact": True, "message": "Compact enabled"})
        monkeypatch.setattr(sys_optimizer, "toggle_compact_os", mock_fn)

        res = api.toggle_compact_os(enable=True)
        assert res["success"] is True
        assert res["is_compact"] is True
        mock_fn.assert_called_once_with(enable=True)


class TestPyCleanAPIExceptionSafety:
    def test_api_exception_safety_on_errors(self, api, monkeypatch):
        """Verifica que si cualquier módulo genera una excepción inesperada, la API la capture y devuelva dict de fallo."""
        def raise_err(*args, **kwargs):
            raise RuntimeError("Fallo crítico simulado")

        monkeypatch.setattr(cleaner, "run_dism_component_cleanup", raise_err)
        monkeypatch.setattr(cleaner, "clean_vss_old_shadows", raise_err)
        monkeypatch.setattr(cleaner, "clean_docker_system", raise_err)
        monkeypatch.setattr(cleaner, "find_stale_node_modules", raise_err)
        monkeypatch.setattr(cleaner, "delete_selected_node_modules", raise_err)
        monkeypatch.setattr(sys_optimizer, "unlock_ultimate_performance_plan", raise_err)
        monkeypatch.setattr(sys_optimizer, "tune_tcp_network", raise_err)
        monkeypatch.setattr(sys_optimizer, "reindex_windows_search", raise_err)
        monkeypatch.setattr(sys_optimizer, "get_compact_os_status", raise_err)
        monkeypatch.setattr(sys_optimizer, "toggle_compact_os", raise_err)

        assert api.clean_dism()["success"] is False
        assert api.clean_vss_shadows()["success"] is False
        assert api.prune_docker()["success"] is False
        assert api.scan_stale_node_modules() == []
        assert api.delete_selected_node_modules([])["success"] is False
        assert api.set_ultimate_performance()["success"] is False
        assert api.optimize_tcp_stack()["success"] is False
        assert api.repair_search_indexer()["success"] is False
        assert api.get_compact_os_status()["success"] is False
        assert api.toggle_compact_os(True)["success"] is False
