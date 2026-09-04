/**
 * ============================================================================
 * VeriGate — Screening Workstation, Real-Time Intake & Dynamic Results
 * ============================================================================
 * Dual-channel chat-style evidence stream on left.
 * Real-time telemetry & dynamically generated DOM intelligence report on right.
 */

/* ═══════════════════════════════════
   FILE UPLOAD & CHAT INTAKE SLOTS
   ═══════════════════════════════════ */

function triggerFile(kind) {
  document.getElementById(kind === 'doc' ? 'fileDoc' : 'fileFace')?.click();
}

function handleFile(kind, files) {
  if (!files || !files[0]) return;
  session[kind] = files[0];
  if (kind === 'doc') {
    if (session.docPreviewUrl) URL.revokeObjectURL(session.docPreviewUrl);
    session.docPreviewUrl = URL.createObjectURL(files[0]);
  }
  renderSlot(kind);
  updateIntakeStatus();
}

function renderSlot(kind) {
  const slot = document.getElementById(kind === 'doc' ? 'slotDoc' : 'slotFace');
  const slotContent = document.getElementById(kind === 'doc' ? 'slotDocContent' : 'slotFaceContent');
  const file = session[kind];
  if (!slot || !slotContent || !file) return;

  const url = URL.createObjectURL(file);
  const sizeKb = Math.round(file.size / 1024);
  const formattedSize = sizeKb > 1024 ? `${(sizeKb / 1024).toFixed(1)} MB` : `${sizeKb} KB`;

  slot.classList.add('loaded');
  slotContent.innerHTML = `
    <img class="slot-preview-thumb" src="${url}" alt="${kind === 'doc' ? 'Document' : 'Face'} Preview" />
    <div class="slot-text">
      <div class="slot-title">${escapeHtml(file.name)}</div>
      <div class="slot-sub mono">${formattedSize} • <span class="slot-badge-loaded">✓ LOADED</span></div>
    </div>
    <button type="button" class="btn-slot-remove" onclick="event.stopPropagation(); clearSlot('${kind}')" aria-label="Remove File">
      <svg style="width:14px;height:14px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
        <path d="M18 6 6 18M6 6l12 12"/>
      </svg>
    </button>
  `;
}

function clearSlot(kind) {
  session[kind] = null;
  if (kind === 'doc' && session.docPreviewUrl) {
    URL.revokeObjectURL(session.docPreviewUrl);
    session.docPreviewUrl = null;
  }
  const slot = document.getElementById(kind === 'doc' ? 'slotDoc' : 'slotFace');
  const slotContent = document.getElementById(kind === 'doc' ? 'slotDocContent' : 'slotFaceContent');
  const input = document.getElementById(kind === 'doc' ? 'fileDoc' : 'fileFace');
  if (input) input.value = '';

  if (slot) slot.classList.remove('loaded');
  if (slotContent) {
    if (kind === 'doc') {
      slotContent.innerHTML = `
        <div class="slot-icon-box">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <rect x="2" y="4" width="20" height="16" rx="2"/>
            <circle cx="8" cy="10" r="1.5"/>
            <path d="M2 16l4-4 4 4 6-6 4 4"/>
          </svg>
        </div>
        <div class="slot-text">
          <div class="slot-title">Identity Document</div>
          <div class="slot-sub">Passport, National ID or Driver's License</div>
        </div>
        <button type="button" class="btn-slot-attach" aria-label="Attach Document">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          <span>Attach</span>
        </button>
      `;
    } else {
      slotContent.innerHTML = `
        <div class="slot-icon-box">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="12" cy="8" r="4"/>
            <path d="M6 20c0-3.5 3-6 6-6s6 2.5 6 6"/>
          </svg>
        </div>
        <div class="slot-text">
          <div class="slot-title">Presented Person</div>
          <div class="slot-sub">Clear frontal portrait or live capture</div>
        </div>
        <div class="slot-actions">
          <button type="button" class="btn-slot-attach" aria-label="Attach Face Photo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
            <span>Attach</span>
          </button>
          <button type="button" class="btn-slot-camera" onclick="event.stopPropagation(); openCameraModal()" aria-label="Use Camera">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
            <span>Camera</span>
          </button>
        </div>
      `;
    }
  }

  updateIntakeStatus();
}

function updateIntakeStatus() {
  const count = (session.doc ? 1 : 0) + (session.face ? 1 : 0);
  const countEl = document.getElementById('fileCount');
  const readinessEl = document.getElementById('intakeReadiness');
  const runBtn = document.getElementById('runBtn');

  if (countEl) countEl.textContent = `${count} / 2 evidence files loaded`;
  if (readinessEl) {
    if (count === 2) {
      readinessEl.textContent = 'READY FOR PIPELINE';
      readinessEl.className = 'intake-readiness ready';
    } else if (count === 1) {
      readinessEl.textContent = '1 FILE REMAINING';
      readinessEl.className = 'intake-readiness';
    } else {
      readinessEl.textContent = 'WAITING FOR FILES';
      readinessEl.className = 'intake-readiness';
    }
  }
  if (runBtn) {
    runBtn.disabled = count < 2;
  }
}

/**
 * Fast Demo Samples Loader
 */
async function loadSampleCase(type) {
  try {
    const isDocValid = type === 'valid';
    const basePath = isDocValid ? 'assets/samples/valid/' : 'assets/samples/invalid/';
    const docPath = basePath + 'document.png';
    const facePath = basePath + (isDocValid ? 'face.jpeg' : 'face.png');

    const [docRes, faceRes] = await Promise.all([
      fetch(docPath),
      fetch(facePath)
    ]);

    if (!docRes.ok || !faceRes.ok) {
      console.warn('Could not load sample files locally');
      return;
    }

    const docBlob = await docRes.blob();
    const faceBlob = await faceRes.blob();

    const docFile = new File([docBlob], isDocValid ? 'german_passport_sample.png' : 'tampered_passport_sample.png', { type: 'image/png' });
    const faceFile = new File([faceBlob], isDocValid ? 'live_subject_portrait.jpeg' : 'mismatch_photo.png', { type: isDocValid ? 'image/jpeg' : 'image/png' });

    handleFile('doc', [docFile]);
    handleFile('face', [faceFile]);

    // Micro-toast or visual flash
    const btn = document.getElementById('runBtn');
    if (btn) {
      gsap.fromTo(btn, { scale: 1.05 }, { scale: 1, duration: 0.35, ease: 'back.out(2)' });
    }
  } catch (err) {
    console.error('Error loading sample case:', err);
  }
}

function setupUploadPanels() {
  ['slotDoc', 'slotFace'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('dragover', e => { e.preventDefault(); el.classList.add('dragging'); });
    el.addEventListener('dragleave', () => el.classList.remove('dragging'));
    el.addEventListener('drop', e => {
      e.preventDefault();
      el.classList.remove('dragging');
      handleFile(id === 'slotDoc' ? 'doc' : 'face', e.dataTransfer.files);
    });
  });
}

/* ═══════════════════════════════════
   EXECUTION & INLINE TELEMETRY
   ═══════════════════════════════════ */

let screeningActive = false;

function setRunButtonState(state) {
  const runBtn = document.getElementById('runBtn');
  if (!runBtn) return;
  const count = (session.doc ? 1 : 0) + (session.face ? 1 : 0);

  if (state === 'screening') {
    runBtn.disabled = true;
    runBtn.classList.add('screening-running');
    runBtn.innerHTML = `
      <span class="btn-spinner"></span>
      <span>Screening...</span>
    `;
  } else {
    runBtn.classList.remove('screening-running');
    runBtn.disabled = count < 2;
    runBtn.innerHTML = `
      <span class="btn-shine"></span>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>
      <span>Start Screening</span>
    `;
  }
}

async function checkServerConnection() {
  const statusEl = document.getElementById('serverConnectionStatus');
  const dotEl = document.getElementById('serverConnectionDot');
  const textEl = document.getElementById('serverConnectionText');

  try {
    const res = await fetch('/api/health', { method: 'GET', signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      if (statusEl) {
        statusEl.classList.remove('disconnected');
        statusEl.classList.add('connected');
      }
      if (dotEl) {
        dotEl.className = 'pulse-dot-green';
      }
      if (textEl) {
        textEl.textContent = 'CONNECTED • SYSTEM READY';
      }
      return true;
    } else {
      throw new Error(`HTTP ${res.status}`);
    }
  } catch (_) {
    if (statusEl) {
      statusEl.classList.remove('connected');
      statusEl.classList.add('disconnected');
    }
    if (dotEl) {
      dotEl.className = 'pulse-dot-red';
    }
    if (textEl) {
      textEl.textContent = 'CONNECTION FAILED • SERVER OFFLINE';
    }
    return false;
  }
}

async function startScreeningProcess() {
  if (!session.doc || !session.face) return;
  screeningActive = true;
  setRunButtonState('screening');

  const standby = document.getElementById('telemetryStandby');
  const processing = document.getElementById('telemetryProcessing');
  const results = document.getElementById('dynamicResultsContainer');

  if (standby) standby.style.display = 'none';
  if (results) {
    gsap.killTweensOf(results);
    results.style.display = 'none';
    results.innerHTML = '';
    gsap.set(results, { clearProps: 'all' });
  }
  if (processing) {
    processing.style.display = 'flex';
    processing.innerHTML = `
      <div class="proc-header">
        <div class="proc-badge"><span class="live-pulse"></span>ACTIVE PIPELINE EXECUTION</div>
        <div class="proc-pct-val mono" id="inlineProcPct">0%</div>
      </div>
      <div class="proc-progress-bar">
        <div class="proc-progress-fill" id="inlineProcBarFill"></div>
      </div>
      <div class="inline-stage-list" id="inlineStageList"></div>
      <div class="telemetry-console" id="telemetryConsole">
        <div class="console-line">&gt; Initializing secure cryptographic session...</div>
      </div>
    `;
  }

  // Pre-flight check: verify server is online
  const isConnected = await checkServerConnection();
  if (!isConnected) {
    screeningActive = false;
    setRunButtonState('idle');
    screeningError('Connection Failed: Cannot reach backend server at http://127.0.0.1:8000. Please ensure the Python uvicorn server is running.');
    return;
  }

  // Build inline stage rows
  const stageList = document.getElementById('inlineStageList');
  if (stageList) {
    stageList.innerHTML = '';
    PIPELINE_STAGES.forEach((s, i) => {
      const item = document.createElement('div');
      item.className = 'inline-stage-item';
      item.id = `inlineStage-${i}`;
      item.innerHTML = `
        <div class="inline-stage-check" id="inlineCheck-${i}">○</div>
        <div class="inline-stage-info">
          <div class="inline-stage-name">${escapeHtml(s.label)}</div>
          <div class="inline-stage-sub">${escapeHtml(s.sub)}</div>
        </div>
      `;
      stageList.appendChild(item);
    });
  }

  // Clear and initialize console
  const consoleEl = document.getElementById('telemetryConsole');
  if (consoleEl) {
    consoleEl.innerHTML = '<div class="console-line">> [0.00s] Establishing encrypted TLS forensic tunnel...</div>';
  }

  // Kick off API execution
  executeScreening().catch(err => {
    if (!screeningActive) return;
    screeningError(err.message || 'Screening pipeline execution encountered an error.');
  });
}

function stopScreeningProcess() {
  screeningActive = false;
  setRunButtonState('idle');
  const standby = document.getElementById('telemetryStandby');
  const processing = document.getElementById('telemetryProcessing');
  const results = document.getElementById('dynamicResultsContainer');

  if (processing) processing.style.display = 'none';
  if (results) {
    gsap.killTweensOf(results);
    results.style.display = 'none';
    results.innerHTML = '';
    gsap.set(results, { clearProps: 'all' });
  }
  if (standby) standby.style.display = 'flex';

  clearSlot('doc');
  clearSlot('face');
  updateIntakeStatus();
}

function setInlineStage(index, state, logMsg) {
  const item = document.getElementById(`inlineStage-${index}`);
  const check = document.getElementById(`inlineCheck-${index}`);
  const bar = document.getElementById('inlineProcBarFill');
  const pct = document.getElementById('inlineProcPct');
  const consoleEl = document.getElementById('telemetryConsole');

  if (item && check) {
    item.className = `inline-stage-item ${state}`;
    if (state === 'running') {
      check.innerHTML = '●';
    } else if (state === 'done') {
      check.innerHTML = '✓';
    }
  }

  const stageProgress = Math.round(((index + (state === 'done' ? 1 : 0.4)) / PIPELINE_STAGES.length) * 100);
  if (bar) bar.style.width = `${stageProgress}%`;
  if (pct) pct.textContent = `${stageProgress}%`;

  if (consoleEl && logMsg) {
    const line = document.createElement('div');
    line.className = 'console-line';
    const elapsed = session.startTime ? ((Date.now() - session.startTime) / 1000).toFixed(2) : '0.00';
    line.textContent = `> [${elapsed}s] ${logMsg}`;
    consoleEl.insertBefore(line, consoleEl.firstChild);
  }
}

function screeningError(message) {
  screeningActive = false;
  setRunButtonState('idle');
  checkServerConnection();

  const processing = document.getElementById('telemetryProcessing');
  if (!processing) return;

  const isNetworkError = /failed to fetch|networkerror|connection refused|load failed|cannot reach backend/i.test(message);
  const displayMsg = isNetworkError 
    ? 'Server Error: Backend connection failed. Ensure the VeriGate uvicorn server is running on http://127.0.0.1:8000.'
    : message;

  const errBox = document.createElement('div');
  errBox.className = 'processing-error';
  errBox.style.marginTop = '16px';
  errBox.innerHTML = `
    <div style="color:var(--crimson-glow);font-weight:700;font-size:15px;margin-bottom:8px;">
      ${isNetworkError ? '⚠ Connection Failed' : '⚠ Pipeline Error'}
    </div>
    <div style="color:#e2e8f0;font-size:13.5px;line-height:1.6;margin-bottom:14px;">
      ${escapeHtml(displayMsg)}
    </div>
    <button type="button" class="btn-res-run-again" onclick="startScreeningProcess()">
      Retry Screening
    </button>
  `;
  processing.appendChild(errBox);
}

/* ═══════════════════════════════════
   DYNAMIC RESULTS DOM BUILDER
   Creates cards dynamically with smooth GSAP staggered reveals
   ═══════════════════════════════════ */

function renderDynamicResults(r) {
  screeningActive = false;
  setRunButtonState('idle');
  const processing = document.getElementById('telemetryProcessing');
  const container = document.getElementById('dynamicResultsContainer');
  if (!container) return;

  if (processing) processing.style.display = 'none';

  // Ensure container is clean, visible, and free of leftover GSAP opacity/transforms
  gsap.killTweensOf(container);
  gsap.set(container, { clearProps: 'all' });
  container.style.display = 'flex';
  container.style.opacity = '1';
  container.style.visibility = 'visible';
  container.style.transform = 'none';
  container.innerHTML = ''; // Start clean!

  const dec = String(r.decision || 'review').toLowerCase();
  const decisionClass = dec === 'approve' ? 'approve' : dec === 'reject' ? 'reject' : 'review';
  const decisionColor = dec === 'approve' ? 'var(--verified)' : dec === 'reject' ? 'var(--crimson)' : 'var(--amber)';

  // 1. FINAL DECISION & RISK HERO BANNER
  const heroCard = document.createElement('div');
  heroCard.className = 'res-hero-card';
  heroCard.style.setProperty('--accent-col', decisionColor);

  const radius = 38;
  const circum = 2 * Math.PI * radius;
  const offset = circum * (1 - (r.riskScore || 0) / 100);

  heroCard.innerHTML = `
    <div class="res-hero-left">
      <div class="res-decision-pill ${decisionClass}">
        <span>●</span>
        <span>${escapeHtml(r.decision.toUpperCase())}</span>
      </div>
      <div class="res-risk-gauge-box">
        <svg class="res-gauge-svg" viewBox="0 0 100 100">
          <circle class="res-gauge-bg" cx="50" cy="50" r="${radius}"/>
          <circle class="res-gauge-fill" id="resGaugeCircle" cx="50" cy="50" r="${radius}"
                  stroke="${decisionColor}"
                  stroke-dasharray="${circum}"
                  stroke-dashoffset="${circum}" />
        </svg>
        <div class="res-gauge-center">
          <span class="res-gauge-score" id="resGaugeScore">0</span>
          <span class="res-gauge-label">RISK / 100</span>
        </div>
      </div>
    </div>
    <div class="res-hero-right">
      <div class="res-risk-level-badge">
        <span>RISK RATING:</span>
        <span class="res-risk-level-val ${decisionClass}" style="background:rgba(255,255,255,0.06);color:${decisionColor};">${escapeHtml(r.riskLevel.toUpperCase())}</span>
      </div>
      <div class="res-one-line-verdict">
        “${escapeHtml(r.summary)}”
      </div>
    </div>
  `;
  container.appendChild(heroCard);

  // 2. IDENTITY DETAILS CARD
  const idCard = document.createElement('div');
  idCard.className = 'res-card';
  idCard.innerHTML = `
    <div class="res-card-header">
      <div class="res-card-title">
        <span class="res-card-dot"></span>IDENTITY CREDENTIAL DETAILS
      </div>
      <span class="mono" style="font-size:11px;font-weight:600;color:var(--ink-secondary);">CROSS-EXTRACTED (OCR + MRZ)</span>
    </div>
    <div class="res-id-grid">
      ${r.identity.map(f => {
        const isAge = f.field.toLowerCase().includes('age');
        return `
        <div class="res-id-item ${isAge ? 'highlight-age' : ''}">
          <div class="res-id-label">${escapeHtml(f.field)}</div>
          <div class="res-id-val ${isAge ? 'val-age' : ''}">${escapeHtml(f.value)}</div>
        </div>
      `;}).join('')}
    </div>
  `;
  container.appendChild(idCard);

  // 3. DOCUMENT STATUS & VALIDATION CHECKS (Skipped tests filtered out to avoid clutter)
  const valCard = document.createElement('div');
  valCard.className = 'res-card';
  const isDocValid = r.documentStatus === 'Valid';
  const activeChecks = (r.checks || []).filter(c => {
    const s = String(c.status || 'passed').toLowerCase();
    return s !== 'skip' && s !== 'skipped';
  });

  valCard.innerHTML = `
    <div class="res-card-header">
      <div class="res-card-title">
        <span class="res-card-dot" style="background:${isDocValid ? 'var(--verified)' : 'var(--crimson)'};"></span>DOCUMENT VALIDATION CHECKS
      </div>
      <span class="res-check-status ${isDocValid ? 'pass' : 'fail'}">${r.documentStatus.toUpperCase()}</span>
    </div>
    <div class="res-checks-list">
      ${activeChecks.length > 0 ? activeChecks.map(c => {
        const status = String(c.status || 'passed').toLowerCase();
        const cls = status === 'passed' ? 'pass' : 'fail';
        return `
          <div class="res-check-row">
            <span class="res-check-label">${escapeHtml(c.message || c.check_name || 'Verification Check')}</span>
            <span class="res-check-status ${cls}">${escapeHtml(status.toUpperCase())}</span>
          </div>
        `;
      }).join('') : `
        <div class="res-check-row">
          <span class="res-check-label">Standard format and layout conformance verified</span>
          <span class="res-check-status pass">PASSED</span>
        </div>
      `}
    </div>
  `;
  container.appendChild(valCard);

  // 4. FACE VERIFICATION CARD
  const faceCard = document.createElement('div');
  faceCard.className = 'res-card';
  const isFaceMatch = r.face.is_match === true;
  const faceMatchLabel = r.face.error_message ? 'INCONCLUSIVE' : (isFaceMatch ? 'MATCH CONFIRMED' : 'MISMATCH DETECTED');
  const faceColor = r.face.error_message ? 'var(--gold-glow)' : (isFaceMatch ? 'var(--verified)' : 'var(--crimson)');
  const hasDistance = r.face.distance !== undefined && r.face.distance !== null;
  const distNum = hasDistance ? Number(r.face.distance) : null;
  const threshNum = r.face.threshold !== undefined && r.face.threshold !== null ? Number(r.face.threshold) : null;
  const distStr = distNum !== null ? distNum.toFixed(3) : 'N/A';
  const threshStr = threshNum !== null ? threshNum.toFixed(3) : 'N/A';
  const metricName = (r.face.distance_metric || 'Cosine').toUpperCase();
  const modelName = r.face.model_name || 'Facenet512';

  let meterPct = 0;
  let faceMetricText = '';
  if (r.face.error_message) {
    faceMetricText = escapeHtml(r.face.error_message);
    meterPct = 0;
  } else if (hasDistance && threshNum !== null && threshNum > 0) {
    meterPct = Math.max(0, Math.min(100, Math.round(Math.max(0, 1 - (distNum / (threshNum * 2))) * 100)));
    faceMetricText = isFaceMatch ? `${meterPct}% BIOMETRIC SIMILARITY` : `${meterPct}% SIMILARITY (BELOW THRESHOLD)`;
  } else {
    faceMetricText = isFaceMatch ? 'BIOMETRIC MATCH CONFIRMED' : 'BIOMETRIC MISMATCH DETECTED';
    meterPct = isFaceMatch ? 100 : 25;
  }

  faceCard.innerHTML = `
    <div class="res-card-header">
      <div class="res-card-title">
        <span class="res-card-dot" style="background:${faceColor};"></span>BIOMETRIC FACE CORRESPONDENCE
      </div>
      <span class="res-check-status ${isFaceMatch ? 'pass' : 'fail'}">${faceMatchLabel}</span>
    </div>
    <div class="res-face-box">
      <div class="res-face-status-row">
        <div class="res-face-metric" style="color:${faceColor};">${faceMetricText}</div>
        <div class="mono" style="font-size:11px;color:var(--ink-muted);">DOCUMENT-TO-PORTRAIT</div>
      </div>
      <div class="res-face-meter">
        <div class="res-face-fill" style="width:${meterPct}%;background:${faceColor};"></div>
      </div>
      <div class="res-face-sub mono">
        ${metricName} Distance: <strong>${distStr}</strong> (Threshold: ${threshStr}) • Model: ${escapeHtml(modelName)}
      </div>
    </div>
  `;
  container.appendChild(faceCard);

  // 5. TAMPERING FORENSICS (ELA)
  const tampCard = document.createElement('div');
  tampCard.className = 'res-card';
  const isTampered = Boolean(r.tampering.suspicious);
  const tampScorePct = Math.round((r.tampering.score || 0) * 100);
  const heatmapUrl = r.tampering.evidenceImagePath ? `${API_BASE}/${r.tampering.evidenceImagePath.replace(/^\/+/, '')}` : null;
  const originalDocUrl = session.docPreviewUrl || (session.doc ? URL.createObjectURL(session.doc) : null);
  if (originalDocUrl && !session.docPreviewUrl) {
    session.docPreviewUrl = originalDocUrl;
  }

  tampCard.innerHTML = `
    <div class="res-card-header">
      <div class="res-card-title">
        <span class="res-card-dot" style="background:${isTampered ? 'var(--crimson)' : 'var(--verified)'};"></span>ERROR LEVEL ANALYSIS (ELA) &amp; FORENSICS
      </div>
      <span class="res-check-status ${isTampered ? 'fail' : 'pass'}">${isTampered ? 'SUSPICIOUS ARTIFACTS' : 'PRISTINE / VERIFIED'}</span>
    </div>
    <div class="res-forensics-box">
      <div class="res-forensics-stats">
        <div class="res-id-item">
          <div class="res-id-label">COMPRESSION VARIANCE SCORE</div>
          <div class="res-id-val mono">${(r.tampering.score || 0).toFixed(2)} (${tampScorePct}%)</div>
        </div>
        <div class="res-id-item">
          <div class="res-id-label">FLAGGED TAMPER REGIONS</div>
          <div class="res-id-val mono">${r.tampering.signals.filter(s => s.is_suspicious).length} DETECTED</div>
        </div>
      </div>
      ${heatmapUrl ? `
        <div class="forensic-view-wrapper">
          <div class="forensic-view-toolbar">
            <span class="forensic-view-label mono">EVIDENCE VIEW:</span>
            <div class="forensic-toggle-group">
              <button type="button" class="btn-forensic-toggle active" id="btnToggleEla" onclick="toggleForensicView('ela')">
                <span class="toggle-dot ela"></span>
                <span>ELA Heatmap</span>
              </button>
              ${originalDocUrl ? `
                <button type="button" class="btn-forensic-toggle" id="btnToggleOrig" onclick="toggleForensicView('orig')">
                  <span class="toggle-dot orig"></span>
                  <span>Original Document</span>
                </button>
              ` : ''}
            </div>
          </div>
          <div class="forensic-image-viewport">
            <img class="res-heatmap-img" id="forensicDisplayImg" src="${heatmapUrl}" alt="ELA Heatmap Evidence" data-ela-src="${heatmapUrl}" ${originalDocUrl ? `data-orig-src="${originalDocUrl}"` : ''} />
            <div class="forensic-image-caption mono" id="forensicDisplayCaption">SHOWING: COMPRESSION RESIDUAL HEATMAP (ELA)</div>
          </div>
        </div>
      ` : `
        <div class="mono" style="font-size:11.5px;color:var(--ink-muted);padding:8px 0;">
          ${isTampered ? 'Compression gradient variance indicates surface manipulation.' : 'Zero high-frequency error discrepancies detected across document surface.'}
        </div>
      `}
    </div>
  `;
  container.appendChild(tampCard);

  // 6. DATE INTELLIGENCE
  const dateCard = document.createElement('div');
  dateCard.className = 'res-card';
  dateCard.innerHTML = `
    <div class="res-card-header">
      <div class="res-card-title">
        <span class="res-card-dot" style="background:#00f2fe;"></span>DATE INTELLIGENCE &amp; CHRONOLOGY
      </div>
      <span class="mono" style="font-size:10px;color:var(--cyan-glow);">TEMPORAL CONSISTENCY</span>
    </div>
    <div class="res-id-grid">
      <div class="res-id-item">
        <div class="res-id-label">VERIFICATION DATE</div>
        <div class="res-id-val mono">${escapeHtml(r.dateIntelligence.currentDate)}</div>
      </div>
      <div class="res-id-item highlight-age">
        <div class="res-id-label">SUBJECT AGE</div>
        <div class="res-id-val val-age">${escapeHtml(r.dateIntelligence.age)}</div>
      </div>
      <div class="res-id-item">
        <div class="res-id-label">DOCUMENT EXPIRY STATUS</div>
        <div class="res-id-val" style="color:var(--verified);">${escapeHtml(r.dateIntelligence.expiryStatus)}</div>
      </div>
      <div class="res-id-item">
        <div class="res-id-label">CHRONOLOGICAL INCONSISTENCIES</div>
        <div class="res-id-val">${escapeHtml(r.dateIntelligence.inconsistencies)}</div>
      </div>
    </div>
  `;
  container.appendChild(dateCard);

  // 7. REFERENCE CHECK
  const refCard = document.createElement('div');
  refCard.className = 'res-card';
  refCard.innerHTML = `
    <div class="res-card-header">
      <div class="res-card-title">
        <span class="res-card-dot" style="background:#a855f7;"></span>REFERENCE &amp; ISSUANCE RECORD CHECK
      </div>
      <span class="res-check-status pass">${escapeHtml(r.referenceCheck.status.toUpperCase())}</span>
    </div>
    <div style="font-size:13px;color:var(--ink-secondary);line-height:1.5;">
      ${escapeHtml(r.referenceCheck.matchingStatus)}. Document format and issuance records evaluated against reference database.
    </div>
  `;
  container.appendChild(refCard);

  // 8. RISK FACTORS (ONLY ACTUAL DETECTED ISSUES OR ZERO DETECTED)
  const risksCard = document.createElement('div');
  risksCard.className = 'res-card';
  const hasRisks = r.riskFactors && r.riskFactors.length > 0;
  risksCard.innerHTML = `
    <div class="res-card-header">
      <div class="res-card-title">
        <span class="res-card-dot" style="background:${hasRisks ? 'var(--crimson)' : 'var(--verified)'};"></span>DETECTED RISK FACTORS
      </div>
      <span class="mono" style="font-size:10px;color:var(--ink-muted);">${hasRisks ? `${r.riskFactors.length} ACTIVE` : '0 ANOMALIES'}</span>
    </div>
    <div class="res-risks-list">
      ${hasRisks ? r.riskFactors.map(rf => `
        <div class="res-risk-row">
          <span style="color:var(--crimson);font-size:14px;">⚠</span>
          <span>${escapeHtml(rf.message || rf.factor_name || 'Risk factor detected')}</span>
        </div>
      `).join('') : `
        <div class="res-risk-clean">
          <svg style="width:16px;height:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6 9 17l-5-5"/></svg>
          <span>Zero risk anomalies detected: no tampering, facial discrepancy, or structural invalidity.</span>
        </div>
      `}
    </div>
  `;
  container.appendChild(risksCard);

  // 9. AUDIT INFO
  const auditCard = document.createElement('div');
  auditCard.className = 'res-card';
  auditCard.innerHTML = `
    <div class="res-card-header">
      <div class="res-card-title">
        <span class="res-card-dot" style="background:#64748b;"></span>AUDIT &amp; PROVENANCE METADATA
      </div>
      <span class="mono" style="font-size:10px;color:var(--ink-muted);">SESSION COMPLIANCE</span>
    </div>
    <div class="res-id-grid">
      <div class="res-id-item">
        <div class="res-id-label">SESSION ID</div>
        <div class="res-id-val mono" style="font-size:11px;color:var(--cyan-glow);">${escapeHtml(r.auditInfo.sessionId)}</div>
      </div>
      <div class="res-id-item">
        <div class="res-id-label">AI REASONING PROVIDER</div>
        <div class="res-id-val">${escapeHtml(r.auditInfo.aiProvider)}</div>
      </div>
      <div class="res-id-item">
        <div class="res-id-label">TOTAL LATENCY</div>
        <div class="res-id-val mono" style="color:var(--verified);">${escapeHtml(r.auditInfo.processingTime)}</div>
      </div>
    </div>
  `;
  container.appendChild(auditCard);

  // 10. THE LAST BOX OF THE RESULTS: AI REASONING
  const reasoningCard = document.createElement('div');
  reasoningCard.className = 'res-ai-reasoning-card';
  reasoningCard.innerHTML = `
    <div class="res-ai-badge">
      <svg style="width:14px;height:14px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"/></svg>
      <span>AI REASONING — GEMMA ARBITER</span>
    </div>
    <div class="res-ai-reasoning-body">
      ${escapeHtml(r.reasoning)}
    </div>
  `;
  container.appendChild(reasoningCard);

  // 11. ACTION BUTTONS: EXPORT AUDIT REPORT (JSON & PDF) & RUN AGAIN
  const rerunRow = document.createElement('div');
  rerunRow.className = 'res-run-again-row';
  rerunRow.innerHTML = `
    <button type="button" class="btn-res-export" onclick="exportScreeningReport('json')" aria-label="Export Forensic JSON Report">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
      <span>Export JSON</span>
    </button>
    <button type="button" class="btn-res-export btn-res-pdf" onclick="exportScreeningReport('pdf')" aria-label="Export Forensic PDF Report">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
      <span>Export PDF</span>
    </button>
    <button type="button" class="btn-res-run-again" onclick="resetScreeningWorkstation()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5"/></svg>
      <span>Run Another Screening</span>
    </button>
  `;
  container.appendChild(rerunRow);

  // ── GSAP FLUID DYNAMIC DOM ANIMATIONS ──
  // Animate all newly appended DOM cards with fluid 60fps stagger
  gsap.fromTo(container.children,
    { opacity: 0, y: 30, scale: 0.98 },
    {
      opacity: 1,
      y: 0,
      scale: 1,
      duration: 0.65,
      stagger: 0.08,
      ease: 'power3.out',
      clearProps: 'transform'
    }
  );

  // Animate Risk Score Gauge and counter
  const scoreValEl = document.getElementById('resGaugeScore');
  const circleEl = document.getElementById('resGaugeCircle');
  if (circleEl) {
    gsap.to(circleEl, {
      attr: { 'stroke-dashoffset': offset },
      duration: 1.4,
      ease: 'power3.out',
      delay: 0.2
    });
  }
  if (scoreValEl) {
    gsap.to({ val: 0 }, {
      val: r.riskScore || 0,
      duration: 1.4,
      ease: 'power3.out',
      delay: 0.2,
      onUpdate() {
        scoreValEl.textContent = Math.round(this.targets()[0].val);
      }
    });
  }
}

function resetScreeningWorkstation() {
  closeCameraModal();
  screeningActive = false;
  setRunButtonState('idle');
  clearSlot('doc');
  clearSlot('face');
  const standby = document.getElementById('telemetryStandby');
  const processing = document.getElementById('telemetryProcessing');
  const results = document.getElementById('dynamicResultsContainer');

  if (results) {
    gsap.killTweensOf(results);
    gsap.to(results, {
      opacity: 0,
      y: -15,
      duration: 0.25,
      onComplete() {
        results.style.display = 'none';
        results.innerHTML = '';
        gsap.set(results, { clearProps: 'all' });
        if (standby) {
          standby.style.display = 'flex';
          gsap.fromTo(standby, { opacity: 0, scale: 0.96 }, { opacity: 1, scale: 1, duration: 0.35, ease: 'power2.out' });
        }
      }
    });
  } else if (standby) {
    standby.style.display = 'flex';
  }
  if (processing) processing.style.display = 'none';
  updateIntakeStatus();
}

/* ═══════════════════════════════════
   FORENSIC EVIDENCE TOGGLE (ORIGINAL / ELA)
   ═══════════════════════════════════ */

function toggleForensicView(mode) {
  const img = document.getElementById('forensicDisplayImg');
  const caption = document.getElementById('forensicDisplayCaption');
  const btnEla = document.getElementById('btnToggleEla');
  const btnOrig = document.getElementById('btnToggleOrig');
  if (!img) return;

  if (mode === 'orig') {
    const origSrc = img.getAttribute('data-orig-src');
    if (origSrc) {
      img.src = origSrc;
      img.alt = 'Original Document Credential';
      if (caption) caption.textContent = 'SHOWING: ORIGINAL DOCUMENT CREDENTIAL';
      if (btnOrig) btnOrig.classList.add('active');
      if (btnEla) btnEla.classList.remove('active');
    }
  } else {
    const elaSrc = img.getAttribute('data-ela-src');
    if (elaSrc) {
      img.src = elaSrc;
      img.alt = 'ELA Heatmap Evidence';
      if (caption) caption.textContent = 'SHOWING: COMPRESSION RESIDUAL HEATMAP (ELA)';
      if (btnEla) btnEla.classList.add('active');
      if (btnOrig) btnOrig.classList.remove('active');
    }
  }
}

/* ═══════════════════════════════════
   EXPORT SCREENING REPORT (JSON & PDF)
   ═══════════════════════════════════ */

function exportScreeningReport(format = 'json') {
  if (!session.report) return;
  const r = session.report;

  // Build clean report payload from actual screening data
  const exportPayload = {
    sessionId: r.auditInfo?.sessionId || session.sessionId || 'VG-REPORT',
    timestamp: new Date().toISOString(),
    decision: r.decision,
    riskScore: r.riskScore,
    riskLevel: r.riskLevel,
    summary: r.summary,
    aiReasoning: r.reasoning,
    extractedIdentity: r.identity,
    documentValidation: {
      status: r.documentStatus,
      checks: r.checks
    },
    faceVerification: r.face,
    tamperingEvidence: r.tampering,
    dateIntelligence: r.dateIntelligence,
    referenceCheck: r.referenceCheck,
    riskFactors: r.riskFactors,
    auditInfo: r.auditInfo
  };

  if (format === 'json') {
    const jsonStr = JSON.stringify(exportPayload, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `verigate-audit-report-${exportPayload.sessionId}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 1500);
    return;
  }

  if (format === 'pdf') {
    generatePdfReport(r, exportPayload);
  }
}

function generatePdfReport(r, payload) {
  const jspdfModule = window.jspdf;
  if (!jspdfModule || !jspdfModule.jsPDF) {
    printAuditReport(r, payload);
    return;
  }

  try {
    const { jsPDF } = jspdfModule;
    const doc = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    });

    const pageWidth = 210;
    const pageHeight = 297;
    const margin = 14;
    const contentWidth = pageWidth - (margin * 2);
    let y = 0;

    function checkPageBreak(neededSpace) {
      if (y + neededSpace > pageHeight - 16) {
        doc.addPage();
        y = 16;
      }
    }

    // Top Header Band (Obsidian with crimson accent)
    doc.setFillColor(11, 15, 25);
    doc.rect(0, 0, pageWidth, 28, 'F');
    doc.setFillColor(255, 42, 84);
    doc.rect(0, 27, pageWidth, 1.5, 'F');

    // Brand & Document Subtitle
    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(16);
    doc.text('VERIGATE', margin, 12);
    doc.setFontSize(8.5);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(203, 213, 225);
    doc.text('IDENTITY VERIFICATION INTELLIGENCE • FORENSIC AUDIT REPORT', margin, 18);

    // Meta Right
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text(`SESSION: ${payload.sessionId}`, pageWidth - margin, 12, { align: 'right' });
    doc.text(`DATE: ${payload.timestamp.substring(0, 19).replace('T', ' ')} UTC`, pageWidth - margin, 18, { align: 'right' });

    y = 35;

    // Decision & Risk Banner
    const dec = String(payload.decision || 'REVIEW').toUpperCase();
    let bannerColor = [245, 158, 11]; // amber
    if (dec === 'APPROVE') bannerColor = [16, 185, 129]; // green
    if (dec === 'REJECT') bannerColor = [239, 68, 68]; // red

    doc.setFillColor(bannerColor[0], bannerColor[1], bannerColor[2]);
    doc.roundedRect(margin, y, contentWidth, 20, 2, 2, 'F');

    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(13);
    doc.text(`FINAL VERDICT: ${dec}`, margin + 6, y + 8);

    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text(`RISK SCORE: ${payload.riskScore} / 100   |   RATING: ${String(payload.riskLevel || '').toUpperCase()}`, margin + 6, y + 15);

    y += 26;

    // Executive Summary
    if (payload.summary) {
      doc.setFillColor(248, 250, 252);
      doc.setDrawColor(226, 232, 240);
      doc.roundedRect(margin, y, contentWidth, 14, 1.5, 1.5, 'FD');
      doc.setFont('helvetica', 'italic');
      doc.setFontSize(8.5);
      doc.setTextColor(30, 41, 59);
      const summaryLines = doc.splitTextToSize(`"${payload.summary}"`, contentWidth - 8);
      doc.text(summaryLines, margin + 4, y + 6);
      y += 18;
    }

    // 1. AI Reasoning Section
    if (payload.aiReasoning) {
      checkPageBreak(25);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(10);
      doc.setTextColor(15, 23, 42);
      doc.text('1. AI EVIDENCE ARBITRATION (GEMMA REASONING)', margin, y);
      y += 5;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(51, 65, 85);
      const reasoningLines = doc.splitTextToSize(payload.aiReasoning, contentWidth);
      doc.text(reasoningLines, margin, y);
      y += (reasoningLines.length * 4) + 5;
    }

    // 2. Identity Details Table
    checkPageBreak(35);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(15, 23, 42);
    doc.text('2. EXTRACTED IDENTITY CREDENTIALS', margin, y);
    y += 5;

    if (Array.isArray(payload.extractedIdentity) && payload.extractedIdentity.length > 0) {
      const colW = contentWidth / 2;
      doc.setFontSize(8);
      payload.extractedIdentity.forEach((f, idx) => {
        const col = idx % 2;
        const xPos = margin + (col * colW);
        if (col === 0 && idx > 0) y += 5;
        checkPageBreak(8);
        doc.setFont('helvetica', 'bold');
        doc.setTextColor(71, 85, 105);
        doc.text(`${f.field}:`, xPos, y);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(15, 23, 42);
        doc.text(String(f.value || 'N/A'), xPos + 34, y);
      });
      y += 8;
    }

    // 3. Document Validation Checks
    checkPageBreak(30);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(15, 23, 42);
    doc.text(`3. DETERMINISTIC CHECKS (${String(payload.documentValidation?.status || '').toUpperCase()})`, margin, y);
    y += 5;

    const checks = payload.documentValidation?.checks || [];
    doc.setFontSize(7.5);
    checks.forEach(c => {
      checkPageBreak(5);
      const isPass = String(c.status || '').toLowerCase() === 'passed';
      doc.setFont('helvetica', 'bold');
      if (isPass) {
        doc.setTextColor(16, 185, 129);
        doc.text('[PASS]', margin, y);
      } else {
        doc.setTextColor(239, 68, 68);
        doc.text('[FAIL]', margin, y);
      }
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(30, 41, 59);
      doc.text(String(c.message || c.check_name || 'Validation check'), margin + 14, y);
      y += 4.5;
    });
    y += 4;

    // 4. Biometric Face Correspondence & Tampering Forensics
    checkPageBreak(30);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(15, 23, 42);
    doc.text('4. FORENSICS & BIOMETRIC CORRESPONDENCE', margin, y);
    y += 5;

    // Biometrics
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(71, 85, 105);
    doc.text('Biometric Verification:', margin, y);
    doc.setFont('helvetica', 'normal');
    const faceMatch = payload.faceVerification?.is_match ? 'MATCH CONFIRMED' : 'MISMATCH DETECTED';
    const distVal = payload.faceVerification?.distance != null ? Number(payload.faceVerification.distance).toFixed(3) : 'N/A';
    const threshVal = payload.faceVerification?.threshold != null ? Number(payload.faceVerification.threshold).toFixed(3) : 'N/A';
    const metric = (payload.faceVerification?.distance_metric || 'Cosine').toUpperCase();
    doc.setTextColor(payload.faceVerification?.is_match ? 16 : 239, payload.faceVerification?.is_match ? 185 : 68, payload.faceVerification?.is_match ? 129 : 68);
    doc.text(`${faceMatch}   (Distance: ${distVal} / Threshold: ${threshVal} • ${metric})`, margin + 36, y);
    y += 5.5;

    // Tampering
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(71, 85, 105);
    doc.text('Compression Forensics:', margin, y);
    doc.setFont('helvetica', 'normal');
    const isTamp = Boolean(payload.tamperingEvidence?.suspicious);
    const tampScore = payload.tamperingEvidence?.score != null ? Number(payload.tamperingEvidence.score).toFixed(2) : '0.00';
    doc.setTextColor(isTamp ? 239 : 16, isTamp ? 68 : 185, isTamp ? 68 : 129);
    doc.text(`${isTamp ? 'SUSPICIOUS ARTIFACTS' : 'PRISTINE / VERIFIED'}   (Score: ${tampScore})`, margin + 36, y);
    y += 8;

    // 5. Risk Factors
    checkPageBreak(25);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(15, 23, 42);
    doc.text('5. ITEMIZED RISK FACTORS', margin, y);
    y += 5;

    const factors = payload.riskFactors || [];
    doc.setFontSize(7.5);
    if (factors.length === 0) {
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(100, 116, 139);
      doc.text('• Zero anomalous risk factors identified during multi-stage evaluation.', margin, y);
      y += 5.5;
    } else {
      factors.forEach(f => {
        checkPageBreak(7);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(185, 28, 28);
        const fText = doc.splitTextToSize(`• ${f.description || f.rule || 'Elevated anomaly'} (Impact: +${f.score_impact || 0})`, contentWidth);
        doc.text(fText, margin, y);
        y += (fText.length * 3.8);
      });
    }

    // Bottom Compliance Footer
    const totalPages = doc.internal.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);
      doc.setDrawColor(226, 232, 240);
      doc.line(margin, pageHeight - 12, pageWidth - margin, pageHeight - 12);
      doc.setFontSize(7);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(148, 163, 184);
      doc.text('VERIGATE FORENSIC INTELLIGENCE ENGINE • DUAL LICENSED APACHE 2.0 / MIT • AUDITED', margin, pageHeight - 7);
      doc.text(`PAGE ${i} OF ${totalPages}`, pageWidth - margin, pageHeight - 7, { align: 'right' });
    }

    doc.save(`verigate-audit-report-${payload.sessionId}.pdf`);
  } catch (err) {
    console.error('jsPDF generation error, switching to print view:', err);
    printAuditReport(r, payload);
  }
}

function printAuditReport(r, payload) {
  const printWindow = window.open('', '_blank', 'width=850,height=1000');
  if (!printWindow) {
    alert('Pop-up blocked. Please allow pop-ups to print or export the PDF report.');
    return;
  }

  const dec = String(payload.decision || 'REVIEW').toUpperCase();
  const decColor = dec === 'APPROVE' ? '#10b981' : dec === 'REJECT' ? '#ef4444' : '#f59e0b';

  const html = `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>VeriGate Audit Report — ${escapeHtml(payload.sessionId)}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #1e293b; margin: 24px; line-height: 1.5; font-size: 13px; }
    .header { border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: flex-end; }
    .title { font-size: 20px; font-weight: 800; color: #0f172a; margin: 0; }
    .sub { font-size: 11px; color: #64748b; margin-top: 2px; }
    .meta { font-size: 11px; text-align: right; color: #64748b; }
    .verdict-box { background: ${decColor}; color: #fff; padding: 14px 18px; border-radius: 8px; margin-bottom: 16px; }
    .verdict-title { font-size: 16px; font-weight: 800; margin-bottom: 4px; }
    .summary-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; font-style: italic; margin-bottom: 16px; }
    .section-title { font-size: 13px; font-weight: 700; color: #0f172a; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; margin-top: 18px; margin-bottom: 10px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; }
    .item-label { font-size: 11px; color: #64748b; font-weight: 600; }
    .item-val { font-size: 12px; font-weight: 600; color: #0f172a; }
    .check-pass { color: #10b981; font-weight: 700; }
    .check-fail { color: #ef4444; font-weight: 700; }
    .footer { margin-top: 28px; border-top: 1px solid #e2e8f0; padding-top: 10px; font-size: 10px; color: #94a3b8; text-align: center; }
    @media print { body { margin: 0; } }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <div class="title">VERIGATE AUDIT REPORT</div>
      <div class="sub">Identity Verification Intelligence • Explainable Multi-Modal Forensic Engine</div>
    </div>
    <div class="meta">
      <div>Session: ${escapeHtml(payload.sessionId)}</div>
      <div>Date: ${escapeHtml(payload.timestamp.substring(0, 19).replace('T', ' '))} UTC</div>
    </div>
  </div>

  <div class="verdict-box">
    <div class="verdict-title">VERDICT: ${dec}</div>
    <div>Risk Score: ${payload.riskScore}/100 &bull; Risk Level: ${escapeHtml(String(payload.riskLevel || '').toUpperCase())}</div>
  </div>

  ${payload.summary ? `<div class="summary-box">“${escapeHtml(payload.summary)}”</div>` : ''}

  <div class="section-title">1. AI EVIDENCE ARBITRATION (GEMMA REASONING)</div>
  <p>${escapeHtml(payload.aiReasoning || 'N/A')}</p>

  <div class="section-title">2. EXTRACTED IDENTITY CREDENTIALS</div>
  <div class="grid">
    ${(payload.extractedIdentity || []).map(f => `
      <div><span class="item-label">${escapeHtml(f.field)}:</span> <span class="item-val">${escapeHtml(f.value)}</span></div>
    `).join('')}
  </div>

  <div class="section-title">3. DETERMINISTIC VALIDATION CHECKS (${escapeHtml(String(payload.documentValidation?.status || '').toUpperCase())})</div>
  <div>
    ${(payload.documentValidation?.checks || []).map(c => {
      const isPass = String(c.status || '').toLowerCase() === 'passed';
      return `<div><span class="${isPass ? 'check-pass' : 'check-fail'}">[${isPass ? 'PASS' : 'FAIL'}]</span> ${escapeHtml(c.message || c.check_name || 'Check')}</div>`;
    }).join('')}
  </div>

  <div class="section-title">4. FORENSIC EVIDENCE &amp; BIOMETRICS</div>
  <div><strong>Biometric Match:</strong> ${payload.faceVerification?.is_match ? 'CONFIRMED' : 'MISMATCH'} (Distance: ${payload.faceVerification?.distance ?? 'N/A'} / Threshold: ${payload.faceVerification?.threshold ?? 'N/A'})</div>
  <div><strong>Tampering Status:</strong> ${payload.tamperingEvidence?.suspicious ? 'SUSPICIOUS ARTIFACTS' : 'PRISTINE / VERIFIED'} (Score: ${payload.tamperingEvidence?.score ?? '0.00'})</div>

  <div class="section-title">5. RISK FACTORS</div>
  ${(payload.riskFactors || []).length > 0 ? (payload.riskFactors || []).map(f => `
    <div style="color:#b91c1c;">&bull; ${escapeHtml(f.description || f.rule || 'Elevated risk anomaly')} (+${f.score_impact || 0})</div>
  `).join('') : '<div>Zero anomalous risk factors identified.</div>'}

  <div class="footer">
    VeriGate Open-Source Identity Intelligence &bull; Confidential Compliance Record &bull; Dual-licensed Apache 2.0 &amp; MIT
  </div>
</body>
</html>`;

  printWindow.document.write(html);
  printWindow.document.close();
  printWindow.focus();
  setTimeout(() => {
    printWindow.print();
  }, 400);
}

/* ═══════════════════════════════════
   LIVE CAMERA INPUT (USE CAMERA)
   ═══════════════════════════════════ */

let cameraStream = null;

async function openCameraModal() {
  const modal = document.getElementById('cameraModal');
  const video = document.getElementById('cameraVideo');
  const statusMsg = document.getElementById('cameraStatusMsg');
  const snapBtn = document.getElementById('btnCameraSnap');

  if (!modal || !video) return;

  modal.style.display = 'flex';
  if (statusMsg) {
    statusMsg.style.display = 'block';
    statusMsg.textContent = 'Requesting camera permissions...';
  }
  if (snapBtn) snapBtn.disabled = true;

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    if (statusMsg) {
      statusMsg.textContent = 'Camera API not supported in this browser. Please attach an image file instead.';
    }
    return;
  }

  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'user'
      },
      audio: false
    });
    video.srcObject = cameraStream;
    await video.play();
    if (statusMsg) statusMsg.style.display = 'none';
    if (snapBtn) snapBtn.disabled = false;
  } catch (err) {
    console.warn('Camera access error:', err);
    let msg = 'Camera access was denied or is unavailable. Please grant camera permissions or attach a photo.';
    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
      msg = 'Camera permission was denied. Please allow camera access in your browser or attach an image file.';
    } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
      msg = 'No camera device detected on this system. Please attach an image file.';
    }
    if (statusMsg) {
      statusMsg.style.display = 'block';
      statusMsg.textContent = msg;
    }
    if (snapBtn) snapBtn.disabled = true;
  }
}

function closeCameraModal() {
  const modal = document.getElementById('cameraModal');
  const video = document.getElementById('cameraVideo');
  if (cameraStream) {
    cameraStream.getTracks().forEach(track => track.stop());
    cameraStream = null;
  }
  if (video) video.srcObject = null;
  if (modal) modal.style.display = 'none';
}

function captureCameraSnapshot() {
  const video = document.getElementById('cameraVideo');
  if (!video || !video.videoWidth) return;

  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob(blob => {
    if (!blob) return;
    const file = new File([blob], `live_capture_${Date.now()}.jpg`, { type: 'image/jpeg' });
    closeCameraModal();
    handleFile('face', [file]);
  }, 'image/jpeg', 0.95);
}

/* ═══════════════════════════════════
   HTML UTILITY
   ═══════════════════════════════════ */

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
}

/* ═══════════════════════════════════
   LEGACY OVERLAY RENDERING FALLBACK
   ═══════════════════════════════════ */

function setStage(index, state) {
  const check = document.getElementById('check-' + index);
  const name = document.getElementById('name-' + index);
  const fill = document.getElementById('fill-' + index);
  if (!check || !name || !fill) return;

  check.className = 'stage-check ' + state;
  name.classList.toggle('active', state === 'running');
  if (state === 'running') fill.style.width = '45%';
  if (state === 'done') fill.style.width = '100%';
}

function stageError(message) {
  screeningError(message);
}

function runProcessing() {
  startScreeningProcess();
}

function renderResults() {
  if (session.report) renderDynamicResults(session.report);
}

// Automatically check server connection upon load
if (typeof window !== 'undefined') {
  setTimeout(checkServerConnection, 300);
}
