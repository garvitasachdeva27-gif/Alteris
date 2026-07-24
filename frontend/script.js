// Update this to your deployed backend URL before deploying the frontend.
const API_BASE = "http://127.0.0.1:8000";

// ---------- Shared helpers ----------

function getToken() {
  return localStorage.getItem("alteris_token");
}

function getEmail() {
  return localStorage.getItem("alteris_email");
}

function saveSession(token, email) {
  localStorage.setItem("alteris_token", token);
  localStorage.setItem("alteris_email", email);
}

function clearSession() {
  localStorage.removeItem("alteris_token");
  localStorage.removeItem("alteris_email");
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = "login.html";
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ---------- Signup page ----------

const signupForm = document.getElementById("signup-form");
if (signupForm) {
  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const errorEl = document.getElementById("signup-error");
    const btn = document.getElementById("signup-btn");

    errorEl.textContent = "";
    btn.textContent = "Creating account...";
    btn.disabled = true;

    try {
      const res = await fetch(`${API_BASE}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Signup failed");
      }

      saveSession(data.access_token, email);
      window.location.href = "dashboard.html";
    } catch (err) {
      errorEl.textContent = err.message;
      btn.textContent = "Sign Up";
      btn.disabled = false;
    }
  });
}

// ---------- Login page ----------

const loginForm = document.getElementById("login-form");
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const errorEl = document.getElementById("login-error");
    const btn = document.getElementById("login-btn");

    errorEl.textContent = "";
    btn.textContent = "Logging in...";
    btn.disabled = true;

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Login failed");
      }

      saveSession(data.access_token, email);
      window.location.href = "dashboard.html";
    } catch (err) {
      errorEl.textContent = err.message;
      btn.textContent = "Log In";
      btn.disabled = false;
    }
  });
}

// ---------- Dashboard page ----------

const promptGrid = document.getElementById("prompt-grid");

if (promptGrid) {
  requireAuth();
  document.getElementById("user-email").textContent = getEmail();

  const modal = document.getElementById("prompt-modal");
  const promptForm = document.getElementById("prompt-form");
  const modalTitle = document.getElementById("modal-title");
  const emptyState = document.getElementById("empty-state");

  document.getElementById("logout-btn").addEventListener("click", () => {
    clearSession();
    window.location.href = "login.html";
  });

  document.getElementById("new-prompt-btn").addEventListener("click", () => {
    openModal();
  });

  document.getElementById("cancel-modal-btn").addEventListener("click", () => {
    closeModal();
  });

  function openModal(prompt = null) {
    document.getElementById("prompt-id").value = prompt ? prompt.id : "";
    document.getElementById("prompt-title").value = prompt ? prompt.title : "";
    document.getElementById("prompt-category").value = prompt ? prompt.category : "";
    document.getElementById("prompt-content").value = prompt ? prompt.content : "";
    modalTitle.textContent = prompt ? "Edit Prompt" : "New Prompt";
    modal.style.display = "flex";
  }

  function closeModal() {
    modal.style.display = "none";
    promptForm.reset();
  }

  async function apiRequest(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${getToken()}`,
        ...(options.headers || {}),
      },
    });

    if (res.status === 401) {
      clearSession();
      window.location.href = "login.html";
      return null;
    }

    return res;
  }

  async function loadPrompts() {
    const res = await apiRequest("/prompts");
    if (!res) return;
    const prompts = await res.json();

    promptGrid.innerHTML = "";
    emptyState.style.display = prompts.length === 0 ? "block" : "none";

    prompts.forEach((prompt) => {
      const card = document.createElement("div");
      card.className = "prompt-card";
      card.innerHTML = `
        <span class="prompt-card-category">${prompt.category}</span>
        <div class="prompt-card-title">${escapeHtml(prompt.title)}</div>
        <div class="prompt-card-preview">${escapeHtml(prompt.content)}</div>
        <div class="prompt-card-footer">
          <span>Updated ${new Date(prompt.updated_at).toLocaleDateString()}</span>
          <button class="prompt-card-delete" data-id="${prompt.id}">Delete</button>
        </div>
      `;

      card.addEventListener("click", (e) => {
        if (e.target.classList.contains("prompt-card-delete")) return;
        window.location.href = `prompt-detail.html?id=${prompt.id}`;
      });

      card.querySelector(".prompt-card-delete").addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!confirm("Delete this prompt?")) return;
        await apiRequest(`/prompts/${prompt.id}`, { method: "DELETE" });
        loadPrompts();
      });

      promptGrid.appendChild(card);
    });
  }

  promptForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("prompt-id").value;
    const title = document.getElementById("prompt-title").value;
    const category = document.getElementById("prompt-category").value || "General";
    const content = document.getElementById("prompt-content").value;

    const body = JSON.stringify({ title, category, content });

    if (id) {
      await apiRequest(`/prompts/${id}`, { method: "PUT", body });
    } else {
      await apiRequest("/prompts", { method: "POST", body });
    }

    closeModal();
    loadPrompts();
  });

  loadPrompts();
}

// ---------- Prompt Detail / Workspace page ----------

const runBtn = document.getElementById("run-btn");

if (runBtn) {
  requireAuth();

  const urlParams = new URLSearchParams(window.location.search);
  const promptId = urlParams.get("id");

  if (!promptId) {
    window.location.href = "dashboard.html";
  }

  const systemPromptView = document.getElementById("system-prompt-view");
  const titleDisplay = document.getElementById("prompt-title-display");
  const categoryDisplay = document.getElementById("prompt-category-display");
  const responseBox = document.getElementById("response-box");
  const responseMeta = document.getElementById("response-meta");
  const runError = document.getElementById("run-error");
  const historyList = document.getElementById("history-list");

  async function apiRequest(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${getToken()}`,
        ...(options.headers || {}),
      },
    });

    if (res.status === 401) {
      clearSession();
      window.location.href = "login.html";
      return null;
    }

    return res;
  }

  async function loadPromptDetails() {
    const res = await apiRequest(`/prompts/${promptId}`);
    if (!res || !res.ok) return;
    const prompt = await res.json();

    titleDisplay.textContent = prompt.title;
    categoryDisplay.textContent = prompt.category;
    systemPromptView.value = prompt.content;
  }

  async function loadHistory() {
    const res = await apiRequest(`/prompts/${promptId}/history`);
    if (!res || !res.ok) return;
    const executions = await res.json();

    historyList.innerHTML = "";

    if (executions.length === 0) {
      historyList.innerHTML = `<p class="response-placeholder">No test runs yet.</p>`;
      return;
    }

    executions.forEach((exec) => {
      const item = document.createElement("div");
      item.className = "history-item";
      item.innerHTML = `
        <div class="history-item-top">
          <span>${new Date(exec.created_at).toLocaleString()}</span>
          <span>${exec.model} · ${exec.total_tokens} tokens · ${exec.latency_seconds}s</span>
        </div>
        <div class="history-item-input">Input: ${escapeHtml(exec.test_input)}</div>
        <div class="history-item-response">${escapeHtml(exec.response)}</div>
      `;
      historyList.appendChild(item);
    });
  }

  runBtn.addEventListener("click", async () => {
    const testInput = document.getElementById("test-input").value.trim();
    const model = document.getElementById("model-select").value;

    if (!testInput) {
      runError.textContent = "Enter a test input first.";
      return;
    }

    runError.textContent = "";
    runBtn.textContent = "Running...";
    runBtn.disabled = true;
    responseBox.innerHTML = `<span class="response-placeholder">Generating response...</span>`;
    responseMeta.textContent = "";

    try {
      const res = await apiRequest(`/prompts/${promptId}/execute`, {
        method: "POST",
        body: JSON.stringify({ test_input: testInput, model }),
      });

      if (!res) return;
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Execution failed");
      }

      responseBox.textContent = data.response;
      responseMeta.textContent =
        `${data.model} · ${data.total_tokens} tokens · ${data.latency_seconds}s`;

      loadHistory();
      if (typeof loadAnalytics === "function") loadAnalytics();
    } catch (err) {
      runError.textContent = err.message;
      responseBox.innerHTML = `<span class="response-placeholder">Run the prompt to see a response here.</span>`;
    } finally {
      runBtn.textContent = "Run Prompt";
      runBtn.disabled = false;
    }
  });

  loadPromptDetails();
  loadHistory();
}

// ---------- Prompt Detail: Versions + Analytics ----------

const saveVersionBtn = document.getElementById("save-version-btn");
let loadAnalytics; // hoisted so the execute handler above can call it if defined

if (saveVersionBtn) {
  const urlParams = new URLSearchParams(window.location.search);
  const promptId = urlParams.get("id");

  document.getElementById("compare-link").href = `compare.html?id=${promptId}`;

  async function apiReq(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${getToken()}`,
        ...(options.headers || {}),
      },
    });
    if (res.status === 401) {
      clearSession();
      window.location.href = "login.html";
      return null;
    }
    return res;
  }

  loadAnalytics = async function () {
    const res = await apiReq(`/prompts/${promptId}/analytics`);
    if (!res || !res.ok) return;
    const data = await res.json();

    document.getElementById("stat-total-runs").textContent = data.total_runs;
    document.getElementById("stat-avg-tokens").textContent = data.avg_tokens || "—";
    document.getElementById("stat-avg-latency").textContent =
      data.avg_latency ? `${data.avg_latency}s` : "—";
  };

  async function loadVersions() {
    const res = await apiReq(`/prompts/${promptId}/versions`);
    if (!res || !res.ok) return;
    const versionsData = await res.json();

    const list = document.getElementById("version-list");
    list.innerHTML = "";

    if (versionsData.length === 0) {
      list.innerHTML = `<p class="response-placeholder">No versions saved yet. Save your current prompt as v1 to start tracking changes.</p>`;
      return;
    }

    versionsData.forEach((v) => {
      const item = document.createElement("div");
      item.className = "version-item";
      item.innerHTML = `
        <div class="version-item-info">
          <span class="version-item-number">v${v.version_number}</span>
          <span class="version-item-note">${v.note ? escapeHtml(v.note) : "No note"}</span>
          <span class="version-item-date">${new Date(v.created_at).toLocaleString()}</span>
        </div>
        <div class="version-item-actions">
          <button class="btn btn-secondary btn-small" data-revert="${v.id}">Revert</button>
        </div>
      `;
      item.querySelector("[data-revert]").addEventListener("click", async () => {
        if (!confirm(`Revert live prompt to v${v.version_number}? This won't delete any version history.`)) return;
        await apiReq(`/prompts/${promptId}/versions/${v.id}/revert`, { method: "POST" });
        loadPromptDetailsAfterRevert();
        loadVersions();
      });
      list.appendChild(item);
    });
  }

  async function loadPromptDetailsAfterRevert() {
    const res = await apiReq(`/prompts/${promptId}`);
    if (!res || !res.ok) return;
    const prompt = await res.json();
    const systemPromptView = document.getElementById("system-prompt-view");
    if (systemPromptView) systemPromptView.value = prompt.content;
  }

  saveVersionBtn.addEventListener("click", async () => {
    const note = document.getElementById("version-note").value.trim();
    saveVersionBtn.textContent = "Saving...";
    saveVersionBtn.disabled = true;

    await apiReq(`/prompts/${promptId}/versions`, {
      method: "POST",
      body: JSON.stringify({ note: note || null }),
    });

    document.getElementById("version-note").value = "";
    saveVersionBtn.textContent = "Save Current as Version";
    saveVersionBtn.disabled = false;
    loadVersions();
  });

  loadAnalytics();
  loadVersions();
}

// ---------- Compare page ----------

const runCompareBtn = document.getElementById("run-compare-btn");

if (runCompareBtn) {
  requireAuth();

  const urlParams = new URLSearchParams(window.location.search);
  const promptId = urlParams.get("id");

  if (!promptId) {
    window.location.href = "dashboard.html";
  }

  document.getElementById("back-link").href = `prompt-detail.html?id=${promptId}`;

  const versionASelect = document.getElementById("version-a-select");
  const versionBSelect = document.getElementById("version-b-select");
  const compareError = document.getElementById("compare-error");

  async function apiReq(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${getToken()}`,
        ...(options.headers || {}),
      },
    });
    if (res.status === 401) {
      clearSession();
      window.location.href = "login.html";
      return null;
    }
    return res;
  }

  async function loadVersionOptions() {
    const res = await apiReq(`/prompts/${promptId}/versions`);
    if (!res || !res.ok) return;
    const versionsData = await res.json();

    const currentOption = `<option value="">Current (live prompt)</option>`;
    const versionOptions = versionsData
      .map((v) => `<option value="${v.id}">v${v.version_number} ${v.note ? "— " + v.note : ""}</option>`)
      .join("");

    versionASelect.innerHTML = currentOption + versionOptions;
    versionBSelect.innerHTML = currentOption + versionOptions;

    // Sensible defaults: A = current, B = most recent saved version (if any)
    if (versionsData.length > 0) {
      versionBSelect.value = versionsData[0].id;
    }
  }

  runCompareBtn.addEventListener("click", async () => {
    const testInput = document.getElementById("compare-test-input").value.trim();
    if (!testInput) {
      compareError.textContent = "Enter a test input first.";
      return;
    }

    compareError.textContent = "";
    runCompareBtn.textContent = "Running...";
    runCompareBtn.disabled = true;

    const responseA = document.getElementById("response-a");
    const responseB = document.getElementById("response-b");
    responseA.innerHTML = `<span class="response-placeholder">Generating...</span>`;
    responseB.innerHTML = `<span class="response-placeholder">Generating...</span>`;

    const versionAId = versionASelect.value || null;
    const versionBId = versionBSelect.value || null;

    try {
      const res = await apiReq(`/prompts/${promptId}/compare`, {
        method: "POST",
        body: JSON.stringify({
          test_input: testInput,
          version_a_id: versionAId,
          version_b_id: versionBId,
        }),
      });

      if (!res) return;
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Comparison failed");
      }

      document.getElementById("label-a").textContent = `Version ${data.result_a.label}`;
      document.getElementById("label-b").textContent = `Version ${data.result_b.label}`;
      responseA.textContent = data.result_a.response;
      responseB.textContent = data.result_b.response;
      document.getElementById("meta-a").textContent =
        `${data.result_a.model} · ${data.result_a.total_tokens} tokens · ${data.result_a.latency_seconds}s`;
      document.getElementById("meta-b").textContent =
        `${data.result_b.model} · ${data.result_b.total_tokens} tokens · ${data.result_b.latency_seconds}s`;
    } catch (err) {
      compareError.textContent = err.message;
    } finally {
      runCompareBtn.textContent = "Run Comparison";
      runCompareBtn.disabled = false;
    }
  });

  loadVersionOptions();
}

// ---------- Insights page ----------

const costChartCanvas = document.getElementById("cost-chart");

if (costChartCanvas) {
  requireAuth();

  document.getElementById("logout-btn").addEventListener("click", () => {
    clearSession();
    window.location.href = "login.html";
  });

  async function apiReqInsights(path) {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Authorization": `Bearer ${getToken()}` },
    });
    if (res.status === 401) {
      clearSession();
      window.location.href = "login.html";
      return null;
    }
    return res;
  }

  async function loadInsights() {
    const res = await apiReqInsights("/insights");
    if (!res || !res.ok) return;
    const data = await res.json();

    document.getElementById("stat-total-prompts").textContent = data.global_stats.total_prompts;
    document.getElementById("stat-total-runs-global").textContent = data.global_stats.total_runs;
    document.getElementById("stat-total-tokens").textContent = data.global_stats.total_tokens.toLocaleString();
    document.getElementById("stat-total-cost").textContent = `$${data.global_stats.total_cost_usd.toFixed(4)}`;

    renderCostChart(data.cost_over_time);
    renderCategoryChart(data.category_usage);
  }

  function renderCostChart(points) {
    const emptyEl = document.getElementById("cost-chart-empty");
    if (points.length === 0) {
      emptyEl.style.display = "block";
      costChartCanvas.style.display = "none";
      return;
    }
    emptyEl.style.display = "none";
    costChartCanvas.style.display = "block";

    new Chart(costChartCanvas, {
      type: "line",
      data: {
        labels: points.map((p) => p.date),
        datasets: [{
          label: "Cost (USD)",
          data: points.map((p) => p.cost_usd),
          borderColor: "#5E8BFF",
          backgroundColor: "rgba(94, 139, 255, 0.15)",
          fill: true,
          tension: 0.35,
          pointRadius: 3,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#94A3B8" }, grid: { color: "rgba(255,255,255,0.05)" } },
          y: { ticks: { color: "#94A3B8" }, grid: { color: "rgba(255,255,255,0.05)" } },
        },
      },
    });
  }

  function renderCategoryChart(points) {
    const emptyEl = document.getElementById("category-chart-empty");
    const chartCanvas = document.getElementById("category-chart");
    if (points.length === 0) {
      emptyEl.style.display = "block";
      chartCanvas.style.display = "none";
      return;
    }
    emptyEl.style.display = "none";
    chartCanvas.style.display = "block";

    new Chart(chartCanvas, {
      type: "bar",
      data: {
        labels: points.map((p) => p.category),
        datasets: [{
          label: "Total Tokens",
          data: points.map((p) => p.total_tokens),
          backgroundColor: "#7DD3FC",
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#94A3B8" }, grid: { display: false } },
          y: { ticks: { color: "#94A3B8" }, grid: { color: "rgba(255,255,255,0.05)" } },
        },
      },
    });
  }

  loadInsights();
}
