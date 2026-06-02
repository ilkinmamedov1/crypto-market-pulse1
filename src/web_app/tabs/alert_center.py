from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from src.web_app.db import fetch_all, execute


router = APIRouter()


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Alert Center</title>
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

    .grid {
      display: grid;
      grid-template-columns: 500px minmax(0, 1fr);
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

    label {
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin: 12px 0 6px;
      font-weight: 700;
    }

    input, select, textarea, button {
      width: 100%;
      background: #2b3748;
      color: var(--text);
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 12px;
      padding: 11px 12px;
      font-weight: 700;
      outline: none;
    }

    textarea {
      min-height: 96px;
      resize: vertical;
      font-family: inherit;
    }

    select option {
      background: #101b2b;
      color: var(--text);
    }

    button {
      cursor: pointer;
      margin-top: 14px;
      background: linear-gradient(135deg, rgba(74,168,255,0.45), rgba(33,211,145,0.24));
    }

    .small-button {
      width: auto;
      padding: 7px 10px;
      margin: 0;
      font-size: 12px;
    }

    .danger {
      background: rgba(255,93,108,0.18);
      border-color: rgba(255,93,108,0.35);
    }

    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .status {
      margin-top: 10px;
      min-height: 22px;
      color: var(--muted);
      font-size: 14px;
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
      vertical-align: top;
    }

    th {
      color: var(--muted);
      font-size: 12px;
    }

    .pill {
      display: inline-flex;
      padding: 6px 9px;
      border-radius: 999px;
      font-weight: 900;
      font-size: 12px;
    }

    .enabled {
      color: var(--green);
      background: rgba(33,211,145,0.12);
      border: 1px solid rgba(33,211,145,0.28);
    }

    .disabled {
      color: var(--yellow);
      background: rgba(255,209,102,0.12);
      border: 1px solid rgba(255,209,102,0.28);
    }

    .green { color: var(--green); }
    .red { color: var(--red); }
    .yellow { color: var(--yellow); }

    .section {
      margin-top: 18px;
    }

    @media (max-width: 1150px) {
      .grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 760px) {
      .app {
        padding: 14px;
      }

      .header {
        flex-direction: column;
      }

      .form-row {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <div class="header">
      <div>
        <h1>Alert Center</h1>
        <div class="muted">All-market rule engine for price movement alerts and newly listed symbols</div>
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
      <a class="tab" href="/data-health">Data Health</a>
      <a class="tab active" href="/alert-center">Alert Center</a>
    </div>

    <div class="grid">
      <div class="panel">
        <h2>Create All-Market Alert</h2>
        <div class="muted">The rule applies to the selected market scope, not a single symbol. Recipients are stored in PostgreSQL. SMTP sender credentials stay in .env.</div>

        <label>Rule Name</label>
        <input id="ruleName" placeholder="Example: USDT pairs dropped 50% from January average">

        <div class="form-row">
          <div>
            <label>Market Scope</label>
            <select id="scopeSelect">
              <option value="">All symbols</option>
              <option value="USDT" selected>USDT pairs</option>
              <option value="USDC">USDC pairs</option>
              <option value="FDUSD">FDUSD pairs</option>
              <option value="BTC">BTC pairs</option>
              <option value="TRY">TRY pairs</option>
            </select>
          </div>

          <div>
            <label>Direction</label>
            <select id="directionSelect">
              <option value="down">Price drops by</option>
              <option value="up">Price increases by</option>
            </select>
          </div>
        </div>

        <div class="form-row">
          <div>
            <label>Threshold Percent</label>
            <input id="thresholdInput" type="number" step="0.01" value="50">
          </div>

          <div>
            <label>Cooldown Minutes</label>
            <input id="cooldownInput" type="number" step="1" value="60">
          </div>
        </div>

        <label>Comparison Mode</label>
        <select id="comparisonMode" onchange="toggleComparisonFields()">
          <option value="rolling_window">Rolling window</option>
          <option value="fixed_date_range" selected>Fixed historical date range</option>
        </select>

        <div id="rollingFields">
          <label>Rolling Window</label>
          <select id="windowSelect">
            <option value="60">1 hour</option>
            <option value="180">3 hours</option>
            <option value="360">6 hours</option>
            <option value="720">12 hours</option>
            <option value="1440" selected>24 hours</option>
            <option value="10080">7 days</option>
          </select>
        </div>

        <div id="fixedFields">
          <div class="form-row">
            <div>
              <label>Baseline Start Date</label>
              <input id="startDateInput" type="date">
            </div>

            <div>
              <label>Baseline End Date</label>
              <input id="endDateInput" type="date">
            </div>
          </div>

          <label>Baseline Price Type</label>
          <select id="baselineTypeSelect">
            <option value="avg_close" selected>Average close</option>
            <option value="first_close">First close</option>
            <option value="last_close">Last close</option>
            <option value="highest_high">Highest high</option>
            <option value="lowest_low">Lowest low</option>
          </select>
        </div>

        <label>
          <input id="includeNewSymbolsInput" type="checkbox" checked style="width:auto; margin-right:8px;">
          Include newly listed symbols in the email footer
        </label>

        <label>Recipient Emails</label>
        <textarea id="emailsInput" placeholder="one@example.com&#10;two@example.com&#10;three@example.com"></textarea>

        <button onclick="createRule()">Create Rule</button>
        <div class="status" id="formStatus"></div>
      </div>

      <div class="panel">
        <h2>Alert Rules</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Name</th>
                <th>Scope</th>
                <th>Condition</th>
                <th>Comparison</th>
                <th>Recipients</th>
                <th>Last Triggered</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="rulesBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="panel section">
      <h2>Recent Matched Symbols</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Created At</th>
              <th>Rule</th>
              <th>Symbol</th>
              <th>Direction</th>
              <th>Threshold</th>
              <th>Actual Change</th>
              <th>Baseline</th>
              <th>Latest</th>
              <th>Email Status</th>
            </tr>
          </thead>
          <tbody id="eventsBody"></tbody>
        </table>
      </div>
    </div>

    <div class="panel section">
      <h2>Recent Email Logs</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Created At</th>
              <th>Rule</th>
              <th>Recipient</th>
              <th>Status</th>
              <th>Matched</th>
              <th>New Symbols</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody id="emailLogsBody"></tbody>
        </table>
      </div>
    </div>
  </div>

<script>
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

async function getJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return await r.json();
}

async function postJson(url, payload) {
  const r = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  if (!r.ok) throw new Error(await r.text());
  return await r.json();
}

async function deleteJson(url) {
  const r = await fetch(url, {method: "DELETE"});
  if (!r.ok) throw new Error(await r.text());
  return await r.json();
}

function parseEmails(text) {
  return String(text || "")
    .split(/[\\n,; ]+/)
    .map(x => x.trim())
    .filter(Boolean);
}

function toggleComparisonFields() {
  const mode = document.getElementById("comparisonMode").value;
  document.getElementById("rollingFields").style.display = mode === "rolling_window" ? "block" : "none";
  document.getElementById("fixedFields").style.display = mode === "fixed_date_range" ? "block" : "none";
}

function setDefaultDates() {
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth(), 0);
  const start = new Date(end.getFullYear(), end.getMonth(), 1);

  document.getElementById("startDateInput").value = start.toISOString().slice(0, 10);
  document.getElementById("endDateInput").value = end.toISOString().slice(0, 10);
}

async function createRule() {
  const comparisonMode = document.getElementById("comparisonMode").value;

  const payload = {
    name: document.getElementById("ruleName").value.trim(),
    scope_quote_asset: document.getElementById("scopeSelect").value,
    direction: document.getElementById("directionSelect").value,
    threshold_percent: Number(document.getElementById("thresholdInput").value),
    comparison_mode: comparisonMode,
    window_minutes: comparisonMode === "rolling_window" ? Number(document.getElementById("windowSelect").value) : null,
    baseline_start_date: comparisonMode === "fixed_date_range" ? document.getElementById("startDateInput").value : null,
    baseline_end_date: comparisonMode === "fixed_date_range" ? document.getElementById("endDateInput").value : null,
    baseline_price_type: document.getElementById("baselineTypeSelect").value,
    cooldown_minutes: Number(document.getElementById("cooldownInput").value),
    include_new_symbols: document.getElementById("includeNewSymbolsInput").checked,
    emails: parseEmails(document.getElementById("emailsInput").value),
    is_enabled: true
  };

  if (!payload.name) {
    document.getElementById("formStatus").textContent = "Rule name is required.";
    return;
  }

  if (!payload.threshold_percent || payload.threshold_percent <= 0) {
    document.getElementById("formStatus").textContent = "Threshold must be greater than zero.";
    return;
  }

  if (payload.comparison_mode === "fixed_date_range" && (!payload.baseline_start_date || !payload.baseline_end_date)) {
    document.getElementById("formStatus").textContent = "Start and end dates are required.";
    return;
  }

  if (payload.emails.length === 0) {
    document.getElementById("formStatus").textContent = "At least one recipient email is required.";
    return;
  }

  try {
    const result = await postJson("/api/alert-center/rules", payload);

    if (!result.ok) {
      document.getElementById("formStatus").textContent = result.error || "Could not create rule.";
      return;
    }

    document.getElementById("formStatus").textContent = "Alert rule created.";

    document.getElementById("ruleName").value = "";
    document.getElementById("thresholdInput").value = "50";
    document.getElementById("emailsInput").value = "";

    await reloadAll();
  } catch (err) {
    document.getElementById("formStatus").textContent = "Error: " + err.message;
  }
}

async function loadRules() {
  const rules = await getJson("/api/alert-center/rules");
  const body = document.getElementById("rulesBody");
  body.innerHTML = "";

  rules.forEach(rule => {
    const tr = document.createElement("tr");
    const statusClass = rule.is_enabled ? "enabled" : "disabled";
    const statusText = rule.is_enabled ? "ENABLED" : "DISABLED";

    const scope = rule.scope_quote_asset ? `${rule.scope_quote_asset} pairs` : "All symbols";
    const directionText = rule.direction === "up" ? "increase" : "drop";

    let comparison = "";
    if (rule.comparison_mode === "rolling_window") {
      comparison = `Last ${rule.window_minutes} min`;
    } else {
      comparison = `${rule.baseline_start_date || "-"} → ${rule.baseline_end_date || "-"} / ${rule.baseline_price_type}`;
    }

    tr.innerHTML = `
      <td><span class="pill ${statusClass}">${statusText}</span></td>
      <td>${rule.name}</td>
      <td>${scope}</td>
      <td>${directionText} ${fmt(rule.threshold_percent, 2)}%</td>
      <td>${comparison}</td>
      <td>${rule.recipients || "-"}</td>
      <td>${rule.last_triggered_at || "-"}</td>
      <td>
        <button class="small-button" onclick="toggleRule(${rule.id})">Toggle</button>
        <button class="small-button danger" onclick="deleteRule(${rule.id})">Delete</button>
      </td>
    `;

    body.appendChild(tr);
  });
}

async function toggleRule(id) {
  await postJson(`/api/alert-center/rules/${id}/toggle`, {});
  await reloadAll();
}

async function deleteRule(id) {
  if (!confirm("Delete this alert rule?")) return;
  await deleteJson(`/api/alert-center/rules/${id}`);
  await reloadAll();
}

async function loadEvents() {
  const events = await getJson("/api/alert-center/events");
  const body = document.getElementById("eventsBody");
  body.innerHTML = "";

  events.forEach(event => {
    const actual = Number(event.actual_percent || 0);
    const cls = actual >= 0 ? "green" : "red";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${event.created_at || "-"}</td>
      <td>${event.rule_name || "-"}</td>
      <td><strong>${event.symbol}</strong></td>
      <td>${event.direction}</td>
      <td>${fmt(event.threshold_percent, 2)}%</td>
      <td class="${cls}"><strong>${fmt(actual, 4)}%</strong></td>
      <td>${money(event.baseline_price)}</td>
      <td>${money(event.latest_price)}</td>
      <td>${event.email_status || "-"}</td>
    `;
    body.appendChild(tr);
  });
}

async function loadEmailLogs() {
  const logs = await getJson("/api/alert-center/email-logs");
  const body = document.getElementById("emailLogsBody");
  body.innerHTML = "";

  logs.forEach(log => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${log.created_at || "-"}</td>
      <td>${log.rule_name || "-"}</td>
      <td>${log.recipient_email || "-"}</td>
      <td>${log.status || "-"}</td>
      <td>${log.matched_count || 0}</td>
      <td>${log.new_symbol_count || 0}</td>
      <td>${log.error_message || ""}</td>
    `;
    body.appendChild(tr);
  });
}

async function reloadAll() {
  await loadRules();
  await loadEvents();
  await loadEmailLogs();
  document.getElementById("lastUpdated").textContent = "Updated: " + new Date().toLocaleString();
}

setDefaultDates();
toggleComparisonFields();

reloadAll().catch(err => {
  console.error(err);
  document.getElementById("lastUpdated").textContent = "Error: " + err.message;
});
</script>
</body>
</html>
"""


def ensure_alert_schema():
    execute("""
    CREATE TABLE IF NOT EXISTS alert_rules (
        id BIGSERIAL PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        scope_quote_asset VARCHAR(30),
        direction VARCHAR(10) NOT NULL CHECK (direction IN ('up', 'down')),
        threshold_percent NUMERIC NOT NULL,
        comparison_mode VARCHAR(30) NOT NULL CHECK (comparison_mode IN ('rolling_window', 'fixed_date_range')),
        window_minutes INTEGER,
        baseline_start_date DATE,
        baseline_end_date DATE,
        baseline_price_type VARCHAR(30) NOT NULL DEFAULT 'avg_close',
        cooldown_minutes INTEGER NOT NULL DEFAULT 60,
        include_new_symbols BOOLEAN NOT NULL DEFAULT TRUE,
        is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        last_checked_at TIMESTAMPTZ,
        last_triggered_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS alert_recipients (
        id BIGSERIAL PRIMARY KEY,
        rule_id BIGINT NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
        email VARCHAR(320) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS alert_events (
        id BIGSERIAL PRIMARY KEY,
        rule_id BIGINT REFERENCES alert_rules(id) ON DELETE SET NULL,
        rule_name VARCHAR(200),
        symbol VARCHAR(30) NOT NULL,
        direction VARCHAR(10) NOT NULL,
        threshold_percent NUMERIC NOT NULL,
        actual_percent NUMERIC NOT NULL,
        baseline_price NUMERIC,
        latest_price NUMERIC,
        baseline_time TIMESTAMPTZ,
        latest_time TIMESTAMPTZ,
        comparison_mode VARCHAR(30),
        baseline_price_type VARCHAR(30),
        window_minutes INTEGER,
        baseline_start_date DATE,
        baseline_end_date DATE,
        email_status VARCHAR(80),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS alert_email_logs (
        id BIGSERIAL PRIMARY KEY,
        rule_id BIGINT REFERENCES alert_rules(id) ON DELETE SET NULL,
        recipient_email VARCHAR(320) NOT NULL,
        status VARCHAR(80) NOT NULL,
        matched_count INTEGER NOT NULL DEFAULT 0,
        new_symbol_count INTEGER NOT NULL DEFAULT 0,
        error_message TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS alert_new_symbol_notifications (
        rule_id BIGINT NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
        symbol VARCHAR(30) NOT NULL,
        notified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (rule_id, symbol)
    );
    """)


@router.get("/alert-center", response_class=HTMLResponse)
def alert_center_page():
    ensure_alert_schema()
    return HTMLResponse(HTML)


@router.get("/api/alert-center/rules")
def rules():
    ensure_alert_schema()

    return fetch_all("""
        SELECT
            r.id,
            r.name,
            COALESCE(r.scope_quote_asset, '') AS scope_quote_asset,
            r.direction,
            r.threshold_percent::double precision AS threshold_percent,
            r.comparison_mode,
            r.window_minutes,
            r.baseline_start_date::text AS baseline_start_date,
            r.baseline_end_date::text AS baseline_end_date,
            r.baseline_price_type,
            r.cooldown_minutes,
            r.include_new_symbols,
            r.is_enabled,
            TO_CHAR(r.last_triggered_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS last_triggered_at,
            COALESCE(string_agg(ar.email, ', ' ORDER BY ar.email), '') AS recipients
        FROM alert_rules r
        LEFT JOIN alert_recipients ar
            ON ar.rule_id = r.id
        GROUP BY
            r.id,
            r.name,
            r.scope_quote_asset,
            r.direction,
            r.threshold_percent,
            r.comparison_mode,
            r.window_minutes,
            r.baseline_start_date,
            r.baseline_end_date,
            r.baseline_price_type,
            r.cooldown_minutes,
            r.include_new_symbols,
            r.is_enabled,
            r.last_triggered_at
        ORDER BY r.created_at DESC;
    """)


@router.post("/api/alert-center/rules")
async def create_rule(request: Request):
    ensure_alert_schema()

    payload = await request.json()

    name = str(payload.get("name", "")).strip()
    scope_quote_asset = str(payload.get("scope_quote_asset", "")).upper().strip() or None
    direction = str(payload.get("direction", "")).lower().strip()
    threshold_percent = float(payload.get("threshold_percent", 0))
    comparison_mode = str(payload.get("comparison_mode", "")).lower().strip()
    window_minutes = payload.get("window_minutes")
    baseline_start_date = payload.get("baseline_start_date")
    baseline_end_date = payload.get("baseline_end_date")
    baseline_price_type = str(payload.get("baseline_price_type", "avg_close")).lower().strip()
    cooldown_minutes = int(payload.get("cooldown_minutes", 60))
    include_new_symbols = bool(payload.get("include_new_symbols", True))
    emails = payload.get("emails", [])
    is_enabled = bool(payload.get("is_enabled", True))

    if not name:
        return {"ok": False, "error": "Rule name is required"}

    if direction not in ("up", "down"):
        return {"ok": False, "error": "Direction must be up or down"}

    if threshold_percent <= 0:
        return {"ok": False, "error": "Threshold must be greater than zero"}

    if comparison_mode not in ("rolling_window", "fixed_date_range"):
        return {"ok": False, "error": "Invalid comparison mode"}

    if comparison_mode == "rolling_window":
        if not window_minutes or int(window_minutes) <= 0:
            return {"ok": False, "error": "Rolling window minutes are required"}
        window_minutes = int(window_minutes)
        baseline_start_date = None
        baseline_end_date = None

    if comparison_mode == "fixed_date_range":
        if not baseline_start_date or not baseline_end_date:
            return {"ok": False, "error": "Start and end dates are required"}
        window_minutes = None

    if baseline_price_type not in ("first_close", "last_close", "avg_close", "highest_high", "lowest_low"):
        return {"ok": False, "error": "Invalid baseline price type"}

    clean_emails = []
    for email in emails:
        email = str(email).strip()
        if email and "@" in email:
            clean_emails.append(email)

    if not clean_emails:
        return {"ok": False, "error": "At least one valid email is required"}

    rule = execute(
        """
        INSERT INTO alert_rules (
            name,
            scope_quote_asset,
            direction,
            threshold_percent,
            comparison_mode,
            window_minutes,
            baseline_start_date,
            baseline_end_date,
            baseline_price_type,
            cooldown_minutes,
            include_new_symbols,
            is_enabled
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (
            name,
            scope_quote_asset,
            direction,
            threshold_percent,
            comparison_mode,
            window_minutes,
            baseline_start_date,
            baseline_end_date,
            baseline_price_type,
            cooldown_minutes,
            include_new_symbols,
            is_enabled,
        ),
        fetch_one_result=True,
    )

    rule_id = rule["id"]

    for email in clean_emails:
        execute(
            """
            INSERT INTO alert_recipients (rule_id, email)
            VALUES (%s, %s);
            """,
            (rule_id, email),
        )

    return {"ok": True, "rule_id": rule_id}


@router.post("/api/alert-center/rules/{rule_id}/toggle")
def toggle_rule(rule_id: int):
    ensure_alert_schema()

    execute("""
        UPDATE alert_rules
        SET is_enabled = NOT is_enabled,
            updated_at = NOW()
        WHERE id = %s;
    """, (rule_id,))

    return {"ok": True}


@router.delete("/api/alert-center/rules/{rule_id}")
def delete_rule(rule_id: int):
    ensure_alert_schema()

    execute("""
        DELETE FROM alert_rules
        WHERE id = %s;
    """, (rule_id,))

    return {"ok": True}


@router.get("/api/alert-center/events")
def events(limit: int = Query(default=100, ge=1, le=500)):
    ensure_alert_schema()

    return fetch_all("""
        SELECT
            id,
            TO_CHAR(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS created_at,
            rule_name,
            symbol,
            direction,
            threshold_percent::double precision AS threshold_percent,
            actual_percent::double precision AS actual_percent,
            baseline_price::double precision AS baseline_price,
            latest_price::double precision AS latest_price,
            email_status
        FROM alert_events
        ORDER BY created_at DESC
        LIMIT %s;
    """, (limit,))


@router.get("/api/alert-center/email-logs")
def email_logs(limit: int = Query(default=100, ge=1, le=500)):
    ensure_alert_schema()

    return fetch_all("""
        SELECT
            TO_CHAR(l.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS created_at,
            r.name AS rule_name,
            l.recipient_email,
            l.status,
            l.matched_count,
            l.new_symbol_count,
            l.error_message
        FROM alert_email_logs l
        LEFT JOIN alert_rules r
            ON r.id = l.rule_id
        ORDER BY l.created_at DESC
        LIMIT %s;
    """, (limit,))
