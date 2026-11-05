from django.db import models
from django.conf import settings

class ChatMessage(models.Model):
    # Usuario que envió el mensaje (vinculado a tu sistema de autenticación)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="Usuario"
    )
    
    # Nombre de la sala de chat (por si tienes varias salas, o una general)
    room = models.CharField(
        max_length=255, 
        default="general", 
        verbose_name="Sala"
    )
    
    # Contenido del mensaje
    message = models.TextField(verbose_name="Mensaje")
    
    # Fecha y hora en que se envió automáticamente
    timestamp = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Fecha y Hora"
    )

    def __str__(self):
        return f"{self.user.username}: {self.message[:30]} ({self.timestamp.strftime('%H:%M')})"

    class Meta:
        verbose_name = "Mensaje de Chat"
        verbose_name_plural = "Mensajes de Chat"
        ordering = ['timestamp']