#!/bin/bash
# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Comprueba si hay commits nuevos en GitHub y actualiza el servidor si los hay.
# Ejecutado diariamente a las 3:00 por el timer help-request-server-update.timer

set -euo pipefail

INSTALL_DIR="/opt/help-request-server"
VENV_DIR="$INSTALL_DIR/venv"
CONFIG_DIR="/etc/help-request-server"
SERVICE_NAME="help-request-server"
LOG_FILE="/var/log/help-request-server/auto-update.log"
VERSION_FILE="$INSTALL_DIR/.installed_commit"
REPO_URL="https://github.com/Directsur/help-request-server"
API_URL="https://api.github.com/repos/Directsur/help-request-server/commits/main"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

# Cargar proxy si está configurado en el sistema
set -a
[[ -f /etc/environment ]] && source /etc/environment 2>/dev/null || true
set +a

log "── Comprobando actualizaciones ──────────────────────────"

# Obtener hash del último commit en main desde la API de GitHub
REMOTE_HASH=$(curl -sf --max-time 30 "$API_URL" | \
    python3 -c "import sys,json; print(json.load(sys.stdin)['sha'])" 2>/dev/null || echo "")

if [[ -z "$REMOTE_HASH" ]]; then
    log "No se pudo contactar con GitHub. Sin cambios aplicados."
    exit 0
fi

LOCAL_HASH=$(cat "$VERSION_FILE" 2>/dev/null || echo "")

if [[ "$REMOTE_HASH" == "$LOCAL_HASH" ]]; then
    log "Sin cambios (versión instalada: ${LOCAL_HASH:0:8}). Nada que actualizar."
    exit 0
fi

log "Actualización disponible: ${LOCAL_HASH:0:8} → ${REMOTE_HASH:0:8}"

# Clonar en directorio temporal
TMPDIR=$(mktemp -d /tmp/hr-update-XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT

log "Descargando repositorio..."
if ! git clone --depth=1 "$REPO_URL" "$TMPDIR/repo" 2>&1 | tee -a "$LOG_FILE"; then
    log "ERROR: no se pudo clonar el repositorio. Actualización cancelada."
    exit 1
fi

# Detener el servicio
log "Deteniendo servicio..."
systemctl stop "$SERVICE_NAME"

# Actualizar archivos (preserva venv, config y logs)
log "Instalando archivos nuevos..."
rsync -a --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    "$TMPDIR/repo/" "$INSTALL_DIR/"
chown -R helprequest:helprequest "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/scripts/reset-admin-password"
chmod +x "$INSTALL_DIR/scripts/auto-update.sh"

# Actualizar la copia instalada del propio script si ha cambiado
if ! diff -q "$INSTALL_DIR/scripts/auto-update.sh" /usr/local/bin/help-request-auto-update > /dev/null 2>&1; then
    log "Actualizando script de actualización automática..."
    install -m 755 "$INSTALL_DIR/scripts/auto-update.sh" /usr/local/bin/help-request-auto-update
fi

# Actualizar dependencias Python
log "Actualizando dependencias Python..."
"$VENV_DIR/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"

# Aplicar cambios de esquema de base de datos (solo añade, nunca borra)
log "Verificando esquema de base de datos..."
(
    set -a; source "$CONFIG_DIR/env"; set +a
    cd "$INSTALL_DIR"
    "$VENV_DIR/bin/python3" -c "from database import init_db; init_db()" 2>&1 | tee -a "$LOG_FILE"
)

# Guardar versión instalada
echo "$REMOTE_HASH" > "$VERSION_FILE"

# Arrancar servicio
log "Arrancando servicio..."
systemctl start "$SERVICE_NAME"
sleep 3

if systemctl is-active --quiet "$SERVICE_NAME"; then
    log "Actualización completada. Versión instalada: ${REMOTE_HASH:0:8}"
else
    log "ADVERTENCIA: el servicio no arrancó tras la actualización."
    log "Revise los logs: journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi
