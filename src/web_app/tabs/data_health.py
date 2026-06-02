from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.web_app.db import fetch_all, fetch_one


router = APIRouter()


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Data Health</title>
  <style>
    :root {
      --bg: #07111f;
      --panel: #172231;
      --line: rgba(255,255,255,0.13);
      --text: #eef6ff;
      --muted: #9db0c5;
      --green: #21d391;
      --red: #ff5d6c;
      --yellow: #ffd166;
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

    .cards {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 14px;
      margin-bottom: 18px;
    }

    .card {
      background: rgba(23,34,49,0.96);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 16px;
      box-shadow: 0 18px 55px rgba(0,0,0,0.28);
    }

    .card span {
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }

    .card strong {
      font-size: 24px;
      letter-spacing: -0.04em;
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
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

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 11px;
      border-radius: 999px;
      font-weight: 900;
      font-size: 13px;
    }

    .ok {
      color: var(--green);
      background: rgba(33,211,145,0.12);
      border: 1px solid rgba(33,211,145,0.28);
    }

    .warn {
      color: var(--yellow);
      background: rgba(255,209,102,0.12);
      border: 1px solid rgba(255,209,102,0.28);
    }

    .bad {
      color: var(--red);
      background: rgba(255,93,108,0.12);
      border: 1px solid rgba(255,93,108,0.28);
    }

    .table-wrap {
      overflow: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
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
      font-size: 12px;
    }

    .green { color: var(--green); }
    .red { color: var(--red); }
    .yellow { color: var(--yellow); }
    .blue { color: var(--blue); }

    .section {
      margin-top: 18px;
    }

    button {
      background: linear-gradient(135deg, rgba(74,168,255,0.45), rgba(33,211,145,0.24));
      color: var(--text);
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 12px;
      padding: 10px 14px;
      font-weight: 800;
      cursor: pointer;
    }

    @media (max-width: 1200px) {
      .cards {
        grid-template-columns: repeat(2, 1fr);
      }

      .grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 700px) {
      .app {
        padding: 14px;
      }

      .header {
        flex-direction: column;
      }

      .cards {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <div class="header">
      <div>
        <h1>Data Health</h1>
        <div class="muted">Database freshness, table counts, coverage and ingestion monitoring</div>
      </div>
      <div>
        <button onclick="reloadAll()">Refresh</button>
        <div class="muted" id="lastUpdated" style="margin-top:8px;">Loading...</div>
      </div>
    </div>

    <div class="tabs">
      <a class="tab" href="/market-pulse">Market Pulse</a>
      <a class="tab" href="/daily-history">Daily History</a>
      <a class="tab" href="/live-snapshots">Live Snapshots</a>
      <a class="tab active" href="/data-health">Data Health</a>
      <a class="tab" href="/alert-center">Alert Center</a>
    </div>

    <div class="cards">
      <div class="card">
        <span>Overall Status</span>
        <strong id="overallStatus">-</strong>
      </div>
      <div class="card">
        <span>Daily Rows</span>
        <strong id="dailyRows">-</strong>
      </div>
      <div class="card">
        <span>Realtime Rows</span>
        <strong id="realtimeRows">-</strong>
      </div>
      <div class="card">
        <span>Latest Symbols</span>
        <strong id="latestSymbols">-</strong>
      </div>
      <div class="card">
        <span>Coin Metadata</span>
        <strong id="coinMeta">-</strong>
      </div>
    </div>

    <div class="grid">
      <div class="panel">
        <h2>Freshness</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Dataset</th>
                <th>Status</th>
                <th>Last Update</th>
                <th>Delay</th>
              </tr>
            </thead>
            <tbody id="freshnessBody"></tbody>
          </table>
        </div>
      </div>

      <div class="panel">
        <h2>Historical Coverage</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody id="coverageBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="grid section">
      <div class="panel">
        <h2>Table Row Counts</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Table</th>
                <th>Rows</th>
              </tr>
            </thead>
            <tbody id="tableCountsBody"></tbody>
          </table>
        </div>
      </div>

      <div class="panel">
        <h2>Recent Snapshot Batches</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Fetched At</th>
                <th>Symbols</th>
              </tr>
            </thead>
            <tbody id="snapshotBatchesBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="panel section">
      <h2>Recent Ingestion Logs</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Created At</th>
              <th>Pipeline</th>
              <th>Source</th>
              <th>Status</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody id="logsBody"></tbody>
        </table>
      </div>
    </div>
  </div>

<script>
function fmt(value) {
  if (value === null || value === undefined || isNaN(Number(value))) return "-";
  return Number(value).toLocaleString();
}

function compact(value) {
  if (value === null || value === undefined || isNaN(Number(value))) return "-";
  return Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 2 }).format(Number(value));
}

function delayText(seconds) {
  if (seconds === null || seconds === undefined || isNaN(Number(seconds))) return "-";
  const s = Math.max(0, Number(seconds));
  if (s < 60) return `${Math.round(s)}s`;
  if (s < 3600) return `${Math.round(s / 60)}m`;
  if (s < 86400) return `${Math.round(s / 3600)}h`;
  return `${Math.round(s / 86400)}d`;
}

function pill(status) {
  const value = String(status || "UNKNOWN").toUpperCase();
  let cls = "warn";
  if (value === "OK") cls = "ok";
  if (value === "BAD" || value === "ERROR") cls = "bad";
  return `<span class="status-pill ${cls}">${value}</span>`;
}

async function getJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url);
  return await r.json();
}

async function loadOverview() {
  const data = await getJson("/api/data-health/overview");

  document.getElementById("overallStatus").innerHTML = pill(data.overall_status);
  document.getElementById("dailyRows").textContent = compact(data.daily_rows);
  document.getElementById("realtimeRows").textContent = compact(data.realtime_rows);
  document.getElementById("latestSymbols").textContent = fmt(data.latest_symbols);
  document.getElementById("coinMeta").textContent = fmt(data.coin_meta_rows);

  const freshnessBody = document.getElementById("freshnessBody");
  freshnessBody.innerHTML = "";

  data.freshness.forEach(item => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.dataset}</td>
      <td>${pill(item.status)}</td>
      <td>${item.last_update || "-"}</td>
      <td>${delayText(item.delay_seconds)}</td>
    `;
    freshnessBody.appendChild(tr);
  });

  const coverage = data.coverage || {};
  document.getElementById("coverageBody").innerHTML = `
    <tr><td>Daily symbols</td><td>${fmt(coverage.daily_symbols)}</td></tr>
    <tr><td>First daily candle</td><td>${coverage.first_day || "-"}</td></tr>
    <tr><td>Last daily candle</td><td>${coverage.last_day || "-"}</td></tr>
    <tr><td>Market symbols</td><td>${fmt(coverage.market_symbols)}</td></tr>
    <tr><td>CoinGecko metadata rows</td><td>${fmt(coverage.coin_meta_rows)}</td></tr>
  `;
}

async function loadTables() {
  const rows = await getJson("/api/data-health/table-counts");
  const body = document.getElementById("tableCountsBody");
  body.innerHTML = "";

  rows.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.table_name}</td>
      <td>${fmt(row.rows)}</td>
    `;
    body.appendChild(tr);
  });
}

async function loadBatches() {
  const rows = await getJson("/api/data-health/snapshot-batches");
  const body = document.getElementById("snapshotBatchesBody");
  body.innerHTML = "";

  rows.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.fetched_at}</td>
      <td>${fmt(row.symbol_count)}</td>
    `;
    body.appendChild(tr);
  });
}

async function loadLogs() {
  const rows = await getJson("/api/data-health/logs");
  const body = document.getElementById("logsBody");
  body.innerHTML = "";

  rows.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.created_at || "-"}</td>
      <td>${row.pipeline_name || "-"}</td>
      <td>${row.source || "-"}</td>
      <td>${pill(row.status)}</td>
      <td>${row.message || ""}</td>
    `;
    body.appendChild(tr);
  });
}

async function reloadAll() {
  await loadOverview();
  await loadTables();
  await loadBatches();
  await loadLogs();
  document.getElementById("lastUpdated").textContent = "Updated: " + new Date().toLocaleString();
}

reloadAll().catch(err => {
  console.error(err);
  document.getElementById("lastUpdated").textContent = "Error: " + err.message;
});
</script>
</body>
</html>
"""


@router.get("/data-health", response_class=HTMLResponse)
def data_health_page():
    return HTMLResponse(HTML)


@router.get("/api/data-health/overview")
def overview():
    daily = fetch_one("""
        SELECT
            COUNT(*)::bigint AS rows,
            COUNT(DISTINCT symbol)::integer AS symbols,
            MIN(open_time)::date::text AS first_day,
            MAX(open_time)::date::text AS last_day
        FROM daily_klines
        WHERE source = 'binance'
          AND interval_name = '1d';
    """) or {}

    realtime = fetch_one("""
        SELECT
            COUNT(*)::bigint AS rows,
            COUNT(DISTINCT symbol)::integer AS symbols,
            TO_CHAR(MAX(fetched_at) AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS last_update,
            EXTRACT(EPOCH FROM (NOW() - MAX(fetched_at)))::double precision AS delay_seconds
        FROM market_ticker_history
        WHERE source = 'binance';
    """) or {}

    latest = fetch_one("""
        SELECT
            COUNT(*)::integer AS symbols,
            TO_CHAR(MAX(fetched_at) AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS last_update,
            EXTRACT(EPOCH FROM (NOW() - MAX(fetched_at)))::double precision AS delay_seconds
        FROM market_ticker_latest
        WHERE source = 'binance';
    """) or {}

    meta = fetch_one("""
        SELECT
            COUNT(*)::integer AS rows,
            TO_CHAR(MAX(fetched_at) AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS last_update,
            EXTRACT(EPOCH FROM (NOW() - MAX(fetched_at)))::double precision AS delay_seconds
        FROM coin_market_meta_latest
        WHERE source = 'coingecko';
    """) or {}

    market_symbols = fetch_one("""
        SELECT COUNT(*)::integer AS rows
        FROM market_symbols
        WHERE source = 'binance';
    """) or {}

    realtime_status = freshness_status(realtime.get("delay_seconds"), ok_limit=180, warn_limit=900)
    latest_status = freshness_status(latest.get("delay_seconds"), ok_limit=180, warn_limit=900)
    meta_status = freshness_status(meta.get("delay_seconds"), ok_limit=86400, warn_limit=259200)

    overall_status = "OK"
    if "BAD" in [realtime_status, latest_status, meta_status]:
        overall_status = "BAD"
    elif "WARN" in [realtime_status, latest_status, meta_status]:
        overall_status = "WARN"

    return {
        "overall_status": overall_status,
        "daily_rows": daily.get("rows", 0),
        "realtime_rows": realtime.get("rows", 0),
        "latest_symbols": latest.get("symbols", 0),
        "coin_meta_rows": meta.get("rows", 0),
        "freshness": [
            {
                "dataset": "Realtime snapshots",
                "status": realtime_status,
                "last_update": realtime.get("last_update"),
                "delay_seconds": realtime.get("delay_seconds"),
            },
            {
                "dataset": "Latest ticker table",
                "status": latest_status,
                "last_update": latest.get("last_update"),
                "delay_seconds": latest.get("delay_seconds"),
            },
            {
                "dataset": "Coin metadata",
                "status": meta_status,
                "last_update": meta.get("last_update"),
                "delay_seconds": meta.get("delay_seconds"),
            },
        ],
        "coverage": {
            "daily_symbols": daily.get("symbols", 0),
            "first_day": daily.get("first_day"),
            "last_day": daily.get("last_day"),
            "market_symbols": market_symbols.get("rows", 0),
            "coin_meta_rows": meta.get("rows", 0),
        },
    }


@router.get("/api/data-health/table-counts")
def table_counts():
    return fetch_all("""
        SELECT 'market_symbols' AS table_name, COUNT(*)::bigint AS rows FROM market_symbols
        UNION ALL
        SELECT 'daily_klines', COUNT(*)::bigint FROM daily_klines
        UNION ALL
        SELECT 'market_ticker_history', COUNT(*)::bigint FROM market_ticker_history
        UNION ALL
        SELECT 'market_ticker_latest', COUNT(*)::bigint FROM market_ticker_latest
        UNION ALL
        SELECT 'coin_market_meta_latest', COUNT(*)::bigint FROM coin_market_meta_latest
        UNION ALL
        SELECT 'ingestion_logs', COUNT(*)::bigint FROM ingestion_logs
        ORDER BY table_name;
    """)


@router.get("/api/data-health/snapshot-batches")
def snapshot_batches():
    return fetch_all("""
        SELECT
            TO_CHAR(fetched_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS fetched_at,
            COUNT(*)::integer AS symbol_count
        FROM market_ticker_history
        WHERE source = 'binance'
        GROUP BY fetched_at
        ORDER BY fetched_at DESC
        LIMIT 20;
    """)


@router.get("/api/data-health/logs")
def logs():
    return fetch_all("""
        SELECT
            TO_CHAR(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS created_at,
            pipeline_name,
            source,
            status,
            message
        FROM ingestion_logs
        ORDER BY created_at DESC
        LIMIT 50;
    """)


def freshness_status(delay_seconds, ok_limit, warn_limit):
    if delay_seconds is None:
        return "BAD"

    try:
        delay = float(delay_seconds)
    except Exception:
        return "BAD"

    if delay <= ok_limit:
        return "OK"

    if delay <= warn_limit:
        return "WARN"

    return "BAD"
