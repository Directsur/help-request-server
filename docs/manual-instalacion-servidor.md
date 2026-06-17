# Manual de instalación — Servidor de Solicitudes de Ayuda

## Descripción

El servidor centraliza el registro de alertas, gestiona las ubicaciones de los equipos,
genera informes y sirve el interfaz web de administración. Los clientes pueden funcionar
sin servidor (modo local), pero sin él no hay histórico ni informes.

---

## Requisitos del sistema

| Componente | Versión mínima              | Notas                                 |
|------------|------------------------------|---------------------------------------|
| SO         | Debian 11 / Ubuntu 22.04 LTS | También Debian 12, 13, Ubuntu 24.04   |
| Python     | 3.11                         | Debian 12: 3.11 · Debian 13: 3.13    |
| MySQL      | 8.0                          | O MariaDB 10.6+                       |
| RAM        | 512 MB                       | 1 GB recomendado                      |
| Disco      | 2 GB libres                  | Para logs y base de datos             |
| Red        | IP estática recomendada      | O reserva DHCP fija                   |

> El servidor se ha diseñado para funcionar en una máquina virtual de pocos recursos.
> Con 1 vCPU y 1 GB de RAM es más que suficiente para un centro sanitario completo.

---

## Preparación de MySQL

Si MySQL no está instalado:

```bash
sudo apt-get update
sudo apt-get install -y mysql-server
sudo mysql_secure_installation
```

Cree la base de datos y el usuario para la aplicación:

```sql
-- Conéctese como root: sudo mysql
CREATE DATABASE help_request CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'helprequest'@'localhost' IDENTIFIED BY 'ContraseñaSegura';
GRANT ALL PRIVILEGES ON help_request.* TO 'helprequest'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Anote la contraseña: la necesitará durante la instalación.

---

## Instalación

### 1. Descomprima el paquete

```bash
tar -xzf help-request-server.tar.gz
cd help-request-server
```

O si lo ha descargado desde el repositorio:

```bash
git clone https://github.com/su-repo/help-request-server.git
cd help-request-server
```

### 2. Ejecute el script de instalación

```bash
sudo bash install.sh
```

El script le pedirá de forma interactiva:

- **Contraseña de MySQL** para el usuario `helprequest`
- **Contraseña del administrador web** (usuario: `admin`)
- **Clave secreta** para las sesiones (pulse Enter para generar una aleatoria)

Al finalizar, el script:
- Crea el usuario de sistema `helprequest`
- Instala el entorno virtual Python en `/opt/help-request-server/venv/`
- Crea el fichero de configuración en `/etc/help-request-server/env` (modo 600)
- Registra e inicia el servicio systemd `help-request-server`
- Inicializa la base de datos

### 3. Verifique la instalación

```bash
systemctl status help-request-server
```

Debería ver `active (running)`. El servicio escucha en el puerto **8080** (HTTP).

---

## Configuración del cortafuegos

Si el sistema tiene `ufw` activo:

```bash
# Interfaz web de administración (solo desde la red interna)
sudo ufw allow from 192.168.0.0/16 to any port 8080

# Alertas UDP (todos los equipos de la red)
sudo ufw allow 54321/udp
```

Ajuste el rango de red según su infraestructura. El puerto 8080 **no debe exponerse
a internet** salvo que se use una VPN o proxy inverso con HTTPS.

---

## Acceso al interfaz web

Abra un navegador y vaya a:

```
http://<IP-del-servidor>:8080
```

Inicie sesión con el usuario `admin` y la contraseña que estableció durante la instalación.

---

## Comandos de administración

### Iniciar / detener / reiniciar el servicio

```bash
sudo systemctl start help-request-server
sudo systemctl stop help-request-server
sudo systemctl restart help-request-server
```

### Ver los registros en tiempo real

```bash
sudo journalctl -u help-request-server -f
```

### Restablecer la contraseña del administrador web

Si olvidó la contraseña del administrador:

```bash
sudo reset-admin-password
```

El comando le pedirá la nueva contraseña y la actualiza en la base de datos.

---

## Actualización

1. Detenga el servicio:
   ```bash
   sudo systemctl stop help-request-server
   ```
2. Sustituya los archivos de la aplicación en `/opt/help-request-server/`:
   ```bash
   sudo rsync -a --exclude=venv ./ /opt/help-request-server/
   ```
3. Actualice las dependencias Python:
   ```bash
   sudo -u helprequest /opt/help-request-server/venv/bin/pip install -r /opt/help-request-server/requirements.txt
   ```
4. Reinicie el servicio:
   ```bash
   sudo systemctl start help-request-server
   ```

---

## Configuración avanzada

El fichero de configuración está en `/etc/help-request-server/env`:

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

Puede cambiar el puerto de escucha modificando `API_PORT` y reiniciando el servicio.
Si cambia el puerto, actualice también el cortafuegos.

---

## Desinstalación

```bash
sudo systemctl stop help-request-server
sudo systemctl disable help-request-server
sudo rm /etc/systemd/system/help-request-server.service
sudo systemctl daemon-reload
sudo rm -rf /opt/help-request-server/
sudo rm -rf /etc/help-request-server/
sudo userdel helprequest
# Para borrar también la base de datos:
sudo mysql -e "DROP DATABASE help_request; DROP USER 'helprequest'@'localhost';"
```

---

## Licencia, soporte y contacto

**Licencia:** Solicitudes de Ayuda se publica bajo la
**GNU Affero General Public License, versión 3** (AGPL-3.0-or-later).
Puede usar, copiar, modificar y redistribuir el software libremente siempre que
conserve esta misma licencia y haga públicas las modificaciones que distribuya o
ponga en producción. Esta licencia no limita en ningún caso la prestación de
servicios profesionales sobre el software.

Texto completo: <https://www.gnu.org/licenses/agpl-3.0.html>

---

Solicitudes de Ayuda es un producto de **Direct Sevilla Global Services SL**, empresa con
20 años de experiencia en desarrollos para el sector sanitario.

Para soporte técnico, servicios de instalación o cualquier consulta:

**info@directsur.com**
