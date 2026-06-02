from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.web_app.db import fetch_all, fetch_one


router = APIRouter()


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Daily History</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #07111f;
      --panel: #172231;
      --line: rgba(255,255,255,0.13);
      --text: #eef6ff;
      --muted: #9db0c5;
      --green: #21d391;
      --red: #ff5d6c;
      --blue: #4aa8ff;
      --yellow: #ffd166;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(74,168,255,0.18), transparent 30%),
        radial-gradient(circle at top right, rgba(33,211,145,0.12), transparent 26%),
        #07111f;
      color: var(--text);
      font-family: Arial, sans-serif;
    }

    .app {
      width: 100%;
      max-width: none;
      padding: 22px 34px;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 18px;
      margin-bottom: 18px;
    }

    h1 {
      margin: 0;
      font-size: 34px;
      letter-spacing: -0.04em;
    }

    h2 {
      margin-top: 0;
      letter-spacing: -0.03em;
    }

    .muted {
      color: var(--muted);
      font-size: 14px;
    }

    .tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 18px;
      flex-wrap: wrap;
    }

    .tab {
      padding: 10px 14px;
      background: rgba(255,255,255,0.08);
      border: 1px solid var(--line);
      border-radius: 12px;
      color: var(--text);
      text-decoration: none;
      font-weight: 700;
    }

    .tab.active {
      background: linear-gradient(135deg, rgba(74,168,255,0.45), rgba(33,211,145,0.24));
    }

    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 430px;
      gap: 18px;
      align-items: start;
    }

    .panel {
      background: rgba(23,34,49,0.96);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
      box-shadow: 0 18px 55px rgba(0,0,0,0.34);
    }

    .controls {
      display: grid;
      grid-template-columns: 1.4fr 0.8fr 0.9fr auto;
      gap: 10px;
      margin-bottom: 14px;
      align-items: center;
    }

    select, button, input {
      width: 100%;
      background: #2b3748;
      color: var(--text);
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 12px;
      padding: 11px 12px;
      font-weight: 700;
      outline: none;
    }

    select option {
      background: #101b2b;
      color: var(--text);
    }

    button {
      cursor: pointer;
      background: linear-gradient(135deg, rgba(74,168,255,0.45), rgba(33,211,145,0.24));
      min-width: 100px;
    }

    .native-symbol-select {
      display: none;
    }

    .symbol-combo {
      position: relative;
      width: 100%;
    }

    .symbol-combo-button {
      width: 100%;
      display: grid;
      grid-template-columns: 30px minmax(0, 1fr) 18px;
      align-items: center;
      gap: 10px;
      text-align: left;
      background: #2b3748;
      color: var(--text);
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 12px;
      padding: 9px 12px;
      font-weight: 800;
      cursor: pointer;
    }

    .symbol-combo-icon {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      overflow: hidden;
      background: rgba(255,255,255,0.12);
      font-size: 10px;
      font-weight: 900;
    }

    .symbol-combo-icon img {
      width: 25px;
      height: 25px;
      object-fit: contain;
    }

    .symbol-combo-text {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .symbol-combo-arrow {
      color: var(--muted);
      text-align: right;
    }

    .symbol-combo-menu {
      display: none;
      position: absolute;
      z-index: 50;
      top: calc(100% + 8px);
      left: 0;
      width: min(540px, 95vw);
      max-height: 480px;
      background: #101b2b;
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 16px;
      box-shadow: 0 24px 70px rgba(0,0,0,0.45);
      overflow: hidden;
    }

    .symbol-combo.open .symbol-combo-menu {
      display: block;
    }

    .symbol-search {
      width: calc(100% - 18px);
      margin: 9px;
      background: #1c2a3b;
      color: var(--text);
      border: 1px solid rgba(255,255,255,0.14);
      border-radius: 12px;
      padding: 11px 12px;
      outline: none;
      font-weight: 700;
    }

    .symbol-options {
      max-height: 405px;
      overflow: auto;
      padding: 4px 7px 8px;
    }

    .symbol-option {
      display: grid;
      grid-template-columns: 34px minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      padding: 9px;
      border-radius: 13px;
      cursor: pointer;
    }

    .symbol-option:hover,
    .symbol-option.active {
      background: rgba(255,255,255,0.10);
    }

    .symbol-option-icon {
      width: 30px;
      height: 30px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      overflow: hidden;
      background: rgba(255,255,255,0.12);
      font-size: 10px;
      font-weight: 900;
    }

    .symbol-option-icon img {
      width: 26px;
      height: 26px;
      object-fit: contain;
    }

    .symbol-option-main {
      min-width: 0;
    }

    .symbol-option-main strong,
    .symbol-option-main small {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .symbol-option-main small {
      color: var(--muted);
      margin-top: 2px;
      font-size: 12px;
    }

    .symbol-option-days {
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }

    .status {
      min-height: 22px;
      margin: 6px 0 10px;
      color: var(--muted);
      font-size: 14px;
    }

    .stats {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 10px;
      margin: 14px 0;
    }

    .stat {
      background: rgba(255,255,255,0.07);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 16px;
      padding: 12px;
    }

    .stat span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 5px;
    }

    .stat strong {
      font-size: 17px;
      letter-spacing: -0.03em;
    }

    .chart-box {
      height: calc(100vh - 420px);
      min-height: 430px;
      max-height: 690px;
    }

    .side-list {
      display: grid;
      gap: 10px;
      max-height: calc(100vh - 245px);
      min-height: 520px;
      overflow: auto;
      padding-right: 3px;
    }

    .history-card {
      display: grid;
      grid-template-columns: 44px 1fr;
      gap: 10px;
      align-items: center;
      background: rgba(255,255,255,0.07);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 16px;
      padding: 11px;
      cursor: pointer;
    }

    .history-card:hover {
      background: rgba(255,255,255,0.12);
    }

    .icon {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: rgba(255,255,255,0.12);
      display: grid;
      place-items: center;
      overflow: hidden;
      font-size: 11px;
      font-weight: 800;
    }

    .icon img {
      width: 32px;
      height: 32px;
    }

    .row {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
    }

    .green { color: var(--green); }
    .red { color: var(--red); }
    .yellow { color: var(--yellow); }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 16px;
      font-size: 13px;
    }

    th, td {
      padding: 10px;
      border-bottom: 1px solid rgba(255,255,255,0.12);
      text-align: left;
      white-space: nowrap;
    }

    th {
      color: var(--muted);
    }

    .table-wrap {
      overflow: auto;
    }

    @media (max-width: 1250px) {
      .grid {
        grid-template-columns: 1fr;
      }

      .side-list {
        min-height: 0;
        max-height: 520px;
      }

      .chart-box {
        min-height: 380px;
      }
    }

    @media (max-width: 920px) {
      .app {
        padding: 14px;
      }

      .header {
        flex-direction: column;
      }

      .controls {
        grid-template-columns: 1fr;
      }

      .stats {
        grid-template-columns: 1fr 1fr;
      }

      .chart-box {
        height: 360px;
        min-height: 360px;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <div class="header">
      <div>
        <h1>Daily History</h1>
        <div class="muted">Daily OHLCV history from PostgreSQL daily_klines</div>
      </div>
      <div class="muted" id="lastUpdated">Loading...</div>
    </div>

    <div class="tabs">
      <a class="tab" href="/market-pulse">Market Pulse</a>
      <a class="tab active" href="/daily-history">Daily History</a>
      <a class="tab" href="/live-snapshots">Live Snapshots</a>
      <a class="tab" href="/data-health">Data Health</a>
      <a class="tab" href="/alert-center">Alert Center</a>
    </div>

    <div class="grid">
      <div class="panel">
        <h2>Daily Close Chart</h2>

        <div class="controls">
          <select id="symbolSelect" class="native-symbol-select"></select>

          <div class="symbol-combo" id="symbolCombo">
            <button type="button" class="symbol-combo-button" id="symbolComboButton">
              <span class="symbol-combo-icon" id="selectedSymbolIcon">--</span>
              <span class="symbol-combo-text" id="selectedSymbolText">Select symbol</span>
              <span class="symbol-combo-arrow">▾</span>
            </button>

            <div class="symbol-combo-menu" id="symbolComboMenu">
              <input id="symbolSearch" class="symbol-search" placeholder="Search coin or symbol...">
              <div id="symbolOptions" class="symbol-options"></div>
            </div>
          </div>

          <select id="quoteSelect">
            <option value="">All symbols</option>
            <option value="USDT" selected>USDT pairs</option>
            <option value="USDC">USDC pairs</option>
            <option value="FDUSD">FDUSD pairs</option>
            <option value="BTC">BTC pairs</option>
            <option value="TRY">TRY pairs</option>
          </select>

          <select id="rangeSelect">
            <option value="30" selected>30 days</option>
            <option value="90">90 days</option>
            <option value="180">180 days</option>
            <option value="365">365 days</option>
            <option value="730">2 years</option>
            <option value="1095">3 years</option>
            <option value="0">All history</option>
          </select>

          <button onclick="loadHistory()">Refresh</button>
        </div>

        <div class="status" id="chartStatus">Preparing daily history...</div>

        <div class="stats">
          <div class="stat"><span>Days</span><strong id="statDays">-</strong></div>
          <div class="stat"><span>First Day</span><strong id="statFirstDay">-</strong></div>
          <div class="stat"><span>Last Day</span><strong id="statLastDay">-</strong></div>
          <div class="stat"><span>Range High</span><strong id="statHigh">-</strong></div>
          <div class="stat"><span>Range Low</span><strong id="statLow">-</strong></div>
        </div>

        <div class="chart-box">
          <canvas id="dailyChart"></canvas>
        </div>
      </div>

      <div class="panel">
        <h2>Most Complete Histories</h2>
        <div class="muted">Symbols with the largest number of daily candles</div>
        <div class="side-list" id="historyList"></div>
      </div>
    </div>

    <div class="panel" style="margin-top:18px;">
      <h2>Recent Daily Candles</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Day</th>
              <th>Open</th>
              <th>High</th>
              <th>Low</th>
              <th>Close</th>
              <th>Volume</th>
              <th>Quote Volume</th>
              <th>Trades</th>
            </tr>
          </thead>
          <tbody id="candlesBody"></tbody>
        </table>
      </div>
    </div>
  </div>

<script>
let allSymbols = [];
let historyLeaders = [];
let chart = null;

function fmt(value, digits = 2) {
  if (value === null || value === undefined || isNaN(Number(value))) return "-";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
}

function money(value) {
  if (value === null || value === undefined || isNaN(Number(value))) return "-";
  const n = Number(value);
  if (n >= 1) return "$" + n.toLocaleString(undefined, { maximumFractionDigits: 4 });
  return "$" + n.toLocaleString(undefined, { maximumFractionDigits: 10 });
}

function compact(value) {
  if (value === null || value === undefined || isNaN(Number(value))) return "-";
  return Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 2 }).format(Number(value));
}

function fallbackIcon(baseAsset) {
  return String(baseAsset || "?").slice(0, 2).toUpperCase();
}

function symbolIconHtml(item) {
  if (item && item.image_url) {
    return `<img src="${item.image_url}" onerror="this.remove(); this.parentElement.textContent='${fallbackIcon(item.base_asset)}';">`;
  }
  return fallbackIcon(item?.base_asset || item?.symbol);
}

async function getJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url);
  return await r.json();
}

function selectedQuote() {
  return document.getElementById("quoteSelect").value;
}

function getSymbolItem(symbol) {
  return allSymbols.find(x => x.symbol === symbol) || null;
}

function syncSelectedSymbolDisplay() {
  const symbol = document.getElementById("symbolSelect").value;
  const item = getSymbolItem(symbol);

  document.getElementById("selectedSymbolIcon").innerHTML = symbolIconHtml(item || { symbol });
  document.getElementById("selectedSymbolText").textContent = item
    ? `${item.symbol} (${item.base_asset || "-"} / ${item.quote_asset || "-"})`
    : symbol || "Select symbol";
}

function renderSymbolOptions(filterText = "") {
  const options = document.getElementById("symbolOptions");
  const filter = String(filterText || "").trim().toUpperCase();
  const selected = document.getElementById("symbolSelect").value;

  const filtered = allSymbols.filter(item => {
    const haystack = `${item.symbol || ""} ${item.base_asset || ""} ${item.quote_asset || ""} ${item.name || ""}`.toUpperCase();
    return !filter || haystack.includes(filter);
  });

  options.innerHTML = "";

  filtered.forEach(item => {
    const div = document.createElement("div");
    div.className = "symbol-option" + (item.symbol === selected ? " active" : "");
    div.onclick = () => {
      document.getElementById("symbolSelect").value = item.symbol;
      syncSelectedSymbolDisplay();
      renderSymbolOptions(document.getElementById("symbolSearch").value || "");
      document.getElementById("symbolCombo").classList.remove("open");
      loadHistory();
    };

    div.innerHTML = `
      <div class="symbol-option-icon">${symbolIconHtml(item)}</div>
      <div class="symbol-option-main">
        <strong>${item.symbol}</strong>
        <small>${item.name || item.base_asset || "-"} / ${item.quote_asset || "-"}</small>
      </div>
      <div class="symbol-option-days">${item.days_count || 0} days</div>
    `;

    options.appendChild(div);
  });

  if (filtered.length === 0) {
    options.innerHTML = `<div class="symbol-option"><div></div><div class="muted">No symbol found</div><div></div></div>`;
  }
}

function setupSymbolComboEvents() {
  const combo = document.getElementById("symbolCombo");
  const button = document.getElementById("symbolComboButton");
  const search = document.getElementById("symbolSearch");

  button.addEventListener("click", (event) => {
    event.stopPropagation();
    combo.classList.toggle("open");
    if (combo.classList.contains("open")) {
      search.value = "";
      renderSymbolOptions("");
      setTimeout(() => search.focus(), 50);
    }
  });

  search.addEventListener("click", (event) => event.stopPropagation());
  search.addEventListener("input", () => renderSymbolOptions(search.value));

  document.addEventListener("click", () => combo.classList.remove("open"));
}

async function loadSymbols() {
  const quote = selectedQuote();
  allSymbols = await getJson(`/api/daily-history/symbols?quote=${encodeURIComponent(quote)}`);

  const select = document.getElementById("symbolSelect");
  const current = select.value;
  select.innerHTML = "";

  allSymbols.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.symbol;
    opt.textContent = c.symbol;
    select.appendChild(opt);
  });

  const preferred = allSymbols.find(x => x.symbol === "BTCUSDT");
  const keepCurrent = allSymbols.find(x => x.symbol === current);

  if (keepCurrent) {
    select.value = current;
  } else if (preferred) {
    select.value = "BTCUSDT";
  } else if (allSymbols.length > 0) {
    select.value = allSymbols[0].symbol;
  }

  syncSelectedSymbolDisplay();
  renderSymbolOptions("");
}

async function loadLeaders() {
  const quote = selectedQuote();
  historyLeaders = await getJson(`/api/daily-history/leaders?quote=${encodeURIComponent(quote)}&limit=30`);
  renderLeaders();
}

function renderLeaders() {
  const box = document.getElementById("historyList");
  box.innerHTML = "";

  historyLeaders.forEach(item => {
    const div = document.createElement("div");
    div.className = "history-card";
    div.onclick = () => {
      document.getElementById("symbolSelect").value = item.symbol;
      syncSelectedSymbolDisplay();
      renderSymbolOptions("");
      loadHistory();
      window.scrollTo({ top: 0, behavior: "smooth" });
    };

    div.innerHTML = `
      <div class="icon">${symbolIconHtml(item)}</div>
      <div>
        <div class="row">
          <strong>${item.symbol}</strong>
          <span class="yellow">${item.days_count} days</span>
        </div>
        <div class="row muted">
          <span>${item.name || item.base_asset || "-"} / ${item.quote_asset || "-"}</span>
          <span>${item.first_day || "-"} → ${item.last_day || "-"}</span>
        </div>
      </div>
    `;

    box.appendChild(div);
  });
}

async function loadHistory() {
  const symbol = document.getElementById("symbolSelect").value;
  const days = document.getElementById("rangeSelect").value;

  if (!symbol) return;

  document.getElementById("chartStatus").textContent = `Loading ${symbol} daily history...`;

  const payload = await getJson(`/api/daily-history/detail?symbol=${encodeURIComponent(symbol)}&days=${encodeURIComponent(days)}`);

  document.getElementById("statDays").textContent = payload.summary?.days_count || "-";
  document.getElementById("statFirstDay").textContent = payload.summary?.first_day || "-";
  document.getElementById("statLastDay").textContent = payload.summary?.last_day || "-";
  document.getElementById("statHigh").textContent = money(payload.summary?.range_high);
  document.getElementById("statLow").textContent = money(payload.summary?.range_low);

  renderChart(symbol, payload.points || []);
  renderCandles(payload.candles || []);

  const pointCount = payload.points?.length || 0;
  if (pointCount === 0) {
    document.getElementById("chartStatus").textContent = `No daily history found for ${symbol}.`;
  } else {
    document.getElementById("chartStatus").textContent = `${symbol}: ${pointCount} daily close points.`;
  }

  document.getElementById("lastUpdated").textContent = "Updated: " + new Date().toLocaleString();
}

function renderChart(symbol, points) {
  const labels = points.map(x => x.t);
  const closeValues = points.map(x => x.close);
  const highValues = points.map(x => x.high);
  const lowValues = points.map(x => x.low);

  if (chart) chart.destroy();

  chart = new Chart(document.getElementById("dailyChart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: `${symbol} close`,
          data: closeValues,
          borderWidth: 2,
          tension: 0.3,
          pointRadius: points.length > 150 ? 0 : 2
        },
        {
          label: `${symbol} high`,
          data: highValues,
          borderWidth: 1,
          tension: 0.3,
          pointRadius: 0
        },
        {
          label: `${symbol} low`,
          data: lowValues,
          borderWidth: 1,
          tension: 0.3,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#eef6ff" } }
      },
      scales: {
        x: {
          ticks: { color: "#9db0c5", maxTicksLimit: 10 },
          grid: { color: "rgba(255,255,255,0.05)" }
        },
        y: {
          ticks: { color: "#9db0c5" },
          grid: { color: "rgba(255,255,255,0.07)" }
        }
      }
    }
  });
}

function renderCandles(candles) {
  const body = document.getElementById("candlesBody");
  body.innerHTML = "";

  candles.forEach(c => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${c.day || "-"}</td>
      <td>${money(c.open)}</td>
      <td>${money(c.high)}</td>
      <td>${money(c.low)}</td>
      <td>${money(c.close)}</td>
      <td>${compact(c.volume)}</td>
      <td>${compact(c.quote_volume)}</td>
      <td>${fmt(c.trade_count, 0)}</td>
    `;
    body.appendChild(tr);
  });
}

async function reloadAll() {
  await loadSymbols();
  await loadLeaders();
  await loadHistory();
}

document.getElementById("symbolSelect").addEventListener("change", () => {
  syncSelectedSymbolDisplay();
  loadHistory();
});

document.getElementById("quoteSelect").addEventListener("change", reloadAll);
document.getElementById("rangeSelect").addEventListener("change", loadHistory);

setupSymbolComboEvents();

reloadAll().catch(err => {
  console.error(err);
  document.getElementById("lastUpdated").textContent = "Error: " + err.message;
  document.getElementById("chartStatus").textContent = "Dashboard error: " + err.message;
});
</script>
</body>
</html>
"""


def meta_cte():
    return """
        WITH best_meta AS (
            SELECT DISTINCT ON (symbol_upper)
                symbol_upper,
                coingecko_id,
                name,
                image_url,
                market_cap,
                market_cap_rank,
                total_volume,
                circulating_supply,
                total_supply,
                max_supply
            FROM coin_market_meta_latest
            WHERE source = 'coingecko'
              AND symbol_upper IS NOT NULL
            ORDER BY
                symbol_upper,
                market_cap_rank NULLS LAST,
                market_cap DESC NULLS LAST
        )
    """


@router.get("/daily-history", response_class=HTMLResponse)
def daily_history_page():
    return HTMLResponse(HTML)


@router.get("/api/daily-history/symbols")
def symbols(quote: str = ""):
    quote = quote.upper().strip()

    params = []
    quote_filter = ""

    if quote:
        quote_filter = "AND COALESCE(s.quote_asset, '') = %s"
        params.append(quote)

    sql = f"""
        {meta_cte()}
        SELECT
            d.symbol,
            COALESCE(s.base_asset, '') AS base_asset,
            COALESCE(s.quote_asset, '') AS quote_asset,
            COALESCE(m.name, s.base_asset, '') AS name,
            m.image_url,
            COUNT(*)::integer AS days_count,
            MIN(d.open_time)::date::text AS first_day,
            MAX(d.open_time)::date::text AS last_day
        FROM daily_klines d
        LEFT JOIN market_symbols s
            ON s.source = d.source
           AND s.symbol = d.symbol
        LEFT JOIN best_meta m
            ON m.symbol_upper = UPPER(s.base_asset)
        WHERE d.source = 'binance'
          AND d.interval_name = '1d'
          {quote_filter}
        GROUP BY
            d.symbol,
            s.base_asset,
            s.quote_asset,
            m.name,
            m.image_url
        ORDER BY
            CASE WHEN d.symbol = 'BTCUSDT' THEN 0 ELSE 1 END,
            COUNT(*) DESC,
            d.symbol ASC;
    """

    return fetch_all(sql, tuple(params))


@router.get("/api/daily-history/leaders")
def leaders(
    quote: str = "",
    limit: int = Query(default=30, ge=1, le=100),
):
    quote = quote.upper().strip()

    params = []
    quote_filter = ""

    if quote:
        quote_filter = "AND COALESCE(s.quote_asset, '') = %s"
        params.append(quote)

    params.append(limit)

    sql = f"""
        {meta_cte()}
        SELECT
            d.symbol,
            COALESCE(s.base_asset, '') AS base_asset,
            COALESCE(s.quote_asset, '') AS quote_asset,
            COALESCE(m.name, s.base_asset, '') AS name,
            m.image_url,
            COUNT(*)::integer AS days_count,
            MIN(d.open_time)::date::text AS first_day,
            MAX(d.open_time)::date::text AS last_day
        FROM daily_klines d
        LEFT JOIN market_symbols s
            ON s.source = d.source
           AND s.symbol = d.symbol
        LEFT JOIN best_meta m
            ON m.symbol_upper = UPPER(s.base_asset)
        WHERE d.source = 'binance'
          AND d.interval_name = '1d'
          {quote_filter}
        GROUP BY
            d.symbol,
            s.base_asset,
            s.quote_asset,
            m.name,
            m.image_url
        ORDER BY
            COUNT(*) DESC,
            d.symbol ASC
        LIMIT %s;
    """

    return fetch_all(sql, tuple(params))


@router.get("/api/daily-history/detail")
def daily_detail(symbol: str, days: int = Query(default=30, ge=0, le=5000)):
    symbol = symbol.upper().strip()

    params = [symbol]
    where_days = ""

    if days > 0:
        where_days = "AND open_time >= NOW() - (%s || ' days')::interval"
        params.append(days)

    points_sql = f"""
        SELECT
            open_time::date::text AS t,
            open_price::double precision AS open,
            high_price::double precision AS high,
            low_price::double precision AS low,
            close_price::double precision AS close,
            volume::double precision AS volume,
            quote_volume::double precision AS quote_volume,
            trade_count::bigint AS trade_count
        FROM daily_klines
        WHERE source = 'binance'
          AND interval_name = '1d'
          AND symbol = %s
          {where_days}
        ORDER BY open_time ASC;
    """

    summary_sql = f"""
        SELECT
            COUNT(*)::integer AS days_count,
            MIN(open_time)::date::text AS first_day,
            MAX(open_time)::date::text AS last_day,
            MAX(high_price)::double precision AS range_high,
            MIN(low_price)::double precision AS range_low,
            SUM(volume)::double precision AS total_volume,
            SUM(quote_volume)::double precision AS total_quote_volume
        FROM daily_klines
        WHERE source = 'binance'
          AND interval_name = '1d'
          AND symbol = %s
          {where_days};
    """

    candles_sql = """
        SELECT
            open_time::date::text AS day,
            open_price::double precision AS open,
            high_price::double precision AS high,
            low_price::double precision AS low,
            close_price::double precision AS close,
            volume::double precision AS volume,
            quote_volume::double precision AS quote_volume,
            trade_count::bigint AS trade_count
        FROM daily_klines
        WHERE source = 'binance'
          AND interval_name = '1d'
          AND symbol = %s
        ORDER BY open_time DESC
        LIMIT 30;
    """

    return {
        "symbol": symbol,
        "summary": fetch_one(summary_sql, tuple(params)) or {},
        "points": fetch_all(points_sql, tuple(params)),
        "candles": fetch_all(candles_sql, (symbol,)),
    }
