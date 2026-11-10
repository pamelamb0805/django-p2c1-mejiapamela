asgiref==3.12.1
Django==6.1
sqlparse==0.6.0
tzdata==2026.3

# EcoEnergy - Backend with Django

## Description and Objective
This project is developed with Python and Django.  
Its main objective is to build the backend foundation for EcoEnergy, focusing on structured development and scalability.

## Prerequisites
- Python 3.x installed
- Git installed
- Django (version defined in `requirements.txt`)

## Repository Cloning
```bash
git clone https://github.com/pamelamb0805/django-p2c1-mejiapamela
cd django-p2c1-mejiapamela

python -m venv .venv
# Activate environment
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows

pip install -r requirements.txt

python manage.py migrate
python manage.py runserver
```

##EVA 1
## Rutas funcionales
- `/` — Inicio
- `/zonas/` — Listado de zonas
- `/zonas/<id>/` — Detalle de zona (dispositivos, consumo, estado)
- `/dispositivos/` — Catálogo de dispositivos

## Pruebas realizadas
- Zona con estado NORMAL y ALERTA verificadas.
- Zona sin dispositivos (Austral) muestra mensaje correcto.
- ID de zona inexistente devuelve 404.

## Perfil de usuario: ver, editar y foto con recorte

Rama de trabajo: `feature/media-perfil`

### Páginas
- **Mi perfil** (`/accounts/perfil/`, `accounts:perfil`): muestra los datos del usuario autenticado (usuario, nombre, correo, organización, departamento, código de empleado, RUT, teléfono, dirección y rol).
- **Editar mi perfil** (`/accounts/perfil/editar/`, `accounts:perfil_editar`): tres formularios independientes.
  1. **Datos personales:** nombre, apellido y correo (obligatorios) y, opcionales, teléfono y dirección. Límites: nombre y apellido hasta 50 caracteres (solo letras, espacios, guion y apóstrofe); correo hasta 100 y sin repetirse; teléfono chileno de 9 dígitos; dirección hasta 100 caracteres (letras, números y `. , # - /`). Se rechazan datos sin sentido (por ejemplo, el mismo carácter repetido 4 o más veces). El RUT, el código de empleado, la organización y el departamento solo los cambia un administrador.
  2. **Foto de perfil:** se elige una imagen, se recorta con **Croppr**, se ve la vista previa y recién al presionar "Guardar foto" se envía.
  3. **Cambiar contraseña:** pide la contraseña actual, la nueva y su confirmación; aplica los validadores de Django. La sesión se mantiene abierta al cambiarla.

### Seguridad
- Ninguna vista recibe un id: todas usan `request.user`, así nadie puede cambiar el perfil, la foto o la contraseña de otro usuario.
- Los formularios tienen `fields` explícitos: no se puede modificar rol, permisos, organización ni código de empleado desde el perfil.
- Una acción de formulario inventada responde 400.
- Todos los formularios llevan `{% csrf_token %}`.

### Foto de perfil
- `UserProfile.avatar` (`ImageField`, requiere **Pillow**). El archivo se guarda en `media/accounts/avatars/AAAA/MM/` y en la base solo queda la ruta.
- El recorte se hace en el navegador con Croppr sobre un `<canvas>`; la imagen **ya recortada** es la que viaja al servidor y la que queda guardada (no es un recorte visual con CSS). Si se recarga la página, el recorte persiste.
- **Cancelar** descarta la imagen elegida y conserva la foto anterior.

| Validación (en el servidor) | Regla |
|---|---|
| Formato | Solo JPEG o PNG (se comprueba el contenido con Pillow, no la extensión) |
| Tamaño | Máximo 2 MiB |
| Archivo que no es imagen | Se rechaza con mensaje claro |

### Política de archivos reemplazados
- Al cambiar la foto, el perfil apunta al archivo nuevo y el anterior **queda en `media/accounts/avatars/`** (no se borra automáticamente).
- `media/` está en `.gitignore`: las fotos subidas no se versionan.
- Los archivos bajo `/media/` son de acceso público por URL.

### Pruebas realizadas
- Cambiar nombre y correo; correo repetido y campos vacíos (mensaje de error junto al campo).
- Cambiar contraseña: contraseña actual incorrecta, confirmación distinta y contraseña débil (error); caso correcto y entrar con la nueva.
- Subir foto con recorte, ver la vista previa, guardar, recargar y comprobar que persiste.
- Cancelar un recorte y comprobar que la foto anterior se conserva.
- Subir un WEBP/GIF, un PDF renombrado a `.jpg` y una imagen de más de 2 MiB (rechazos).
- Entrar con otro usuario y comprobar que solo puede editar lo suyo.

## Tiempo real (Django Channels)

- **Servidor:** `python manage.py runserver --noreload` levanta Daphne (ASGI): atiende HTTP y WebSocket. Con DEBUG desactivado se usa `daphne config.asgi:application`.
- **Ruta WebSocket:** `/ws/chat/` (autenticada por sesión; solo orígenes de `ALLOWED_HOSTS`). Cada usuario entra al grupo `chat_org_<id de su organización>`, calculado en el servidor: el navegador no elige la organización.
- **Capa de canales:** `InMemoryChannelLayer` (un solo proceso). Para varios procesos se necesita `channels_redis` y Redis.
- **Chat:** burbuja flotante abajo a la derecha, disponible en todas las pantallas (menú de páginas y panel). Al presionarla se abre una ventana emergente pequeña; muestra un contador de mensajes nuevos cuando está cerrada y se cierra con la X o la tecla Esc. El mensaje se envía por HTTP (`POST /chat/send/` con CSRF), el servicio `publish_chat_message` lo publica al grupo, el Consumer lo entrega y JavaScript lo muestra. Máximo 300 caracteres y el HTML se muestra literal. **Los mensajes no se guardan en la base de datos**; para que no desaparezcan al cambiar de pantalla, cada pestaña recuerda los últimos 50 (`sessionStorage`, por usuario; se borra al cerrar la pestaña). La página completa `/chat/` sigue disponible.
- **Listado de dispositivos en vivo:** cuando alguien crea, edita o elimina un dispositivo, el servidor publica un aviso **después de confirmar el guardado** (`transaction.on_commit`; no se avisa si el formulario es inválido ni si no cambió ningún dato). Los demás navegadores de la misma organización piden por HTTP la tabla actualizada y reemplazan solo ese bloque, sin recargar la página; el servidor vuelve a aplicar permisos, organización, filtros, orden y paginación. Si se pierde la conexión, el indicador de la pantalla pasa a "Sin conexión".
- **Para activarlo en otro listado:** agregar al bloque de la tabla `data-live-table="..."`, `data-live-modules="<módulo>"` y `data-live-url="{% url '...' %}"`.

### Pruebas
- Dos navegadores (uno en ventana privada) con usuarios de la misma organización: A escribe en `/chat/` y B lo ve sin recargar.
- Un usuario de otra organización no recibe los mensajes ni los avisos.
- Texto HTML en el chat: se muestra literal.
- A edita un dispositivo y B, con `/devices/` abierto (con filtros o en la página 2), ve el cambio sin F5.