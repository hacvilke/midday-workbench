const form = document.querySelector("#composer");
const promptInput = document.querySelector("#prompt");
const messages = document.querySelector("#messages");
const providerStatus = document.querySelector("#providerStatus");
const toolList = document.querySelector("#toolList");
const topbarBadge = document.querySelector("#topbarBadge");
const healthStatus = document.querySelector("#healthStatus");
const toolHealthStatus = document.querySelector("#toolHealthStatus");
const metricsPanel = document.querySelector("#metricsPanel");
const operationalReview = document.querySelector("#operationalReview");
const clearMemoryButton = document.querySelector("#clearMemory");
const toolSelect = document.querySelector("#toolSelect");
const toolQuery = document.querySelector("#toolQuery");
const runToolButton = document.querySelector("#runTool");
const toolOutput = document.querySelector("#toolOutput");
const inspectRouteButton = document.querySelector("#inspectRoute");
const routeOutput = document.querySelector("#routeOutput");
const delegationOutput = document.querySelector("#delegationOutput");
const recentDecisions = document.querySelector("#recentDecisions");
const commandInput = document.querySelector("#commandInput");
const runCommandButton = document.querySelector("#runCommand");
const runQualityGatesButton = document.querySelector("#runQualityGates");
const commandPolicy = document.querySelector("#commandPolicy");
const commandOutput = document.querySelector("#commandOutput");
const recentCommands = document.querySelector("#recentCommands");
const qualityGates = document.querySelector("#qualityGates");
const graphNodes = document.querySelector("#graphNodes");
const graphEdges = document.querySelector("#graphEdges");
const graphCentrality = document.querySelector("#graphCentrality");
const recentRuns = document.querySelector("#recentRuns");
const runDetail = document.querySelector("#runDetail");
const sessionList = document.querySelector("#sessionList");
const promptHarness = document.querySelector("#promptHarness");
const contextWindow = document.querySelector("#contextWindow");
const clearContextWindowButton = document.querySelector("#clearContextWindow");
const clearRunsButton = document.querySelector("#clearRuns");
const fileEditorPath = document.querySelector("#fileEditorPath");
const fileEditorContent = document.querySelector("#fileEditorContent");
const fileEditorStatus = document.querySelector("#fileEditorStatus");
const readFileButton = document.querySelector("#readFileButton");
const writeFileButton = document.querySelector("#writeFileButton");
const sessionId = getSessionId();

let isStreaming = false;

function getSessionId() {
  const existing = localStorage.getItem("mw-session");
  if (existing) return existing;
  const created = crypto.randomUUID();
  localStorage.setItem("mw-session", created);
  return created;
}

function addMessage(role, text) {
  const el = document.createElement("article");
  el.className = `message ${role}`;
  if (role === "agent") {
    el.innerHTML = renderMarkdown(text);
  } else {
    el.textContent = text;
  }
  messages.appendChild(el);
  renderMermaidBlocks(el);
  messages.scrollTop = messages.scrollHeight;
  return el;
}

function addPendingMessage() {
  const el = document.createElement("article");
  el.className = "message agent pending";
  el.innerHTML = `
    <div class="pending-row">
      <span class="spinner"></span>
      <div>
        <strong>Running agent</strong>
        <span class="pending-status">Selecting tools and preparing context...</span>
      </div>
      <time>0.0s</time>
    </div>
  `;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
  const started = performance.now();
  const timer = setInterval(() => {
    const seconds = ((performance.now() - started) / 1000).toFixed(1);
    const time = el.querySelector("time");
    if (time) time.textContent = `${seconds}s`;
  }, 100);
  return { el, timer };
}

function renderRunMetadata(metadata) {
  if (!metadata) return "";
  const tools = metadata.tools_used?.length ? metadata.tools_used : ["no active OSS tool"];
  const steps = metadata.react_steps || [];
  const attempts = metadata.provider_attempts || [];
  const plan = metadata.plan || null;
  const verifierReports = metadata.verifier_reports || [];
  const stepHtml = steps.length
    ? steps
        .map(
          (step, index) => `
            <div class="trace-step">
              <strong>Step ${index + 1}: ${escapeHtml(step.action || "tool")}</strong>
              <span>${escapeHtml(step.observation || "")}</span>
            </div>
          `,
        )
        .join("")
    : `<div class="trace-step muted">No ReAct tool action was needed.</div>`;
  return `
    <details class="run-meta">
      <summary>Run ${escapeHtml(metadata.run_id || "")} · ${tools.length} tool${tools.length === 1 ? "" : "s"} · ${Number(metadata.duration_ms || 0)}ms</summary>
      <div class="meta-grid">
        <div><span>Provider</span><strong>${escapeHtml(metadata.provider || "unknown")}</strong></div>
        <div><span>Memory</span><strong>${Number(metadata.memory_items || 0)} items</strong></div>
        <div><span>Context</span><strong>${metadata.context_attached ? "attached" : "direct"}</strong></div>
        <div><span>Fallback</span><strong>${metadata.fallback_used ? "used" : "no"}</strong></div>
      </div>
      <div class="attempt-list">
        ${attempts
          .map(
            (attempt) => `
              <div class="${attempt.ok ? "ok" : "fail"}">
                <strong>${escapeHtml(attempt.provider || "unknown")}</strong>
                <span>${attempt.ok ? "ok" : "failed"} · ${Number(attempt.duration_ms || 0)}ms</span>
              </div>
            `,
          )
          .join("")}
      </div>
      ${metadata.error ? `<blockquote>${escapeHtml(metadata.error)}</blockquote>` : ""}
      <div class="tool-chips">
        ${tools.map((tool) => `<span>${escapeHtml(tool)}</span>`).join("")}
      </div>
      ${
        plan
          ? `<div class="plan-card">
              <strong>${escapeHtml(plan.intent || "plan")}</strong>
              <span>${escapeHtml(plan.tool || "direct response")}</span>
              <em>${escapeHtml(plan.stop_condition || "")}</em>
            </div>`
          : ""
      }
      ${
        verifierReports.length
          ? `<div class="verifier-list">
              ${verifierReports
                .map(
                  (report) => `
                    <div class="${report.passed ? "ok" : "fail"}">
                      <strong>${report.passed ? "Verifier pass" : "Verifier fail"}</strong>
                      <span>${escapeHtml(report.summary || "")}</span>
                    </div>
                  `,
                )
                .join("")}
            </div>`
          : ""
      }
      <div class="trace-list">${stepHtml}</div>
    </details>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatTimestamp(epochSeconds) {
  if (!epochSeconds) return "never";
  try {
    return new Date(Number(epochSeconds) * 1000).toLocaleString();
  } catch {
    return "unknown";
  }
}

function renderInline(value) {
  return escapeHtml(value)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function renderTable(lines) {
  const rows = lines
    .filter((line) => !/^\|\s*-+/.test(line))
    .map((line) => line.split("|").slice(1, -1).map((cell) => renderInline(cell.trim())));
  if (!rows.length) return "";
  const [head, ...body] = rows;
  return `<table><thead><tr>${head.map((cell) => `<th>${cell}</th>`).join("")}</tr></thead><tbody>${body
    .map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`)
    .join("")}</tbody></table>`;
}

function renderMarkdown(markdown) {
  const lines = markdown.split("\n");
  const html = [];
  let code = [];
  let table = [];
  let inCode = false;
  let codeLang = "";

  function flushCode() {
    if (!code.length) return;
    if (codeLang === "mermaid") {
      html.push(`<div class="mermaid-block"><pre>${escapeHtml(code.join("\n"))}</pre></div>`);
      code = [];
      codeLang = "";
      return;
    }
    const label = codeLang ? `<div class="code-label">${escapeHtml(codeLang)}</div>` : "";
    html.push(`<div class="code-block">${label}<pre><code>${escapeHtml(code.join("\n"))}</code></pre></div>`);
    code = [];
    codeLang = "";
  }

  function flushTable() {
    if (!table.length) return;
    html.push(renderTable(table));
    table = [];
  }

  for (const line of lines) {
    const fence = line.match(/^```(\w+)?/);
    if (fence) {
      if (inCode) {
        flushCode();
        inCode = false;
      } else {
        flushTable();
        inCode = true;
        codeLang = fence[1] || "";
      }
      continue;
    }
    if (inCode) {
      code.push(line);
      continue;
    }
    if (/^\|.+\|$/.test(line.trim())) {
      table.push(line.trim());
      continue;
    }
    flushTable();
    if (!line.trim()) {
      html.push("");
    } else if (line.startsWith("#### ")) {
      html.push(`<h4>${renderInline(line.slice(5))}</h4>`);
    } else if (line.startsWith("### ")) {
      html.push(`<h4>${renderInline(line.slice(4))}</h4>`);
    } else if (line.startsWith("## ")) {
      html.push(`<h3>${renderInline(line.slice(3))}</h3>`);
    } else if (line.startsWith("# ")) {
      html.push(`<h2>${renderInline(line.slice(2))}</h2>`);
    } else if (line.startsWith("> ")) {
      html.push(`<blockquote>${renderInline(line.slice(2))}</blockquote>`);
    } else if (/^- /.test(line)) {
      html.push(`<div class="bullet">${renderInline(line.slice(2))}</div>`);
    } else if (/^\d+\. /.test(line)) {
      html.push(`<div class="numbered">${renderInline(line)}</div>`);
    } else {
      html.push(`<p>${renderInline(line)}</p>`);
    }
  }
  flushCode();
  flushTable();
  return html.join("\n");
}

async function renderMermaidBlocks(root) {
  const blocks = [...root.querySelectorAll(".mermaid-block")];
  if (!blocks.length) return;
  if (!window.mermaid) {
    blocks.forEach((block) => renderSimpleMermaidBlock(block));
    window.addEventListener("mermaid-ready", () => renderMermaidBlocks(root), { once: true });
    return;
  }
  for (const block of blocks) {
    const source = block.textContent.trim();
    if (!source) continue;
    try {
      const id = `mermaid-${crypto.randomUUID().replaceAll("-", "")}`;
      const rendered = await window.mermaid.render(id, source);
      block.innerHTML = rendered.svg;
      block.classList.add("rendered");
    } catch {
      renderSimpleMermaidBlock(block);
      if (!block.classList.contains("rendered")) block.classList.add("failed");
    }
  }
}

function renderSimpleMermaidBlock(block) {
  const source = block.textContent.trim();
  const lines = source.split("\n").map((line) => line.trim()).filter(Boolean);
  if ((lines[0] || "") === "xychart-beta") {
    renderXyChartFallback(block, lines);
    return;
  }
  if (!/^(graph|flowchart)\s+(TD|LR)/.test(lines[0] || "")) return;
  const edges = lines.slice(1).map((line) => {
    const match = line.match(/(.+?)--.*?-->(.+)/) || line.match(/(.+?)-->(.+)/);
    if (!match) return null;
    return [cleanMermaidLabel(match[1]), cleanMermaidLabel(match[2])];
  }).filter(Boolean);
  if (!edges.length) return;
  const nodes = [...new Set(edges.flat())].slice(0, 12);
  const width = 760;
  const rowHeight = 54;
  const height = Math.max(140, nodes.length * rowHeight + 40);
  const positions = new Map(nodes.map((node, index) => [node, { x: index % 2 ? 470 : 80, y: 30 + index * rowHeight }]));
  const edgeSvg = edges.map(([from, to]) => {
    const a = positions.get(from);
    const b = positions.get(to);
    if (!a || !b) return "";
    return `<path d="M${a.x + 150} ${a.y + 18} C${a.x + 240} ${a.y + 18}, ${b.x - 60} ${b.y + 18}, ${b.x} ${b.y + 18}" stroke="#5fbca4" fill="none" stroke-width="2" marker-end="url(#arrow)" />`;
  }).join("");
  const nodeSvg = nodes.map((node) => {
    const pos = positions.get(node);
    return `<g><rect x="${pos.x}" y="${pos.y}" width="170" height="36" rx="8" fill="#17231e" stroke="#314438"/><text x="${pos.x + 12}" y="${pos.y + 23}" fill="#edf1f6" font-size="12">${escapeHtml(node).slice(0, 22)}</text></g>`;
  }).join("");
  block.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Rendered Mermaid graph"><defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#5fbca4"/></marker></defs>${edgeSvg}${nodeSvg}</svg>`;
  block.classList.add("rendered", "fallback-rendered");
}

function renderXyChartFallback(block, lines) {
  const title = readQuotedValue(lines.find((line) => line.startsWith("title ")) || "") || "Chart";
  const series = lines
    .filter((line) => line.startsWith("line "))
    .map((line) => {
      const label = readQuotedValue(line) || "Series";
      const values = (line.match(/\[([^\]]+)\]\s*$/)?.[1] || "")
        .split(",")
        .map((value) => Number(value.trim()))
        .filter((value) => Number.isFinite(value));
      return { label, values };
    })
    .filter((item) => item.values.length);
  if (!series.length) return;

  const width = 760;
  const height = 360;
  const pad = 54;
  const max = Math.max(...series.flatMap((item) => item.values), 100);
  const min = Math.min(...series.flatMap((item) => item.values), 0);
  const span = Math.max(1, max - min);
  const colors = ["#5fbca4", "#f0b85a", "#9db7ff"];
  const xFor = (index, count) => pad + (index / Math.max(1, count - 1)) * (width - pad * 2);
  const yFor = (value) => height - pad - ((value - min) / span) * (height - pad * 2);
  const grid = [0, 1, 2, 3, 4].map((index) => {
    const y = pad + index * ((height - pad * 2) / 4);
    return `<line x1="${pad}" y1="${y}" x2="${width - pad}" y2="${y}" stroke="#26352f" stroke-width="1"/>`;
  }).join("");
  const paths = series.map((item, index) => {
    const points = item.values.map((value, pointIndex) => `${xFor(pointIndex, item.values.length)},${yFor(value)}`).join(" ");
    const color = colors[index % colors.length];
    return `<polyline points="${points}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`;
  }).join("");
  const legends = series.map((item, index) => {
    const y = 34 + index * 20;
    const color = colors[index % colors.length];
    return `<g><rect x="${width - 220}" y="${y - 10}" width="10" height="10" rx="2" fill="${color}"/><text x="${width - 202}" y="${y}" fill="#c8d4cf" font-size="12">${escapeHtml(item.label)}</text></g>`;
  }).join("");
  block.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(title)}"><rect width="${width}" height="${height}" rx="12" fill="#101813"/><text x="${pad}" y="34" fill="#edf1f6" font-size="18" font-weight="700">${escapeHtml(title)}</text>${grid}<line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" stroke="#5b6f65"/><line x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}" stroke="#5b6f65"/>${paths}${legends}</svg>`;
  block.classList.add("rendered", "fallback-rendered");
}

function readQuotedValue(line) {
  return line.match(/"([^"]+)"/)?.[1] || "";
}

function cleanMermaidLabel(value) {
  return value
    .replace(/\[[^\]]*\]/g, (match) => match.slice(1, -1))
    .replace(/[()[\]{};]/g, "")
    .trim()
    .split(/\s+/)[0];
}

function addTradingChart() {
  const card = document.createElement("article");
  card.className = "message agent chart-card";
  const canvas = document.createElement("canvas");
  canvas.width = 900;
  canvas.height = 420;
  card.appendChild(canvas);
  messages.appendChild(card);

  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const pad = 42;
  const volumeHeight = 72;
  const chartHeight = height - pad * 2 - volumeHeight;
  const candles = [];
  let price = 100;
  for (let i = 0; i < 72; i += 1) {
    const open = price;
    const drift = Math.sin(i / 7) * 0.45 + (Math.random() - 0.46) * 2.2;
    const close = Math.max(82, open + drift);
    const high = Math.max(open, close) + Math.random() * 2.8;
    const low = Math.min(open, close) - Math.random() * 2.8;
    const volume = 450 + Math.random() * 1150 + Math.abs(close - open) * 180;
    candles.push({ open, high, low, close, volume });
    price = close;
  }

  const maxPrice = Math.max(...candles.map((c) => c.high));
  const minPrice = Math.min(...candles.map((c) => c.low));
  const maxVolume = Math.max(...candles.map((c) => c.volume));
  const xStep = (width - pad * 2) / candles.length;
  const yForPrice = (value) => pad + ((maxPrice - value) / (maxPrice - minPrice)) * chartHeight;

  ctx.fillStyle = "#101114";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#29313a";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = pad + (chartHeight / 4) * i;
    ctx.beginPath();
    ctx.moveTo(pad, y);
    ctx.lineTo(width - pad, y);
    ctx.stroke();
  }

  ctx.fillStyle = "#cbd3df";
  ctx.font = "700 18px Inter, sans-serif";
  ctx.fillText("Demo Trading Chart", pad, 26);
  ctx.font = "12px Inter, sans-serif";
  ctx.fillStyle = "#8f9aaa";
  ctx.fillText("Generated OHLC candles. Connect market data next.", pad + 190, 26);

  candles.forEach((candle, index) => {
    const x = pad + index * xStep + xStep / 2;
    const up = candle.close >= candle.open;
    const color = up ? "#3c8f7c" : "#d05f5f";
    const yOpen = yForPrice(candle.open);
    const yClose = yForPrice(candle.close);
    const yHigh = yForPrice(candle.high);
    const yLow = yForPrice(candle.low);
    const bodyTop = Math.min(yOpen, yClose);
    const bodyHeight = Math.max(2, Math.abs(yClose - yOpen));
    const bodyWidth = Math.max(4, xStep * 0.58);

    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, yHigh);
    ctx.lineTo(x, yLow);
    ctx.stroke();
    ctx.fillRect(x - bodyWidth / 2, bodyTop, bodyWidth, bodyHeight);

    const volumeTop = height - pad - (candle.volume / maxVolume) * volumeHeight;
    ctx.globalAlpha = 0.45;
    ctx.fillRect(x - bodyWidth / 2, volumeTop, bodyWidth, height - pad - volumeTop);
    ctx.globalAlpha = 1;
  });

  ctx.fillStyle = "#8f9aaa";
  ctx.font = "12px Inter, sans-serif";
  ctx.fillText(minPrice.toFixed(2), width - pad + 8, pad + chartHeight);
  ctx.fillText(maxPrice.toFixed(2), width - pad + 8, pad + 4);
  messages.scrollTop = messages.scrollHeight;
}

// ── SSE streaming ──────────────────────────────────────────────────────────────

function parseSSEChunk(buffer) {
  const events = [];
  const remaining = [];
  const parts = buffer.split("\n\n");
  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i].trim();
    if (!part) continue;
    for (const line of part.split("\n")) {
      if (line.startsWith("data:")) {
        const raw = line.slice(5).trim();
        try {
          events.push(JSON.parse(raw));
        } catch {
          // skip malformed
        }
      }
    }
  }
  return { events, remainder: parts[parts.length - 1] || "" };
}

async function streamChat(prompt) {
  if (isStreaming) return;
  isStreaming = true;

  addMessage("user", prompt);

  const msgEl = document.createElement("article");
  msgEl.className = "message agent streaming";
  messages.appendChild(msgEl);
  messages.scrollTop = messages.scrollHeight;

  let rawText = "";
  let metadataReceived = null;
  let toolBadgesEl = null;

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, session_id: sessionId }),
    });

    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const { events, remainder } = parseSSEChunk(buffer);
      buffer = remainder;

      for (const event of events) {
        if (event.type === "tool") {
          // Show tool badge before the answer text
          if (!toolBadgesEl) {
            toolBadgesEl = document.createElement("div");
            toolBadgesEl.style.marginBottom = "10px";
            msgEl.prepend(toolBadgesEl);
          }
          const badge = document.createElement("span");
          badge.className = "streaming-tool-badge";
          badge.innerHTML = `<span class="dot"></span>${escapeHtml(event.tool)}`;
          toolBadgesEl.appendChild(badge);
        } else if (event.type === "token") {
          rawText += event.token;
          const answerEl = toolBadgesEl
            ? (msgEl.querySelector(".stream-answer") || (() => {
                const el = document.createElement("div");
                el.className = "stream-answer";
                msgEl.appendChild(el);
                return el;
              })())
            : msgEl;
          answerEl.innerHTML = renderMarkdown(rawText);
          messages.scrollTop = messages.scrollHeight;
        } else if (event.type === "file_written") {
          const badge = document.createElement("div");
          badge.className = "file-written-badge";
          badge.innerHTML = `✓ Written: <code>${escapeHtml(event.path)}</code>`;
          msgEl.appendChild(badge);
        } else if (event.type === "done") {
          metadataReceived = event.metadata;
        } else if (event.type === "error") {
          rawText += `\n\n> Error: ${event.error}`;
        }
      }
    }
  } catch (err) {
    rawText = rawText || `Streaming failed: ${err}. Trying standard mode...`;
    // Fallback to non-streaming
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, session_id: sessionId }),
      });
      const data = await response.json();
      rawText = data.answer || rawText;
      metadataReceived = data.metadata;
    } catch {
      // Keep error message
    }
  }

  // Finalize message
  msgEl.classList.remove("streaming");
  const answerEl = msgEl.querySelector(".stream-answer") || msgEl;
  answerEl.innerHTML = renderMarkdown(rawText);
  renderMermaidBlocks(msgEl);
  if (metadataReceived) {
    msgEl.insertAdjacentHTML("beforeend", renderRunMetadata(metadataReceived));
  }
  messages.scrollTop = messages.scrollHeight;

  if (prompt.toLowerCase().includes("trading chart")) addTradingChart();

  loadRecentRuns();
  loadSessions();
  loadContextWindow();
  loadMetrics();
  loadOperationalReview();
  isStreaming = false;
}

// ── Status and panel loaders ───────────────────────────────────────────────────

async function showStatus() {
  try {
    const response = await fetch("/api/status");
    const status = await response.json();
    const provider = status.provider === "offline" ? "offline retrieval" : status.provider;
    providerStatus.textContent = `Provider: ${provider}`;
    topbarBadge.textContent = `${status.tools.length} tools · ${status.provider_route?.join(" → ") || provider}`;
    toolList.innerHTML = "";
    status.tools.forEach((entry) => {
      const clean = entry.replace(/^- /, "");
      const [name, description] = clean.split(": ");
      const item = document.createElement("li");
      item.textContent = name;
      const detail = document.createElement("span");
      detail.textContent = description || "";
      item.appendChild(detail);
      toolList.appendChild(item);
    });
    toolSelect.innerHTML = "";
    (status.tool_records || []).forEach((tool) => {
      const option = document.createElement("option");
      option.value = tool.name;
      option.textContent = tool.name;
      option.title = tool.description;
      toolSelect.appendChild(option);
    });
    const healthResponse = await fetch("/api/health");
    const health = await healthResponse.json();
    healthStatus.textContent = health.passed ? `${health.checks.length}/OK` : "Review";
    healthStatus.className = health.passed ? "ok" : "warn";
    const okTools = (health.tools || []).filter((tool) => tool.status === "ok").length;
    toolHealthStatus.textContent = `${okTools}/${(health.tools || []).length || 0} OK`;
    toolHealthStatus.className = okTools === (health.tools || []).length ? "ok" : "warn";
    addMessage("agent", `Ready. Provider: ${provider}. ${status.tools.length} OSS tools, streaming enabled.`);
  } catch {
    addMessage("agent", "Ready.");
  }
}

async function loadMemory() {
  try {
    const response = await fetch(`/api/memory?session_id=${encodeURIComponent(sessionId)}`);
    const data = await response.json();
    if (!data.messages?.length) return;
    messages.innerHTML = "";
    data.messages.forEach((message) => addMessage(message.role, message.content));
  } catch {
    // Memory is helpful, not required.
  }
}

async function loadRepoGraph() {
  try {
    const response = await fetch("/api/graph");
    const graph = await response.json();
    graphNodes.textContent = graph.nodes.length;
    graphEdges.textContent = graph.edges.length;
    graphCentrality.innerHTML = "";
    (graph.centrality || []).slice(0, 5).forEach(([name, score]) => {
      const row = document.createElement("div");
      row.innerHTML = `<span>${escapeHtml(name)}</span><strong>${Number(score)}</strong>`;
      graphCentrality.appendChild(row);
    });
    if (!graphCentrality.children.length) graphCentrality.textContent = "No edges detected yet.";
  } catch {
    graphCentrality.textContent = "Graph unavailable.";
  }
}

async function loadRecentRuns() {
  try {
    const response = await fetch(`/api/runs?session_id=${encodeURIComponent(sessionId)}`);
    const data = await response.json();
    recentRuns.innerHTML = "";
    if (!data.runs?.length) {
      recentRuns.textContent = "No runs yet.";
      return;
    }
    data.runs.slice(0, 6).forEach((run) => {
      const row = document.createElement("div");
      const tools = run.tools_used?.length ? run.tools_used.join(", ") : "direct";
      row.innerHTML = `
        <strong>${escapeHtml(run.run_id)}</strong>
        <span>${escapeHtml(run.provider)} · ${Number(run.duration_ms || 0)}ms</span>
        <em>${escapeHtml(tools)}</em>
      `;
      row.tabIndex = 0;
      row.title = "Inspect run metadata";
      row.addEventListener("click", () => loadRunDetail(run.run_id));
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          loadRunDetail(run.run_id);
        }
      });
      recentRuns.appendChild(row);
    });
  } catch {
    recentRuns.textContent = "Runs unavailable.";
  }
}

async function loadRunDetail(runId) {
  runDetail.textContent = "Loading run detail...";
  try {
    const response = await fetch(`/api/runs/${encodeURIComponent(runId)}`);
    const data = await response.json();
    if (!response.ok) {
      runDetail.textContent = data.error || "Run detail unavailable.";
      return;
    }
    const run = data.run || {};
    const plan = run.plan || {};
    const delegations = plan.delegations || [];
    const verifier = run.verifier_reports || [];
    runDetail.textContent = [
      `run ${run.run_id}`,
      `intent ${plan.intent || "unknown"}`,
      `tool ${plan.tool || "direct"}`,
      `provider ${run.provider || "unknown"} - ${Number(run.duration_ms || 0)}ms`,
      `delegations ${delegations.map((item) => item.agent_id).join(", ") || "none"}`,
      `verifier ${verifier.map((item) => (item.passed ? "pass" : "fail")).join(", ") || "none"}`,
    ].join("\n");
  } catch {
    runDetail.textContent = "Run detail unavailable.";
  }
}

async function loadSessions() {
  try {
    const response = await fetch("/api/sessions");
    const data = await response.json();
    sessionList.innerHTML = "";
    if (!data.sessions?.length) {
      sessionList.textContent = "No sessions yet.";
      return;
    }
    data.sessions.slice(0, 6).forEach((session) => {
      const row = document.createElement("div");
      const isCurrent = session.session_id === sessionId;
      const summary = isCurrent ? "current" : `${Number(session.run_count || 0)} runs`;
      row.innerHTML = `
        <strong>${escapeHtml(session.session_id)}</strong>
        <span>${escapeHtml(summary)} - ${escapeHtml(formatTimestamp(session.last_active))}</span>
      `;
      sessionList.appendChild(row);
    });
  } catch {
    sessionList.textContent = "Sessions unavailable.";
  }
}

async function loadPromptHarness() {
  try {
    const response = await fetch("/api/prompts");
    const data = await response.json();
    promptHarness.innerHTML = "";
    Object.entries(data)
      .slice(0, 6)
      .forEach(([name, prompt]) => {
        const row = document.createElement("div");
        const preview = String(prompt).replace(/\s+/g, " ").trim().slice(0, 90);
        row.innerHTML = `
          <strong>${escapeHtml(name)}</strong>
          <span>${escapeHtml(preview)}${preview.length >= 90 ? "..." : ""}</span>
        `;
        promptHarness.appendChild(row);
      });
    if (!promptHarness.children.length) {
      promptHarness.textContent = "No prompt harness entries.";
    }
  } catch {
    promptHarness.textContent = "Prompt harness unavailable.";
  }
}

async function loadContextWindow() {
  try {
    const response = await fetch("/api/context-window");
    const data = await response.json();
    const items = data.context_window?.items || [];
    contextWindow.innerHTML = "";
    if (!items.length) {
      contextWindow.textContent = "No chained tool context.";
      return;
    }
    items.slice(-5).reverse().forEach((item) => {
      const row = document.createElement("div");
      row.innerHTML = `
        <strong>${escapeHtml(item.tool)}</strong>
        <span>${escapeHtml(item.summary)}</span>
        <em>${escapeHtml(String(item.content || "").slice(0, 90))}</em>
      `;
      contextWindow.appendChild(row);
    });
  } catch {
    contextWindow.textContent = "Context window unavailable.";
  }
}

async function loadSandboxPolicy() {
  try {
    const response = await fetch("/api/sandbox");
    const data = await response.json();
    commandPolicy.textContent = `Allowed: ${(data.allowed_commands || []).join(", ")}`;
  } catch {
    commandPolicy.textContent = "Sandbox policy unavailable.";
  }
}

async function loadRecentCommands() {
  try {
    const response = await fetch(`/api/commands?session_id=${encodeURIComponent(sessionId)}`);
    const data = await response.json();
    recentCommands.innerHTML = "";
    if (!data.commands?.length) {
      recentCommands.textContent = "No command history yet.";
      return;
    }
    data.commands.slice(0, 5).forEach((entry) => {
      const row = document.createElement("div");
      row.innerHTML = `
        <strong>${escapeHtml(entry.command)}</strong>
        <span>exit ${Number(entry.exit_code)} - ${Number(entry.duration_ms || 0)}ms</span>
        <em>${escapeHtml(entry.verified?.summary || "")}</em>
      `;
      recentCommands.appendChild(row);
    });
  } catch {
    recentCommands.textContent = "Command history unavailable.";
  }
}

async function loadMetrics() {
  try {
    const response = await fetch(`/api/metrics?session_id=${encodeURIComponent(sessionId)}`);
    const data = await response.json();
    const passRate = data.verifier?.pass_rate == null ? "n/a" : `${Math.round(data.verifier.pass_rate * 100)}%`;
    metricsPanel.innerHTML = `
      <div><span>Runs</span><strong>${Number(data.runs?.count || 0)}</strong></div>
      <div><span>Commands</span><strong>${Number(data.commands?.count || 0)}</strong></div>
      <div><span>Decisions</span><strong>${Number(data.decisions?.count || 0)}</strong></div>
      <div><span>Verifier</span><strong>${escapeHtml(passRate)}</strong></div>
    `;
  } catch {
    metricsPanel.textContent = "Metrics unavailable.";
  }
}

async function loadOperationalReview() {
  try {
    const response = await fetch(`/api/operational-review?session_id=${encodeURIComponent(sessionId)}`);
    const data = await response.json();
    const risk = (data.risks || [])[0] || "No risk summary.";
    const next = (data.recommendations || [])[0] || "No recommendation.";
    operationalReview.textContent = [
      `score ${Number(data.score || 0)}/100 (${data.grade || "unknown"})`,
      `risk ${risk}`,
      `next ${next}`,
    ].join("\n");
  } catch {
    operationalReview.textContent = "Operational review unavailable.";
  }
}

async function loadRecentDecisions() {
  try {
    const response = await fetch(`/api/decisions?session_id=${encodeURIComponent(sessionId)}`);
    const data = await response.json();
    recentDecisions.innerHTML = "";
    if (!data.decisions?.length) {
      recentDecisions.textContent = "No decisions yet.";
      return;
    }
    data.decisions.slice(0, 5).forEach((entry) => {
      const row = document.createElement("div");
      const decision = entry.decision || {};
      row.innerHTML = `
        <strong>${escapeHtml(entry.kind)}</strong>
        <span>${escapeHtml(entry.input)}</span>
        <em>${escapeHtml(decision.intent || decision.action_type || "decision")}</em>
      `;
      recentDecisions.appendChild(row);
    });
  } catch {
    recentDecisions.textContent = "Decision history unavailable.";
  }
}

async function loadQualityGates() {
  try {
    const response = await fetch("/api/quality");
    const data = await response.json();
    qualityGates.innerHTML = "";
    (data.gates || []).forEach((gate) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "quality-gate";
      button.innerHTML = `<strong>${escapeHtml(gate.name)}</strong><span>${escapeHtml(gate.purpose)}</span>`;
      button.addEventListener("click", () => {
        commandInput.value = gate.command;
        commandInput.focus();
      });
      qualityGates.appendChild(button);
    });
    if (!qualityGates.children.length) {
      qualityGates.textContent = "No quality gates configured.";
    }
  } catch {
    qualityGates.textContent = "Quality gates unavailable.";
  }
}

showStatus()
  .then(loadMemory)
  .then(loadRepoGraph)
  .then(loadRecentRuns)
  .then(loadSessions)
  .then(loadPromptHarness)
  .then(loadContextWindow)
  .then(loadSandboxPolicy)
  .then(loadRecentCommands)
  .then(loadRecentDecisions)
  .then(loadMetrics)
  .then(loadOperationalReview)
  .then(loadQualityGates);

// ── Event handlers ─────────────────────────────────────────────────────────────

clearMemoryButton.addEventListener("click", async () => {
  await fetch("/api/memory/clear", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  messages.innerHTML = "";
  addMessage("agent", "Memory cleared for this browser session.");
});

clearRunsButton.addEventListener("click", async () => {
  await fetch("/api/runs/clear", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  recentRuns.textContent = "No runs yet.";
  loadSessions();
  loadMetrics();
  loadOperationalReview();
});

clearContextWindowButton.addEventListener("click", async () => {
  await fetch("/api/context-window/clear", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  loadContextWindow();
});

runToolButton.addEventListener("click", async () => {
  const tool = toolSelect.value;
  const query = toolQuery.value.trim() || "overview";
  toolOutput.textContent = "Running tool...";
  try {
    const response = await fetch("/api/tools/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool, query }),
    });
    const data = await response.json();
    if (!response.ok) {
      toolOutput.textContent = data.error || "Tool failed.";
      return;
    }
    toolOutput.textContent = `${data.name}\n${data.summary}\n\n${data.content}`;
    loadContextWindow();
  } catch (error) {
    toolOutput.textContent = `Tool request failed: ${error}`;
  }
});

inspectRouteButton.addEventListener("click", async () => {
  const query = toolQuery.value.trim() || promptInput.value.trim() || "hi";
  routeOutput.textContent = "Inspecting route...";
  delegationOutput.textContent = "Inspecting delegation...";
  try {
    const response = await fetch(`/api/route?message=${encodeURIComponent(query)}&session_id=${encodeURIComponent(sessionId)}`);
    const data = await response.json();
    routeOutput.textContent = `intent: ${data.intent}\ntools: ${(data.tools || []).join(", ") || "none"}\nconfidence: ${Number(data.confidence || 0).toFixed(2)}\nreason: ${data.rationale}`;
    const delegationResponse = await fetch(`/api/delegation?message=${encodeURIComponent(query)}`);
    const delegation = await delegationResponse.json();
    delegationOutput.innerHTML = "";
    (delegation.assignments || []).forEach((assignment) => {
      const row = document.createElement("div");
      row.innerHTML = `
        <strong>${escapeHtml(assignment.role)}</strong>
        <span>${escapeHtml(assignment.mode)} - ${escapeHtml(assignment.objective)}</span>
        <em>${escapeHtml((assignment.tools || []).join(", ") || "no tools")}</em>
      `;
      delegationOutput.appendChild(row);
    });
    if (!delegationOutput.children.length) {
      delegationOutput.textContent = "No delegation assignments.";
    }
    loadRecentDecisions();
    loadMetrics();
    loadOperationalReview();
  } catch {
    routeOutput.textContent = "Route inspector unavailable.";
    delegationOutput.textContent = "Delegation unavailable.";
  }
});

runCommandButton.addEventListener("click", async () => {
  const command = commandInput.value.trim();
  if (!command) return;
  commandOutput.textContent = "Running command...";
  try {
    const response = await fetch("/api/sandbox/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command, session_id: sessionId }),
    });
    const data = await response.json();
    if (!response.ok) {
      commandOutput.textContent = data.error || "Command blocked.";
      return;
    }
    commandOutput.textContent = `$ ${data.command}\nexit ${data.exit_code} - ${Number(data.duration_ms || 0)}ms\nverify ${data.verified?.summary || "unknown"}\n\n${data.output || "(no output)"}`;
    loadRecentCommands();
    loadMetrics();
    loadOperationalReview();
  } catch {
    commandOutput.textContent = "Command runner unavailable.";
  }
});

runQualityGatesButton.addEventListener("click", async () => {
  commandOutput.textContent = "Running required quality gates...";
  try {
    const response = await fetch("/api/quality/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ required_only: true }),
    });
    const data = await response.json();
    if (!response.ok) {
      commandOutput.textContent = data.error || "Quality gates unavailable.";
      return;
    }
    commandOutput.textContent = [
      `quality gates ${data.passed ? "passed" : "failed"} - ${Number(data.duration_ms || 0)}ms`,
      ...(data.results || []).map((gate) => `${gate.name}: ${gate.verified?.summary || "unknown"} (${Number(gate.duration_ms || 0)}ms)`),
    ].join("\n");
    loadOperationalReview();
  } catch {
    commandOutput.textContent = "Quality gates unavailable.";
  }
});

// File editor
readFileButton.addEventListener("click", async () => {
  const path = fileEditorPath.value.trim();
  if (!path) {
    fileEditorStatus.textContent = "Enter a file path first.";
    return;
  }
  fileEditorStatus.textContent = "Reading...";
  try {
    const resp = await fetch(`/api/files/read?path=${encodeURIComponent(path)}`);
    const data = await resp.json();
    if (data.error) {
      fileEditorStatus.textContent = `Error: ${data.error}`;
      return;
    }
    fileEditorContent.value = data.content;
    fileEditorStatus.textContent = `Read ${data.size.toLocaleString()} chars from ${data.path}`;
  } catch (err) {
    fileEditorStatus.textContent = `Read failed: ${err}`;
  }
});

writeFileButton.addEventListener("click", async () => {
  const path = fileEditorPath.value.trim();
  const content = fileEditorContent.value;
  if (!path) {
    fileEditorStatus.textContent = "Enter a file path first.";
    return;
  }
  fileEditorStatus.textContent = "Writing...";
  try {
    const resp = await fetch("/api/files/write", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content, confirmed: true }),
    });
    const data = await resp.json();
    if (data.error) {
      fileEditorStatus.textContent = `Error: ${data.error}`;
      return;
    }
    fileEditorStatus.textContent = data.message;
  } catch (err) {
    fileEditorStatus.textContent = `Write failed: ${err}`;
  }
});

// Keyboard shortcut: Ctrl+Enter to submit
promptInput.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
  }
});

// Main chat submit — streaming
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt || isStreaming) return;
  promptInput.value = "";
  await streamChat(prompt);
});
