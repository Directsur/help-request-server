# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from api.auth import require_auth
from database import Alert, get_db
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/reports", response_class=HTMLResponse)
def reports_view(request: Request, db: Session = Depends(get_db),
                 from_date: str = "", to_date: str = ""):
    redir = require_auth(request)
    if redir:
        return redir

    query = db.query(Alert).filter(Alert.is_drill == False)
    if from_date:
        query = query.filter(Alert.triggered_at >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.filter(Alert.triggered_at <= datetime.fromisoformat(to_date + "T23:59:59"))

    alerts = query.all()
    total = len(alerts)
    unique_users = len(set(a.username for a in alerts if a.username))
    unique_clients = len(set(a.client_id for a in alerts if a.client_id))

    hotspot_query = db.query(
        Alert.center, Alert.building, Alert.floor, Alert.room,
        func.count(Alert.id).label("total")
    ).filter(Alert.is_drill == False)\
     .group_by(Alert.center, Alert.building, Alert.floor, Alert.room)\
     .order_by(func.count(Alert.id).desc())
    if from_date:
        hotspot_query = hotspot_query.filter(
            Alert.triggered_at >= datetime.fromisoformat(from_date))
    if to_date:
        hotspot_query = hotspot_query.filter(
            Alert.triggered_at <= datetime.fromisoformat(to_date + "T23:59:59"))

    hotspots = [
        {
            "location": " > ".join(filter(None, [r.center, r.building, r.floor, r.room])),
            "total": r.total,
        }
        for r in hotspot_query.limit(20).all()
    ]
    max_total = hotspots[0]["total"] if hotspots else 1

    return templates.TemplateResponse(request, "reports.html", {
        "total": total,
        "unique_users": unique_users,
        "unique_clients": unique_clients,
        "hotspots": hotspots,
        "max_total": max_total,
        "filters": {"from_date": from_date, "to_date": to_date},
    })
