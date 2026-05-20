const state = {
  ideas: [],
  articles: [],
  topics: [],
  sources: [],
  signalStatus: "",
  sourceStatus: "",
};

const els = {
  runButton: document.querySelector("#run-button"),
  runStatus: document.querySelector("#run-status"),
  ideaList: document.querySelector("#idea-list"),
  articleList: document.querySelector("#article-list"),
  topicList: document.querySelector("#topic-list"),
  sourceList: document.querySelector("#source-list"),
  articleCount: document.querySelector("#article-count"),
  ideaCount: document.querySelector("#idea-count"),
  topicCount: document.querySelector("#topic-count"),
  sourceCount: document.querySelector("#source-count"),
  healthySourceCount: document.querySelector("#healthy-source-count"),
  watchCount: document.querySelector("#watch-count"),
  archiveCount: document.querySelector("#archive-count"),
  aiCount: document.querySelector("#ai-count"),
  latestFetch: document.querySelector("#latest-fetch"),
};

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function refresh() {
  const signalQuery = state.signalStatus ? `&status=${encodeURIComponent(state.signalStatus)}` : "";
  const sourceQuery = state.sourceStatus ? `&status=${encodeURIComponent(state.sourceStatus)}` : "";
  const [stats, ideas, articles, topics, sources] = await Promise.all([
    api("/api/stats"),
    api(`/api/ideas?limit=30${signalQuery}`),
    api(`/api/articles?limit=24${signalQuery}`),
    api(`/api/topics?limit=24${signalQuery}`),
    api(`/api/sources?limit=50${sourceQuery}`),
  ]);
  state.ideas = ideas;
  state.articles = articles;
  state.topics = topics;
  state.sources = sources;
  renderStats(stats);
  renderSources();
  renderIdeas();
  renderTopics();
  renderArticles();
}

function renderStats(stats) {
  els.articleCount.textContent = stats.articles ?? 0;
  els.ideaCount.textContent = stats.ideas ?? 0;
  els.topicCount.textContent = stats.topics ?? 0;
  els.sourceCount.textContent = stats.sources ?? 0;
  els.healthySourceCount.textContent = stats.healthy_sources ?? 0;
  els.watchCount.textContent = stats.watching ?? 0;
  els.archiveCount.textContent = stats.archived ?? 0;
  els.aiCount.textContent = stats.ai_analyzed ?? 0;
  els.latestFetch.textContent = formatDate(stats.latest_fetch);
}

function renderSources() {
  if (!state.sources.length) {
    els.sourceList.innerHTML = `<div class="empty">No source runs yet.</div>`;
    return;
  }

  els.sourceList.innerHTML = state.sources.map((source) => `
    <article class="source-row">
      <div>
        <h3>${escapeHtml(source.name)}</h3>
        <div class="meta">
          <span class="status ${statusClass(source.status)}">${escapeHtml(source.status)}</span>
          <span>${escapeHtml(source.kind)}</span>
          <span>${escapeHtml(source.category)}</span>
          <span>${Number(source.last_duration_ms || 0)} ms</span>
          <span>${formatDate(source.last_finished_at)}</span>
        </div>
      </div>
      <div class="source-metrics">
        <span>${Number(source.last_fetched_count || 0)} fetched</span>
        <span>${Number(source.last_new_count || 0)} new</span>
        <span>${Number(source.total_runs || 0)} runs</span>
      </div>
      ${source.last_error ? `<p>${escapeHtml(source.last_error)}</p>` : ""}
    </article>
  `).join("");
}

function renderIdeas() {
  if (!state.ideas.length) {
    els.ideaList.innerHTML = `<div class="empty">No ideas yet. Run a collection job or use the sample sources first.</div>`;
    return;
  }

  els.ideaList.innerHTML = state.ideas.map((idea) => `
    <article class="idea-card">
      <header>
        <div>
          <span class="domain">${escapeHtml(idea.domain)}</span>
          <span class="status ${statusClass(idea.recommendation)}">${escapeHtml(idea.recommendation || "validate")}</span>
          <h3>${escapeHtml(idea.title)}</h3>
        </div>
        <div class="score">${Number(idea.score).toFixed(1)}</div>
      </header>
      <div class="idea-grid">
        ${field("Target user", idea.target_user)}
        ${field("Pain point", idea.pain_point)}
        ${field("Product direction", idea.product_idea)}
        ${field("Monetization", idea.monetization)}
        ${field("Next action", idea.next_action)}
        ${listField("MVP", idea.mvp_steps)}
        ${listField("Validation", idea.validation_plan)}
        ${field("Content angle", idea.content_angle)}
        ${listField("Risks", idea.risks)}
      </div>
      <p><a href="${escapeAttr(idea.article_url)}" target="_blank" rel="noreferrer">Open source signal</a></p>
    </article>
  `).join("");
}

function renderTopics() {
  if (!state.topics.length) {
    els.topicList.innerHTML = `<p class="empty">No long-term topics yet.</p>`;
    return;
  }

  els.topicList.innerHTML = state.topics.map((topic) => `
    <article class="article">
      <h3><a href="${escapeAttr(topic.last_article_url)}" target="_blank" rel="noreferrer">${escapeHtml(topic.title)}</a></h3>
      <div class="meta">
        <span class="status ${statusClass(topic.status)}">${escapeHtml(topic.status)}</span>
        <span>${escapeHtml(topic.domain)}</span>
        <span>${Number(topic.best_score || 0).toFixed(1)}</span>
        <span>${Number(topic.signal_count || 0)} signals</span>
      </div>
      <p>${escapeHtml(topic.next_action || "")}</p>
    </article>
  `).join("");
}

function renderArticles() {
  if (!state.articles.length) {
    els.articleList.innerHTML = `<p class="empty">No signals yet.</p>`;
    return;
  }

  els.articleList.innerHTML = state.articles.map((article) => `
    <article class="article">
      <h3><a href="${escapeAttr(article.url)}" target="_blank" rel="noreferrer">${escapeHtml(article.title)}</a></h3>
      <div class="meta">
        <span>${escapeHtml(article.source)}</span>
        <span>${escapeHtml(article.domain || "Unscored")}</span>
        <span>${Number(article.score || 0).toFixed(1)}</span>
        <span class="status ${statusClass(article.recommendation)}">${escapeHtml(article.recommendation || "archive")}</span>
        <span>${escapeHtml(article.analysis_mode || "rules")}</span>
      </div>
      ${article.ai_summary ? `<p>${escapeHtml(article.ai_summary)}</p>` : ""}
      ${article.ai_opportunity ? `<p><strong>AI:</strong> ${escapeHtml(article.ai_opportunity)}</p>` : ""}
      ${renderDimensions(article.dimension_scores)}
    </article>
  `).join("");
}

function renderDimensions(value) {
  if (!value) return "";
  let dimensions = {};
  try {
    dimensions = typeof value === "string" ? JSON.parse(value) : value;
  } catch {
    return "";
  }
  const labels = {
    willingness_to_pay: "Pay",
    pain_intensity: "Pain",
    reachability: "Reach",
    solo_feasibility: "Solo",
    seven_day_validation: "7d",
    content_potential: "Content",
    timing: "Timing",
  };
  return `
    <div class="dimensions">
      ${Object.entries(labels).map(([key, label]) => {
        const score = Number(dimensions[key] || 0);
        const width = Math.max(0, Math.min(100, (score / 5) * 100));
        return `
          <div class="dimension">
            <span>${label}</span>
            <div><i style="width:${width}%"></i></div>
            <b>${score.toFixed(1)}</b>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function field(title, value) {
  return `
    <section>
      <h4>${title}</h4>
      <p>${escapeHtml(value || "-")}</p>
    </section>
  `;
}

function listField(title, value) {
  const items = String(value || "")
    .split("\n")
    .filter(Boolean)
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  return `
    <section>
      <h4>${title}</h4>
      <ul>${items || "<li>-</li>"}</ul>
    </section>
  `;
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

function statusClass(value) {
  const normalized = String(value || "").replaceAll("_", "-");
  return `status-${normalized || "unknown"}`;
}

document.querySelectorAll("[data-signal-status]").forEach((button) => {
  button.addEventListener("click", async () => {
    state.signalStatus = button.dataset.signalStatus || "";
    setActive("[data-signal-status]", button);
    await refresh();
  });
});

document.querySelectorAll("[data-source-status]").forEach((button) => {
  button.addEventListener("click", async () => {
    state.sourceStatus = button.dataset.sourceStatus || "";
    setActive("[data-source-status]", button);
    await refresh();
  });
});

function setActive(selector, activeButton) {
  document.querySelectorAll(selector).forEach((button) => {
    button.classList.toggle("active", button === activeButton);
  });
}

els.runButton.addEventListener("click", async () => {
  els.runButton.disabled = true;
  els.runStatus.textContent = "Collecting...";
  try {
    const result = await api("/api/run", { method: "POST" });
    const failed = Object.keys(result.failed_sources || {}).length;
    els.runStatus.textContent = `Added ${result.inserted_articles} signals, ${result.inserted_ideas} ideas, ${result.inserted_topics} topics across ${result.source_runs} sources; AI ${result.ai_analyzed || 0}${failed ? `, ${failed} failed` : ""}`;
    await refresh();
  } catch (error) {
    els.runStatus.textContent = error.message;
  } finally {
    els.runButton.disabled = false;
  }
});

refresh().catch((error) => {
  els.runStatus.textContent = error.message;
});
