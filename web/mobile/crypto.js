/**
 * PyClean Pro Mobile Companion - Web Crypto API Module
 * Zero-Knowledge cryptographic implementation 1:1 bit-compatible with vault.py
 */

(function (root, factory) {
  if (typeof module === 'object' && typeof module.exports === 'object') {
    module.exports = factory();
  } else if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else {
    root.MobileCrypto = factory();
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const VAULT_AAD = new TextEncoder().encode("pyclean-pro-vault-v1");
  const CRED_QR_AAD = new TextEncoder().encode("pyclean-cred-v1");
  const DEFAULT_VAULT_ITERATIONS = 600000;
  const DEFAULT_CRED_QR_ITERATIONS = 100000;

  function getSubtleCrypto() {
    if (typeof globalThis !== 'undefined' && globalThis.crypto && globalThis.crypto.subtle) {
      return globalThis.crypto.subtle;
    }
    if (typeof window !== 'undefined' && window.crypto && window.crypto.subtle) {
      return window.crypto.subtle;
    }
    throw new Error("Web Crypto API (crypto.subtle) no está disponible en este entorno.");
  }

  function getRandomValues(array) {
    if (typeof globalThis !== 'undefined' && globalThis.crypto && globalThis.crypto.getRandomValues) {
      return globalThis.crypto.getRandomValues(array);
    }
    if (typeof window !== 'undefined' && window.crypto && window.crypto.getRandomValues) {
      return window.crypto.getRandomValues(array);
    }
    throw new Error("crypto.getRandomValues no disponible.");
  }

  function base64ToUint8(b64) {
    if (typeof Buffer !== 'undefined') {
      return new Uint8Array(Buffer.from(b64, 'base64'));
    }
    const binary = atob(b64);
    const len = binary.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
  }

  function uint8ToBase64(bytes) {
    if (typeof Buffer !== 'undefined') {
      return Buffer.from(bytes).toString('base64');
    }
    let binary = '';
    const len = bytes.byteLength;
    const chunkSize = 8192;
    for (let i = 0; i < len; i += chunkSize) {
      const chunk = bytes.subarray(i, Math.min(i + chunkSize, len));
      binary += String.fromCharCode.apply(null, chunk);
    }
    return btoa(binary);
  }

  async function deriveKey(masterPassword, salt, iterations = DEFAULT_VAULT_ITERATIONS) {
    const subtle = getSubtleCrypto();
    const enc = new TextEncoder();
    const saltBytes = typeof salt === 'string' ? base64ToUint8(salt) : (salt instanceof Uint8Array ? salt : new Uint8Array(salt));
    const passBytes = typeof masterPassword === 'string' ? enc.encode(masterPassword) : masterPassword;

    const baseKey = await subtle.importKey(
      "raw",
      passBytes,
      { name: "PBKDF2" },
      false,
      ["deriveKey"]
    );

    return subtle.deriveKey(
      {
        name: "PBKDF2",
        salt: saltBytes,
        iterations: Number(iterations),
        hash: "SHA-256"
      },
      baseKey,
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"]
    );
  }

  async function decryptVaultEnvelope(envelope, masterPassword) {
    const subtle = getSubtleCrypto();
    const env = typeof envelope === 'string' ? JSON.parse(envelope) : envelope;

    if (!env || !env.salt || !env.nonce || !env.ciphertext) {
      throw new Error("El contenedor de la bóveda está dañado (faltan campos salt/nonce/ciphertext).");
    }

    const salt = base64ToUint8(env.salt);
    const nonce = base64ToUint8(env.nonce);
    const ciphertext = base64ToUint8(env.ciphertext);
    const iterations = Number(env.iterations || DEFAULT_VAULT_ITERATIONS);

    const key = await deriveKey(masterPassword, salt, iterations);

    let decryptedBuffer;
    try {
      decryptedBuffer = await subtle.decrypt(
        {
          name: "AES-GCM",
          iv: nonce,
          additionalData: VAULT_AAD,
          tagLength: 128
        },
        key,
        ciphertext
      );
    } catch (err) {
      throw new Error("Contraseña maestra incorrecta o archivo de bóveda alterado.");
    }

    const plaintextStr = new TextDecoder().decode(decryptedBuffer);
    const payload = JSON.parse(plaintextStr);
    return payload.entries ? payload.entries : payload;
  }

  async function encryptVaultEnvelope(entries, masterPassword, salt = null, iterations = DEFAULT_VAULT_ITERATIONS) {
    const subtle = getSubtleCrypto();
    const saltBytes = salt ? (typeof salt === 'string' ? base64ToUint8(salt) : salt) : getRandomValues(new Uint8Array(16));
    const nonceBytes = getRandomValues(new Uint8Array(12));
    const iter = Number(iterations || DEFAULT_VAULT_ITERATIONS);

    const key = await deriveKey(masterPassword, saltBytes, iter);
    const payloadObj = Array.isArray(entries) ? { entries } : (entries.entries ? entries : { entries: [entries] });
    const plaintext = new TextEncoder().encode(JSON.stringify(payloadObj));

    const ciphertextBuffer = await subtle.encrypt(
      {
        name: "AES-GCM",
        iv: nonceBytes,
        additionalData: VAULT_AAD,
        tagLength: 128
      },
      key,
      plaintext
    );

    return {
      version: 1,
      kdf: "pbkdf2-sha256",
      iterations: iter,
      salt: uint8ToBase64(saltBytes),
      nonce: uint8ToBase64(nonceBytes),
      ciphertext: uint8ToBase64(new Uint8Array(ciphertextBuffer))
    };
  }

  async function decryptSingleCredentialQr(payloadStr, pin = "") {
    const subtle = getSubtleCrypto();
    const raw = (payloadStr || "").trim();
    if (!raw) {
      throw new Error("El código QR está vacío.");
    }

    // Caso 1: URI compacta pyclean:// o pyclean:
    if (raw.startsWith("pyclean://") || raw.startsWith("pyclean:cred") || raw.startsWith("pyclean:")) {
      let queryStr = "";
      const qIndex = raw.indexOf("?");
      if (qIndex !== -1) {
        queryStr = raw.substring(qIndex + 1);
      }
      const params = new URLSearchParams(queryStr);
      const title = params.get("title") || params.get("t") || "";
      const user = params.get("user") || params.get("u") || params.get("username") || "";
      const pass = params.get("pass") || params.get("p") || params.get("password") || "";
      const url = params.get("url") || "";
      const category = params.get("category") || params.get("c") || "General";
      const notes = params.get("notes") || params.get("n") || "";

      return {
        title,
        username: user,
        user,
        password: pass,
        pass,
        url,
        category,
        notes,
        updated_at: Math.floor(Date.now() / 1000)
      };
    }

    // Caso 2: Objeto JSON
    let data;
    try {
      data = JSON.parse(raw);
    } catch (e) {
      throw new Error("El formato del código QR no es un JSON o URI válido.");
    }

    if (!data || typeof data !== "object") {
      throw new Error("Payload no válido");
    }

    const ptype = data.t || data.type;

    if (ptype === "pyclean-cred" || ptype === "credential") {
      const user = data.username || data.user || "";
      const pass = data.password || data.pass || "";
      const res = {
        title: data.title || "",
        username: user,
        user,
        password: pass,
        pass,
        url: data.url || "",
        category: data.category || "General",
        notes: data.notes || "",
        updated_at: data.updated_at || Math.floor(Date.now() / 1000)
      };
      if (data.id) res.id = data.id;
      return res;
    }

    if (ptype === "pyclean-cred-enc" || ptype === "ephemeral_credential") {
      if (!pin) {
        throw new Error("Se requiere el PIN numérico de 6 dígitos para descifrar esta credencial.");
      }

      const salt = base64ToUint8(data.salt);
      const nonce = base64ToUint8(data.nonce);
      const ciphertext = base64ToUint8(data.ciphertext);
      const iterations = Number(data.iterations || DEFAULT_CRED_QR_ITERATIONS);

      const enc = new TextEncoder();
      const baseKey = await subtle.importKey(
        "raw",
        enc.encode(pin.toString()),
        { name: "PBKDF2" },
        false,
        ["deriveKey"]
      );

      const key = await subtle.deriveKey(
        {
          name: "PBKDF2",
          salt,
          iterations,
          hash: "SHA-256"
        },
        baseKey,
        { name: "AES-GCM", length: 256 },
        false,
        ["decrypt"]
      );

      let decryptedBuffer;
      try {
        decryptedBuffer = await subtle.decrypt(
          {
            name: "AES-GCM",
            iv: nonce,
            additionalData: CRED_QR_AAD,
            tagLength: 128
          },
          key,
          ciphertext
        );
      } catch (e) {
        throw new Error("PIN incorrecto o credencial alterada.");
      }

      const inner = JSON.parse(new TextDecoder().decode(decryptedBuffer));
      const user = inner.username || inner.user || "";
      const pass = inner.password || inner.pass || "";

      const res = {
        title: inner.title || "",
        username: user,
        user,
        password: pass,
        pass,
        url: inner.url || "",
        category: inner.category || "General",
        notes: inner.notes || "",
        updated_at: inner.updated_at || Math.floor(Date.now() / 1000)
      };
      if (inner.id) res.id = inner.id;
      return res;
    }

    throw new Error(`Tipo de payload QR desconocido: ${ptype}`);
  }

  async function encryptSingleCredentialQr(entry, pin = "") {
    if (!pin) {
      const payload = {
        t: "pyclean-cred",
        v: 1,
        title: entry.title || "",
        user: entry.username || entry.user || "",
        pass: entry.password || entry.pass || "",
        url: entry.url || "",
        category: entry.category || "General",
        notes: entry.notes || "",
      };
      if (entry.id) payload.id = entry.id;
      return JSON.stringify(payload);
    }

    const subtle = getSubtleCrypto();
    const salt = getRandomValues(new Uint8Array(16));
    const nonce = getRandomValues(new Uint8Array(12));
    const iterations = DEFAULT_CRED_QR_ITERATIONS;

    const baseKey = await subtle.importKey(
      "raw",
      new TextEncoder().encode(pin.toString()),
      { name: "PBKDF2" },
      false,
      ["deriveKey"]
    );

    const key = await subtle.deriveKey(
      {
        name: "PBKDF2",
        salt,
        iterations,
        hash: "SHA-256"
      },
      baseKey,
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt"]
    );

    const inner = {
      id: entry.id || "",
      title: entry.title || "",
      user: entry.username || entry.user || "",
      username: entry.username || entry.user || "",
      pass: entry.password || entry.pass || "",
      password: entry.password || entry.pass || "",
      url: entry.url || "",
      category: entry.category || "General",
      notes: entry.notes || "",
      updated_at: entry.updated_at || Math.floor(Date.now() / 1000)
    };

    const plaintext = new TextEncoder().encode(JSON.stringify(inner));
    const ciphertextBuffer = await subtle.encrypt(
      {
        name: "AES-GCM",
        iv: nonce,
        additionalData: CRED_QR_AAD,
        tagLength: 128
      },
      key,
      plaintext
    );

    const payload = {
      t: "pyclean-cred-enc",
      v: 1,
      salt: uint8ToBase64(salt),
      nonce: uint8ToBase64(nonce),
      ciphertext: uint8ToBase64(new Uint8Array(ciphertextBuffer)),
      iterations
    };
    return JSON.stringify(payload);
  }

  return {
    VAULT_AAD,
    CRED_QR_AAD,
    DEFAULT_VAULT_ITERATIONS,
    DEFAULT_CRED_QR_ITERATIONS,
    deriveKey,
    decryptVaultEnvelope,
    encryptVaultEnvelope,
    decryptSingleCredentialQr,
    encryptSingleCredentialQr,
    base64ToUint8,
    uint8ToBase64
  };
});
