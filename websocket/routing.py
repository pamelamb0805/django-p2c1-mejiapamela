from django.urls import path
from . import consumers  # Importa los consumers que crearás en tu app

websocket_urlpatterns = [
    # Ruta del WebSocket (ejemplo: ws://127.0.0.1:8000/ws/chat/)
    path('ws/chat/', consumers.ChatConsumer.as_asgi()),
]