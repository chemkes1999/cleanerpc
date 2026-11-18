"""
Suite de pruebas unitarias para los módulos v2.4 de PyClean Pro:
- sys_monitor (procesos, protección de procesos críticos, validación DNS)
- hardware_health (parseo XML de batería, validación de letra TRIM, fallbacks)
- context_menu (protección de claves nativas, fallbacks multiplataforma)
- vault (cifrado AES-256-GCM, rechazo de contraseña incorrecta, CRUD, generador, fortaleza, backup)
"""

import os
import sys
import json
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sys_monitor
import hardware_health
import context_menu
import vault


# --- 1. Monitor de Procesos y Red ---

def test_critical_process_protection():
    assert sys_monitor.is_critical_process("lsass.exe", 500) is True
    assert sys_monitor.is_critical_process("svchost.exe", 800) is True
    assert sys_monitor.is_critical_process("System", 4) is True
    assert sys_monitor.is_critical_process("notepad.exe", 9999) is False

    # No debe permitir matar el propio proceso ni PID 0/4
    ok_self, _ = sys_monitor.terminate_process(os.getpid())
    assert ok_self is False


def test_get_top_processes_and_dns_validation():
    procs = sys_monitor.get_top_processes(sort_by="memory", limit=10)
    assert isinstance(procs, list)
    if sys_monitor.psutil is not None:
        assert len(procs) >= 1
        assert "pid" in procs[0]
        assert "memory_formatted" in procs[0]

    ok_bad_preset, _ = sys_monitor.set_dns_preset("Ethernet", "invalid_dns")
    assert ok_bad_preset is False

    ok_empty_adapter, _ = sys_monitor.set_dns_preset("", "cloudflare")
    assert ok_empty_adapter is False


# --- 2. Salud de Hardware (SSD & Batería) ---

def test_parse_battery_report_xml():
    sample_xml = """<?xml version="1.0" encoding="utf-8"?>
    <BatteryReport xmlns="http://schemas.microsoft.com/battery/2012">
      <Batteries>
        <Battery>
          <DesignCapacity>50000</DesignCapacity>
          <FullChargeCapacity>42500</FullChargeCapacity>
          <CycleCount>145</CycleCount>
        </Battery>
      </Batteries>
    </BatteryReport>
    """
    parsed = hardware_health.parse_battery_report_xml(sample_xml)
    assert parsed["design_capacity_mwh"] == 50000
    assert parsed["full_charge_capacity_mwh"] == 42500
    assert parsed["cycle_count"] == 145
    assert parsed["health_percent"] == 85.0
    assert parsed["wear_percent"] == 15.0


def test_run_ssd_trim_validation():
    # Previene inyección de comandos en la letra de unidad
    ok_bad, msg = hardware_health.run_ssd_trim("C; calc.exe")
    assert ok_bad is False
    assert "inválida" in msg.lower()

    disks = hardware_health.get_disk_health()
    assert isinstance(disks, list)


# --- 3. Gestor del Menú Contextual ---

def test_context_menu_protection():
    assert context_menu.is_protected_context_key("open") is True
    assert context_menu.is_protected_context_key("PowerShell") is True
    assert context_menu.is_protected_context_key("MyCustomAppMenu") is False

    items = context_menu.get_context_menu_items()
    assert isinstance(items, list)


# --- 4. Bóveda Local de Contraseñas (AES-256-GCM) ---

@pytest.mark.skipif(not vault.CRYPTO_AVAILABLE, reason="cryptography no instalado")
def test_vault_full_lifecycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        v_path = os.path.join(tmp_dir, "test_vault.enc")
        backup_path = os.path.join(tmp_dir, "backup.vault")

        # Usar iteraciones reducidas en test para velocidad (en producción son 600,000)
        v = vault.PasswordVault(vault_path=v_path, iterations=10_000)
        assert v.exists() is False
        assert v.is_unlocked() is False

        # Contraseña maestra demasiado corta debe rechazarse
        ok_short, _ = v.create("12345")
        assert ok_short is False

        # Crear bóveda válida
        ok_create, _ = v.create("MasterPass#2026!")
        assert ok_create is True
        assert v.exists() is True
        assert v.is_unlocked() is True

        # Guardar credencial
        ok_save, entry = v.save_entry(
            title="GitHub",
            username="chemkes1999",
            password="SuperSecretPassword!99",
            url="https://github.com",
            category="Desarrollo",
            notes="2FA activo",
        )
        assert ok_save is True
        assert entry["title"] == "GitHub"

        # Verificar que el archivo en disco está cifrado (no contiene texto plano)
        with open(v_path, "r", encoding="utf-8") as f:
            raw_disk = f.read()
        assert "SuperSecretPassword!99" not in raw_disk
        assert "chemkes1999" not in raw_disk
        envelope_1 = json.loads(raw_disk)

        # Actualizar credencial y verificar que el nonce GCM cambia en cada guardado
        ok_upd, _ = v.save_entry(
            title="GitHub Pro",
            username="chemkes1999",
            password="UpdatedPassword!2026",
            entry_id=entry["id"],
        )
        assert ok_upd is True
        with open(v_path, "r", encoding="utf-8") as f:
            envelope_2 = json.load(f)
        assert envelope_1["nonce"] != envelope_2["nonce"]

        # Bloquear y probar contraseña maestra incorrecta
        v.lock()
        assert v.is_unlocked() is False
        ok_bad_unlock, _ = v.unlock("WrongMasterPass!")
        assert ok_bad_unlock is False
        assert v.is_unlocked() is False

        # Desbloquear con contraseña correcta y verificar datos
        ok_unlock, _ = v.unlock("MasterPass#2026!")
        assert ok_unlock is True
        entries = v.list_entries()
        assert len(entries) == 1
        assert entries[0]["title"] == "GitHub Pro"
        assert entries[0]["password"] == "UpdatedPassword!2026"

        # Exportar respaldo cifrado
        ok_exp, _ = v.export_encrypted_backup(backup_path)
        assert ok_exp is True
        assert os.path.exists(backup_path)

        # Eliminar credencial
        ok_del, _ = v.delete_entry(entry["id"])
        assert ok_del is True
        assert len(v.list_entries()) == 0


def test_password_generator_and_strength():
    pwd = vault.generate_password(length=24, use_upper=True, use_lower=True, use_digits=True, use_symbols=True)
    assert len(pwd) == 24
    assert any(c.isupper() for c in pwd)
    assert any(c.islower() for c in pwd)
    assert any(c.isdigit() for c in pwd)

    strong = vault.evaluate_password_strength(pwd)
    assert strong["score"] == 4
    assert strong["entropy_bits"] > 100

    weak = vault.evaluate_password_strength("12345")
    assert weak["score"] == 1


# --- 5. Soporte macOS (Categorías y Estadísticas de Sistema) ---

def test_macos_target_categories_and_system_stats(monkeypatch):
    import cleaner

    monkeypatch.setattr(cleaner.sys, "platform", "darwin")
    cats = cleaner.get_target_categories()
    assert "macos_user_caches" in cats
    assert "macos_user_logs" in cats
    assert "macos_trash" in cats
    assert "dev_tools" in cats
    assert any("Library/Caches" in p.replace("\\", "/") for p in cats["macos_user_caches"]["paths"])

    stats = cleaner.get_system_stats()
    assert stats["ram_total"] > 0
    assert 0 <= stats["ram_load"] <= 100

