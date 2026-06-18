# Despliegue del servidor mediante ISO preconfigurada

## ¿Qué es la ISO preconfigurada?

La ISO `solicitud-ayuda-servidor-debian13-amd64.iso` es una imagen de instalación de
Debian 13 modificada que instala y configura automáticamente el servidor de Solicitudes
de Ayuda sin ninguna intervención manual. Basta con arrancar un equipo (físico o virtual)
con ella para tener el servidor funcionando en 10-15 minutos.

> Desarrollado por **Direct Sevilla Global Services SL** — 20 años de experiencia en
> desarrollos para el sector sanitario. Aplicable a cualquier organización donde sea
> necesario comunicar emergencias de forma rápida en red local.
> Soporte e instalación: **info@directsur.com**

---

## Credenciales por defecto

| Acceso | Usuario | Contraseña |
|---|---|---|
| Root del sistema (SSH) | `root` | `Direct2025!` |
| Interfaz web admin | `admin` | `admin` |
| Base de datos | `helprequest` | *(generada automáticamente)* |

> **Cambie estas contraseñas inmediatamente después del primer acceso.**

---

## Requisitos del equipo (físico o virtual)

| Recurso | Mínimo | Recomendado |
|---|---|---|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Disco | 20 GB | 40 GB |
| Red | 1 adaptador (DHCP o IP fija) | IP estática recomendada |

---

## Despliegue en equipo físico

La ISO es una imagen híbrida que arranca tanto en BIOS como en UEFI, por lo que puede
grabarse en un USB y usarse para instalar el servidor en cualquier PC o servidor físico.

### Grabar la ISO en un USB

**Desde Windows** — con [Rufus](https://rufus.ie):
1. Conecte un USB de al menos 2 GB (se borrará todo su contenido).
2. Abra Rufus, seleccione la ISO y pulse **Empezar**.
3. Si pregunta por el modo de escritura, elija **Escritura en modo DD**.

**Desde Linux** — con `dd`:
```bash
# Sustituya /dev/sdX por el dispositivo USB (compruébelo con lsblk)
sudo dd if=solicitud-ayuda-servidor-debian13-amd64.iso of=/dev/sdX bs=4M status=progress
sudo sync
```

**Desde macOS** — con `dd`:
```bash
# Sustituya /dev/diskN por el dispositivo USB (compruébelo con diskutil list)
sudo dd if=solicitud-ayuda-servidor-debian13-amd64.iso of=/dev/rdiskN bs=4m
sudo sync
```

### Instalar en el equipo físico

1. Conecte el USB al equipo y arránquelo.
2. Entre en la BIOS/UEFI (normalmente F2, F12, Supr o Esc al encender) y configure
   el USB como primer dispositivo de arranque. O use el menú de arranque puntual (Boot Menu).
3. El instalador arranca. La única pregunta que aparece es el proxy HTTP (déjelo vacío si no es necesario). El resto es completamente desatendido.
4. **Atención:** el disco duro del equipo se particionará y formateará automáticamente.
   Asegúrese de que no hay datos que conservar en ese equipo.
5. Al terminar, el equipo se reinicia y el servidor queda en funcionamiento.
6. Retire el USB antes del siguiente arranque (o vuelva a configurar el orden de arranque).

> **Nota:** la instalación descarga paquetes de internet durante el proceso.
> El equipo debe tener conexión de red por cable (DHCP) durante la instalación.

---

## Despliegue en VMware (ESXi / Workstation / Fusion)

### VMware ESXi / vSphere

1. Descargue la ISO desde la página de releases:
   `https://github.com/Directsur/help-request-server/releases`

2. Suba la ISO al datastore de ESXi:
   **Storage → Datastores → Upload file**

3. Cree una nueva máquina virtual:
   - **Guest OS:** Linux → Debian GNU/Linux 11 (64-bit) o posterior
   - **CPU:** 2 vCPU · **RAM:** 2 GB · **Disco:** 40 GB (thin provision)
   - **Red:** adaptador en la red local del centro (VLAN correspondiente)
   - **CD/DVD:** conectar la ISO subida al datastore

4. Arranque la VM. La única pregunta que aparece es la del proxy:
   ```
   Arranca el instalador de Debian
        ↓
   Pregunta: ¿proxy HTTP? (vacío = sin proxy)
        ↓
   Particiona el disco automáticamente
        ↓
   Instala el sistema base (~5-8 min con buena red)
        ↓
   Descarga e instala el servidor de Solicitudes de Ayuda
        ↓
   Reinicia y queda en funcionamiento
   ```

5. Al terminar (la VM se reinicia sola), anote la IP que aparece en la consola
   o consúltela en su router/switch: `http://<IP-de-la-VM>:8080`

### VMware Workstation / Fusion

1. **File → New Virtual Machine → Custom**
2. Seleccione la ISO cuando pida el medio de instalación.
3. Guest OS: **Linux → Debian 11 o posterior (64-bit)**
4. Asigne los recursos (mínimo 1 GB RAM, 20 GB disco).
5. Arranque. La única pregunta que aparece es el proxy HTTP; responda y el resto es automático.

---

## Despliegue en VirtualBox

1. **Machine → New**
   - Name: `Solicitudes-Ayuda-Servidor`
   - Type: **Linux** · Version: **Debian (64-bit)**

2. **RAM:** 1024 MB o más · **Disco:** crear VDI de 20 GB (dinámico)

3. **Settings → Storage → Controller IDE:**
   - Haga clic en el icono de disco junto a "Empty"
   - Seleccione la ISO descargada

4. **Settings → Network:**
   - Adapter 1: **Bridged Adapter** (para que la VM esté en la misma red que los clientes)

5. Arranque la VM. Solo aparece la pregunta del proxy HTTP; el resto es completamente automático.

---

## Despliegue en Proxmox VE

1. Suba la ISO en **local (pve) → ISO Images → Upload**

2. Cree una VM:
   ```
   General:  nombre = solicitud-ayuda-servidor
   OS:       Type Linux, Version 6.x - 2.6 Kernel
   System:   BIOS = SeaBIOS (o OVMF para UEFI)
   Disks:    20 GB, VirtIO Block
   CPU:      2 cores
   Memory:   2048 MB
   Network:  VirtIO, bridge a la red del centro
   ```

3. En **Hardware → CD/DVD Drive**, añada la ISO.

4. Arranque. Solo aparece la pregunta del proxy HTTP; el resto es completamente desatendido.

5. Una vez terminada, puede crear una **plantilla** de la VM para despliegues futuros:
   - Apague la VM
   - Clic derecho → **Convert to Template**
   - Clone la plantilla para cada nueva instalación

---

## Primer acceso tras la instalación

### Interfaz web

Abra un navegador desde cualquier equipo de la red:

```
http://<IP-del-servidor>:8080
```

Usuario: `admin` · Contraseña: `admin`

**Pasos iniciales recomendados:**

1. **Cambiar contraseña admin** — menú de usuario (esquina superior derecha)
2. **Crear las ubicaciones** — Ubicaciones → Nuevo centro → Edificios → Plantas → Salas
3. **Crear grupos** (si se necesitan) — Grupos → Nuevo grupo
4. **Configurar el atajo de teclado** — Configuración → Atajo de teclado
5. **Configurar correo SMTP** (opcional) — Configuración → Servidor de correo

### Acceso SSH para administración

```bash
ssh root@<IP-del-servidor>
# Contraseña: Direct2025!  ← cámbiela inmediatamente
passwd
```

### Cambiar la contraseña del administrador web por línea de comandos

```bash
reset-admin-password admin
```

### IP estática (recomendado)

Edite `/etc/network/interfaces` para asignar una IP fija:

```
auto eth0
iface eth0 inet static
    address 192.168.1.10
    netmask 255.255.255.0
    gateway 192.168.1.1
    dns-nameservers 8.8.8.8
```

Reinicie la red: `systemctl restart networking`

---

## Puertos necesarios en el cortafuegos

| Puerto | Protocolo | Uso |
|---|---|---|
| 8080 | TCP | Interfaz web y API REST |
| 54321 | UDP | Descubrimiento de clientes y alertas |
| 22 | TCP | SSH (administración remota) |

Si hay un cortafuegos entre el servidor y los clientes, abra estos puertos en ambas direcciones.

---

## Comandos de administración

```bash
# Estado del servicio
systemctl status help-request-server

# Logs en tiempo real
journalctl -u help-request-server -f

# Reiniciar el servicio
systemctl restart help-request-server

# Resetear contraseña del administrador web
reset-admin-password admin

# Ver IP del servidor
ip a
```

---

## Instalación en redes con proxy

Si la infraestructura requiere un proxy para acceder a internet, el propio instalador
lo preguntará durante el proceso. No es necesario configurar nada antes de arrancar la ISO.

Durante el arranque de la ISO, el instalador de Debian mostrará la siguiente pregunta:

```
Información del proxy HTTP
Por favor, introduzca la información del proxy HTTP:
[                                        ]
```

- Si la red tiene salida directa a internet: **déjelo vacío** y pulse Enter.
- Si se necesita proxy: introduzca la URL completa, por ejemplo:
  `http://proxy.empresa.com:3128`

El proxy queda configurado automáticamente en el sistema instalado para apt, git y pip,
por lo que las actualizaciones futuras también lo usarán.

> Si el proxy requiere autenticación, use el formato:
> `http://usuario:contraseña@proxy.empresa.com:3128`

Para **instalaciones manuales** con `install.sh`, el script también preguntará por el
proxy al inicio de la instalación.

---

## Generar la ISO localmente (para personalizar)

Si desea regenerar la ISO con cambios (contraseñas distintas, hostname diferente, etc.):

```bash
# Requisitos
sudo apt-get install -y xorriso wget

# Desde la raíz del proyecto servidor
bash preseed/build_iso.sh
```

Consulte `preseed/preseed.cfg` para modificar parámetros como el hostname, la zona horaria
o la contraseña de root antes de generar la ISO.

El proxy no necesita configurarse en tiempo de construcción: el instalador lo preguntará
durante el arranque de la ISO.

---

Solicitudes de Ayuda es un producto de **Direct Sevilla Global Services SL**,
empresa con 20 años de experiencia en desarrollos para el sector sanitario.
Publicado bajo licencia [GNU AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html).
Para soporte técnico, servicios de instalación o consultas: **info@directsur.com**
