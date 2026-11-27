/**
 * PyClean Pro v2.4 - Lógica Frontend para Módulos Avanzados:
 * 1. Monitor de Procesos y Red (CPU/RAM, DNS Presets, Ping)
 * 2. Salud de Hardware (S.M.A.R.T., TRIM SSD y Batería)
 * 3. Gestor del Menú Contextual (Clic Derecho reversible)
 * 4. Bóveda Local de Contraseñas (AES-256-GCM Offline)
 */

const V24State = {
  contextMenuItems: [],
  vaultEntries: [],
  vaultExists: false,
  listenersBound: false,
};

function v24Escape(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function v24Log(msg, tag = "info") {
  if (typeof addLog === "function") {
    addLog(msg, tag);
  }
}

// =========================================================================
// 1. MONITOR DE PROCESOS Y RED
// =========================================================================

async function loadMonitorView() {
  await Promise.all([loadTopProcesses(), loadNetworkAdapters()]);
}

async function loadTopProcesses() {
  const tbody = document.getElementById("monitor-processes-tbody");
  const sortSel = document.getElementById("monitor-sort-select");
  if (!tbody) return;

  const sortBy = sortSel ? sortSel.value : "memory";
  tbody.innerHTML = `<tr><td colspan="5" class="table-loading">Leyendo procesos activos...</td></tr>`;

  try {
    let procs = [];
    if (window.pywebview) {
      procs = await window.pywebview.api.get_top_processes(sortBy, 35);
    }
    tbody.innerHTML = "";

    if (!procs || procs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="table-loading">No se pudieron leer los procesos activos.</td></tr>`;
      return;
    }

    procs.forEach(p => {
      const tr = document.createElement("tr");
      const badge = p.is_critical
        ? `<span class="badge badge-dim" style="margin-left:6px;">SO</span>`
        : "";

      tr.innerHTML = `
        <td style="font-weight: 500;">${v24Escape(p.name)}${badge}</td>
        <td style="font-family: Consolas, monospace; color: var(--text-muted);">${p.pid}</td>
        <td><strong style="color: var(--accent-cyan);">${v24Escape(p.memory_formatted)}</strong></td>
        <td>${p.cpu_percent}%</td>
        <td style="text-align: right;">
          ${
            p.is_critical
              ? `<span style="font-size:11px; color: var(--text-dim);">Protegido</span>`
              : `<button class="btn-tool btn-kill-proc" style="padding:3px 9px; font-size:11px; color: var(--danger); border-color: rgba(239,68,68,0.35);">Finalizar</button>`
          }
        </td>
      `;

      const btnKill = tr.querySelector(".btn-kill-proc");
      if (btnKill) {
        btnKill.addEventListener("click", async () => {
          if (!confirm(`¿Finalizar el proceso '${p.name}' (PID ${p.pid})?`)) return;
          try {
            const res = await window.pywebview.api.terminate_process(p.pid);
            if (res.success) {
              v24Log(res.message, "success");
              tr.remove();
            } else {
              v24Log(res.message, "warning");
            }
          } catch (err) {
            v24Log(`Error finalizando proceso: ${err}`, "error");
          }
        });
      }

      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="table-loading" style="color: var(--danger);">Error: ${v24Escape(err)}</td></tr>`;
  }
}

async function loadNetworkAdapters() {
  const sel = document.getElementById("dns-adapter-select");
  if (!sel) return;

  try {
    let ifaces = [];
    if (window.pywebview) {
      ifaces = await window.pywebview.api.get_network_interfaces();
    }
    sel.innerHTML = "";
    if (!ifaces || ifaces.length === 0) {
      sel.innerHTML = `<option value="">Sin adaptadores activos detectados</option>`;
      return;
    }
    ifaces.forEach(net => {
      const opt = document.createElement("option");
      opt.value = net.name;
      opt.textContent = `${net.name} — ${net.ip} (↓ ${net.recv_formatted} / ↑ ${net.sent_formatted})`;
      sel.appendChild(opt);
    });
  } catch (err) {
    sel.innerHTML = `<option value="">Error leyendo adaptadores</option>`;
  }
}

async function runPingTestUI() {
  const list = document.getElementById("ping-results-list");
  const btn = document.getElementById("btn-run-ping");
  if (!list) return;

  if (btn) btn.disabled = true;
  list.innerHTML = `<div class="table-loading">Midiendo latencia a servidores globales...</div>`;
  v24Log("Ejecutando prueba de latencia (ping)...", "info");

  try {
    let results = [];
    if (window.pywebview) {
      results = await window.pywebview.api.run_ping_test();
    }
    list.innerHTML = "";
    results.forEach(r => {
      const row = document.createElement("div");
      row.className = "ping-row";
      let color = "var(--success)";
      if (!r.reachable) color = "var(--danger)";
      else if (r.latency_ms > 120) color = "var(--warning)";

      const valText = r.reachable ? `${r.latency_ms} ms` : "Sin respuesta";
      row.innerHTML = `
        <div><strong>${v24Escape(r.label)}</strong> <span style="color:var(--text-dim); font-size:11px;">(${v24Escape(r.host)})</span></div>
        <span style="font-weight: 700; color: ${color};">${valText}</span>
      `;
      list.appendChild(row);
    });
    v24Log("Prueba de latencia completada.", "success");
  } catch (err) {
    list.innerHTML = `<div class="empty-state" style="color: var(--danger);">Error en ping: ${v24Escape(err)}</div>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

// =========================================================================
// 2. SALUD DE HARDWARE (SSD S.M.A.R.T., TRIM Y BATERÍA)
// =========================================================================

async function loadHardwareView() {
  populateTrimDriveSelector();
  await Promise.all([loadDiskHealthUI(), loadBatteryHealthUI()]);
}

function populateTrimDriveSelector() {
  const sel = document.getElementById("trim-drive-select");
  if (!sel || typeof AppState === "undefined" || !AppState.drives) return;
  const current = sel.value || "C";
  sel.innerHTML = "";
  AppState.drives.forEach(d => {
    const letter = String(d.letter || "C").replace(/[:\\\/]+/g, "").toUpperCase();
    if (/^[A-Z]$/.test(letter)) {
      const opt = document.createElement("option");
      opt.value = letter;
      opt.textContent = `${letter}:\\`;
      if (letter === current) opt.selected = true;
      sel.appendChild(opt);
    }
  });
  if (sel.options.length === 0) {
    sel.innerHTML = `<option value="C">C:\\</option>`;
  }
}

async function loadDiskHealthUI() {
  const grid = document.getElementById("hardware-disks-grid");
  if (!grid) return;
  grid.innerHTML = `<div class="table-loading">Consultando sensores S.M.A.R.T....</div>`;

  try {
    let disks = [];
    if (window.pywebview) {
      disks = await window.pywebview.api.get_disk_health();
    }
    grid.innerHTML = "";
    if (!disks || disks.length === 0) {
      grid.innerHTML = `<div class="empty-state">No se detectaron discos físicos.</div>`;
      return;
    }

    disks.forEach(d => {
      const healthy = (d.health_status || "").toLowerCase() === "healthy";
      const badgeColor = healthy ? "var(--success)" : "var(--warning)";
      const card = document.createElement("div");
      card.className = "partition-card";
      card.style.cursor = "default";
      card.innerHTML = `
        <div class="partition-top">
          <div class="partition-drive"><span>💾 ${v24Escape(d.name)}</span></div>
          <span class="partition-fs" style="color:${badgeColor}; background: rgba(16,185,129,0.12);">${v24Escape(d.health_status)}</span>
        </div>
        <div class="partition-label">Tipo: <strong>${v24Escape(d.media_type)}</strong> ${d.bus_type ? `• Bus: ${v24Escape(d.bus_type)}` : ""}</div>
        <div class="partition-meta">
          <span>Estado: ${v24Escape(d.operational_status)}</span>
          <span>Capacidad: <strong>${v24Escape(d.size_formatted)}</strong></span>
        </div>
      `;
      grid.appendChild(card);
    });
  } catch (err) {
    grid.innerHTML = `<div class="empty-state" style="color: var(--danger);">Error consultando discos: ${v24Escape(err)}</div>`;
  }
}

function renderBatteryCalibrationBanner(calibState) {
  const banner = document.getElementById("battery-calibration-banner");
  const btnStart = document.getElementById("btn-batt-calib-start");
  const btnFinish = document.getElementById("btn-batt-calib-finish");
  if (!banner) return;

  if (calibState && calibState.active) {
    const baseMwh = calibState.baseline_full_charge_mwh || 0;
    const baseHealth = calibState.baseline_health_percent !== null && calibState.baseline_health_percent !== undefined
      ? `${calibState.baseline_health_percent}%`
      : "N/A";
    const stepsHtml = (calibState.steps || [])
      .map(s => `<li>${v24Escape(s.replace(/^\d+\.\s*/, ""))}</li>`)
      .join("");

    banner.innerHTML = `
      <div><strong>🎯 Sesión de calibración activa</strong> (Base inicial: <strong>${baseMwh} mWh</strong> • Salud: <strong>${baseHealth}</strong>)</div>
      <ol>${stepsHtml}</ol>
    `;
    banner.style.display = "block";
    if (btnStart) btnStart.style.display = "none";
    if (btnFinish) btnFinish.style.display = "inline-block";
  } else {
    banner.style.display = "none";
    banner.innerHTML = "";
    if (btnStart) btnStart.style.display = "inline-block";
    if (btnFinish) btnFinish.style.display = "none";
  }
}

function renderBatteryAuditResults(audit) {
  const container = document.getElementById("battery-audit-results");
  if (!container) return;

  const findings = audit.findings || [];
  const topProcs = audit.top_processes || [];

  let findingsHtml = "";
  if (audit.success && findings.length === 0) {
    findingsHtml = `<div style="color: var(--success); margin-top: 6px;">✅ No se detectaron errores ni advertencias críticas de eficiencia energética.</div>`;
  } else if (findings.length > 0) {
    findingsHtml = findings.map(f => `
      <div class="battery-finding-item ${f.severity === "error" ? "sev-error" : ""}">
        <div style="font-weight: 600; color: var(--text-main);">
          ${f.severity === "error" ? "🔴" : "🟡"} ${v24Escape(f.name)}
        </div>
        ${f.description ? `<div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">${v24Escape(f.description)}</div>` : ""}
      </div>
    `).join("");
  } else {
    findingsHtml = `<div style="color: var(--warning); margin-top: 6px;">${v24Escape(audit.message || "Sin datos del reporte de energía.")}</div>`;
  }

  let procsHtml = "";
  if (topProcs.length > 0) {
    procsHtml = topProcs.map(p => `
      <div class="ping-row" style="margin-top: 6px; padding: 6px 10px; font-size: 12px;">
        <span><strong>${v24Escape(p.name)}</strong> <span style="color: var(--text-dim);">(PID ${p.pid})</span></span>
        <span>CPU: <strong style="color: var(--warning);">${p.cpu_percent}%</strong> • RAM: ${v24Escape(p.memory_formatted)}</span>
      </div>
    `).join("");
  } else {
    procsHtml = `<div style="color: var(--text-muted); margin-top: 6px;">Sin procesos con consumo elevado detectado en este instante.</div>`;
  }

  container.innerHTML = `
    <div class="battery-audit-grid">
      <div class="battery-audit-panel">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong>📋 Auditoría de Energía de Windows</strong>
          <span style="font-size: 11px; color: var(--text-muted);">
            Errores: <strong style="color:var(--danger);">${audit.errors_count || 0}</strong> • Advertencias: <strong style="color:var(--warning);">${audit.warnings_count || 0}</strong>
          </span>
        </div>
        <div style="max-height: 220px; overflow-y: auto; margin-top: 4px;">${findingsHtml}</div>
      </div>
      <div class="battery-audit-panel">
        <strong>🔥 Procesos con Mayor Impacto Actual</strong>
        <div style="max-height: 220px; overflow-y: auto; margin-top: 4px;">${procsHtml}</div>
      </div>
    </div>
  `;
  container.style.display = "block";
}

function setBatteryActionStatus(msg, level = "info") {
  const box = document.getElementById("battery-action-status");
  if (!box) return;
  box.textContent = msg;
  if (level === "success") box.style.color = "var(--success)";
  else if (level === "error") box.style.color = "var(--danger)";
  else if (level === "warning") box.style.color = "var(--warning)";
  else box.style.color = "var(--text-main)";
}

async function loadBatteryHealthUI() {
  const panel = document.getElementById("battery-health-panel");
  const toolsSec = document.getElementById("battery-tools-section");
  const btnRestore = document.getElementById("btn-batt-restore-backup");
  if (!panel) return;

  try {
    let batt = { has_battery: false };
    if (window.pywebview) {
      batt = await window.pywebview.api.get_battery_health();
    }

    if (!batt || !batt.has_battery) {
      panel.innerHTML = `<div class="tool-status-box">🖥️ Equipo de escritorio detectado (no cuenta con batería interna).</div>`;
      if (toolsSec) toolsSec.style.display = "none";
      return;
    }

    if (toolsSec) toolsSec.style.display = "block";
    if (btnRestore) btnRestore.style.display = batt.has_power_backup ? "inline-block" : "none";
    renderBatteryCalibrationBanner(batt.calibration_state);

    const healthPct = batt.health_percent !== null && batt.health_percent !== undefined ? batt.health_percent : null;
    const healthColor = healthPct === null ? "var(--primary)" : healthPct >= 80 ? "var(--success)" : healthPct >= 60 ? "var(--warning)" : "var(--danger)";
    const cycleLabel = batt.cycle_count_reported
      ? `Ciclos de carga: ${batt.cycle_count}`
      : "Ciclos: No reportado por BIOS";
    const chemInfo = [batt.chemistry, batt.manufacturer].filter(Boolean).join(" • ");

    let telemetryVal = batt.active_power_plan && batt.active_power_plan.name
      ? batt.active_power_plan.name
      : "Estándar";
    let telemetrySubParts = [];
    if (batt.power_draw_watts) {
      telemetrySubParts.push(`${batt.power_plugged ? "Carga" : "Consumo"}: ${batt.power_draw_watts} W`);
    }
    if (batt.voltage_mv) {
      telemetrySubParts.push(`${(batt.voltage_mv / 1000).toFixed(2)} V`);
    }
    const telemetrySub = telemetrySubParts.length > 0 ? telemetrySubParts.join(" • ") : (chemInfo || "Sensor ACPI activo");

    const diag = batt.diagnosis || {};
    const diagLevel = diag.level || "unknown";
    const recsHtml = (diag.recommendations || []).length > 0
      ? `<ul class="battery-diagnosis-recs">${diag.recommendations.map(r => `<li>${v24Escape(r)}</li>`).join("")}</ul>`
      : "";

    let historyHtml = "";
    if (Array.isArray(batt.capacity_history) && batt.capacity_history.length >= 2) {
      const items = batt.capacity_history.slice(-6).map(h => `
        <div class="battery-history-item">
          <span style="color: var(--text-dim);">${v24Escape(h.date)}</span>
          <strong style="color: var(--text-main);">${h.health_percent}%</strong>
          <span style="color: var(--text-muted);">${h.full_charge_mwh} mWh</span>
        </div>
      `).join("");
      historyHtml = `
        <div class="battery-history-strip">
          <div style="font-size: 11px; font-weight: 600; color: var(--text-dim); text-transform: uppercase;">📈 Historial Reciente de Capacidad Real</div>
          <div class="battery-history-list">${items}</div>
        </div>
      `;
    }

    panel.innerHTML = `
      <div class="battery-stats-grid">
        <div class="battery-stat-box">
          <span class="battery-stat-label">Carga Actual</span>
          <strong class="battery-stat-value">${batt.percent ?? 0}%</strong>
          <span class="battery-stat-sub">${batt.power_plugged ? "⚡ Conectado a corriente" : `🔋 En batería • ${v24Escape(batt.time_remaining_formatted || "Calculando...")}`}</span>
        </div>
        <div class="battery-stat-box">
          <span class="battery-stat-label">Salud Real</span>
          <strong class="battery-stat-value" style="color:${healthColor};">${healthPct !== null ? healthPct + "%" : "N/A"}</strong>
          <span class="battery-stat-sub">${batt.wear_percent !== null && batt.wear_percent !== undefined ? `Desgaste: ${batt.wear_percent}%` : "Sin reporte XML"}</span>
          ${healthPct !== null ? `<div class="battery-health-bar"><div class="battery-health-bar-fill" style="width:${Math.max(4, Math.min(100, healthPct))}%; background:${healthColor};"></div></div>` : ""}
        </div>
        <div class="battery-stat-box">
          <span class="battery-stat-label">Capacidad (Actual / Diseño)</span>
          <strong class="battery-stat-value" style="font-size: 16px;">${batt.full_charge_capacity_mwh || 0} / ${batt.design_capacity_mwh || 0} mWh</strong>
          <span class="battery-stat-sub">${v24Escape(cycleLabel)}${chemInfo ? ` • ${v24Escape(chemInfo)}` : ""}</span>
        </div>
        <div class="battery-stat-box">
          <span class="battery-stat-label">Plan Activo &amp; Telemetría</span>
          <strong class="battery-stat-value" style="font-size: 15px;">${v24Escape(telemetryVal)}</strong>
          <span class="battery-stat-sub">${v24Escape(telemetrySub)}</span>
        </div>
      </div>

      ${diag.title ? `
        <div class="battery-diagnosis-box diag-${v24Escape(diagLevel)}">
          <div class="battery-diagnosis-title">🩺 Diagnóstico: ${v24Escape(diag.title)}</div>
          <div style="color: var(--text-main);">${v24Escape(diag.summary || "")}</div>
          ${recsHtml}
        </div>
      ` : ""}

      ${historyHtml}
    `;
  } catch (err) {
    panel.innerHTML = `<div class="tool-status-box" style="color: var(--danger);">Error analizando batería: ${v24Escape(err)}</div>`;
  }
}

// =========================================================================
// 3. GESTOR DEL MENÚ CONTEXTUAL (CLIC DERECHO)
// =========================================================================

async function loadContextMenuView() {
  const tbody = document.getElementById("context-menu-tbody");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="5" class="table-loading">Escaneando claves del menú contextual...</td></tr>`;

  try {
    let items = [];
    if (window.pywebview) {
      items = await window.pywebview.api.get_context_menu_items();
    }
    V24State.contextMenuItems = items || [];
    renderContextMenuTable(V24State.contextMenuItems);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="table-loading" style="color: var(--danger);">Error: ${v24Escape(err)}</td></tr>`;
  }
}

function renderContextMenuTable(items) {
  const tbody = document.getElementById("context-menu-tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!items || items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="table-loading">No se encontraron entradas editables del menú contextual.</td></tr>`;
    return;
  }

  items.forEach(item => {
    const tr = document.createElement("tr");
    const statusHtml = item.enabled
      ? `<span class="badge badge-success">Activo</span>`
      : `<span class="badge badge-dim">Oculto</span>`;

    tr.innerHTML = `
      <td>${statusHtml}</td>
      <td style="font-weight: 500;">${v24Escape(item.label)}</td>
      <td><span class="badge badge-primary">${v24Escape(item.scope)}</span></td>
      <td style="font-family: Consolas, monospace; font-size: 11px; color: var(--text-muted); max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${v24Escape(item.command)}">
        ${v24Escape(item.command || item.subkey)}
      </td>
      <td style="text-align: right;">
        ${
          item.is_protected
            ? `<span style="font-size:11px; color: var(--text-dim);">Nativo Windows</span>`
            : `<button class="btn-tool btn-toggle-cm" style="padding:3px 10px; font-size:11px;">${item.enabled ? "Desactivar" : "Reactivar"}</button>`
        }
      </td>
    `;

    const btn = tr.querySelector(".btn-toggle-cm");
    if (btn) {
      btn.addEventListener("click", async () => {
        const nextState = !item.enabled;
        try {
          const res = await window.pywebview.api.toggle_context_menu_item(item.hive, item.subkey, nextState);
          if (res.success) {
            v24Log(res.message, "success");
            loadContextMenuView();
          } else {
            v24Log(res.message, "warning");
          }
        } catch (err) {
          v24Log(`Error modificando menú contextual: ${err}`, "error");
        }
      });
    }

    tbody.appendChild(tr);
  });
}

// =========================================================================
// 4. BÓVEDA LOCAL DE CONTRASEÑAS (AES-256-GCM OFFLINE)
// =========================================================================

async function loadVaultView() {
  try {
    let st = { crypto_available: true, exists: false, unlocked: false };
    if (window.pywebview) {
      st = await window.pywebview.api.vault_status();
    }
    applyVaultStatus(st);
  } catch (err) {
    v24Log(`Error consultando estado de bóveda: ${err}`, "error");
  }
}

function setVaultAuthStatus(message, type = "") {
  const authStatus = document.getElementById("vault-auth-status");
  if (!authStatus) return;
  authStatus.textContent = message;
  authStatus.classList.remove("error", "success");
  if (type) authStatus.classList.add(type);
}

function applyVaultStatus(st) {
  V24State.vaultExists = Boolean(st && st.exists);
  const lockScreen = document.getElementById("vault-lock-screen");
  const mainPanel = document.getElementById("vault-main-panel");
  const unlockedTools = document.getElementById("vault-unlocked-tools");
  const lockTitle = document.getElementById("vault-lock-title");
  const lockDesc = document.getElementById("vault-lock-desc");
  const confirmField = document.getElementById("vault-confirm-field");
  const masterMeter = document.getElementById("vault-master-meter");
  const submitBtn = document.getElementById("btn-vault-submit");

  if (!lockScreen || !mainPanel) return;

  if (st && st.unlocked) {
    lockScreen.style.display = "none";
    mainPanel.style.display = "block";
    if (unlockedTools) unlockedTools.style.display = "flex";
    refreshVaultEntries();
  } else {
    lockScreen.style.display = "flex";
    mainPanel.style.display = "none";
    if (unlockedTools) unlockedTools.style.display = "none";

    if (V24State.vaultExists) {
      if (lockTitle) lockTitle.textContent = "Desbloquear Bóveda";
      if (lockDesc) lockDesc.textContent = "Introduce tu contraseña maestra para descifrar tus credenciales en memoria.";
      if (confirmField) confirmField.style.display = "none";
      if (masterMeter) masterMeter.style.display = "none";
      if (submitBtn) submitBtn.textContent = "Desbloquear Bóveda";
      setVaultAuthStatus("Bóveda cifrada lista para desbloquear.");
    } else {
      if (lockTitle) lockTitle.textContent = "Crear Nueva Bóveda Cifrada";
      if (lockDesc) lockDesc.textContent = "Elige una contraseña maestra fuerte (mín. 8 caracteres). Nunca se guarda en disco y no se puede recuperar si la olvidas.";
      if (confirmField) confirmField.style.display = "flex";
      if (masterMeter) masterMeter.style.display = "flex";
      if (submitBtn) submitBtn.textContent = "Crear Bóveda Cifrada";
      setVaultAuthStatus("Aún no existe una bóveda en este equipo.");
    }
  }
}

async function refreshVaultEntries() {
  const tbody = document.getElementById("vault-entries-tbody");
  if (!tbody) return;

  try {
    const res = await window.pywebview.api.vault_get_entries();
    if (!res.unlocked) {
      loadVaultView();
      return;
    }
    V24State.vaultEntries = res.entries || [];
    updateVaultKpisAndFilters(V24State.vaultEntries);
    applyVaultSearchAndFilter();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" class="table-loading" style="color:var(--danger);">Error: ${v24Escape(err)}</td></tr>`;
  }
}

function updateVaultKpisAndFilters(entries) {
  const totalEl = document.getElementById("vault-kpi-total");
  const catsEl = document.getElementById("vault-kpi-categories");
  const pillsWrap = document.getElementById("vault-filter-pills");

  const categories = [...new Set((entries || []).map(e => e.category || "General"))].sort();
  if (totalEl) totalEl.textContent = String((entries || []).length);
  if (catsEl) catsEl.textContent = String(categories.length);

  if (!pillsWrap) return;
  if (!V24State.vaultActiveCategory) V24State.vaultActiveCategory = "Todas";
  if (V24State.vaultActiveCategory !== "Todas" && !categories.includes(V24State.vaultActiveCategory)) {
    V24State.vaultActiveCategory = "Todas";
  }

  const allCats = ["Todas", ...categories];
  pillsWrap.innerHTML = "";
  allCats.forEach(cat => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `vault-filter-pill${V24State.vaultActiveCategory === cat ? " active" : ""}`;
    btn.textContent = cat;
    btn.addEventListener("click", () => {
      V24State.vaultActiveCategory = cat;
      updateVaultKpisAndFilters(V24State.vaultEntries);
      applyVaultSearchAndFilter();
    });
    pillsWrap.appendChild(btn);
  });
}

function applyVaultSearchAndFilter() {
  const searchEl = document.getElementById("vault-search");
  const q = searchEl ? searchEl.value.trim().toLowerCase() : "";
  const activeCat = V24State.vaultActiveCategory || "Todas";

  const filtered = (V24State.vaultEntries || []).filter(en => {
    const matchesCat = activeCat === "Todas" || (en.category || "General") === activeCat;
    const matchesQuery =
      !q ||
      (en.title && en.title.toLowerCase().includes(q)) ||
      (en.username && en.username.toLowerCase().includes(q)) ||
      (en.category && en.category.toLowerCase().includes(q)) ||
      (en.url && en.url.toLowerCase().includes(q));
    return matchesCat && matchesQuery;
  });

  renderVaultEntries(filtered);
}

function renderVaultEntries(entries) {
  const tbody = document.getElementById("vault-entries-tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!entries || entries.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="table-loading">No hay credenciales que coincidan. Agrega una nueva arriba.</td></tr>`;
    return;
  }

  entries.forEach(entry => {
    const initials = (entry.title || "??").trim().slice(0, 2).toUpperCase();
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <div class="vault-service-cell">
          <div class="vault-avatar">${v24Escape(initials)}</div>
          <div>
            <div class="vault-service-title">${v24Escape(entry.title)}</div>
            ${entry.url ? `<div class="vault-service-url">${v24Escape(entry.url)}</div>` : ""}
          </div>
        </div>
      </td>
      <td><span class="vault-user-chip">${v24Escape(entry.username || "—")}</span></td>
      <td><span class="badge badge-primary">${v24Escape(entry.category || "General")}</span></td>
      <td style="text-align: right; white-space: nowrap;">
        <button class="btn-tool btn-vault-copy" style="padding:5px 10px; font-size:11.5px; margin-right:5px;">📋 Copiar Clave</button>
        <button class="btn-tool btn-vault-qr" style="padding:5px 10px; font-size:11.5px; margin-right:5px;">📱 QR</button>
        <button class="btn-tool btn-vault-edit" style="padding:5px 10px; font-size:11.5px; margin-right:5px;">✏️ Editar</button>
        <button class="btn-tool btn-vault-del vault-btn-del" style="padding:5px 9px; font-size:11.5px;">🗑️</button>
      </td>
    `;

    const copyBtn = tr.querySelector(".btn-vault-copy");
    copyBtn.addEventListener("click", async () => {
      try {
        await window.pywebview.api.vault_copy_secret(entry.password, 30);
        const origText = copyBtn.textContent;
        copyBtn.textContent = "✓ Copiado (30s)";
        setTimeout(() => { copyBtn.textContent = origText; }, 2200);
        v24Log(`Contraseña de '${entry.title}' copiada (se limpiará en 30s).`, "success");
      } catch (e) {
        v24Log(`Error copiando contraseña: ${e}`, "error");
      }
    });

    const qrBtn = tr.querySelector(".btn-vault-qr");
    if (qrBtn) {
      qrBtn.addEventListener("click", () => {
        openVaultQrModal(entry.id);
      });
    }

    tr.querySelector(".btn-vault-edit").addEventListener("click", () => {
      document.getElementById("vault-entry-id").value = entry.id;
      document.getElementById("vault-title").value = entry.title || "";
      document.getElementById("vault-category").value = entry.category || "General";
      document.getElementById("vault-username").value = entry.username || "";
      document.getElementById("vault-url").value = entry.url || "";
      document.getElementById("vault-password").value = entry.password || "";
      document.getElementById("vault-notes").value = entry.notes || "";
      document.getElementById("vault-form-title").textContent = `Editando: ${entry.title}`;
      updatePasswordStrengthUI(entry.password || "");
    });

    tr.querySelector(".btn-vault-del").addEventListener("click", async () => {
      const ok = await window.showConfirmModal({
        title: "Eliminar credencial",
        message: `¿Eliminar definitivamente la credencial '${entry.title}' de tu bóveda cifrada?`,
        confirmText: "Eliminar",
        danger: true,
      });
      if (!ok) return;
      const res = await window.pywebview.api.vault_delete_entry(entry.id);
      if (res.success) {
        v24Log(res.message, "success");
        refreshVaultEntries();
      } else {
        v24Log(res.message, "error");
      }
    });

    tbody.appendChild(tr);
  });
}

async function updatePasswordStrengthUI(pwd, fillId = "vault-strength-fill", labelId = "vault-strength-label") {
  const fill = document.getElementById(fillId);
  const label = document.getElementById(labelId);
  if (!fill || !label) return;

  if (!pwd) {
    fill.style.width = "0%";
    label.textContent = fillId.includes("master") ? "Seguridad: —" : "Fortaleza: —";
    label.style.color = "var(--text-muted)";
    return;
  }

  try {
    const info = await window.pywebview.api.vault_evaluate_strength(pwd);
    const pct = Math.min(100, (info.score || 0) * 25);
    fill.style.width = `${pct}%`;
    fill.style.background = info.color || "var(--primary)";
    label.textContent = `${info.label} (${info.entropy_bits} bits)`;
    label.style.color = info.color || "var(--text-muted)";
  } catch (e) {
    // fallback silencioso
  }
}

function clearVaultForm() {
  const ids = ["vault-entry-id", "vault-title", "vault-username", "vault-url", "vault-password", "vault-notes"];
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  const cat = document.getElementById("vault-category");
  if (cat) cat.value = "General";
  const title = document.getElementById("vault-form-title");
  if (title) title.textContent = "Agregar Credencial";
  updatePasswordStrengthUI("");
}

// =========================================================================
// GESTIÓN DE MODALES QR Y SINCRONIZACIÓN MÓVIL (Milestone 2)
// =========================================================================

let vaultCurrentQrEntryId = null;
let vaultQrCountdownTimer = null;
let vaultCurrentQrPayload = "";
let vaultSyncInterval = null;

async function openVaultQrModal(entryId, usePin = false) {
  const modal = document.getElementById("vault-qr-modal");
  const container = document.getElementById("vault-qr-canvas-container");
  const timerEl = document.getElementById("vault-qr-timer");
  const titleEl = document.getElementById("vault-qr-service-title");
  const userEl = document.getElementById("vault-qr-username");
  const pinToggle = document.getElementById("vault-qr-pin-toggle");
  const pinContainer = document.getElementById("vault-qr-pin-container");
  const pinBadge = document.getElementById("vault-qr-pin-badge");

  if (!modal || !container) return;

  vaultCurrentQrEntryId = entryId;

  // Buscar información de la credencial en caché para poblar la cabecera
  const vaultList = (typeof V24State !== "undefined" && V24State.vaultEntries) || (typeof window !== "undefined" && window.V24State && window.V24State.vaultEntries) || [];
  const entry = vaultList.find(e => e.id === entryId);
  if (titleEl) titleEl.textContent = entry ? (entry.title || "Credencial") : "Credencial";
  if (userEl) userEl.textContent = (entry && entry.username) ? entry.username : "—";
  if (pinToggle) pinToggle.checked = Boolean(usePin);

  try {
    let res = null;
    if (window.pywebview && window.pywebview.api && window.pywebview.api.vault_get_qr_payload) {
      res = await window.pywebview.api.vault_get_qr_payload(entryId, Boolean(usePin));
    } else {
      // Fallback seguro para entorno de navegador o pruebas sin pywebview
      res = {
        status: "ok",
        payload: JSON.stringify({
          t: usePin ? "pyclean-cred-enc" : "pyclean-cred",
          v: 1,
          title: entry ? entry.title : "Servicio",
          user: entry ? entry.username : "usuario",
          pass: entry ? entry.password : "secreto"
        }),
        pin: usePin ? "849201" : ""
      };
    }

    if (!res || res.status !== "ok" || !res.payload) {
      v24Log(res && res.message ? res.message : "Error generando código QR", "error");
      return;
    }

    vaultCurrentQrPayload = res.payload;

    if (usePin && res.pin) {
      if (pinContainer) pinContainer.style.display = "flex";
      if (pinBadge) pinBadge.textContent = res.pin;
    } else {
      if (pinContainer) pinContainer.style.display = "none";
    }

    // Renderizar código QR en el contenedor de alto contraste
    container.innerHTML = "";
    if (typeof QRCode !== "undefined") {
      new QRCode(container, {
        text: res.payload,
        width: 210,
        height: 210,
        colorDark: "#0B0E17",
        colorLight: "#FFFFFF",
        correctLevel: QRCode.CorrectLevel ? QRCode.CorrectLevel.M : 0
      });
    } else {
      container.textContent = "Error: Motor QRCode no cargado.";
    }

    // Iniciar temporizador de seguridad de 60 segundos con auto-cierre
    if (vaultQrCountdownTimer) clearInterval(vaultQrCountdownTimer);
    let secondsLeft = 60;
    if (timerEl) timerEl.textContent = String(secondsLeft);

    vaultQrCountdownTimer = setInterval(() => {
      secondsLeft--;
      if (timerEl) timerEl.textContent = String(Math.max(0, secondsLeft));
      if (secondsLeft <= 0) {
        closeVaultQrModal();
        v24Log("Modal QR cerrado automáticamente por seguridad.", "info");
      }
    }, 1000);

    modal.classList.add("open");
  } catch (err) {
    v24Log(`Error abriendo código QR: ${err}`, "error");
  }
}

function closeVaultQrModal() {
  const modal = document.getElementById("vault-qr-modal");
  if (modal) modal.classList.remove("open");

  if (vaultQrCountdownTimer) {
    clearInterval(vaultQrCountdownTimer);
    vaultQrCountdownTimer = null;
  }

  const container = document.getElementById("vault-qr-canvas-container");
  if (container) container.innerHTML = "";

  vaultCurrentQrEntryId = null;
  vaultCurrentQrPayload = "";
}

async function openVaultSyncModal() {
  const modal = document.getElementById("vault-sync-modal");
  const container = document.getElementById("vault-sync-qr-container");
  const urlEl = document.getElementById("vault-sync-url");
  const badgeEl = document.getElementById("vault-sync-status-badge");
  const statusTextEl = document.getElementById("vault-sync-status-text");
  const clientsEl = document.getElementById("vault-sync-clients-count");

  if (!modal || !container) return;

  try {
    let res = null;
    if (window.pywebview && window.pywebview.api && window.pywebview.api.vault_start_mobile_sync) {
      res = await window.pywebview.api.vault_start_mobile_sync();
    } else {
      // Mock para vista previa en navegador
      const mockIp = "192.168.1.100";
      const mockPort = 8765;
      const mockToken = "token_preview_sync";
      res = {
        status: "ok",
        url: `http://${mockIp}:${mockPort}/mobile?token=${mockToken}`,
        token: mockToken,
        qr_payload: JSON.stringify({
          v: 1,
          type: "pair",
          url: `http://${mockIp}:${mockPort}`,
          token: mockToken,
          ip: mockIp,
          port: mockPort
        }),
        ip: mockIp,
        port: mockPort
      };
    }

    if (!res || res.status !== "ok") {
      v24Log(res && res.message ? res.message : "Error iniciando servidor de sincronización", "error");
      return;
    }

    const fullUrl = res.url || `http://${res.ip}:${res.port}/mobile?token=${res.token}`;
    if (urlEl) urlEl.textContent = fullUrl;

    // Renderizar código QR de emparejamiento
    container.innerHTML = "";
    const qrPairString = res.url || res.qr_payload;
    if (typeof QRCode !== "undefined") {
      new QRCode(container, {
        text: qrPairString,
        width: 210,
        height: 210,
        colorDark: "#0B0E17",
        colorLight: "#FFFFFF",
        correctLevel: QRCode.CorrectLevel ? QRCode.CorrectLevel.M : 0
      });
    } else {
      container.textContent = "Error: Motor QRCode no cargado.";
    }

    if (badgeEl) badgeEl.classList.add("active");
    if (statusTextEl) statusTextEl.textContent = `Servidor activo en ${res.ip}:${res.port}`;
    if (clientsEl) clientsEl.textContent = "Dispositivos conectados: 0";

    // Iniciar sondeo periódico del estado de sincronización
    if (vaultSyncInterval) clearInterval(vaultSyncInterval);
    vaultSyncInterval = setInterval(async () => {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.vault_get_mobile_sync_status) {
        try {
          const st = await window.pywebview.api.vault_get_mobile_sync_status();
          if (st) {
            if (st.running) {
              if (badgeEl) badgeEl.classList.add("active");
              if (statusTextEl) statusTextEl.textContent = `Servidor activo en ${res.ip}:${res.port}`;
            } else {
              if (badgeEl) badgeEl.classList.remove("active");
              if (statusTextEl) statusTextEl.textContent = "Servidor detenido";
            }
            if (clientsEl) {
              clientsEl.textContent = `Dispositivos conectados: ${st.clients_connected || 0}`;
            }
            if (st.last_sync && st.last_sync > 0) {
              refreshVaultEntries();
            }
          }
        } catch (e) {
          // Ignorar fallo transitorio en sondeo
        }
      }
    }, 2500);

    modal.classList.add("open");
  } catch (err) {
    v24Log(`Error al iniciar sincronización móvil: ${err}`, "error");
  }
}

async function closeVaultSyncModal(stopServer = false) {
  const modal = document.getElementById("vault-sync-modal");
  if (modal) modal.classList.remove("open");

  if (vaultSyncInterval) {
    clearInterval(vaultSyncInterval);
    vaultSyncInterval = null;
  }

  const container = document.getElementById("vault-sync-qr-container");
  if (container) container.innerHTML = "";

  if (stopServer) {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.vault_stop_mobile_sync) {
      try {
        const res = await window.pywebview.api.vault_stop_mobile_sync();
        if (res && res.status === "ok") {
          v24Log("Servidor de sincronización móvil detenido.", "info");
        }
      } catch (e) {
        v24Log(`Error al detener sincronización: ${e}`, "error");
      }
    }
  }
}

// =========================================================================
// INICIALIZACIÓN DE EVENTOS v2.4
// =========================================================================

function initV24Modules() {
  if (V24State.listenersBound) return;
  V24State.listenersBound = true;

  // --- Monitor & Red ---
  const btnRefreshMon = document.getElementById("btn-refresh-monitor");
  if (btnRefreshMon) btnRefreshMon.addEventListener("click", loadMonitorView);

  const sortSel = document.getElementById("monitor-sort-select");
  if (sortSel) sortSel.addEventListener("change", loadTopProcesses);

  document.querySelectorAll(".btn-dns-preset").forEach(btn => {
    btn.addEventListener("click", async () => {
      const adapterSel = document.getElementById("dns-adapter-select");
      const statusBox = document.getElementById("dns-status-box");
      const adapter = adapterSel ? adapterSel.value : "";
      const preset = btn.dataset.preset;
      if (!adapter) {
        if (statusBox) statusBox.textContent = "Selecciona primero un adaptador de red activo.";
        return;
      }
      if (statusBox) statusBox.textContent = `Aplicando DNS '${preset}' en ${adapter}...`;
      try {
        const res = await window.pywebview.api.set_dns_preset(adapter, preset);
        if (statusBox) statusBox.textContent = res.message;
        v24Log(res.message, res.success ? "success" : "warning");
      } catch (err) {
        if (statusBox) statusBox.textContent = `Error: ${err}`;
        v24Log(`Error cambiando DNS: ${err}`, "error");
      }
    });
  });

  const btnPing = document.getElementById("btn-run-ping");
  if (btnPing) btnPing.addEventListener("click", runPingTestUI);

  // --- Salud Hardware ---
  const btnRefreshHw = document.getElementById("btn-refresh-hardware");
  if (btnRefreshHw) btnRefreshHw.addEventListener("click", loadHardwareView);

  const btnTrim = document.getElementById("btn-run-trim");
  if (btnTrim) {
    btnTrim.addEventListener("click", async () => {
      const driveSel = document.getElementById("trim-drive-select");
      const statusBox = document.getElementById("trim-status-box");
      const drive = driveSel ? driveSel.value : "C";
      btnTrim.disabled = true;
      if (statusBox) statusBox.textContent = `Ejecutando Optimize-Volume -ReTrim en ${drive}:\\...`;
      v24Log(`Ejecutando TRIM en unidad ${drive}:\\...`, "info");
      try {
        const res = await window.pywebview.api.run_ssd_trim(drive);
        if (statusBox) statusBox.textContent = res.message;
        v24Log(res.message, res.success ? "success" : "warning");
      } catch (err) {
        if (statusBox) statusBox.textContent = `Error: ${err}`;
      } finally {
        btnTrim.disabled = false;
      }
    });
  }

  // --- Centro de Batería (Auditoría, Optimización, Reparación y Calibración) ---
  const btnBattAudit = document.getElementById("btn-battery-audit");
  if (btnBattAudit) {
    btnBattAudit.addEventListener("click", async () => {
      if (!window.pywebview) return;
      btnBattAudit.disabled = true;
      setBatteryActionStatus("Ejecutando auditoría de eficiencia energética de Windows (10 segundos)...", "info");
      v24Log("Iniciando auditoría de drenaje de batería (powercfg /energy)...", "info");
      try {
        const res = await window.pywebview.api.run_battery_energy_audit(10);
        renderBatteryAuditResults(res);
        setBatteryActionStatus(res.message, res.success ? "success" : "warning");
        v24Log(res.message, res.success ? "success" : "warning");
      } catch (err) {
        setBatteryActionStatus(`Error en auditoría: ${err}`, "error");
      } finally {
        btnBattAudit.disabled = false;
      }
    });
  }

  const btnBattExportHtml = document.getElementById("btn-battery-export-html");
  if (btnBattExportHtml) {
    btnBattExportHtml.addEventListener("click", async () => {
      if (!window.pywebview) return;
      btnBattExportHtml.disabled = true;
      setBatteryActionStatus("Generando reporte oficial HTML de batería...", "info");
      try {
        const res = await window.pywebview.api.export_battery_report_html();
        setBatteryActionStatus(res.message, res.success ? "success" : "warning");
        v24Log(res.message, res.success ? "success" : "warning");
      } catch (err) {
        setBatteryActionStatus(`Error exportando reporte: ${err}`, "error");
      } finally {
        btnBattExportHtml.disabled = false;
      }
    });
  }

  const bindBatteryProfileBtn = (btnId, profile, runningLabel) => {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.addEventListener("click", async () => {
      if (!window.pywebview) return;
      btn.disabled = true;
      setBatteryActionStatus(runningLabel, "info");
      v24Log(runningLabel, "info");
      try {
        const res = await window.pywebview.api.optimize_battery_performance(profile);
        setBatteryActionStatus(res.message, res.success ? "success" : "warning");
        v24Log(res.message, res.success ? "success" : "warning");
        await loadBatteryHealthUI();
      } catch (err) {
        setBatteryActionStatus(`Error aplicando perfil: ${err}`, "error");
      } finally {
        btn.disabled = false;
      }
    });
  };

  bindBatteryProfileBtn(
    "btn-batt-opt-autonomy",
    "autonomy",
    "Aplicando perfil de Máxima Autonomía y Cuidado de Batería..."
  );
  bindBatteryProfileBtn(
    "btn-batt-opt-performance",
    "performance",
    "Aplicando perfil de Rendimiento Estable sin throttling..."
  );
  bindBatteryProfileBtn(
    "btn-batt-repair-schemes",
    "repair_schemes",
    "Restaurando esquemas de energía por defecto de Windows..."
  );

  const btnBattRepairDriver = document.getElementById("btn-batt-repair-driver");
  if (btnBattRepairDriver) {
    btnBattRepairDriver.addEventListener("click", async () => {
      if (!window.pywebview) return;
      if (!confirm("Se reiniciará temporalmente el controlador ACPI de batería (toma ~3 segundos). ¿Continuar?")) return;
      btnBattRepairDriver.disabled = true;
      setBatteryActionStatus("Reiniciando controlador ACPI de batería y reescaneando hardware...", "info");
      v24Log("Reparando controlador ACPI de batería...", "info");
      try {
        const res = await window.pywebview.api.repair_battery_driver();
        setBatteryActionStatus(res.message, res.success ? "success" : "warning");
        v24Log(res.message, res.success ? "success" : "warning");
        await loadBatteryHealthUI();
      } catch (err) {
        setBatteryActionStatus(`Error reparando driver ACPI: ${err}`, "error");
      } finally {
        btnBattRepairDriver.disabled = false;
      }
    });
  }

  const btnBattCalibStart = document.getElementById("btn-batt-calib-start");
  if (btnBattCalibStart) {
    btnBattCalibStart.addEventListener("click", async () => {
      if (!window.pywebview) return;
      btnBattCalibStart.disabled = true;
      setBatteryActionStatus("Preparando plan de energía para calibración segura de batería...", "info");
      try {
        const res = await window.pywebview.api.start_battery_calibration();
        setBatteryActionStatus(res.message, res.success ? "success" : "warning");
        v24Log(res.message, res.success ? "success" : "warning");
        await loadBatteryHealthUI();
      } catch (err) {
        setBatteryActionStatus(`Error iniciando calibración: ${err}`, "error");
      } finally {
        btnBattCalibStart.disabled = false;
      }
    });
  }

  const btnBattCalibFinish = document.getElementById("btn-batt-calib-finish");
  if (btnBattCalibFinish) {
    btnBattCalibFinish.addEventListener("click", async () => {
      if (!window.pywebview) return;
      btnBattCalibFinish.disabled = true;
      setBatteryActionStatus("Finalizando calibración, restaurando energía y comparando salud...", "info");
      try {
        const res = await window.pywebview.api.finish_battery_calibration();
        setBatteryActionStatus(res.message, res.success ? "success" : "warning");
        v24Log(res.message, res.success ? "success" : "warning");
        await loadBatteryHealthUI();
      } catch (err) {
        setBatteryActionStatus(`Error finalizando calibración: ${err}`, "error");
      } finally {
        btnBattCalibFinish.disabled = false;
      }
    });
  }

  const btnBattRestore = document.getElementById("btn-batt-restore-backup");
  if (btnBattRestore) {
    btnBattRestore.addEventListener("click", async () => {
      if (!window.pywebview) return;
      btnBattRestore.disabled = true;
      setBatteryActionStatus("Restaurando configuración previa de energía...", "info");
      try {
        const res = await window.pywebview.api.restore_battery_power_backup();
        setBatteryActionStatus(res.message, res.success ? "success" : "warning");
        v24Log(res.message, res.success ? "success" : "warning");
        await loadBatteryHealthUI();
      } catch (err) {
        setBatteryActionStatus(`Error restaurando respaldo: ${err}`, "error");
      } finally {
        btnBattRestore.disabled = false;
      }
    });
  }

  // --- Menú Contextual ---
  const btnRefreshCm = document.getElementById("btn-refresh-context-menu");
  if (btnRefreshCm) btnRefreshCm.addEventListener("click", loadContextMenuView);

  const cmSearch = document.getElementById("context-menu-search");
  if (cmSearch) {
    cmSearch.addEventListener("input", e => {
      const q = e.target.value.toLowerCase();
      const filtered = V24State.contextMenuItems.filter(
        i => i.label.toLowerCase().includes(q) || (i.command && i.command.toLowerCase().includes(q))
      );
      renderContextMenuTable(filtered);
    });
  }

  // --- Bóveda ---
  const bindEyeToggle = (btnId, inputId) => {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.addEventListener("click", () => {
      const inp = document.getElementById(inputId);
      if (inp) inp.type = inp.type === "password" ? "text" : "password";
    });
  };
  bindEyeToggle("btn-vault-toggle-master", "vault-master-input");
  bindEyeToggle("btn-vault-toggle-confirm", "vault-master-confirm");
  bindEyeToggle("btn-vault-toggle-pwd", "vault-password");

  const masterInput = document.getElementById("vault-master-input");
  const confirmInput = document.getElementById("vault-master-confirm");
  const btnVaultSubmit = document.getElementById("btn-vault-submit");

  if (masterInput) {
    masterInput.addEventListener("input", e => {
      if (!V24State.vaultExists) {
        updatePasswordStrengthUI(e.target.value, "vault-master-strength-fill", "vault-master-strength-label");
      }
    });
    masterInput.addEventListener("keydown", e => {
      if (e.key === "Enter" && btnVaultSubmit) btnVaultSubmit.click();
    });
  }
  if (confirmInput) {
    confirmInput.addEventListener("keydown", e => {
      if (e.key === "Enter" && btnVaultSubmit) btnVaultSubmit.click();
    });
  }

  if (btnVaultSubmit) {
    btnVaultSubmit.addEventListener("click", async () => {
      const pwd = masterInput ? masterInput.value : "";

      if (!V24State.vaultExists) {
        const confirmPwd = confirmInput ? confirmInput.value : "";
        if (!pwd || pwd.length < 8) {
          setVaultAuthStatus("La contraseña maestra debe tener al menos 8 caracteres.", "error");
          return;
        }
        if (pwd !== confirmPwd) {
          setVaultAuthStatus("Las contraseñas maestras no coinciden.", "error");
          return;
        }
        const res = await window.pywebview.api.vault_create(pwd);
        setVaultAuthStatus(res.message, res.success ? "success" : "error");
        if (res.success) {
          masterInput.value = "";
          confirmInput.value = "";
          updatePasswordStrengthUI("", "vault-master-strength-fill", "vault-master-strength-label");
          v24Log(res.message, "success");
          applyVaultStatus(res.status);
        }
      } else {
        if (!pwd) {
          setVaultAuthStatus("Introduce tu contraseña maestra.", "error");
          return;
        }
        const res = await window.pywebview.api.vault_unlock(pwd);
        setVaultAuthStatus(res.message, res.success ? "success" : "error");
        if (res.success) {
          masterInput.value = "";
          v24Log(res.message, "success");
          applyVaultStatus(res.status);
        }
      }
    });
  }

  const btnVaultLock = document.getElementById("btn-vault-lock");
  if (btnVaultLock) {
    btnVaultLock.addEventListener("click", async () => {
      closeVaultQrModal();
      closeVaultSyncModal(true);
      const res = await window.pywebview.api.vault_lock();
      clearVaultForm();
      v24Log("Bóveda bloqueada y memoria limpiada.", "info");
      applyVaultStatus(res.status);
    });
  }

  const btnVaultExport = document.getElementById("btn-vault-export");
  if (btnVaultExport) {
    btnVaultExport.addEventListener("click", async () => {
      const res = await window.pywebview.api.vault_export_backup();
      v24Log(res.message, res.success ? "success" : "warning");
    });
  }

  const btnVaultImport = document.getElementById("btn-vault-import");
  if (btnVaultImport) {
    btnVaultImport.addEventListener("click", async () => {
      const res = await window.pywebview.api.vault_import_backup();
      v24Log(res.message, res.success ? "success" : "warning");
      if (res.status) applyVaultStatus(res.status);
    });
  }

  const pwdField = document.getElementById("vault-password");
  if (pwdField) {
    pwdField.addEventListener("input", e => updatePasswordStrengthUI(e.target.value));
  }

  const btnGenFill = document.getElementById("btn-vault-gen-fill");
  if (btnGenFill) {
    btnGenFill.addEventListener("click", async () => {
      const res = await window.pywebview.api.vault_generate_password(20, true, true, true, true);
      if (pwdField) {
        pwdField.value = res.password;
        pwdField.type = "text";
        updatePasswordStrengthUI(res.password);
      }
    });
  }

  const btnSaveEntry = document.getElementById("btn-vault-save-entry");
  if (btnSaveEntry) {
    btnSaveEntry.addEventListener("click", async () => {
      const entryId = document.getElementById("vault-entry-id").value || null;
      const title = document.getElementById("vault-title").value;
      const category = document.getElementById("vault-category").value;
      const username = document.getElementById("vault-username").value;
      const url = document.getElementById("vault-url").value;
      const password = document.getElementById("vault-password").value;
      const notes = document.getElementById("vault-notes").value;

      const res = await window.pywebview.api.vault_save_entry(
        title,
        username,
        password,
        url,
        category,
        notes,
        entryId
      );
      if (res.success) {
        v24Log(res.message, "success");
        clearVaultForm();
        refreshVaultEntries();
      } else {
        v24Log(res.message, "warning");
      }
    });
  }

  const btnClearForm = document.getElementById("btn-vault-clear-form");
  if (btnClearForm) btnClearForm.addEventListener("click", clearVaultForm);

  const genRange = document.getElementById("vault-gen-length");
  if (genRange) {
    genRange.addEventListener("input", e => {
      const val = document.getElementById("vault-gen-length-val");
      if (val) val.textContent = `${e.target.value} caracteres`;
    });
  }

  const btnGenerate = document.getElementById("btn-vault-generate");
  if (btnGenerate) {
    btnGenerate.addEventListener("click", async () => {
      const len = parseInt(document.getElementById("vault-gen-length").value) || 20;
      const upper = document.getElementById("vault-gen-upper").checked;
      const digits = document.getElementById("vault-gen-digits").checked;
      const symbols = document.getElementById("vault-gen-symbols").checked;
      const res = await window.pywebview.api.vault_generate_password(len, upper, true, digits, symbols);
      const preview = document.getElementById("vault-gen-preview");
      if (preview) preview.textContent = res.password;
    });
  }

  const btnCopyGen = document.getElementById("btn-vault-copy-gen");
  if (btnCopyGen) {
    btnCopyGen.addEventListener("click", async () => {
      const preview = document.getElementById("vault-gen-preview");
      const pwd = preview ? preview.textContent : "";
      if (!pwd || pwd.startsWith("Pulsa")) return;
      await window.pywebview.api.vault_copy_secret(pwd, 30);
      const orig = btnCopyGen.textContent;
      btnCopyGen.textContent = "✓ Copiado";
      setTimeout(() => { btnCopyGen.textContent = orig; }, 2000);
      v24Log("Contraseña generada copiada (se limpiará del portapapeles en 30s).", "success");
    });
  }

  const vaultSearch = document.getElementById("vault-search");
  if (vaultSearch) {
    vaultSearch.addEventListener("input", () => applyVaultSearchAndFilter());
  }

  // --- Sincronización Móvil & Modales QR (Milestone 2) ---
  const btnVaultSync = document.getElementById("btn-vault-sync");
  if (btnVaultSync) {
    btnVaultSync.addEventListener("click", () => openVaultSyncModal());
  }

  const btnSyncClose = document.getElementById("btn-vault-sync-close");
  if (btnSyncClose) {
    btnSyncClose.addEventListener("click", () => closeVaultSyncModal(false));
  }

  const btnSyncStop = document.getElementById("btn-vault-sync-stop");
  if (btnSyncStop) {
    btnSyncStop.addEventListener("click", () => closeVaultSyncModal(true));
  }

  const btnSyncCopyUrl = document.getElementById("btn-vault-sync-copy-url");
  if (btnSyncCopyUrl) {
    btnSyncCopyUrl.addEventListener("click", async () => {
      const urlEl = document.getElementById("vault-sync-url");
      const urlText = urlEl ? urlEl.textContent : "";
      if (urlText) {
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(urlText);
          } else if (window.pywebview && window.pywebview.api && window.pywebview.api.vault_copy_secret) {
            await window.pywebview.api.vault_copy_secret(urlText, 60);
          }
          const orig = btnSyncCopyUrl.textContent;
          btnSyncCopyUrl.textContent = "✓";
          setTimeout(() => { btnSyncCopyUrl.textContent = orig; }, 2000);
          v24Log("Enlace de sincronización copiado.", "success");
        } catch (e) {
          v24Log(`Error copiando enlace: ${e}`, "error");
        }
      }
    });
  }

  const btnQrClose = document.getElementById("btn-vault-qr-close");
  if (btnQrClose) {
    btnQrClose.addEventListener("click", () => closeVaultQrModal());
  }

  const btnQrCopy = document.getElementById("btn-vault-qr-copy");
  if (btnQrCopy) {
    btnQrCopy.addEventListener("click", async () => {
      if (vaultCurrentQrPayload) {
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(vaultCurrentQrPayload);
          } else if (window.pywebview && window.pywebview.api && window.pywebview.api.vault_copy_secret) {
            await window.pywebview.api.vault_copy_secret(vaultCurrentQrPayload, 60);
          }
          const orig = btnQrCopy.textContent;
          btnQrCopy.textContent = "✓ Copiado";
          setTimeout(() => { btnQrCopy.textContent = orig; }, 2000);
          v24Log("Texto del código QR copiado al portapapeles.", "success");
        } catch (e) {
          v24Log(`Error copiando texto QR: ${e}`, "error");
        }
      }
    });
  }

  const pinToggle = document.getElementById("vault-qr-pin-toggle");
  if (pinToggle) {
    pinToggle.addEventListener("change", (e) => {
      if (vaultCurrentQrEntryId) {
        openVaultQrModal(vaultCurrentQrEntryId, e.target.checked);
      }
    });
  }

  // Cierre de modales al hacer clic en el fondo difuminado (overlay)
  const qrModal = document.getElementById("vault-qr-modal");
  if (qrModal) {
    qrModal.addEventListener("click", (e) => {
      if (e.target === qrModal) closeVaultQrModal();
    });
  }
  const syncModal = document.getElementById("vault-sync-modal");
  if (syncModal) {
    syncModal.addEventListener("click", (e) => {
      if (e.target === syncModal) closeVaultSyncModal(false);
    });
  }
}

window.V24State = V24State;
window.initV24Modules = initV24Modules;
window.openVaultQrModal = openVaultQrModal;
window.closeVaultQrModal = closeVaultQrModal;
window.openVaultSyncModal = openVaultSyncModal;
window.closeVaultSyncModal = closeVaultSyncModal;

window.onV24TabSelected = function (tabId) {
  if (tabId === "tab-monitor") loadMonitorView();
  else if (tabId === "tab-hardware") loadHardwareView();
  else if (tabId === "tab-context-menu") loadContextMenuView();
  else if (tabId === "tab-vault") loadVaultView();
};
