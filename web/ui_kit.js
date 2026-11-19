/**
 * PyClean Pro v2.6 - UI Kit (Toasts, Modales Oscuros y Selector de Tema)
 */

(function () {
  const THEMES = [
    { id: "dark-theme", label: "Oscuro" },
    { id: "oled-theme", label: "OLED" },
    { id: "light-theme", label: "Claro" },
  ];

  function applyTheme(themeId) {
    const valid = THEMES.find(t => t.id === themeId) || THEMES[0];
    document.body.classList.remove("dark-theme", "oled-theme", "light-theme");
    document.body.classList.add(valid.id);
    try {
      localStorage.setItem("pyclean_theme", valid.id);
    } catch (_) {}

    const labelEl = document.getElementById("theme-toggle-label");
    if (labelEl) labelEl.textContent = valid.label;
  }

  function initThemeSwitcher() {
    let saved = "dark-theme";
    try {
      saved = localStorage.getItem("pyclean_theme") || "dark-theme";
    } catch (_) {}
    applyTheme(saved);

    const btn = document.getElementById("btn-theme-toggle");
    if (btn) {
      btn.addEventListener("click", () => {
        const current = THEMES.findIndex(t => document.body.classList.contains(t.id));
        const next = THEMES[(current + 1) % THEMES.length];
        applyTheme(next.id);
        window.showToast(`Tema cambiado a ${next.label}`, "info", 2200);
      });
    }
  }

  function showToast(message, type = "info", duration = 3400) {
    const container = document.getElementById("toast-container");
    if (!container || !message) return;

    const icons = {
      success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="20 6 9 17 4 12"/></svg>`,
      error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
      warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
      info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
    };

    const toast = document.createElement("div");
    toast.className = `ui-toast ui-toast-${type}`;
    toast.innerHTML = `
      <span class="ui-toast-icon">${icons[type] || icons.info}</span>
      <span class="ui-toast-msg"></span>
      <button type="button" class="ui-toast-close" aria-label="Cerrar">&times;</button>
    `;
    toast.querySelector(".ui-toast-msg").textContent = message;

    const dismiss = () => {
      if (toast.dataset.closing) return;
      toast.dataset.closing = "1";
      toast.classList.add("closing");
      setTimeout(() => toast.remove(), 220);
    };

    toast.querySelector(".ui-toast-close").addEventListener("click", dismiss);
    container.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add("visible"));
    if (duration > 0) setTimeout(dismiss, duration);
  }

  function showConfirmModal({ title = "Confirmar acción", message = "", confirmText = "Confirmar", cancelText = "Cancelar", danger = false } = {}) {
    return new Promise(resolve => {
      const overlay = document.getElementById("custom-confirm-modal");
      if (!overlay) {
        resolve(window.confirm(message || title));
        return;
      }

      const titleEl = document.getElementById("confirm-modal-title");
      const msgEl = document.getElementById("confirm-modal-msg");
      const okBtn = document.getElementById("confirm-modal-ok");
      const cancelBtn = document.getElementById("confirm-modal-cancel");

      if (titleEl) titleEl.textContent = title;
      if (msgEl) msgEl.textContent = message;
      if (okBtn) {
        okBtn.textContent = confirmText;
        okBtn.classList.toggle("danger", Boolean(danger));
      }
      if (cancelBtn) cancelBtn.textContent = cancelText;

      overlay.classList.add("open");

      const cleanup = result => {
        overlay.classList.remove("open");
        okBtn.removeEventListener("click", onOk);
        cancelBtn.removeEventListener("click", onCancel);
        overlay.removeEventListener("click", onBackdrop);
        document.removeEventListener("keydown", onKey);
        resolve(result);
      };

      const onOk = () => cleanup(true);
      const onCancel = () => cleanup(false);
      const onBackdrop = e => { if (e.target === overlay) cleanup(false); };
      const onKey = e => {
        if (e.key === "Escape") cleanup(false);
        else if (e.key === "Enter") cleanup(true);
      };

      okBtn.addEventListener("click", onOk);
      cancelBtn.addEventListener("click", onCancel);
      overlay.addEventListener("click", onBackdrop);
      document.addEventListener("keydown", onKey);
    });
  }

  window.showToast = showToast;
  window.showConfirmModal = showConfirmModal;
  window.initUiKit = initThemeSwitcher;

  document.addEventListener("DOMContentLoaded", initThemeSwitcher);
})();
