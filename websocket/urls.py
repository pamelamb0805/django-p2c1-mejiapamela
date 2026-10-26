from django.urls import path
from . import views  # Importa las vistas de tu app websocket

app_name = 'websocket'

urlpatterns = [
    # Ruta principal del chat (ej: /chat/)
    path('', views.chat_view, name='chat_room'), 
]