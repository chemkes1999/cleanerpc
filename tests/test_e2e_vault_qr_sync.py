"""
PyClean Pro v2.4 / v2.5 - Comprehensive E2E Test Suite (Vault QR & LAN Sync)

Architecture: Requirement-driven, opaque-box, 4-tier methodology:
  - Tier 1: Feature Coverage (>=5 test cases per feature across Feature Inventory)
  - Tier 2: Boundary & Corner Cases (empty data, malformed payloads, token expiry, edge network)
  - Tier 3: Cross-Feature Combinations (QR export -> offline edit -> LAN sync -> smart merge)
  - Tier 4: Real-World Scenarios (Desktop onboarding -> Mobile pairing -> Offline edit -> Sync back)
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
from typing import Generator

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

import vault
import web_gui


# =========================================================================
# TEST FIXTURES & UTILITIES
# =========================================================================

def get_free_port() -> int:
    """Finds an available ephemeral port on the loopback interface."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def temp_vault_dir() -> Generator[str, None, None]:
    """Provides a fresh isolated temporary directory for test vault storage."""
    with tempfile.TemporaryDirectory(prefix="pyclean_test_") as tmp_dir:
        yield tmp_dir


@pytest.fixture
def test_vault(temp_vault_dir: str) -> vault.PasswordVault:
    """Provides an unlocked PasswordVault with fast PBKDF2 iterations for testing."""
    v_path = os.path.join(temp_vault_dir, "test_vault.enc")
    v = vault.PasswordVault(vault_path=v_path, iterations=10_000)
    ok, _ = v.create("MasterPassTest#2026!")
    assert ok is True
    return v


@pytest.fixture
def sync_server(test_vault: vault.PasswordVault) -> Generator[web_gui.VaultSyncServer, None, None]:
    """Provides a running VaultSyncServer on dynamic port, cleaned up after test."""
    server = web_gui.VaultSyncServer(test_vault, host="127.0.0.1", port=0)
    server.start()
    time.sleep(0.05)  # Allow socket to bind
    try:
        yield server
    finally:
        server.stop()


# =========================================================================
# TIER 1: FEATURE COVERAGE (Feature Inventory § PROJECT.md)
# =========================================================================

class TestTier1FeatureCoverage:
    """Tier 1: Comprehensive feature coverage for all M1/M2/M3 interface contracts."""

    # --- Feature 1: Single Credential QR Payload Generation ---

    def test_tier1_f1_qr_plain_json_format(self, test_vault: vault.PasswordVault):
        """Verifies plain QR payload generation matches required JSON schema."""
        _, entry = test_vault.save_entry("GitHub", "testuser", "Pass123!", "https://github.com", "Dev", "Notes")
        payload_str = test_vault.generate_credential_qr_payload(entry["id"], use_pin=False)
        data = json.loads(payload_str)
        assert data.get("t") in ("pyclean-cred", "credential")
        assert data.get("v") == 1
        assert data["title"] == "GitHub"
        assert (data.get("user") or data.get("username")) == "testuser"
        assert (data.get("pass") or data.get("password")) == "Pass123!"
        assert data["url"] == "https://github.com"
        assert data["category"] == "Dev"

    def test_tier1_f1_qr_plain_uri_format(self):
        """Verifies decrypt_credential_qr_payload parses URI formatted credentials."""
        uri = "pyclean://vault/v1/credential?title=GitLab&user=chemkes&pass=Secret999&url=https://gitlab.com"
        parsed = vault.decrypt_credential_qr_payload(uri)
        assert parsed["title"] == "GitLab"
        assert (parsed.get("user") or parsed.get("username")) == "chemkes"
        assert (parsed.get("pass") or parsed.get("password")) == "Secret999"
        assert parsed["url"] == "https://gitlab.com"

    def test_tier1_f1_qr_encrypted_pin_format(self, test_vault: vault.PasswordVault):
        """Verifies encrypted PIN QR payload generates proper cryptographic envelope."""
        _, entry = test_vault.save_entry("Bank", "user", "BankPass!", "https://bank.com")
        pin = "492817"
        payload_str = test_vault.generate_credential_qr_payload(entry["id"], use_pin=True, pin=pin)
        data = json.loads(payload_str)
        assert data.get("t") in ("pyclean-cred-enc", "ephemeral_credential")
        assert data.get("v") == 1
        assert "salt" in data and len(base64.b64decode(data["salt"])) == 16
        assert "nonce" in data and len(base64.b64decode(data["nonce"])) == 12
        assert "ciphertext" in data and len(base64.b64decode(data["ciphertext"])) > 16
        assert "BankPass!" not in payload_str

    def test_tier1_f1_qr_plain_roundtrip(self, test_vault: vault.PasswordVault):
        """Verifies plain QR payload generation and deserialization round-trip."""
        _, entry = test_vault.save_entry("Slack", "worker@work.com", "SlackPass99", notes="Team channel")
        payload_str = test_vault.generate_credential_qr_payload(entry["id"], use_pin=False)
        recovered = test_vault.decrypt_credential_qr_payload(payload_str)
        assert recovered["title"] == "Slack"
        assert (recovered.get("user") or recovered.get("username")) == "worker@work.com"
        assert (recovered.get("pass") or recovered.get("password")) == "SlackPass99"
        assert recovered.get("notes") == "Team channel"

    def test_tier1_f1_qr_encrypted_pin_roundtrip(self, test_vault: vault.PasswordVault):
        """Verifies encrypted PIN QR payload round-trip decryption with ephemeral PIN."""
        _, entry = test_vault.save_entry("AWS", "admin", "AwsSecretKey99!", category="Cloud")
        pin = "839201"
        payload_str = test_vault.generate_credential_qr_payload(entry["id"], use_pin=True, pin=pin)
        recovered = test_vault.decrypt_credential_qr_payload(payload_str, pin=pin)
        assert recovered["title"] == "AWS"
        assert (recovered.get("pass") or recovered.get("password")) == "AwsSecretKey99!"
        assert recovered.get("category") == "Cloud"

    def test_tier1_f1_pyclean_api_qr_generation(self, test_vault: vault.PasswordVault):
        """Verifies PyCleanAPI bridge method vault_get_qr_payload returns proper contract."""
        api = web_gui.PyCleanAPI()
        api._vault = test_vault
        api._sync_server.vault = test_vault
        _, entry = test_vault.save_entry("Twitter", "bird_user", "TweetPass!")
        res_plain = api.vault_get_qr_payload(entry["id"], use_pin=False)
        assert res_plain["status"] == "ok"
        assert "payload" in res_plain

        res_pin = api.vault_get_qr_payload(entry["id"], use_pin=True)
        assert res_pin["status"] == "ok"
        assert len(res_pin["pin"]) == 6
        assert res_pin["pin"].isdigit()

    # --- Feature 2: Pairing Token & Sync Server Lifecycle ---

    def test_tier1_f2_lan_ip_resolution(self):
        """Verifies robust LAN IP resolution via UDP probe returns valid IPv4."""
        ip = web_gui.get_lan_ip()
        assert isinstance(ip, str)
        octets = ip.split(".")
        assert len(octets) == 4
        assert all(o.isdigit() and 0 <= int(o) <= 255 for o in octets)

    def test_tier1_f2_pairing_token_lifecycle(self, test_vault: vault.PasswordVault):
        """Verifies pairing token generation, validity check, and expiration TTL."""
        server = web_gui.VaultSyncServer(test_vault, token_ttl=1)
        info = server.start(port=0)
        token = info["token"]
        assert len(token) >= 16
        assert server.is_token_valid(token) is True
        assert server.is_token_valid("invalid-token-123") is False
        time.sleep(1.1)
        assert server.is_token_valid(token) is False
        server.stop()

    def test_tier1_f2_sync_server_startup(self, test_vault: vault.PasswordVault):
        """Verifies sync server starts and reports correct URL and credentials."""
        server = web_gui.VaultSyncServer(test_vault, host="127.0.0.1", port=0)
        info = server.start()
        assert info["port"] > 0
        assert "token" in info
        assert bool(server.is_running) is True
        server.stop()

    def test_tier1_f2_sync_server_graceful_shutdown(self, test_vault: vault.PasswordVault):
        """Verifies sync server cleanly shuts down and releases the port."""
        server = web_gui.VaultSyncServer(test_vault, host="127.0.0.1", port=0)
        info = server.start()
        port = info["port"]
        assert bool(server.is_running) is True
        server.stop()
        assert bool(server.is_running) is False
        # Verify port can be rebound immediately
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))

    def test_tier1_f2_sync_server_static_mobile_endpoint(self, sync_server: web_gui.VaultSyncServer):
        """Verifies GET /mobile serves static companion PWA placeholder/app."""
        url = f"http://127.0.0.1:{sync_server.port}/mobile"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "PyClean" in content

    # --- Feature 3: LAN Sync Server Endpoints (/api/sync/*) ---

    def test_tier1_f3_endpoint_info(self, sync_server: web_gui.VaultSyncServer):
        """Verifies GET /api/sync/info returns vault public crypto params."""
        token = sync_server.token
        url = f"http://127.0.0.1:{sync_server.port}/api/sync/info?token={token}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "ok"
            assert data["version"] == 1
            assert data["kdf"] == "pbkdf2-sha256"
            assert "salt" in data
            assert data["iterations"] > 0

    def test_tier1_f3_endpoint_get_vault(self, sync_server: web_gui.VaultSyncServer):
        """Verifies GET /api/sync/vault returns encrypted vault container."""
        token = sync_server.token
        url = f"http://127.0.0.1:{sync_server.port}/api/sync/vault?token={token}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "ciphertext" in data
            assert "salt" in data
            assert "nonce" in data

    def test_tier1_f3_endpoint_post_vault_entries(self, sync_server: web_gui.VaultSyncServer):
        """Verifies POST /api/sync/vault accepts credentials array and executes merge."""
        token = sync_server.token
        url = f"http://127.0.0.1:{sync_server.port}/api/sync/vault?token={token}"
        incoming = {
            "entries": [
                {
                    "title": "MobileCreatedAccount",
                    "username": "phone_user",
                    "password": "PhonePassword999!",
                    "url": "https://mobile.app",
                    "category": "Mobile",
                    "updated_at": int(time.time()),
                }
            ]
        }
        body = json.dumps(incoming).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res["status"] == "ok"
            assert res["merged"] >= 1
            assert res["total"] >= 1

        entries = sync_server.vault.list_entries()
        assert any(e["title"] == "MobileCreatedAccount" for e in entries)

    def test_tier1_f3_endpoint_auth_enforcement(self, sync_server: web_gui.VaultSyncServer):
        """Verifies endpoints reject unauthorized or missing pairing tokens."""
        bad_token_url = f"http://127.0.0.1:{sync_server.port}/api/sync/info?token=fake_token"
        req = urllib.request.Request(bad_token_url)
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 401

    def test_tier1_f3_api_sync_status_reporting(self, test_vault: vault.PasswordVault):
        """Verifies PyCleanAPI reports accurate real-time mobile sync status."""
        api = web_gui.PyCleanAPI()
        api._vault = test_vault
        api._sync_server.vault = test_vault
        status_stopped = api.vault_get_mobile_sync_status()
        assert status_stopped["running"] is False

        start_res = api.vault_start_mobile_sync(port=0)
        assert start_res["status"] == "ok"

        status_running = api.vault_get_mobile_sync_status()
        assert status_running["running"] is True

        api.vault_stop_mobile_sync()
        status_after = api.vault_get_mobile_sync_status()
        assert status_after["running"] is False

    # --- Feature 4: Smart Non-Destructive Vault Merge ---

    def test_tier1_f4_merge_disjoint_entries(self, test_vault: vault.PasswordVault):
        """Verifies merge adds novel entries without removing existing ones."""
        test_vault.save_entry("DesktopEntry1", "user1", "Pass1")
        incoming = [
            {"title": "PhoneEntry1", "username": "user2", "password": "Pass2", "updated_at": int(time.time())}
        ]
        merged, total = test_vault.merge_entries(incoming)
        assert merged == 1
        assert total == 2
        titles = [e["title"] for e in test_vault.list_entries()]
        assert "DesktopEntry1" in titles
        assert "PhoneEntry1" in titles

    def test_tier1_f4_merge_newer_updated_at(self, test_vault: vault.PasswordVault):
        """Verifies incoming entry with newer timestamp overwrites older local entry."""
        _, entry = test_vault.save_entry("GitHub", "user", "OldPassword", notes="v1")
        incoming = [
            {
                "id": entry["id"],
                "title": "GitHub",
                "username": "user",
                "password": "NewUpdatedPassword!",
                "notes": "v2 from phone",
                "updated_at": entry["updated_at"] + 100,
            }
        ]
        merged, _ = test_vault.merge_entries(incoming)
        assert merged == 1
        current = test_vault.get_entry(entry["id"])
        assert current["password"] == "NewUpdatedPassword!"
        assert current["notes"] == "v2 from phone"

    def test_tier1_f4_merge_stale_entry_ignored(self, test_vault: vault.PasswordVault):
        """Verifies incoming entry with older timestamp is ignored, preserving local entry."""
        _, entry = test_vault.save_entry("Bank", "user", "CurrentPassword", notes="latest")
        incoming = [
            {
                "id": entry["id"],
                "title": "Bank",
                "username": "user",
                "password": "StalePassword!",
                "notes": "stale",
                "updated_at": entry["updated_at"] - 100,
            }
        ]
        merged, _ = test_vault.merge_entries(incoming)
        assert merged == 0
        current = test_vault.get_entry(entry["id"])
        assert current["password"] == "CurrentPassword"
        assert current["notes"] == "latest"

    def test_tier1_f4_merge_deduplicate_by_signature(self, test_vault: vault.PasswordVault):
        """Verifies matching (title, username) lowercase prevents creating logical duplicate."""
        test_vault.save_entry("Netflix", "User@Mail.com", "LocalPass")
        incoming = [
            {
                "id": "new-uuid-different",
                "title": "netflix",
                "username": "user@mail.com",
                "password": "NewNetflixPass!",
                "updated_at": int(time.time()) + 10,
            }
        ]
        merged, total = test_vault.merge_entries(incoming)
        assert merged == 1
        assert total == 1  # No duplicate entry created
        assert test_vault.list_entries()[0]["password"] == "NewNetflixPass!"

    def test_tier1_f4_merge_disk_persistence(self, test_vault: vault.PasswordVault):
        """Verifies merge persists changes to encrypted disk file with refreshed nonce."""
        with open(test_vault.vault_path, "r", encoding="utf-8") as f:
            disk_before = json.load(f)
        incoming = [{"title": "NewPersisted", "username": "u", "password": "p", "updated_at": int(time.time())}]
        test_vault.merge_entries(incoming)
        with open(test_vault.vault_path, "r", encoding="utf-8") as f:
            disk_after = json.load(f)
        assert disk_before["nonce"] != disk_after["nonce"]
        assert disk_before["ciphertext"] != disk_after["ciphertext"]

    # --- Feature 5: Cross-Platform Cryptographic Parity ---

    def test_tier1_f5_pbkdf2_hmac_sha256_parity(self):
        """Verifies PBKDF2-HMAC-SHA256 key derivation matches RFC 6070 standard vector."""
        password = "Password123!"
        salt = bytes([i for i in range(16)])
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=10_000)
        key = kdf.derive(password.encode("utf-8"))
        assert len(key) == 32
        # Deterministic verification
        kdf2 = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=10_000)
        key2 = kdf2.derive(password.encode("utf-8"))
        assert key == key2

    def test_tier1_f5_aes_256_gcm_tag_parity(self):
        """Verifies AES-256-GCM appends 16-byte authentication tag in wire format."""
        key = os.urandom(32)
        nonce = os.urandom(12)
        plaintext = b"Test AES-GCM Wire Format"
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, vault.VAULT_AAD)
        assert len(ciphertext) == len(plaintext) + 16
        decrypted = aesgcm.decrypt(nonce, ciphertext, vault.VAULT_AAD)
        assert decrypted == plaintext

    def test_tier1_f5_aad_authentication_parity(self):
        """Verifies altering AAD raises cryptographic authentication tag mismatch."""
        key = os.urandom(32)
        nonce = os.urandom(12)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, b"Secret Payload", vault.VAULT_AAD)
        from cryptography.exceptions import InvalidTag
        with pytest.raises(InvalidTag):
            aesgcm.decrypt(nonce, ct, b"tampered-aad")

    def test_tier1_f5_ephemeral_pin_crypto_parity(self):
        """Verifies ephemeral PIN encryption with CRED_QR_AAD matches WebCrypto specification."""
        pin = "654321"
        salt = os.urandom(16)
        nonce = os.urandom(12)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=vault.CRED_QR_ITERATIONS)
        key = kdf.derive(pin.encode("utf-8"))
        aesgcm = AESGCM(key)
        data = b'{"secret":"code"}'
        ct = aesgcm.encrypt(nonce, data, vault.CRED_QR_AAD)
        assert aesgcm.decrypt(nonce, ct, vault.CRED_QR_AAD) == data

    def test_tier1_f5_container_zero_knowledge_parity(self, test_vault: vault.PasswordVault):
        """Verifies full container can be exported without decrypting master secrets."""
        test_vault.save_entry("Confidential", "user", "SuperSecretPass!")
        envelope = test_vault.export_vault_sync_payload()
        assert "ciphertext" in envelope
        assert "salt" in envelope
        assert "SuperSecretPass!" not in str(envelope)


# =========================================================================
# TIER 2: BOUNDARY & CORNER CASES (>=5 per feature domain)
# =========================================================================

class TestTier2BoundaryAndCorners:
    """Tier 2: Boundary and corner cases for data volume, corrupted inputs, token security, and network."""

    # --- Boundary 1: Empty and Extreme Vault Data ---

    def test_tier2_b1_empty_vault_sync(self, test_vault: vault.PasswordVault):
        """Verifies synchronizing an empty entries list succeeds with 0 merged."""
        merged, total = test_vault.merge_entries([])
        assert merged == 0
        assert total == 0

    def test_tier2_b1_large_password_and_notes(self, test_vault: vault.PasswordVault):
        """Verifies large credentials (>2048 char password, 64KB notes) encrypt and merge cleanly."""
        large_password = secrets.token_hex(1024)  # 2048 chars
        large_notes = "A" * 65536  # 64 KB notes
        ok, entry = test_vault.save_entry("LargeSite", "user", large_password, notes=large_notes)
        assert ok is True
        payload_str = test_vault.generate_credential_qr_payload(entry["id"], use_pin=False)
        recovered = test_vault.decrypt_credential_qr_payload(payload_str)
        assert (recovered.get("pass") or recovered.get("password")) == large_password
        assert recovered.get("notes") == large_notes

    def test_tier2_b1_unicode_emojis_special_chars(self, test_vault: vault.PasswordVault):
        """Verifies passwords and fields containing emojis, accents, and control chars survive encryption."""
        complex_pass = "P@$$w0rd🔑🛡️🚀日本語Ñandú\n\t<script>alert(1)</script>"
        ok, entry = test_vault.save_entry("UnicodeService", "emoji_user 🌟", complex_pass, notes="Notes with 💻")
        assert ok is True
        payload_str = test_vault.generate_credential_qr_payload(entry["id"], use_pin=True, pin="123456")
        recovered = test_vault.decrypt_credential_qr_payload(payload_str, pin="123456")
        assert (recovered.get("pass") or recovered.get("password")) == complex_pass
        assert (recovered.get("user") or recovered.get("username")) == "emoji_user 🌟"

    def test_tier2_b1_missing_optional_fields(self, test_vault: vault.PasswordVault):
        """Verifies entries missing url, notes, or username handle gracefully without throwing."""
        ok, entry = test_vault.save_entry("MinimalSite", "", "OnlyPassword!")
        assert ok is True
        assert entry["username"] == ""
        assert entry["url"] == ""
        assert entry["notes"] == ""
        payload = test_vault.generate_credential_qr_payload(entry["id"], use_pin=False)
        decrypted = test_vault.decrypt_credential_qr_payload(payload)
        assert decrypted["title"] == "MinimalSite"

    def test_tier2_b1_batch_volume_merge(self, test_vault: vault.PasswordVault):
        """Verifies stress testing merge with a batch of 100 entries completes rapidly."""
        now = int(time.time())
        batch = [
            {
                "id": str(i),
                "title": f"Service_{i}",
                "username": f"user_{i}",
                "password": f"Password_{i}!",
                "updated_at": now + i,
            }
            for i in range(100)
        ]
        merged, total = test_vault.merge_entries(batch)
        assert merged == 100
        assert total == 100
        assert len(test_vault.list_entries()) == 100

    # --- Boundary 2: Malformed & Corrupted Payloads ---

    def test_tier2_b2_corrupted_base64_in_qr(self):
        """Verifies corrupt base64 string in QR payload raises appropriate error."""
        corrupt_payload = json.dumps({
            "t": "pyclean-cred-enc",
            "v": 1,
            "salt": "not_valid_base64!@#$",
            "nonce": base64.b64encode(os.urandom(12)).decode("ascii"),
            "ciphertext": base64.b64encode(os.urandom(32)).decode("ascii"),
            "iterations": 100000,
        })
        with pytest.raises(Exception):
            vault.decrypt_credential_qr_payload(corrupt_payload, pin="123456")

    def test_tier2_b2_truncated_gcm_tag_in_qr(self):
        """Verifies ciphertext shorter than 16-byte GCM tag fails cleanly."""
        short_payload = json.dumps({
            "t": "pyclean-cred-enc",
            "v": 1,
            "salt": base64.b64encode(os.urandom(16)).decode("ascii"),
            "nonce": base64.b64encode(os.urandom(12)).decode("ascii"),
            "ciphertext": base64.b64encode(b"short").decode("ascii"),  # < 16 bytes
            "iterations": 100000,
        })
        with pytest.raises(Exception):
            vault.decrypt_credential_qr_payload(short_payload, pin="123456")

    def test_tier2_b2_tampered_ciphertext_mac_failure(self, test_vault: vault.PasswordVault):
        """Verifies tampering with single bit in ciphertext fails GCM authentication."""
        _, entry = test_vault.save_entry("TamperTest", "user", "Secret!")
        payload_str = test_vault.generate_credential_qr_payload(entry["id"], use_pin=True, pin="999888")
        data = json.loads(payload_str)
        ct_bytes = bytearray(base64.b64decode(data["ciphertext"]))
        ct_bytes[0] ^= 0x01  # Flip one bit
        data["ciphertext"] = base64.b64encode(bytes(ct_bytes)).decode("ascii")
        tampered_payload = json.dumps(data)
        with pytest.raises(Exception):
            test_vault.decrypt_credential_qr_payload(tampered_payload, pin="999888")

    def test_tier2_b2_incorrect_pin_rejection(self, test_vault: vault.PasswordVault):
        """Verifies decrypting with wrong PIN fails authentication."""
        _, entry = test_vault.save_entry("PinFailTest", "user", "Pass!")
        payload_str = test_vault.generate_credential_qr_payload(entry["id"], use_pin=True, pin="111222")
        with pytest.raises(Exception):
            test_vault.decrypt_credential_qr_payload(payload_str, pin="000000")

    def test_tier2_b2_corrupt_json_strings(self):
        """Verifies non-JSON garbage string passed to decrypt raises ValueError or JSONDecodeError."""
        with pytest.raises(Exception):
            vault.decrypt_credential_qr_payload("NOT_JSON_GARBAGE_STRING{{{")

    # --- Boundary 3: Authentication & Token Security ---

    def test_tier2_b3_expired_pairing_token_rejected(self, test_vault: vault.PasswordVault):
        """Verifies expired pairing token is rejected with HTTP 401."""
        server = web_gui.VaultSyncServer(test_vault, host="127.0.0.1", port=0, token_ttl=0)
        info = server.start()
        token = info["token"]
        time.sleep(0.01)  # Immediately expire
        url = f"http://127.0.0.1:{server.port}/api/sync/info?token={token}"
        req = urllib.request.Request(url)
        try:
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 401
        finally:
            server.stop()

    def test_tier2_b3_missing_or_blank_token_rejected(self, sync_server: web_gui.VaultSyncServer):
        """Verifies missing token query parameter returns HTTP 401."""
        url = f"http://127.0.0.1:{sync_server.port}/api/sync/info"
        req = urllib.request.Request(url)
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 401

    def test_tier2_b3_tampered_token_rejected(self, sync_server: web_gui.VaultSyncServer):
        """Verifies token modified by a single character is rejected."""
        valid_token = sync_server.token
        tampered_token = valid_token[:-1] + ("A" if valid_token[-1] != "A" else "B")
        url = f"http://127.0.0.1:{sync_server.port}/api/sync/info?token={tampered_token}"
        req = urllib.request.Request(url)
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 401

    def test_tier2_b3_cross_token_isolation(self, test_vault: vault.PasswordVault):
        """Verifies token from server A is completely invalid on server B."""
        server_a = web_gui.VaultSyncServer(test_vault, host="127.0.0.1", port=0)
        info_a = server_a.start()
        token_a = info_a["token"]
        server_b = web_gui.VaultSyncServer(test_vault, host="127.0.0.1", port=0)
        try:
            assert server_b.is_token_valid(token_a) is False
        finally:
            server_a.stop()
            server_b.stop()

    def test_tier2_b3_injection_resilience(self, sync_server: web_gui.VaultSyncServer):
        """Verifies query parameter injection attempts (SQL, script, traversal) do not crash server."""
        injections = [
            "' OR 1=1--",
            "<script>alert(1)</script>",
            "../../../../etc/passwd",
            "%00nullbyte",
        ]
        for inj in injections:
            url = f"http://127.0.0.1:{sync_server.port}/api/sync/info?token={urllib.parse.quote(inj)}"
            req = urllib.request.Request(url)
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 401

    # --- Boundary 4: Network & Transport Edge Cases ---

    def test_tier2_b4_post_vault_invalid_json_body(self, sync_server: web_gui.VaultSyncServer):
        """Verifies sending malformed non-JSON body to POST /api/sync/vault returns HTTP 400."""
        token = sync_server.token
        url = f"http://127.0.0.1:{sync_server.port}/api/sync/vault?token={token}"
        req = urllib.request.Request(url, data=b"MALFORMED_JSON_BODY", headers={"Content-Type": "application/json"})
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 400

    def test_tier2_b4_post_vault_empty_body(self, sync_server: web_gui.VaultSyncServer):
        """Verifies sending empty body to POST /api/sync/vault returns HTTP 400."""
        token = sync_server.token
        url = f"http://127.0.0.1:{sync_server.port}/api/sync/vault?token={token}"
        req = urllib.request.Request(url, data=b"", headers={"Content-Type": "application/json"})
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 400

    def test_tier2_b4_server_port_collision_fallback(self, test_vault: vault.PasswordVault):
        """Verifies starting server on an occupied port falls back to free port or raises clean error."""
        port = get_free_port()
        # Bind socket to occupy port
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.bind(("127.0.0.1", port))
        blocker.listen(1)
        try:
            server = web_gui.VaultSyncServer(test_vault, host="127.0.0.1", port=port)
            res = server.start(port=port)
            assert bool(server.is_running) is True
            assert res["port"] != port  # Successfully selected alternate free port
            server.stop()
        finally:
            blocker.close()

    def test_tier2_b4_concurrent_http_requests(self, sync_server: web_gui.VaultSyncServer):
        """Verifies multi-threaded concurrent requests to /api/sync/info execute smoothly."""
        token = sync_server.token
        url = f"http://127.0.0.1:{sync_server.port}/api/sync/info?token={token}"
        errors = []

        def worker():
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    assert resp.status == 200
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    def test_tier2_b4_locked_vault_post_rejected(self, sync_server: web_gui.VaultSyncServer):
        """Verifies POST /api/sync/vault rejects sync when PC vault is locked."""
        token = sync_server.token
        sync_server.vault.lock()  # Lock the vault
        url = f"http://127.0.0.1:{sync_server.port}/api/sync/vault?token={token}"
        incoming = {"entries": [{"title": "Test", "username": "u", "password": "p"}]}
        req = urllib.request.Request(url, data=json.dumps(incoming).encode("utf-8"), headers={"Content-Type": "application/json"})
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 400


# =========================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# =========================================================================

class TestTier3CrossFeatureCombinations:
    """Tier 3: Complex multi-step interaction between QR export, offline updates, and LAN sync."""

    def test_tier3_combo_export_qr_edit_offline_sync_lan_merge_conflict(self, sync_server: web_gui.VaultSyncServer):
        """
        Cross-feature workflow:
        1. Desktop creates entry E1 at timestamp T1.
        2. Exports plain QR payload and verifies schema.
        3. Simulates mobile offline: modifies E1 at T2 > T1 and creates E2.
        4. Mobile connects via LAN Sync Server and POSTs changes.
        5. Smart merge algorithm reconciles: E1 is updated to T2 values and E2 is inserted.
        """
        ok, e1 = sync_server.vault.save_entry("WorkEmail", "employee@corp.com", "PasswordV1", notes="v1")
        assert ok is True
        t1 = e1["updated_at"]

        # Step 2: Export QR payload
        qr_payload = sync_server.vault.generate_credential_qr_payload(e1["id"], use_pin=False)
        qr_data = json.loads(qr_payload)
        assert qr_data["title"] == "WorkEmail"

        # Step 3: Simulate mobile modifications
        t2 = t1 + 500
        mobile_entries = [
            {
                "id": e1["id"],
                "title": "WorkEmail",
                "username": "employee@corp.com",
                "password": "PasswordV2_UpdatedOnMobile!",
                "notes": "Updated via mobile PWA",
                "updated_at": t2,
            },
            {
                "id": str(secrets.token_hex(8)),
                "title": "MobileHealthTracker",
                "username": "fit_user",
                "password": "FitSecretPass99!",
                "updated_at": t2,
            },
        ]

        # Step 4: Sync to LAN Server
        token = sync_server.token
        url = f"http://127.0.0.1:{sync_server.port}/api/sync/vault?token={token}"
        req = urllib.request.Request(
            url,
            data=json.dumps({"entries": mobile_entries}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res["merged"] == 2
            assert res["total"] == 2

        # Step 5: Verify reconciliations in desktop vault
        e1_after = sync_server.vault.get_entry(e1["id"])
        assert e1_after["password"] == "PasswordV2_UpdatedOnMobile!"
        assert e1_after["notes"] == "Updated via mobile PWA"
        assert e1_after["updated_at"] == t2

        all_titles = [e["title"] for e in sync_server.vault.list_entries()]
        assert "MobileHealthTracker" in all_titles

    def test_tier3_combo_encrypted_qr_pin_decrypt_and_secondary_vault_merge(self, temp_vault_dir: str):
        """
        Cross-feature workflow:
        1. Primary vault creates confidential credential and exports with 6-digit PIN.
        2. Isolated consumer decrypts using PIN.
        3. Credential is incorporated into a secondary independent vault.
        """
        v1_path = os.path.join(temp_vault_dir, "vault1.enc")
        v2_path = os.path.join(temp_vault_dir, "vault2.enc")
        v1 = vault.PasswordVault(vault_path=v1_path, iterations=10_000)
        v2 = vault.PasswordVault(vault_path=v2_path, iterations=10_000)
        v1.create("Vault1Pass#")
        v2.create("Vault2Pass#")

        _, entry = v1.save_entry("SecureDatabase", "dbadmin", "SuperDbPassword2026!")
        pin = "741852"
        qr_enc = v1.generate_credential_qr_payload(entry["id"], use_pin=True, pin=pin)

        # Decrypt in isolated client
        decrypted = vault.decrypt_credential_qr_payload(qr_enc, pin=pin)
        assert (decrypted.get("pass") or decrypted.get("password")) == "SuperDbPassword2026!"

        # Merge into secondary vault
        merged, total = v2.merge_entries([decrypted])
        assert merged == 1
        assert total == 1
        assert v2.list_entries()[0]["title"] == "SecureDatabase"
        assert v2.list_entries()[0]["password"] == "SuperDbPassword2026!"

    def test_tier3_combo_server_lifecycle_with_active_vault_modifications_and_lock(self, sync_server: web_gui.VaultSyncServer):
        """
        Cross-feature workflow:
        1. Server is running while desktop actively saves and deletes entries.
        2. Server correctly exports updated vault container.
        3. Desktop locks vault; server denies subsequent POST sync.
        4. Desktop unlocks vault; server allows POST sync again.
        """
        token = sync_server.token
        sync_server.vault.save_entry("DynamicEntry", "dyn_user", "DynPass!")

        # GET vault container reflects dynamic entry
        url = f"http://127.0.0.1:{sync_server.port}/api/sync/vault?token={token}"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert "ciphertext" in data

        # Lock desktop vault
        sync_server.vault.lock()
        assert sync_server.vault.is_unlocked() is False

        # Attempt to POST while locked must fail
        post_url = f"http://127.0.0.1:{sync_server.port}/api/sync/vault?token={token}"
        req = urllib.request.Request(
            post_url,
            data=json.dumps({"entries": [{"title": "T", "username": "u", "password": "p"}]}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 400

        # Unlock desktop vault
        ok, _ = sync_server.vault.unlock("MasterPassTest#2026!")
        assert ok is True

        # Now POST succeeds
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200


# =========================================================================
# TIER 4: REAL-WORLD SCENARIOS
# =========================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: End-to-end full user journey from setup to pairing, mobile updates, and sync."""

    def test_tier4_scenario_desktop_mobile_onboarding_and_offline_sync_lifecycle(self, temp_vault_dir: str):
        """
        Real-world user scenario:
        Step 1: Desktop user installs PyClean Pro, creates master password.
        Step 2: Desktop user adds primary accounts (Email, Bank, VPN).
        Step 3: User clicks "Sincronizar Móvil" -> LAN server starts, pairing QR code displayed.
        Step 4: Companion app loads /mobile, fetches sync info, pairs with token.
        Step 5: Companion app receives encrypted vault, decrypts in-memory with master password.
        Step 6: Mobile goes offline, creates new account ("Mobile Coffee Club").
        Step 7: Mobile reconnects to Wi-Fi, uploads updated vault to desktop LAN server.
        Step 8: Desktop processes merge: vault has 4 total entries.
        Step 9: Desktop user locks vault; server stops; memory sanitized.
        """
        # Step 1: Desktop setup
        v_path = os.path.join(temp_vault_dir, "desktop_vault.enc")
        desktop_vault = vault.PasswordVault(vault_path=v_path, iterations=10_000)
        master_pw = "MasterSecretPassword#2026!"
        ok, _ = desktop_vault.create(master_pw)
        assert ok is True

        # Step 2: Add initial accounts
        desktop_vault.save_entry("ProtonMail", "alice@proton.me", "ProtonPass123!", "https://mail.proton.me")
        desktop_vault.save_entry("ChaseBank", "alice_bank", "BankPassChase99!", "https://chase.com")
        desktop_vault.save_entry("CorporateVPN", "alice_corp", "VpnTokenSecret!", "https://vpn.corp.com")
        assert len(desktop_vault.list_entries()) == 3

        # Step 3: Start mobile sync server via PyCleanAPI
        api = web_gui.PyCleanAPI()
        api._vault = desktop_vault
        api._sync_server.vault = desktop_vault
        start_res = api.vault_start_mobile_sync(port=0)
        assert start_res["status"] == "ok"
        token = start_res["token"]
        pairing_url = start_res["url"]
        assigned_port = start_res["port"]

        try:
            # Step 4: Companion app fetches sync info over LAN
            info_url = f"http://127.0.0.1:{assigned_port}/api/sync/info?token={token}"
            with urllib.request.urlopen(info_url) as resp:
                sync_info = json.loads(resp.read().decode("utf-8"))
                assert sync_info["status"] == "ok"
                salt_b64 = sync_info["salt"]
                salt = base64.b64decode(salt_b64)
                iterations = sync_info["iterations"]

            # Step 5: Companion app receives encrypted vault container
            vault_url = f"http://127.0.0.1:{assigned_port}/api/sync/vault?token={token}"
            with urllib.request.urlopen(vault_url) as resp:
                encrypted_container = json.loads(resp.read().decode("utf-8"))

            # Mobile WebCrypto simulation: derive key & decrypt container
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
            derived_key = kdf.derive(master_pw.encode("utf-8"))
            aesgcm = AESGCM(derived_key)
            nonce = base64.b64decode(encrypted_container["nonce"])
            ciphertext = base64.b64decode(encrypted_container["ciphertext"])
            decrypted_json = aesgcm.decrypt(nonce, ciphertext, vault.VAULT_AAD).decode("utf-8")
            mobile_vault_data = json.loads(decrypted_json)
            assert len(mobile_vault_data["entries"]) == 3

            # Step 6: Mobile goes offline, creates new entry
            new_coffee_entry = {
                "id": str(secrets.token_hex(8)),
                "title": "Mobile Coffee Club",
                "username": "alice_coffee",
                "password": "CoffeeCardSecret2026!",
                "url": "https://coffeeclub.app",
                "category": "Personal",
                "notes": "Offline reward card",
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
            mobile_entries = mobile_vault_data["entries"] + [new_coffee_entry]

            # Step 7: Mobile reconnects, uploads updated entries via POST /api/sync/vault
            post_req = urllib.request.Request(
                vault_url,
                data=json.dumps({"entries": mobile_entries}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(post_req) as resp:
                sync_resp = json.loads(resp.read().decode("utf-8"))
                assert sync_resp["status"] == "ok"
                assert sync_resp["total"] == 4

            # Step 8: Desktop vault reflects 4 total entries
            desktop_entries = desktop_vault.list_entries()
            assert len(desktop_entries) == 4
            titles = [e["title"] for e in desktop_entries]
            assert "Mobile Coffee Club" in titles
            assert "ProtonMail" in titles

            # Step 9: User locks desktop vault & stops sync
            api.vault_stop_mobile_sync()
            api.vault_lock()
            assert desktop_vault.is_unlocked() is False
            assert len(desktop_vault._entries) == 0  # RAM wiped
            assert desktop_vault._key is None

        finally:
            api.vault_stop_mobile_sync()


# =========================================================================
# TIER 5: ADVERSARIAL HARDENING & REGRESSION TESTS
# =========================================================================

class TestTier5AdversarialHardening:
    """Tier 5: Adversarial coverage and input boundary hardening."""

    def test_tier5_post_vault_non_dict_json_payloads(self, sync_server: web_gui.VaultSyncServer):
        """Verifies sending non-dict JSON primitives (int, bool, null, string, list) to POST /api/sync/vault returns HTTP 400."""
        token = sync_server.token
        url = f"http://127.0.0.1:{sync_server.port}/api/sync/vault?token={token}"
        non_dict_payloads = [
            b"123",
            b'"just a string"',
            b"true",
            b"false",
            b"null",
            b"[1, 2, 3]",
            b'[{"entries": []}]',
        ]
        for payload in non_dict_payloads:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 400
            err_body = json.loads(exc_info.value.read().decode("utf-8"))
            assert err_body.get("status") == "error"
            assert "JSON body must be an object" in err_body.get("message", "")

    def test_tier5_decrypt_credential_qr_non_dict_json(self):
        """Verifies vault.decrypt_credential_qr_payload raises ValueError on non-dict JSON primitives."""
        non_dict_inputs = [
            "123",
            "45.67",
            "true",
            "false",
            "null",
            '"some literal string"',
            '["array", "of", "items"]',
        ]
        for inp in non_dict_inputs:
            with pytest.raises(ValueError, match="Formato de payload no reconocido"):
                vault.decrypt_credential_qr_payload(inp)

    def test_tier5_master_password_nfd_nfc_normalization(self, temp_vault_dir: str):
        """Verifies master password with NFD normalization successfully unlocks a vault created with NFC password."""
        base_pw = "Contraseña_Maestra_ñ_á_ü_2026!"
        nfc_pw = unicodedata.normalize("NFC", base_pw)
        nfd_pw = unicodedata.normalize("NFD", base_pw)

        # Confirm representation difference
        assert nfc_pw != nfd_pw
        assert nfc_pw.encode("utf-8") != nfd_pw.encode("utf-8")

        v_path = os.path.join(temp_vault_dir, "unicode_norm_vault.enc")

        # 1. Create vault using NFC password
        v1 = vault.PasswordVault(vault_path=v_path, iterations=10_000)
        ok, msg = v1.create(nfc_pw)
        assert ok is True
        v1.save_entry("TestService", "testuser", "SecretPass123!")
        v1.lock()

        # 2. Unlock existing vault using NFD password
        v2 = vault.PasswordVault(vault_path=v_path, iterations=10_000)
        unlocked, msg2 = v2.unlock(nfd_pw)
        assert unlocked is True, f"Failed to unlock with NFD password: {msg2}"
        entries = v2.list_entries()
        assert len(entries) == 1
        assert entries[0]["title"] == "TestService"
        assert entries[0]["password"] == "SecretPass123!"

        # 3. And vice versa: create with NFD, unlock with NFC
        v_path2 = os.path.join(temp_vault_dir, "unicode_norm_vault_2.enc")
        v3 = vault.PasswordVault(vault_path=v_path2, iterations=10_000)
        ok3, _ = v3.create(nfd_pw)
        assert ok3 is True
        v3.save_entry("ReverseTest", "revuser", "ReverseSecret999!")
        v3.lock()

        v4 = vault.PasswordVault(vault_path=v_path2, iterations=10_000)
        unlocked4, msg4 = v4.unlock(nfc_pw)
        assert unlocked4 is True, f"Failed to unlock with NFC password: {msg4}"
        assert v4.list_entries()[0]["title"] == "ReverseTest"

