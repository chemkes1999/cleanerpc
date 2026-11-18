/**
 * PyClean Pro - Frontend Logic con Animaciones GSAP
 * Se comunica con Python a través de window.pywebview.api
 */

// Estado global de la aplicación
const AppState = {
  isAdmin: false,
  drives: [],
  selectedDrive: "C:\\",
  config: { min_age_hours: 24, exclusions: [] },
  categories: [],
  selectedCategories: new Set(),
  scannedResults: {},
  totalScannedBytes: 0,
  totalScannedFiles: 0,
  heavyFiles: [],
  isBusy: false,
  logOpen: true
};

// Formateador de bytes a unidades legibles
function formatSize(bytes) {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let size = parseFloat(bytes);
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i++;
  }
  return `${size.toFixed(2)} ${units[i]}`;
}

// Inicialización de la aplicación
window.addEventListener("pywebviewready", initApp);
// Fallback para testing en navegador si no está pywebview
document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    if (!window.pywebview) {
      console.warn("PyWebView no detectado. Modo desarrollo activo.");
      initMockApp();
    }
  }, 600);
});

async function initApp() {
  addLog("Conexión con el núcleo Python establecida.", "success");
  
  // Registrar callback para logs desde Python
  window.onPyLog = (msg, tag) => addLog(msg, tag);

  try {
    const state = await window.pywebview.api.get_initial_state(AppState.selectedDrive);
    applyInitialState(state);
  } catch (err) {
    addLog(`Error al inicializar estado: ${err}`, "error");
  }

  setupEventListeners();
  runIntroAnimations();
}

function applyInitialState(state) {
  AppState.isAdmin = state.is_admin;
  AppState.drives = state.drives || [];
  AppState.config = state.config || { min_age_hours: 24, exclusions: [] };
  AppState.categories = state.categories || [];

  // Marcar todas las categorías seleccionadas por defecto
  AppState.categories.forEach(c => AppState.selectedCategories.add(c.key));

  // Renderizar componentes iniciales
  renderAdminStatus();
  renderDriveSelector();
  updateSystemGauges(state.stats);
  renderCategoriesGrid();
  renderExclusionsList();
  document.getElementById("setting-age").value = AppState.config.min_age_hours || 24;
  updatePresetButtons(AppState.config.min_age_hours || 24);

  // Comprobar aplicaciones abiertas que bloquean limpieza
  const lockedBanner = document.getElementById("locked-apps-banner");
  if (state.locked_apps && state.locked_apps.length > 0) {
    const appsText = state.locked_apps.map(a => a.name).join(", ");
    document.getElementById("banner-apps-text").textContent = appsText;
    lockedBanner.style.display = "flex";
    addLog(`Aviso: Detectadas aplicaciones abiertas (${appsText}). Ciérralas para limpiar su caché.`, "warning");
  } else {
    lockedBanner.style.display = "none";
  }

  // Cargar lista de inicio
  loadStartupPrograms();
}

// --- Animaciones GSAP de Entrada y Transiciones ---

function runIntroAnimations() {
  if (typeof gsap === "undefined") return;

  const tl = gsap.timeline();
  tl.from(".sidebar", { x: -30, opacity: 0, duration: 0.6, ease: "power3.out" })
    .from(".top-bar", { y: -20, opacity: 0, duration: 0.4, ease: "power2.out" }, "-=0.3")
    .from(".hero-card", {
      y: 30,
      opacity: 0,
      stagger: 0.1,
      duration: 0.5,
      ease: "back.out(1.2)"
    }, "-=0.2")
    .from(".breakdown-card", { y: 20, opacity: 0, duration: 0.4, ease: "power2.out" }, "-=0.2");
}

function animateTabTransition(targetTabId) {
  const currentActive = document.querySelector(".tab-view.active");
  const targetView = document.getElementById(targetTabId);

  if (currentActive === targetView) return;

  if (typeof gsap !== "undefined" && currentActive) {
    gsap.to(currentActive, {
      opacity: 0,
      y: -10,
      duration: 0.18,
      ease: "power1.in",
      onComplete: () => {
        currentActive.classList.remove("active");
        currentActive.style.display = "none";
        
        targetView.style.display = "flex";
        targetView.classList.add("active");
        gsap.fromTo(targetView,
          { opacity: 0, y: 15 },
          { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }
        );
      }
    });
  } else {
    if (currentActive) currentActive.classList.remove("active");
    targetView.classList.add("active");
  }
}

// --- Gráficos Circulares SVG Animados con GSAP ---

function updateSystemGauges(stats) {
  if (!stats) return;

  const circumference = 314; // 2 * PI * 50

  // 1. Disco
  const diskPct = Math.min(100, Math.max(0, stats.disk_percent || 0));
  const diskOffset = circumference * (1 - diskPct / 100);

  if (typeof gsap !== "undefined") {
    gsap.to("#disk-gauge-fill", {
      strokeDashoffset: diskOffset,
      duration: 1.2,
      ease: "power2.out"
    });
    gsap.to("#disk-mini-bar", {
      width: `${diskPct}%`,
      duration: 1.0,
      ease: "power2.out"
    });

    const currentText = parseInt(document.getElementById("disk-percent-text").textContent) || 0;
    const diskCounter = { val: currentText };
    gsap.to(diskCounter, {
      val: diskPct,
      duration: 1.2,
      ease: "power2.out",
      onUpdate: () => {
        document.getElementById("disk-percent-text").textContent = `${Math.round(diskCounter.val)}%`;
      }
    });
  } else {
    document.getElementById("disk-gauge-fill").style.strokeDashoffset = diskOffset;
    document.getElementById("disk-mini-bar").style.width = `${diskPct}%`;
    document.getElementById("disk-percent-text").textContent = `${diskPct}%`;
  }

  const freeGb = (stats.disk_free / (1024 ** 3)).toFixed(1);
  const totalGb = (stats.disk_total / (1024 ** 3)).toFixed(1);
  document.getElementById("disk-detail-text").textContent = `${freeGb} GB libres de ${totalGb} GB`;

  // 2. RAM
  const ramPct = Math.min(100, Math.max(0, stats.ram_load || 0));
  const ramOffset = circumference * (1 - ramPct / 100);

  if (typeof gsap !== "undefined") {
    gsap.to("#ram-gauge-fill", {
      strokeDashoffset: ramOffset,
      duration: 1.2,
      ease: "power2.out"
    });
    gsap.to("#ram-mini-bar", {
      width: `${ramPct}%`,
      duration: 1.0,
      ease: "power2.out"
    });

    const currentRam = parseInt(document.getElementById("ram-percent-text").textContent) || 0;
    const ramCounter = { val: currentRam };
    gsap.to(ramCounter, {
      val: ramPct,
      duration: 1.2,
      ease: "power2.out",
      onUpdate: () => {
        document.getElementById("ram-percent-text").textContent = `${Math.round(ramCounter.val)}%`;
      }
    });
  } else {
    document.getElementById("ram-gauge-fill").style.strokeDashoffset = ramOffset;
    document.getElementById("ram-mini-bar").style.width = `${ramPct}%`;
    document.getElementById("ram-percent-text").textContent = `${ramPct}%`;
  }

  const ramUsedMb = Math.round((stats.ram_used || 0) / (1024 ** 2));
  const ramTotalMb = Math.round((stats.ram_total || 0) / (1024 ** 2));
  document.getElementById("ram-detail-text").textContent = `${ramUsedMb.toLocaleString()} MB en uso / ${ramTotalMb.toLocaleString()} MB`;
}

// Contador Animado con GSAP para Espacio Reclamable
function animateReclaimableCounter(targetBytes, targetFiles) {
  const display = document.getElementById("total-scanned-display");
  const filesLabel = document.getElementById("total-scanned-files");
  
  if (typeof gsap !== "undefined") {
    const counterObj = { bytes: AppState.totalScannedBytes };
    gsap.to(counterObj, {
      bytes: targetBytes,
      duration: 0.9,
      ease: "power2.out",
      onUpdate: () => {
        display.textContent = formatSize(counterObj.bytes);
      }
    });
    gsap.fromTo(display, { scale: 1.15 }, { scale: 1.0, duration: 0.4, ease: "elastic.out(1, 0.5)" });
  } else {
    display.textContent = formatSize(targetBytes);
  }

  AppState.totalScannedBytes = targetBytes;
  AppState.totalScannedFiles = targetFiles;
  filesLabel.textContent = `${targetFiles.toLocaleString()} archivos detectados`;
}

// --- Renderizado de Componentes UI ---

function renderAdminStatus() {
  const chip = document.getElementById("admin-chip");
  const label = document.getElementById("admin-label");
  const btnElevate = document.getElementById("btn-elevate");

  if (AppState.isAdmin) {
    chip.className = "admin-chip is-admin";
    label.textContent = "Modo Administrador";
    btnElevate.style.display = "none";
  } else {
    chip.className = "admin-chip not-admin";
    label.textContent = "Modo Estándar";
    btnElevate.style.display = "block";
  }
}

function renderDriveSelector() {
  const select = document.getElementById("drive-select");
  const summary = document.getElementById("drive-summary");
  select.innerHTML = "";

  AppState.drives.forEach(d => {
    const opt = document.createElement("option");
    opt.value = d.letter;
    const freeGb = (d.free / (1024 ** 3)).toFixed(1);
    opt.textContent = `${d.letter} (${d.type} - ${freeGb} GB libres)`;
    if (d.letter === AppState.selectedDrive) opt.selected = true;
    select.appendChild(opt);
  });

  const cur = AppState.drives.find(d => d.letter === AppState.selectedDrive) || AppState.drives[0];
  if (cur) {
    const totalGb = (cur.total / (1024 ** 3)).toFixed(1);
    const freeGb = (cur.free / (1024 ** 3)).toFixed(1);
    summary.textContent = `${freeGb} GB libres de ${totalGb} GB`;
  }
}

function renderCategoriesGrid() {
  const grid = document.getElementById("categories-grid");
  grid.innerHTML = "";

  AppState.categories.forEach(cat => {
    const isSelected = AppState.selectedCategories.has(cat.key);
    const card = document.createElement("div");
    card.className = `category-card ${isSelected ? 'selected' : ''}`;
    card.id = `cat-card-${cat.key}`;

    const adminTag = cat.requires_admin ? `<span class="tag-admin">Admin</span>` : "";

    card.innerHTML = `
      <input type="checkbox" class="cat-checkbox" id="chk-${cat.key}" ${isSelected ? 'checked' : ''}>
      <div class="cat-info">
        <div class="cat-header">
          <span class="cat-name">${cat.name}</span>
          <span class="cat-size-badge" id="size-badge-${cat.key}">0 B</span>
        </div>
        <p class="cat-desc">${cat.desc}</p>
        <div class="cat-meta">
          ${adminTag}
          <span class="file-count-label" id="files-badge-${cat.key}">0 archivos</span>
        </div>
      </div>
    `;

    // Interacción al hacer clic
    card.addEventListener("click", (e) => {
      if (e.target.tagName !== "INPUT") {
        const chk = card.querySelector(".cat-checkbox");
        chk.checked = !chk.checked;
        toggleCategorySelection(cat.key, chk.checked, card);
      }
    });

    const chk = card.querySelector(".cat-checkbox");
    chk.addEventListener("change", () => {
      toggleCategorySelection(cat.key, chk.checked, card);
    });

    grid.appendChild(card);
  });

  updateCleanBadge();
}

function toggleCategorySelection(catKey, isChecked, cardEl) {
  if (isChecked) {
    AppState.selectedCategories.add(catKey);
    cardEl.classList.add("selected");
  } else {
    AppState.selectedCategories.delete(catKey);
    cardEl.classList.remove("selected");
  }
  updateCleanBadge();
}

function updateCleanBadge() {
  document.getElementById("clean-badge").textContent = AppState.selectedCategories.size;
}

function renderBreakdownList() {
  const list = document.getElementById("breakdown-list");
  list.innerHTML = "";

  const results = Object.values(AppState.scannedResults).filter(r => r.size > 0);
  if (results.length === 0) {
    list.innerHTML = `<div class="empty-state">No se detectaron archivos basura en las categorías analizadas.</div>`;
    return;
  }

  const maxSize = Math.max(...results.map(r => r.size));

  results.sort((a, b) => b.size - a.size).forEach(res => {
    const cat = AppState.categories.find(c => c.key === res.key);
    const catName = cat ? cat.name : res.key;
    const pct = ((res.size / maxSize) * 100).toFixed(0);

    const row = document.createElement("div");
    row.className = "breakdown-row";
    row.innerHTML = `
      <div class="breakdown-row-header">
        <span>${catName}</span>
        <strong>${res.size_formatted} (${res.count} archivos)</strong>
      </div>
      <div class="breakdown-bar-track">
        <div class="breakdown-bar-fill" style="width: 0%;" data-target="${pct}"></div>
      </div>
    `;
    list.appendChild(row);
  });

  // Animación GSAP de llenado de barras
  if (typeof gsap !== "undefined") {
    gsap.utils.toArray(".breakdown-bar-fill").forEach(bar => {
      const target = bar.getAttribute("data-target");
      gsap.to(bar, { width: `${target}%`, duration: 0.8, ease: "power2.out" });
    });
  } else {
    document.querySelectorAll(".breakdown-bar-fill").forEach(bar => {
      bar.style.width = `${bar.getAttribute("data-target")}%`;
    });
  }
}

// --- Programas de Inicio de Windows ---

async function loadStartupPrograms() {
  const tbody = document.getElementById("startup-tbody");
  tbody.innerHTML = `<tr><td colspan="5" class="table-loading">Cargando programas de inicio...</td></tr>`;

  try {
    let progs = [];
    if (window.pywebview) {
      progs = await window.pywebview.api.get_startup_programs();
    }
    renderStartupTable(progs);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="table-loading">Error al cargar programas: ${err}</td></tr>`;
  }
}

function renderStartupTable(progs) {
  const tbody = document.getElementById("startup-tbody");
  tbody.innerHTML = "";

  if (!progs || progs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No se detectaron programas de inicio configurados.</td></tr>`;
    return;
  }

  progs.forEach((p, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <label class="switch">
          <input type="checkbox" ${p.enabled ? 'checked' : ''} data-idx="${idx}">
          <span class="slider"></span>
        </label>
      </td>
      <td><strong>${escapeHtml(p.name)}</strong></td>
      <td><span class="tag-admin" style="color: var(--text-muted); background: var(--bg-card-hover);">${escapeHtml(p.scope)}</span></td>
      <td style="max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(p.command)}">
        <code>${escapeHtml(p.command)}</code>
      </td>
      <td style="text-align: right;">
        <span class="status-indicator" style="color: ${p.enabled ? 'var(--success)' : 'var(--text-dim)'}; font-weight: 600;">
          ${p.enabled ? 'Habilitado' : 'Deshabilitado'}
        </span>
      </td>
    `;

    const chk = tr.querySelector("input[type='checkbox']");
    chk.addEventListener("change", async () => {
      addLog(`Cambiando estado de '${p.name}'...`, "info");
      try {
        const res = await window.pywebview.api.toggle_startup_program(p);
        if (res.success) {
          addLog(res.message, "success");
          p.enabled = !p.enabled;
          const statusText = tr.querySelector(".status-indicator");
          statusText.textContent = p.enabled ? 'Habilitado' : 'Deshabilitado';
          statusText.style.color = p.enabled ? 'var(--success)' : 'var(--text-dim)';
        } else {
          addLog(res.message, "warning");
          chk.checked = p.enabled; // Revertir
        }
      } catch (e) {
        addLog(`Error al modificar inicio: ${e}`, "error");
        chk.checked = p.enabled;
      }
    });

    tbody.appendChild(tr);
  });
}

// --- Top Archivos Pesados ---

function renderHeavyFilesTable() {
  const tbody = document.getElementById("files-tbody");
  tbody.innerHTML = "";

  if (AppState.heavyFiles.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-state">Ejecuta un análisis para inspeccionar los archivos más pesados.</td></tr>`;
    return;
  }

  AppState.heavyFiles.forEach(f => {
    const tr = document.createElement("tr");
    const filename = f.path.split(/[\\/]/).pop();
    tr.innerHTML = `
      <td><strong>${escapeHtml(filename)}</strong></td>
      <td><span class="cat-size-badge">${formatSize(f.size)}</span></td>
      <td style="max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(f.path)}">
        <span style="color: var(--text-muted); font-size: 12px;">${escapeHtml(f.path)}</span>
      </td>
      <td style="text-align: right;">
        <button class="btn-tool btn-open-folder" title="Abrir en Explorador de Windows">
          📁 Explorar
        </button>
      </td>
    `;

    tr.querySelector(".btn-open-folder").addEventListener("click", () => {
      if (window.pywebview) {
        window.pywebview.api.open_folder(f.path);
      }
    });

    tbody.appendChild(tr);
  });
}

// --- Configuración y Exclusiones ---

function renderExclusionsList() {
  const list = document.getElementById("exclusions-list");
  list.innerHTML = "";

  const exclusions = AppState.config.exclusions || [];
  if (exclusions.length === 0) {
    list.innerHTML = `<div class="empty-state">No hay carpetas excluidas actualmente.</div>`;
    return;
  }

  exclusions.forEach((exc, idx) => {
    const item = document.createElement("div");
    item.className = "exclusion-item";
    item.innerHTML = `
      <span>${escapeHtml(exc)}</span>
      <button class="btn-del-exclusion" title="Eliminar exclusión">✕</button>
    `;
    item.querySelector(".btn-del-exclusion").addEventListener("click", () => {
      AppState.config.exclusions.splice(idx, 1);
      renderExclusionsList();
    });
    list.appendChild(item);
  });
}

function updatePresetButtons(hours) {
  document.querySelectorAll(".preset-btn").forEach(btn => {
    btn.classList.toggle("active", parseInt(btn.dataset.hours) === parseInt(hours));
  });
}

// --- Operaciones Principales: Escaneo y Limpieza ---

async function runScan() {
  if (AppState.isBusy) return;
  if (AppState.selectedCategories.size === 0) {
    addLog("Selecciona al menos una categoría para analizar.", "warning");
    return;
  }

  setBusyState(true, "Iniciando análisis del sistema...");
  addLog("--- INICIANDO ANÁLISIS DE ARCHIVOS BASURA ---", "info");

  AppState.scannedResults = {};
  AppState.heavyFiles = [];
  let totalBytes = 0;
  let totalFiles = 0;

  const categoriesToScan = AppState.categories.filter(c => AppState.selectedCategories.has(c.key));
  const totalCount = categoriesToScan.length;

  for (let i = 0; i < totalCount; i++) {
    const cat = categoriesToScan[i];
    const pct = Math.round(((i + 1) / totalCount) * 100);
    
    updateProgress(pct, `Analizando: ${cat.name}...`);
    addLog(`Analizando ${cat.name}...`, "dim");

    try {
      const res = await window.pywebview.api.scan_category(
        cat.key,
        parseInt(AppState.config.min_age_hours || 24),
        AppState.config.exclusions || []
      );

      AppState.scannedResults[cat.key] = res;
      totalBytes += res.size;
      totalFiles += res.count;

      if (res.items && res.items.length > 0) {
        AppState.heavyFiles.push(...res.items);
      }

      // Actualizar tarjeta de categoría
      const sizeBadge = document.getElementById(`size-badge-${cat.key}`);
      const filesBadge = document.getElementById(`files-badge-${cat.key}`);
      if (sizeBadge) sizeBadge.textContent = res.size_formatted;
      if (filesBadge) filesBadge.textContent = `${res.count} archivos`;

    } catch (err) {
      addLog(`Error analizando ${cat.name}: ${err}`, "error");
    }
  }

  // Ordenar archivos pesados
  AppState.heavyFiles.sort((a, b) => b.size - a.size);
  AppState.heavyFiles = AppState.heavyFiles.slice(0, 100);

  // Animaciones finales con GSAP
  animateReclaimableCounter(totalBytes, totalFiles);
  renderBreakdownList();
  renderHeavyFilesTable();

  updateProgress(100, "Análisis completado con éxito");
  addLog(`Análisis finalizado: ${formatSize(totalBytes)} recuperables en ${totalFiles.toLocaleString()} archivos.`, "success");

  // Habilitar botón de limpieza si hay algo que borrar
  document.getElementById("btn-main-clean").disabled = (totalBytes === 0 && totalFiles === 0);

  setBusyState(false);
}

async function runClean() {
  if (AppState.isBusy) return;
  if (AppState.selectedCategories.size === 0) return;

  if (AppState.totalScannedBytes === 0 && AppState.totalScannedFiles === 0) {
    addLog("No hay archivos marcados para limpieza.", "warning");
    return;
  }

  setBusyState(true, "Iniciando limpieza segura del equipo...");
  addLog("--- INICIANDO LIMPIEZA DE ARCHIVOS BASURA ---", "info");

  let totalFreed = 0;
  let totalDeleted = 0;
  let totalSkipped = 0;

  const categoriesToClean = AppState.categories.filter(c => AppState.selectedCategories.has(c.key));
  const totalCount = categoriesToClean.length;

  for (let i = 0; i < totalCount; i++) {
    const cat = categoriesToClean[i];
    const pct = Math.round(((i + 1) / totalCount) * 100);

    updateProgress(pct, `Limpiando: ${cat.name}...`);
    addLog(`Limpiando ${cat.name}...`, "dim");

    try {
      const res = await window.pywebview.api.clean_category(
        cat.key,
        parseInt(AppState.config.min_age_hours || 24),
        AppState.config.exclusions || []
      );

      totalFreed += res.freed;
      totalDeleted += res.deleted;
      totalSkipped += res.skipped;

      if (res.freed > 0 || res.deleted > 0) {
        addLog(`✔ ${cat.name}: ${res.freed_formatted} liberados (${res.deleted} eliminados).`, "success");
      }

      // Resetear insignias
      const sizeBadge = document.getElementById(`size-badge-${cat.key}`);
      const filesBadge = document.getElementById(`files-badge-${cat.key}`);
      if (sizeBadge) sizeBadge.textContent = "0 B";
      if (filesBadge) filesBadge.textContent = "0 archivos";

    } catch (err) {
      addLog(`Error limpiando ${cat.name}: ${err}`, "error");
    }
  }

  // Refrescar estadísticas del sistema
  refreshSystemStats();

  // Animación de éxito con GSAP
  if (typeof gsap !== "undefined") {
    gsap.fromTo(".app-container", 
      { boxShadow: "inset 0 0 50px rgba(16, 185, 129, 0.4)" }, 
      { boxShadow: "inset 0 0 0px rgba(16, 185, 129, 0)", duration: 1.5, ease: "power2.out" }
    );
  }

  animateReclaimableCounter(0, 0);
  document.getElementById("btn-main-clean").disabled = true;
  AppState.heavyFiles = [];
  renderHeavyFilesTable();
  renderBreakdownList();

  updateProgress(100, `Limpieza completada: ${formatSize(totalFreed)} liberados`);
  addLog(`✨ Limpieza exitosa: ${formatSize(totalFreed)} liberados en total. ${totalDeleted} eliminados, ${totalSkipped} omitidos por seguridad.`, "success");

  setBusyState(false);
}

async function refreshSystemStats() {
  try {
    const res = await window.pywebview.api.get_system_stats(AppState.selectedDrive);
    AppState.drives = res.drives;
    renderDriveSelector();
    updateSystemGauges(res.stats);
  } catch (err) {
    console.error("Error refrescando stats:", err);
  }
}

// --- Animación de Progreso con GSAP ---

function updateProgress(pct, statusText) {
  const fill = document.getElementById("global-progress");
  const pctText = document.getElementById("progress-percent");
  const status = document.getElementById("progress-status");

  pctText.textContent = `${pct}%`;
  status.textContent = statusText;

  if (typeof gsap !== "undefined") {
    gsap.to(fill, { width: `${pct}%`, duration: 0.3, ease: "power1.out" });
  } else {
    fill.style.width = `${pct}%`;
  }
}

function setBusyState(busy, statusText = "") {
  AppState.isBusy = busy;
  document.getElementById("btn-main-scan").disabled = busy;
  if (busy) {
    document.getElementById("btn-main-clean").disabled = true;
    document.body.style.cursor = "wait";
  } else {
    document.body.style.cursor = "default";
  }
  if (statusText) {
    document.getElementById("progress-status").textContent = statusText;
  }
}

// --- Sistema de Logs ---

function addLog(message, tag = "dim") {
  const terminal = document.getElementById("log-terminal");
  const line = document.createElement("div");
  line.className = `log-line ${tag}`;
  line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  terminal.appendChild(line);

  // Auto-scroll al final
  terminal.scrollTop = terminal.scrollHeight;
}

// --- Event Listeners ---

function setupEventListeners() {
  // Navegación de pestañas
  document.querySelectorAll(".nav-item").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      animateTabTransition(btn.dataset.tab);
    });
  });

  // Selector de disco
  document.getElementById("drive-select").addEventListener("change", (e) => {
    AppState.selectedDrive = e.target.value;
    refreshSystemStats();
  });

  // Botón optimizar RAM
  document.getElementById("btn-optimize-ram").addEventListener("click", async () => {
    addLog("Optimizando memoria RAM del sistema...", "info");
    try {
      const res = await window.pywebview.api.optimize_ram();
      addLog(`Memoria compactada en ${res.freed_processes} procesos del sistema.`, "success");
      updateSystemGauges(res.stats);
    } catch (err) {
      addLog(`Error optimizando RAM: ${err}`, "error");
    }
  });

  // Botón vaciar DNS
  document.getElementById("btn-flush-dns").addEventListener("click", async () => {
    addLog("Vaciando caché DNS de Windows...", "info");
    try {
      const res = await window.pywebview.api.flush_dns();
      if (res.success) {
        addLog(res.message, "success");
      } else {
        addLog(`Aviso DNS: ${res.message}`, "warning");
      }
    } catch (err) {
      addLog(`Error al vaciar DNS: ${err}`, "error");
    }
  });

  // Botón elevar administrador
  document.getElementById("btn-elevate").addEventListener("click", () => {
    if (window.pywebview) {
      window.pywebview.api.request_admin();
    }
  });

  // Seleccionar / Deseleccionar Todos
  document.getElementById("btn-select-all").addEventListener("click", () => {
    AppState.categories.forEach(c => AppState.selectedCategories.add(c.key));
    document.querySelectorAll(".category-card").forEach(c => c.classList.add("selected"));
    document.querySelectorAll(".cat-checkbox").forEach(c => c.checked = true);
    updateCleanBadge();
  });

  document.getElementById("btn-deselect-all").addEventListener("click", () => {
    AppState.selectedCategories.clear();
    document.querySelectorAll(".category-card").forEach(c => c.classList.remove("selected"));
    document.querySelectorAll(".cat-checkbox").forEach(c => c.checked = false);
    updateCleanBadge();
  });

  // Acciones principales
  document.getElementById("btn-main-scan").addEventListener("click", runScan);
  document.getElementById("btn-main-clean").addEventListener("click", runClean);

  // Botones de ajustes
  document.querySelectorAll(".preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const hours = parseInt(btn.dataset.hours);
      document.getElementById("setting-age").value = hours;
      updatePresetButtons(hours);
    });
  });

  document.getElementById("setting-age").addEventListener("input", (e) => {
    updatePresetButtons(e.target.value);
  });

  // Añadir exclusión vía explorador nativo
  document.getElementById("btn-add-exclusion").addEventListener("click", async () => {
    if (window.pywebview) {
      const res = await window.pywebview.api.pick_folder();
      if (res.folder && !AppState.config.exclusions.includes(res.folder)) {
        AppState.config.exclusions.push(res.folder);
        renderExclusionsList();
        addLog(`Carpeta excluida: ${res.folder}`, "info");
      }
    }
  });

  // Guardar configuración
  document.getElementById("btn-save-settings").addEventListener("click", async () => {
    const age = parseInt(document.getElementById("setting-age").value) || 24;
    AppState.config.min_age_hours = age;

    try {
      const res = await window.pywebview.api.save_config(AppState.config);
      const status = document.getElementById("save-status");
      if (res.success) {
        status.textContent = "✔ Configuración guardada";
        addLog("Configuración guardada correctamente.", "success");
      } else {
        status.textContent = "⚠️ Error al guardar";
      }
      setTimeout(() => { status.textContent = ""; }, 3000);
    } catch (err) {
      addLog(`Error guardando configuración: ${err}`, "error");
    }
  });

  // Toggle drawer de logs
  const logToggle = document.getElementById("log-drawer-toggle");
  const logTerminal = document.getElementById("log-terminal");
  const logArrow = document.querySelector(".toggle-icon");
  logToggle.addEventListener("click", (e) => {
    if (e.target.id === "btn-clear-log") return;
    AppState.logOpen = !AppState.logOpen;
    if (AppState.logOpen) {
      logTerminal.style.display = "block";
      logArrow.textContent = "▲";
    } else {
      logTerminal.style.display = "none";
      logArrow.textContent = "▼";
    }
  });

  document.getElementById("btn-clear-log").addEventListener("click", () => {
    document.getElementById("log-terminal").innerHTML = "";
  });

  // Refrescar programas de inicio
  document.getElementById("btn-refresh-startup").addEventListener("click", loadStartupPrograms);

  // Exportar Reporte
  document.getElementById("btn-export-report").addEventListener("click", async () => {
    if (!window.pywebview) {
      addLog("Exportación disponible al ejecutar la app en Windows.", "info");
      return;
    }
    const reportData = {
      timestamp: new Date().toISOString(),
      drive: AppState.selectedDrive,
      scanned_bytes: AppState.totalScannedBytes,
      scanned_files: AppState.totalScannedFiles,
      categories: AppState.scannedResults
    };
    addLog("Generando y exportando reporte estructurado...", "info");
    try {
      const res = await window.pywebview.api.export_report(reportData, "json");
      if (res.success) {
        addLog(res.message, "success");
      } else {
        addLog(`Error al exportar: ${res.message}`, "error");
      }
    } catch (err) {
      addLog(`Error en exportación: ${err}`, "error");
    }
  });

  // --- Herramienta 1: Triturador de Archivos ---
  const shredInput = document.getElementById("shred-file-path");
  const btnRunShred = document.getElementById("btn-run-shred");
  const shredStatus = document.getElementById("shred-status");

  document.getElementById("btn-browse-shred").addEventListener("click", async () => {
    if (window.pywebview) {
      const res = await window.pywebview.api.pick_file();
      if (res.file) {
        shredInput.value = res.file;
        btnRunShred.disabled = false;
        shredStatus.textContent = `Archivo seleccionado listo para destrucción: ${res.file}`;
        shredStatus.style.color = "var(--text-main)";
      }
    }
  });

  btnRunShred.addEventListener("click", async () => {
    const filePath = shredInput.value.trim();
    if (!filePath) return;
    const passes = parseInt(document.getElementById("shred-passes").value) || 1;

    if (!confirm(`⚠️ ATENCIÓN: Se triturará y eliminará de forma irreversible el archivo:\n\n${filePath}\n\n¿Deseas continuar?`)) {
      return;
    }

    shredStatus.textContent = `Triturando archivo (${passes} pasadas)...`;
    btnRunShred.disabled = true;
    addLog(`Iniciando triturado seguro de: ${filePath}`, "warning");

    try {
      const res = await window.pywebview.api.shred_file(filePath, passes);
      if (res.success) {
        shredStatus.textContent = `✔ ${res.message}`;
        shredStatus.style.color = "var(--success)";
        shredInput.value = "";
        addLog(res.message, "success");
      } else {
        shredStatus.textContent = `❌ ${res.message}`;
        shredStatus.style.color = "var(--danger)";
        addLog(res.message, "error");
        btnRunShred.disabled = false;
      }
    } catch (err) {
      shredStatus.textContent = `Error: ${err}`;
      shredStatus.style.color = "var(--danger)";
      addLog(`Fallo al triturar: ${err}`, "error");
      btnRunShred.disabled = false;
    }
  });

  // --- Herramienta 2: Buscador de Duplicados ---
  const dupInput = document.getElementById("dup-folder-path");
  const btnRunDup = document.getElementById("btn-run-dup");
  const dupStatus = document.getElementById("dup-status");
  const dupResults = document.getElementById("dup-results");

  document.getElementById("btn-browse-dup").addEventListener("click", async () => {
    if (window.pywebview) {
      const res = await window.pywebview.api.pick_folder();
      if (res.folder) {
        dupInput.value = res.folder;
        btnRunDup.disabled = false;
        dupStatus.textContent = `Carpeta seleccionada: ${res.folder}`;
      }
    }
  });

  btnRunDup.addEventListener("click", async () => {
    const folderPath = dupInput.value.trim();
    if (!folderPath) return;

    dupStatus.textContent = "Analizando archivos y calculando firmas SHA-256...";
    btnRunDup.disabled = true;
    dupResults.style.display = "none";
    dupResults.innerHTML = "";
    addLog(`Auditando duplicados en: ${folderPath}`, "info");

    try {
      const res = await window.pywebview.api.find_duplicates(folderPath, 1);
      btnRunDup.disabled = false;
      const dups = res.duplicates || [];

      if (dups.length === 0) {
        dupStatus.textContent = "✔ No se encontraron archivos duplicados en la carpeta.";
        addLog("Auditoría de duplicados: 0 duplicados encontrados.", "success");
      } else {
        const totalWasted = dups.reduce((acc, d) => acc + (d.wasted_bytes || 0), 0);
        dupStatus.textContent = `✔ Se encontraron ${dups.length} grupos de duplicados (${formatSize(totalWasted)} desperdiciados).`;
        addLog(`Duplicados encontrados: ${dups.length} grupos (${formatSize(totalWasted)} desperdiciados).`, "warning");

        dupResults.style.display = "flex";
        dups.forEach(g => {
          const item = document.createElement("div");
          item.className = "dup-item";
          item.innerHTML = `
            <div class="dup-header">
              <span>Tamaño c/u: ${g.size_formatted}</span>
              <span style="color: var(--warning);">Desperdicio: ${g.wasted_formatted}</span>
            </div>
            <div class="dup-files-list">
              ${g.files.map(f => `<div>• ${escapeHtml(f)}</div>`).join("")}
            </div>
          `;
          dupResults.appendChild(item);
        });
      }
    } catch (err) {
      btnRunDup.disabled = false;
      dupStatus.textContent = `Error auditando duplicados: ${err}`;
      addLog(`Fallo al buscar duplicados: ${err}`, "error");
    }
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Mock para entorno navegador sin Python
function initMockApp() {
  applyInitialState({
    is_admin: false,
    drives: [
      { letter: "C:\\", type: "Fijo", total: 256 * 1024 ** 3, used: 180 * 1024 ** 3, free: 76 * 1024 ** 3, percent: 70.3 }
    ],
    stats: { disk_total: 256 * 1024 ** 3, disk_used: 180 * 1024 ** 3, disk_free: 76 * 1024 ** 3, disk_percent: 70.3, ram_load: 62, ram_used: 9.8 * 1024 ** 3, ram_total: 16 * 1024 ** 3 },
    config: { min_age_hours: 24, exclusions: ["C:\\Users\\Mock\\Important"] },
    categories: [
      { key: "user_temp", name: "Temporales de Usuario", desc: "Archivos residuales en %TEMP%", requires_admin: false },
      { key: "system_temp", name: "Temporales de Windows", desc: "Archivos temporales del sistema", requires_admin: true },
      { key: "recycle_bin", name: "Papelera de Reciclaje", desc: "Archivos en la papelera", requires_admin: false },
      { key: "browser_chrome", name: "Caché de Google Chrome", desc: "Caché y multimedia de Chrome", requires_admin: false }
    ]
  });
  setupEventListeners();
  runIntroAnimations();
}
