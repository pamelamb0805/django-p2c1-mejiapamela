import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import websocket.routing  # Importa las rutas de tu app websocket
from config.routing import application

# Configurar el entorno de Django por defecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


# Inicializar la aplicación ASGI de Django para peticiones HTTP tradicionales
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket.routing.websocket_urlpatterns
        )
    ),
})