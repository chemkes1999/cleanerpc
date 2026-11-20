"""
Tests for Milestone 3: Mobile Companion PWA & Standalone Bundle
Verifies:
- All required mobile companion assets exist and have valid structure/syntax.
- PWA manifest.webmanifest is valid JSON with required standalone metadata.
- Service worker (sw.js) implements Cache-First strategy with precache list.
- Web/mobile index.html contains all 5 required views and mobile UI components.
- Mobile CSS implements dark theme, 48px touch targets, and safe-area-insets.
- Standalone vault_mobile.html is self-contained with inlined styles and scripts.
- Bit-for-bit cryptographic parity between vault.py and web/mobile/crypto.js.
"""

from __future__ import annotations

import os
import json
import subprocess
import base64
import time
import pytest
from pathlib import Path

import vault
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

BASE_DIR = Path(__file__).resolve().parent.parent
MOBILE_DIR = BASE_DIR / "web" / "mobile"
STANDALONE_FILE = BASE_DIR / "vault_mobile.html"


def test_mobile_companion_files_exist():
    """Verifica que todos los archivos requeridos del Mobile Companion existan."""
    required_files = [
        "index.html",
        "mobile.css",
        "mobile.js",
        "crypto.js",
        "scanner.js",
        "storage.js",
        "jsqr.min.js",
        "sw.js",
        "manifest.webmanifest",
    ]

    for filename in required_files:
        filepath = MOBILE_DIR / filename
        assert filepath.is_file(), f"Falta el archivo requerido: {filepath}"
        assert filepath.stat().st_size > 0, f"El archivo está vacío: {filepath}"

    assert STANDALONE_FILE.is_file(), f"Falta el archivo standalone: {STANDALONE_FILE}"
    assert STANDALONE_FILE.stat().st_size > 50_000, "vault_mobile.html es demasiado pequeño para contener el bundle inlined"


def test_manifest_webmanifest_valid():
    """Verifica que manifest.webmanifest sea JSON válido con configuración PWA standalone."""
    manifest_path = MOBILE_DIR / "manifest.webmanifest"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "PyClean" in data.get("name", "")
    assert data.get("display") == "standalone"
    assert data.get("theme_color") == "#090B10"
    assert data.get("background_color") == "#090B10"
    assert data.get("start_url") == "./index.html"
    assert isinstance(data.get("icons"), list)
    assert len(data["icons"]) >= 2
    for icon in data["icons"]:
        assert "src" in icon
        assert "sizes" in icon
        assert "type" in icon


def test_service_worker_asset_caching():
    """Verifica que sw.js implemente Cache-First y pre-almacene los assets offline."""
    sw_path = MOBILE_DIR / "sw.js"
    with open(sw_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "caches.open" in content
    assert "caches.match" in content
    assert "PRECACHE_ASSETS" in content or "CACHE_NAME" in content

    # Comprobar que los assets esenciales están presentes en la lista de caché
    essential = ["index.html", "mobile.css", "mobile.js", "crypto.js", "scanner.js", "storage.js", "jsqr.min.js"]
    for asset in essential:
        assert asset in content, f"Asset no encontrado en la lista de caché de sw.js: {asset}"


def test_mobile_html_markup_and_views():
    """Verifica que index.html contenga las 5 vistas requeridas y componentes de interfaz."""
    html_path = MOBILE_DIR / "index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Verificar encabezado y marca
    assert "PyClean Vault" in html
    assert "vault-status-badge" in html

    # Verificar 5 vistas principales
    assert 'id="view-unlock"' in html, "Falta Vista 1: Desbloqueo"
    assert 'id="view-list"' in html, "Falta Vista 2: Lista de Credenciales"
    assert 'id="view-detail"' in html, "Falta Vista 3: Detalle de Credencial"
    assert 'id="view-scanner"' in html, "Falta Vista 4: Escáner QR de Cámara"
    assert 'id="view-sync"' in html, "Falta Vista 5: Sincronización y Emparejamiento LAN"

    # Componentes de interacción táctil y seguridad
    assert 'id="unlock-password-input"' in html
    assert 'id="btn-unlock-vault"' in html
    assert 'id="search-credentials-input"' in html
    assert 'id="category-chips"' in html
    assert 'id="scanner-video"' in html
    assert 'id="btn-flip-camera"' in html
    assert 'id="btn-toggle-torch"' in html
    assert 'id="pin-modal"' in html
    assert 'id="toast-container"' in html
    assert 'id="btn-pull-sync"' in html
    assert 'id="btn-push-sync"' in html


def test_mobile_css_styling():
    """Verifica mobile.css para diseño responsivo, safe-area-insets y touch-targets."""
    css_path = MOBILE_DIR / "mobile.css"
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    # Safe-area-insets para pantallas con notch
    assert "safe-area-inset-top" in css
    assert "safe-area-inset-bottom" in css

    # Paleta de colores PyClean Pro
    assert "#090B10" in css  # Dark background
    assert "#3B82F6" in css  # Primary blue
    assert "#06B6D4" in css  # Cyan accent

    # Touch targets mínimos de 48px
    assert "--touch-target: 48px" in css or "48px" in css


def test_standalone_vault_mobile_bundle():
    """Verifica que vault_mobile.html esté 100% autocontenido sin enlaces externos."""
    assert STANDALONE_FILE.is_file()
    with open(STANDALONE_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # No debe tener <link rel="stylesheet" href="mobile.css">
    assert '<link rel="stylesheet" href="mobile.css">' not in content
    assert "<style>" in content

    # Debe contener inlined los módulos JavaScript
    assert "MobileCrypto" in content
    assert "MobileScanner" in content
    assert "MobileStorage" in content

    # No debe tener dependencias a CDNs externos (unpkg, cdnjs, etc.)
    assert "unpkg.com" not in content
    assert "cdnjs.cloudflare.com" not in content
    assert "fonts.googleapis.com" not in content


def test_crypto_parity_python_to_webcrypto():
    """
    Prueba de paridad criptográfica: Python cifra con vault.py -> Node.js descifra con crypto.js.
    Verifica contenedor completo de bóveda, QR con PIN y QR plano.
    """
    # 1. Contenedor de bóveda cifrado desde Python
    salt = os.urandom(16)
    nonce = os.urandom(12)
    master_pwd = "TestMasterPassword_2026!#"
    iterations = 25_000

    kdf = PBKDF2HMAC(hashes.SHA256(), 32, salt, iterations)
    key = kdf.derive(master_pwd.encode("utf-8"))
    aesgcm = AESGCM(key)

    entries = [
        {
            "id": "uuid-test-1",
            "title": "GitHub Pro",
            "username": "developer@pyclean.local",
            "password": "CorrectHorseBatteryStaple99!",
            "url": "https://github.com",
            "category": "Trabajo",
            "notes": "Token personal con permisos repo",
            "created_at": 1732120000,
            "updated_at": 1732120500,
        },
        {
            "id": "uuid-test-2",
            "title": "Banco Santander",
            "username": "cliente_santander",
            "password": "SantanderSuperPassword77!",
            "url": "https://santander.es",
            "category": "Finanzas",
            "notes": "Clave de acceso online",
            "created_at": 1732121000,
            "updated_at": 1732121000,
        }
    ]

    plaintext = json.dumps({"entries": entries}, ensure_ascii=False).encode("utf-8")
    ct = aesgcm.encrypt(nonce, plaintext, vault.VAULT_AAD)

    envelope = {
        "version": 1,
        "kdf": "pbkdf2-sha256",
        "iterations": iterations,
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ct).decode("ascii"),
    }

    # 2. QR payload cifrado con PIN efímero de 6 dígitos desde Python
    pin = "654321"
    pin_payload = vault.generate_credential_qr_payload(entries[0], use_pin=True, pin=pin)

    # 3. QR payload plano desde Python
    plain_payload = vault.generate_credential_qr_payload(entries[1], use_pin=False)

    # 4. Validar descifrado en Node.js usando crypto.js
    node_test_script = """
    const MobileCrypto = require('./web/mobile/crypto.js');
    const assert = require('assert');

    async function run() {
      const envelope = JSON.parse(process.argv[1]);
      const pinPayload = process.argv[2];
      const plainPayload = process.argv[3];
      const masterPassword = process.argv[4];
      const pin = process.argv[5];

      // A) Descifrar contenedor de bóveda
      const decryptedEntries = await MobileCrypto.decryptVaultEnvelope(envelope, masterPassword);
      assert.strictEqual(decryptedEntries.length, 2);
      assert.strictEqual(decryptedEntries[0].title, "GitHub Pro");
      assert.strictEqual(decryptedEntries[0].password, "CorrectHorseBatteryStaple99!");
      assert.strictEqual(decryptedEntries[1].title, "Banco Santander");
      assert.strictEqual(decryptedEntries[1].password, "SantanderSuperPassword77!");

      // B) Probar contraseña errónea en contenedor -> debe rechazar
      let failedAsExpected = false;
      try {
        await MobileCrypto.decryptVaultEnvelope(envelope, "WrongPassword123!");
      } catch (err) {
        failedAsExpected = true;
      }
      assert(failedAsExpected, "crypto.js debió fallar al recibir contraseña incorrecta");

      // C) Descifrar QR protegido con PIN
      const pinDecrypted = await MobileCrypto.decryptSingleCredentialQr(pinPayload, pin);
      assert.strictEqual(pinDecrypted.title, "GitHub Pro");
      assert.strictEqual(pinDecrypted.password, "CorrectHorseBatteryStaple99!");

      // D) Probar PIN erróneo -> debe rechazar
      let pinFailedAsExpected = false;
      try {
        await MobileCrypto.decryptSingleCredentialQr(pinPayload, "000000");
      } catch (err) {
        pinFailedAsExpected = true;
      }
      assert(pinFailedAsExpected, "crypto.js debió fallar con PIN incorrecto");

      // E) Descifrar QR plano
      const plainDecrypted = await MobileCrypto.decryptSingleCredentialQr(plainPayload);
      assert.strictEqual(plainDecrypted.title, "Banco Santander");
      assert.strictEqual(plainDecrypted.password, "SantanderSuperPassword77!");

      // F) Non-object / null primitives -> must reject
      for (const nonObj of ["null", "123", "true", '"plain string"']) {
        let nonObjFailed = false;
        try {
          await MobileCrypto.decryptSingleCredentialQr(nonObj);
        } catch (err) {
          nonObjFailed = true;
        }
        assert(nonObjFailed, `MobileCrypto.decryptSingleCredentialQr debió fallar con payload: ${nonObj}`);
      }

      console.log("CRYPT_PARITY_PY_TO_NODE_OK");
    }

    run().catch(err => {
      console.error(err);
      process.exit(1);
    });
    """

    cmd = [
        "node",
        "-e",
        node_test_script,
        json.dumps(envelope),
        pin_payload,
        plain_payload,
        master_pwd,
        pin,
    ]
    result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
    assert result.returncode == 0, f"Node.js falló al verificar paridad criptográfica:\n{result.stderr}"
    assert "CRYPT_PARITY_PY_TO_NODE_OK" in result.stdout


def test_crypto_parity_webcrypto_to_python():
    """
    Prueba de paridad criptográfica: Node.js cifra con crypto.js -> Python descifra con vault.py.
    """
    node_encrypt_script = """
    const MobileCrypto = require('./web/mobile/crypto.js');

    async function run() {
      const entries = [
        {
          id: "web-crypto-uuid",
          title: "ProtonMail",
          username: "user@proton.me",
          password: "WebCryptoPassword2026!#$",
          url: "https://proton.me",
          category: "Personal",
          notes: "Correo encriptado",
          created_at: 1732130000,
          updated_at: 1732130000
        }
      ];

      const masterPassword = "MasterFromMobileBrowser!";
      const pin = "789123";

      const envelope = await MobileCrypto.encryptVaultEnvelope(entries, masterPassword, null, 25000);
      const pinPayload = await MobileCrypto.encryptSingleCredentialQr(entries[0], pin);
      const plainPayload = await MobileCrypto.encryptSingleCredentialQr(entries[0]);

      console.log(JSON.stringify({
        envelope,
        pinPayload,
        plainPayload,
        masterPassword,
        pin
      }));
    }

    run().catch(err => {
      console.error(err);
      process.exit(1);
    });
    """

    cmd = ["node", "-e", node_encrypt_script]
    result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
    assert result.returncode == 0, f"Node.js falló en el cifrado:\n{result.stderr}"

    out_data = json.loads(result.stdout)
    envelope = out_data["envelope"]
    pin_payload = out_data["pinPayload"]
    plain_payload = out_data["plainPayload"]
    master_pwd = out_data["masterPassword"]
    pin = out_data["pin"]

    # 1. Python descifra el contenedor generado por crypto.js
    salt = base64.b64decode(envelope["salt"])
    nonce = base64.b64decode(envelope["nonce"])
    ct = base64.b64decode(envelope["ciphertext"])
    iterations = envelope["iterations"]

    kdf = PBKDF2HMAC(hashes.SHA256(), 32, salt, iterations)
    key = kdf.derive(master_pwd.encode("utf-8"))
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ct, vault.VAULT_AAD)
    payload = json.loads(plaintext.decode("utf-8"))

    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["title"] == "ProtonMail"
    assert payload["entries"][0]["password"] == "WebCryptoPassword2026!#$"

    # 2. Python descifra el QR cifrado con PIN generado por crypto.js
    cred_from_pin = vault.decrypt_credential_qr_payload(pin_payload, pin=pin)
    assert cred_from_pin["title"] == "ProtonMail"
    assert cred_from_pin["password"] == "WebCryptoPassword2026!#$"

    # 3. Python falla con PIN incorrecto
    with pytest.raises(Exception):
        vault.decrypt_credential_qr_payload(pin_payload, pin="000000")

    # 4. Python deserializa el QR plano generado por crypto.js
    cred_plain = vault.decrypt_credential_qr_payload(plain_payload)
    assert cred_plain["title"] == "ProtonMail"
    assert cred_plain["password"] == "WebCryptoPassword2026!#$"


def test_storage_module_behavior():
    """Prueba unitaria del módulo storage.js ejecutado en Node."""
    node_storage_script = """
    const MobileStorage = require('./web/mobile/storage.js');
    const assert = require('assert');

    // Inicialmente bloqueada
    assert.strictEqual(MobileStorage.isUnlocked(), false);
    assert.strictEqual(MobileStorage.getUnlockedEntries(), null);

    // Asignar credenciales en sesión
    const testEntries = [{ id: '1', title: 'Test' }];
    MobileStorage.setUnlockedEntries(testEntries);
    assert.strictEqual(MobileStorage.isUnlocked(), true);
    assert.strictEqual(MobileStorage.getUnlockedEntries().length, 1);

    // Registrar callback de bloqueo
    let lockTriggered = false;
    MobileStorage.onLock(() => {
      lockTriggered = true;
    });

    // Bloquear explícitamente
    MobileStorage.lockVault();
    assert.strictEqual(MobileStorage.isUnlocked(), false);
    assert.strictEqual(MobileStorage.getUnlockedEntries(), null);
    assert.strictEqual(lockTriggered, true, "Callback de bloqueo debió dispararse");

    console.log("STORAGE_MODULE_TEST_OK");
    """

    cmd = ["node", "-e", node_storage_script]
    result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
    assert result.returncode == 0, f"Error en test de almacenamiento:\n{result.stderr}"
    assert "STORAGE_MODULE_TEST_OK" in result.stdout
