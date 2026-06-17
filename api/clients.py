# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.auth import require_auth
from database import Client, Floor, Building, Center, Group, Room, get_db

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")

ONLINE_THRESHOLD = timedelta(minutes=5)


def _full_location(client: Client) -> dict:
    loc = {"room": "", "floor": "", "building": "", "center": ""}
    if client.room:
        loc["room"] = client.room.name
        f = client.room.floor
        if f:
            loc["floor"] = f.name
            b = f.building
            if b:
                loc["building"] = b.name
                c = b.center
                if c:
                    loc["center"] = c.name
    return loc


def _peers(client: Client, db: Session) -> list:
    now = datetime.utcnow()
    peers = []
    security = db.query(Client).filter(
        Client.is_security == True,
        Client.id != client.id,
        Client.last_ip != None,
        Client.last_seen >= now - ONLINE_THRESHOLD,
    ).all()
    for p in security:
        peers.append({"client_id": p.id, "ip": p.last_ip})

    if client.group_id:
        group_peers = db.query(Client).filter(
            Client.group_id == client.group_id,
            Client.id != client.id,
            Client.is_security == False,
            Client.last_ip != None,
            Client.last_seen >= now - ONLINE_THRESHOLD,
        ).all()
        for p in group_peers:
            peers.append({"client_id": p.id, "ip": p.last_ip})
    else:
        other = db.query(Client).filter(
            Client.id != client.id,
            Client.is_security == False,
            Client.last_ip != None,
            Client.last_seen >= now - ONLINE_THRESHOLD,
        ).all()
        for p in other:
            peers.append({"client_id": p.id, "ip": p.last_ip})

    seen = set()
    unique = []
    for p in peers:
        if p["client_id"] not in seen:
            seen.add(p["client_id"])
            unique.append(p)
    return unique


class RegisterIn(BaseModel):
    name: str | None = None
    ip: str | None = None


class LocationIn(BaseModel):
    room_id: int


class GroupAssignIn(BaseModel):
    group_id: int | None


class SecurityIn(BaseModel):
    is_security: bool


@router.get("/clients", response_class=HTMLResponse)
def clients_view(request: Request, db: Session = Depends(get_db)):
    redir = require_auth(request)
    if redir:
        return redir
    clients = db.query(Client).all()
    groups = db.query(Group).all()
    now = datetime.utcnow()
    data = []
    for c in clients:
        loc = _full_location(c)
        loc_str = " > ".join(filter(None, [loc["center"], loc["building"], loc["floor"], loc["room"]]))
        online = bool(c.last_seen and c.last_seen >= now - ONLINE_THRESHOLD)
        data.append({
            "id": c.id,
            "name": c.name or c.id,
            "location": loc_str,
            "group_id": c.group_id,
            "group_name": c.group.name if c.group else "—",
            "is_security": c.is_security,
            "online": online,
            "last_seen": c.last_seen.strftime("%d/%m/%Y %H:%M") if c.last_seen else "—",
        })
    return templates.TemplateResponse("clients.html", {
        "request": request,
        "clients": data,
        "groups": [{"id": g.id, "name": g.name} for g in groups],
    })


@router.get("/api/clients")
def list_clients(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    clients = db.query(Client).all()
    now = datetime.utcnow()
    result = []
    for c in clients:
        loc = _full_location(c)
        loc_str = " > ".join(filter(None, [loc["center"], loc["building"], loc["floor"], loc["room"]]))
        result.append({
            "id": c.id,
            "name": c.name or c.id,
            "location": loc_str,
            "group_id": c.group_id,
            "group_name": c.group.name if c.group else None,
            "is_security": c.is_security,
            "online": bool(c.last_seen and c.last_seen >= now - ONLINE_THRESHOLD),
        })
    return result


@router.post("/api/clients/{client_id}/register")
def register_client(client_id: str, data: RegisterIn, request: Request,
                    db: Session = Depends(get_db)):
    ip = data.ip or request.client.host
    client = db.get(Client, client_id)
    if not client:
        client = Client(id=client_id, name=data.name, last_ip=ip, last_seen=datetime.utcnow())
        db.add(client)
    else:
        if data.name:
            client.name = data.name
        client.last_ip = ip
        client.last_seen = datetime.utcnow()
    db.commit()
    loc = _full_location(client)
    return {
        "location": loc,
        "room_id": client.room_id,
        "group_id": client.group_id,
        "is_security": client.is_security,
        "peers": _peers(client, db),
    }


@router.post("/api/clients/{client_id}/heartbeat")
def heartbeat(client_id: str, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host
    client = db.get(Client, client_id)
    if not client:
        client = Client(id=client_id, last_ip=ip, last_seen=datetime.utcnow())
        db.add(client)
    else:
        client.last_ip = ip
        client.last_seen = datetime.utcnow()
    db.commit()
    return {"peers": _peers(client, db)}


@router.get("/api/clients/{client_id}/location")
def get_location(client_id: str, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        return {"room_id": None, "location": {"room": "", "floor": "", "building": "", "center": ""}}
    return {"room_id": client.room_id, "location": _full_location(client)}


@router.put("/api/clients/{client_id}/location")
def update_location(client_id: str, data: LocationIn, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    client.room_id = data.room_id
    db.commit()
    return {"ok": True, "location": _full_location(client)}


@router.put("/api/clients/{client_id}/group")
def assign_group(client_id: str, data: GroupAssignIn, request: Request,
                 db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    client = db.get(Client, client_id)
    if not client:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    client.group_id = data.group_id
    db.commit()
    return {"ok": True}


@router.put("/api/clients/{client_id}/security")
def set_security(client_id: str, data: SecurityIn, request: Request,
                 db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    client = db.get(Client, client_id)
    if not client:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    client.is_security = data.is_security
    db.commit()
    return {"ok": True}


@router.get("/api/clients/{client_id}/peers")
def get_peers(client_id: str, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        return []
    return _peers(client, db)
