(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const state = { summary: null, models: null, figures: [] };
  const labels = {
    big_data_skills: "Big data skills", maths_stats_skills: "Maths & statistics", coding_skills: "Coding skills",
    ai_and_ml_skills: "AI & machine learning", dashboard_and_storytelling_skills: "Dashboard & storytelling",
    neuroticism: "Neuroticism", extraversion: "Extraversion", openness_to_experience: "Openness to experience",
    agreeableness: "Agreeableness", conscientiousness: "Conscientiousness"
  };

  async function getJson(path) {
    const response = await fetch(path, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return response.json();
  }

  function showView(name) {
    $$(".view").forEach(view => view.classList.toggle("active", view.id === `view-${name}`));
    $$(".nav-item").forEach(button => button.classList.toggle("active", button.dataset.view === name));
    const active = $(`.nav-item[data-view="${name}"]`);
    $("#current-section").textContent = active ? active.textContent.trim() : "Overview";
    window.location.hash = name;
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function number(value) {
    return typeof value === "number" && Number.isFinite(value) ? new Intl.NumberFormat().format(value) : "Not available";
  }

  function metric(value) {
    return typeof value === "number" && Number.isFinite(value) ? value.toFixed(3) : "—";
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
    const entries = Object.values(counts);
    const total = entries.reduce((sum, value) => sum + value, 0);
    const jobs = summary?.job_market?.total_jobs;
    const readyModels = Object.values(summary?.models || {}).filter(model => model.status === "ready").length;
    const cards = [
      ["Source datasets", Object.keys(counts).length || null, "Organizer-provided files"],
      ["Source rows", entries.length ? total : null, "Aggregated row counts"],
      ["Job postings", typeof jobs === "number" ? jobs : null, "Across available job datasets"],
      ["Models ready", summary?.models ? readyModels : null, "Artifacts with valid metadata"]
    ];
    cards.forEach(([title, value, hint]) => {
      const card = document.createElement("div");
      card.className = "stat-card";
      card.innerHTML = `<div class="stat-label"></div><div class="stat-value"></div><div class="stat-hint"></div>`;
      $(".stat-label", card).textContent = title;
      $(".stat-value", card).textContent = value === null ? "—" : number(value);
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
      sub.textContent = model.target || "Model metadata unavailable";
      info.append(title, sub);
      const badge = document.createElement("span");
      badge.className = `badge ${model.status === "ready" ? "ready" : "missing"}`;
      badge.textContent = model.status === "ready" ? "Ready" : model.status.replaceAll("_", " ");
      row.append(info, badge);
      root.append(row);
      renderModelDetail(key, model, comparisonRoot, metricsRoot, featureRoot);
      makePredictor(key, model);
    });
  }

  function renderModelDetail(key, info, comparisonRoot, metricsRoot, featureRoot) {
    if (!info?.metadata) {
      if (metricsRoot) metricsRoot.innerHTML = `<div class="metric-card"><small>${key.toUpperCase()} model</small><strong>Not ready</strong><span>Waiting for a valid local artifact</span></div>`;
      if (comparisonRoot) comparisonRoot.textContent = "Model comparison will appear after local evaluation.";
      if (featureRoot) featureRoot.textContent = "Feature interpretation is not available.";
      return;
    }
    const metadata = info.metadata;
    const metrics = metadata.validation_metrics || {};
    if (metricsRoot) {
      metricsRoot.replaceChildren();
      ["accuracy", "precision_macro", "recall_macro", "f1_macro", "roc_auc"].forEach(name => {
        const card = document.createElement("div");
        card.className = "metric-card";
        card.innerHTML = `<small></small><strong></strong><span>Stratified out-of-fold</span>`;
        $("small", card).textContent = name.replaceAll("_", " ");
        $("strong", card).textContent = metric(metrics[name]);
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
    const market = $("#market-figures");
    overview.replaceChildren(); market.replaceChildren();
    $$(".figure-slot").forEach(slot => slot.replaceChildren());
    if (!state.figures.length) {
      overview.innerHTML = `<div class="figure-empty">Figures will appear here after a successful local pipeline run.</div>`;
      return;
    }
    state.figures.forEach(item => {
      const figure = document.createElement("figure");
      figure.className = "figure-card";
      const image = document.createElement("img");
      image.src = item.path;
      image.alt = item.name;
      image.loading = "lazy";
      const caption = document.createElement("figcaption");
      caption.textContent = item.name;
      figure.append(image, caption);
      if (item.name.toLowerCase().includes("job market") || item.path.includes("job_market")) market.append(figure.cloneNode(true));
      if (overview.children.length < 4) overview.append(figure.cloneNode(true));
      const name = item.name.toLowerCase();
      $$(".figure-slot").forEach(slot => {
        const match = slot.dataset.figureMatch;
        if (name.includes(match) || item.path.toLowerCase().includes(match.replaceAll(" ", "_")) || (match.startsWith("jds") && item.path.toLowerCase().includes("jds/") && item.name.toLowerCase().includes(match.replace("jds ", ""))) || (match.startsWith("sds") && item.path.toLowerCase().includes("sds/") && item.name.toLowerCase().includes(match.replace("sds ", "")))) {
          const img = document.createElement("img"); img.src = item.path; img.alt = item.name; img.loading = "lazy"; slot.append(img);
        }
      });
    });
  }

  function renderDashboard(summary) {
    state.summary = summary;
    renderStats(summary);
    const status = $("#system-status");
    status.className = `status-pill ${summary?.status || ""}`;
    status.innerHTML = `<i></i>${summary?.status === "ready" ? "All artifacts ready" : summary?.status === "partial" ? "Partial local results" : "Artifacts not ready"}`;
    $("#updated-at").textContent = summary?.generated_at ? new Date(summary.generated_at).toLocaleString() : "Not available";
    if (summary?.status === "ready") $("#data-notice").remove();
    else setNotice($("#data-notice"), "Local results are incomplete", "Add all four organizer files under data/raw/ and run the pipeline. Missing results are not replaced with sample data.");

    const market = summary?.job_market;
    renderRankList($("#overview-skills"), market?.top_skills);
    renderRankList($("#market-roles"), market?.top_roles);
    renderRankList($("#market-skills"), market?.top_skills);
    renderRankList($("#market-locations"), market?.top_locations || market?.locations);
    renderRankList($("#market-companies"), market?.top_companies);
    if (market) {
      setNotice($("#market-status"), "Aggregate summaries loaded", `${number(market.total_jobs)} rows across the available job datasets. Descriptive patterns only.`);
      const salary = market.salary_summary || {};
      $("#salary-stats").replaceChildren();
      const salaryRows = Object.entries(salary.by_dataset || {});
      const salaryMetrics = salaryRows.length
        ? salaryRows.map(([dataset, details]) => [`${dataset.replaceAll("_", " ")} median`, details.median]).concat(salaryRows.map(([dataset, details]) => [`${dataset.replaceAll("_", " ")} parsed`, details.observed_count]))
        : [["Median", salary.median], ["Minimum", salary.min], ["Maximum", salary.max], ["Parsed rows", salary.observed_count]];
      salaryMetrics.forEach(([name, value]) => {
        const item = document.createElement("div");
        const small = document.createElement("small"); small.textContent = name;
        const strong = document.createElement("strong"); strong.textContent = value == null ? "—" : number(value);
        item.append(small, strong); $("#salary-stats").append(item);
      });
      $("#experience-summary").textContent = `Observed ${number(market.experience_summary?.observed_count)} experience values; unit: ${market.experience_summary?.unit || "not specified"}.`;
      const relationships = market.notable_relationships || {};
      $("#market-relationships").textContent = Object.keys(relationships).length ? Object.entries(relationships).map(([name, value]) => `${name}: Pearson r ${metric(value.pearson_r)} (${number(value.paired_rows)} paired rows), descriptive association only.`).join(" ") : "No salary and experience relationship met the minimum data requirements.";
      renderNotes($("#market-limitations"), market.limitations || []);
      const cards = [
        ["MOST LISTED SKILL", market.top_skills?.[0] ? `${market.top_skills[0].name} appears ${number(market.top_skills[0].count)} times in parsed skill mentions.` : "No skill summary available."],
        ["ROLE MIX", market.top_roles?.[0] ? `${market.top_roles[0].name} is the most frequent listed role in the available postings.` : "No role summary available."],
        ["INTERPRETATION", "Posting counts describe these supplied sources; they do not establish total market demand or causality."]
      ];
      const root = $("#insight-cards"); root.replaceChildren();
      cards.forEach(([title, text]) => { const card = document.createElement("article"); card.className = "insight-card"; card.innerHTML = `<div class="insight-label"></div><p></p>`; $(".insight-label", card).textContent = title; $("p", card).textContent = text; root.append(card); });
    } else {
      $("#salary-stats").textContent = "Not available";
      $("#experience-summary").textContent = "Not available until local analysis is generated.";
      $("#market-relationships").textContent = "Not available until local analysis is generated.";
    }
    renderNotes($("#all-limitations"), summary?.important_limitations || market?.limitations || []);
  }

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
    submit.disabled = !metadata;
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
    form.addEventListener("submit", event => submitPrediction(event, key, metadata));
  }

  async function submitPrediction(event, key, metadata) {
    event.preventDefault();
    const form = event.currentTarget;
    const result = $(`#${key}-result`);
    const button = $(`#${key}-submit`);
    const payload = Object.fromEntries(new FormData(form).entries());
    Object.keys(payload).forEach(name => { payload[name] = Number(payload[name]); });
    if (Object.values(payload).some(value => !Number.isFinite(value))) { result.textContent = "Enter finite numeric values for every feature."; result.className = "prediction-result error-text"; return; }
    button.disabled = true; button.textContent = "Running locally…"; result.textContent = "";
    try {
      const response = await fetch(`/api/models/${key}/predict`, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(payload) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
      result.replaceChildren(); result.className = "prediction-result";
      if (body.status !== "ready" || !body.prediction) {
        result.textContent = body.detail || `Prediction unavailable: ${body.status}.`;
        result.classList.add("error-text");
      } else {
        const label = document.createElement("div"); label.className = "prediction-label"; label.textContent = `Predicted source class: ${body.prediction}`;
        const note = document.createElement("div"); note.className = "prediction-meta"; note.textContent = `${metadata.model_name} · ${metadata.algorithm || "validated local model"}. Source target labels are preserved as encoded; demo input only, not a guarantee or decision recommendation.`;
        result.append(label, note);
      }
    } catch (error) {
      result.textContent = `Could not complete local prediction: ${error.message}`;
      result.className = "prediction-result error-text";
    } finally {
      button.disabled = false; button.textContent = "Run local prediction";
    }
  }

  async function refresh() {
    const [summaryResult, modelsResult, figuresResult] = await Promise.allSettled([
      getJson("/api/reports/summary"), getJson("/api/models"), getJson("/api/figures")
    ]);
    if (summaryResult.status === "fulfilled") renderDashboard(summaryResult.value);
    else setNotice($("#data-notice"), "API is unavailable", "Start the local FastAPI server, then refresh this view.", "warning");
    if (modelsResult.status === "fulfilled") {
      state.models = modelsResult.value;
      renderModels(state.models, null, null, null);
      renderModelDetail("jds", state.models.jds, $("#jds-comparison"), $("#jds-metrics"), $("#jds-features"));
      renderModelDetail("sds", state.models.sds, $("#sds-comparison"), $("#sds-metrics"), $("#sds-features"));
    }
    if (figuresResult.status === "fulfilled") renderFigures(figuresResult.value.figures);
  }

  $$(".nav-item").forEach(button => button.addEventListener("click", () => showView(button.dataset.view)));
  $$('[data-go]').forEach(button => button.addEventListener("click", () => showView(button.dataset.go)));
  $("#refresh-button").addEventListener("click", refresh);
  window.addEventListener("hashchange", () => {
    const name = window.location.hash.slice(1);
    if ($(`#view-${name}`)) showView(name);
  });
  const initial = window.location.hash.slice(1);
  if ($(`#view-${initial}`)) showView(initial);
  refresh();
})();
