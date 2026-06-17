# Solicitudes de Ayuda — Servidor

> Sistema de alertas de emergencia en red local — componente servidor

[![Licencia: AGPL v3](https://img.shields.io/badge/Licencia-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.11%2B-yellow.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com/)

Solicitudes de Ayuda es un sistema de alerta inmediata diseñado originalmente para personal sanitario y administrativo de centros de salud y hospitales, aunque es igualmente aplicable a cualquier organización o sector donde sea necesario comunicar una emergencia de forma rápida entre equipos de una misma red local: centros educativos, residencias, instalaciones industriales, servicios de seguridad, etc. Cuando alguien pulsa el atajo de teclado configurado en su equipo, todos los compañeros de su grupo reciben una notificación instantánea en pantalla con la ubicación exacta de quien solicitó ayuda.

Este repositorio contiene el **componente servidor**: API REST, interfaz web de administración y escucha UDP. Los clientes de escritorio están en un repositorio separado.

---

## Características

- **Interfaz web de administración** con Bootstrap 5 — gestión completa desde el navegador
- **Jerarquía de ubicaciones** configurable: Centro → Edificio → Planta → Sala
- **Grupos de notificación** para filtrar alertas por zona o especialidad
- **Equipos de seguridad** que reciben siempre todos los avisos, independientemente del grupo
- **Historial de alertas** con filtros por fecha, centro, edificio y usuario
- **Informes** para identificar puntos de mayor incidencia
- **Envío periódico de informes** por correo al responsable de prevención de riesgos
- **Modo simulacro** separado del historial real, con límite de 5 registros conservados
- **Atajo de teclado global** configurable desde el servidor y distribuido automáticamente a todos los clientes
- **Descubrimiento automático** por UDP broadcast — los clientes encuentran el servidor sin configuración manual
- **Funcionamiento sin servidor** — los clientes se comunican en P2P aunque el servidor esté caído

---

## Arquitectura

```
                        Red local del centro
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  ┌───────────┐  UDP broadcast / unicast  ┌───────────────┐ │
  │  │  Cliente  │ ──────────────────────── ▶│    Cliente    │ │
  │  │ (consulta)│                           │  (seguridad)  │ │
  │  └─────┬─────┘                           └───────────────┘ │
  │        │ TCP REST :8080                                     │
  │        ▼                                                    │
  │  ┌─────────────────────────┐                               │
  │  │       Servidor          │  :8080  Interfaz web admin    │
  │  │   FastAPI + MySQL       │  :54321 UDP (broadcast)       │
  │  └─────────────────────────┘                               │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

Los clientes envían las alertas por **UDP broadcast** (y unicast a peers conocidos para redes con VLANs) de forma inmediata. En paralelo, notifican al servidor por **TCP REST** para el registro histórico. Si el servidor no está disponible, las alertas P2P siguen funcionando.

---

## Requisitos

| Componente | Versión mínima              | Notas                            |
|------------|-----------------------------|----------------------------------|
| SO         | Debian 12 / Ubuntu 22.04    | También Ubuntu 24.04, Debian 11  |
| Python     | 3.11                        | Incluido en Debian 12            |
| MySQL      | 8.0                         | O MariaDB 10.6+                  |
| RAM        | 512 MB                      | 1 GB recomendado                 |

---

## Instalación rápida

```bash
# 1. Preparar MySQL (si no está instalado)
sudo apt-get install -y mysql-server
sudo mysql -e "
  CREATE DATABASE help_request CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  CREATE USER 'helprequest'@'localhost' IDENTIFIED BY 'TuContraseña';
  GRANT ALL PRIVILEGES ON help_request.* TO 'helprequest'@'localhost';
  FLUSH PRIVILEGES;"

# 2. Ejecutar el instalador
sudo bash install.sh
```

El script solicita de forma interactiva la contraseña de MySQL, la contraseña del administrador web y una clave secreta para las sesiones (se genera automáticamente si se deja en blanco).

Al finalizar, el servicio queda activo en el puerto **8080**:

```
http://<IP-del-servidor>:8080
```

Para más detalles, consulta [`docs/manual-instalacion-servidor.md`](docs/manual-instalacion-servidor.md).

---

## Configuración

El instalador crea `/etc/help-request-server/env` (modo 600):

```ini
DB_HOST=localhost
DB_PORT=3306
DB_NAME=help_request
DB_USER=helprequest
DB_PASSWORD=<contraseña>
SECRET_KEY=<clave secreta>
UDP_PORT=54321
API_PORT=8080
```

Edite este fichero y reinicie el servicio para aplicar cambios:

```bash
sudo systemctl restart help-request-server
```

---

## Comandos de administración

```bash
# Estado del servicio
sudo systemctl status help-request-server

# Logs en tiempo real
sudo journalctl -u help-request-server -f

# Restablecer contraseña del administrador web
sudo reset-admin-password
```

---

## Interfaz web

| Sección        | Descripción                                               |
|----------------|-----------------------------------------------------------|
| Dashboard       | Estado en tiempo real: equipos en línea, alertas del día |
| Equipos         | Gestión de clientes registrados, grupos y seguridad      |
| Grupos          | Definición de grupos de notificación por zona            |
| Ubicaciones     | Jerarquía Centro → Edificio → Planta → Sala              |
| Solicitudes     | Historial de alertas reales + sección separada de simulacros |
| Informes        | Resúmenes filtrables por fecha, centro, edificio, usuario |
| Configuración   | Atajo de teclado global, SMTP, responsable de prevención, programación de correos |
| Ayuda           | Manual de usuario integrado                              |

---

## API para clientes

Los clientes se comunican con el servidor a través de estos endpoints públicos (sin autenticación):

| Método | Ruta                                 | Descripción                          |
|--------|--------------------------------------|--------------------------------------|
| `GET`  | `/api/config`                        | Obtiene el atajo de teclado activo   |
| `POST` | `/api/clients/{id}/register`         | Registro/actualización del cliente   |
| `POST` | `/api/clients/{id}/heartbeat`        | Señal de vida y obtención de peers   |
| `PUT`  | `/api/clients/{id}/location`         | Actualiza la sala asignada           |
| `POST` | `/api/alerts`                        | Registra una alerta o simulacro      |
| `GET`  | `/api/centers`                       | Lista de centros                     |
| `GET`  | `/api/buildings?center_id=X`         | Edificios de un centro               |
| `GET`  | `/api/floors?building_id=X`          | Plantas de un edificio               |
| `GET`  | `/api/rooms?floor_id=X`              | Salas de una planta                  |
| `POST` | `/api/centers` `/buildings` `/floors` `/rooms` | Crear nuevas ubicaciones |

El servidor también escucha en UDP (puerto 54321) los mensajes `DISCOVER`, `HEARTBEAT` y `ALERT` enviados por los clientes.

---

## Desarrollo local

```bash
# Clonar y preparar entorno
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Variables de entorno mínimas
export DB_HOST=localhost DB_PORT=3306 DB_NAME=help_request \
       DB_USER=helprequest DB_PASSWORD=dev SECRET_KEY=dev-secret

# Arrancar
uvicorn main:app --reload --port 8080
```

---

## Estructura del proyecto

```
help-request-server/
├── main.py                  # Punto de entrada FastAPI, lifespan, rutas principales
├── config.py                # Variables de entorno
├── database.py              # Modelos SQLAlchemy y sesión
├── api/
│   ├── auth.py              # Login/logout, middleware de sesión
│   ├── alerts.py            # CRUD de alertas y simulacros
│   ├── clients.py           # Registro, heartbeat y ubicación de clientes
│   ├── groups.py            # Gestión de grupos
│   ├── locations.py         # Centros, edificios, plantas, salas
│   ├── reports.py           # Generación de informes
│   └── settings.py          # Atajo de teclado, SMTP, responsable, programación
├── services/
│   ├── udp_listener.py      # Escucha UDP broadcast (DISCOVER, HEARTBEAT, ALERT)
│   ├── email_service.py     # Envío de informes por correo
│   └── scheduler.py         # APScheduler para envíos periódicos
├── web/
│   ├── templates/           # Plantillas Jinja2 + Bootstrap 5
│   └── static/              # CSS personalizado
├── scripts/
│   └── reset-admin-password # Utilidad de consola para restablecer contraseña
├── docs/
│   ├── manual-instalacion-servidor.md
│   └── manual-usuario-servidor.md
├── install.sh               # Instalador para Debian/Ubuntu
├── requirements.txt
└── LICENSE
```

---

## Licencia

Solicitudes de Ayuda se publica bajo la **GNU Affero General Public License, versión 3**
(AGPL-3.0-or-later). Puede usar, copiar, modificar y redistribuir el software libremente
siempre que conserve esta misma licencia y haga públicas las modificaciones que distribuya
o ponga en producción.

Texto completo: <https://www.gnu.org/licenses/agpl-3.0.html>

---

## Soporte comercial e instalación

Desarrollado por **Direct Sevilla Global Services SL**, con 20 años de experiencia en
desarrollos para el sector sanitario.

Ofrecemos la plantilla de máquina virtual preconfigurada lista para desplegar, así como
servicios profesionales de instalación, formación y soporte técnico.

**info@directsur.com**
