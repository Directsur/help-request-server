# Manual de usuario — Interfaz web del servidor

## Acceso al sistema

Abra un navegador en cualquier equipo de la red y vaya a:

```
http://<IP-del-servidor>:8080
```

Introduzca el usuario (`admin`) y la contraseña configurada durante la instalación.
La sesión permanece activa mientras el navegador esté abierto. Para cerrar sesión,
pulse **Cerrar sesión** en la parte inferior del menú lateral.

> Si olvidó la contraseña, el administrador del servidor puede restablecerla ejecutando
> `sudo reset-admin-password` en la consola del servidor.

---

## Panel de control (Dashboard)

La pantalla inicial muestra un resumen del estado del sistema:

- **Equipos en línea**: equipos que han enviado señal de vida en los últimos 5 minutos.
- **Equipos de seguridad en línea**: subconjunto de los anteriores marcados como seguridad.
- **Solicitudes hoy / este mes**: contador de alertas reales (los simulacros no se cuentan).
- **Últimas solicitudes**: tabla con las 10 alertas más recientes.

---

## Ubicaciones

Desde **Ubicaciones** se gestiona la jerarquía geográfica del centro:

```
Centro → Edificio → Planta → Sala
```

### Añadir un centro

1. Pulse **Nuevo centro**.
2. Introduzca el **nombre** del centro y opcionalmente su **dirección completa**.
3. Pulse **Guardar**.

La dirección es solo informativa y no se incluye en los mensajes de alerta.

### Añadir edificio, planta y sala

El proceso es idéntico para cada nivel. Seleccione siempre el elemento padre antes de crear
uno nuevo (por ejemplo, seleccione el centro antes de crear un edificio).

### Editar o eliminar

Utilice los botones de lápiz (editar) y papelera (eliminar) junto a cada elemento.
**No se puede eliminar un elemento que tenga subelementos o equipos asociados.**

### Creación desde el cliente

Los equipos cliente también pueden crear nuevos centros, edificios, plantas y salas
directamente desde su ventana de configuración de ubicación, pulsando el botón **[+]**
junto al campo correspondiente. Esto permite al personal añadir una sala nueva sin
necesidad de acceder al interfaz web de administración. Las ediciones y eliminaciones
solo están disponibles desde este interfaz web.

---

## Equipos

Desde **Equipos** se ven y gestionan todos los equipos cliente registrados.

Un equipo se registra automáticamente la primera vez que el cliente arranca y contacta con
el servidor. Aparece en la lista con:

- **Nombre**: nombre de red del equipo.
- **Ubicación**: sala asignada.
- **Grupo**: grupo al que pertenece.
- **Seguridad**: indica si es un equipo de guardia/seguridad.
- **Última conexión**: hora del último contacto.

### Asignar ubicación y grupo

1. Pulse el botón de edición junto al equipo.
2. Seleccione la sala en el desplegable de ubicaciones.
3. Seleccione el grupo (opcional).
4. Active **Equipo de seguridad** si este equipo debe recibir siempre todas las alertas,
   independientemente del grupo.
5. Pulse **Guardar**.

> Los equipos de seguridad reciben todas las alertas de todos los grupos, sin excepción.

---

## Grupos

Los grupos permiten filtrar qué equipos reciben las alertas. Un equipo solo recibe alertas
del equipo que envía si ambos pertenecen al mismo grupo, o si el receptor es de seguridad.

### Casos de uso típicos

- **Grupo por planta**: todos los equipos de la primera planta en un grupo; las alertas de
  esa planta solo llegan a esa planta (más los de seguridad).
- **Grupo por especialidad**: urgencias, consultas externas, etc.
- **Sin grupo**: si ningún equipo tiene grupo asignado, las alertas llegan a todos.

### Crear un grupo

1. Pulse **Nuevo grupo**.
2. Introduzca el nombre del grupo.
3. Pulse **Guardar**.
4. Asigne los equipos al grupo desde la vista de **Equipos**.

---

## Historial de solicitudes

La sección **Solicitudes** muestra el listado completo de alertas registradas (excluye
simulacros). Para cada alerta se muestra:

- Fecha y hora
- Usuario y equipo de origen
- Ubicación completa (sala / planta / edificio / centro)
- Grupo

Se puede filtrar por rango de fechas usando los campos de fecha en la parte superior.

### Simulacros

Los simulacros (Ctrl + Mayúsculas + F12) se muestran en una sección separada con fondo
naranja al final de la página. Solo se conservan los últimos 5 registros de simulacro.
Los simulacros no aparecen en los informes ni en los correos enviados al responsable.

---

## Informes

Desde **Informes** puede generar resúmenes del historial de alertas filtrados por:

- **Rango de fechas**
- **Centro**
- **Edificio**
- **Usuario**

El informe muestra el número de alertas por equipo y por ubicación, lo que permite
identificar los puntos de mayor incidencia.

> Los simulacros quedan excluidos de todos los informes.

---

## Configuración

### Responsable de prevención de riesgos

En **Configuración → Responsable** puede registrar el nombre y correo electrónico del
responsable de prevención de riesgos laborales del centro. Este correo recibirá los
informes periódicos programados.

### Configuración SMTP (correo saliente)

Para que los correos funcionen, configure el servidor de correo saliente:

| Campo        | Descripción                                      |
|--------------|--------------------------------------------------|
| Servidor     | Nombre o IP del servidor SMTP (p. ej. smtp.gmail.com) |
| Puerto       | Normalmente 587 (TLS) o 465 (SSL)               |
| Usuario      | Cuenta de correo emisora                        |
| Contraseña   | Contraseña de la cuenta                         |
| Usar TLS     | Activado para la mayoría de servidores modernos |
| Dirección de envío | Dirección que aparecerá como remitente    |

Pulse **Guardar** y luego **Enviar correo de prueba** para verificar la configuración.

### Envíos periódicos

Configure cuándo se envían automáticamente los informes al responsable:

- **Frecuencia**: diaria, semanal o mensual.
- **Día de la semana** (para envíos semanales): lunes a domingo.
- **Día del mes** (para envíos mensuales): del 1 al 28.
- **Hora de envío**: hora exacta (formato 24h).
- **Activo**: active o desactive el envío periódico sin perder la configuración.

### Atajo de teclado global

El atajo de teclado que activa la alerta en todos los clientes se configura aquí.

1. Pulse el campo de atajo.
2. Pulse la combinación de teclas deseada (por ejemplo, Ctrl + F10).
3. El campo muestra la combinación detectada.
4. Pulse **Guardar**.

El nuevo atajo se distribuye automáticamente a todos los clientes la próxima vez que
arranquen o se reconecten al servidor. **El atajo de simulacro (Ctrl + Mayúsculas + F12)
es fijo y no se puede cambiar.**

> Evite atajos que colisionen con atajos del sistema operativo o de las aplicaciones
> médicas en uso. Se recomienda usar teclas de función (F9–F12) con Ctrl.

---

## Ayuda y soporte

Para consultas técnicas o incidencias, contacte con el administrador del sistema o con
el proveedor del servicio. Los registros del servidor están disponibles en la consola
mediante:

```bash
sudo journalctl -u help-request-server -f
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
