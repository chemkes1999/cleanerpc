"""
PyClean Pro v2.4 - Bóveda Local de Contraseñas (Offline AES-256-GCM)
Almacén local cifrado con Zero-Knowledge:
- Derivación de clave: PBKDF2-HMAC-SHA256 (600,000 iteraciones, salt aleatorio de 16 bytes).
- Cifrado autenticado: AES-256-GCM (nonce aleatorio de 12 bytes regenerado en cada guardado).
- La contraseña maestra nunca se almacena en disco.
"""

from __future__ import annotations

import os
import sys
import json
import time
import uuid
import math
import base64
import shutil
import string
import secrets

try:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

VAULT_VERSION = 1
PBKDF2_ITERATIONS = 600_000
VAULT_AAD = b"pyclean-pro-vault-v1"
AUTO_LOCK_SECONDS = 300  # 5 minutos de inactividad


def get_default_vault_path() -> str:
    """Retorna la ruta estándar persistente para la bóveda cifrada del usuario."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(base, "PyCleanPro")
    else:
        folder = os.path.join(os.path.expanduser("~"), ".pycleanpro")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "vault.enc")


def _derive_key(master_password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("La librería 'cryptography' no está instalada.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(master_password.encode("utf-8"))


def generate_password(
    length: int = 18,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """Genera una contraseña criptográficamente segura usando el módulo secrets."""
    length = max(8, min(128, int(length)))
    pools = []
    if use_lower:
        pools.append(string.ascii_lowercase)
    if use_upper:
        pools.append(string.ascii_uppercase)
    if use_digits:
        pools.append(string.digits)
    if use_symbols:
        pools.append("!@#$%^&*()-_=+[]{}|;:,.<>?")

    if not pools:
        pools = [string.ascii_letters, string.digits]

    all_chars = "".join(pools)
    # Garantizar al menos un carácter de cada conjunto seleccionado
    chars = [secrets.choice(pool) for pool in pools]
    while len(chars) < length:
        chars.append(secrets.choice(all_chars))

    # Mezclar con Fisher-Yates usando secrets.randbelow
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]

    return "".join(chars)


def evaluate_password_strength(password: str) -> dict:
    """Calcula la entropía estimada (bits) y clasifica la fortaleza de una contraseña."""
    if not password:
        return {"score": 0, "entropy_bits": 0.0, "label": "Vacía", "color": "#64748B"}

    charset = 0
    if any(c.islower() for c in password):
        charset += 26
    if any(c.isupper() for c in password):
        charset += 26
    if any(c.isdigit() for c in password):
        charset += 10
    if any(not c.isalnum() for c in password):
        charset += 32

    entropy = round(len(password) * math.log2(max(1, charset)), 1)

    if entropy < 40:
        return {"score": 1, "entropy_bits": entropy, "label": "Débil", "color": "#EF4444"}
    elif entropy < 60:
        return {"score": 2, "entropy_bits": entropy, "label": "Media", "color": "#F59E0B"}
    elif entropy < 85:
        return {"score": 3, "entropy_bits": entropy, "label": "Fuerte", "color": "#10B981"}
    else:
        return {"score": 4, "entropy_bits": entropy, "label": "Muy Fuerte", "color": "#06B6D4"}


class PasswordVault:
    """Gestor en memoria + persistencia cifrada AES-256-GCM para credenciales locales."""

    def __init__(self, vault_path: str = None, iterations: int = PBKDF2_ITERATIONS):
        self.vault_path = vault_path or get_default_vault_path()
        self.iterations = iterations
        self._key: bytes | None = None
        self._salt: bytes | None = None
        self._entries: list[dict] = []
        self._last_activity: float = 0.0

    def exists(self) -> bool:
        return os.path.exists(self.vault_path)

    def is_unlocked(self) -> bool:
        if self._key is None:
            return False
        if (time.time() - self._last_activity) > AUTO_LOCK_SECONDS:
            self.lock()
            return False
        return True

    def _touch(self):
        self._last_activity = time.time()

    def status(self) -> dict:
        return {
            "crypto_available": CRYPTO_AVAILABLE,
            "exists": self.exists(),
            "unlocked": self.is_unlocked(),
            "entry_count": len(self._entries) if self.is_unlocked() else 0,
            "vault_path": self.vault_path,
        }

    def lock(self):
        """Borra la clave y credenciales de memoria inmediatamente."""
        self._key = None
        self._salt = None
        self._entries = []
        self._last_activity = 0.0

    def create(self, master_password: str) -> tuple[bool, str]:
        """Crea una bóveda nueva cifrada con la contraseña maestra indicada."""
        if not CRYPTO_AVAILABLE:
            return False, "Falta instalar el paquete 'cryptography'."
        if not master_password or len(master_password) < 8:
            return False, "La contraseña maestra debe tener al menos 8 caracteres."
        if self.exists():
            return False, "Ya existe una bóveda creada en este equipo."

        salt = os.urandom(16)
        key = _derive_key(master_password, salt, self.iterations)
        self._salt = salt
        self._key = key
        self._entries = []
        self._touch()
        self._persist()
        return True, "Bóveda AES-256-GCM creada y desbloqueada correctamente."

    def unlock(self, master_password: str) -> tuple[bool, str]:
        """Desbloquea la bóveda verificando la etiqueta de autenticación GCM."""
        if not CRYPTO_AVAILABLE:
            return False, "Falta instalar el paquete 'cryptography'."
        if not self.exists():
            return False, "No existe ninguna bóveda creada todavía."
        if not master_password:
            return False, "Introduce tu contraseña maestra."

        try:
            with open(self.vault_path, "r", encoding="utf-8") as f:
                envelope = json.load(f)

            salt = base64.b64decode(envelope["salt"])
            nonce = base64.b64decode(envelope["nonce"])
            ciphertext = base64.b64decode(envelope["ciphertext"])
            iterations = int(envelope.get("iterations", PBKDF2_ITERATIONS))

            key = _derive_key(master_password, salt, iterations)
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, VAULT_AAD)
            payload = json.loads(plaintext.decode("utf-8"))

            self._salt = salt
            self._key = key
            self.iterations = iterations
            self._entries = payload.get("entries", [])
            self._touch()
            return True, f"Bóveda desbloqueada ({len(self._entries)} credenciales)."
        except Exception:
            self.lock()
            return False, "Contraseña maestra incorrecta o archivo de bóveda alterado."

    def _persist(self):
        if self._key is None or self._salt is None:
            raise RuntimeError("La bóveda está bloqueada.")

        os.makedirs(os.path.dirname(os.path.abspath(self.vault_path)), exist_ok=True)
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._key)
        plaintext = json.dumps({"entries": self._entries}, ensure_ascii=False).encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, plaintext, VAULT_AAD)

        envelope = {
            "version": VAULT_VERSION,
            "kdf": "pbkdf2-sha256",
            "iterations": self.iterations,
            "salt": base64.b64encode(self._salt).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }

        tmp_path = f"{self.vault_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(envelope, f, indent=2)
        os.replace(tmp_path, self.vault_path)

    def list_entries(self) -> list[dict]:
        if not self.is_unlocked():
            return []
        self._touch()
        return list(self._entries)

    def save_entry(
        self,
        title: str,
        username: str,
        password: str,
        url: str = "",
        category: str = "General",
        notes: str = "",
        entry_id: str | None = None,
    ) -> tuple[bool, dict | str]:
        if not self.is_unlocked():
            return False, "La bóveda está bloqueada."
        if not title or not title.strip():
            return False, "El título es obligatorio."
        if not password:
            return False, "La contraseña no puede estar vacía."

        self._touch()
        now = int(time.time())

        if entry_id:
            for item in self._entries:
                if item.get("id") == entry_id:
                    item.update({
                        "title": title.strip(),
                        "username": (username or "").strip(),
                        "password": password,
                        "url": (url or "").strip(),
                        "category": (category or "General").strip(),
                        "notes": (notes or "").strip(),
                        "updated_at": now,
                    })
                    self._persist()
                    return True, item

        new_entry = {
            "id": str(uuid.uuid4()),
            "title": title.strip(),
            "username": (username or "").strip(),
            "password": password,
            "url": (url or "").strip(),
            "category": (category or "General").strip(),
            "notes": (notes or "").strip(),
            "created_at": now,
            "updated_at": now,
        }
        self._entries.append(new_entry)
        self._persist()
        return True, new_entry

    def delete_entry(self, entry_id: str) -> tuple[bool, str]:
        if not self.is_unlocked():
            return False, "La bóveda está bloqueada."
        self._touch()
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.get("id") != entry_id]
        if len(self._entries) == before:
            return False, "Credencial no encontrada."
        self._persist()
        return True, "Credencial eliminada de la bóveda."

    def export_encrypted_backup(self, dest_path: str) -> tuple[bool, str]:
        if not self.exists():
            return False, "No hay ninguna bóveda para exportar."
        try:
            shutil.copy2(self.vault_path, dest_path)
            return True, f"Respaldo cifrado exportado a {dest_path}"
        except Exception as e:
            return False, f"Error exportando respaldo: {e}"

    def import_encrypted_backup(self, src_path: str) -> tuple[bool, str]:
        if not os.path.exists(src_path):
            return False, "Archivo de respaldo no encontrado."
        try:
            with open(src_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not all(k in data for k in ("salt", "nonce", "ciphertext")):
                return False, "El archivo seleccionado no es una bóveda válida de PyClean Pro."
            self.lock()
            os.makedirs(os.path.dirname(os.path.abspath(self.vault_path)), exist_ok=True)
            shutil.copy2(src_path, self.vault_path)
            return True, "Respaldo cifrado importado. Desbloquéalo con su contraseña maestra."
        except Exception as e:
            return False, f"Error importando respaldo: {e}"
