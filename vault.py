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
import urllib.parse
import threading
import unicodedata

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
CRED_QR_AAD = b"pyclean-cred-v1"
CRED_QR_ITERATIONS = 100_000


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
    master_password = unicodedata.normalize("NFC", master_password)
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
        self._lock = threading.RLock()

    def exists(self) -> bool:
        with self._lock:
            return os.path.exists(self.vault_path)

    def is_unlocked(self) -> bool:
        with self._lock:
            if self._key is None:
                return False
            if (time.time() - self._last_activity) > AUTO_LOCK_SECONDS:
                self.lock()
                return False
            return True

    def _touch(self):
        with self._lock:
            self._last_activity = time.time()

    def status(self) -> dict:
        with self._lock:
            return {
                "crypto_available": CRYPTO_AVAILABLE,
                "exists": self.exists(),
                "unlocked": self.is_unlocked(),
                "entry_count": len(self._entries) if self.is_unlocked() else 0,
                "vault_path": self.vault_path,
            }

    def lock(self):
        """Borra la clave y credenciales de memoria inmediatamente."""
        with self._lock:
            self._key = None
            self._salt = None
            self._entries = []
            self._last_activity = 0.0

    def create(self, master_password: str) -> tuple[bool, str]:
        """Crea una bóveda nueva cifrada con la contraseña maestra indicada."""
        with self._lock:
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
        with self._lock:
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
        with self._lock:
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

            tmp_path = f"{self.vault_path}.tmp.{uuid.uuid4().hex}"
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(envelope, f, indent=2)
                os.replace(tmp_path, self.vault_path)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

    def list_entries(self) -> list[dict]:
        with self._lock:
            if not self.is_unlocked():
                return []
            self._touch()
            return [dict(e) for e in self._entries]

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
        with self._lock:
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
        with self._lock:
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
        with self._lock:
            if not self.exists():
                return False, "No hay ninguna bóveda para exportar."
            try:
                shutil.copy2(self.vault_path, dest_path)
                return True, f"Respaldo cifrado exportado a {dest_path}"
            except Exception as e:
                return False, f"Error exportando respaldo: {e}"

    def import_encrypted_backup(self, src_path: str) -> tuple[bool, str]:
        with self._lock:
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

    def get_entry(self, entry_id: str) -> dict | None:
        """Obtiene una credencial específica por su UUID."""
        with self._lock:
            if not self.is_unlocked():
                return None
            self._touch()
            for item in self._entries:
                if item.get("id") == entry_id:
                    return dict(item)
            return None

    def generate_credential_qr_payload(
        self, entry_id: str, use_pin: bool = False, pin: str = ""
    ) -> str:
        """
        Genera el payload para código QR de una sola credencial.
        - use_pin=False: JSON estandarizado para escaneo directo.
        - use_pin=True: Cifrado con PIN efímero de 6 dígitos mediante PBKDF2 + AES-GCM.
        """
        with self._lock:
            if not self.is_unlocked():
                raise RuntimeError("La bóveda está bloqueada.")
            entry = self.get_entry(entry_id)
            if not entry:
                raise ValueError(f"Credencial con ID '{entry_id}' no encontrada.")

            if not use_pin:
                payload = {
                    "t": "pyclean-cred",
                    "v": 1,
                    "title": entry["title"],
                    "user": entry.get("username", ""),
                    "pass": entry["password"],
                    "url": entry.get("url", ""),
                    "category": entry.get("category", "General"),
                    "notes": entry.get("notes", ""),
                }
                if entry.get("id"):
                    payload["id"] = entry["id"]
                return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

            if not pin:
                raise ValueError("Se requiere un PIN numérico para el modo cifrado.")
            if not CRYPTO_AVAILABLE:
                raise RuntimeError("La librería 'cryptography' no está instalada.")

            salt = os.urandom(16)
            nonce = os.urandom(12)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=CRED_QR_ITERATIONS,
            )
            key = kdf.derive(pin.encode("utf-8"))
            aesgcm = AESGCM(key)

            inner_data = {
                "id": entry.get("id", ""),
                "title": entry["title"],
                "user": entry.get("username", ""),
                "username": entry.get("username", ""),
                "pass": entry["password"],
                "password": entry["password"],
                "url": entry.get("url", ""),
                "category": entry.get("category", "General"),
                "notes": entry.get("notes", ""),
                "updated_at": entry.get("updated_at", int(time.time())),
            }
            plaintext = json.dumps(inner_data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ciphertext = aesgcm.encrypt(nonce, plaintext, CRED_QR_AAD)

            payload = {
                "t": "pyclean-cred-enc",
                "v": 1,
                "salt": base64.b64encode(salt).decode("ascii"),
                "nonce": base64.b64encode(nonce).decode("ascii"),
                "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
                "iterations": CRED_QR_ITERATIONS,
            }
            return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    def decrypt_credential_qr_payload(self, payload_str: str, pin: str = "") -> dict:
        """Descifra o deserializa el payload de un código QR de credencial."""
        return decrypt_credential_qr_payload(payload_str, pin=pin)

    def export_vault_sync_payload(self) -> dict:
        """
        Exporta el contenedor cifrado completo de la bóveda sin descifrarlo (Zero-Knowledge).
        Retorna: {version, kdf, iterations, salt, nonce, ciphertext}
        """
        with self._lock:
            if not self.exists():
                raise FileNotFoundError("No existe ningún archivo de bóveda para exportar.")
            try:
                with open(self.vault_path, "r", encoding="utf-8") as f:
                    envelope = json.load(f)
                for k in ("salt", "nonce", "ciphertext"):
                    if k not in envelope:
                        raise ValueError(f"El contenedor de la bóveda está dañado (falta {k}).")
                return {
                    "version": envelope.get("version", VAULT_VERSION),
                    "kdf": envelope.get("kdf", "pbkdf2-sha256"),
                    "iterations": int(envelope.get("iterations", self.iterations)),
                    "salt": envelope["salt"],
                    "nonce": envelope["nonce"],
                    "ciphertext": envelope["ciphertext"],
                }
            except Exception as e:
                if isinstance(e, (FileNotFoundError, ValueError)):
                    raise
                raise RuntimeError(f"Error al leer el contenedor cifrado de la bóveda: {e}")

    def merge_entries(self, incoming_entries: list[dict]) -> tuple[int, int]:
        """
        Fusión inteligente y no destructiva de credenciales basada en 'id' y 'updated_at'.
        Retorna (added_or_updated_count, total_count).
        """
        with self._lock:
            if not self.is_unlocked():
                raise RuntimeError("La bóveda está bloqueada. Debe desbloquearse para fusionar credenciales.")

            self._touch()
            existing_by_id = {e.get("id"): e for e in self._entries if e.get("id")}
            existing_by_sig = {
                (e.get("title", "").strip().lower(), (e.get("username") or "").strip().lower()): e
                for e in self._entries
            }

            added_or_updated = 0

            for inc in incoming_entries:
                title = str(inc.get("title") or "").strip()
                pwd = str(inc.get("password") or inc.get("pass") or "")
                if not title or not pwd:
                    continue

                inc_id = inc.get("id")
                try:
                    inc_updated = int(inc.get("updated_at") or time.time())
                except (ValueError, TypeError):
                    inc_updated = int(time.time())

                try:
                    inc_created = int(inc.get("created_at") or inc_updated)
                except (ValueError, TypeError):
                    inc_created = inc_updated

                inc_user = str(inc.get("username") or inc.get("user") or "").strip()

                clean = {
                    "id": inc_id or str(uuid.uuid4()),
                    "title": title,
                    "username": inc_user,
                    "password": pwd,
                    "url": str(inc.get("url") or "").strip(),
                    "category": str(inc.get("category") or "General").strip(),
                    "notes": str(inc.get("notes") or "").strip(),
                    "created_at": inc_created,
                    "updated_at": inc_updated,
                }

                # 1. Coincidencia por UUID exacto
                if inc_id and inc_id in existing_by_id:
                    local = existing_by_id[inc_id]
                    if inc_updated > int(local.get("updated_at", 0)):
                        update_data = dict(clean)
                        update_data["id"] = local["id"]
                        update_data["created_at"] = local.get("created_at", clean["created_at"])
                        local.update(update_data)
                        added_or_updated += 1
                    continue

                # 2. Coincidencia por servicio + usuario (evitar duplicados lógicos)
                sig = (clean["title"].lower(), clean["username"].lower())
                if sig in existing_by_sig:
                    local = existing_by_sig[sig]
                    if inc_updated > int(local.get("updated_at", 0)):
                        update_data = dict(clean)
                        update_data["id"] = local["id"]
                        update_data["created_at"] = local.get("created_at", clean["created_at"])
                        local.update(update_data)
                        added_or_updated += 1
                    continue

                # 3. Nueva credencial
                self._entries.append(clean)
                existing_by_id[clean["id"]] = clean
                existing_by_sig[sig] = clean
                added_or_updated += 1

            if added_or_updated > 0:
                self._persist()

            return added_or_updated, len(self._entries)


def decrypt_credential_qr_payload(payload_str: str, pin: str = "") -> dict:
    """
    Descifra o deserializa el payload de un código QR de credencial (plano, URI o cifrado con PIN).
    Retorna diccionario estandarizado con la credencial.
    """
    payload_str = (payload_str or "").strip()
    if not payload_str:
        raise ValueError("El payload QR está vacío.")

    # Manejo de URI compacta (e.g. pyclean://vault/v1/credential?... o pyclean:cred?...)
    if payload_str.startswith("pyclean://") or payload_str.startswith("pyclean:cred") or payload_str.startswith("pyclean:"):
        parsed = urllib.parse.urlparse(payload_str)
        qs = parsed.query or (parsed.path.split("?", 1)[1] if "?" in parsed.path else "")
        params = urllib.parse.parse_qs(qs)
        title = params.get("title", params.get("t", [""]))[0]
        user = params.get("user", params.get("u", params.get("username", [""])))[0]
        pwd = params.get("pass", params.get("p", params.get("password", [""])))[0]
        url = params.get("url", [""])[0]
        cat = params.get("category", params.get("c", ["General"]))[0]
        notes = params.get("notes", params.get("n", [""]))[0]
        return {
            "title": title,
            "user": user,
            "username": user,
            "pass": pwd,
            "password": pwd,
            "url": url,
            "category": cat,
            "notes": notes,
        }

    data = json.loads(payload_str)
    if not isinstance(data, dict):
        raise ValueError("Formato de payload no reconocido.")
    ptype = data.get("t") or data.get("type")

    if ptype in ("pyclean-cred", "credential"):
        user = data.get("user") or data.get("username", "")
        pwd = data.get("pass") or data.get("password", "")
        res = {
            "title": data.get("title", ""),
            "user": user,
            "username": user,
            "pass": pwd,
            "password": pwd,
            "url": data.get("url", ""),
            "category": data.get("category", "General"),
            "notes": data.get("notes", ""),
        }
        if "id" in data:
            res["id"] = data["id"]
        return res

    elif ptype in ("pyclean-cred-enc", "ephemeral_credential"):
        if not pin:
            raise ValueError("Se requiere el PIN numérico para descifrar esta credencial.")
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("La librería 'cryptography' no está instalada.")

        salt = base64.b64decode(data["salt"])
        nonce = base64.b64decode(data["nonce"])
        ciphertext = base64.b64decode(data["ciphertext"])
        iterations = int(data.get("iterations", CRED_QR_ITERATIONS))

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        key = kdf.derive(pin.encode("utf-8"))
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, CRED_QR_AAD)
        inner = json.loads(plaintext.decode("utf-8"))

        user = inner.get("user") or inner.get("username", "")
        pwd = inner.get("pass") or inner.get("password", "")
        res = {
            "title": inner.get("title", ""),
            "user": user,
            "username": user,
            "pass": pwd,
            "password": pwd,
            "url": inner.get("url", ""),
            "category": inner.get("category", "General"),
            "notes": inner.get("notes", ""),
        }
        if "id" in inner:
            res["id"] = inner["id"]
        if "updated_at" in inner:
            res["updated_at"] = inner["updated_at"]
        return res
    else:
        raise ValueError(f"Tipo de payload desconocido: {ptype}")


def generate_credential_qr_payload(
    entry: dict | str,
    use_pin: bool = False,
    pin: str = "",
    vault: PasswordVault | None = None,
) -> str:
    """
    Función de utilidad a nivel de módulo para generar payload QR.
    Acepta un diccionario de credencial directamente, o un entry_id si se pasa vault.
    """
    if isinstance(entry, dict):
        if not use_pin:
            payload = {
                "t": "pyclean-cred",
                "v": 1,
                "title": entry.get("title", ""),
                "user": entry.get("username") or entry.get("user", ""),
                "pass": entry.get("password") or entry.get("pass", ""),
                "url": entry.get("url", ""),
                "category": entry.get("category", "General"),
                "notes": entry.get("notes", ""),
            }
            if entry.get("id"):
                payload["id"] = entry["id"]
            return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

        if not pin:
            raise ValueError("Se requiere un PIN numérico para el modo cifrado.")
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("La librería 'cryptography' no está instalada.")

        salt = os.urandom(16)
        nonce = os.urandom(12)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=CRED_QR_ITERATIONS,
        )
        key = kdf.derive(pin.encode("utf-8"))
        aesgcm = AESGCM(key)

        inner_data = {
            "id": entry.get("id", ""),
            "title": entry.get("title", ""),
            "user": entry.get("username") or entry.get("user", ""),
            "username": entry.get("username") or entry.get("user", ""),
            "pass": entry.get("password") or entry.get("pass", ""),
            "password": entry.get("password") or entry.get("pass", ""),
            "url": entry.get("url", ""),
            "category": entry.get("category", "General"),
            "notes": entry.get("notes", ""),
            "updated_at": entry.get("updated_at", int(time.time())),
        }
        plaintext = json.dumps(inner_data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, plaintext, CRED_QR_AAD)

        payload = {
            "t": "pyclean-cred-enc",
            "v": 1,
            "salt": base64.b64encode(salt).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            "iterations": CRED_QR_ITERATIONS,
        }
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    if vault is not None:
        return vault.generate_credential_qr_payload(entry, use_pin=use_pin, pin=pin)

    raise ValueError("Debe proporcionarse un objeto dict o un objeto vault con entry_id.")
