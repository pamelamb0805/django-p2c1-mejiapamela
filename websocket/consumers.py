from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist

from .services import CHAT_MAX_LENGTH


class ChatConsumer(JsonWebsocketConsumer):

    def connect(self):
        user = self.scope["user"]

        # Solo usuarios autenticados.
        if not user.is_authenticated:
            self.close()
            return

        # Obtener la organización del perfil.
        try:
            organization_id = user.profile.organization_id
        except (ObjectDoesNotExist, AttributeError):
            self.close()
            return

        if not organization_id:
            self.close()
            return

        # Grupo exclusivo de la organización.
        self.group_name = f"chat_org_{organization_id}"

        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name,
        )

        self.accept()

    def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name,
                self.channel_name,
            )

    def receive_json(self, content, **kwargs):
        # Recibir mensajes del chat enviados directamente por WebSocket.
        # (El chat de la clase 11 envía por HTTP; esto se mantiene con el MISMO formato de mensaje y el mismo límite.)
        mensaje = content.get("message", content.get("mensaje", ""))

        if not isinstance(mensaje, str):
            return

        mensaje = mensaje.strip()

        if not mensaje or len(mensaje) > CHAT_MAX_LENGTH:
            return

        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                "type": "chat_event",
                "payload": {
                    "type": "chat_message",
                    "username": self.scope["user"].username,
                    "message": mensaje,
                },
            },
        )

    def chat_event(self, event):
        # Entregar mensajes normales del chat.
        self.send_json(event["payload"])

    def crud_event(self, event):
        # Entregar notificaciones de operaciones CRUD.
        self.send_json({
            "type": "crud_update",
            "module": event["module"],
            "action": event["action"],
            "actor_id": event["actor_id"],
        })