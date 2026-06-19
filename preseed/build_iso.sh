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
for cmd in xorriso wget cpio gzip; do
    command -v "$cmd" &>/dev/null || error "Falta '$cmd'. Instálalo con: sudo apt-get install -y xorriso wget cpio gzip"
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

# ── 3. Incrustar preseed en el initrd ─────────────────────────────────────────
# El preseed en el initrd se carga automáticamente sin parámetros de arranque.
# Se copia también a la raíz de la ISO como respaldo (file=/cdrom/preseed.cfg).
info "Incorporando preseed.cfg en el initrd..."
INITRD_PATH=""
for candidate in "install.amd/initrd.gz" "install/initrd.gz"; do
    [[ -f "$WORK_DIR/iso/$candidate" ]] && INITRD_PATH="$candidate" && break
done

if [[ -n "$INITRD_PATH" ]]; then
    INITRD_FULL="$WORK_DIR/iso/$INITRD_PATH"
    INITRD_TMP="$WORK_DIR/initrd-work"
    mkdir -p "$INITRD_TMP"
    # cpio suele devolver código de error aunque funcione — se ignora con || true
    (cd "$INITRD_TMP" && zcat "$INITRD_FULL" | cpio -i --no-absolute-filenames 2>/dev/null) || true
    if [[ $(ls "$INITRD_TMP" 2>/dev/null | wc -l) -gt 0 ]]; then
        cp "$PRESEED_FILE" "$INITRD_TMP/preseed.cfg"
        (cd "$INITRD_TMP" && find . | cpio -o -H newc 2>/dev/null | gzip -9 > "$INITRD_FULL") || \
            warn "Aviso: reempaquetado del initrd falló — se usará file=/cdrom/preseed.cfg como respaldo."
        info "Preseed incrustado en $INITRD_PATH"
    else
        warn "No se pudo extraer el initrd — se usará file=/cdrom/preseed.cfg como respaldo."
    fi
    rm -rf "$INITRD_TMP"
else
    warn "No se encontró el initrd."
fi
# Copia también el preseed a la raíz de la ISO como método de respaldo
cp "$PRESEED_FILE" "$WORK_DIR/iso/preseed.cfg"

# ── 4. Modificar arranque BIOS (isolinux) ─────────────────────────────────────
# priority=critical: suprime todas las preguntas con respuesta en el preseed.
# file= actúa como respaldo por si el preseed del initrd no se aplica.
PARAMS="auto=true priority=critical file=/cdrom/preseed.cfg"

TXT_CFG="$WORK_DIR/iso/isolinux/txt.cfg"
ISOLINUX_CFG="$WORK_DIR/iso/isolinux/isolinux.cfg"
if [[ -f "$TXT_CFG" ]]; then
    info "Modificando isolinux (BIOS)..."
    # Añade parámetros al final de la línea 'append' del instalador
    sed -i "s|^\(\s*append\s\+.*\)|\1 $PARAMS|" "$TXT_CFG"
    # Selecciona la entrada 'install' como defecto y establece timeout de 5 s (50 décimas)
    sed -i 's/^default .*/default install/' "$ISOLINUX_CFG" 2>/dev/null || true
    sed -i 's/^timeout .*/timeout 50/'     "$ISOLINUX_CFG" 2>/dev/null || true
fi

# ── 5. Modificar arranque UEFI (grub) ────────────────────────────────────────
GRUB_CFG="$WORK_DIR/iso/boot/grub/grub.cfg"
if [[ -f "$GRUB_CFG" ]]; then
    info "Modificando grub.cfg (UEFI)..."
    # Añade parámetros a las líneas 'linux' del instalador
    sed -i "s|^\(\s*linux\s\+.*/vmlinuz.*\)|\1 $PARAMS|" "$GRUB_CFG"
    # Elimina cualquier set default/timeout existente y los reinserta al principio
    # para evitar que líneas posteriores del archivo original los sobreescriban.
    # Índice 1='Install' (Graphical install=0, Install=1)
    sed -i '/^\s*set default=/d; /^\s*set timeout=/d' "$GRUB_CFG"
    sed -i "1s/^/set default=1\nset timeout=5\n\n/" "$GRUB_CFG"
fi

# ── 6. Reempaquetar ISO ───────────────────────────────────────────────────────
info "Reempaquetando ISO → $OUTPUT_ISO ..."

# Extraer el MBR híbrido de la ISO original (primeros 432 bytes)
dd if="$ISO_NAME" bs=1 count=432 of="$WORK_DIR/mbr.bin" 2>/dev/null

# Localizar la imagen EFI dentro del contenido extraído
EFI_IMG=""
for candidate in "boot/grub/efi.img" "EFI/boot/efi.img" "efi.img"; do
    [[ -f "$WORK_DIR/iso/$candidate" ]] && EFI_IMG="$candidate" && break
done

# Construir comando xorriso
XORRISO_CMD=(
    xorriso -as mkisofs
    -r -J -joliet-long -l -cache-inodes
    -V "Solicitudes de Ayuda Srv"
    -b isolinux/isolinux.bin
    -c isolinux/boot.cat
    -no-emul-boot -boot-load-size 4 -boot-info-table
    -isohybrid-mbr "$WORK_DIR/mbr.bin"
)
if [[ -n "$EFI_IMG" ]]; then
    info "Imagen EFI encontrada: $EFI_IMG"
    XORRISO_CMD+=(-eltorito-alt-boot -e "$EFI_IMG" -no-emul-boot -isohybrid-gpt-basdat)
else
    warn "No se encontró imagen EFI — la ISO solo arrancará en modo BIOS."
fi
XORRISO_CMD+=(-o "$OUTPUT_ISO" "$WORK_DIR/iso")

"${XORRISO_CMD[@]}" || error "xorriso falló al reempaquetar la ISO."

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
