# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text, Time, create_engine, text)
from sqlalchemy.orm import DeclarativeBase, Session, relationship
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class Center(Base):
    __tablename__ = "centers"
    id      = Column(Integer, primary_key=True, autoincrement=True)
    name    = Column(String(128), nullable=False, unique=True)
    address = Column(Text)
    buildings = relationship("Building", back_populates="center", cascade="all, delete-orphan")


class Building(Base):
    __tablename__ = "buildings"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    center_id = Column(Integer, ForeignKey("centers.id"), nullable=False)
    name      = Column(String(128), nullable=False)
    address   = Column(Text)
    center    = relationship("Center", back_populates="buildings")
    floors    = relationship("Floor", back_populates="building", cascade="all, delete-orphan")


class Floor(Base):
    __tablename__ = "floors"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    name        = Column(String(64), nullable=False)
    building    = relationship("Building", back_populates="floors")
    rooms       = relationship("Room", back_populates="floor", cascade="all, delete-orphan")


class Room(Base):
    __tablename__ = "rooms"
    id       = Column(Integer, primary_key=True, autoincrement=True)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=False)
    name     = Column(String(128), nullable=False)
    floor    = relationship("Floor", back_populates="rooms")
    clients  = relationship("Client", back_populates="room")


class Group(Base):
    __tablename__ = "groups"
    id      = Column(Integer, primary_key=True, autoincrement=True)
    name    = Column(String(128), nullable=False)
    clients = relationship("Client", back_populates="group")


class Client(Base):
    __tablename__ = "clients"
    id          = Column(String(64), primary_key=True)
    name        = Column(String(128))
    room_id     = Column(Integer, ForeignKey("rooms.id"))
    group_id    = Column(Integer, ForeignKey("groups.id"))
    is_security = Column(Boolean, default=False)
    is_portable = Column(Boolean, default=False)
    last_ip     = Column(String(45))
    last_seen   = Column(DateTime)
    room        = relationship("Room", back_populates="clients")
    group       = relationship("Group", back_populates="clients")


class Alert(Base):
    __tablename__ = "alerts"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    client_id    = Column(String(64))
    username     = Column(String(128))
    room         = Column(String(128))
    floor        = Column(String(64))
    building     = Column(String(128))
    center       = Column(String(128))
    group_id     = Column(Integer)
    is_drill     = Column(Boolean, default=False)
    triggered_at = Column(DateTime, nullable=False)


class AdminUser(Base):
    __tablename__ = "admin_users"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)


class RiskOfficer(Base):
    __tablename__ = "risk_officer"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    name      = Column(String(256))
    email     = Column(String(256))
    center_id = Column(Integer, ForeignKey("centers.id"), nullable=True)
    center    = relationship("Center")


class SmtpConfig(Base):
    __tablename__ = "smtp_config"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    host      = Column(String(256))
    port      = Column(Integer, default=587)
    username  = Column(String(256))
    password  = Column(String(256))
    use_tls   = Column(Boolean, default=True)
    from_addr = Column(String(256))


class EmailSchedule(Base):
    __tablename__ = "email_schedule"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    frequency    = Column(String(16))
    day_of_week  = Column(Integer)
    day_of_month = Column(Integer)
    send_time    = Column(String(8))
    active       = Column(Boolean, default=True)
    last_sent    = Column(DateTime)


class ServerConfig(Base):
    __tablename__ = "server_config"
    id     = Column(Integer, primary_key=True, autoincrement=True)
    hotkey = Column(String(64), default="Ctrl+F12")


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(engine)
    _migrate(engine)


def _migrate(eng):
    """Migraciones incrementales que create_all no aplica en tablas existentes."""
    with eng.connect() as conn:
        # v2: responsable de prevención por centro
        result = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = 'risk_officer' AND column_name = 'center_id'"
        ))
        if result.scalar() == 0:
            conn.execute(text(
                "ALTER TABLE risk_officer "
                "ADD COLUMN center_id INT NULL, "
                "ADD CONSTRAINT fk_officer_center "
                "FOREIGN KEY (center_id) REFERENCES centers(id) ON DELETE CASCADE"
            ))
            conn.commit()

        # v3: equipo portátil
        result = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = 'clients' AND column_name = 'is_portable'"
        ))
        if result.scalar() == 0:
            conn.execute(text(
                "ALTER TABLE clients ADD COLUMN is_portable BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            conn.commit()
