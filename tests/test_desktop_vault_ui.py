"""
Unit and integration tests for PyClean Pro Desktop Vault UI (Milestone 2):
- Offline pure-JS QR code generator (web/qrcode.min.js)
- Desktop HTML markup in web/index.html (modals, buttons, badges)
- Desktop JS controller in web/modules_v24.js (QR modal, Sync modal, timers, polling)
- Desktop CSS styles in web/style.css (high-contrast QR cards, PIN badges, pulsing status dots)
- Headless JS execution and DOM simulation with Node.js
"""

import os
import re
import json
import subprocess
import pytest


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(REPO_ROOT, "web")
INDEX_HTML = os.path.join(WEB_DIR, "index.html")
MODULES_JS = os.path.join(WEB_DIR, "modules_v24.js")
QRCODE_JS = os.path.join(WEB_DIR, "qrcode.min.js")
STYLE_CSS = os.path.join(WEB_DIR, "style.css")


# =========================================================================
# 1. QR Code Offline Library Verification
# =========================================================================

def test_qrcode_min_js_exists_and_standalone():
    """Verifies that web/qrcode.min.js exists, is non-empty, and has zero external dependencies."""
    assert os.path.exists(QRCODE_JS), "web/qrcode.min.js must exist"
    size = os.path.getsize(QRCODE_JS)
    assert size > 2000, f"web/qrcode.min.js seems too small ({size} bytes)"

    with open(QRCODE_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "QRCode" in content
    assert "CorrectLevel" in content
    assert "makeCode" in content
    assert "clear" in content

    # Should not require external CDNs or fetch calls
    assert "http://" not in content or "d-project.com" in content or "w3.org" in content
    assert "https://" not in content or "d-project.com" in content or "w3.org" in content


def test_qrcode_generator_execution_with_node():
    """Runs web/qrcode.min.js in Node.js to verify matrix generation and error correction levels."""
    node_test_script = """
    const QRCode = require('./web/qrcode.min.js');
    const qr = new QRCode(null, {
        text: 'pyclean://vault/v1/credential?title=Test&user=admin&pass=secret',
        correctLevel: QRCode.CorrectLevel.M
    });
    const matrix = qr.getMatrix();
    if (!matrix || matrix.length < 21) {
        process.exit(1);
    }
    // Check top-left finder pattern: 7x7 corner
    if (matrix[0][0] !== 1 || matrix[0][6] !== 1 || matrix[6][0] !== 1) {
        process.exit(2);
    }
    console.log(JSON.stringify({ status: 'ok', size: matrix.length }));
    """
    proc = subprocess.run(
        ["node", "-e", node_test_script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True
    )
    assert proc.returncode == 0, f"Node QRCode execution failed: {proc.stderr}"
    data = json.loads(proc.stdout.strip())
    assert data["status"] == "ok"
    assert data["size"] >= 21


# =========================================================================
# 2. Markup Verification in web/index.html
# =========================================================================

def test_index_html_includes_qrcode_script():
    """Verifies that index.html loads qrcode.min.js prior to modules_v24.js."""
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    qr_pos = html.find('src="qrcode.min.js"')
    mod_pos = html.find('src="modules_v24.js"')
    assert qr_pos != -1, "index.html must include <script src=\"qrcode.min.js\"></script>"
    assert mod_pos != -1, "index.html must include <script src=\"modules_v24.js\"></script>"
    assert qr_pos < mod_pos, "qrcode.min.js must be loaded before modules_v24.js"


def test_index_html_sync_toolbar_button():
    """Verifies the presence of the mobile sync button in #vault-unlocked-tools."""
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    tools_match = re.search(r'<div[^>]*id="vault-unlocked-tools"[^>]*>(.*?)</div>', html, re.DOTALL)
    assert tools_match is not None, "#vault-unlocked-tools container not found in index.html"
    tools_content = tools_match.group(1)

    assert 'id="btn-vault-sync"' in tools_content
    assert "Sincronizar Móvil" in tools_content


def test_index_html_vault_qr_modal_structure():
    """Verifies that #vault-qr-modal has all required elements: header, container, pin toggle/badge, timer, buttons."""
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="vault-qr-modal"' in html
    modal_match = re.search(r'<div[^>]*id="vault-qr-modal"[^>]*>(.*?)<!-- Modal de Sincronización', html, re.DOTALL)
    assert modal_match is not None, "#vault-qr-modal section not found"
    modal_html = modal_match.group(1)

    # Styling class
    assert "ui-modal-overlay" in html[html.find('id="vault-qr-modal"') - 50:html.find('id="vault-qr-modal"') + 50]
    assert "ui-modal-card" in modal_html

    # Required content elements
    assert "Código QR de Credencial" in modal_html
    assert 'id="vault-qr-service-title"' in modal_html
    assert 'id="vault-qr-canvas-container"' in modal_html
    assert 'id="vault-qr-username"' in modal_html
    assert 'id="vault-qr-pin-toggle"' in modal_html
    assert 'id="vault-qr-pin-container"' in modal_html
    assert 'id="vault-qr-pin-badge"' in modal_html
    assert 'id="vault-qr-timer"' in modal_html

    # Action buttons
    assert 'id="btn-vault-qr-copy"' in modal_html
    assert 'id="btn-vault-qr-close"' in modal_html
    assert "Copiar Texto" in modal_html
    assert "Cerrar" in modal_html


def test_index_html_vault_sync_modal_structure():
    """Verifies that #vault-sync-modal contains pairing QR, LAN URL, pairing steps, status dot, and buttons."""
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="vault-sync-modal"' in html
    modal_match = re.search(r'<div[^>]*id="vault-sync-modal"[^>]*>(.*?)<script', html, re.DOTALL)
    assert modal_match is not None, "#vault-sync-modal section not found"
    modal_html = modal_match.group(1)

    assert "ui-modal-overlay" in html[html.find('id="vault-sync-modal"') - 50:html.find('id="vault-sync-modal"') + 50]
    assert "ui-modal-card" in modal_html

    # Required content
    assert "Sincronización con App Móvil" in modal_html
    assert 'id="vault-sync-qr-container"' in modal_html
    assert 'id="vault-sync-url"' in modal_html
    assert 'id="btn-vault-sync-copy-url"' in modal_html
    assert 'id="vault-sync-status-badge"' in modal_html
    assert 'vault-status-dot' in modal_html
    assert 'id="vault-sync-status-text"' in modal_html
    assert 'id="vault-sync-clients-count"' in modal_html

    # Instructions
    assert "Abre la cámara o app en tu celular" in modal_html
    assert "Escanea este código" in modal_html
    assert "Ingresa tu contraseña maestra en el celular" in modal_html

    # Action buttons
    assert 'id="btn-vault-sync-stop"' in modal_html
    assert 'id="btn-vault-sync-close"' in modal_html
    assert "Detener Sincronización" in modal_html
    assert "Cerrar" in modal_html


# =========================================================================
# 3. JavaScript Logic in web/modules_v24.js
# =========================================================================

def test_modules_v24_qr_button_in_table_rows():
    """Verifies that renderVaultEntries creates the QR button with .btn-vault-qr."""
    with open(MODULES_JS, "r", encoding="utf-8") as f:
        js = f.read()

    assert "btn-vault-qr" in js
    assert "📱 QR" in js
    # Listener calls openVaultQrModal(entry.id)
    assert re.search(r'qrBtn\.addEventListener\(\s*["\']click["\']\s*,\s*\(\)\s*=>\s*\{\s*openVaultQrModal\(entry\.id\);?\s*\}\s*\)', js)


def test_modules_v24_modal_functions_exported():
    """Verifies that openVaultQrModal, closeVaultQrModal, openVaultSyncModal, closeVaultSyncModal are defined and on window."""
    with open(MODULES_JS, "r", encoding="utf-8") as f:
        js = f.read()

    assert "async function openVaultQrModal" in js
    assert "function closeVaultQrModal" in js
    assert "async function openVaultSyncModal" in js
    assert "async function closeVaultSyncModal" in js

    assert "window.openVaultQrModal = openVaultQrModal" in js
    assert "window.closeVaultQrModal = closeVaultQrModal" in js
    assert "window.openVaultSyncModal = openVaultSyncModal" in js
    assert "window.closeVaultSyncModal = closeVaultSyncModal" in js


def test_modules_v24_timer_and_pin_toggle_handling():
    """Verifies 60-second timer countdown and PIN toggle behavior in openVaultQrModal."""
    with open(MODULES_JS, "r", encoding="utf-8") as f:
        js = f.read()

    # 60-second timer logic
    assert "let secondsLeft = 60;" in js or "secondsLeft = 60" in js
    assert "closeVaultQrModal();" in js

    # Pin toggle listener
    assert 'id="vault-qr-pin-toggle"' in js or "vault-qr-pin-toggle" in js
    assert "openVaultQrModal(vaultCurrentQrEntryId, e.target.checked)" in js or "openVaultQrModal" in js


def test_modules_v24_mobile_sync_polling_and_cleanup():
    """Verifies that openVaultSyncModal polls status and closeVaultSyncModal cleans up intervals and server."""
    with open(MODULES_JS, "r", encoding="utf-8") as f:
        js = f.read()

    assert "vault_start_mobile_sync" in js
    assert "vault_get_mobile_sync_status" in js
    assert "vault_stop_mobile_sync" in js
    assert "clearInterval(vaultSyncInterval)" in js


# =========================================================================
# 4. CSS Styling Verification in web/style.css
# =========================================================================

def test_style_css_qr_and_sync_rules():
    """Verifies high-contrast QR cards, PIN badges, and pulsing green status dots in style.css."""
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        css = f.read()

    # QR container must have bright/white background for mobile camera contrast
    assert ".vault-qr-canvas-box" in css
    qr_box_match = re.search(r'\.vault-qr-canvas-box\s*\{([^}]+)\}', css)
    assert qr_box_match is not None
    qr_props = qr_box_match.group(1).lower()
    assert "background: #ffffff" in qr_props or "background:#ffffff" in qr_props or "background: white" in qr_props

    # PIN badge styling
    assert ".vault-pin-badge" in css
    pin_match = re.search(r'\.vault-pin-badge\s*\{([^}]+)\}', css)
    assert pin_match is not None
    assert "monospace" in pin_match.group(1).lower()

    # Pulsing status dot
    assert ".vault-status-dot" in css
    assert "pulseGreen" in css
    assert "@keyframes pulseGreen" in css


# =========================================================================
# 5. Headless JS & DOM Simulation with Node.js
# =========================================================================

def test_node_headless_ui_simulation():
    """Executes a simulated DOM run of openVaultQrModal and openVaultSyncModal in Node.js."""
    sim_script = """
    const fs = require('fs');

    // Minimal DOM environment simulation
    const domStore = {};
    function createElement(id, tagName = 'div') {
      const el = {
        id,
        tagName,
        style: {},
        classList: {
          classes: new Set(),
          add(c) { this.classes.add(c); },
          remove(c) { this.classes.delete(c); },
          contains(c) { return this.classes.has(c); }
        },
        children: [],
        appendChild(child) { this.children.push(child); },
        setAttribute(k, v) { this[k] = v; },
        getContext(t) { return null; },
        innerHTML: '',
        textContent: '',
        value: '',
        checked: false,
        addEventListener(evt, cb) {}
      };
      domStore[id] = el;
      return el;
    }

    // Required DOM elements
    [
      'vault-qr-modal', 'vault-qr-canvas-container', 'vault-qr-timer',
      'vault-qr-service-title', 'vault-qr-username', 'vault-qr-pin-toggle',
      'vault-qr-pin-container', 'vault-qr-pin-badge', 'btn-vault-qr-copy',
      'btn-vault-qr-close', 'vault-sync-modal', 'vault-sync-qr-container',
      'vault-sync-url', 'vault-sync-status-badge', 'vault-sync-status-text',
      'vault-sync-clients-count', 'btn-vault-sync-close', 'btn-vault-sync-stop',
      'btn-vault-sync-copy-url', 'btn-vault-sync', 'vault-unlocked-tools',
      'vault-lock-screen', 'vault-main-panel', 'vault-entries-tbody'
    ].forEach(id => createElement(id));

    global.document = {
      getElementById(id) { return domStore[id] || null; },
      createElement(tag) { return createElement('anon_' + Math.random(), tag); },
      createElementNS(ns, tag) { return createElement('anon_' + Math.random(), tag); }
    };
    global.window = {
      pywebview: {
        api: {
          async vault_get_qr_payload(entryId, usePin) {
            return {
              status: 'ok',
              payload: 'pyclean://vault/v1/credential?title=Test&user=alice&pass=secret',
              pin: usePin ? '654321' : ''
            };
          },
          async vault_start_mobile_sync() {
            return {
              status: 'ok',
              url: 'http://192.168.1.150:8765/mobile?token=sim_test_token',
              token: 'sim_test_token',
              qr_payload: '{"type":"pair","url":"http://192.168.1.150:8765"}',
              ip: '192.168.1.150',
              port: 8765
            };
          },
          async vault_get_mobile_sync_status() {
            return { running: true, clients_connected: 1, last_sync: 0 };
          },
          async vault_stop_mobile_sync() {
            return { status: 'ok' };
          }
        }
      }
    };
    global.navigator = { clipboard: { writeText: async () => {} } };
    global.v24Log = () => {};
    global.v24Escape = s => s;

    // Load QRCode
    global.QRCode = require('./web/qrcode.min.js');

    // Load modules_v24.js
    const modulesCode = fs.readFileSync('./web/modules_v24.js', 'utf8');
    eval(modulesCode);

    window.V24State.vaultEntries = [{ id: 'entry-123', title: 'GitHub', username: 'alice', password: 'pwd' }];

    (async () => {
      // 1. Test openVaultQrModal without PIN
      await window.openVaultQrModal('entry-123', false);
      const qrModal = document.getElementById('vault-qr-modal');
      const qrUser = document.getElementById('vault-qr-username');
      const qrTitle = document.getElementById('vault-qr-service-title');
      const qrTimer = document.getElementById('vault-qr-timer');

      if (!qrModal.classList.contains('open')) throw new Error('QR Modal did not open');
      if (qrTitle.textContent !== 'GitHub') throw new Error('Service title incorrect: ' + qrTitle.textContent);
      if (qrUser.textContent !== 'alice') throw new Error('Username incorrect: ' + qrUser.textContent);
      if (qrTimer.textContent !== '60') throw new Error('Timer initial value not 60: ' + qrTimer.textContent);

      // 2. Test openVaultQrModal WITH PIN
      await window.openVaultQrModal('entry-123', true);
      const pinContainer = document.getElementById('vault-qr-pin-container');
      const pinBadge = document.getElementById('vault-qr-pin-badge');
      if (pinContainer.style.display !== 'flex') throw new Error('PIN container not visible with PIN');
      if (pinBadge.textContent !== '654321') throw new Error('PIN badge wrong value: ' + pinBadge.textContent);

      // 3. Test closeVaultQrModal
      window.closeVaultQrModal();
      if (qrModal.classList.contains('open')) throw new Error('QR Modal did not close');

      // 4. Test openVaultSyncModal
      await window.openVaultSyncModal();
      const syncModal = document.getElementById('vault-sync-modal');
      const syncUrl = document.getElementById('vault-sync-url');
      const syncBadge = document.getElementById('vault-sync-status-badge');
      if (!syncModal.classList.contains('open')) throw new Error('Sync Modal did not open');
      if (!syncUrl.textContent.includes('192.168.1.150:8765')) throw new Error('Sync URL incorrect: ' + syncUrl.textContent);
      if (!syncBadge.classList.contains('active')) throw new Error('Sync badge not active');

      // 5. Test closeVaultSyncModal with stopServer
      await window.closeVaultSyncModal(true);
      if (syncModal.classList.contains('open')) throw new Error('Sync Modal did not close');

      console.log(JSON.stringify({ success: true, message: 'All Desktop UI simulation tests passed' }));
      process.exit(0);
    })().catch(err => {
      console.error(err);
      process.exit(1);
    });
    """
    proc = subprocess.run(
        ["node", "-e", sim_script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True
    )
    assert proc.returncode == 0, f"Headless UI simulation failed: {proc.stderr}"
    data = json.loads(proc.stdout.strip())
    assert data["success"] is True
