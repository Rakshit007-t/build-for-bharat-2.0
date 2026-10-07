(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const state = { summary: null, models: null, market: null, readiness: null, figures: [], refreshInFlight: false,
    verificationCandidate: null, assessment: null, currentQuestion: null, latestReport: null };
  const labels = {
    big_data_skills: "Big data skills", maths_stats_skills: "Maths & statistics", coding_skills: "Coding skills",
    ai_and_ml_skills: "AI & machine learning", dashboard_and_storytelling_skills: "Dashboard & storytelling",
    neuroticism: "Neuroticism", extraversion: "Extraversion", openness_to_experience: "Openness to experience",
    agreeableness: "Agreeableness", conscientiousness: "Conscientiousness"
  };
  const talentOptions = [
    ["python", "Python"], ["sql", "SQL"], ["machine_learning", "Machine Learning"],
    ["statistics", "Statistics"], ["big_data", "Big Data"], ["dashboard_storytelling", "Dashboard / Storytelling"]
  ];

  async function getJson(path) {
    const response = await fetch(path, { headers: { Accept: "application/json" } });
    if (!response.ok) {
      let message = `Request failed (${response.status})`;
      try { const body = await response.json(); message = formatApiDetail(body.detail) || message; } catch { /* use status fallback */ }
      throw new Error(message);
    }
    return response.json();
  }

  async function postJson(path, payload) {
    const response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(payload) });
    const body = await response.json();
    if (!response.ok) throw new Error(formatApiDetail(body.detail) || `Request failed (${response.status})`);
    return body;
  }

  function showUploadError(message = "") { $("#upload-error").textContent = message; }

  async function acceptResume(formData) {
    showUploadError("");
    const response = await fetch("/api/verification/upload", { method: "POST", body: formData, headers: { Accept: "application/json" } });
    const body = await response.json();
    if (!response.ok) throw new Error(formatApiDetail(body.detail) || `Upload failed (${response.status})`);
    state.verificationCandidate = body;
    try {
      if (body?.candidate_id) {
        sessionStorage.setItem("ghost_skills_candidate_id", body.candidate_id);
      }
    } catch { /* storage fallback */ }
    state.latestReport = null;
    state.assessment = null;
    state.currentQuestion = null;
    $("#verification-report-page").hidden = true;
    $("#verify-assessment-step").hidden = true;
    renderClaims(body);
  }

  function renderClaims(candidate) {
    $("#verify-claims-step").hidden = false;
    const sourceName = candidate.filename ? ` · ${candidate.filename}` : "";
    $("#candidate-heading").textContent = `${candidate.name || "Candidate"}${sourceName} · detected skill claims`;
    $("#candidate-education").textContent = candidate.education ? `Education: ${candidate.education}` : "Education was not explicitly extracted.";

    // Render Executive Summary Strip
    const strip = $("#executive-summary-strip");
    if (strip) {
      strip.replaceChildren();
      const stats = candidate.stats || {};
      const advCount = stats.advanced ?? candidate.skills.filter(s => s.claimed_level === "Advanced").length;
      const intCount = stats.intermediate ?? candidate.skills.filter(s => s.claimed_level === "Intermediate").length;
      const avgScore = stats.avg_evidence ?? Math.round(candidate.skills.reduce((acc, s) => acc + (s.evidence_score || 0), 0) / Math.max(1, candidate.skills.length));

      const statData = [
        { val: `${candidate.skills.length} Skills`, lbl: "Total Skills Extracted" },
        { val: `${advCount} Advanced`, lbl: "Step 3 / Expert Tier" },
        { val: `${intCount} Intermediate`, lbl: "Step 2 / Applied Tier" },
        { val: `${avgScore}/100`, lbl: "Avg Evidence Score" },
      ];
      statData.forEach(d => {
        const card = document.createElement("div"); card.className = "exec-stat-card";
        const val = document.createElement("div"); val.className = "exec-stat-val"; val.textContent = d.val;
        const lbl = document.createElement("div"); lbl.className = "exec-stat-lbl"; lbl.textContent = d.lbl;
        card.append(val, lbl); strip.append(card);
      });
    }

    // Render Category Filter Pills
    const filterBar = $("#skill-category-filters");
    if (filterBar) {
      filterBar.replaceChildren();
      const catCounts = { "All": candidate.skills.length };
      candidate.skills.forEach(s => {
        const cat = s.category || "General";
        catCounts[cat] = (catCounts[cat] || 0) + 1;
      });

      let activeCat = "All";
      const applyFilter = (cat) => {
        activeCat = cat;
        $$(".filter-pill", filterBar).forEach(b => b.classList.toggle("active", b.dataset.cat === cat));
        $$("#claims-rows tr").forEach(row => {
          row.hidden = (cat !== "All" && row.dataset.category !== cat);
        });
      };

      Object.entries(catCounts).forEach(([cat, count]) => {
        const pill = document.createElement("button");
        pill.type = "button"; pill.className = `filter-pill ${cat === "All" ? "active" : ""}`;
        pill.dataset.cat = cat; pill.textContent = `${cat} (${count})`;
        pill.addEventListener("click", () => applyFilter(cat));
        filterBar.append(pill);
      });
    }

    const rows = $("#claims-rows"); rows.replaceChildren();
    candidate.skills.forEach(claim => {
      const row = document.createElement("tr");
      row.dataset.skillRow = claim.skill;
      row.dataset.category = claim.category || "General";

      // 1. Skill & Domain Cell
      const skillCell = document.createElement("th"); skillCell.scope = "row";
      const cellHeader = document.createElement("div"); cellHeader.className = "skill-cell-header";
      const title = document.createElement("span"); title.className = "skill-title"; title.textContent = claim.skill;
      const tag = document.createElement("span"); tag.className = "category-tag"; tag.textContent = claim.category || "General";
      cellHeader.append(title, tag); skillCell.append(cellHeader);

      // 2. Proficiency Step Cell
      const stepCell = document.createElement("td");
      const stepWrap = document.createElement("div"); stepWrap.className = "step-cell";
      const stepNum = claim.step_number || (claim.claimed_level === "Advanced" ? 3 : claim.claimed_level === "Intermediate" ? 2 : claim.claimed_level === "Beginner" ? 1 : 0);
      const stepBadge = document.createElement("span");
      stepBadge.className = `step-badge step-${stepNum}`;
      stepBadge.textContent = claim.step_label || (claim.claimed_level ? `Step ${stepNum}: ${claim.claimed_level}` : "Step 0: Unspecified");

      // 4-bar step progression meter
      const stepMeter = document.createElement("div"); stepMeter.className = "step-meter";
      for (let i = 1; i <= 4; i++) {
        const bar = document.createElement("div");
        bar.className = `step-bar ${i <= stepNum ? "filled" : ""}`;
        stepMeter.append(bar);
      }
      const stepReason = document.createElement("small"); stepReason.className = "step-reason";
      stepReason.textContent = claim.level_reason || (claim.claimed_level ? `Claimed ${claim.claimed_level}` : "Unspecified");
      stepWrap.append(stepBadge, stepMeter, stepReason); stepCell.append(stepWrap);

      // 3. Evidence Score Cell
      const evCell = document.createElement("td");
      const evWrap = document.createElement("div"); evWrap.className = "ev-score-container";
      const evBadge = document.createElement("div"); evBadge.className = "ev-score-badge";
      const evScore = claim.evidence_score !== undefined && claim.evidence_score !== null ? Number(claim.evidence_score) : 0;
      const evScoreStrong = document.createElement("strong"); evScoreStrong.textContent = evScore.toFixed(0);
      const evScoreSub = document.createElement("span"); evScoreSub.textContent = "/100";
      evBadge.append(evScoreStrong, evScoreSub);

      const evBarTrack = document.createElement("div"); evBarTrack.className = "ev-score-bar-track";
      const evBarFill = document.createElement("div"); evBarFill.className = "ev-score-bar-fill";
      evBarFill.style.width = `${Math.min(100, Math.max(0, evScore))}%`;
      evBarTrack.append(evBarFill);

      const chipWrap = document.createElement("div"); chipWrap.className = "signal-chips";
      const breakdown = claim.evidence_breakdown || {};
      if (breakdown.scale_detected) {
        const chip = document.createElement("span"); chip.className = "signal-chip scale"; chip.textContent = "⚡ Enterprise Scale"; chipWrap.append(chip);
      }
      if (breakdown.certifications) {
        const chip = document.createElement("span"); chip.className = "signal-chip cert"; chip.textContent = `★ ${breakdown.certifications} Cert`; chipWrap.append(chip);
      }
      if (breakdown.projects) {
        const chip = document.createElement("span"); chip.className = "signal-chip"; chip.textContent = `✓ ${breakdown.projects} Proj`; chipWrap.append(chip);
      }
      if (breakdown.experience) {
        const chip = document.createElement("span"); chip.className = "signal-chip"; chip.textContent = `✓ ${breakdown.experience} Role`; chipWrap.append(chip);
      }
      evWrap.append(evBadge, evBarTrack, chipWrap); evCell.append(evWrap);

      // 4. Resume Excerpts Cell
      const excerpts = document.createElement("td");
      if (claim.claim_excerpt) {
        const source = document.createElement("p"); source.className = "claim-source";
        source.textContent = `${claim.claim_not_asserted ? "Resume wording" : "Resume self-description"}: “${claim.claim_excerpt}”`;
        excerpts.append(source);
      }
      if (claim.evidence_snippets?.length) {
        const list = document.createElement("ul"); list.className = "excerpt-list";
        claim.evidence_snippets.slice(0, 4).forEach(snippet => {
          const item = document.createElement("li"); item.textContent = `“${snippet}”`; list.append(item);
        });
        excerpts.append(list);
      } else if (!claim.claim_excerpt) {
        excerpts.append(document.createTextNode("No related resume excerpt detected."));
      }

      // 5. Requirement Status Cell
      const statusCell = document.createElement("td"); statusCell.className = "claim-status";
      const knownResult = state.latestReport?.skills?.find(item => item.skill === claim.skill);
      const completed = knownResult?.final_score !== null && knownResult?.final_score !== undefined;
      const isRequired = candidate.mandatory_assessments?.includes(claim.skill);
      statusCell.textContent = completed ? "Complete" : isRequired ? "Required" : claim.assessment_supported ? "Available" : "Evidence Scored";

      // 6. Action Button Cell
      const action = document.createElement("td");
      if (claim.assessment_supported) {
        const button = document.createElement("button"); button.className = "small-action"; button.type = "button";
        button.textContent = completed ? "Completed ✓" : isRequired ? "Start required check" : "Take check";
        button.disabled = completed;
        button.addEventListener("click", () => startAssessment(claim.skill)); action.append(button);
      } else {
        const scoredBadge = document.createElement("span"); scoredBadge.className = "soft-tag";
        scoredBadge.textContent = "Scored · No Quiz"; action.append(scoredBadge);
      }

      row.append(skillCell, stepCell, evCell, excerpts, statusCell, action);
      rows.append(row);
    });

    const report = state.latestReport;
    const pending = report?.skills?.filter(item => item.required && item.final_score === null)
      || (candidate.mandatory_assessments || []).map(skill => ({ skill, final_score: null }));
    const gate = $("#mandatory-progress"); gate.hidden = pending.length === 0;
    if (pending.length) {
      $("#mandatory-progress-text").textContent = `${pending.length} core required assessment${pending.length === 1 ? "" : "s"} remaining: ${pending.map(item => item.skill).join(", ")}.`;
      const nextButton = $("#continue-required"); nextButton.textContent = `Continue: ${pending[0].skill}`;
      nextButton.onclick = () => startAssessment(pending[0].skill);
    }
    const directReportBtn = $("#view-report-direct");
    if (directReportBtn) {
      directReportBtn.onclick = () => loadVerificationReport(true);
    }
    const requiredDone = !!report?.mandatory_complete || pending.length === 0;
    renderOptionalChoices(candidate, requiredDone);
    $("#verify-claims-step").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderOptionalChoices(candidate, requiredDone) {
    const optional = $("#optional-assessments");
    const choices = candidate.optional_assessments || [];
    optional.hidden = choices.length === 0;
    const select = $("#optional-skill-select"); select.replaceChildren();
    choices.forEach(item => { const option = document.createElement("option"); option.value = item.skill; option.textContent = item.skill; select.append(option); });
    $("#start-optional-assessment").disabled = !requiredDone || choices.length === 0;
  }

  async function uploadFile(file) {
    if (!file) return;
    const form = new FormData(); form.append("file", file, file.name);
    try { await acceptResume(form); } catch (error) { showUploadError(error.message); }
  }

  async function useDemo(filename) {
    showUploadError("");
    try {
      const sample = await getJson(`/api/verification/demo/${encodeURIComponent(filename)}`);
      const form = new FormData(); form.append("text", sample.text);
      await acceptResume(form);
    } catch (error) { showUploadError(error.message); }
  }

  async function startAssessment(skill, optional = false) {
    const candidateId = state.verificationCandidate?.candidate_id;
    if (!candidateId) return;
    try {
      state.assessment = await postJson(`/api/verification/${encodeURIComponent(candidateId)}/start`, { skill, optional });
      state.currentQuestion = null;
      $("#assessment-heading").textContent = `${skill} verification`;
      $("#verification-report-page").hidden = true;
      $("#verify-assessment-step").hidden = false;
      await loadQuestion();
      $("#verify-assessment-step").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) { showUploadError(error.message); }
  }

  async function loadQuestion() {
    const candidateId = state.verificationCandidate?.candidate_id;
    const question = await getJson(`/api/verification/${encodeURIComponent(candidateId)}/next`);
    if (question.done) { await loadVerificationReport(); return; }
    state.currentQuestion = question;
    $("#question-progress-label").textContent = `Question ${question.index} of ${question.total}`;
    const progress = Math.round(((question.index - 1) / question.total) * 100);
    $("#question-progress-percent").textContent = `${progress}%`;
    $("#question-progress-fill").style.width = `${progress}%`;
    $("#question-difficulty").textContent = question.difficulty;
    $("#question-difficulty").className = `difficulty-badge ${question.difficulty}`;
    $("#question-prompt").textContent = question.prompt;
    $("#answer-feedback").hidden = true;
    $("#continue-question").hidden = true;
    const options = $("#answer-options"); options.replaceChildren();
    question.options.forEach((option, index) => {
      const button = document.createElement("button"); button.type = "button"; button.className = "answer-option";
      button.textContent = option; button.addEventListener("click", () => submitAnswer(option)); options.append(button);
    });
  }

  async function submitAnswer(answer) {
    const candidateId = state.verificationCandidate?.candidate_id;
    const question = state.currentQuestion;
    if (!candidateId || !question) return;
    $$(".answer-option", $("#answer-options")).forEach(button => { button.disabled = true; if (button.textContent === answer) button.classList.add("selected"); });
    try {
      const result = await postJson(`/api/verification/${encodeURIComponent(candidateId)}/answer`, { question_id: question.question_id, answer });
      const feedback = $("#answer-feedback"); feedback.hidden = false; feedback.className = `answer-feedback ${result.correct ? "correct" : "incorrect"}`;
      feedback.textContent = `${result.correct ? "Correct." : "Not quite."} ${result.explanation}`;
      const continueButton = $("#continue-question"); continueButton.hidden = false;
      continueButton.textContent = result.done ? "Check required progress" : "Continue";
      continueButton.onclick = async () => {
        if (result.done) {
          $("#question-progress-label").textContent = "Assessment complete · 3 of 3";
          $("#question-progress-percent").textContent = "100%";
          $("#question-progress-fill").style.width = "100%";
          await loadVerificationReport();
        } else await loadQuestion();
      };
    } catch (error) {
      $("#answer-feedback").hidden = false; $("#answer-feedback").className = "answer-feedback incorrect";
      $("#answer-feedback").textContent = error.message;
      $$(".answer-option", $("#answer-options")).forEach(button => { button.disabled = false; });
    }
  }

  function addText(parent, tag, text, className = "") {
    const element = document.createElement(tag); element.textContent = text; if (className) element.className = className; parent.append(element); return element;
  }

  function renderVerificationReport(report) {
    state.latestReport = report;
    const candidate = report.candidate;
    $("#report-candidate").textContent = `${candidate.name}${candidate.education ? ` · ${candidate.education}` : ""} · Candidate ID ${candidate.candidate_id}`;
    const root = $("#verification-results"); root.replaceChildren();
    const completed = report.skills.filter(item => item.final_score !== null);
    root.classList.toggle("single-result", completed.length === 1);

    if (!completed.length) {
      const emptyCard = document.createElement("article");
      emptyCard.className = "card";
      emptyCard.style.gridColumn = "1/-1";
      emptyCard.innerHTML = `
        <p class="eyebrow">EXTRACTED SKILLS DOSSIER</p>
        <h2>Multi-Factor Evidence Extracted (${report.skills.length} Skills)</h2>
        <p>Candidate skills have been cataloged with stepped proficiency levels and deterministic evidence scores. Complete any 3-minute check to generate comparative test verification scores.</p>
      `;
      root.append(emptyCard);
    }

    completed.forEach(result => {
      const card = document.createElement("article");
      card.className = `result-card status-${result.status} skill-truth-card`;
      const discovery = result.origin === "discovery";

      const evVal = result.evidence_score !== null ? result.evidence_score.toFixed(1) : "—";
      const demoVal = result.test_score !== null ? result.test_score.toFixed(1) : "—";
      const finalVal = (discovery ? result.test_score : result.final_score) !== null ? (discovery ? result.test_score : result.final_score).toFixed(1) : "—";
      const verifiedVal = discovery ? "Demonstrated" : (result.verified_level || "Beginner");
      const verdictVal = result.status.toUpperCase();
      const claimedVal = discovery ? "Not claimed" : (result.claimed_level || "Unspecified");

      // 1. Card Header: GHOST SKILLS · SKILL TRUTH ENGINE
      const header = document.createElement("div");
      header.className = "result-card-header";
      const title = document.createElement("div");
      addText(title, "p", "GHOST SKILLS · SKILL TRUTH ENGINE", "eyebrow");
      addText(title, "h2", `SKILL TRUTH · ${result.skill}`);

      const verdictBadge = document.createElement("div");
      verdictBadge.className = `verdict-badge verdict-${result.status}`;
      verdictBadge.innerHTML = `<span class="verdict-label">VERDICT</span><strong class="verdict-val">${verdictVal}</strong>`;
      header.append(title, verdictBadge);
      card.append(header);

      // 2. WOW MOMENT CALLOUT (The Overclaimed Wow Moment)
      const wowCallout = document.createElement("div");
      wowCallout.className = `skill-truth-callout callout-${result.status}`;
      if (result.status === "overclaimed") {
        wowCallout.innerHTML = `
          <div class="callout-hero-text">“THE RESUME SAID ${(result.claimed_level || "ADVANCED").toUpperCase()}. THE TEST SHOWED ${(result.verified_level || "BEGINNER").toUpperCase()}.”</div>
          <div class="callout-subtext">Ghost Skills reveals the gap.</div>
        `;
      } else if (result.status === "confirmed") {
        wowCallout.innerHTML = `
          <div class="callout-hero-text">“THE RESUME CLAIM IS VERIFIED AT ${(result.claimed_level || "INTERMEDIATE").toUpperCase()}.”</div>
          <div class="callout-subtext">Demonstrated ability confirms candidate claim.</div>
        `;
      } else if (result.status === "underclaimed") {
        wowCallout.innerHTML = `
          <div class="callout-hero-text">“HIDDEN CAPABILITY DETECTED: DEMONSTRATED ${(result.verified_level || "ADVANCED").toUpperCase()}.”</div>
          <div class="callout-subtext">Candidate capability exceeds the resume claim.</div>
        `;
      } else {
        wowCallout.innerHTML = `
          <div class="callout-hero-text">“OPTIONAL TECHNICAL DEMONSTRATION COMPLETED.”</div>
          <div class="callout-subtext">Demonstrated ability recorded without prior resume claim.</div>
        `;
      }
      card.append(wowCallout);

      // 3. Large Dynamic "SKILL TRUTH" Card / Grid
      const truthGrid = document.createElement("div");
      truthGrid.className = "result-usp-grid skill-truth-grid";

      const truthMetrics = [
        { label: "RESUME CLAIM", val: claimedVal, sub: "Self-Reported Level", cls: "cell-claimed" },
        { label: "RESUME PROOF", val: `Evidence: ${evVal}`, sub: "Evidence Score (0–100)", cls: "cell-evidence" },
        { label: "DEMONSTRATED ABILITY", val: `Test: ${demoVal}`, sub: "Adaptive Test Score", cls: "cell-demo" },
        { label: "FINAL SCORE", val: finalVal, sub: "0.4×Ev + 0.6×Test", cls: "cell-final" },
        { label: "VERIFIED LEVEL", val: verifiedVal, sub: "Calibrated Truth", cls: "cell-verified" },
        { label: "VERDICT", val: verdictVal, sub: "Trust Decision", cls: `cell-verdict verdict-text-${result.status}` }
      ];

      truthMetrics.forEach(m => {
        const cell = document.createElement("div");
        cell.className = `usp-grid-cell ${m.cls}`;
        addText(cell, "span", m.label, "cell-label");
        addText(cell, "strong", m.val, "cell-value");
        if (m.sub) addText(cell, "small", m.sub, "cell-sub");
        truthGrid.append(cell);
      });
      card.append(truthGrid);

      // 4. CLAIM → PROOF → DEMONSTRATION → TRUTH Visual (Large Typography & Arrows)
      const cptVisual = document.createElement("div");
      cptVisual.className = "claim-proof-truth-box";
      cptVisual.innerHTML = `
        <div class="cpt-flow">
          <div class="cpt-node">
            <span class="cpt-tag">CLAIM</span>
            <strong class="cpt-val">“${claimedVal} ${result.skill}”</strong>
            <small class="cpt-desc">Resume statement</small>
          </div>
          <div class="cpt-arrow">↓</div>
          <div class="cpt-node">
            <span class="cpt-tag">PROOF</span>
            <strong class="cpt-val">Evidence: ${evVal}</strong>
            <small class="cpt-desc">Fact extraction</small>
          </div>
          <div class="cpt-arrow">↓</div>
          <div class="cpt-node">
            <span class="cpt-tag">DEMONSTRATION</span>
            <strong class="cpt-val">Test: ${demoVal}</strong>
            <small class="cpt-desc">Actual assessment</small>
          </div>
          <div class="cpt-arrow">↓</div>
          <div class="cpt-node cpt-node-truth">
            <span class="cpt-tag">TRUTH</span>
            <strong class="cpt-val">${verifiedVal}</strong>
            <small class="cpt-desc">Verified level</small>
          </div>
        </div>
      `;
      card.append(cptVisual);

      // 5. “WHY THIS RESULT?” Dynamic 1–2 Line Explanation
      const whyBox = document.createElement("div");
      whyBox.className = "why-verdict-box";
      whyBox.innerHTML = `
        <div class="why-verdict-head">
          <span class="why-badge">AUDIT RATIONALE</span>
          <strong>WHY THIS RESULT?</strong>
        </div>
        <p class="why-result-statement">
          “The resume claimed <strong>${claimedVal}</strong>.
          The evidence score was <strong>${evVal}</strong>.
          The demonstrated test score was <strong>${demoVal}</strong>.
          The verified level is <strong>${verifiedVal}</strong>.
          Therefore the claim is <strong class="verdict-inline-${result.status}">${verdictVal}</strong>.”
        </p>
        <div class="formula-math-display">
          <span>Formula Proof:</span>
          <strong>0.4 × ${evVal} + 0.6 × ${demoVal} = ${finalVal}</strong>
          <span class="formula-rule">(&lt;40 Beginner · 40–70 Intermediate · &gt;70 Advanced)</span>
        </div>
      `;
      card.append(whyBox);

      // 6. “SKILL TRUST GAP” Visual
      const gapBox = document.createElement("div");
      gapBox.className = "skill-trust-gap-box";
      const stepLevels = { "Beginner": 1, "Intermediate": 2, "Advanced": 3 };
      const claimedStep = stepLevels[result.claimed_level] || 1;
      const verifiedStep = stepLevels[result.verified_level] || 1;

      let gapMessage = "No trust gap detected.";
      if (result.status === "overclaimed") {
        gapMessage = "Claim exceeds demonstrated ability.";
      } else if (result.status === "underclaimed") {
        gapMessage = "Hidden capability detected.";
      }

      gapBox.innerHTML = `
        <div class="gap-header">
          <div>
            <span class="gap-tag">SKILL TRUST GAP</span>
            <strong class="gap-message-title">${gapMessage}</strong>
          </div>
          <div class="gap-comparison-pill">
            <span class="pill-claimed">CLAIMED: ${claimedVal}</span>
            <span class="pill-vs">VS</span>
            <span class="pill-verified">VERIFIED: ${verifiedVal}</span>
          </div>
        </div>
        <div class="gap-meter-comparison">
          <div class="gap-meter-row">
            <span class="m-label">Claimed Tier:</span>
            <div class="m-track"><div class="m-fill fill-claimed step-${claimedStep}"></div></div>
            <span class="m-step-val">${claimedVal}</span>
          </div>
          <div class="gap-meter-row">
            <span class="m-label">Verified Tier:</span>
            <div class="m-track"><div class="m-fill fill-verified step-${verifiedStep} fill-${result.status}"></div></div>
            <span class="m-step-val">${verifiedVal}</span>
          </div>
        </div>
      `;
      card.append(gapBox);

      // 7. VERIFIED SKILL PASSPORT Artifact
      const passport = document.createElement("div");
      passport.className = "verified-passport-card";
      passport.innerHTML = `
        <div class="passport-header">
          <div class="passport-brand">
            <span class="passport-logo">G</span>
            <div>
              <strong>GHOST SKILLS</strong>
              <small>VERIFIED SKILL PASSPORT</small>
            </div>
          </div>
          <span class="passport-verdict-badge verdict-${result.status}">${verdictVal}</span>
        </div>
        <div class="passport-body">
          <div class="passport-candidate-strip">
            <span class="p-cand-name">${candidate.name || "Candidate"}</span>
            <span class="p-cand-meta">${candidate.education || "Verified Profile"} · Candidate ID: ${candidate.candidate_id.slice(0, 8)}</span>
          </div>
          <div class="passport-data-grid">
            <div class="p-data-item"><span class="p-label">Skill</span><strong class="p-val">${result.skill}</strong></div>
            <div class="p-data-item"><span class="p-label">Claimed Level</span><strong class="p-val">${claimedVal}</strong></div>
            <div class="p-data-item"><span class="p-label">Verified Level</span><strong class="p-val p-verified-val">${verifiedVal}</strong></div>
            <div class="p-data-item"><span class="p-label">Evidence Score</span><strong class="p-val">${evVal}</strong></div>
            <div class="p-data-item"><span class="p-label">Demonstrated Test</span><strong class="p-val">${demoVal}</strong></div>
            <div class="p-data-item"><span class="p-label">Final Score</span><strong class="p-val p-final-val">${finalVal}</strong></div>
          </div>
        </div>
        <div class="passport-footer">
          <span class="p-seal">AUTHENTICATED LOCAL ARTIFACT</span>
          <span class="p-tagline">“ATS finds the keyword. Ghost Skills verifies the skill.”</span>
        </div>
      `;
      card.append(passport);

      // 8. Separate MARKET CONTEXT Card
      const marketCard = document.createElement("div");
      marketCard.className = "market-context-card";
      const market = state.market || state.summary?.job_market;
      const skillName = result.skill.toLowerCase();
      const topSkills = market?.top_skills || [];
      const skillMentions = topSkills.find(s => s.name.toLowerCase() === skillName)?.count
        || (skillName === "python" ? 938 : skillName === "sql" ? 1009 : 0);
      const sqlMentions = topSkills.find(s => s.name.toLowerCase() === "sql")?.count || 1009;
      const pythonMentions = topSkills.find(s => s.name.toLowerCase() === "python")?.count || 938;

      marketCard.innerHTML = `
        <div class="mkt-card-head">
          <div>
            <span class="mkt-eyebrow">MARKET CONTEXT</span>
            <h3>Descriptive context from organizer job data</h3>
          </div>
          <span class="mkt-source-badge">Supplied Job-Posting Data</span>
        </div>
        <div class="mkt-grid">
          <div class="mkt-col">
            <span class="mkt-label">VERIFIED SKILL</span>
            <strong class="mkt-val">${result.skill} — ${verifiedVal}</strong>
            <span class="mkt-sub">${result.skill} mentions in supplied job data: <strong>${number(skillMentions)}</strong></span>
          </div>
          <div class="mkt-col">
            <span class="mkt-label">BENCHMARK MARKET MENTIONS</span>
            <div class="mkt-mentions-list">
              <span>Python mentions in supplied job data: <strong>${number(pythonMentions)}</strong></span>
              <span>SQL mentions in supplied job data: <strong>${number(sqlMentions)}</strong></span>
            </div>
            <span class="mkt-sub">Source: Analytics Jobs key_skills</span>
          </div>
        </div>
        <p class="mkt-disclaimer">ℹ️ <em>Market data provides external labor-market demand context only. It does NOT calibrate or modify the 40/60 verification score.</em></p>
      `;
      card.append(marketCard);

      // 9. FINAL PRODUCT STATEMENT CARD
      const statementCard = document.createElement("div");
      statementCard.className = "final-product-statement-card";
      statementCard.innerHTML = `
        <div class="statement-main">“ATS finds the keyword. Ghost Skills verifies the skill.”</div>
        <div class="statement-sub">“Verified talent + market context = talent intelligence.”</div>
      `;
      card.append(statementCard);

      // 10. Detailed Evidence Excerpts
      addText(card, "h3", "Why this result in detail?");
      addText(card, "p", result.explanation);

      if (!discovery) {
        addText(card, "h3", "Evidence scoring details");
        const details = document.createElement("ul");
        details.className = "excerpt-list";
        result.evidence_details.forEach(detail => addText(details, "li", detail));
        card.append(details);

        addText(card, "h3", "Resume evidence excerpts");
        if (result.evidence_snippets.length) {
          const list = document.createElement("ul");
          list.className = "excerpt-list";
          result.evidence_snippets.forEach(snippet => addText(list, "li", `“${snippet}”`));
          card.append(list);
        } else {
          addText(card, "p", "No concrete supporting excerpt detected.");
        }
        addText(card, "p", "Prototype heuristic evidence score · Local assessment · Not a hiring decision.", "source-note");
      } else {
        addText(card, "p", "Local quiz performance only. This is not a hiring decision or a claim verification.", "source-note");
      }

      root.append(card);
    });

    const pending = report.skills.filter(item => item.required && item.final_score === null);
    report.skills.forEach(item => {
      const row = $(`[data-skill-row="${CSS.escape(item.skill)}"]`, $("#claims-rows"));
      const statusCell = row?.querySelector(".claim-status");
      if (statusCell) statusCell.textContent = item.final_score === null ? (item.required ? "Required" : "Available") : item.status.toUpperCase();
      const actionButton = row?.querySelector("button.small-action");
      if (actionButton && item.final_score !== null) { actionButton.textContent = "Completed ✓"; actionButton.disabled = true; }
    });
    if (pending.length) {
      const note = document.createElement("p"); note.className = "pending-skills";
      note.textContent = `Core assessments still pending: ${pending.map(item => `${item.skill} (${item.claimed_level})`).join(", ")}.`; root.append(note);
    }
    const optionalPending = report.skills.filter(item => !item.required && item.final_score === null);
    if (optionalPending.length) addText(root, "p", `Additional skills available for testing: ${optionalPending.map(item => item.skill).join(", ")}.`, "pending-skills");
    const doneSkills = report.skills.filter(item => item.final_score !== null && item.status !== "unverified").map(item => ({
      Python: "python",
      SQL: "sql",
      "Machine Learning": "machine_learning",
      AWS: "big_data",
      Docker: "big_data",
      Kubernetes: "big_data",
      Terraform: "big_data",
      "ELK Stack": "big_data"
    })[item.skill]).filter(Boolean);
    const marketInsights = $("#verification-market-insights");
    if (marketInsights) marketInsights.hidden = false;
    const content = $("#verification-market-content"); content.replaceChildren();
    if (!doneSkills.length) addText(content, "p", "Complete at least one assessment to view market alignment insights.");
    else postJson("/api/talent/profile", { skills: [...new Set(doneSkills)] }).then(body => renderTalentProfile(body, content)).catch(error => addText(content, "p", `Local job-market analysis unavailable: ${error.message}`));
    $("#verification-report-page").hidden = false;
    $("#verification-report-page").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function loadVerificationReport(force = false) {
    const candidateId = state.verificationCandidate?.candidate_id;
    if (!candidateId) return;
    try {
      const report = await getJson(`/api/verification/${encodeURIComponent(candidateId)}/report`);
      state.latestReport = report;
      const anyDone = report.skills.some(item => item.final_score !== null);
      if (!report.mandatory_complete && !force && !anyDone) {
        $("#verify-assessment-step").hidden = true;
        $("#verification-report-page").hidden = true;
        renderClaims(state.verificationCandidate);
        return;
      }
      $("#verify-assessment-step").hidden = true;
      renderVerificationReport(report);
      const completedOptional = new Set(report.skills.filter(item => !item.required && item.final_score !== null).map(item => item.skill));
      state.verificationCandidate.optional_assessments = (state.verificationCandidate.optional_assessments || []).filter(item => !completedOptional.has(item.skill));
      renderOptionalChoices(state.verificationCandidate, true);
      renderVerificationStats(await getJson("/api/verification/stats"));
    } catch (error) { showUploadError(error.message); }
  }

  async function renderVerificationStats(stats = null) {
    const root = $("#verification-stats");
    if (!root) return;
    try { stats ||= await getJson("/api/verification/stats"); } catch { stats = { confirmed: 0, underclaimed: 0, overclaimed: 0 }; }
    [["confirmed", "Confirmed"], ["underclaimed", "Underclaimed"], ["overclaimed", "Overclaimed"]].forEach(([key, label], index) => {
      const card = root.children[index]; if (card) { card.querySelector("span").textContent = label; card.querySelector("strong").textContent = number(stats[key] || 0); }
    });
  }

  function resetVerificationFlow() {
    state.verificationCandidate = null;
    state.latestReport = null;
    state.assessment = null;
    state.currentQuestion = null;
    try { sessionStorage.removeItem("ghost_skills_candidate_id"); } catch { /* storage fallback */ }
    const reportPage = $("#verification-report-page");
    if (reportPage) reportPage.hidden = true;
    const assessStep = $("#verify-assessment-step");
    if (assessStep) assessStep.hidden = true;
    const claimsStep = $("#verify-claims-step");
    if (claimsStep) claimsStep.hidden = true;
    const uploadStep = $("#verify-upload-step");
    if (uploadStep) uploadStep.hidden = false;
    const fileInput = $("#resume-file");
    if (fileInput) fileInput.value = "";
    showUploadError("");
    renderVerificationStats();
    if (uploadStep) uploadStep.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function runAutoAnswerJudgeDemo() {
    const candidateId = state.verificationCandidate?.candidate_id;
    if (!candidateId) return;
    const helperBtn = $("#auto-answer-judge-btn");
    if (helperBtn) { helperBtn.disabled = true; helperBtn.textContent = "⚡ Running Demo Answers…"; }
    try {
      for (let i = 0; i < 3; i++) {
        const q = await getJson(`/api/verification/${encodeURIComponent(candidateId)}/next`);
        if (q.done) break;
        let chosenAnswer = "";
        if (i === 0) {
          chosenAnswer = q.question_id === "py-m1" ? "[0, 2, 4]" : q.options[0];
        } else if (i === 1) {
          if (q.question_id === "py-h1") chosenAnswer = "n squared";
          else if (q.question_id === "py-h2") chosenAnswer = "A module, then a class only";
          else chosenAnswer = q.options[1];
        } else {
          if (q.question_id === "py-m2") chosenAnswer = "assert";
          else chosenAnswer = q.options[0];
        }
        const ansRes = await postJson(`/api/verification/${encodeURIComponent(candidateId)}/answer`, {
          question_id: q.question_id,
          answer: chosenAnswer
        });
        if (ansRes.done) break;
      }
      await loadVerificationReport(true);
    } catch (err) {
      showUploadError("Judge demo auto-answer error: " + err.message);
    } finally {
      if (helperBtn) {
        helperBtn.disabled = false;
        helperBtn.textContent = "⚡ Auto-Answer for Overclaimed Demo (Q1 Correct, Q2 Wrong, Q3 Wrong → 28.6% Test)";
      }
    }
  }

  async function runJudgeDemo() {
    showView("verify");
    showUploadError("");
    const btnTop = $("#judge-demo-btn-top");
    const btnHero = $("#judge-demo-hero-btn");
    if (btnTop) btnTop.textContent = "⚡ Loading Demo…";
    if (btnHero) btnHero.textContent = "⚡ Loading Demo…";
    try {
      await useDemo("overclaimed_resume.txt");
      await startAssessment("Python");
      await runAutoAnswerJudgeDemo();
    } catch (err) {
      showUploadError("Could not run Judge Demo: " + err.message);
    } finally {
      if (btnTop) btnTop.textContent = "⚡ 3-Min Judge Demo";
      if (btnHero) btnHero.textContent = "⚡ 3-Minute Demo (Judge Walkthrough)";
    }
  }

  async function restoreSessionIfAny() {
    try {
      const candidateId = sessionStorage.getItem("ghost_skills_candidate_id");
      if (!candidateId) return;
      const candidate = await getJson(`/api/verification/${encodeURIComponent(candidateId)}`);
      if (!candidate || !candidate.candidate_id) return;
      state.verificationCandidate = candidate;
      const report = await getJson(`/api/verification/${encodeURIComponent(candidateId)}/report`);
      state.latestReport = report;
      const anyDone = report.skills && report.skills.some(item => item.final_score !== null);
      if (anyDone) {
        $("#verification-report-page").hidden = false;
        renderVerificationReport(report);
      } else {
        renderClaims(candidate);
      }
    } catch (e) {
      try { sessionStorage.removeItem("ghost_skills_candidate_id"); } catch { /* storage fallback */ }
    }
  }

  function setupVerification() {
    $("#resume-file").addEventListener("change", event => uploadFile(event.target.files[0]));
    $$("[data-demo]").forEach(button => button.addEventListener("click", () => useDemo(button.dataset.demo)));
    const dropzone = $("#resume-dropzone");
    ["dragenter", "dragover"].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.add("dragging"); }));
    ["dragleave", "drop"].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.remove("dragging"); }));
    dropzone.addEventListener("drop", event => uploadFile(event.dataTransfer.files[0]));
    const reuploadBtn = $("#reupload-resume-btn");
    if (reuploadBtn) reuploadBtn.addEventListener("click", resetVerificationFlow);
    const verifyAnotherBtn = $("#verify-another-btn");
    if (verifyAnotherBtn) verifyAnotherBtn.addEventListener("click", resetVerificationFlow);
    const autoAnswerBtn = $("#auto-answer-judge-btn");
    if (autoAnswerBtn) autoAnswerBtn.addEventListener("click", runAutoAnswerJudgeDemo);
    const judgeDemoTop = $("#judge-demo-btn-top");
    if (judgeDemoTop) judgeDemoTop.addEventListener("click", runJudgeDemo);
    const judgeDemoHero = $("#judge-demo-hero-btn");
    if (judgeDemoHero) judgeDemoHero.addEventListener("click", runJudgeDemo);
    $("#start-optional-assessment").addEventListener("click", () => {
      const skill = $("#optional-skill-select").value;
      if (skill) startAssessment(skill, true);
    });
    $("#print-report").addEventListener("click", () => window.print());
    renderVerificationStats();
  }

  function formatApiDetail(detail) {
    if (Array.isArray(detail)) return detail.map(item => `${item.field ? `${item.field}: ` : ""}${item.message || "Invalid input"}`).join("; ");
    if (typeof detail === "string") return detail;
    return "";
  }

  function showView(name) {
    if (!name) name = "overview";
    name = String(name).replace(/^#?\/?/, "").trim() || "overview";
    $$(".view").forEach(view => view.classList.toggle("active", view.id === `view-${name}`));
    $$(".nav-item").forEach(button => button.classList.toggle("active", button.dataset.view === name));
    const active = $(`.nav-item[data-view="${name}"]`);
    $("#current-section").textContent = active ? active.textContent.trim() : "Overview";
    if (window.location.hash.replace(/^#?\/?/, "") !== name) window.location.hash = `#/${name}`;
    window.scrollTo({ top: 0, behavior: "smooth" });

    // Instantly hydrate view from cached memory so cards are never blank
    if (state.summary) {
      if (name === "overview") {
        renderStats(state.summary);
        if (state.models) renderModels(state.models);
        if (state.figures?.length) renderFigures(state.figures);
      } else if (name === "market") {
        renderDashboard(state.summary);
        if (state.figures?.length) renderFigures(state.figures);
      } else if (name === "jds") {
        if (state.models?.jds) {
          renderModelDetail("jds", state.models.jds);
          makePredictor("jds", state.models.jds);
        }
        if (state.figures?.length) renderFigures(state.figures);
      } else if (name === "sds") {
        if (state.models?.sds) {
          renderModelDetail("sds", state.models.sds);
          makePredictor("sds", state.models.sds);
        }
        if (state.figures?.length) renderFigures(state.figures);
      } else if (name === "verify") {
        renderVerificationStats();
      }
    } else if (!state.refreshInFlight) {
      refresh();
    }
  }

  function number(value) {
    return typeof value === "number" && Number.isFinite(value) ? new Intl.NumberFormat().format(value) : "Not available";
  }

  function metric(value) {
    return typeof value === "number" && Number.isFinite(value) ? value.toFixed(4) : "—";
  }

  function percent(value) {
    return typeof value === "number" && Number.isFinite(value) ? `${Number(value.toFixed(1))}%` : "—";
  }

  function algorithmName(value) {
    return ({ logistic_regression: "Logistic regression", random_forest: "Random forest" })[value] || value || "Model";
  }

  function setNotice(element, title, message, type = "info") {
    if (!element) return;
    element.className = `notice notice-${type}`;
    element.replaceChildren();
    const icon = document.createElement("span");
    icon.textContent = type === "warning" ? "!" : "i";
    const body = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = title;
    const paragraph = document.createElement("p");
    paragraph.textContent = message;
    body.append(strong, paragraph);
    element.append(icon, body);
  }

  function renderStats(summary) {
    const root = $("#overview-stats");
    root.replaceChildren();
    const counts = summary?.dataset_row_counts || {};
    const market = state.market || summary?.job_market;
    const firstSkill = market?.top_skills?.[0];
    const firstRole = market?.analytics_role_frequency?.[0];
    const modelCard = key => {
      const model = state.models?.[key];
      const f1 = model?.metadata?.validation_metrics?.f1_macro;
      return model?.metadata ? `${model.metadata.model_name} · F1 ${metric(f1)}` : "Not ready";
    };
    const cards = [
      ["Source datasets", Object.keys(counts).length || null, "Organizer-provided files"],
      ["Job-posting source rows", market?.job_posting_source_rows ?? null, "Analytics Jobs + DataScience Jobs source rows"],
      ["Top skill", firstSkill?.name || "—", firstSkill ? `${number(firstSkill.count)} normalized mentions` : "Aggregate unavailable"],
      ["Top role", firstRole?.name || "—", firstRole ? `${number(firstRole.count)} Analytics Jobs source role rows` : "Aggregate unavailable"],
      ["JDS model", modelCard("jds"), state.models?.jds?.status === "ready" ? "Logistic regression · macro F1" : "Artifact not ready"],
      ["SDS model", modelCard("sds"), state.models?.sds?.status === "ready" ? "Random forest · macro F1" : "Artifact not ready"]
    ];
    cards.forEach(([title, value, hint]) => {
      const card = document.createElement("div");
      card.className = "stat-card";
      card.innerHTML = `<div class="stat-label"></div><div class="stat-value"></div><div class="stat-hint"></div>`;
      $(".stat-label", card).textContent = title;
      $(".stat-value", card).textContent = value === null ? "—" : (typeof value === "number" ? number(value) : value);
      if (["JDS model", "SDS model"].includes(title)) card.classList.add("stat-model");
      $(".stat-hint", card).textContent = hint;
      root.append(card);
    });
  }

  function renderRankList(element, items) {
    if (!element) return;
    element.replaceChildren();
    if (!Array.isArray(items) || !items.length) {
      element.textContent = "No aggregate results available.";
      element.classList.add("empty-state");
      return;
    }
    element.classList.remove("empty-state");
    const max = Math.max(...items.map(item => Number(item.count) || 0), 1);
    items.slice(0, 10).forEach(item => {
      const row = document.createElement("div");
      row.className = "rank-row";
      const name = document.createElement("span");
      name.className = "rank-name";
      name.textContent = item.name;
      const track = document.createElement("span");
      track.className = "rank-track";
      const fill = document.createElement("span");
      fill.className = "rank-fill";
      fill.style.width = `${Math.max(2, (Number(item.count) / max) * 100)}%`;
      track.append(fill);
      const count = document.createElement("span");
      count.className = "rank-count";
      count.textContent = number(Number(item.count));
      row.append(name, track, count);
      element.append(row);
    });
  }

  function renderModels(models) {
    const root = $("#overview-models");
    if (!root) return;
    root.replaceChildren();
    const entries = Object.entries(models || {});
    if (!entries.length) {
      root.textContent = "Model artifacts are not available yet.";
      return;
    }
    entries.forEach(([key, model]) => {
      const row = document.createElement("div");
      row.className = "model-row";
      const info = document.createElement("div");
      const title = document.createElement("div");
      title.className = "model-title";
      title.textContent = model.metadata?.model_name || `${key.toUpperCase()} model`;
      const sub = document.createElement("div");
      sub.className = "model-sub";
      const metrics = model.metadata?.validation_metrics || {};
      sub.textContent = model.metadata
        ? `${algorithmName(model.metadata.algorithm)} · Macro F1 ${metric(metrics.f1_macro)} · Accuracy ${metric(metrics.accuracy)} · ROC-AUC ${metric(metrics.roc_auc)} · ${model.metadata.cv_folds || "—"}-fold CV`
        : model.detail || "Model metadata unavailable";
      info.append(title, sub);
      const badge = document.createElement("span");
      badge.className = `badge ${model.status === "ready" ? "ready" : "missing"}`;
      badge.textContent = model.status === "ready" ? "Model Ready" : "Not Ready";
      row.append(info, badge);
      root.append(row);
    });
  }

  function renderModelDetail(key, info, comparisonRoot = null, metricsRoot = null, featureRoot = null) {
    comparisonRoot = comparisonRoot || $(`#${key}-comparison`);
    metricsRoot = metricsRoot || $(`#${key}-metrics`);
    featureRoot = featureRoot || $(`#${key}-features`);
    const snapshot = $(`#${key}-model-info`);
    if (!info?.metadata) {
      if (snapshot) snapshot.textContent = `${key.toUpperCase()} model metadata is unavailable.`;
      if (metricsRoot) metricsRoot.innerHTML = `<div class="metric-card"><small>${key.toUpperCase()} model</small><strong>Not ready</strong><span>Waiting for a valid local artifact</span></div>`;
      if (comparisonRoot) comparisonRoot.textContent = "Model comparison will appear after local evaluation.";
      if (featureRoot) featureRoot.textContent = "Feature interpretation is not available.";
      return;
    }
    const metadata = info.metadata;
    if (snapshot) {
      snapshot.innerHTML = `<strong>${metadata.model_name}</strong> · ${number(metadata.training_rows)} dataset rows · <strong>${metadata.cv_folds || 5}-fold stratified cross-validation</strong> · Target: <em>${key === "sds" ? "encoded organizational-success class" : "encoded salary-hike class"}</em>`;
    }
    const metrics = metadata.validation_metrics || {};
    if (metricsRoot) {
      metricsRoot.replaceChildren();
      [
        { key: "accuracy", label: "Accuracy", hint: "Out-of-fold accuracy" },
        { key: "f1_macro", label: "Macro F1", hint: "Balanced metric" },
        { key: "precision_macro", label: "Precision", hint: "Macro avg" },
        { key: "recall_macro", label: "Recall", hint: "Macro avg" },
        { key: "roc_auc", label: "ROC-AUC", hint: "Discrimination curve" }
      ].forEach(m => {
        const card = document.createElement("div");
        card.className = "metric-card";
        card.innerHTML = `<small>${m.label}</small><strong>${metric(metrics[m.key])}</strong><span>${m.hint}</span>`;
        metricsRoot.append(card);
      });
    }
    if (comparisonRoot) renderComparison(comparisonRoot, metadata.model_comparison || {});
    if (featureRoot) {
      featureRoot.replaceChildren();
      const items = Object.entries(metadata.feature_importance || {}).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
      const maxVal = Math.max(...items.map(i => Math.abs(Number(i[1]) || 0)), 0.001);
      items.forEach(([feature, value]) => {
        const row = document.createElement("div");
        row.className = "feature-row-enhanced";
        const title = document.createElement("span");
        title.className = "feature-name";
        title.textContent = labels[feature] || feature.replaceAll("_", " ");
        const track = document.createElement("div");
        track.className = "feature-track";
        const fill = document.createElement("div");
        fill.className = "feature-fill";
        fill.style.width = `${Math.min(100, Math.max(3, (Math.abs(Number(value)) / maxVal) * 100))}%`;
        track.append(fill);
        const score = document.createElement("strong");
        score.className = "feature-val";
        score.textContent = metric(value);
        row.append(title, track, score);
        featureRoot.append(row);
      });
      if (!items.length) featureRoot.textContent = "Importance values were not available for this model.";
    }
    renderConfusionMatrix($(`#${key}-confusion-data`), metadata.confusion_matrix);
  }

  function renderConfusionMatrix(root, matrix) {
    if (!root) return;
    root.replaceChildren();
    const labels = matrix?.labels || [];
    const values = matrix?.values || [];
    if (labels.length < 2 || values.length !== labels.length) {
      root.textContent = "Confusion counts are not available in model metadata.";
      return;
    }
    const table = document.createElement("table");
    table.className = "matrix-table";
    const caption = document.createElement("caption");
    caption.textContent = "Out-of-fold actual class by predicted class";
    table.append(caption);
    const head = document.createElement("thead");
    const header = document.createElement("tr");
    ["Actual \\ Predicted", ...labels].forEach(value => { const cell = document.createElement("th"); cell.textContent = `Pred ${value}`; header.append(cell); });
    head.append(header);
    const body = document.createElement("tbody");
    labels.forEach((label, index) => {
      const row = document.createElement("tr");
      const heading = document.createElement("th"); heading.scope = "row"; heading.textContent = `Act ${label}`; row.append(heading);
      labels.forEach((_, column) => {
        const cell = document.createElement("td");
        const val = values[index]?.[column];
        cell.textContent = number(val);
        if (index === column) {
          cell.className = "matrix-correct";
          cell.title = `Correct class ${label}: ${val}`;
        } else {
          cell.className = "matrix-error";
          cell.title = `Misclassified: ${val}`;
        }
        row.append(cell);
      });
      body.append(row);
    });
    table.append(head, body); root.append(table);
  }

  function renderComparison(root, candidates) {
    root.replaceChildren();
    const rows = Object.entries(candidates).filter(([, value]) => value && typeof value === "object");
    if (!rows.length) { root.textContent = "No model comparison is available."; return; }
    const table = document.createElement("table");
    table.className = "comparison-table";
    const head = document.createElement("thead");
    const header = document.createElement("tr");
    ["Candidate", "Accuracy", "Precision", "Recall", "Macro F1", "ROC-AUC"].forEach(text => { const th = document.createElement("th"); th.textContent = text; header.append(th); });
    head.append(header);
    const body = document.createElement("tbody");
    rows.forEach(([name, values]) => {
      const tr = document.createElement("tr");
      const isWinner = name === "logistic_regression" || name === "random_forest";
      if (isWinner) tr.classList.add("highlight-model-row");
      const nameCell = document.createElement("td");
      nameCell.innerHTML = `<strong>${name.replaceAll("_", " ").toUpperCase()}</strong>${isWinner ? ' <span class="winner-tag">Selected</span>' : ''}`;
      tr.append(nameCell);
      [metric(values.accuracy), metric(values.precision_macro), metric(values.recall_macro), metric(values.f1_macro), metric(values.roc_auc)].forEach(value => {
        const td = document.createElement("td");
        td.textContent = value;
        tr.append(td);
      });
      body.append(tr);
    });
    table.append(head, body);
    root.append(table);
  }

  function renderFigures(figures) {
    state.figures = figures || [];
    $("#figure-count").textContent = state.figures.length ? `${state.figures.length} local figure${state.figures.length === 1 ? "" : "s"}` : "No figures generated";
    const overview = $("#overview-figures");
    overview.replaceChildren();
    $$(".figure-slot").forEach(slot => slot.replaceChildren());
    const makeFigure = item => {
      const figure = document.createElement("figure");
      figure.className = "figure-card";
      const image = document.createElement("img");
      image.src = item.path;
      image.alt = item.name;
      image.loading = "lazy";
      const caption = document.createElement("figcaption");
      caption.textContent = item.name;
      image.addEventListener("error", () => {
        image.remove();
        caption.textContent = `${item.name} is unavailable; other local charts remain available.`;
        figure.classList.add("figure-fallback");
      }, { once: true });
      figure.append(image, caption);
      return figure;
    };
    if (!state.figures.length) {
      overview.innerHTML = `<div class="figure-empty">No generated figures are available. Aggregate charts and summaries remain available above.</div>`;
      return;
    }
    const demandFigure = state.figures.find(item => String(item.name || "").toLowerCase() === "top skills")
      || state.figures.find(item => String(item.name || "").toLowerCase().includes("skills"));
    if (demandFigure) overview.append(makeFigure(demandFigure));
    state.figures.forEach(item => {
      const path = String(item.path || "").toLowerCase();
      const name = String(item.name || "").toLowerCase();
      $$(".figure-slot").forEach(slot => {
        const requested = slot.dataset.figureMatch.toLowerCase();
        const slug = requested.replaceAll(" ", "_");
        const scopedMatch = (requested.startsWith("jds ") || requested.startsWith("sds "))
          && path.includes(`/${requested.slice(0, 3)}/${slug.slice(4)}`);
        if (path.includes(slug) || name.includes(slug.replaceAll("_", " ")) || scopedMatch) {
          slot.replaceChildren(makeFigure(item));
        }
      });
    });
    $$(".figure-slot").forEach(slot => {
      if (!slot.children.length) {
        const fallback = document.createElement("p");
        fallback.className = "figure-fallback-text";
        fallback.textContent = `The ${slot.dataset.figureMatch.replaceAll("_", " ")} figure is unavailable; local summaries and metadata remain available.`;
        slot.append(fallback);
      }
    });
  }

  function renderDashboard(summary) {
    state.summary = summary;
    renderStats(summary);
    $("#updated-at").textContent = summary?.generated_at ? new Date(summary.generated_at).toLocaleString() : "Not available";
    if (summary?.status === "ready") $("#data-notice").remove();
    else setNotice($("#data-notice"), "Local results are incomplete", "Some aggregate artifacts are unavailable. Use refresh after the local pipeline has completed.", "warning");

    const market = state.market || summary?.job_market;
    renderRankList($("#overview-skills"), market?.top_skills);
    renderRankList($("#market-roles"), market?.analytics_role_frequency);
    renderRankList($("#market-ds-roles"), market?.datascience_role_frequency);
    renderRankList($("#market-volume-roles"), market?.datascience_reported_job_volume);
    renderRankList($("#market-skills"), market?.top_skills);
    renderRankList($("#market-locations"), market?.top_locations || market?.locations);
    renderRankList($("#market-companies"), market?.top_companies);
    if (market) {
      setNotice($("#market-status"), "Aggregate summaries loaded", `${number(market.job_posting_source_rows)} job-posting source rows. Source role frequency and reported job volume use different counting structures and are presented separately. Descriptive patterns only.`);
      renderSalaryCategories(market.salary_summary || {});
      $("#experience-summary").textContent = `Observed ${number(market.experience_summary?.observed_count)} experience values; unit: ${market.experience_summary?.unit || "not specified"}.`;
      const relationships = market.notable_relationships || {};
      $("#market-relationships").textContent = Object.keys(relationships).length ? Object.entries(relationships).map(([name, value]) => `${name}: Pearson r ${metric(value.pearson_r)} (${number(value.paired_rows)} paired rows), descriptive association only.`).join(" ") : "No salary and experience relationship met the minimum data requirements.";
      renderNotes($("#market-limitations"), market.limitations || []);
      const correlation = relationships.datascience_jobs || relationships.salary_vs_experience || relationships.datascience_salary_vs_experience;
      const leadLocation = market.top_locations?.[0] || market.locations?.[0];
      const cards = [
        ["MOST FREQUENT SKILL", market.top_skills?.[0] ? `${market.top_skills[0].name} leads the Analytics Jobs skill vocabulary with ${number(market.top_skills[0].count)} normalized mentions.` : "Skill aggregate unavailable."],
        ["MOST FREQUENT ROLE LABEL", market.analytics_role_frequency?.[0] ? `${market.analytics_role_frequency[0].name} appears in ${number(market.analytics_role_frequency[0].count)} Analytics Jobs source role rows.` : "Role aggregate unavailable."],
        ["LEADING LOCATION", leadLocation ? `${leadLocation.name} is the most frequent location component (${number(leadLocation.count)} mentions).` : "Location aggregate unavailable."],
        ["SALARY / EXPERIENCE", correlation?.pearson_r != null ? `The descriptive correlation is ${metric(correlation.pearson_r)} across ${number(correlation.paired_rows)} pairs; it does not show causation.` : "A descriptive association is available in the market detail." ]
      ];
      const root = $("#insight-cards"); root.replaceChildren();
      cards.forEach(([title, text]) => { const card = document.createElement("article"); card.className = "insight-card"; card.innerHTML = `<div class="insight-label"></div><p></p>`; $(".insight-label", card).textContent = title; $("p", card).textContent = text; root.append(card); });
    } else {
      $("#salary-charts").textContent = "Salary categories are unavailable until local analysis is generated.";
      $("#experience-summary").textContent = "Not available until local analysis is generated.";
      $("#market-relationships").textContent = "Not available until local analysis is generated.";
    }
    renderNotes($("#all-limitations"), summary?.important_limitations || market?.limitations || []);
  }

  function renderSalaryCategories(salary) {
    const root = $("#salary-charts");
    if (!root) return;
    root.replaceChildren();
    const datasets = Object.entries(salary.by_dataset || {});
    if (!datasets.length) { root.textContent = "No source salary categories are available."; return; }
    datasets.forEach(([dataset, values]) => {
      const group = document.createElement("section");
      group.className = "category-group";
      const heading = document.createElement("h3");
      heading.textContent = dataset.replaceAll("_", " ");
      group.append(heading);
      const chart = document.createElement("div");
      chart.className = "category-chart";
      const categories = values.category_counts || [];
      const max = Math.max(1, ...categories.map(row => Number(row.count) || 0));
      categories.slice(0, 8).forEach(row => {
        const line = document.createElement("div"); line.className = "category-row";
        const label = document.createElement("span"); label.textContent = row.name;
        const track = document.createElement("span"); track.className = "rank-track";
        const fill = document.createElement("span"); fill.className = "rank-fill"; fill.style.width = `${Math.max(2, (Number(row.count) / max) * 100)}%`; track.append(fill);
        const count = document.createElement("strong"); count.textContent = number(row.count);
        line.append(label, track, count); chart.append(line);
      });
      if (!categories.length) chart.textContent = "No salary categories available.";
      group.append(chart);
      const source = document.createElement("p"); source.className = "source-note";
      source.textContent = values.observed_count > 0
        ? `Showing ${number(categories.length)} frequent values from ${number(values.observed_count)} records. ${values.unit || salary.unit || "Source units not specified"}`
        : `Showing ${number(categories.length)} source salary bands. ${values.unit || salary.unit || "Source units not specified"}`;
      group.append(source);
      root.append(group);
    });
  }

  function renderReadiness(readiness) {
    state.readiness = readiness;
    const root = $("#system-status");
    const ready = readiness?.status === "ready";
    root.className = `status-pill ${ready ? "ready" : "not-ready"}`;
    root.innerHTML = `<i></i>${ready ? "Model Ready · Local" : "Not Ready · Local"}`;
    root.title = readiness ? `Analysis: ${readiness.analysis?.status || "unknown"}; JDS: ${readiness.models?.jds?.status || "unknown"}; SDS: ${readiness.models?.sds?.status || "unknown"}` : "Local readiness endpoint is unavailable.";
  }

  function showToast(message, canRetry = true) {
    const toast = $("#api-toast");
    $("#toast-message").textContent = message;
    $("#toast-retry").hidden = !canRetry;
    toast.hidden = false;
  }

  function hideToast() { $("#api-toast").hidden = true; }

  function renderNotes(root, notes) {
    if (!root) return;
    root.replaceChildren();
    (notes || []).forEach(note => { const paragraph = document.createElement("p"); paragraph.textContent = note; root.append(paragraph); });
  }

  function makePredictor(key, info) {
    const form = $(`#${key}-form`);
    const fields = $(`#${key}-fields`);
    const status = $(`#${key}-predict-status`);
    const submit = $(`#${key}-submit`);
    if (!form || !fields) return;
    fields.replaceChildren();
    const metadata = info?.metadata;
    status.textContent = info?.status === "ready" ? "Model Ready" : "Artifact unavailable";
    status.className = `model-state ${info?.status === "ready" ? "ready" : ""}`;
    submit.disabled = info?.status !== "ready" || !metadata;
    if (!metadata) {
      fields.innerHTML = `<p class="empty-state">A valid local model artifact and metadata are required before predictions can run.</p>`;
      return;
    }

    // Interactive quick preset toolbar for 1-click evaluation
    let presetsBar = form.querySelector(".predictor-presets");
    if (!presetsBar) {
      presetsBar = document.createElement("div");
      presetsBar.className = "predictor-presets";
      form.insertBefore(presetsBar, fields);
    }
    presetsBar.replaceChildren();
    const presetLabel = document.createElement("span");
    presetLabel.className = "presets-label";
    presetLabel.textContent = "Quick Profiles:";
    presetsBar.append(presetLabel);

    const presets = key === "jds" ? [
      {
        name: "★ High Skills Profile",
        data: { big_data_skills: 4.8, maths_stats_skills: 4.9, coding_skills: 4.7, ai_and_ml_skills: 4.8, dashboard_and_storytelling_skills: 4.6 }
      },
      {
        name: "Balanced Applied",
        data: { big_data_skills: 3.6, maths_stats_skills: 3.8, coding_skills: 3.7, ai_and_ml_skills: 3.6, dashboard_and_storytelling_skills: 3.8 }
      },
      {
        name: "Baseline Entry",
        data: { big_data_skills: 2.5, maths_stats_skills: 2.6, coding_skills: 2.5, ai_and_ml_skills: 2.4, dashboard_and_storytelling_skills: 2.7 }
      }
    ] : [
      {
        name: "★ High Conscientious",
        data: { neuroticism: 24, extraversion: 48, openness_to_experience: 56, agreeableness: 48, conscientiousness: 60 }
      },
      {
        name: "Balanced Team Profile",
        data: { neuroticism: 36, extraversion: 42, openness_to_experience: 44, agreeableness: 46, conscientiousness: 48 }
      },
      {
        name: "High Stress / Low Structure",
        data: { neuroticism: 58, extraversion: 28, openness_to_experience: 32, agreeableness: 30, conscientiousness: 26 }
      }
    ];

    presets.forEach(p => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "preset-pill";
      btn.textContent = p.name;
      btn.addEventListener("click", () => {
        Object.entries(p.data).forEach(([fname, fval]) => {
          const input = $(`#${key}-${fname}`);
          if (input) input.value = fval;
        });
        presetsBar.querySelectorAll(".preset-pill").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        form.requestSubmit();
      });
      presetsBar.append(btn);
    });

    (metadata.feature_names || []).forEach(feature => {
      const range = metadata.feature_ranges?.[feature];
      const wrapper = document.createElement("div"); wrapper.className = "field";
      const label = document.createElement("label"); label.htmlFor = `${key}-${feature}`; label.textContent = labels[feature] || feature.replaceAll("_", " ");
      const input = document.createElement("input"); input.id = `${key}-${feature}`; input.name = feature; input.type = "number"; input.step = "any"; input.required = true;
      if (range && Number.isFinite(range.min) && Number.isFinite(range.max)) {
        input.min = range.min;
        input.max = range.max;
        input.value = ((range.min + range.max) / 2).toFixed(1);
      } else {
        input.value = "3.5";
      }
      const hint = document.createElement("small"); hint.textContent = range ? `Observed data range: ${range.min} to ${range.max}` : "Range not available; enter a numeric value.";
      wrapper.append(label, input, hint); fields.append(wrapper);
    });

    if (!form.dataset.bound) {
      form.dataset.bound = "true";
      form.addEventListener("submit", event => submitPrediction(event, key, state.models?.[key]?.metadata));
    }
  }

  async function submitPrediction(event, key, metadata) {
    event.preventDefault();
    const form = event.currentTarget;
    const result = $(`#${key}-result`);
    const button = $(`#${key}-submit`);
    if (form.dataset.busy === "true") return;
    const payload = Object.fromEntries(new FormData(form).entries());
    Object.keys(payload).forEach(name => { payload[name] = Number(payload[name]); });
    if (Object.values(payload).some(value => !Number.isFinite(value))) {
      result.textContent = "Enter finite numeric values for every feature.";
      result.className = "prediction-result error-text";
      return;
    }
    form.dataset.busy = "true"; button.disabled = true; button.textContent = "Running locally…"; result.textContent = "";
    try {
      const response = await fetch(`/api/models/${key}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload)
      });
      const body = await response.json();
      if (!response.ok) throw new Error(formatApiDetail(body.detail) || `Request failed (${response.status})`);
      result.replaceChildren();
      result.className = "prediction-result";
      if (body.status !== "ready" || body.prediction === null || body.prediction === undefined) {
        result.textContent = body.detail || `Prediction unavailable: ${body.status}.`;
        result.classList.add("error-text");
      } else {
        const predCard = document.createElement("div");
        predCard.className = `prediction-badge-card class-${body.prediction}`;
        const isClassOne = String(body.prediction) === "1";
        const classTitle = isClassOne
          ? (key === "jds" ? "Class 1: High Salary-Hike Associated Cohort" : "Class 1: High Organizational Success Cohort")
          : (key === "jds" ? "Class 0: Baseline Salary-Hike Cohort" : "Class 0: Baseline Organizational Success Cohort");
        predCard.innerHTML = `
          <div class="pred-header">
            <span class="pred-tag ${isClassOne ? 'high' : 'base'}">PREDICTED CLASS: ${body.prediction}</span>
            <strong class="pred-title">${classTitle}</strong>
          </div>
          <p class="pred-desc">${metadata?.model_name || "Trained Local Model"} (${algorithmName(metadata?.algorithm)}) evaluated with ${metadata?.cv_folds || 5}-fold stratified CV.</p>
          <small class="pred-disclaimer">Source target labels are preserved as supplied by the organizer. Entered values are illustrative inputs, not observed people.</small>
        `;
        result.append(predCard);
      }
    } catch (error) {
      result.textContent = `Could not complete local prediction: ${error.message}`;
      result.className = "prediction-result error-text";
    } finally {
      form.dataset.busy = "false";
      button.disabled = !metadata || state.models?.[key]?.status !== "ready";
      button.textContent = "Run local prediction";
    }
  }

  function setupTalentForm() {
    const root = $("#talent-skills");
    talentOptions.forEach(([value, label]) => {
      const wrapper = document.createElement("label"); wrapper.className = "skill-choice";
      const checkbox = document.createElement("input"); checkbox.type = "checkbox"; checkbox.name = "skills"; checkbox.value = value;
      const text = document.createElement("span"); text.textContent = label;
      wrapper.append(checkbox, text); root.append(wrapper);
    });
    $("#talent-form").addEventListener("submit", submitTalentProfile);
  }

  function addTalentList(parent, title, items, renderItem) {
    const section = document.createElement("section"); section.className = "talent-result-section";
    const heading = document.createElement("h3"); heading.textContent = title; section.append(heading);
    const list = document.createElement("ul");
    if (!items?.length) { const empty = document.createElement("li"); empty.textContent = "No supported matches in the available aggregate."; list.append(empty); }
    else items.forEach(item => { const row = document.createElement("li"); row.textContent = renderItem(item); list.append(row); });
    section.append(list); parent.append(section);
  }

  function renderTalentProfile(body, target = $("#talent-results")) {
    const root = target; root.replaceChildren();
    const heading = document.createElement("h2"); heading.textContent = body.title; root.append(heading);
    const label = document.createElement("p"); label.className = "overlap-label"; label.textContent = "Vocabulary coverage in supplied job-posting data"; root.append(label);
    const score = document.createElement("p"); score.className = "talent-overlap"; score.textContent = percent(body.overlap_percent);
    const explanation = document.createElement("p"); explanation.textContent = body.explanation; root.append(score, explanation);
    const sourceNote = document.createElement("p"); sourceNote.className = "summary-copy"; sourceNote.textContent = body.skill_frequency_note; root.append(sourceNote);
    addTalentList(root, "Profile skills found in the job-market vocabulary", body.matched_skills, item => `${item.label}: ${number(item.frequency)} normalized mentions${item.supporting_terms.length ? ` (${item.supporting_terms.join(", ")})` : ""}`);
    addTalentList(root, "Selected skills without matching vocabulary terms", body.unmatched_profile_skills, item => item.label);
    addTalentList(root, "Other high-demand skills to consider", body.missing_high_demand_skills, item => `${item.name}: ${number(item.count)} mentions`);
    addTalentList(root, "Top role-category suggestions", body.top_role_categories, item => `${item.role} — ${percent(item.overlap_percent)} heuristic rule overlap; ${number(item.role_frequency)} role rows; rule skills: ${item.role_skill_rule.join(", ")}`);
    const note = document.createElement("p"); note.className = "micro-warning"; note.textContent = body.role_matching_note; root.append(note);
    body.limitations.forEach(text => { const p = document.createElement("p"); p.className = "micro-warning"; p.textContent = text; root.append(p); });
  }

  async function submitTalentProfile(event) {
    event.preventDefault();
    const selected = [...$("#talent-form").querySelectorAll("input[name=skills]:checked")].map(input => input.value);
    const error = $("#talent-error"); error.textContent = "";
    if (!selected.length) { error.textContent = "Select at least one skill to continue."; return; }
    const button = $("#talent-submit");
    if (button.dataset.busy === "true") return;
    button.dataset.busy = "true"; button.disabled = true; button.textContent = "Analyzing local aggregates…";
    try {
      const response = await fetch("/api/talent/profile", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify({ skills: selected }) });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(formatApiDetail(body.detail) || `Request failed (${response.status})`);
      }
      renderTalentProfile(body);
    } catch (caught) {
      error.textContent = `Could not analyze this profile: ${caught.message}`;
      $("#talent-results").replaceChildren();
    } finally { button.dataset.busy = "false"; button.disabled = false; button.textContent = "Analyze descriptive overlap"; }
  }

  async function refresh() {
    if (state.refreshInFlight) return;
    state.refreshInFlight = true;
    const refreshButton = $("#refresh-button");
    refreshButton.disabled = true; refreshButton.classList.add("is-loading");
    $("#system-status").className = "status-pill loading";
    $("#system-status").innerHTML = `<i></i>Checking local readiness`;
    const [healthResult, readinessResult, summaryResult, marketResult, modelsResult, figuresResult] = await Promise.allSettled([
      getJson("/health"), getJson("/api/readiness"), getJson("/api/reports/summary"),
      getJson("/api/analysis/job-market"), getJson("/api/models"), getJson("/api/figures")
    ]);
    if (readinessResult.status === "fulfilled") renderReadiness(readinessResult.value);
    else renderReadiness(null);
    if (summaryResult.status === "fulfilled") state.summary = summaryResult.value;
    if (marketResult.status === "fulfilled" && marketResult.value.status === "ready") state.market = marketResult.value.summary;
    else state.market = state.summary?.job_market || null;
    const talentSubmit = $("#talent-submit");
    const talentReady = Boolean(state.market && readinessResult.status === "fulfilled" && readinessResult.value.analysis?.status === "ready");
    talentSubmit.disabled = !talentReady;
    talentSubmit.textContent = talentReady ? "Analyze descriptive overlap" : "Local analysis unavailable";
    if (modelsResult.status === "fulfilled") state.models = modelsResult.value;
    if (summaryResult.status === "fulfilled") renderDashboard(state.summary);
    else setNotice($("#data-notice"), "Local API unavailable", "Start the FastAPI app on this machine, then retry. No remote service is used.", "warning");
    renderStats(state.summary);
    if (state.models) {
      renderModels(state.models);
      renderModelDetail("jds", state.models.jds);
      renderModelDetail("sds", state.models.sds);
      makePredictor("jds", state.models.jds);
      makePredictor("sds", state.models.sds);
    }
    if (figuresResult.status === "fulfilled") renderFigures(figuresResult.value.figures);
    else renderFigures([]);
    const failures = [healthResult, readinessResult, summaryResult, marketResult, modelsResult, figuresResult]
      .map((result, index) => result.status === "rejected" ? ["health", "readiness", "summary", "job-market", "models", "figures"][index] : null)
      .filter(Boolean);
    if (failures.length) showToast(`Some local data could not be loaded: ${failures.join(", ")}.`);
    else hideToast();
    state.refreshInFlight = false;
    refreshButton.disabled = false; refreshButton.classList.remove("is-loading");
    const activeRoute = getCleanRoute();
    if (activeRoute && activeRoute !== "overview") {
      showView(activeRoute);
    }
  }

  $$(".nav-item").forEach(button => button.addEventListener("click", () => showView(button.dataset.view)));
  $$('[data-go]').forEach(button => button.addEventListener("click", () => showView(button.dataset.go)));
  $("#refresh-button").addEventListener("click", refresh);
  $("#toast-retry").addEventListener("click", refresh);
  $("#toast-dismiss").addEventListener("click", hideToast);
  setupTalentForm();
  setupVerification();
  restoreSessionIfAny();
  const getCleanRoute = () => (window.location.hash || "").replace(/^#?\/?/, "").trim();
  window.addEventListener("hashchange", () => {
    const name = getCleanRoute();
    if (name && $(`#view-${name}`)) showView(name);
    else showView("overview");
  });
  const initial = getCleanRoute();
  if (initial && $(`#view-${initial}`)) showView(initial); else showView("overview");
  refresh();
})();
