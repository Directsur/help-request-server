# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from database import EmailSchedule, engine

_scheduler = BackgroundScheduler()


def _run_report():
    from services.email_service import send_report_email
    send_report_email()


def reschedule(db: Session | None = None):
    close_db = False
    if db is None:
        db = Session(engine)
        close_db = True
    try:
        _scheduler.remove_all_jobs()
        schedule = db.query(EmailSchedule).first()
        if not schedule or not schedule.active or not schedule.frequency:
            return

        time_parts = (schedule.send_time or "08:00").split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0

        if schedule.frequency == "daily":
            _scheduler.add_job(_run_report, "cron", hour=hour, minute=minute, id="report")
        elif schedule.frequency == "weekly":
            dow = schedule.day_of_week if schedule.day_of_week is not None else 0
            _scheduler.add_job(_run_report, "cron", day_of_week=dow,
                               hour=hour, minute=minute, id="report")
        elif schedule.frequency == "monthly":
            dom = schedule.day_of_month if schedule.day_of_month else 1
            _scheduler.add_job(_run_report, "cron", day=dom,
                               hour=hour, minute=minute, id="report")
    finally:
        if close_db:
            db.close()


def start_scheduler():
    _scheduler.start()
    reschedule()
