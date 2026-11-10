from django.urls import path
from . import views  # Importa las vistas de tu app websocket

app_name = 'websocket'

urlpatterns = [
    # Ruta principal del chat (ej: /chat/)
    path('', views.chat_view, name='chat_room'),

    # Clase 11 --> PM: envío de mensajes por HTTP (POST + CSRF), ej: /chat/send/
    path('send/', views.send_message, name='send'),
]