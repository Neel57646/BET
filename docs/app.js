const fmtPercent = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;
const fmtEv = (value) => `${Number(value || 0) >= 0 ? "+" : ""}${Number(value || 0).toFixed(2)}`;
const fmtOdds = (value) => Number(value || 0).toFixed(2);

function statusLabel(status) {
  if (status === "value_bets") return "Value Bets Found";
  if (status === "no_value_bets") return "No Value Bets";
  return "Waiting";
}

function callClass(recommendation) {
  if (recommendation === "Value Bet") return "good";
  if (recommendation === "Watchlist") return "warn";
  return "bad";
}

function card(candidate) {
  const reasons = (candidate.reasons || [])
    .slice(0, 4)
    .map((reason) => `<li>${escapeHtml(reason)}</li>`)
    .join("");

  return `
    <article class="card">
      <p class="meta">${escapeHtml(candidate.sport || "")}</p>
      <h3>${escapeHtml(candidate.match || "")}</h3>
      <div class="pill-row">
        <span class="pill">Side: ${escapeHtml(candidate.side || "")}</span>
        <span class="pill">Odds: ${fmtOdds(candidate.odds)}</span>
        <span class="pill">Model: ${fmtPercent(candidate.model_probability)}</span>
        <span class="pill good">Edge: ${fmtPercent(candidate.edge)}</span>
        <span class="pill">EV: ${fmtEv(candidate.expected_value)}</span>
        <span class="pill">Confidence: ${candidate.confidence || 0}/100</span>
      </div>
      <ul class="reasons">${reasons}</ul>
    </article>
  `;
}

function emptyState(text) {
  return `<div class="empty">${escapeHtml(text)}</div>`;
}

function row(candidate) {
  const cls = callClass(candidate.recommendation);
  return `
    <tr>
      <td>${escapeHtml(candidate.match || "")}</td>
      <td>${escapeHtml(candidate.side || "")}</td>
      <td>${fmtOdds(candidate.odds)}</td>
      <td>${fmtPercent(candidate.model_probability)}</td>
      <td>${fmtPercent(candidate.edge)}</td>
      <td>${fmtEv(candidate.expected_value)}</td>
      <td>${candidate.confidence || 0}/100</td>
      <td class="${cls}">${escapeHtml(candidate.recommendation || "")}</td>
    </tr>
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

async function loadDashboard() {
  const response = await fetch(`./data/latest.json?ts=${Date.now()}`);
  if (!response.ok) throw new Error(`Failed to load latest scan: ${response.status}`);
  const data = await response.json();

  document.getElementById("status").textContent = statusLabel(data.status);
  document.getElementById("alert-count").textContent = data.alert_count ?? 0;
  document.getElementById("scanned-events").textContent = data.scanned_events ?? 0;
  document.getElementById("last-updated").textContent = data.generated_at
    ? new Date(data.generated_at).toLocaleString()
    : "-";

  const alerts = data.alerts || [];
  document.getElementById("alerts").innerHTML = alerts.length
    ? alerts.map(card).join("")
    : emptyState("No high-confidence value bets passed the alert threshold in the latest run.");

  const watchlist = data.watchlist || [];
  document.getElementById("watchlist").innerHTML = watchlist.length
    ? watchlist.map(card).join("")
    : emptyState("No watchlist candidates in the latest run.");

  const ranked = data.ranked || [];
  document.getElementById("ranked").innerHTML = ranked.length
    ? ranked.map(row).join("")
    : `<tr><td colspan="8">No scan data yet.</td></tr>`;
}

loadDashboard().catch((error) => {
  document.getElementById("status").textContent = "Error";
  document.getElementById("alerts").innerHTML = emptyState(error.message);
});
