# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
import os

DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", 3306))
DB_NAME     = os.getenv("DB_NAME", "help_request")
DB_USER     = os.getenv("DB_USER", "helprequest")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

SECRET_KEY  = os.getenv("SECRET_KEY", "cambia-esta-clave-en-produccion")
UDP_PORT    = int(os.getenv("UDP_PORT", 54321))
API_PORT    = int(os.getenv("API_PORT", 8080))
