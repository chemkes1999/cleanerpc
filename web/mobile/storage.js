/**
 * PyClean Pro Mobile Companion - Storage & Memory Security Module
 * Enforces Zero-Knowledge offline persistence:
 * - Only encrypted envelopes are written to persistent storage (localStorage).
 * - Decrypted credentials reside ONLY in transient memory (sessionEntries).
 * - Automatic lock on 5 min inactivity or tab minimization (visibilitychange).
 */

(function (root, factory) {
  if (typeof module === 'object' && typeof module.exports === 'object') {
    module.exports = factory();
  } else if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else {
    root.MobileStorage = factory();
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const STORAGE_KEY_ENVELOPE = 'pyclean_mobile_vault_envelope';
  const STORAGE_KEY_PAIRING = 'pyclean_mobile_pairing_config';
  const AUTO_LOCK_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutos de inactividad

  let _sessionEntries = null;
  let _lastActivity = Date.now();
  let _autoLockTimer = null;
  const _lockCallbacks = [];

  function isLocalStorageAvailable() {
    try {
      const testKey = '__storage_test__';
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(testKey, testKey);
        window.localStorage.removeItem(testKey);
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  function saveEnvelope(envelope) {
    const serialized = typeof envelope === 'string' ? envelope : JSON.stringify(envelope);
    if (isLocalStorageAvailable()) {
      window.localStorage.setItem(STORAGE_KEY_ENVELOPE, serialized);
    }
  }

  function getEnvelope() {
    if (!isLocalStorageAvailable()) return null;
    const raw = window.localStorage.getItem(STORAGE_KEY_ENVELOPE);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  function hasEnvelope() {
    if (!isLocalStorageAvailable()) return false;
    return !!window.localStorage.getItem(STORAGE_KEY_ENVELOPE);
  }

  function clearEnvelope() {
    if (isLocalStorageAvailable()) {
      window.localStorage.removeItem(STORAGE_KEY_ENVELOPE);
    }
    lockVault();
  }

  function savePairingConfig(config) {
    if (isLocalStorageAvailable()) {
      window.localStorage.setItem(STORAGE_KEY_PAIRING, JSON.stringify(config));
    }
  }

  function getPairingConfig() {
    if (!isLocalStorageAvailable()) return null;
    const raw = window.localStorage.getItem(STORAGE_KEY_PAIRING);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  // Session Memory Management
  function setUnlockedEntries(entries) {
    _sessionEntries = Array.isArray(entries) ? entries : [];
    if (typeof window !== 'undefined') {
      window.sessionEntries = _sessionEntries;
    }
    touch();
  }

  function getUnlockedEntries() {
    if (!isUnlocked()) {
      return null;
    }
    touch();
    return _sessionEntries;
  }

  function isUnlocked() {
    if (_sessionEntries === null) {
      return false;
    }
    if (Date.now() - _lastActivity > AUTO_LOCK_TIMEOUT_MS) {
      lockVault();
      return false;
    }
    return true;
  }

  function touch() {
    _lastActivity = Date.now();
    if (_autoLockTimer) {
      clearTimeout(_autoLockTimer);
    }
    _autoLockTimer = setTimeout(() => {
      lockVault();
    }, AUTO_LOCK_TIMEOUT_MS);
  }

  function lockVault() {
    if (_autoLockTimer) {
      clearTimeout(_autoLockTimer);
      _autoLockTimer = null;
    }
    _sessionEntries = null;
    if (typeof window !== 'undefined') {
      window.sessionEntries = null;
    }
    _lastActivity = 0;

    for (const cb of _lockCallbacks) {
      try {
        cb();
      } catch (e) {
        console.error("Error en callback de bloqueo:", e);
      }
    }
  }

  function onLock(callback) {
    if (typeof callback === 'function') {
      _lockCallbacks.push(callback);
    }
  }

  // Setup security listeners in browser environment
  if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    const activityEvents = ['touchstart', 'touchend', 'click', 'keydown', 'scroll', 'mousemove'];
    activityEvents.forEach(evt => {
      document.addEventListener(evt, () => {
        if (_sessionEntries !== null) {
          touch();
        }
      }, { passive: true });
    });

    document.addEventListener('visibilitychange', () => {
      if (document.hidden && _sessionEntries !== null) {
        // Tab backgrounded or phone locked: auto-lock for security
        lockVault();
      }
    });
  }

  return {
    saveEnvelope,
    getEnvelope,
    hasEnvelope,
    clearEnvelope,
    savePairingConfig,
    getPairingConfig,
    setUnlockedEntries,
    getUnlockedEntries,
    isUnlocked,
    touch,
    lockVault,
    onLock,
    AUTO_LOCK_TIMEOUT_MS
  };
});
