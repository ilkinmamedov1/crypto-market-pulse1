from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.web_app.tabs.market_pulse import router as market_pulse_router
from src.web_app.tabs.daily_history import router as daily_history_router
from src.web_app.tabs.live_snapshots import router as live_snapshots_router
from src.web_app.tabs.data_health import router as data_health_router
from src.web_app.tabs.alert_center import router as alert_center_router


app = FastAPI(
    title="Crypto Market Pulse",
    description="Historical and interval-based crypto market dashboard powered by PostgreSQL.",
    version="0.1.0",
)


@app.get("/")
def home():
    return RedirectResponse(url="/market-pulse")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(market_pulse_router)
app.include_router(daily_history_router)
app.include_router(live_snapshots_router)
app.include_router(data_health_router)
app.include_router(alert_center_router)
