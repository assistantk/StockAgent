let priceChartInstance = null;
let pollInterval = null;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  initChart();
  initRangeInputs();
  initControls();
  fetchMarketData();
  fetchStatus();
  fetchTrades();
  fetchAgents();
  fetchForum();
  fetchLogs();

  // Polling every 2.5s for live simulation data
  pollInterval = setInterval(() => {
    fetchStatus();
    fetchMarketData();
    fetchTrades();
    fetchAgents();
    fetchForum();
    fetchLogs();
  }, 2500);
});

// Setup Chart.js
function initChart() {
  const ctx = document.getElementById("priceChart").getContext("2d");

  // Gradients
  const gradA = ctx.createLinearGradient(0, 0, 0, 300);
  gradA.addColorStop(0, "rgba(56, 189, 248, 0.35)");
  gradA.addColorStop(1, "rgba(56, 189, 248, 0.0)");

  const gradB = ctx.createLinearGradient(0, 0, 0, 300);
  gradB.addColorStop(0, "rgba(168, 85, 247, 0.35)");
  gradB.addColorStop(1, "rgba(168, 85, 247, 0.0)");

  priceChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: ["D1-S1"],
      datasets: [
        {
          label: "Stock A ($)",
          data: [26.78],
          borderColor: "#38bdf8",
          backgroundColor: gradA,
          borderWidth: 2.5,
          pointBackgroundColor: "#38bdf8",
          pointBorderColor: "#fff",
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: true,
          tension: 0.35,
        },
        {
          label: "Stock B ($)",
          data: [42.22],
          borderColor: "#a855f7",
          backgroundColor: gradB,
          borderWidth: 2.5,
          pointBackgroundColor: "#a855f7",
          pointBorderColor: "#fff",
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: true,
          tension: 0.35,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.95)",
          titleColor: "#94a3b8",
          bodyColor: "#f8fafc",
          borderColor: "rgba(255, 255, 255, 0.1)",
          borderWidth: 1,
          padding: 12,
          boxPadding: 6,
          usePointStyle: true,
        },
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.04)" },
          ticks: { color: "#64748b", font: { family: "JetBrains Mono", size: 11 } },
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.04)" },
          ticks: {
            color: "#64748b",
            font: { family: "JetBrains Mono", size: 11 },
            callback: (val) => `$${val}`,
          },
        },
      },
    },
  });
}

function initRangeInputs() {
  const agentsInput = document.getElementById("agentsInput");
  const agentsVal = document.getElementById("agentsVal");
  agentsInput.addEventListener("input", (e) => {
    agentsVal.textContent = e.target.value;
  });

  const daysInput = document.getElementById("daysInput");
  const daysVal = document.getElementById("daysVal");
  daysInput.addEventListener("input", (e) => {
    daysVal.textContent = e.target.value;
  });

  const sessionsInput = document.getElementById("sessionsInput");
  const sessionsVal = document.getElementById("sessionsVal");
  sessionsInput.addEventListener("input", (e) => {
    sessionsVal.textContent = e.target.value;
  });
}

function initControls() {
  const btnStart = document.getElementById("btnStartSim");
  const btnStop = document.getElementById("btnStopSim");
  const btnClearLog = document.getElementById("btnClearLog");

  btnStart.addEventListener("click", async () => {
    const payload = {
      model: document.getElementById("modelSelect").value,
      agents: parseInt(document.getElementById("agentsInput").value, 10),
      days: parseInt(document.getElementById("daysInput").value, 10),
      sessions: parseInt(document.getElementById("sessionsInput").value, 10),
    };

    btnStart.disabled = true;
    try {
      const res = await fetch("/api/simulation/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "Failed to start simulation");
      }
      fetchStatus();
    } catch (err) {
      console.error(err);
      alert("Error starting simulation");
    } finally {
      setTimeout(() => { btnStart.disabled = false; }, 1000);
    }
  });

  btnStop.addEventListener("click", async () => {
    btnStop.disabled = true;
    try {
      await fetch("/api/simulation/stop", { method: "POST" });
      fetchStatus();
    } catch (err) {
      console.error(err);
    } finally {
      btnStop.disabled = false;
    }
  });

  btnClearLog.addEventListener("click", () => {
    document.getElementById("terminalConsole").innerHTML = '<div class="terminal-line text-muted">[Console cleared]</div>';
  });
}

// Fetch Status & Update Controls
async function fetchStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();

    const dot = document.getElementById("simStatusDot");
    const text = document.getElementById("simStatusText");
    const btnStart = document.getElementById("btnStartSim");
    const btnStop = document.getElementById("btnStopSim");
    const progressDays = document.getElementById("simProgressDays");
    const currentSession = document.getElementById("simCurrentSession");
    const activeAgents = document.getElementById("activeAgentsCount");

    if (data.running) {
      dot.className = "status-dot running";
      text.textContent = "Simulation Running (PID: " + data.pid + ")";
      btnStart.disabled = true;
      btnStop.disabled = false;
    } else {
      dot.className = "status-dot";
      text.textContent = data.status === "Completed" ? "Simulation Completed" : "Ready";
      btnStart.disabled = false;
      btnStop.disabled = true;
    }

    if (data.progress) {
      progressDays.textContent = `Day ${data.progress.day} / ${data.progress.total_days}`;
      currentSession.textContent = `Session: ${data.progress.session}`;
      activeAgents.textContent = `Agents: ${data.config?.agents || 10}`;
    }

    if (data.config?.model) {
      const prov = document.getElementById("providerName");
      if (data.config.model.includes("groq") || data.config.model.includes("openai/gpt-oss") || data.config.model.includes("qwen")) {
        prov.textContent = "Groq High-Speed";
      } else if (data.config.model.includes("gemini")) {
        prov.textContent = "Google Gemini";
      } else {
        prov.textContent = "OpenAI API";
      }
    }
  } catch (err) {
    console.error("Status fetch error", err);
  }
}

// Fetch Market & Chart Data
async function fetchMarketData() {
  try {
    const res = await fetch("/api/market");
    const data = await res.json();

    document.getElementById("priceStockA").textContent = `$${data.current_stock_a.toFixed(2)}`;
    document.getElementById("priceStockB").textContent = `$${data.current_stock_b.toFixed(2)}`;

    const elChangeA = document.getElementById("changeStockA");
    elChangeA.textContent = `${data.change_a >= 0 ? "+" : ""}${data.change_a}%`;
    elChangeA.className = `price-change ${data.change_a >= 0 ? "positive" : "negative"}`;

    const elChangeB = document.getElementById("changeStockB");
    elChangeB.textContent = `${data.change_b >= 0 ? "+" : ""}${data.change_b}%`;
    elChangeB.className = `price-change ${data.change_b >= 0 ? "positive" : "negative"}`;

    if (priceChartInstance && data.history && data.history.length > 0) {
      const labels = data.history.map((h) => h.label);
      const dataA = data.history.map((h) => h.stock_a);
      const dataB = data.history.map((h) => h.stock_b);

      priceChartInstance.data.labels = labels;
      priceChartInstance.data.datasets[0].data = dataA;
      priceChartInstance.data.datasets[1].data = dataB;
      priceChartInstance.update("none");
    }
  } catch (err) {
    console.error("Market fetch error", err);
  }
}

// Fetch Trades Feed
async function fetchTrades() {
  try {
    const res = await fetch("/api/trades?limit=25");
    const data = await res.json();

    document.getElementById("totalTradesCount").textContent = data.total_trades.toLocaleString();
    document.getElementById("totalVolumeShares").textContent = `${data.total_volume.toLocaleString()} shares`;

    const feed = document.getElementById("tradesFeed");
    if (!data.trades || data.trades.length === 0) {
      return;
    }

    feed.innerHTML = data.trades.map((t) => `
      <div class="trade-item">
        <div class="trade-agents">
          <span class="stock-badge ${t.stock === 'A' ? 'badge-a' : 'badge-b'}">${t.stock}</span>
          <span class="trade-buyer">Agent #${t.buyer}</span>
          <span class="trade-arrow">&#8592;</span>
          <span class="trade-seller">Agent #${t.seller}</span>
        </div>
        <div class="trade-details">
          <span class="trade-qty">${t.quantity.toLocaleString()} shs</span>
          <span class="trade-price">@ $${t.price.toFixed(2)}</span>
          <span class="text-dim">D${t.day} S${t.session}</span>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Trades fetch error", err);
  }
}

// Fetch Agents Table
async function fetchAgents() {
  try {
    const res = await fetch("/api/agents");
    const data = await res.json();

    document.getElementById("agentCountBadge").textContent = `${data.count} Agents`;
    const tbody = document.getElementById("agentsTableBody");

    if (!data.agents || data.agents.length === 0) {
      return;
    }

    tbody.innerHTML = data.agents.map((a) => `
      <tr>
        <td style="font-weight: 700;">#${a.agent_id}</td>
        <td><span class="persona-tag persona-${a.personality}">${a.personality}</span></td>
        <td style="color: #38bdf8; font-weight: 700;">$${a.total_proper.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
        <td>$${a.cash.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
        <td>$${a.stock_a_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
        <td>$${a.stock_b_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
        <td>
          <span class="badge-neutral">${a.last_action_type.toUpperCase()} ${a.last_stock !== '-' ? a.last_stock : ''}</span>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Agents fetch error", err);
  }
}

// Fetch Forum Messages
async function fetchForum() {
  try {
    const res = await fetch("/api/forum");
    const data = await res.json();

    const feed = document.getElementById("forumFeed");
    if (!data.posts || data.posts.length === 0) {
      return;
    }

    feed.innerHTML = data.posts.map((p) => `
      <div class="forum-card">
        <div class="forum-header">
          <span class="forum-author">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
            Agent #${p.agent_id}
          </span>
          <span class="sentiment-badge sentiment-${p.sentiment}">${p.sentiment}</span>
        </div>
        <div class="forum-msg">${escapeHtml(p.message)}</div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Forum fetch error", err);
  }
}

// Fetch Console Logs
async function fetchLogs() {
  try {
    const res = await fetch("/api/logs?lines=40");
    const data = await res.json();
    const consoleBox = document.getElementById("terminalConsole");

    if (!data.lines || data.lines.length === 0) return;

    consoleBox.innerHTML = data.lines.map((l) => {
      let cls = "terminal-line";
      if (l.includes("INFO")) cls += " info";
      else if (l.includes("WARNING")) cls += " warning";
      else if (l.includes("ERROR")) cls += " error";
      else if (l.includes("DEBUG")) cls += " debug";
      return `<div class="${cls}">${escapeHtml(l)}</div>`;
    }).join("");

    consoleBox.scrollTop = consoleBox.scrollHeight;
  } catch (err) {
    console.error("Logs fetch error", err);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
