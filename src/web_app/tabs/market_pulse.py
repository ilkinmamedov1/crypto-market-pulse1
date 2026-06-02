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
  <title>Crypto Market Pulse</title>
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
      grid-template-columns: 1.4fr 0.8fr 0.9fr 0.9fr auto;
      gap: 10px;
      margin-bottom: 14px;
      align-items: center;
    }

    select, button {
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
      color: var(--text);
      flex: 0 0 auto;
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
      width: min(520px, 95vw);
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

    .symbol-option-volume {
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
      grid-template-columns: repeat(4, 1fr);
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

    .coins {
      display: grid;
      gap: 10px;
      max-height: calc(100vh - 245px);
      min-height: 520px;
      overflow: auto;
      padding-right: 3px;
    }

    .coin {
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

    .coin:hover {
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

    .price {
      font-weight: 900;
    }

    .green { color: var(--green); }
    .red { color: var(--red); }

    .coin-extra {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 5px;
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }

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

    @media (max-width: 1200px) {
      .grid {
        grid-template-columns: 1fr;
      }

      .coins {
        min-height: 0;
        max-height: 520px;
      }

      .chart-box {
        min-height: 380px;
      }
    }

    @media (max-width: 850px) {
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
        <h1>Crypto Market Pulse</h1>
        <div class="muted">Historical and interval-based crypto market data powered by PostgreSQL</div>
      </div>
      <div class="muted" id="lastUpdated">Loading...</div>
    </div>

    <div class="tabs">
      <a class="tab active" href="/market-pulse">Market Pulse</a>
      <a class="tab" href="/daily-history">Daily History</a>
      <a class="tab" href="/live-snapshots">Live Snapshots</a>
      <a class="tab" href="/data-health">Data Health</a>
      <a class="tab" href="/alert-center">Alert Center</a>
    </div>

    <div class="grid">
      <div class="panel">
        <h2>Market Line Chart</h2>

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

          <select id="chartMode">
            <option value="daily" selected>Daily history</option>
            <option value="realtime">Interval snapshots</option>
          </select>

          <select id="rangeSelect">
            <option value="7">7 days</option>
            <option value="30" selected>30 days</option>
            <option value="90">90 days</option>
            <option value="180">180 days</option>
            <option value="365">365 days</option>
            <option value="0">All</option>
          </select>

          <button onclick="loadChart()">Refresh</button>
        </div>

        <div class="status" id="chartStatus">Preparing chart...</div>

        <div class="stats">
          <div class="stat"><span>Market Cap</span><strong id="statMarketCap">-</strong></div>
          <div class="stat"><span>Volume 24h</span><strong id="statVolume24h">-</strong></div>
          <div class="stat"><span>Total Supply</span><strong id="statTotalSupply">-</strong></div>
          <div class="stat"><span>Max Supply</span><strong id="statMaxSupply">-</strong></div>
        </div>

        <div class="chart-box">
          <canvas id="mainChart"></canvas>
        </div>
      </div>

      <div class="panel">
        <h2>Top 30 Coins</h2>
        <div class="muted">Ranked by quote volume. Click a card to update the chart.</div>
        <div class="coins" id="coins"></div>
      </div>
    </div>

    <div class="panel" style="margin-top:18px;">
      <h2>Top Market Table</h2>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Symbol</th>
            <th>Name</th>
            <th>Price</th>
            <th>24h %</th>
            <th>Market Cap</th>
            <th>Volume 24h</th>
            <th>Total Supply</th>
            <th>Max Supply</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
  </div>

<script>
let topCoins = [];
let allSymbols = [];
let chart = null;

function fmt(value, digits = 2) {
  if (value === null || value === undefined || isNaN(Number(value))) return "-";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
}

function compact(value) {
  if (value === null || value === undefined || isNaN(Number(value))) return "-";
  const n = Number(value);
  return "$" + Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 2 }).format(n);
}

function compactPlain(value) {
  if (value === null || value === undefined || isNaN(Number(value))) return "-";
  const n = Number(value);
  return Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 2 }).format(n);
}

function money(value) {
  if (value === null || value === undefined || isNaN(Number(value))) return "-";
  const n = Number(value);
  if (n >= 1) return "$" + n.toLocaleString(undefined, { maximumFractionDigits: 4 });
  return "$" + n.toLocaleString(undefined, { maximumFractionDigits: 10 });
}

function fallbackIcon(baseAsset) {
  return String(baseAsset || "?").slice(0, 2).toUpperCase();
}

async function getJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url);
  return await r.json();
}

function selectedQuote() {
  return document.getElementById("quoteSelect").value;
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

function setSelectedSymbol(symbol, renderOnly = false) {
  document.getElementById("symbolSelect").value = symbol;
  syncSelectedSymbolDisplay();
  renderSymbolOptions(document.getElementById("symbolSearch").value || "");

  if (!renderOnly) {
    document.getElementById("symbolCombo").classList.remove("open");
    loadChart();
  }
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
    div.onclick = () => setSelectedSymbol(item.symbol);

    div.innerHTML = `
      <div class="symbol-option-icon">${symbolIconHtml(item)}</div>
      <div class="symbol-option-main">
        <strong>${item.symbol}</strong>
        <small>${item.name || item.base_asset || "-"} / ${item.quote_asset || "-"}</small>
      </div>
      <div class="symbol-option-volume">${compact(item.quote_volume)}</div>
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

  search.addEventListener("input", () => {
    renderSymbolOptions(search.value);
  });

  document.addEventListener("click", () => {
    combo.classList.remove("open");
  });
}


async function loadSymbols() {
  const quote = selectedQuote();
  allSymbols = await getJson(`/api/market-pulse/symbols?quote=${encodeURIComponent(quote)}`);

  const select = document.getElementById("symbolSelect");
  const current = select.value;
  select.innerHTML = "";

  allSymbols.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.symbol;
    opt.textContent = `${c.symbol}  (${c.base_asset || "-"} / ${c.quote_asset || "-"})`;
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

async function loadTop() {
  const quote = selectedQuote();
  topCoins = await getJson(`/api/market-pulse/top?limit=30&quote=${encodeURIComponent(quote)}`);
  renderCoins();
  renderTable();
}

function renderCoins() {
  const box = document.getElementById("coins");
  box.innerHTML = "";

  topCoins.forEach(c => {
    const change = Number(c.change_percent || 0);
    const div = document.createElement("div");
    div.className = "coin";
    div.onclick = () => {
      setSelectedSymbol(c.symbol, true);
      loadChart();
      window.scrollTo({ top: 0, behavior: "smooth" });
    };

    const image = c.image_url
      ? `<img src="${c.image_url}" onerror="this.remove(); this.parentElement.textContent='${fallbackIcon(c.base_asset)}';">`
      : fallbackIcon(c.base_asset);

    div.innerHTML = `
      <div class="icon">${image}</div>
      <div>
        <div class="row">
          <strong>${c.symbol}</strong>
          <span class="${change >= 0 ? "green" : "red"}">${change.toFixed(2)}%</span>
        </div>
        <div class="row muted">
          <span>${c.name || c.base_asset || "-"} / ${c.quote_asset || "-"}</span>
          <span class="price">${money(c.last_price)}</span>
        </div>
        <div class="coin-extra">
          <span>Cap: ${compact(c.market_cap)}</span>
          <span>Vol: ${compact(c.volume_24h)}</span>
          <span>Total: ${compactPlain(c.total_supply)}</span>
          <span>Max: ${compactPlain(c.max_supply)}</span>
        </div>
      </div>
    `;
    box.appendChild(div);
  });
}

function renderTable() {
  const body = document.getElementById("tableBody");
  body.innerHTML = "";

  topCoins.forEach((c, i) => {
    const change = Number(c.change_percent || 0);
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td><strong>${c.symbol}</strong></td>
      <td>${c.name || "-"}</td>
      <td>${money(c.last_price)}</td>
      <td class="${change >= 0 ? "green" : "red"}"><strong>${change.toFixed(2)}%</strong></td>
      <td>${compact(c.market_cap)}</td>
      <td>${compact(c.volume_24h)}</td>
      <td>${compactPlain(c.total_supply)}</td>
      <td>${compactPlain(c.max_supply)}</td>
    `;
    body.appendChild(tr);
  });
}

async function loadChart() {
  const symbol = document.getElementById("symbolSelect").value;
  const mode = document.getElementById("chartMode").value;
  const days = document.getElementById("rangeSelect").value;

  if (!symbol) return;

  document.getElementById("chartStatus").textContent = `Loading ${symbol} data...`;

  let url;
  if (mode === "daily") {
    url = `/api/market-pulse/chart/daily?symbol=${encodeURIComponent(symbol)}&days=${encodeURIComponent(days)}`;
  } else {
    const hours = days === "0" ? 720 : Math.max(1, Number(days) * 24);
    url = `/api/market-pulse/chart/realtime?symbol=${encodeURIComponent(symbol)}&hours=${hours}`;
  }

  const payload = await getJson(url);
  const labels = payload.points.map(x => x.t);
  const values = payload.points.map(x => x.v);

  const latest = payload.latest || {};
  document.getElementById("statMarketCap").textContent = compact(latest.market_cap);
  document.getElementById("statVolume24h").textContent = compact(latest.volume_24h);
  document.getElementById("statTotalSupply").textContent = compactPlain(latest.total_supply);
  document.getElementById("statMaxSupply").textContent = compactPlain(latest.max_supply);

  if (chart) chart.destroy();

  if (values.length === 0) {
    document.getElementById("chartStatus").textContent =
      `No ${mode} data found for ${symbol}. Historical sync may still be loading this symbol.`;
  } else {
    document.getElementById("chartStatus").textContent =
      `${symbol}: ${values.length} data points. Last price: ${money(latest.last_price)}`;
  }

  chart = new Chart(document.getElementById("mainChart"), {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: `${symbol} ${mode === "daily" ? "daily close" : "snapshot price"}`,
        data: values,
        borderWidth: 2,
        tension: 0.3,
        pointRadius: values.length > 150 ? 0 : 2,
        fill: false
      }]
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

  document.getElementById("lastUpdated").textContent = "Updated: " + new Date().toLocaleString();
}

async function reloadAll() {
  await loadSymbols();
  await loadTop();
  await loadChart();
}

document.getElementById("symbolSelect").addEventListener("change", () => {
  syncSelectedSymbolDisplay();
  loadChart();
});
setupSymbolComboEvents();
document.getElementById("chartMode").addEventListener("change", loadChart);
document.getElementById("rangeSelect").addEventListener("change", loadChart);
document.getElementById("quoteSelect").addEventListener("change", reloadAll);

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


@router.get("/market-pulse", response_class=HTMLResponse)
def market_pulse_page():
    return HTMLResponse(HTML)


@router.get("/api/market-pulse/symbols")
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
            l.symbol,
            COALESCE(s.base_asset, '') AS base_asset,
            COALESCE(s.quote_asset, '') AS quote_asset,
            COALESCE(m.name, s.base_asset, '') AS name,
            m.image_url,
            l.quote_volume::double precision AS quote_volume
        FROM market_ticker_latest l
        LEFT JOIN market_symbols s
            ON s.source = l.source
           AND s.symbol = l.symbol
        LEFT JOIN best_meta m
            ON m.symbol_upper = UPPER(s.base_asset)
        WHERE l.source = 'binance'
          AND l.symbol IS NOT NULL
          {quote_filter}
        ORDER BY
            CASE WHEN l.symbol = 'BTCUSDT' THEN 0 ELSE 1 END,
            COALESCE(l.quote_volume, 0) DESC,
            l.symbol ASC;
    """
    return fetch_all(sql, tuple(params))


@router.get("/api/market-pulse/top")
def top_market(
    limit: int = Query(default=30, ge=1, le=100),
    quote: str = "",
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
            l.symbol,
            s.base_asset,
            s.quote_asset,
            COALESCE(m.name, s.base_asset) AS name,
            m.image_url,

            l.last_price::double precision AS last_price,
            l.open_price::double precision AS open_price,
            l.quote_volume::double precision AS quote_volume,

            m.market_cap::double precision AS market_cap,
            COALESCE(m.total_volume, l.quote_volume)::double precision AS volume_24h,
            m.total_supply::double precision AS total_supply,
            m.max_supply::double precision AS max_supply,

            CASE
                WHEN l.open_price IS NOT NULL AND l.open_price <> 0
                THEN ROUND(((l.last_price - l.open_price) / l.open_price * 100)::numeric, 4)::double precision
                ELSE 0
            END AS change_percent,
            TO_CHAR(l.fetched_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS fetched_at
        FROM market_ticker_latest l
        LEFT JOIN market_symbols s
            ON s.source = l.source
           AND s.symbol = l.symbol
        LEFT JOIN best_meta m
            ON m.symbol_upper = UPPER(s.base_asset)
        WHERE l.source = 'binance'
          AND l.last_price IS NOT NULL
          AND l.quote_volume IS NOT NULL
          {quote_filter}
        ORDER BY l.quote_volume DESC NULLS LAST
        LIMIT %s;
    """
    return fetch_all(sql, tuple(params))


@router.get("/api/market-pulse/chart/daily")
def daily_chart(symbol: str, days: int = Query(default=30, ge=0, le=5000)):
    params = [symbol.upper()]
    where_days = ""

    if days > 0:
        where_days = "AND open_time >= NOW() - (%s || ' days')::interval"
        params.append(days)

    sql = f"""
        SELECT
            TO_CHAR(open_time AT TIME ZONE 'UTC', 'YYYY-MM-DD') AS t,
            close_price::double precision AS v
        FROM daily_klines
        WHERE source = 'binance'
          AND symbol = %s
          AND interval_name = '1d'
          {where_days}
        ORDER BY open_time ASC;
    """

    return {
        "symbol": symbol.upper(),
        "latest": get_latest(symbol),
        "points": fetch_all(sql, tuple(params)),
    }


@router.get("/api/market-pulse/chart/realtime")
def realtime_chart(symbol: str, hours: int = Query(default=24, ge=1, le=720)):
    sql = """
        SELECT
            TO_CHAR(fetched_at AT TIME ZONE 'UTC', 'MM-DD HH24:MI') AS t,
            last_price::double precision AS v
        FROM market_ticker_history
        WHERE source = 'binance'
          AND symbol = %s
          AND fetched_at >= NOW() - (%s || ' hours')::interval
        ORDER BY fetched_at ASC
        LIMIT 5000;
    """

    return {
        "symbol": symbol.upper(),
        "latest": get_latest(symbol),
        "points": fetch_all(sql, (symbol.upper(), hours)),
    }


def get_latest(symbol: str):
    sql = f"""
        {meta_cte()}
        SELECT
            l.symbol,
            s.base_asset,
            s.quote_asset,
            COALESCE(m.name, s.base_asset) AS name,
            m.image_url,

            l.last_price::double precision AS last_price,
            l.open_price::double precision AS open_price,

            m.market_cap::double precision AS market_cap,
            COALESCE(m.total_volume, l.quote_volume)::double precision AS volume_24h,
            m.total_supply::double precision AS total_supply,
            m.max_supply::double precision AS max_supply,

            CASE
                WHEN l.open_price IS NOT NULL AND l.open_price <> 0
                THEN ROUND(((l.last_price - l.open_price) / l.open_price * 100)::numeric, 4)::double precision
                ELSE 0
            END AS change_percent,
            TO_CHAR(l.fetched_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS fetched_at
        FROM market_ticker_latest l
        LEFT JOIN market_symbols s
            ON s.source = l.source
           AND s.symbol = l.symbol
        LEFT JOIN best_meta m
            ON m.symbol_upper = UPPER(s.base_asset)
        WHERE l.source = 'binance'
          AND l.symbol = %s
        LIMIT 1;
    """
    return fetch_one(sql, (symbol.upper(),)) or {}
