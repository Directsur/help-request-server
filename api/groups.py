# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.auth import require_auth
from database import Client, Group, get_db

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


class GroupIn(BaseModel):
    name: str


@router.get("/groups", response_class=HTMLResponse)
def groups_view(request: Request, db: Session = Depends(get_db)):
    redir = require_auth(request)
    if redir:
        return redir
    groups = db.query(Group).all()
    data = []
    for g in groups:
        count = db.query(Client).filter(Client.group_id == g.id).count()
        data.append({"id": g.id, "name": g.name, "client_count": count})
    return templates.TemplateResponse(request, "groups.html", {"groups": data})


@router.get("/api/groups")
def list_groups(db: Session = Depends(get_db)):
    groups = db.query(Group).all()
    return [{"id": g.id, "name": g.name} for g in groups]


@router.post("/api/groups")
def create_group(data: GroupIn, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    g = Group(name=data.name)
    db.add(g)
    db.commit()
    db.refresh(g)
    return {"id": g.id, "name": g.name}


@router.put("/api/groups/{id}")
def update_group(id: int, data: GroupIn, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    g = db.get(Group, id)
    if not g:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    g.name = data.name
    db.commit()
    return {"ok": True}


@router.delete("/api/groups/{id}")
def delete_group(id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    g = db.get(Group, id)
    if not g:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    db.query(Client).filter(Client.group_id == id).update({"group_id": None})
    db.delete(g)
    db.commit()
    return {"ok": True}
