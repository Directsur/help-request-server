# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from sqlalchemy.orm import Session
from database import Alert, Client, EmailSchedule, RiskOfficer, SmtpConfig, engine


def _build_report(alerts: list, period_start: datetime, period_end: datetime,
                  client_names: dict) -> str:
    total = len(alerts)
    users = set(a.username for a in alerts if a.username)
    hotspots: dict[str, int] = {}
    for a in alerts:
        loc = " > ".join(filter(None, [a.center, a.building, a.floor, a.room]))
        hotspots[loc] = hotspots.get(loc, 0) + 1
    sorted_hotspots = sorted(hotspots.items(), key=lambda x: x[1], reverse=True)

    lines = [
        "Informe de solicitudes de ayuda",
        f"Período: {period_start.strftime('%d/%m/%Y')} — {period_end.strftime('%d/%m/%Y')}",
        "",
        "RESUMEN",
        f"  Total de solicitudes: {total}",
        f"  Usuarios implicados: {len(users)}",
    ]
    if sorted_hotspots:
        lines.append(f"  Punto más frecuente: {sorted_hotspots[0][0]} ({sorted_hotspots[0][1]} solicitudes)")
    lines += ["", "DETALLE"]
    for a in alerts:
        loc    = " > ".join(filter(None, [a.center, a.building, a.floor, a.room]))
        name   = client_names.get(a.client_id)
        equipo = f"{name} ({a.client_id})" if name else (a.client_id or "—")
        lines.append(
            f"  {a.triggered_at.strftime('%d/%m/%Y %H:%M')}  |  {a.username or '—'}  |  {equipo}  |  {loc}"
        )
    lines += ["", "PUNTOS DE MAYOR FRECUENCIA"]
    for i, (loc, count) in enumerate(sorted_hotspots[:10], 1):
        lines.append(f"  {i}. {loc} — {count} solicitudes")
    lines += ["", "—", "Informe generado automáticamente por el sistema de solicitudes de ayuda."]
    return "\n".join(lines)


def _send(smtp_cfg: SmtpConfig, to_addr: str, subject: str, body: str):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = smtp_cfg.from_addr
    msg["To"] = to_addr

    if smtp_cfg.use_tls:
        server = smtplib.SMTP(smtp_cfg.host, smtp_cfg.port)
        server.starttls()
    else:
        server = smtplib.SMTP(smtp_cfg.host, smtp_cfg.port)

    if smtp_cfg.username and smtp_cfg.password:
        server.login(smtp_cfg.username, smtp_cfg.password)

    server.sendmail(smtp_cfg.from_addr, [to_addr], msg.as_string())
    server.quit()


def send_test_email(smtp_cfg: SmtpConfig, to_addr: str):
    _send(smtp_cfg, to_addr, "Prueba de conexión SMTP — Sistema de solicitudes de ayuda",
          "Este es un correo de prueba del sistema de solicitudes de ayuda.\n\nLa configuración SMTP es correcta.")


def send_report_email(db: Session | None = None):
    close_db = False
    if db is None:
        db = Session(engine)
        close_db = True
    try:
        smtp_cfg = db.query(SmtpConfig).first()
        officer = db.query(RiskOfficer).first()
        schedule = db.query(EmailSchedule).first()

        if not smtp_cfg or not officer or not officer.email:
            return

        now = datetime.utcnow()
        freq = schedule.frequency if schedule else "weekly"
        if freq == "daily":
            period_start = now - timedelta(days=1)
        elif freq == "monthly":
            period_start = now - timedelta(days=30)
        else:
            period_start = now - timedelta(weeks=1)

        alerts = db.query(Alert).filter(
            Alert.triggered_at >= period_start,
            Alert.triggered_at <= now,
            Alert.is_drill == False,
        ).order_by(Alert.triggered_at.desc()).all()

        ids = {a.client_id for a in alerts if a.client_id}
        client_names = {c.id: c.name for c in db.query(Client).filter(Client.id.in_(ids)).all()}

        body = _build_report(alerts, period_start, now, client_names)
        subject = (
            f"Informe de solicitudes de ayuda — "
            f"{period_start.strftime('%d/%m/%Y')} al {now.strftime('%d/%m/%Y')}"
        )
        _send(smtp_cfg, officer.email, subject, body)

        if schedule:
            schedule.last_sent = now
            db.commit()
    finally:
        if close_db:
            db.close()
