# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import socket
import threading
from datetime import datetime
from sqlalchemy.orm import Session
from database import Client, engine


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
