# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.auth import require_auth
from database import EmailSchedule, RiskOfficer, ServerConfig, SmtpConfig, get_db

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


class RiskOfficerIn(BaseModel):
    name: str
    email: str


class SmtpIn(BaseModel):
    host: str
    port: int = 587
    username: str
    password: str
    use_tls: bool = True
    from_addr: str


class ScheduleIn(BaseModel):
    frequency: str
    day_of_week: int | None = None
    day_of_month: int | None = None
    send_time: str
    active: bool = True


class ServerConfigIn(BaseModel):
    hotkey: str


@router.get("/settings", response_class=HTMLResponse)
def settings_view(request: Request, db: Session = Depends(get_db)):
    redir = require_auth(request)
    if redir:
        return redir
    officer = db.query(RiskOfficer).first()
    smtp = db.query(SmtpConfig).first()
    schedule = db.query(EmailSchedule).first()
    sc = db.query(ServerConfig).first()
    return templates.TemplateResponse(request, "settings.html", {
        "officer": officer,
        "smtp": smtp,
        "schedule": schedule,
        "hotkey": sc.hotkey if sc else "Ctrl+F12",
    })


@router.get("/api/risk-officer")
def get_risk_officer(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    o = db.query(RiskOfficer).first()
    if not o:
        return {"name": "", "email": ""}
    return {"id": o.id, "name": o.name, "email": o.email}


@router.put("/api/risk-officer")
def update_risk_officer(data: RiskOfficerIn, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    o = db.query(RiskOfficer).first()
    if not o:
        o = RiskOfficer(name=data.name, email=data.email)
        db.add(o)
    else:
        o.name = data.name
        o.email = data.email
    db.commit()
    return {"ok": True}


@router.get("/api/smtp-config")
def get_smtp(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    s = db.query(SmtpConfig).first()
    if not s:
        return {}
    return {
        "id": s.id, "host": s.host, "port": s.port,
        "username": s.username, "use_tls": s.use_tls, "from_addr": s.from_addr,
    }


@router.put("/api/smtp-config")
def update_smtp(data: SmtpIn, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    s = db.query(SmtpConfig).first()
    if not s:
        s = SmtpConfig()
        db.add(s)
    s.host = data.host
    s.port = data.port
    s.username = data.username
    if data.password:
        s.password = data.password
    s.use_tls = data.use_tls
    s.from_addr = data.from_addr
    db.commit()
    return {"ok": True}


@router.post("/api/smtp-config/test")
def test_smtp(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    from services.email_service import send_test_email
    s = db.query(SmtpConfig).first()
    o = db.query(RiskOfficer).first()
    if not s or not o:
        return JSONResponse({"error": "Configura primero el SMTP y el responsable"}, status_code=400)
    try:
        send_test_email(s, o.email)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/email-schedule")
def get_schedule(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    s = db.query(EmailSchedule).first()
    if not s:
        return {}
    return {
        "frequency": s.frequency, "day_of_week": s.day_of_week,
        "day_of_month": s.day_of_month, "send_time": s.send_time,
        "active": s.active,
        "last_sent": s.last_sent.isoformat() if s.last_sent else None,
    }


@router.put("/api/email-schedule")
def update_schedule(data: ScheduleIn, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    s = db.query(EmailSchedule).first()
    if not s:
        s = EmailSchedule()
        db.add(s)
    s.frequency = data.frequency
    s.day_of_week = data.day_of_week
    s.day_of_month = data.day_of_month
    s.send_time = data.send_time
    s.active = data.active
    db.commit()
    from services.scheduler import reschedule
    reschedule(db)
    return {"ok": True}


@router.get("/api/config")
def get_config(db: Session = Depends(get_db)):
    sc = db.query(ServerConfig).first()
    return {"hotkey": sc.hotkey if sc else "Ctrl+F12"}


@router.put("/api/config")
def update_config(data: ServerConfigIn, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    sc = db.query(ServerConfig).first()
    if not sc:
        sc = ServerConfig(hotkey=data.hotkey)
        db.add(sc)
    else:
        sc.hotkey = data.hotkey
    db.commit()
    return {"ok": True}


@router.post("/api/email-schedule/send-now")
def send_now(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    from services.email_service import send_report_email
    try:
        send_report_email(db)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
