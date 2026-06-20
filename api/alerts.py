# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
import csv
import io
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from api.auth import require_auth
from database import Alert, get_db

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")

MAX_DRILL_RECORDS = 5


class AlertIn(BaseModel):
    client_id:    str
    username:     str
    room:         str = ""
    floor:        str = ""
    building:     str = ""
    center:       str = ""
    group_id:     int | None = None
    is_drill:     bool = False
    triggered_at: str | None = None


def _apply_filters(query, db, from_date, to_date, username, client_id,
                   center, building, floor, room, group_id):
    if from_date:
        query = query.filter(Alert.triggered_at >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.filter(Alert.triggered_at <= datetime.fromisoformat(to_date + "T23:59:59"))
    if username:
        query = query.filter(Alert.username.ilike(f"%{username}%"))
    if client_id:
        query = query.filter(Alert.client_id == client_id)
    if center:
        query = query.filter(Alert.center.ilike(f"%{center}%"))
    if building:
        query = query.filter(Alert.building.ilike(f"%{building}%"))
    if floor:
        query = query.filter(Alert.floor.ilike(f"%{floor}%"))
    if room:
        query = query.filter(Alert.room.ilike(f"%{room}%"))
    if group_id:
        query = query.filter(Alert.group_id == int(group_id))
    return query


def _purge_old_drills(db: Session):
    drills = (
        db.query(Alert)
        .filter(Alert.is_drill == True)
        .order_by(Alert.triggered_at.desc())
        .all()
    )
    if len(drills) > MAX_DRILL_RECORDS:
        for old in drills[MAX_DRILL_RECORDS:]:
            db.delete(old)
        db.commit()


@router.post("/api/alerts")
def receive_alert(data: AlertIn, db: Session = Depends(get_db)):
    triggered_at = datetime.utcnow()
    if data.triggered_at:
        try:
            triggered_at = datetime.fromisoformat(data.triggered_at)
        except ValueError:
            pass
    alert = Alert(
        client_id=data.client_id,
        username=data.username,
        room=data.room,
        floor=data.floor,
        building=data.building,
        center=data.center,
        group_id=data.group_id,
        is_drill=data.is_drill,
        triggered_at=triggered_at,
    )
    db.add(alert)
    db.commit()
    if data.is_drill:
        _purge_old_drills(db)
    return {"ok": True, "id": alert.id}


@router.get("/alerts", response_class=HTMLResponse)
def alerts_view(request: Request, db: Session = Depends(get_db),
                from_date: str = "", to_date: str = "", username: str = "",
                client_id: str = "", center: str = "", building: str = "",
                floor: str = "", room: str = "", group_id: str = ""):
    redir = require_auth(request)
    if redir:
        return redir
    query = db.query(Alert).filter(Alert.is_drill == False).order_by(Alert.triggered_at.desc())
    query = _apply_filters(query, db, from_date, to_date, username, client_id,
                           center, building, floor, room, group_id)
    alerts = query.limit(500).all()
    drills = (
        db.query(Alert)
        .filter(Alert.is_drill == True)
        .order_by(Alert.triggered_at.desc())
        .limit(MAX_DRILL_RECORDS)
        .all()
    )
    return templates.TemplateResponse(request, "alerts.html", {
        "alerts": alerts,
        "drills": drills,
        "filters": {
            "from_date": from_date, "to_date": to_date, "username": username,
            "client_id": client_id, "center": center, "building": building,
            "floor": floor, "room": room, "group_id": group_id,
        },
    })


@router.get("/api/alerts")
def list_alerts(request: Request, db: Session = Depends(get_db),
                from_date: str = "", to_date: str = "", username: str = "",
                client_id: str = "", center: str = "", building: str = "",
                floor: str = "", room: str = "", group_id: str = ""):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    query = db.query(Alert).filter(Alert.is_drill == False).order_by(Alert.triggered_at.desc())
    query = _apply_filters(query, db, from_date, to_date, username, client_id,
                           center, building, floor, room, group_id)
    alerts = query.limit(500).all()
    return [
        {
            "id": a.id,
            "client_id": a.client_id,
            "username": a.username,
            "room": a.room,
            "floor": a.floor,
            "building": a.building,
            "center": a.center,
            "triggered_at": a.triggered_at.isoformat(),
        }
        for a in alerts
    ]


@router.get("/api/alerts/hotspots")
def hotspots(request: Request, db: Session = Depends(get_db),
             from_date: str = "", to_date: str = ""):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    query = (
        db.query(
            Alert.center, Alert.building, Alert.floor, Alert.room,
            func.count(Alert.id).label("total")
        )
        .filter(Alert.is_drill == False)
        .group_by(Alert.center, Alert.building, Alert.floor, Alert.room)
        .order_by(func.count(Alert.id).desc())
    )
    if from_date:
        query = query.filter(Alert.triggered_at >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.filter(Alert.triggered_at <= datetime.fromisoformat(to_date + "T23:59:59"))
    rows = query.limit(20).all()
    return [
        {
            "location": " > ".join(filter(None, [r.center, r.building, r.floor, r.room])),
            "total": r.total,
        }
        for r in rows
    ]


@router.get("/api/alerts/export")
def export_csv(request: Request, db: Session = Depends(get_db),
               from_date: str = "", to_date: str = "", username: str = "",
               client_id: str = "", center: str = "", building: str = "",
               floor: str = "", room: str = "", group_id: str = ""):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    query = db.query(Alert).filter(Alert.is_drill == False).order_by(Alert.triggered_at.desc())
    query = _apply_filters(query, db, from_date, to_date, username, client_id,
                           center, building, floor, room, group_id)
    alerts = query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fecha/hora", "Usuario", "Equipo", "Centro", "Edificio", "Planta", "Sala"])
    for a in alerts:
        writer.writerow([
            a.triggered_at.strftime("%d/%m/%Y %H:%M:%S"),
            a.username, a.client_id,
            a.center, a.building, a.floor, a.room,
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=solicitudes-ayuda.csv"},
    )
