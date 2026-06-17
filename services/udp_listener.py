# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import socket
import threading
from datetime import datetime
from sqlalchemy.orm import Session
from database import Alert, Client, engine


def _handle(sock: socket.socket, msg: dict, addr: tuple):
    msg_type = msg.get("type")

    if msg_type == "DISCOVER":
        response = json.dumps({"type": "SERVER_HERE"}).encode()
        sock.sendto(response, addr)

    elif msg_type == "HEARTBEAT":
        client_id = msg.get("client_id")
        if client_id:
            with Session(engine) as db:
                client = db.get(Client, client_id)
                if client:
                    client.last_ip = addr[0]
                    client.last_seen = datetime.utcnow()
                    db.commit()

    elif msg_type == "ALERT":
        with Session(engine) as db:
            triggered_at = datetime.utcnow()
            if msg.get("timestamp"):
                try:
                    triggered_at = datetime.fromisoformat(msg["timestamp"])
                except ValueError:
                    pass
            is_drill = bool(msg.get("is_drill", False))
            alert = Alert(
                client_id=msg.get("client_id", ""),
                username=msg.get("username", ""),
                room=msg.get("location", {}).get("room", ""),
                floor=msg.get("location", {}).get("floor", ""),
                building=msg.get("location", {}).get("building", ""),
                center=msg.get("location", {}).get("center", ""),
                group_id=msg.get("group_id"),
                is_drill=is_drill,
                triggered_at=triggered_at,
            )
            db.add(alert)
            db.commit()
            if is_drill:
                from api.alerts import _purge_old_drills
                _purge_old_drills(db)


def start_udp_listener(port: int = 54321):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", port))

    def loop():
        while True:
            try:
                data, addr = sock.recvfrom(4096)
                msg = json.loads(data.decode())
                _handle(sock, msg, addr)
            except Exception:
                pass

    threading.Thread(target=loop, daemon=True, name="udp-listener").start()
