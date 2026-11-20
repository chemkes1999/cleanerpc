"""
Unit and integration tests for PyClean Pro Password Vault Mobile Sync & QR Credential Sharing.
Tests cover:
- QR payload generation (plain and PIN-encrypted) & decryption round-trip
- Non-destructive smart merge of vault entries
- VaultSyncServer HTTP server lifecycle, token authentication, and endpoints
- PyCleanAPI bridge methods for mobile sync and QR generation
"""

import os
import sys
import json
import time
import uuid
import base64
import urllib.request
import urllib.parse
import urllib.error
import tempfile
import concurrent.futures
import pytest

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

import vault
import web_gui


@pytest.fixture
def temp_vault():
    """Provides a fresh temporary PasswordVault instance unlocked with test credentials."""
    fd, path = tempfile.mkstemp(suffix=".enc")
    os.close(fd)
    if os.path.exists(path):
        os.remove(path)

    v = vault.PasswordVault(vault_path=path, iterations=10_000)
    ok, msg = v.create("MasterPassTest1234!")
    assert ok, f"Vault creation failed: {msg}"
    assert v.is_unlocked()

    yield v

    v.lock()
    if os.path.exists(path):
        os.remove(path)
    tmp_file = f"{path}.tmp"
    if os.path.exists(tmp_file):
        os.remove(tmp_file)


class TestCredentialQRPayloads:
    def test_plain_qr_payload_roundtrip(self, temp_vault):
        ok, entry = temp_vault.save_entry(
            title="GitHub Dev",
            username="chemkes1999",
            password="SuperSecurePassword2026!",
            url="https://github.com",
            category="Development",
            notes="2FA enabled with Yubikey",
        )
        assert ok
        entry_id = entry["id"]

        # Generate plain QR payload
        payload_str = temp_vault.generate_credential_qr_payload(entry_id, use_pin=False)
        assert isinstance(payload_str, str)

        parsed_json = json.loads(payload_str)
        assert parsed_json["t"] == "pyclean-cred"
        assert parsed_json["v"] == 1
        assert parsed_json["title"] == "GitHub Dev"
        assert parsed_json["user"] == "chemkes1999"
        assert parsed_json["pass"] == "SuperSecurePassword2026!"
        assert parsed_json["url"] == "https://github.com"
        assert parsed_json["category"] == "Development"

        # Decrypt / unpack using vault method
        decrypted = temp_vault.decrypt_credential_qr_payload(payload_str)
        assert decrypted["title"] == "GitHub Dev"
        assert decrypted["user"] == "chemkes1999"
        assert decrypted["username"] == "chemkes1999"
        assert decrypted["pass"] == "SuperSecurePassword2026!"
        assert decrypted["password"] == "SuperSecurePassword2026!"
        assert decrypted["url"] == "https://github.com"
        assert decrypted["category"] == "Development"

        # Decrypt / unpack using module-level function
        mod_decrypted = vault.decrypt_credential_qr_payload(payload_str)
        assert mod_decrypted["title"] == "GitHub Dev"
        assert mod_decrypted["password"] == "SuperSecurePassword2026!"

    def test_uri_format_decryption(self):
        uri = "pyclean://vault/v1/credential?title=GitLab&user=developer&pass=SecretGitLab99!&url=https://gitlab.com&category=Work&notes=Token"
        dec = vault.decrypt_credential_qr_payload(uri)
        assert dec["title"] == "GitLab"
        assert dec["username"] == "developer"
        assert dec["password"] == "SecretGitLab99!"
        assert dec["url"] == "https://gitlab.com"
        assert dec["category"] == "Work"

    def test_pin_encrypted_qr_payload_roundtrip(self, temp_vault):
        ok, entry = temp_vault.save_entry(
            title="ProtonMail",
            username="user@proton.me",
            password="MyProtonPassword#999",
            url="https://mail.proton.me",
        )
        assert ok
        entry_id = entry["id"]

        pin = "654321"
        payload_str = temp_vault.generate_credential_qr_payload(entry_id, use_pin=True, pin=pin)
        assert isinstance(payload_str, str)

        parsed_json = json.loads(payload_str)
        assert parsed_json["t"] == "pyclean-cred-enc"
        assert parsed_json["v"] == 1
        assert "salt" in parsed_json
        assert "nonce" in parsed_json
        assert "ciphertext" in parsed_json
        assert parsed_json["iterations"] == 100_000

        # Attempt decryption without pin should fail
        with pytest.raises(ValueError, match="PIN"):
            vault.decrypt_credential_qr_payload(payload_str, pin="")

        # Attempt decryption with wrong pin should fail authentication
        with pytest.raises(Exception):
            vault.decrypt_credential_qr_payload(payload_str, pin="000000")

        # Decryption with correct pin succeeds
        dec = vault.decrypt_credential_qr_payload(payload_str, pin=pin)
        assert dec["title"] == "ProtonMail"
        assert dec["user"] == "user@proton.me"
        assert dec["username"] == "user@proton.me"
        assert dec["pass"] == "MyProtonPassword#999"
        assert dec["password"] == "MyProtonPassword#999"
        assert dec["url"] == "https://mail.proton.me"

    def test_qr_payload_locked_or_invalid_entry(self, temp_vault):
        ok, entry = temp_vault.save_entry(title="Test", username="u", password="p")
        assert ok

        # Invalid entry id
        with pytest.raises(ValueError, match="no encontrada"):
            temp_vault.generate_credential_qr_payload("non-existent-id")

        # Missing pin when use_pin is True
        with pytest.raises(ValueError, match="PIN"):
            temp_vault.generate_credential_qr_payload(entry["id"], use_pin=True, pin="")

        # Locked vault
        temp_vault.lock()
        with pytest.raises(RuntimeError, match="bloqueada"):
            temp_vault.generate_credential_qr_payload(entry["id"], use_pin=False)


class TestVaultSyncAndMerge:
    def test_export_vault_sync_payload(self, temp_vault):
        temp_vault.save_entry(title="Item 1", username="user1", password="pass1")

        container = temp_vault.export_vault_sync_payload()
        assert isinstance(container, dict)
        assert container["version"] == 1
        assert container["kdf"] == "pbkdf2-sha256"
        assert container["iterations"] == 10_000
        assert "salt" in container
        assert "nonce" in container
        assert "ciphertext" in container

        # Raw bytes base64 verification
        salt_bytes = base64.b64decode(container["salt"])
        nonce_bytes = base64.b64decode(container["nonce"])
        ct_bytes = base64.b64decode(container["ciphertext"])
        assert len(salt_bytes) == 16
        assert len(nonce_bytes) == 12
        assert len(ct_bytes) > 16

    def test_export_sync_payload_non_existent(self):
        v = vault.PasswordVault(vault_path="/tmp/non_existent_vault_12345.enc")
        with pytest.raises(FileNotFoundError):
            v.export_vault_sync_payload()

    def test_merge_entries_new_and_conflict_handling(self, temp_vault):
        # 1. Base entry
        t0 = int(time.time()) - 100
        ok, local_e1 = temp_vault.save_entry(
            title="AWS Console",
            username="root@aws.com",
            password="InitialAwsPassword1",
            notes="Initial notes",
        )
        assert ok
        e1_id = local_e1["id"]

        # 2. Merge brand new entry from mobile
        mobile_e2 = {
            "id": str(uuid.uuid4()),
            "title": "Netflix",
            "username": "family@netflix.com",
            "password": "StreamPassword2026!",
            "url": "https://netflix.com",
            "category": "Entertainment",
            "notes": "Premium UHD",
            "created_at": t0,
            "updated_at": t0 + 10,
        }
        added_or_updated, total = temp_vault.merge_entries([mobile_e2])
        assert added_or_updated == 1
        assert total == 2

        # Verify Netflix is in vault
        netflix = temp_vault.get_entry(mobile_e2["id"])
        assert netflix is not None
        assert netflix["title"] == "Netflix"
        assert netflix["password"] == "StreamPassword2026!"

        # 3. Merge older update for AWS Console -> should be rejected/ignored
        older_aws = {
            "id": e1_id,
            "title": "AWS Console",
            "username": "root@aws.com",
            "password": "OldStalePassword!",
            "updated_at": t0 - 50,
        }
        added_or_updated, total = temp_vault.merge_entries([older_aws])
        assert added_or_updated == 0
        assert total == 2
        current_aws = temp_vault.get_entry(e1_id)
        assert current_aws["password"] == "InitialAwsPassword1"

        # 4. Merge newer update for AWS Console -> should be applied
        newer_aws = {
            "id": e1_id,
            "title": "AWS Console",
            "username": "root@aws.com",
            "password": "UpdatedAwsPassword2026!",
            "notes": "Updated from Phone",
            "updated_at": int(time.time()) + 50,
        }
        added_or_updated, total = temp_vault.merge_entries([newer_aws])
        assert added_or_updated == 1
        assert total == 2
        updated_aws = temp_vault.get_entry(e1_id)
        assert updated_aws["password"] == "UpdatedAwsPassword2026!"
        assert updated_aws["notes"] == "Updated from Phone"

        # 5. Merge orphan duplicate (same title & user, different ID) with newer timestamp
        orphan_newer = {
            "id": str(uuid.uuid4()),
            "title": "AWS Console",
            "username": "root@aws.com",
            "password": "MergedFromDuplicatePassword!",
            "updated_at": int(time.time()) + 200,
        }
        added_or_updated, total = temp_vault.merge_entries([orphan_newer])
        assert added_or_updated == 1
        assert total == 2  # Did not create a 3rd entry, updated existing
        merged_aws = temp_vault.get_entry(e1_id)
        assert merged_aws["password"] == "MergedFromDuplicatePassword!"

    def test_merge_entries_when_locked_raises(self, temp_vault):
        temp_vault.lock()
        with pytest.raises(RuntimeError, match="bloqueada"):
            temp_vault.merge_entries([{"title": "X", "password": "Y"}])


class TestVaultSyncServer:
    def test_lan_ip_resolution(self):
        ip = web_gui.get_lan_ip()
        assert isinstance(ip, str)
        assert len(ip.split(".")) == 4

    def test_server_lifecycle(self, temp_vault):
        server = web_gui.VaultSyncServer(temp_vault, port=0)
        assert not server.is_running

        start_info = server.start()
        assert server.is_running
        assert start_info["status"] == "ok"
        assert start_info["running"] is True
        assert "token" in start_info
        assert start_info["port"] > 0
        token = start_info["token"]

        assert server.is_token_valid(token)
        assert not server.is_token_valid("invalid-token")
        assert not server.is_token_valid("")

        stop_info = server.stop()
        assert not server.is_running
        assert stop_info["status"] == "ok"
        assert not server.is_token_valid(token)

    def test_server_http_endpoints(self, temp_vault):
        ok, _ = temp_vault.save_entry(
            title="Service 1",
            username="alice",
            password="SecretAlicePassword123!",
        )
        assert ok

        server = web_gui.VaultSyncServer(temp_vault, host="127.0.0.1", port=0)
        start_info = server.start()
        port = start_info["port"]
        token = start_info["token"]
        base_url = f"http://127.0.0.1:{port}"

        try:
            # 1. Test Static Mobile serving
            req = urllib.request.Request(f"{base_url}/mobile/")
            with urllib.request.urlopen(req, timeout=5) as resp:
                assert resp.status == 200
                html_body = resp.read().decode("utf-8")
                assert "PyClean" in html_body

            # 2. Test GET /api/sync/info without token -> 401
            try:
                urllib.request.urlopen(f"{base_url}/api/sync/info", timeout=5)
                pytest.fail("Expected HTTP 401 Unauthorized")
            except urllib.error.HTTPError as e:
                assert e.code == 401

            # 3. Test GET /api/sync/info with invalid token -> 401
            try:
                urllib.request.urlopen(f"{base_url}/api/sync/info?token=bad_token", timeout=5)
                pytest.fail("Expected HTTP 401 Unauthorized")
            except urllib.error.HTTPError as e:
                assert e.code == 401

            # 4. Test GET /api/sync/info with valid token -> 200
            req = urllib.request.Request(f"{base_url}/api/sync/info?token={token}")
            with urllib.request.urlopen(req, timeout=5) as resp:
                assert resp.status == 200
                info_data = json.loads(resp.read().decode("utf-8"))
                assert info_data["status"] == "ok"
                assert info_data["vault_name"] == "PyClean Pro"
                assert info_data["version"] == 1
                assert info_data["kdf"] == "pbkdf2-sha256"
                assert "salt" in info_data

            # 5. Test GET /api/sync/vault with valid token -> 200
            req = urllib.request.Request(f"{base_url}/api/sync/vault?token={token}")
            with urllib.request.urlopen(req, timeout=5) as resp:
                assert resp.status == 200
                vault_data = json.loads(resp.read().decode("utf-8"))
                assert vault_data["status"] == "ok"
                assert "ciphertext" in vault_data
                assert "salt" in vault_data
                assert "nonce" in vault_data

            # 6. Test POST /api/sync/vault with decrypted entries -> 200
            new_incoming_entries = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Mobile Service",
                    "username": "mobile_user",
                    "password": "MobileSecret123!",
                    "url": "https://mobile.example.com",
                    "updated_at": int(time.time()),
                }
            ]
            post_body = json.dumps({"entries": new_incoming_entries}).encode("utf-8")
            post_req = urllib.request.Request(
                f"{base_url}/api/sync/vault?token={token}",
                data=post_body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(post_req, timeout=5) as resp:
                assert resp.status == 200
                post_res = json.loads(resp.read().decode("utf-8"))
                assert post_res["status"] == "ok"
                assert post_res["merged"] == 1
                assert post_res["total"] == 2

            # Verify entry is present in vault
            entry = temp_vault.get_entry(new_incoming_entries[0]["id"])
            assert entry is not None
            assert entry["title"] == "Mobile Service"

            # 7. Test POST /api/sync/vault with encrypted container (same master password & salt)
            # Simulate mobile phone re-encrypting vault container with same salt & key
            salt_b64 = base64.b64encode(temp_vault._salt).decode("ascii")
            mobile_entries = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Encrypted Sync Service",
                    "username": "sync_user",
                    "password": "SyncPass999!",
                    "updated_at": int(time.time()) + 10,
                }
            ]
            enc_nonce = os.urandom(12)
            aesgcm = AESGCM(temp_vault._key)
            enc_ct = aesgcm.encrypt(
                enc_nonce,
                json.dumps({"entries": mobile_entries}).encode("utf-8"),
                vault.VAULT_AAD,
            )
            enc_container_payload = {
                "salt": salt_b64,
                "nonce": base64.b64encode(enc_nonce).decode("ascii"),
                "ciphertext": base64.b64encode(enc_ct).decode("ascii"),
            }
            post_enc_req = urllib.request.Request(
                f"{base_url}/api/sync/vault?token={token}",
                data=json.dumps(enc_container_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(post_enc_req, timeout=5) as resp:
                assert resp.status == 200
                post_enc_res = json.loads(resp.read().decode("utf-8"))
                assert post_enc_res["status"] == "ok"
                assert post_enc_res["merged"] == 1

            # 8. Test OPTIONS preflight CORS
            opt_req = urllib.request.Request(
                f"{base_url}/api/sync/vault?token={token}",
                method="OPTIONS",
            )
            with urllib.request.urlopen(opt_req, timeout=5) as resp:
                assert resp.status == 200
                assert resp.headers.get("Access-Control-Allow-Origin") == "*"

            # 9. Verify server status metrics
            status = server.get_status()
            assert status["running"] is True
            assert status["clients_connected"] >= 3
            assert status["last_sync"] > 0

        finally:
            server.stop()

    def test_server_is_running_json_serializable(self, temp_vault):
        server = web_gui.VaultSyncServer(temp_vault, port=0)
        # Assert not running and cleanly JSON serializable
        assert server.is_running is False
        serialized_stopped = json.dumps({"running": server.is_running})
        assert serialized_stopped == '{"running": false}'
        assert json.loads(serialized_stopped)["running"] is False
        assert server.get_is_running() is False

        # Start server and assert running and cleanly JSON serializable
        server.start()
        try:
            assert server.is_running is True
            serialized_running = json.dumps({"running": server.is_running})
            assert serialized_running == '{"running": true}'
            assert json.loads(serialized_running)["running"] is True
            assert server.get_is_running() is True
        finally:
            server.stop()

        assert server.is_running is False
        assert json.dumps({"running": server.is_running}) == '{"running": false}'
        assert server.get_is_running() is False

    def test_high_concurrency_sync_post(self, temp_vault):
        server = web_gui.VaultSyncServer(temp_vault, host="127.0.0.1", port=0)
        start_info = server.start()
        port = start_info["port"]
        token = start_info["token"]
        base_url = f"http://127.0.0.1:{port}"

        num_threads = 40
        generated_entries = []
        for i in range(num_threads):
            generated_entries.append({
                "id": str(uuid.uuid4()),
                "title": f"Concurrent Service {i}",
                "username": f"user_{i}",
                "password": f"Pass_{uuid.uuid4().hex[:10]}!",
                "url": f"https://service{i}.example.com",
                "notes": f"High concurrency entry #{i}",
                "updated_at": int(time.time()),
            })

        def send_sync_post(entry):
            post_body = json.dumps({"entries": [entry]}).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/sync/vault?token={token}",
                data=post_body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.status
                res_data = json.loads(resp.read().decode("utf-8"))
                return status_code, res_data

        try:
            # Verify json serializability while running
            assert json.dumps({"running": server.is_running}) == '{"running": true}'

            # Spawn 40 concurrent threads sending concurrent POST /api/sync/vault requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(send_sync_post, entry) for entry in generated_entries]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

            # Assert 100% success rate (HTTP 200) with 0 errors
            assert len(results) == num_threads
            for status_code, res_data in results:
                assert status_code == 200
                assert res_data["status"] == "ok"
                assert res_data["merged"] == 1

            # Assert all entries merged accurately into vault
            vault_entries = temp_vault.list_entries()
            assert len(vault_entries) == num_threads
            vault_ids = {e["id"] for e in vault_entries}
            for entry in generated_entries:
                assert entry["id"] in vault_ids
                saved = temp_vault.get_entry(entry["id"])
                assert saved is not None
                assert saved["title"] == entry["title"]
                assert saved["password"] == entry["password"]

        finally:
            server.stop()
            assert json.dumps({"running": server.is_running}) == '{"running": false}'

    def test_high_concurrency_mixed_burst(self, temp_vault):
        server = web_gui.VaultSyncServer(temp_vault, host="127.0.0.1", port=0)
        start_info = server.start()
        port = start_info["port"]
        token = start_info["token"]
        base_url = f"http://127.0.0.1:{port}"

        tasks = []
        # 25 GET info
        for _ in range(25):
            tasks.append(("GET", f"{base_url}/api/sync/info?token={token}", None))
        # 25 GET vault
        for _ in range(25):
            tasks.append(("GET", f"{base_url}/api/sync/vault?token={token}", None))
        # 30 concurrent POST vault entries
        for i in range(30):
            entry = {
                "id": str(uuid.uuid4()),
                "title": f"Burst Service {i}",
                "password": f"BurstPass{i}!",
                "updated_at": int(time.time()),
            }
            body = json.dumps({"entries": [entry]}).encode("utf-8")
            tasks.append(("POST", f"{base_url}/api/sync/vault?token={token}", body))

        def execute_request(task):
            method, url, data = task
            req = urllib.request.Request(url, data=data, method=method)
            if data:
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
                futures = [executor.submit(execute_request, t) for t in tasks]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

            assert len(results) == len(tasks)
            assert all(code == 200 for code in results)
        finally:
            server.stop()



class TestPyCleanAPIBridge:
    def test_api_qr_and_sync_methods(self):
        fd, path = tempfile.mkstemp(suffix=".enc")
        os.close(fd)
        if os.path.exists(path):
            os.remove(path)

        api = web_gui.PyCleanAPI()
        # Override default vault path to temp file for isolated testing
        api._vault = vault.PasswordVault(vault_path=path, iterations=10_000)
        api._sync_server.vault = api._vault

        try:
            # 1. Create and unlock vault
            create_res = api.vault_create("DesktopMasterPassword2026!")
            assert create_res["success"]

            # Save an entry
            save_res = api.vault_save_entry(
                title="Google Account",
                username="user@gmail.com",
                password="SecretGooglePassword123!",
                url="https://google.com",
            )
            assert save_res["success"]
            entry_id = save_res["entry"]["id"]

            # 2. Test vault_get_qr_payload in plain mode
            qr_plain = api.vault_get_qr_payload(entry_id, use_pin=False)
            assert qr_plain["status"] == "ok"
            assert "payload" in qr_plain
            assert "pyclean-cred" in qr_plain["payload"]

            # 3. Test vault_get_qr_payload in PIN-encrypted mode
            qr_enc = api.vault_get_qr_payload(entry_id, use_pin=True)
            assert qr_enc["status"] == "ok"
            assert len(qr_enc["pin"]) == 6
            assert "pyclean-cred-enc" in qr_enc["payload"]

            # Round-trip verify PIN decrypt
            decrypted = vault.decrypt_credential_qr_payload(qr_enc["payload"], pin=qr_enc["pin"])
            assert decrypted["title"] == "Google Account"
            assert decrypted["password"] == "SecretGooglePassword123!"

            # 4. Test vault_start_mobile_sync
            start_res = api.vault_start_mobile_sync(port=0)
            assert start_res["status"] == "ok"
            assert "url" in start_res
            assert "token" in start_res
            assert "qr_payload" in start_res
            assert start_res["port"] > 0

            # Verify QR payload is valid JSON pairing data
            pair_data = json.loads(start_res["qr_payload"])
            assert pair_data["type"] == "pair"
            assert pair_data["token"] == start_res["token"]

            # 5. Test vault_get_mobile_sync_status
            status_res = api.vault_get_mobile_sync_status()
            assert status_res["running"] is True

            # 6. Test vault_stop_mobile_sync
            stop_res = api.vault_stop_mobile_sync()
            assert stop_res["status"] == "ok"

            status_res_after = api.vault_get_mobile_sync_status()
            assert status_res_after["running"] is False

        finally:
            api._sync_server.stop()
            api.vault_lock()
            if os.path.exists(path):
                os.remove(path)
            tmp_f = f"{path}.tmp"
            if os.path.exists(tmp_f):
                os.remove(tmp_f)
