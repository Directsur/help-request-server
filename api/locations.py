# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.auth import require_auth
from database import Building, Center, Client, Floor, Room, get_db

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


class CenterIn(BaseModel):
    name: str
    address: str = ""


class BuildingIn(BaseModel):
    center_id: int
    name: str
    address: str = ""


class FloorIn(BaseModel):
    building_id: int
    name: str


class RoomIn(BaseModel):
    floor_id: int
    name: str


@router.get("/locations", response_class=HTMLResponse)
def locations_view(request: Request, db: Session = Depends(get_db)):
    redir = require_auth(request)
    if redir:
        return redir
    centers = db.query(Center).all()
    tree = []
    for c in centers:
        c_data = {"id": c.id, "name": c.name, "address": c.address or "", "buildings": []}
        for b in c.buildings:
            b_data = {"id": b.id, "name": b.name, "address": b.address or "", "floors": []}
            for f in b.floors:
                f_data = {"id": f.id, "name": f.name, "rooms": [
                    {"id": r.id, "name": r.name} for r in f.rooms
                ]}
                b_data["floors"].append(f_data)
            c_data["buildings"].append(b_data)
        tree.append(c_data)
    return templates.TemplateResponse(request, "locations.html", {"tree": tree})


# --- Centers ---
@router.post("/api/centers")
def create_center(data: CenterIn, db: Session = Depends(get_db)):
    # Sin autenticación: los clientes de la red local necesitan crear ubicaciones
    center = Center(name=data.name, address=data.address)
    db.add(center)
    db.commit()
    db.refresh(center)
    return {"id": center.id, "name": center.name}


@router.put("/api/centers/{id}")
def update_center(id: int, data: CenterIn, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    center = db.get(Center, id)
    if not center:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    center.name = data.name
    center.address = data.address
    db.commit()
    return {"ok": True}


@router.delete("/api/centers/{id}")
def delete_center(id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    center = db.get(Center, id)
    if not center:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    db.delete(center)
    db.commit()
    return {"ok": True}


# --- Buildings ---
@router.post("/api/buildings")
def create_building(data: BuildingIn, db: Session = Depends(get_db)):
    b = Building(center_id=data.center_id, name=data.name, address=data.address)
    db.add(b)
    db.commit()
    db.refresh(b)
    return {"id": b.id, "name": b.name}


@router.put("/api/buildings/{id}")
def update_building(id: int, data: BuildingIn, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    b = db.get(Building, id)
    if not b:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    b.name = data.name
    b.address = data.address
    db.commit()
    return {"ok": True}


@router.delete("/api/buildings/{id}")
def delete_building(id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    b = db.get(Building, id)
    if not b:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    db.delete(b)
    db.commit()
    return {"ok": True}


# --- Floors ---
@router.post("/api/floors")
def create_floor(data: FloorIn, db: Session = Depends(get_db)):
    f = Floor(building_id=data.building_id, name=data.name)
    db.add(f)
    db.commit()
    db.refresh(f)
    return {"id": f.id, "name": f.name}


@router.put("/api/floors/{id}")
def update_floor(id: int, data: FloorIn, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    f = db.get(Floor, id)
    if not f:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    f.name = data.name
    db.commit()
    return {"ok": True}


@router.delete("/api/floors/{id}")
def delete_floor(id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    f = db.get(Floor, id)
    if not f:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    db.delete(f)
    db.commit()
    return {"ok": True}


# --- Rooms ---
@router.post("/api/rooms")
def create_room(data: RoomIn, db: Session = Depends(get_db)):
    r = Room(floor_id=data.floor_id, name=data.name)
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "name": r.name}


@router.put("/api/rooms/{id}")
def update_room(id: int, data: RoomIn, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    r = db.get(Room, id)
    if not r:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    r.name = data.name
    db.commit()
    return {"ok": True}


@router.delete("/api/rooms/{id}")
def delete_room(id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return JSONResponse({"error": "no autorizado"}, status_code=401)
    r = db.get(Room, id)
    if not r:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    clients = db.query(Client).filter(Client.room_id == id).count()
    if clients:
        return JSONResponse({"error": f"La sala tiene {clients} equipo(s) asignado(s)"}, status_code=409)
    db.delete(r)
    db.commit()
    return {"ok": True}


# --- Dropdown helpers for clients ---
@router.get("/api/centers")
def list_centers(db: Session = Depends(get_db)):
    return [{"id": c.id, "name": c.name} for c in db.query(Center).all()]


@router.get("/api/buildings")
def list_buildings(center_id: int, db: Session = Depends(get_db)):
    return [{"id": b.id, "name": b.name}
            for b in db.query(Building).filter(Building.center_id == center_id).all()]


@router.get("/api/floors")
def list_floors(building_id: int, db: Session = Depends(get_db)):
    return [{"id": f.id, "name": f.name}
            for f in db.query(Floor).filter(Floor.building_id == building_id).all()]


@router.get("/api/rooms")
def list_rooms(floor_id: int, db: Session = Depends(get_db)):
    return [{"id": r.id, "name": r.name}
            for r in db.query(Room).filter(Room.floor_id == floor_id).all()]
