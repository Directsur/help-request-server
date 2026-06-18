#!/bin/bash
# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
set -e

# ─── Colores ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[+]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*"; exit 1; }
ask()     { echo -e "${YELLOW}[?]${NC} $*"; }

# ─── Comprobaciones previas ────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "Este script debe ejecutarse como root (sudo ./install.sh)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="help-request-server"
SERVICE_USER="helprequest"
INSTALL_DIR="/opt/help-request-server"
CONFIG_DIR="/etc/help-request-server"
LOG_DIR="/var/log/help-request-server"
VENV_DIR="$INSTALL_DIR/venv"
DB_NAME="help_request"
DB_USER="helprequest"

# Modo no-interactivo: NONINTERACTIVE=1 DB_PASSWORD=... API_PORT=... ADMIN_USER=... ADMIN_PASSWORD=...
NONINTERACTIVE="${NONINTERACTIVE:-0}"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Instalación — Sistema de Solicitudes de Ayuda    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ─── Contraseña de base de datos ──────────────────────────────────────────────
if [[ -f "$CONFIG_DIR/env" ]]; then
    warn "Detectada instalación previa en $CONFIG_DIR/env"
    if [[ "$NONINTERACTIVE" == "1" ]]; then
        warn "Modo no-interactivo: reinstalando sobre instalación existente."
    else
        ask "¿Reinstalar? Se mantendrá la base de datos existente. [s/N]"
        read -r REINSTALL
        [[ "$REINSTALL" != "s" && "$REINSTALL" != "S" ]] && { info "Instalación cancelada."; exit 0; }
    fi
    DB_PASSWORD=$(grep DB_PASSWORD "$CONFIG_DIR/env" | cut -d= -f2)
else
    if [[ "$NONINTERACTIVE" == "1" ]]; then
        DB_PASSWORD="${DB_PASSWORD:-$(python3 -c "import secrets; print(secrets.token_hex(16))")}"
        info "Contraseña de base de datos generada automáticamente."
    else
        ask "Contraseña para el usuario de base de datos '$DB_USER':"
        read -rs DB_PASSWORD
        echo ""
        [[ -z "$DB_PASSWORD" ]] && error "La contraseña no puede estar vacía"
    fi
fi

# ─── Puerto de la API ──────────────────────────────────────────────────────────
if [[ "$NONINTERACTIVE" == "1" ]]; then
    API_PORT="${API_PORT:-8080}"
else
    ask "Puerto de la interfaz web [8080]:"
    read -r API_PORT
    API_PORT="${API_PORT:-8080}"
fi

# ─── Proxy de red ─────────────────────────────────────────────────────────────
if [[ "$NONINTERACTIVE" == "1" ]]; then
    PROXY_URL="${PROXY_URL:-}"
else
    ask "Proxy de red (dejar vacío si hay salida directa a internet):"
    ask "Ejemplo: http://proxy.empresa.com:3128"
    read -r PROXY_URL
fi

if [[ -n "$PROXY_URL" ]]; then
    info "Configurando proxy: $PROXY_URL"
    export http_proxy="$PROXY_URL"
    export https_proxy="$PROXY_URL"
    echo "Acquire::http::Proxy \"$PROXY_URL\";" > /etc/apt/apt.conf.d/01proxy
    grep -q "http_proxy" /etc/environment 2>/dev/null || \
        printf 'http_proxy=%s\nhttps_proxy=%s\n' "$PROXY_URL" "$PROXY_URL" >> /etc/environment
fi

# ─── 1. Dependencias del sistema ───────────────────────────────────────────────
info "Actualizando repositorios e instalando dependencias..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv mariadb-server mariadb-client

# ─── 2. Arrancar y habilitar MariaDB ──────────────────────────────────────────
info "Configurando MariaDB..."
systemctl enable --now mariadb

# ─── 3. Crear base de datos y usuario ─────────────────────────────────────────
info "Creando base de datos '$DB_NAME' y usuario '$DB_USER'..."
mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
EOF

# ─── 4. Usuario del sistema ────────────────────────────────────────────────────
info "Creando usuario del sistema '$SERVICE_USER'..."
id "$SERVICE_USER" &>/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"

# ─── 5. Copiar archivos ────────────────────────────────────────────────────────
info "Instalando archivos en $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
rsync -a --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    "$SCRIPT_DIR/" "$INSTALL_DIR/"

# ─── 6. Entorno virtual Python ────────────────────────────────────────────────
info "Creando entorno virtual Python..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"

# ─── 7. Directorios de logs y config ──────────────────────────────────────────
mkdir -p "$CONFIG_DIR" "$LOG_DIR"
chown "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"

# ─── 8. Fichero de configuración ──────────────────────────────────────────────
info "Generando configuración en $CONFIG_DIR/env..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

cat > "$CONFIG_DIR/env" <<EOF
DB_HOST=localhost
DB_PORT=3306
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
SECRET_KEY=$SECRET_KEY
UDP_PORT=54321
API_PORT=$API_PORT
EOF

chmod 600 "$CONFIG_DIR/env"
chown root:root "$CONFIG_DIR/env"

# ─── 9. Permisos de archivos ───────────────────────────────────────────────────
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/scripts/reset-admin-password"

# ─── 10. Script de reset en PATH ──────────────────────────────────────────────
info "Instalando comando 'reset-admin-password'..."
cat > /usr/local/bin/reset-admin-password <<WRAPPER
#!/bin/bash
set -a
source $CONFIG_DIR/env
set +a
exec $VENV_DIR/bin/python3 $INSTALL_DIR/scripts/reset-admin-password "\$@"
WRAPPER
chmod +x /usr/local/bin/reset-admin-password

# ─── 11. Servicio systemd ─────────────────────────────────────────────────────
info "Creando servicio systemd '$SERVICE_NAME'..."
cat > "/etc/systemd/system/$SERVICE_NAME.service" <<EOF
[Unit]
Description=Sistema de Solicitudes de Ayuda
After=network.target mariadb.service
Requires=mariadb.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$CONFIG_DIR/env
ExecStart=$VENV_DIR/bin/uvicorn main:app --host 0.0.0.0 --port \${API_PORT} --workers 1
Restart=on-failure
RestartSec=5
StandardOutput=append:$LOG_DIR/server.log
StandardError=append:$LOG_DIR/error.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# ─── 12. Inicializar base de datos ────────────────────────────────────────────
info "Inicializando tablas en la base de datos..."
(
    set -a; source "$CONFIG_DIR/env"; set +a
    cd "$INSTALL_DIR"
    "$VENV_DIR/bin/python3" -c "from database import init_db; init_db(); print('Tablas creadas.')"
)

# ─── 13. Crear usuario administrador ──────────────────────────────────────────
echo ""
info "Creando usuario administrador para la interfaz web..."
if [[ "$NONINTERACTIVE" == "1" ]]; then
    ADMIN_USER="${ADMIN_USER:-admin}"
    ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
else
    ask "Nombre de usuario administrador [admin]:"
    read -r ADMIN_USER
    ADMIN_USER="${ADMIN_USER:-admin}"
fi

(
    set -a; source "$CONFIG_DIR/env"; set +a
    ADMIN_PASSWORD="${ADMIN_PASSWORD:-}" /usr/local/bin/reset-admin-password "$ADMIN_USER"
)

# ─── 14. Arrancar servicio ────────────────────────────────────────────────────
info "Arrancando servicio..."
systemctl restart "$SERVICE_NAME"
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
    info "Servicio activo correctamente."
else
    warn "El servicio no arrancó. Revisa los logs:"
    echo "  journalctl -u $SERVICE_NAME -n 30"
fi

# ─── Resumen ──────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                Instalación completada                ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Interfaz web:  http://$(hostname -I | awk '{print $1}'):$API_PORT"
echo "  Usuario:       $ADMIN_USER"
echo "  Logs:          $LOG_DIR/"
echo "  Configuración: $CONFIG_DIR/env"
echo ""
echo "  Comandos útiles:"
echo "    systemctl status $SERVICE_NAME"
echo "    journalctl -u $SERVICE_NAME -f"
echo "    reset-admin-password [usuario]"
echo ""
