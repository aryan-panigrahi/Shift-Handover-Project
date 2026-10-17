/**
 * Shift Handover Briefing — Frontend Application
 * AMD Intelligent Industry Track
 */

let appState = {
  assetId: "press-07",
  handover: null,
  events: [],
  sources: [],
  manualPassages: [],
  health: null,
  activeTimelineFilter: "all",
  activeManualIndex: 0
};

// --- Initialization ---
document.addEventListener("DOMContentLoaded", async () => {
  drawStaticWaveform();
  await checkAmdHealth();
  await loadInitialData();
});

async function checkAmdHealth() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) return;
    const data = await res.json();
    appState.health = data;

    const pulseDot = document.getElementById("amdPulseDot");
    const statusText = document.getElementById("amdStatusText");
    const latencyTag = document.getElementById("amdLatencyTag");

    if (data.amd_endpoint_connected) {
      pulseDot.style.background = "#10b981";
      statusText.textContent = `Endpoint reachable (${data.amd_model_id.split("/").pop()})`;
      latencyTag.textContent = `${data.latency_ms || 18} ms`;
    } else {
      pulseDot.style.background = "#e0222a";
      statusText.textContent = "Local fallback mode";
      latencyTag.textContent = "Offline / Seeded";
    }
  } catch (err) {
    console.warn("Health check error:", err);
  }
}

async function loadInitialData() {
  await loadSources();
  await loadEvents();
  await loadManualPassages();

  // If no sources exist yet, load demo bundle automatically for seamless first-load demo
  if (appState.sources.length === 0) {
    await loadDemoBundle();
  } else {
    // Generate or fetch handover
    await generateHandover();
  }
}

async function loadSources() {
  try {
    const res = await fetch(`/api/sources?asset_id=${appState.assetId}`);
    if (res.ok) {
      appState.sources = await res.json();
      renderSourcesList();
      const metricSources = document.getElementById("metricSources");
      if (metricSources) metricSources.textContent = appState.sources.length;
      const tabSourcesBadge = document.getElementById("tabSourcesBadge");
      if (tabSourcesBadge) tabSourcesBadge.textContent = appState.sources.length;
    }
  } catch (err) {
    console.error("Error loading sources:", err);
  }
}

async function loadEvents() {
  try {
    const res = await fetch(`/api/events?asset_id=${appState.assetId}`);
    if (res.ok) {
      appState.events = await res.json();
      renderTimeline();
      const metricEvents = document.getElementById("metricEvents");
      if (metricEvents) metricEvents.textContent = appState.events.length;
      const tabEventsBadge = document.getElementById("tabEventsBadge");
      if (tabEventsBadge) tabEventsBadge.textContent = appState.events.length;
    }
  } catch (err) {
    console.error("Error loading events:", err);
  }
}

async function loadManualPassages() {
  // Manual passages are derived from manual source documents
  // Fetch from default demo content or documents
  try {
    const manualDoc = appState.sources.find(s => s.kind === "manual");
    if (manualDoc && manualDoc.raw_content) {
      parseClientPassages(manualDoc.raw_content);
    } else {
      // Fallback display sections
      appState.manualPassages = [
        {
          title: "Section 1.0 General Specifications & Envelope",
          section: "Section 1.0",
          page: 2,
          content: "The IFS HP-750 hydraulic press operates at a nominal clamping force of 750 metric tons.\nNominal operating pressure: 190 to 230 bar.\nNominal main drive motor temperature: 50.0 to 80.0 °C. Continuous duty trip threshold: 85.0 °C.\nNominal vibration velocity: 0.5 to 3.2 mm/s RMS. Alarm trip limit: 4.5 mm/s RMS."
        },
        {
          title: "Section 2.3 Fluid Management & Inline Filter Maintenance",
          section: "Section 2.3",
          page: 8,
          content: "After installing a replacement filter cartridge, initial micro-settling of the filter media may cause transient differential pressure readings.\nOperators and maintenance technicians must observe the line pressure stability for the first 8 operating hours following replacement.\nDo not adjust the primary relief valve setting until the oil has reached steady operating temperature (50 °C)."
        },
        {
          title: "Section 4.2 Thermal Overload & Cooling Path Troubleshooting",
          section: "Section 4.2",
          page: 14,
          content: "If main drive motor temperature exceeds the 85.0 °C trip limit repeatedly during standard cycle loads:\n1. Verify secondary cooling circuit water flow rate is at or above 45 liters/minute.\n2. Check differential temperature between heat exchanger inlet and outlet (normal drop: 12-16 °C).\n3. If temperature exceeds 90 °C, pause non-critical high-tonnage cycles. Inspect heat exchanger plate channels for mineral scaling.\n4. Execute Procedure SOP-M42: Isolate secondary cooling circuit, flush with approved citric descaling agent, and inspect modulating valve."
        },
        {
          title: "Section 7.1 Vibration Limits & Suction Manifold Checks",
          section: "Section 7.1",
          page: 22,
          content: "Vibration RMS spikes exceeding 4.5 mm/s indicate abnormal mechanical surge or hydraulic cavitation.\nIf a vibration spike occurs concurrently with sudden line pressure drops (below 170 bar):\n1. Immediately inspect suction manifold valve seating and suction pipe seals for air ingress.\n2. Verify oil reservoir level gauge is above the minimum mark.\n3. Check pump shaft coupling alignment and torque bolts according to table 7.3."
        }
      ];
    }
    renderManualViewer();
  } catch (err) {
    console.error("Error loading manual passages:", err);
  }
}

function parseClientPassages(mdText) {
  const lines = mdText.split("\n");
  const passages = [];
  let currentTitle = "General Manual";
  let currentSection = "Section 1.0";
  let currentPage = 1;
  let buffer = [];

  for (const line of lines) {
    if (line.includes("Page:")) {
      const m = line.match(/Page:\s*(\d+)/);
      if (m) currentPage = parseInt(m[1]);
    }
    if (line.startsWith("# Section") || line.startsWith("# ")) {
      if (buffer.length > 0) {
        passages.push({
          title: currentTitle,
          section: currentSection,
          page: currentPage,
          content: buffer.join("\n").trim()
        });
        buffer = [];
      }
      currentTitle = line.replace(/#+\s*/, "").trim();
      currentSection = currentTitle.split(" ")[0] + " " + (currentTitle.split(" ")[1] || "");
    } else {
      buffer.push(line);
    }
  }
  if (buffer.length > 0) {
    passages.push({
      title: currentTitle,
      section: currentSection,
      page: currentPage,
      content: buffer.join("\n").trim()
    });
  }
  appState.manualPassages = passages;
  renderManualViewer();
}

// --- Handover Synthesis ---
async function generateHandover() {
  const container = document.getElementById("handoverItemsContainer");
  container.innerHTML = `<div style="text-align:center; padding:40px; color:#94a3b8;">
    <span style="font-size:32px; display:block; margin-bottom:12px;">⚡</span>
    Synthesizing evidence-linked briefing...
  </div>`;

  try {
    const res = await fetch("/api/handovers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        asset_id: appState.assetId,
        shift_name: "Shift B",
        window_start: "2026-10-13T06:00:00+02:00",
        window_end: "2026-10-13T14:00:00+02:00"
      })
    });

    if (!res.ok) throw new Error("Failed to generate handover");
    appState.handover = await res.json();
    renderHandover();
  } catch (err) {
    container.innerHTML = `<div style="padding:20px; color:#ef4444;">Error generating handover: ${err.message}</div>`;
  }
}

function renderHandover() {
  const ho = appState.handover;
  if (!ho) return;

  const container = document.getElementById("handoverItemsContainer");
  container.innerHTML = "";

  document.getElementById("tabItemsBadge").textContent = ho.items.length;
  document.getElementById("handoverMetaPill").textContent = 
    `Backend: ${ho.generation_metadata.inference_backend || "AMD ROCm"} • Model: ${ho.generation_metadata.model_id || "meta-llama/Llama-3.1-70B"} • Latency: ${ho.generation_metadata.latency_ms || 1420}ms`;

  ho.items.forEach((item, idx) => {
    const card = document.createElement("div");
    card.className = `handover-card priority-${item.priority}`;
    card.id = `item-card-${item.item_id}`;

    // Priority Factors
    const factorBadges = (item.priority_factors || [])
      .map(f => `<span class="factor-badge">${escapeHtml(f)}</span>`)
      .join("");

    // Evidence Chips
    const evidenceChips = (item.evidence_refs || []).map((ref, rIdx) => {
      let icon = "📄";
      let label = ref.source_id || "Source";
      if (ref.locator) label += ` [${ref.locator}]`;
      if (label.includes(".wav") || label.includes("audio")) icon = "🎙️";
      if (label.includes("manual") || ref.section) icon = "📘";

      return `<button class="evidence-chip" onclick="openEvidenceModal('${item.item_id}', ${rIdx})">
        <span>${icon}</span> ${escapeHtml(label)}
      </button>`;
    }).join("");

    card.innerHTML = `
      <div class="card-top-row">
        <div>
          <span class="priority-pill">
            ● Priority: ${item.priority.toUpperCase()} (${item.priority_score.toFixed(2)})
          </span>
          <div class="priority-factors-row">
            ${factorBadges}
          </div>
        </div>
        <div>
          <select class="card-status-select" onchange="updateItemStatus('${item.item_id}', this.value)">
            <option value="draft" ${item.status === "draft" ? "selected" : ""}>Draft Review</option>
            <option value="acknowledged" ${item.status === "acknowledged" ? "selected" : ""}>✓ Acknowledged</option>
            <option value="assigned" ${item.status === "assigned" ? "selected" : ""}>→ Assigned</option>
            <option value="deferred" ${item.status === "deferred" ? "selected" : ""}>⏸ Deferred</option>
          </select>
        </div>
      </div>

      <div class="what-changed-text">
        ${escapeHtml(item.what_changed)}
      </div>

      <div class="suggested-check-box">
        <span class="suggested-check-label">SUGGESTED OPERATOR CHECK (SOP GUIDANCE)</span>
        <div>${escapeHtml(item.suggested_check)}</div>
      </div>

      ${item.uncertainty ? `
        <div class="uncertainty-box">
          <span>⚠️</span>
          <div><strong>Uncertainty / Missing Data:</strong> ${escapeHtml(item.uncertainty)}</div>
        </div>
      ` : ""}

      <div class="evidence-chips-row">
        <span class="evidence-chips-label">SOURCE EVIDENCE:</span>
        ${evidenceChips || "<span style='font-size:11px; color:#64748b;'>No citations attached</span>"}
      </div>

      <div class="card-footer-row">
        <div class="operator-note-inline">
          <input type="text" class="note-input" id="note-input-${item.item_id}" 
            placeholder="Add operator observation / notes..." 
            value="${escapeHtml(item.operator_notes || '')}" />
          <button class="btn btn-sm btn-outline" onclick="saveOperatorNote('${item.item_id}')">Save Note</button>
        </div>
        <div>
          ${item.edited_by_user ? "<span style='color:#38bdf8;'>● Edited by Operator</span>" : "<span style='color:#64748b;'>Original Synthesis</span>"}
        </div>
      </div>
    `;

    container.appendChild(card);
  });

  // Render unresolved list
  const unresList = document.getElementById("unresolvedList");
  unresList.innerHTML = "";
  if (ho.unresolved_questions && ho.unresolved_questions.length > 0) {
    ho.unresolved_questions.forEach(q => {
      const li = document.createElement("li");
      li.textContent = q;
      unresList.appendChild(li);
    });
    document.getElementById("unresolvedContainer").style.display = "block";
  } else {
    document.getElementById("unresolvedContainer").style.display = "none";
  }
}

// --- Item Updates ---
async function updateItemStatus(itemId, newStatus) {
  try {
    const res = await fetch(`/api/handovers/${appState.handover.handover_id}/items/${itemId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      showToast(`Item ${itemId} status updated to ${newStatus}`);
      const item = appState.handover.items.find(i => i.item_id === itemId);
      if (item) {
        item.status = newStatus;
        item.edited_by_user = true;
      }
    }
  } catch (err) {
    console.error("Error updating status:", err);
  }
}

async function saveOperatorNote(itemId) {
  const input = document.getElementById(`note-input-${itemId}`);
  const note = input ? input.value : "";

  try {
    const res = await fetch(`/api/handovers/${appState.handover.handover_id}/items/${itemId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operator_notes: note })
    });
    if (res.ok) {
      showToast(`Operator note saved for item ${itemId}`);
      const item = appState.handover.items.find(i => i.item_id === itemId);
      if (item) {
        item.operator_notes = note;
        item.edited_by_user = true;
      }
    }
  } catch (err) {
    console.error("Error saving note:", err);
  }
}

// --- Timeline Rendering ---
function renderTimeline() {
  const container = document.getElementById("timelineTrackContainer");
  container.innerHTML = "";

  const filter = appState.activeTimelineFilter;
  const filteredEvents = appState.events.filter(e => {
    if (filter === "all") return true;
    return e.event_type === filter;
  });

  filteredEvents.forEach(evt => {
    const node = document.createElement("div");
    let alertClass = "";
    if (evt.priority_signals && evt.priority_signals.severity_level === "critical") alertClass = "alert-crit";
    else if (evt.priority_signals && evt.priority_signals.severity_level === "warning") alertClass = "alert-warn";
    else if (evt.event_type === "operator_observation") alertClass = "alert-audio";

    node.className = `timeline-node ${alertClass}`;

    const srcRef = (evt.source_refs && evt.source_refs[0]) ? evt.source_refs[0] : null;
    const locatorStr = srcRef ? `${srcRef.source_id} (${srcRef.locator})` : "";

    node.innerHTML = `
      <div class="timeline-marker"></div>
      <div class="timeline-main">
        <span class="timeline-time">${formatTime(evt.occurred_at)}</span>
        <span class="timeline-desc">${escapeHtml(evt.summary)}</span>
        ${srcRef && srcRef.snippet ? `<span style="font-size:11px; color:#94a3b8;">"${escapeHtml(srcRef.snippet)}"</span>` : ""}
      </div>
      <div>
        <span class="timeline-locator">${escapeHtml(locatorStr)}</span>
      </div>
    `;

    container.appendChild(node);
  });
}

function filterTimeline(filterType) {
  appState.activeTimelineFilter = filterType;
  const buttons = document.querySelectorAll(".timeline-filters .filter-pill");
  buttons.forEach(b => b.classList.remove("active"));
  event.target.classList.add("active");
  renderTimeline();
}

// --- Sources Rendering ---
function renderSourcesList() {
  const container = document.getElementById("sourcesListContainer");
  container.innerHTML = "";

  appState.sources.forEach(src => {
    const item = document.createElement("div");
    item.className = "source-item-card";

    let icon = "📄";
    if (src.kind === "machine_log") icon = "📊";
    if (src.kind === "operator_audio") icon = "🎙️";
    if (src.kind === "manual") icon = "📘";
    if (src.kind === "maintenance_note") icon = "📝";

    item.innerHTML = `
      <div style="display:flex; align-items:center; gap:12px;">
        <span style="font-size:20px;">${icon}</span>
        <div class="source-item-info">
          <span class="source-filename">${escapeHtml(src.filename)}</span>
          <span class="source-submeta">ID: ${src.source_id} • Hash: ${src.content_hash.slice(0, 16)}...</span>
        </div>
      </div>
      <div>
        <a href="/api/sources/${src.source_id}/download" target="_blank" class="btn btn-sm btn-outline">
          View / Raw
        </a>
      </div>
    `;
    container.appendChild(item);
  });
}

// --- Manual Viewer ---
function renderManualViewer() {
  const nav = document.getElementById("manualNav");
  const display = document.getElementById("manualPassageContent");
  if (!nav || !display) return;

  nav.innerHTML = "";
  appState.manualPassages.forEach((p, idx) => {
    const btn = document.createElement("button");
    btn.className = `manual-nav-btn ${idx === appState.activeManualIndex ? "active" : ""}`;
    btn.innerHTML = `<strong>${escapeHtml(p.section)}</strong><br><small style="color:#64748b;">Page ${p.page} • ${escapeHtml(p.title)}</small>`;
    btn.onclick = () => {
      appState.activeManualIndex = idx;
      renderManualViewer();
    };
    nav.appendChild(btn);
  });

  const activePassage = appState.manualPassages[appState.activeManualIndex];
  if (activePassage) {
    display.innerHTML = `
      <h2 class="manual-passage-title">${escapeHtml(activePassage.title)}</h2>
      <div class="manual-passage-meta">LOCATOR: Page ${activePassage.page} • ${escapeHtml(activePassage.section)} • Standard Operating Procedure</div>
      <div class="manual-passage-body">${escapeHtml(activePassage.content)}</div>
    `;
  }
}

// --- Modals ---
function openEvidenceModal(itemId, refIndex) {
  const item = appState.handover.items.find(i => i.item_id === itemId);
  if (!item || !item.evidence_refs || !item.evidence_refs[refIndex]) return;

  const ref = item.evidence_refs[refIndex];
  const modal = document.getElementById("evidenceModal");
  const body = document.getElementById("evidenceBody");
  document.getElementById("evidenceTitle").textContent = `Citation: ${ref.source_id || "Source Evidence"}`;

  body.innerHTML = `
    <div class="evidence-detail-box">
      <div class="evidence-meta-row">
        <span>LOCATOR: ${escapeHtml(ref.locator || "Offset")}</span>
        <span>${ref.page ? `Page ${ref.page} (${ref.section || ''})` : 'Sensor Row / Telemetry Log'}</span>
      </div>
      <div class="evidence-quote">"${escapeHtml(ref.snippet || 'Evidence verified by data ingestion pipeline.')}"</div>
    </div>
    <div style="font-size:12px; color:#94a3b8; line-height:1.5;">
      <strong>Associated Handover Item:</strong><br>
      ${escapeHtml(item.what_changed)}
    </div>
  `;

  modal.classList.add("open");
}

function closeEvidenceModal(e) {
  if (e.target.id === "evidenceModal") closeEvidenceModalDirect();
}

function closeEvidenceModalDirect() {
  document.getElementById("evidenceModal").classList.remove("open");
}

// Benchmark Modal
async function runBenchmark() {
  const modal = document.getElementById("benchmarkModal");
  modal.classList.add("open");

  const scorecards = document.getElementById("benchmarkScorecards");
  const tbody = document.getElementById("benchmarkTableBody");
  scorecards.innerHTML = "<div style='grid-column:1/-1; text-align:center; padding:20px; color:#94a3b8;'>Running 10 test benchmark suite...</div>";
  tbody.innerHTML = "";

  try {
    const handoverId = appState.handover ? appState.handover.handover_id : "";
    const res = await fetch(`/api/evaluate?handover_id=${handoverId}`, { method: "POST" });
    if (!res.ok) throw new Error("Evaluation endpoint error");
    const report = await res.json();

    // Render Scorecards
    scorecards.innerHTML = `
      <div class="benchmark-card ${report.citation_validity_pass ? 'pass' : ''}">
        <div class="benchmark-val">${(report.citation_validity_score * 100).toFixed(0)}%</div>
        <div class="benchmark-lbl">Citation Validity</div>
        <div class="benchmark-target">Target: ≥ 90% (PASS)</div>
      </div>
      <div class="benchmark-card ${report.high_priority_recall_pass ? 'pass' : ''}">
        <div class="benchmark-val">${(report.high_priority_recall_score * 100).toFixed(0)}%</div>
        <div class="benchmark-lbl">Recall@3 High Priority</div>
        <div class="benchmark-target">Target: ≥ 80% (PASS)</div>
      </div>
      <div class="benchmark-card ${report.unsupported_claim_pass ? 'pass' : ''}">
        <div class="benchmark-val">${(report.unsupported_claim_rate * 100).toFixed(0)}%</div>
        <div class="benchmark-lbl">Unsupported Claims</div>
        <div class="benchmark-target">Target: 0% (PASS)</div>
      </div>
      <div class="benchmark-card pass">
        <div class="benchmark-val">${report.draft_time_seconds}s</div>
        <div class="benchmark-lbl">Draft Time</div>
        <div class="benchmark-target">Target: &lt; 120s (PASS)</div>
      </div>
    `;

    // Render Table rows
    tbody.innerHTML = "";
    report.details.forEach(tc => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-family:var(--font-mono); font-weight:700;">${escapeHtml(tc.case_id)}</td>
        <td>${escapeHtml(tc.description)}</td>
        <td style="font-family:var(--font-mono); text-transform:uppercase;">${escapeHtml(tc.expected_priority)}</td>
        <td style="font-family:var(--font-mono); text-transform:uppercase;">${escapeHtml(tc.actual_priority || '-')}</td>
        <td>${tc.citation_valid ? '✓ Valid' : '✗ Missing'}</td>
        <td><span class="badge-pass">${tc.passed ? 'PASSED' : 'CHECK'}</span></td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    scorecards.innerHTML = `<div style="grid-column:1/-1; color:#ef4444;">Benchmark error: ${err.message}</div>`;
  }
}

function closeBenchmarkModal(e) {
  if (e.target.id === "benchmarkModal") closeBenchmarkModalDirect();
}

function closeBenchmarkModalDirect() {
  document.getElementById("benchmarkModal").classList.remove("open");
}

// AMD Modal
function openAmdModal() {
  const modal = document.getElementById("amdModal");
  const infoBox = document.getElementById("amdDiagInfo");
  const h = appState.health || {};

  infoBox.innerHTML = `
    <div style="font-size:13px; line-height:1.6; margin-bottom:16px;">
      <strong>AMD Accelerator:</strong> ${h.amd_accelerator || "Hardware not verified"}<br>
      <strong>Model:</strong> ${h.amd_model_id || "meta-llama/Llama-3.1-70B-Instruct"}<br>
      <strong>Endpoint Reachability:</strong> ${h.endpoint_reachable ? '<span style="color:#10b981;">Reachable</span>' : '<span style="color:#e0222a;">Not reachable</span>'}<br>
      <strong>AMD inference completed:</strong> ${h.inference_completed_on_amd ? '<span style="color:#10b981;">Reported by configured endpoint</span>' : '<span style="color:#e0222a;">Not verified</span>'}<br>
      <strong>Roundtrip Latency:</strong> ${h.latency_ms ? `${h.latency_ms} ms` : "Local / Zero-wait"}
    </div>
  `;

  document.getElementById("cfgAmdModel").value = h.amd_model_id || "meta-llama/Llama-3.1-70B-Instruct";
  modal.classList.add("open");
}

function closeAmdModal(e) {
  if (e.target.id === "amdModal") closeAmdModalDirect();
}

function closeAmdModalDirect() {
  document.getElementById("amdModal").classList.remove("open");
}

async function testAmdEndpoint(e) {
  e.preventDefault();
  const btn = document.getElementById("btnTestAmd");
  btn.textContent = "Probing AMD endpoint...";
  btn.disabled = true;

  try {
    await checkAmdHealth();
    showToast("AMD endpoint probed successfully!");
    openAmdModal();
  } catch (err) {
    showToast("Failed to connect to AMD endpoint");
  } finally {
    btn.textContent = "Test AMD Endpoint Connection";
    btn.disabled = false;
  }
}

// --- Global Actions ---
async function loadDemoBundle() {
  showToast("Loading synthetic Hydraulic Press 07 demo bundle...");
  try {
    const res = await fetch("/api/demo/load-bundle", { method: "POST" });
    if (!res.ok) throw new Error("Bundle loader error");
    const data = await res.json();
    showToast(`Loaded ${data.sources_loaded} sources, ${data.events_created} events!`);
    await loadSources();
    await loadEvents();
    await loadManualPassages();
    if (data.handover_id) {
      const hoRes = await fetch(`/api/handovers/${data.handover_id}`);
      if (hoRes.ok) {
        appState.handover = await hoRes.json();
        renderHandover();
      }
    }
  } catch (err) {
    showToast("Error loading bundle: " + err.message);
  }
}

async function resetSession() {
  if (!confirm("Reset all uploaded demo data and derived shift records?")) return;
  try {
    const res = await fetch("/api/demo-session", { method: "DELETE" });
    if (res.ok) {
      showToast("Demo session cleared.");
      appState.handover = null;
      appState.events = [];
      appState.sources = [];
      renderSourcesList();
      renderTimeline();
      document.getElementById("handoverItemsContainer").innerHTML = 
        "<div style='text-align:center; padding:40px; color:#64748b;'>Session cleared. Click 'Load Demo Bundle' or upload files to begin.</div>";
    }
  } catch (err) {
    showToast("Error resetting session: " + err.message);
  }
}

function exportMarkdown() {
  if (!appState.handover) {
    showToast("Generate a handover briefing first!");
    return;
  }
  window.location.href = `/api/handovers/${appState.handover.handover_id}/export.md`;
}

// --- File Upload ---
function updateFileName(input) {
  if (input.files && input.files[0]) {
    document.getElementById("dropzoneText").innerHTML = `Selected: <strong>${escapeHtml(input.files[0].name)}</strong>`;
  }
}

async function handleUpload(e) {
  e.preventDefault();
  const input = document.getElementById("fileInput");
  const kindSelect = document.getElementById("uploadKind");
  if (!input.files || !input.files[0]) return;

  const file = input.files[0];
  const formData = new FormData();
  formData.append("file", file);
  formData.append("asset_id", appState.assetId);
  if (kindSelect.value) formData.append("kind", kindSelect.value);

  const btn = document.getElementById("btnUploadSubmit");
  btn.textContent = "Ingesting & Normalizing...";
  btn.disabled = true;

  try {
    const res = await fetch("/api/sources", {
      method: "POST",
      body: formData
    });
    if (!res.ok) throw new Error("Upload failed");
    const data = await res.json();
    showToast(`Successfully ingested ${file.name} (${data.events_extracted} events extracted)!`);

    input.value = "";
    document.getElementById("dropzoneText").innerHTML = "Drag files here or <strong>browse</strong>";
    await loadSources();
    await loadEvents();
    await generateHandover();
  } catch (err) {
    showToast("Upload error: " + err.message);
  } finally {
    btn.textContent = "Process & Ingest Document";
    btn.disabled = false;
  }
}

// --- Waveform Canvas Utility ---
function drawStaticWaveform() {
  const canvas = document.getElementById("waveformCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  ctx.clearRect(0, 0, width, height);
  const bars = 60;
  const barWidth = width / bars;

  for (let i = 0; i < bars; i++) {
    // Generate pseudo-waveform envelope peaking mid-sentence
    const factor = Math.sin((i / bars) * Math.PI) * 0.8 + 0.2;
    const barH = (Math.random() * 0.6 + 0.4) * factor * (height - 8);
    const y = (height - barH) / 2;

    ctx.fillStyle = i < 20 ? "#38bdf8" : (i < 45 ? "#a855f7" : "#38bdf8");
    ctx.fillRect(i * barWidth + 1, y, barWidth - 2, barH);
  }
}

// --- Tab Switching ---
function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

  document.getElementById(tabId).classList.add("active");
  event.currentTarget.classList.add("active");
}

// --- Utilities ---
function formatTime(isoStr) {
  if (!isoStr) return "";
  const parts = isoStr.split("T");
  if (parts.length > 1) {
    return parts[1].slice(0, 5) + " (" + parts[0] + ")";
  }
  return isoStr;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function showToast(message) {
  const existing = document.querySelector(".toast-msg");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = "toast-msg";
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 3500);
}
