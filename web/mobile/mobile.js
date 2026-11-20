/**
 * PyClean Pro Mobile Companion - Main Application Controller
 * Handles SPA navigation, UI rendering, QR scanning, LAN sync, and clipboard auto-clear.
 */

(function () {
  'use strict';

  // Global app state
  const State = {
    activeView: 'view-unlock',
    previousView: 'view-unlock',
    currentEntry: null,
    activeCategory: 'Todas',
    searchTerm: '',
    masterPassword: '',
    clipboardInterval: null,
    clipboardRemaining: 0,
    pairingConfig: {
      ip: window.location.hostname || '127.0.0.1',
      port: window.location.port || '8765',
      token: ''
    }
  };

  // DOM Elements
  const DOM = {};

  function initElements() {
    DOM.app = document.getElementById('app');
    DOM.statusBadge = document.getElementById('vault-status-badge');
    DOM.statusText = document.getElementById('vault-status-text');
    DOM.btnHeaderLock = document.getElementById('btn-header-lock');
    DOM.btnHeaderSync = document.getElementById('btn-header-sync');
    DOM.btnHeaderScan = document.getElementById('btn-header-scan');

    // Views
    DOM.views = {
      'view-unlock': document.getElementById('view-unlock'),
      'view-list': document.getElementById('view-list'),
      'view-detail': document.getElementById('view-detail'),
      'view-scanner': document.getElementById('view-scanner'),
      'view-sync': document.getElementById('view-sync')
    };

    // Unlock View
    DOM.unlockPasswordInput = document.getElementById('unlock-password-input');
    DOM.btnToggleUnlockPass = document.getElementById('btn-toggle-unlock-pass');
    DOM.btnUnlockVault = document.getElementById('btn-unlock-vault');
    DOM.btnScanToPair = document.getElementById('btn-scan-to-pair');
    DOM.unlockError = document.getElementById('unlock-error');

    // List View
    DOM.searchInput = document.getElementById('search-credentials-input');
    DOM.categoryChips = document.getElementById('category-chips');
    DOM.credentialsList = document.getElementById('credentials-list');
    DOM.emptyListState = document.getElementById('empty-list-state');
    DOM.fabScan = document.getElementById('fab-scan');

    // Detail View
    DOM.btnBackToList = document.getElementById('btn-back-to-list');
    DOM.detailAvatar = document.getElementById('detail-avatar');
    DOM.detailTitle = document.getElementById('detail-title');
    DOM.detailCategoryBadge = document.getElementById('detail-category-badge');
    DOM.detailUsername = document.getElementById('detail-username');
    DOM.btnCopyDetailUser = document.getElementById('btn-copy-detail-user');
    DOM.detailPassword = document.getElementById('detail-password');
    DOM.btnToggleDetailPass = document.getElementById('btn-toggle-detail-pass');
    DOM.btnCopyDetailPass = document.getElementById('btn-copy-detail-pass');
    DOM.detailUrlRow = document.getElementById('detail-url-row');
    DOM.detailUrl = document.getElementById('detail-url');
    DOM.btnOpenUrl = document.getElementById('btn-open-url');
    DOM.detailNotesRow = document.getElementById('detail-notes-row');
    DOM.detailNotes = document.getElementById('detail-notes');
    DOM.btnDeleteEntry = document.getElementById('btn-delete-entry');

    // Scanner View
    DOM.scannerVideo = document.getElementById('scanner-video');
    DOM.btnFlipCamera = document.getElementById('btn-flip-camera');
    DOM.btnToggleTorch = document.getElementById('btn-toggle-torch');
    DOM.btnCloseScanner = document.getElementById('btn-close-scanner');
    DOM.fileInputQr = document.getElementById('file-input-qr');
    DOM.btnTriggerFileInput = document.getElementById('btn-trigger-file-input');
    DOM.manualQrInput = document.getElementById('manual-qr-input');
    DOM.btnSubmitManualQr = document.getElementById('btn-submit-manual-qr');
    DOM.cameraFallbackBanner = document.getElementById('camera-fallback-banner');
    DOM.btnSnapFallback = document.getElementById('btn-snap-fallback');

    // Sync View
    DOM.btnBackFromSync = document.getElementById('btn-back-from-sync');
    DOM.syncIpInput = document.getElementById('sync-ip-input');
    DOM.syncPortInput = document.getElementById('sync-port-input');
    DOM.syncTokenInput = document.getElementById('sync-token-input');
    DOM.btnTestConnection = document.getElementById('btn-test-connection');
    DOM.btnPullSync = document.getElementById('btn-pull-sync');
    DOM.btnPushSync = document.getElementById('btn-push-sync');
    DOM.btnExportLocalBackup = document.getElementById('btn-export-local-backup');
    DOM.fileInputImportBackup = document.getElementById('file-input-import-backup');
    DOM.btnTriggerImportBackup = document.getElementById('btn-trigger-import-backup');
    DOM.syncStatusMsg = document.getElementById('sync-status-msg');

    // Modals & Toast
    DOM.pinModal = document.getElementById('pin-modal');
    DOM.pinModalInput = document.getElementById('pin-modal-input');
    DOM.btnSubmitPin = document.getElementById('btn-submit-pin');
    DOM.btnCancelPin = document.getElementById('btn-cancel-pin');
    DOM.toastContainer = document.getElementById('toast-container');
  }

  // Navigation
  function switchView(viewId) {
    if (State.activeView === 'view-scanner' && viewId !== 'view-scanner') {
      window.MobileScanner.stopScanning();
    }

    State.previousView = State.activeView;
    State.activeView = viewId;

    Object.keys(DOM.views).forEach(id => {
      if (DOM.views[id]) {
        DOM.views[id].classList.toggle('active', id === viewId);
      }
    });

    // Update Header buttons visibility
    const isUnlocked = window.MobileStorage.isUnlocked();
    if (DOM.btnHeaderLock) {
      DOM.btnHeaderLock.style.display = isUnlocked ? 'flex' : 'none';
    }
    if (DOM.statusBadge) {
      DOM.statusBadge.className = `status-badge ${isUnlocked ? 'unlocked' : 'locked'}`;
      DOM.statusText.textContent = isUnlocked ? 'Desbloqueada' : 'Bloqueada';
    }

    if (viewId === 'view-list') {
      renderCredentialsList();
    } else if (viewId === 'view-scanner') {
      startCamera();
    }
  }

  // Toast Notifications
  function showToast(message, type = 'info', duration = 3000) {
    if (!DOM.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    DOM.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-10px)';
      toast.style.transition = 'all 0.25s ease';
      setTimeout(() => toast.remove(), 250);
    }, duration);
  }

  // Clipboard Copy with 30s Auto-Clear countdown
  function copyToClipboard(text, label = "Dato copiado") {
    if (!navigator.clipboard) {
      showToast("Portapapeles no soportado", "warning");
      return;
    }

    navigator.clipboard.writeText(text).then(() => {
      // Clear existing interval
      if (State.clipboardInterval) {
        clearInterval(State.clipboardInterval);
      }

      State.clipboardRemaining = 30;
      const toast = document.createElement('div');
      toast.className = 'toast success';
      toast.id = 'clipboard-countdown-toast';
      toast.innerHTML = `
        <span>✓ ${label}</span>
        <span class="countdown-pill" id="copy-countdown-badge">30s</span>
      `;

      // Remove previous countdown toast if any
      const existing = document.getElementById('clipboard-countdown-toast');
      if (existing) existing.remove();

      DOM.toastContainer.appendChild(toast);

      State.clipboardInterval = setInterval(() => {
        State.clipboardRemaining--;
        const badge = document.getElementById('copy-countdown-badge');
        if (badge) {
          badge.textContent = `${State.clipboardRemaining}s`;
        }

        if (State.clipboardRemaining <= 0) {
          clearInterval(State.clipboardInterval);
          State.clipboardInterval = null;
          // Auto-clear clipboard
          navigator.clipboard.writeText('').catch(() => {});
          if (toast) toast.remove();
          showToast("🔒 Portapapeles limpiado automáticamente", "info", 2500);
        }
      }, 1000);
    }).catch(err => {
      showToast("Error copiando al portapapeles", "warning");
    });
  }

  // Unlock Vault
  async function handleUnlock() {
    const pwd = DOM.unlockPasswordInput.value;
    if (!pwd) {
      showUnlockError("Por favor ingresa la contraseña maestra.");
      return;
    }

    showUnlockError("");
    DOM.btnUnlockVault.disabled = true;
    DOM.btnUnlockVault.textContent = "Desbloqueando...";

    try {
      const envelope = window.MobileStorage.getEnvelope();
      if (!envelope) {
        // Primera vez: crear una bóveda vacía con esta contraseña
        const emptyEntries = [];
        const initialEnvelope = await window.MobileCrypto.encryptVaultEnvelope(emptyEntries, pwd);
        window.MobileStorage.saveEnvelope(initialEnvelope);
        window.MobileStorage.setUnlockedEntries(emptyEntries);
        State.masterPassword = pwd;
        DOM.unlockPasswordInput.value = "";
        showToast("Bóveda local inicializada correctamente", "success");
        switchView('view-list');
        return;
      }

      // Descifrar el contenedor existente
      const entries = await window.MobileCrypto.decryptVaultEnvelope(envelope, pwd);
      window.MobileStorage.setUnlockedEntries(entries);
      State.masterPassword = pwd;
      DOM.unlockPasswordInput.value = "";
      showToast(`Bóveda desbloqueada (${entries.length} credenciales)`, "success");
      switchView('view-list');
    } catch (err) {
      showUnlockError("Contraseña incorrecta o contenedor dañado.");
    } finally {
      DOM.btnUnlockVault.disabled = false;
      DOM.btnUnlockVault.textContent = "Desbloquear Bóveda";
    }
  }

  function showUnlockError(msg) {
    if (DOM.unlockError) {
      DOM.unlockError.textContent = msg;
      DOM.unlockError.style.display = msg ? 'block' : 'none';
    }
  }

  // Render Credentials List
  function renderCredentialsList() {
    const entries = window.MobileStorage.getUnlockedEntries();
    if (!entries) {
      switchView('view-unlock');
      return;
    }

    DOM.credentialsList.innerHTML = '';
    const query = State.searchTerm.toLowerCase().trim();
    const cat = State.activeCategory;

    const filtered = entries.filter(e => {
      const matchCat = (cat === 'Todas' || (e.category || 'General').toLowerCase() === cat.toLowerCase());
      if (!matchCat) return false;

      if (!query) return true;
      const titleMatch = (e.title || '').toLowerCase().includes(query);
      const userMatch = (e.username || e.user || '').toLowerCase().includes(query);
      const notesMatch = (e.notes || '').toLowerCase().includes(query);
      return titleMatch || userMatch || notesMatch;
    });

    if (filtered.length === 0) {
      DOM.emptyListState.style.display = 'flex';
      return;
    }
    DOM.emptyListState.style.display = 'none';

    filtered.forEach(entry => {
      const card = document.createElement('div');
      card.className = 'credential-card';

      const initial = (entry.title ? entry.title.charAt(0).toUpperCase() : '?');
      const userStr = entry.username || entry.user || 'Sin usuario';

      card.innerHTML = `
        <div class="card-main">
          <div class="service-avatar">${initial}</div>
          <div class="card-info">
            <span class="card-title">${escapeHtml(entry.title || 'Sin Título')}</span>
            <span class="card-user">${escapeHtml(userStr)}</span>
          </div>
        </div>
        <div class="card-actions">
          <button class="action-btn btn-copy-pwd" title="Copiar contraseña">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          </button>
          <button class="action-btn btn-view-entry" title="Ver detalles">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="1"></circle><circle cx="19" cy="12" r="1"></circle><circle cx="5" cy="12" r="1"></circle></svg>
          </button>
        </div>
      `;

      card.querySelector('.card-main').addEventListener('click', () => {
        openDetailView(entry);
      });
      card.querySelector('.btn-view-entry').addEventListener('click', () => {
        openDetailView(entry);
      });
      card.querySelector('.btn-copy-pwd').addEventListener('click', (e) => {
        e.stopPropagation();
        copyToClipboard(entry.password || entry.pass || '', `Contraseña de ${entry.title}`);
      });

      DOM.credentialsList.appendChild(card);
    });
  }

  // Open Detail View
  function openDetailView(entry) {
    State.currentEntry = entry;
    const initial = (entry.title ? entry.title.charAt(0).toUpperCase() : '?');
    DOM.detailAvatar.textContent = initial;
    DOM.detailTitle.textContent = entry.title || 'Sin Título';
    DOM.detailCategoryBadge.textContent = entry.category || 'General';
    DOM.detailUsername.textContent = entry.username || entry.user || '—';

    DOM.detailPassword.textContent = '••••••••••••';
    DOM.detailPassword.classList.add('masked-pass');
    DOM.detailPassword.dataset.revealed = 'false';

    if (entry.url) {
      DOM.detailUrlRow.style.display = 'flex';
      DOM.detailUrl.textContent = entry.url;
      DOM.btnOpenUrl.onclick = () => window.open(entry.url, '_blank');
    } else {
      DOM.detailUrlRow.style.display = 'none';
    }

    if (entry.notes) {
      DOM.detailNotesRow.style.display = 'flex';
      DOM.detailNotes.textContent = entry.notes;
    } else {
      DOM.detailNotesRow.style.display = 'none';
    }

    switchView('view-detail');
  }

  // Scanner View & Camera
  async function startCamera() {
    if (DOM.cameraFallbackBanner) DOM.cameraFallbackBanner.style.display = 'none';
    const started = await window.MobileScanner.startScanning({
      videoElement: DOM.scannerVideo,
      onDetected: handleQrDetection,
      onError: (err) => {
        if (DOM.cameraFallbackBanner) DOM.cameraFallbackBanner.style.display = 'block';
        showToast("Cámara web no disponible en HTTP. Usa 'Tomar foto'.", "info", 5000);
      }
    });

    if (DOM.btnToggleTorch) {
      DOM.btnToggleTorch.style.display = window.MobileScanner.hasTorchCapability() ? 'flex' : 'none';
    }
  }

  async function handleQrDetection(dataStr) {
    try {
      // 1. Verificar si es URL de sincronización LAN con token
      if (dataStr.includes('/mobile/') && dataStr.includes('token=')) {
        try {
          const urlObj = new URL(dataStr);
          const token = urlObj.searchParams.get('token');
          if (token) {
            State.pairingConfig.ip = urlObj.hostname;
            State.pairingConfig.port = urlObj.port || '8765';
            State.pairingConfig.token = token;
            savePairingConfig();
            window.MobileScanner.stopScanning();
            switchView('view-sync');
            showToast("Emparejamiento QR detectado. Listo para sincronizar.", "success");
            return;
          }
        } catch (e) {}
      }

      // 2. Intentar parsear como credencial (plain o PIN-enc)
      let rawJson = null;
      try {
        rawJson = JSON.parse(dataStr);
      } catch (e) {}

      if (rawJson && (rawJson.t === 'pyclean-cred-enc' || rawJson.type === 'ephemeral_credential')) {
        // Requiere PIN modal
        window.MobileScanner.stopScanning();
        promptPinForQr(dataStr);
        return;
      }

      // Descifrar credencial plain o URI
      const cred = await window.MobileCrypto.decryptSingleCredentialQr(dataStr);
      if (cred && cred.title && (cred.password || cred.pass)) {
        window.MobileScanner.stopScanning();
        await importSingleCredential(cred);
        return;
      }

      showToast("Código QR no reconocido como credencial o sincronización", "warning");
    } catch (err) {
      showToast("Error procesando código QR: " + err.message, "warning");
    }
  }

  function promptPinForQr(payloadStr) {
    DOM.pinModal.classList.add('active');
    DOM.pinModalInput.value = '';
    DOM.pinModalInput.focus();

    DOM.btnSubmitPin.onclick = async () => {
      const pin = DOM.pinModalInput.value.trim();
      if (!pin) {
        showToast("Ingresa el PIN numérico de 6 dígitos", "warning");
        return;
      }
      try {
        const cred = await window.MobileCrypto.decryptSingleCredentialQr(payloadStr, pin);
        DOM.pinModal.classList.remove('active');
        await importSingleCredential(cred);
      } catch (e) {
        showToast("PIN incorrecto: " + e.message, "warning");
      }
    };

    DOM.btnCancelPin.onclick = () => {
      DOM.pinModal.classList.remove('active');
      switchView(State.previousView || 'view-list');
    };
  }

  async function importSingleCredential(cred) {
    const isUnlocked = window.MobileStorage.isUnlocked();
    if (!isUnlocked) {
      showToast("Desbloquea primero la bóveda para guardar la credencial", "warning");
      switchView('view-unlock');
      return;
    }

    const entries = window.MobileStorage.getUnlockedEntries();
    const incomingId = cred.id || ('cred_' + Date.now());
    const now = Math.floor(Date.now() / 1000);

    const newEntry = {
      id: incomingId,
      title: cred.title,
      username: cred.username || cred.user || '',
      password: cred.password || cred.pass,
      url: cred.url || '',
      category: cred.category || 'General',
      notes: cred.notes || '',
      created_at: cred.created_at || now,
      updated_at: cred.updated_at || now
    };

    // Reemplazar si ya existe o agregar
    const idx = entries.findIndex(e => e.id === newEntry.id || (e.title.toLowerCase() === newEntry.title.toLowerCase() && (e.username || '').toLowerCase() === newEntry.username.toLowerCase()));
    if (idx !== -1) {
      entries[idx] = newEntry;
    } else {
      entries.push(newEntry);
    }

    // Persistir contenedor cifrado
    if (State.masterPassword) {
      const updatedEnvelope = await window.MobileCrypto.encryptVaultEnvelope(entries, State.masterPassword);
      window.MobileStorage.saveEnvelope(updatedEnvelope);
    }

    window.MobileStorage.setUnlockedEntries(entries);
    showToast(`✓ Credencial "${newEntry.title}" importada con éxito`, "success");
    switchView('view-list');
  }

  // LAN Sync Operations
  function savePairingConfig() {
    DOM.syncIpInput.value = State.pairingConfig.ip;
    DOM.syncPortInput.value = State.pairingConfig.port;
    DOM.syncTokenInput.value = State.pairingConfig.token;
    window.MobileStorage.savePairingConfig(State.pairingConfig);
  }

  function loadPairingConfig() {
    const saved = window.MobileStorage.getPairingConfig();
    if (saved) {
      State.pairingConfig = Object.assign(State.pairingConfig, saved);
    }

    // Parse URL params for auto-pairing (?token=...&ip=...&port=...)
    const params = new URLSearchParams(window.location.search);
    if (params.get('token')) {
      State.pairingConfig.token = params.get('token');
    }
    if (params.get('ip')) {
      State.pairingConfig.ip = params.get('ip');
    }
    if (params.get('port')) {
      State.pairingConfig.port = params.get('port');
    }

    savePairingConfig();
  }

  async function testLanConnection() {
    const ip = DOM.syncIpInput.value.trim();
    const port = DOM.syncPortInput.value.trim();
    const token = DOM.syncTokenInput.value.trim();

    if (!ip || !port || !token) {
      showToast("Ingresa IP, Puerto y Token de emparejamiento", "warning");
      return;
    }

    DOM.syncStatusMsg.textContent = "Probando conexión con PC...";
    try {
      const resp = await fetch(`http://${ip}:${port}/api/sync/info?token=${encodeURIComponent(token)}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      if (!resp.ok) {
        throw new Error(`Servidor devolvió status ${resp.status}`);
      }
      const data = await resp.json();
      if (data.status === 'ok') {
        DOM.syncStatusMsg.textContent = `✓ Conectado a ${data.vault_name} (KDF: ${data.kdf})`;
        DOM.syncStatusMsg.style.color = 'var(--success)';
        showToast("Conexión con PC verificada", "success");
      } else {
        throw new Error(data.message || "Error desconocido");
      }
    } catch (e) {
      DOM.syncStatusMsg.textContent = `Error: ${e.message}`;
      DOM.syncStatusMsg.style.color = 'var(--danger)';
      showToast("Fallo al conectar con PC: " + e.message, "warning");
    }
  }

  async function pullSyncFromPc() {
    if (!window.MobileStorage.isUnlocked()) {
      showToast("Desbloquea la bóveda antes de sincronizar", "warning");
      return;
    }

    const ip = DOM.syncIpInput.value.trim();
    const port = DOM.syncPortInput.value.trim();
    const token = DOM.syncTokenInput.value.trim();

    DOM.syncStatusMsg.textContent = "Descargando bóveda de PC...";
    try {
      const resp = await fetch(`http://${ip}:${port}/api/sync/vault?token=${encodeURIComponent(token)}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const incomingEnvelope = await resp.json();

      if (!incomingEnvelope.ciphertext) {
        throw new Error("Respuesta inválida del servidor");
      }

      // Descifrar con contraseña maestra
      const incomingEntries = await window.MobileCrypto.decryptVaultEnvelope(incomingEnvelope, State.masterPassword);
      const currentEntries = window.MobileStorage.getUnlockedEntries() || [];

      // Smart Merge basado en ID y updated_at
      const mergedMap = new Map();
      currentEntries.forEach(e => mergedMap.set(e.id || (e.title + '|' + (e.username || '')), e));

      let addedCount = 0;
      let updatedCount = 0;

      incomingEntries.forEach(inc => {
        const key = inc.id || (inc.title + '|' + (inc.username || ''));
        if (mergedMap.has(key)) {
          const local = mergedMap.get(key);
          const incUpdated = inc.updated_at || 0;
          const localUpdated = local.updated_at || 0;
          if (incUpdated > localUpdated) {
            mergedMap.set(key, inc);
            updatedCount++;
          }
        } else {
          mergedMap.set(key, inc);
          addedCount++;
        }
      });

      const finalEntries = Array.from(mergedMap.values());
      const newEnvelope = await window.MobileCrypto.encryptVaultEnvelope(finalEntries, State.masterPassword);
      window.MobileStorage.saveEnvelope(newEnvelope);
      window.MobileStorage.setUnlockedEntries(finalEntries);

      DOM.syncStatusMsg.textContent = `✓ Sincronizado: ${addedCount} agregadas, ${updatedCount} actualizadas (Total: ${finalEntries.length})`;
      DOM.syncStatusMsg.style.color = 'var(--success)';
      showToast(`Sincronización completada (${finalEntries.length} credenciales)`, "success");
      switchView('view-list');
    } catch (e) {
      DOM.syncStatusMsg.textContent = `Error de sincronización: ${e.message}`;
      DOM.syncStatusMsg.style.color = 'var(--danger)';
      showToast("Fallo al descargar de PC: " + e.message, "warning");
    }
  }

  async function pushSyncToPc() {
    if (!window.MobileStorage.isUnlocked()) {
      showToast("Desbloquea la bóveda antes de sincronizar", "warning");
      return;
    }

    const ip = DOM.syncIpInput.value.trim();
    const port = DOM.syncPortInput.value.trim();
    const token = DOM.syncTokenInput.value.trim();

    DOM.syncStatusMsg.textContent = "Subiendo credenciales a PC...";
    try {
      const currentEntries = window.MobileStorage.getUnlockedEntries() || [];
      const envelope = await window.MobileCrypto.encryptVaultEnvelope(currentEntries, State.masterPassword);

      const resp = await fetch(`http://${ip}:${port}/api/sync/vault?token=${encodeURIComponent(token)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(envelope)
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const res = await resp.json();
      if (res.status === 'ok') {
        DOM.syncStatusMsg.textContent = `✓ PC actualizado con éxito (Fusionadas: ${res.merged}, Total en PC: ${res.total})`;
        DOM.syncStatusMsg.style.color = 'var(--success)';
        showToast("Bóveda sincronizada con el PC", "success");
      } else {
        throw new Error(res.message || "Error al sincronizar");
      }
    } catch (e) {
      DOM.syncStatusMsg.textContent = `Error: ${e.message}`;
      DOM.syncStatusMsg.style.color = 'var(--danger)';
      showToast("Fallo al subir a PC: " + e.message, "warning");
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Setup Event Listeners
  function setupListeners() {
    // Unlock View
    DOM.btnUnlockVault.addEventListener('click', handleUnlock);
    DOM.unlockPasswordInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') handleUnlock();
    });
    DOM.btnToggleUnlockPass.addEventListener('click', () => {
      const isPass = DOM.unlockPasswordInput.type === 'password';
      DOM.unlockPasswordInput.type = isPass ? 'text' : 'password';
    });
    DOM.btnScanToPair.addEventListener('click', () => {
      switchView('view-scanner');
    });

    // Header buttons
    DOM.btnHeaderLock.addEventListener('click', () => {
      window.MobileStorage.lockVault();
      State.masterPassword = '';
      showToast("Bóveda bloqueada", "info");
      switchView('view-unlock');
    });
    DOM.btnHeaderSync.addEventListener('click', () => {
      switchView('view-sync');
    });
    DOM.btnHeaderScan.addEventListener('click', () => {
      switchView('view-scanner');
    });

    // List View
    DOM.searchInput.addEventListener('input', (e) => {
      State.searchTerm = e.target.value;
      renderCredentialsList();
    });
    DOM.categoryChips.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (!chip) return;
      DOM.categoryChips.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      State.activeCategory = chip.dataset.category || 'Todas';
      renderCredentialsList();
    });
    DOM.fabScan.addEventListener('click', () => {
      switchView('view-scanner');
    });

    // Detail View
    DOM.btnBackToList.addEventListener('click', () => {
      switchView('view-list');
    });
    DOM.btnToggleDetailPass.addEventListener('click', () => {
      const isRevealed = DOM.detailPassword.dataset.revealed === 'true';
      if (isRevealed) {
        DOM.detailPassword.textContent = '••••••••••••';
        DOM.detailPassword.classList.add('masked-pass');
        DOM.detailPassword.dataset.revealed = 'false';
      } else {
        DOM.detailPassword.textContent = State.currentEntry.password || State.currentEntry.pass || '';
        DOM.detailPassword.classList.remove('masked-pass');
        DOM.detailPassword.dataset.revealed = 'true';
      }
    });
    DOM.btnCopyDetailPass.addEventListener('click', () => {
      if (State.currentEntry) {
        copyToClipboard(State.currentEntry.password || State.currentEntry.pass || '', `Contraseña de ${State.currentEntry.title}`);
      }
    });
    DOM.btnCopyDetailUser.addEventListener('click', () => {
      if (State.currentEntry) {
        copyToClipboard(State.currentEntry.username || State.currentEntry.user || '', `Usuario de ${State.currentEntry.title}`);
      }
    });
    DOM.btnDeleteEntry.addEventListener('click', async () => {
      if (!State.currentEntry) return;
      if (!confirm(`¿Eliminar la credencial "${State.currentEntry.title}"?`)) return;

      const entries = window.MobileStorage.getUnlockedEntries() || [];
      const updated = entries.filter(e => e.id !== State.currentEntry.id);
      if (State.masterPassword) {
        const env = await window.MobileCrypto.encryptVaultEnvelope(updated, State.masterPassword);
        window.MobileStorage.saveEnvelope(env);
      }
      window.MobileStorage.setUnlockedEntries(updated);
      showToast("Credencial eliminada", "info");
      switchView('view-list');
    });

    // Scanner View
    DOM.btnCloseScanner.addEventListener('click', () => {
      switchView(State.previousView || 'view-list');
    });
    DOM.btnFlipCamera.addEventListener('click', () => {
      window.MobileScanner.flipCamera();
    });
    DOM.btnToggleTorch.addEventListener('click', async () => {
      const state = await window.MobileScanner.toggleTorch();
      DOM.btnToggleTorch.style.color = state ? 'var(--accent-cyan)' : 'var(--text-main)';
    });
    DOM.btnTriggerFileInput.addEventListener('click', () => {
      DOM.fileInputQr.click();
    });
    if (DOM.btnSnapFallback) {
      DOM.btnSnapFallback.addEventListener('click', () => {
        DOM.fileInputQr.click();
      });
    }
    DOM.fileInputQr.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      try {
        const qrData = await window.MobileScanner.scanImageFile(file);
        handleQrDetection(qrData);
      } catch (err) {
        showToast(err.message, "warning");
      }
    });
    DOM.btnSubmitManualQr.addEventListener('click', () => {
      const text = DOM.manualQrInput.value.trim();
      if (!text) return;
      handleQrDetection(text);
      DOM.manualQrInput.value = '';
    });

    // Sync View
    DOM.btnBackFromSync.addEventListener('click', () => {
      switchView(State.previousView || (window.MobileStorage.isUnlocked() ? 'view-list' : 'view-unlock'));
    });
    DOM.btnTestConnection.addEventListener('click', testLanConnection);
    DOM.btnPullSync.addEventListener('click', pullSyncFromPc);
    DOM.btnPushSync.addEventListener('click', pushSyncToPc);

    // Export / Import Backup files
    DOM.btnExportLocalBackup.addEventListener('click', () => {
      const env = window.MobileStorage.getEnvelope();
      if (!env) {
        showToast("No hay ninguna bóveda para exportar", "warning");
        return;
      }
      const blob = new Blob([JSON.stringify(env, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pyclean_mobile_vault_${Date.now()}.vault`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Respaldo cifrado exportado", "success");
    });

    DOM.btnTriggerImportBackup.addEventListener('click', () => {
      DOM.fileInputImportBackup.click();
    });

    DOM.fileInputImportBackup.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (evt) => {
        try {
          const env = JSON.parse(evt.target.result);
          if (!env.salt || !env.ciphertext || !env.nonce) {
            throw new Error("Archivo de respaldo inválido");
          }
          window.MobileStorage.saveEnvelope(env);
          window.MobileStorage.lockVault();
          showToast("Respaldo importado. Desbloquéalo con su contraseña maestra.", "success");
          switchView('view-unlock');
        } catch (err) {
          showToast("Error importando respaldo: " + err.message, "warning");
        }
      };
      reader.readAsText(file);
    });

    // Handle auto-lock event from storage module
    window.MobileStorage.onLock(() => {
      State.masterPassword = '';
      if (State.clipboardInterval) {
        clearInterval(State.clipboardInterval);
        State.clipboardInterval = null;
      }
      switchView('view-unlock');
    });
  }

  // Register Service Worker for offline PWA
  function registerServiceWorker() {
    if ('serviceWorker' in navigator && (window.location.protocol === 'https:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
      navigator.serviceWorker.register('./sw.js').then((reg) => {
        console.log("Service Worker registrado con éxito:", reg.scope);
      }).catch((err) => {
        console.warn("Fallo al registrar Service Worker:", err);
      });
    }
  }

  // Initialize App on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    initElements();
    setupListeners();
    loadPairingConfig();
    registerServiceWorker();

    // Check if initial envelope exists
    if (!window.MobileStorage.hasEnvelope()) {
      showToast("¡Bienvenido! Empareja con tu PC o desbloquea para iniciar una bóveda nueva.", "info", 5000);
    }

    switchView('view-unlock');
  });

})();
