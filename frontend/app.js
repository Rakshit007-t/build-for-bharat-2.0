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
    state.latestReport = null;
    state.assessment = null;
    state.currentQuestion = null;
    $("#verification-report-page").hidden = true;
    $("#verify-assessment-step").hidden = true;
    renderClaims(body);
  }

  function renderClaims(candidate) {
    $("#verify-claims-step").hidden = false;
    $("#candidate-heading").textContent = `${candidate.name || "Candidate"} · detected skill claims`;
    $("#candidate-education").textContent = candidate.education ? `Education: ${candidate.education}` : "Education was not explicitly extracted.";
    const rows = $("#claims-rows"); rows.replaceChildren();
    candidate.skills.forEach(claim => {
      const row = document.createElement("tr"); row.dataset.skillRow = claim.skill;
      const skill = document.createElement("th"); skill.scope = "row"; skill.textContent = claim.skill;
      const level = document.createElement("td"); level.textContent = claim.claimed_level;
      const excerpts = document.createElement("td");
      if (claim.evidence_snippets?.length) {
        const list = document.createElement("ul"); list.className = "excerpt-list";
        claim.evidence_snippets.forEach(snippet => { const item = document.createElement("li"); item.textContent = `“${snippet}”`; list.append(item); });
        excerpts.append(list);
      } else excerpts.textContent = "No concrete supporting excerpt detected.";
      const statusCell = document.createElement("td"); statusCell.className = "claim-status";
      const knownResult = state.latestReport?.skills?.find(item => item.skill === claim.skill);
      statusCell.textContent = knownResult?.status || (claim.claimed_level === "Unspecified" ? "Unverified" : "Pending");
      const action = document.createElement("td");
      const button = document.createElement("button"); button.className = "small-action"; button.type = "button"; button.textContent = "Start Verification";
      button.addEventListener("click", () => startAssessment(claim.skill)); action.append(button);
      row.append(skill, level, excerpts, statusCell, action); rows.append(row);
    });
    $("#verify-claims-step").scrollIntoView({ behavior: "smooth", block: "start" });
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

  async function startAssessment(skill) {
    const candidateId = state.verificationCandidate?.candidate_id;
    if (!candidateId) return;
    try {
      state.assessment = await postJson(`/api/verification/${encodeURIComponent(candidateId)}/start`, { skill });
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
      continueButton.textContent = result.done ? "View verification report" : "Continue";
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
    completed.forEach(result => {
      const card = document.createElement("article"); card.className = `result-card status-${result.status}`;
      const header = document.createElement("div"); header.className = "result-card-header";
      const title = document.createElement("div"); addText(title, "p", result.skill.toUpperCase(), "eyebrow"); addText(title, "h2", `${result.status.toUpperCase()}`);
      const score = addText(header, "strong", `${result.final_score.toFixed(1)}`, "result-total"); header.append(title, score);
      const tiles = document.createElement("div"); tiles.className = "result-metrics";
      [["CLAIMED", result.claimed_level], ["VERIFIED", result.verified_level || "Unverified"], ["EVIDENCE", result.evidence_score === null ? "—" : `${result.evidence_score.toFixed(1)}/100`], ["TEST", result.test_score === null ? "—" : `${result.test_score.toFixed(1)}/100`], ["FINAL SCORE", `${result.final_score.toFixed(1)}/100`]].forEach(([label, value]) => {
        const tile = document.createElement("div"); addText(tile, "span", label); addText(tile, "strong", value); tiles.append(tile);
      });
      card.append(header, tiles);
      const calculation = document.createElement("p"); calculation.className = "calculation-line";
      calculation.textContent = `Evidence ${result.evidence_score.toFixed(1)} × 0.4 = ${(result.evidence_score * 0.4).toFixed(1)}  +  Test ${result.test_score.toFixed(1)} × 0.6 = ${(result.test_score * 0.6).toFixed(1)}  →  Final ${result.final_score.toFixed(1)}`;
      card.append(calculation);
      addText(card, "h3", "Why this result?"); addText(card, "p", result.explanation);
      addText(card, "h3", "Evidence scoring details");
      const details = document.createElement("ul"); details.className = "excerpt-list";
      result.evidence_details.forEach(detail => addText(details, "li", detail)); card.append(details);
      addText(card, "h3", "Resume evidence excerpts");
      if (result.evidence_snippets.length) {
        const list = document.createElement("ul"); list.className = "excerpt-list";
        result.evidence_snippets.forEach(snippet => addText(list, "li", `“${snippet}”`)); card.append(list);
      } else addText(card, "p", "No concrete supporting excerpt detected.");
      addText(card, "p", "Prototype heuristic evidence score · Local assessment · Not a hiring decision.", "source-note");
      root.append(card);
    });
    if (!completed.length) addText(root, "p", "Complete a skill assessment to see a result.");
    const pending = report.skills.filter(item => item.final_score === null);
    report.skills.forEach(item => {
      const row = $(`[data-skill-row="${CSS.escape(item.skill)}"]`, $("#claims-rows"));
      const statusCell = row?.querySelector(".claim-status");
      if (statusCell) statusCell.textContent = item.final_score === null ? (item.status === "unverified" ? "Unverified" : "Pending") : item.status.toUpperCase();
    });
    if (pending.length) {
      const note = document.createElement("p"); note.className = "pending-skills";
      note.textContent = `Not yet assessed: ${pending.map(item => `${item.skill} (${item.claimed_level})`).join(", ")}.`; root.append(note);
    }
    const market = $("#verification-market-insights");
    const doneSkills = report.skills.filter(item => item.final_score !== null && item.status !== "unverified").map(item => ({ Python: "python", SQL: "sql", "Machine Learning": "machine_learning" })[item.skill]).filter(Boolean);
    market.hidden = false;
    const content = $("#verification-market-content"); content.replaceChildren();
    if (!doneSkills.length) addText(content, "p", "Market alignment is unavailable until a skill has an explicit claim and a completed assessment.");
    else postJson("/api/talent/profile", { skills: [...new Set(doneSkills)] }).then(body => renderTalentProfile(body, content)).catch(error => addText(content, "p", `Local job-market analysis unavailable: ${error.message}`));
    $("#verification-report-page").hidden = false;
    $("#verification-report-page").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function loadVerificationReport() {
    const candidateId = state.verificationCandidate?.candidate_id;
    if (!candidateId) return;
    try {
      const report = await getJson(`/api/verification/${encodeURIComponent(candidateId)}/report`);
      renderVerificationReport(report);
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

  function setupVerification() {
    $("#resume-file").addEventListener("change", event => uploadFile(event.target.files[0]));
    $$("[data-demo]").forEach(button => button.addEventListener("click", () => useDemo(button.dataset.demo)));
    const dropzone = $("#resume-dropzone");
    ["dragenter", "dragover"].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.add("dragging"); }));
    ["dragleave", "drop"].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.remove("dragging"); }));
    dropzone.addEventListener("drop", event => uploadFile(event.dataTransfer.files[0]));
    $("#print-report").addEventListener("click", () => window.print());
    renderVerificationStats();
  }

  function formatApiDetail(detail) {
    if (Array.isArray(detail)) return detail.map(item => `${item.field ? `${item.field}: ` : ""}${item.message || "Invalid input"}`).join("; ");
    if (typeof detail === "string") return detail;
    return "";
  }

  function showView(name) {
    $$(".view").forEach(view => view.classList.toggle("active", view.id === `view-${name}`));
    $$(".nav-item").forEach(button => button.classList.toggle("active", button.dataset.view === name));
    const active = $(`.nav-item[data-view="${name}"]`);
    $("#current-section").textContent = active ? active.textContent.trim() : "Overview";
    if (window.location.hash !== `#${name}`) window.location.hash = name;
    window.scrollTo({ top: 0, behavior: "smooth" });
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

  function renderModels(models, comparisonRoot, metricsRoot, featureRoot) {
    const root = $("#overview-models");
    root.replaceChildren();
    const entries = Object.entries(models || {});
    if (!entries.length) root.textContent = "Model artifacts are not available yet.";
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
      renderModelDetail(key, model, comparisonRoot, metricsRoot, featureRoot);
      makePredictor(key, model);
    });
  }

  function renderModelDetail(key, info, comparisonRoot, metricsRoot, featureRoot) {
    const snapshot = $(`#${key}-model-info`);
    if (!info?.metadata) {
      if (snapshot) snapshot.textContent = `${key.toUpperCase()} model metadata is unavailable.`;
      if (metricsRoot) metricsRoot.innerHTML = `<div class="metric-card"><small>${key.toUpperCase()} model</small><strong>Not ready</strong><span>Waiting for a valid local artifact</span></div>`;
      if (comparisonRoot) comparisonRoot.textContent = "Model comparison will appear after local evaluation.";
      if (featureRoot) featureRoot.textContent = "Feature interpretation is not available.";
      return;
    }
    const metadata = info.metadata;
    if (snapshot) snapshot.textContent = `${metadata.model_name} · ${number(metadata.training_rows)} dataset rows · ${metadata.cv_folds || "—"}-fold stratified cross-validation · target: ${key === "sds" ? "encoded organizational-success class" : "encoded salary-hike class"}.`;
    const metrics = metadata.validation_metrics || {};
    if (metricsRoot) {
      metricsRoot.replaceChildren();
      ["accuracy", "precision_macro", "recall_macro", "f1_macro", "roc_auc"].forEach(name => {
        const card = document.createElement("div");
        card.className = "metric-card";
        card.innerHTML = `<small></small><strong></strong><span></span>`;
        $("small", card).textContent = name.replaceAll("_", " ");
        $("strong", card).textContent = metric(metrics[name]);
        $("span", card).textContent = name === "roc_auc" && metrics[name] == null ? "Not available" : "Stratified out-of-fold";
        metricsRoot.append(card);
      });
    }
    if (comparisonRoot) renderComparison(comparisonRoot, metadata.model_comparison || {});
    if (featureRoot) {
      featureRoot.replaceChildren();
      const items = Object.entries(metadata.feature_importance || {}).sort((a, b) => b[1] - a[1]);
      items.forEach(([feature, value]) => {
        const row = document.createElement("div");
        row.className = "feature-row";
        const title = document.createElement("span");
        title.textContent = labels[feature] || feature.replaceAll("_", " ");
        const score = document.createElement("strong");
        score.textContent = metric(value);
        row.append(title, score);
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
    ["Actual \\ Predicted", ...labels].forEach(value => { const cell = document.createElement("th"); cell.textContent = value; header.append(cell); });
    head.append(header);
    const body = document.createElement("tbody");
    labels.forEach((label, index) => {
      const row = document.createElement("tr");
      const heading = document.createElement("th"); heading.scope = "row"; heading.textContent = label; row.append(heading);
      labels.forEach((_, column) => { const cell = document.createElement("td"); cell.textContent = number(values[index]?.[column]); row.append(cell); });
      body.append(row);
    });
    table.append(head, body); root.append(table);
  }

  function renderComparison(root, candidates) {
    root.replaceChildren();
    const rows = Object.entries(candidates).filter(([, value]) => value && typeof value === "object");
    if (!rows.length) { root.textContent = "No model comparison is available."; return; }
    const table = document.createElement("table");
    const head = document.createElement("thead");
    const header = document.createElement("tr");
    ["Candidate", "Accuracy", "Precision", "Recall", "Macro F1", "ROC-AUC"].forEach(text => { const th = document.createElement("th"); th.textContent = text; header.append(th); });
    head.append(header);
    const body = document.createElement("tbody");
    rows.forEach(([name, values]) => {
      const tr = document.createElement("tr");
      [name.replaceAll("_", " "), metric(values.accuracy), metric(values.precision_macro), metric(values.recall_macro), metric(values.f1_macro), metric(values.roc_auc)].forEach(value => { const td = document.createElement("td"); td.textContent = value; tr.append(td); });
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
    status.textContent = info?.status === "ready" ? "Ready" : "Artifact unavailable";
    submit.disabled = info?.status !== "ready" || !metadata;
    if (!metadata) { fields.innerHTML = `<p class="empty-state">A valid local model artifact and metadata are required before predictions can run.</p>`; return; }
    (metadata.feature_names || []).forEach(feature => {
      const range = metadata.feature_ranges?.[feature];
      const wrapper = document.createElement("div"); wrapper.className = "field";
      const label = document.createElement("label"); label.htmlFor = `${key}-${feature}`; label.textContent = labels[feature] || feature.replaceAll("_", " ");
      const input = document.createElement("input"); input.id = `${key}-${feature}`; input.name = feature; input.type = "number"; input.step = "any"; input.required = true;
      if (range && Number.isFinite(range.min) && Number.isFinite(range.max)) { input.min = range.min; input.max = range.max; }
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
    if (Object.values(payload).some(value => !Number.isFinite(value))) { result.textContent = "Enter finite numeric values for every feature."; result.className = "prediction-result error-text"; return; }
    form.dataset.busy = "true"; button.disabled = true; button.textContent = "Running locally…"; result.textContent = "";
    try {
      const response = await fetch(`/api/models/${key}/predict`, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(payload) });
      const body = await response.json();
      if (!response.ok) throw new Error(formatApiDetail(body.detail) || `Request failed (${response.status})`);
      result.replaceChildren(); result.className = "prediction-result";
      if (body.status !== "ready" || !body.prediction) {
        result.textContent = body.detail || `Prediction unavailable: ${body.status}.`;
        result.classList.add("error-text");
      } else {
        const label = document.createElement("div"); label.className = "prediction-label"; label.textContent = `Predicted encoded class: ${body.prediction}`;
        const note = document.createElement("div"); note.className = "prediction-meta"; note.textContent = `${metadata.model_name} · ${metadata.algorithm || "local model"}. Target labels are preserved as supplied by the organizer; entered values are illustrative inputs, not observed people or outcomes.`;
        result.append(label, note);
      }
    } catch (error) {
      result.textContent = `Could not complete local prediction: ${error.message}`;
      result.className = "prediction-result error-text";
    } finally {
      form.dataset.busy = "false"; button.disabled = !metadata || state.models?.[key]?.status !== "ready"; button.textContent = "Run local prediction";
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
      renderModels(state.models, null, null, null);
      renderModelDetail("jds", state.models.jds, $("#jds-comparison"), $("#jds-metrics"), $("#jds-features"));
      renderModelDetail("sds", state.models.sds, $("#sds-comparison"), $("#sds-metrics"), $("#sds-features"));
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
  }

  $$(".nav-item").forEach(button => button.addEventListener("click", () => showView(button.dataset.view)));
  $$('[data-go]').forEach(button => button.addEventListener("click", () => showView(button.dataset.go)));
  $("#refresh-button").addEventListener("click", refresh);
  $("#toast-retry").addEventListener("click", refresh);
  $("#toast-dismiss").addEventListener("click", hideToast);
  setupTalentForm();
  setupVerification();
  window.addEventListener("hashchange", () => {
    const name = window.location.hash.slice(1);
    if ($(`#view-${name}`)) showView(name);
    else showView("overview");
  });
  const initial = window.location.hash.slice(1);
  if ($(`#view-${initial}`)) showView(initial); else showView("overview");
  refresh();
})();
