"""
Pruebas unitarias para el Centro de Análisis, Calibración y Optimización de Batería
en hardware_health.py y su exposición en web_gui.py.
"""

import os
import sys
import subprocess
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import hardware_health


def test_parse_battery_report_xml_extended_metadata_and_history():
    sample_xml = """<?xml version="1.0" encoding="utf-8"?>
    <BatteryReport xmlns="http://schemas.microsoft.com/battery/2012">
      <Batteries>
        <Battery>
          <Id>L19C3PF7</Id>
          <Manufacturer>SMP</Manufacturer>
          <SerialNumber>12345</SerialNumber>
          <Chemistry>LION</Chemistry>
          <DesignCapacity>55997</DesignCapacity>
          <FullChargeCapacity>36737</FullChargeCapacity>
          <CycleCount>0</CycleCount>
        </Battery>
      </Batteries>
      <History>
        <HistoryEntry LocalStartDate="2026-09-01T00:00:00" FullChargeCapacity="40000" DesignCapacity="55997" />
        <HistoryEntry LocalStartDate="2026-10-01T00:00:00" FullChargeCapacity="38000" DesignCapacity="55997" />
        <HistoryEntry LocalStartDate="2026-11-01T00:00:00" FullChargeCapacity="36737" DesignCapacity="55997" />
      </History>
    </BatteryReport>
    """
    parsed = hardware_health.parse_battery_report_xml(sample_xml)
    assert parsed["design_capacity_mwh"] == 55997
    assert parsed["full_charge_capacity_mwh"] == 36737
    assert parsed["cycle_count"] == 0
    assert parsed["cycle_count_reported"] is False
    assert parsed["health_percent"] == 65.6
    assert parsed["wear_percent"] == 34.4
    assert parsed["manufacturer"] == "SMP"
    assert parsed["chemistry"] == "LION"
    assert parsed["device_name"] == "L19C3PF7"
    assert len(parsed["capacity_history"]) == 3
    assert parsed["capacity_history"][-1]["date"] == "2026-11-01"
    assert parsed["capacity_history"][-1]["health_percent"] == 65.6


def test_parse_energy_report_xml():
    sample_energy_xml = """<?xml version="1.0" encoding="utf-8"?>
    <EnergyReport xmlns="http://schemas.microsoft.com/energy/2007">
      <Troubleshooter>
        <Warning>
          <Category>CPU</Category>
          <Name>Uso elevado de procesador</Name>
          <Description>Un proceso mantuvo el CPU activo.</Description>
        </Warning>
        <Error>
          <Category>USB</Category>
          <Name>Dispositivo USB no entra en suspensión selectiva</Name>
          <Description>Controlador USB bloqueando estado de bajo consumo.</Description>
        </Error>
      </Troubleshooter>
    </EnergyReport>
    """
    parsed = hardware_health.parse_energy_report_xml(sample_energy_xml)
    assert parsed["errors_count"] == 1
    assert parsed["warnings_count"] == 1
    assert len(parsed["findings"]) == 2
    # Errores deben aparecer antes que advertencias
    assert parsed["findings"][0]["severity"] == "error"
    assert "USB" in parsed["findings"][0]["name"]


def test_oem_tips_and_diagnosis_levels():
    assert "Lenovo Vantage" in hardware_health.get_oem_charge_limit_tip("LENOVO")
    assert "MyASUS" in hardware_health.get_oem_charge_limit_tip("ASUSTeK COMPUTER INC.")
    assert "Dell Power Manager" in hardware_health.get_oem_charge_limit_tip("Dell Inc.")
    assert "BIOS" in hardware_health.get_oem_charge_limit_tip("Generic Brand")

    diag_fair = hardware_health.build_battery_diagnosis({
        "health_percent": 65.6,
        "wear_percent": 34.4,
        "power_plugged": True,
        "percent": 100.0,
        "oem_charge_limit_tip": hardware_health.get_oem_charge_limit_tip("Lenovo"),
    })
    assert diag_fair["level"] == "fair"
    assert any("100%" in r for r in diag_fair["recommendations"])
    assert any("Lenovo Vantage" in r for r in diag_fair["recommendations"])

    diag_crit = hardware_health.build_battery_diagnosis({
        "health_percent": 32.0,
        "wear_percent": 68.0,
        "power_plugged": False,
        "percent": 50.0,
    })
    assert diag_crit["level"] == "critical"


def test_optimize_battery_performance_and_restore(monkeypatch, tmp_path):
    monkeypatch.setattr(hardware_health, "_get_state_dir", lambda: str(tmp_path))
    monkeypatch.setattr(hardware_health.sys, "platform", "win32")

    executed = []

    def fake_run_cmd(args, timeout=15):
        executed.append(args)
        if args == ["powercfg", "/getactivescheme"]:
            return subprocess.CompletedProcess(
                args, 0,
                stdout="Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Equilibrado)\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args, 0, stdout="OK", stderr="")

    monkeypatch.setattr(hardware_health, "_run_cmd", fake_run_cmd)

    # Perfil inválido rechazado
    bad = hardware_health.optimize_battery_performance("invalid_profile")
    assert bad["success"] is False

    # Perfil autonomía aplica ajustes y crea respaldo
    res_auto = hardware_health.optimize_battery_performance("autonomy")
    assert res_auto["success"] is True
    assert hardware_health.has_battery_power_backup() is True
    assert any("PROCTHROTTLEMAX" in " ".join(c) and "80" in c for c in executed)

    # Perfil rendimiento
    res_perf = hardware_health.optimize_battery_performance("performance")
    assert res_perf["success"] is True
    assert any("PROCTHROTTLEMAX" in " ".join(c) and "95" in c for c in executed)

    # Restauración elimina el archivo de respaldo
    res_restore = hardware_health.restore_battery_power_backup()
    assert res_restore["success"] is True
    assert hardware_health.has_battery_power_backup() is False


def test_repair_battery_driver_requires_admin_and_succeeds(monkeypatch):
    monkeypatch.setattr(hardware_health.sys, "platform", "win32")
    monkeypatch.setattr(hardware_health.cleaner, "is_admin", lambda: False)
    res_no_admin = hardware_health.repair_battery_driver()
    assert res_no_admin["success"] is False
    assert "Administrador" in res_no_admin["message"]

    monkeypatch.setattr(hardware_health.cleaner, "is_admin", lambda: True)
    monkeypatch.setattr(
        hardware_health,
        "_run_cmd",
        lambda args, timeout=35: subprocess.CompletedProcess(args, 0, stdout="OK:1\n", stderr=""),
    )
    res_ok = hardware_health.repair_battery_driver()
    assert res_ok["success"] is True


def test_battery_calibration_lifecycle(monkeypatch, tmp_path):
    monkeypatch.setattr(hardware_health, "_get_state_dir", lambda: str(tmp_path))
    monkeypatch.setattr(hardware_health.sys, "platform", "win32")
    monkeypatch.setattr(
        hardware_health,
        "_run_cmd",
        lambda args, timeout=15: subprocess.CompletedProcess(args, 0, stdout="", stderr=""),
    )

    snapshots = iter([
        {
            "has_battery": True,
            "percent": 100.0,
            "full_charge_capacity_mwh": 36737,
            "design_capacity_mwh": 55997,
            "health_percent": 65.6,
        },
        {
            "has_battery": True,
            "percent": 100.0,
            "full_charge_capacity_mwh": 39500,
            "design_capacity_mwh": 55997,
            "health_percent": 70.5,
        },
    ])
    monkeypatch.setattr(hardware_health, "get_battery_health", lambda: next(snapshots))

    start_res = hardware_health.start_battery_calibration()
    assert start_res["success"] is True
    assert hardware_health.get_battery_calibration_state()["active"] is True

    finish_res = hardware_health.finish_battery_calibration()
    assert finish_res["success"] is True
    assert finish_res["delta_mwh"] == 39500 - 36737
    assert finish_res["delta_health"] == 4.9
    assert "Mejora detectada" in finish_res["message"]
    assert hardware_health.get_battery_calibration_state()["active"] is False
