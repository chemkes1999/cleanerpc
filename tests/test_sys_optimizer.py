"""
Unit tests for System Optimizer and OS Tuning Module (sys_optimizer.py):
- Ultimate Performance power plan unlocking and activation
- TCP/IP network stack auto-tuning
- Windows Search indexer reset and WSearch lifecycle
- Compact OS query parsing (English and Spanish) and toggle operations
- Cross-platform non-Windows and non-admin graceful fallbacks
"""

from __future__ import annotations

import sys
import subprocess
from unittest.mock import MagicMock

import pytest
import sys_optimizer


class TestOptimizerFallbacks:
    def test_non_windows_fallbacks(self, monkeypatch):
        """Verifica que en plataformas no-Windows todas las funciones devuelvan fallbacks seguros."""
        monkeypatch.setattr(sys, "platform", "linux")

        res_perf = sys_optimizer.unlock_ultimate_performance_plan()
        assert res_perf["success"] is False
        assert "Requiere privilegios de Administrador" in res_perf["message"]

        res_tcp = sys_optimizer.tune_tcp_network()
        assert res_tcp["success"] is False
        assert "Requiere privilegios de Administrador" in res_tcp["message"]

        res_search = sys_optimizer.reindex_windows_search()
        assert res_search["success"] is False
        assert "Requiere privilegios de Administrador" in res_search["message"]

        res_query = sys_optimizer.get_compact_os_status()
        assert res_query["success"] is False
        assert res_query["is_compact"] is False
        assert "solo está disponible en Windows" in res_query["raw_output"]

        res_toggle = sys_optimizer.toggle_compact_os(True)
        assert res_toggle["success"] is False
        assert res_toggle["is_compact"] is False
        assert "Requiere privilegios de Administrador" in res_toggle["message"]

    def test_non_admin_fallbacks(self, mock_win32_nonadmin):
        """Verifica que en Windows sin permisos de administrador se rechace la ejecución."""
        assert sys_optimizer.unlock_ultimate_performance_plan()["success"] is False
        assert sys_optimizer.tune_tcp_network()["success"] is False
        assert sys_optimizer.reindex_windows_search()["success"] is False
        assert sys_optimizer.toggle_compact_os(True)["success"] is False


class TestUltimatePerformance:
    def test_unlock_plan_already_present(self, mock_win32_admin, monkeypatch):
        """Si el plan ya está en powercfg /list, debe activar directamente sin duplicar."""
        executed_cmds = []

        def mock_run(cmd, **kwargs):
            executed_cmds.append(cmd)
            mock_res = MagicMock()
            mock_res.returncode = 0
            if cmd == ["powercfg", "/list"]:
                mock_res.stdout = f"Power Scheme GUID: {sys_optimizer.ULTIMATE_PERF_GUID} (Ultimate Performance)\n"
            elif cmd[0] == "powercfg" and cmd[1] == "/setactive":
                mock_res.stdout = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)

        res = sys_optimizer.unlock_ultimate_performance_plan()
        assert res["success"] is True
        assert res["guid"] == sys_optimizer.ULTIMATE_PERF_GUID
        assert ["powercfg", "/setactive", sys_optimizer.ULTIMATE_PERF_GUID] in executed_cmds
        assert not any("/duplicatescheme" in cmd for cmd in executed_cmds)

    def test_unlock_plan_duplicate_and_activate(self, mock_win32_admin, monkeypatch):
        """Si el plan no está listado, ejecuta /duplicatescheme y activa el nuevo GUID."""
        executed_cmds = []
        new_guid = "11111111-2222-3333-4444-555555555555"

        def mock_run(cmd, **kwargs):
            executed_cmds.append(cmd)
            mock_res = MagicMock()
            mock_res.returncode = 0
            if cmd == ["powercfg", "/list"]:
                mock_res.stdout = "Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e (Balanced)\n"
            elif cmd[0] == "powercfg" and cmd[1] == "/duplicatescheme":
                mock_res.stdout = f"Power Scheme GUID: {new_guid} (Ultimate Performance)\n"
            elif cmd[0] == "powercfg" and cmd[1] == "/setactive":
                mock_res.stdout = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)

        res = sys_optimizer.unlock_ultimate_performance_plan()
        assert res["success"] is True
        assert res["guid"] == new_guid
        assert ["powercfg", "/setactive", new_guid] in executed_cmds


class TestTcpNetworkTuning:
    def test_tune_tcp_enable(self, mock_win32_admin, monkeypatch):
        """Verifica activación de autotuning normal y flags complementarios."""
        recorded_cmds = []

        def mock_run(cmd, **kwargs):
            recorded_cmds.append(cmd)
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "Ok.\n"
            mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)

        res = sys_optimizer.tune_tcp_network(enable_autotuning=True)
        assert res["success"] is True
        assert res["autotuning"] == "normal"
        assert ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"] in recorded_cmds

    def test_tune_tcp_disable(self, mock_win32_admin, monkeypatch):
        """Verifica desactivación de autotuning."""
        recorded_cmds = []

        def mock_run(cmd, **kwargs):
            recorded_cmds.append(cmd)
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "Ok.\n"
            mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)

        res = sys_optimizer.tune_tcp_network(enable_autotuning=False)
        assert res["success"] is True
        assert res["autotuning"] == "disabled"
        assert ["netsh", "int", "tcp", "set", "global", "autotuninglevel=disabled"] in recorded_cmds


class TestWindowsSearchReindex:
    def test_reindex_windows_search_flow(self, mock_win32_admin, monkeypatch):
        """Verifica detención del servicio, simulación de registro y reinicio del servicio."""
        service_calls = []

        def mock_run(cmd, **kwargs):
            service_calls.append(cmd)
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "Servicio operado con éxito."
            mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Simular winreg si existe
        mock_winreg = MagicMock()
        monkeypatch.setattr(sys_optimizer, "winreg", mock_winreg)

        res = sys_optimizer.reindex_windows_search()
        assert res["success"] is True
        assert ["net", "stop", "WSearch"] in service_calls
        assert ["net", "start", "WSearch"] in service_calls
        assert mock_winreg.SetValueEx.called


class TestCompactOs:
    def test_get_compact_os_status_english_active(self, mock_win32_admin, monkeypatch):
        def mock_run(cmd, **kwargs):
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "The system is in the Compact state because it has been compressed by the user.\n"
            mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)
        res = sys_optimizer.get_compact_os_status()
        assert res["success"] is True
        assert res["is_compact"] is True

    def test_get_compact_os_status_english_inactive(self, mock_win32_admin, monkeypatch):
        def mock_run(cmd, **kwargs):
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "The system is not in the Compact state because Windows determined it is not beneficial.\n"
            mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)
        res = sys_optimizer.get_compact_os_status()
        assert res["success"] is True
        assert res["is_compact"] is False

    def test_get_compact_os_status_spanish_active(self, mock_win32_admin, monkeypatch):
        def mock_run(cmd, **kwargs):
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "El sistema está en estado Compacto porque se ha comprimido.\n"
            mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)
        res = sys_optimizer.get_compact_os_status()
        assert res["success"] is True
        assert res["is_compact"] is True

    def test_get_compact_os_status_spanish_inactive(self, mock_win32_admin, monkeypatch):
        def mock_run(cmd, **kwargs):
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "El sistema no está en estado Compacto.\n"
            mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)
        res = sys_optimizer.get_compact_os_status()
        assert res["success"] is True
        assert res["is_compact"] is False

    def test_toggle_compact_os_always_and_never(self, mock_win32_admin, monkeypatch):
        recorded_cmds = []

        def mock_run(cmd, **kwargs):
            recorded_cmds.append(cmd)
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "Operación completada con éxito."
            mock_res.stderr = ""
            return mock_res

        monkeypatch.setattr(subprocess, "run", mock_run)

        res_on = sys_optimizer.toggle_compact_os(enable=True)
        assert res_on["success"] is True
        assert res_on["is_compact"] is True
        assert ["compact.exe", "/compactos:always"] in recorded_cmds

        res_off = sys_optimizer.toggle_compact_os(enable=False)
        assert res_off["success"] is True
        assert res_off["is_compact"] is False
        assert ["compact.exe", "/compactos:never"] in recorded_cmds
