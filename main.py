# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

import config
from database import Alert, Client, init_db, engine
from datetime import datetime, timedelta
from api import auth, locations, clients, groups, alerts, reports, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from services.udp_listener import start_udp_listener
    from services.scheduler import start_scheduler
    start_udp_listener(config.UDP_PORT)
    start_scheduler()
    yield


app = FastAPI(title="Help Request Server", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY)
app.mount("/static", StaticFiles(directory="web/static"), name="static")

templates = Jinja2Templates(directory="web/templates")

app.include_router(auth.router)
app.include_router(locations.router)
app.include_router(clients.router)
app.include_router(groups.router)
app.include_router(alerts.router)
app.include_router(reports.router)
app.include_router(settings.router)


@app.get("/")
def root(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/dashboard")
    return RedirectResponse("/login")


@app.get("/help")
def help_page(request: Request):
    from api.auth import require_auth
    redir = require_auth(request)
    if redir:
        return redir
    return templates.TemplateResponse(request, "help.html", {})


@app.get("/dashboard")
def dashboard(request: Request):
    from api.auth import require_auth
    redir = require_auth(request)
    if redir:
        return redir
    now = datetime.utcnow()
    threshold = now - timedelta(minutes=5)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    with Session(engine) as db:
        online_count = db.query(Client).filter(Client.last_seen >= threshold).count()
        security_count = db.query(Client).filter(
            Client.is_security == True, Client.last_seen >= threshold).count()
        alerts_today = db.query(Alert).filter(Alert.triggered_at >= today_start).count()
        alerts_month = db.query(Alert).filter(Alert.triggered_at >= month_start).count()
        recent = db.query(Alert).order_by(Alert.triggered_at.desc()).limit(10).all()

    return templates.TemplateResponse(request, "dashboard.html", {
        "online_count": online_count,
        "security_count": security_count,
        "alerts_today": alerts_today,
        "alerts_month": alerts_month,
        "recent_alerts": recent,
    })
