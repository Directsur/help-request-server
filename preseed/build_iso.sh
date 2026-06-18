#!/bin/bash
# Copyright (C) 2025-2026 Direct Sevilla Global Services SL
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Genera una ISO de Debian 13 con instalación desatendida del servidor
# de Solicitudes de Ayuda.
#
# Uso: bash preseed/build_iso.sh
# Requisitos: xorriso, wget  (sudo apt-get install -y xorriso wget)

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ── Configuración ──────────────────────────────────────────────────────────────
DEBIAN_VERSION="13.5.0"
ARCH="amd64"
ISO_NAME="debian-${DEBIAN_VERSION}-${ARCH}-netinst.iso"
ISO_URL="https://cdimage.debian.org/debian-cd/current/${ARCH}/iso-cd/${ISO_NAME}"
OUTPUT_ISO="solicitud-ayuda-servidor-debian13-${ARCH}.iso"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRESEED_FILE="$SCRIPT_DIR/preseed.cfg"
WORK_DIR="$(mktemp -d /tmp/build-iso-XXXXXX)"

trap 'info "Limpiando directorio temporal..."; rm -rf "$WORK_DIR"' EXIT

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Construcción ISO — Solicitudes de Ayuda          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Dependencias ───────────────────────────────────────────────────────────────
for cmd in xorriso wget; do
    command -v "$cmd" &>/dev/null || error "Falta '$cmd'. Instálalo con: sudo apt-get install -y xorriso wget"
done
[[ -f "$PRESEED_FILE" ]] || error "No se encuentra preseed.cfg en $PRESEED_FILE"

# ── 1. Descargar ISO base ──────────────────────────────────────────────────────
if [[ -f "$ISO_NAME" ]]; then
    info "ISO base encontrada: $ISO_NAME"
else
    info "Descargando $ISO_NAME desde $ISO_URL ..."
    wget -q --show-progress "$ISO_URL" -O "$ISO_NAME" || \
        error "No se pudo descargar la ISO. Comprueba la URL o descárgala manualmente."
fi

# ── 2. Extraer ISO ────────────────────────────────────────────────────────────
info "Extrayendo contenido de la ISO..."
mkdir -p "$WORK_DIR/iso"
xorriso -osirrox on -indev "$ISO_NAME" -extract / "$WORK_DIR/iso" 2>/dev/null
chmod -R u+w "$WORK_DIR/iso"

# ── 3. Copiar preseed ─────────────────────────────────────────────────────────
info "Copiando preseed.cfg..."
cp "$PRESEED_FILE" "$WORK_DIR/iso/preseed.cfg"

# ── 4. Modificar arranque BIOS (isolinux) ─────────────────────────────────────
PARAMS="auto=true priority=critical file=/cdrom/preseed.cfg"

TXT_CFG="$WORK_DIR/iso/isolinux/txt.cfg"
if [[ -f "$TXT_CFG" ]]; then
    info "Modificando isolinux/txt.cfg (BIOS)..."
    # Añade parámetros al final de cada línea 'append' del instalador
    sed -i "s|^\(\s*append\s\+.*\)|\1 $PARAMS|" "$TXT_CFG"
    # Reduce timeout para que arranque automáticamente (en décimas de segundo)
    sed -i 's/^timeout .*/timeout 10/' "$WORK_DIR/iso/isolinux/isolinux.cfg" 2>/dev/null || true
fi

# ── 5. Modificar arranque UEFI (grub) ────────────────────────────────────────
GRUB_CFG="$WORK_DIR/iso/boot/grub/grub.cfg"
if [[ -f "$GRUB_CFG" ]]; then
    info "Modificando boot/grub/grub.cfg (UEFI)..."
    # Añade parámetros a las líneas 'linux' que cargan el kernel del instalador
    sed -i "s|^\(\s*linux\s\+.*/vmlinuz.*\)|\1 $PARAMS|" "$GRUB_CFG"
    # Reduce timeout a 1 segundo
    sed -i 's/^set timeout=.*/set timeout=1/' "$GRUB_CFG"
fi

# ── 6. Reempaquetar ISO ───────────────────────────────────────────────────────
info "Reempaquetando ISO → $OUTPUT_ISO ..."

# Extraer parámetros de boot de la ISO original con xorriso
BOOT_INFO=$(xorriso -indev "$ISO_NAME" -report_el_torito as_mkisofs 2>/dev/null || true)

# Construir el comando de reempaquetado
xorriso -as mkisofs \
    -r -J -joliet-long \
    -l -cache-inodes \
    -V "Solicitudes de Ayuda Srv" \
    -b isolinux/isolinux.bin \
    -c isolinux/boot.cat \
    -no-emul-boot \
    -boot-load-size 4 \
    -boot-info-table \
    -eltorito-alt-boot \
    -e boot/grub/efi.img \
    -no-emul-boot \
    -isohybrid-gpt-basdat \
    -isohybrid-mbr "$WORK_DIR/iso/isolinux/isohdpfx.bin" \
    -o "$OUTPUT_ISO" \
    "$WORK_DIR/iso" 2>/dev/null

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║              ISO generada correctamente              ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Archivo: $OUTPUT_ISO"
echo "  Tamaño:  $(du -sh "$OUTPUT_ISO" | cut -f1)"
echo ""
echo "  Credenciales por defecto tras la instalación:"
echo "    Root del sistema:   Direct2025!"
echo "    Web admin:          admin / admin"
echo ""
warn "Cambie las contraseñas después del primer acceso."
echo ""
echo "  Para crear una VM con esta ISO:"
echo "    - VMware/VirtualBox: nueva VM, mínimo 1 vCPU, 1 GB RAM, 30 GB disco"
echo "    - La instalación es completamente desatendida (~15 min con buena red)"
echo "    - Al terminar, acceda a http://<IP-de-la-VM>:8080"
echo ""
