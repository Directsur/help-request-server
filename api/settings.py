# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.auth import require_auth
from database import Center, EmailSchedule, RiskOfficer, ServerConfig, SmtpConfig, get_db

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


class RiskOfficerIn(BaseModel):
    name: str
    email: str
    center_id: int | None = None


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


def _officer_dict(o: RiskOfficer) -> dict:
    return {
        "id": o.id,
        "name": o.name or "",
        "email": o.email or "",
        "center_id": o.center_id,
        "center_name": o.center.name if o.center else None,
    }


@router.get("/settings", response_class=HTMLResponse)
def settings_view(request: Request, db: Session = Depends(get_db)):
    redir = require_auth(request)
    if redir:
        return redir
    officers = db.query(RiskOfficer).order_by(RiskOfficer.center_id.nullsfirst()).all()
    centers  = db.query(Center).order_by(Center.name).all()
    smtp     = db.query(SmtpConfig).first()
    schedule = db.query(EmailSchedule).first()
    sc       = db.query(ServerConfig).first()
    return templates.TemplateResponse(request, "settings.html", {
        "officers": officers,
        "centers": centers,
        "smtp": smtp,
        "schedule": schedule,
        "hotkey": sc.hotkey if sc else "Ctrl+F12",
    })


@router.get("/api/risk-officer")
def get_risk_officers(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    officers = db.query(RiskOfficer).order_by(RiskOfficer.center_id.nullsfirst()).all()
    return [_officer_dict(o) for o in officers]


@router.put("/api/risk-officer")
def upsert_global_officer(data: RiskOfficerIn, request: Request, db: Session = Depends(get_db)):
    """Crea o actualiza el responsable global (center_id=NULL)."""
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    o = db.query(RiskOfficer).filter(RiskOfficer.center_id.is_(None)).first()
    if not o:
        o = RiskOfficer(name=data.name, email=data.email, center_id=None)
        db.add(o)
    else:
        o.name  = data.name
        o.email = data.email
    db.commit()
    return _officer_dict(o)


@router.post("/api/risk-officer")
def add_officer(data: RiskOfficerIn, request: Request, db: Session = Depends(get_db)):
    """Añade un responsable para un centro específico."""
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    if not data.center_id:
        return JSONResponse({"error": "center_id requerido"}, status_code=400)
    existing = db.query(RiskOfficer).filter(RiskOfficer.center_id == data.center_id).first()
    if existing:
        existing.name  = data.name
        existing.email = data.email
        db.commit()
        return _officer_dict(existing)
    o = RiskOfficer(name=data.name, email=data.email, center_id=data.center_id)
    db.add(o)
    db.commit()
    db.refresh(o)
    return _officer_dict(o)


@router.put("/api/risk-officer/{officer_id}")
def update_officer(officer_id: int, data: RiskOfficerIn, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    o = db.get(RiskOfficer, officer_id)
    if not o:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    o.name  = data.name
    o.email = data.email
    db.commit()
    return _officer_dict(o)


@router.delete("/api/risk-officer/{officer_id}")
def delete_officer(officer_id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    o = db.get(RiskOfficer, officer_id)
    if not o:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    if o.center_id is None:
        return JSONResponse({"error": "No se puede eliminar el responsable global"}, status_code=400)
    db.delete(o)
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
    o = db.query(RiskOfficer).filter(RiskOfficer.center_id.is_(None)).first()
    if not s or not o:
        return JSONResponse({"error": "Configura primero el SMTP y el responsable global"}, status_code=400)
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
