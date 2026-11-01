from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist


class ChatConsumer(JsonWebsocketConsumer):

    def connect(self):
        user = self.scope["user"]

        # 1. Solo usuarios autenticados.
        if not user.is_authenticated:
            self.close()
            return

        # 2. Obtener la organización del usuario.
        try:
            org_id = user.profile.organization_id
        except (ObjectDoesNotExist, AttributeError):
            self.close()
            return

        if not org_id:
            self.close()
            return

        # 3. Grupo exclusivo de la organización.
        self.group_name = f"chat_org_{org_id}"

        # 4. Suscribir el socket al grupo.
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name,
        )

        self.accept()

    def disconnect(self, close_code):
        # 5. Salir del grupo al desconectarse.
        if hasattr(self, "group_name"):
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name,
                self.channel_name,
            )

    def receive_json(self, content, **kwargs):
        # 6. Recibir mensajes del chat.
        mensaje = content.get("mensaje", "")

        if not isinstance(mensaje, str):
            return

        mensaje = mensaje.strip()

        if not mensaje or len(mensaje) > 500:
            return

        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                "type": "chat_event",
                "payload": {
                    "mensaje": mensaje,
                    "usuario": self.scope["user"].username,
                },
            },
        )

    def chat_event(self, event):
        # 7. Entregar mensajes de chat al navegador.
        self.send_json(event["payload"])

    def crud_event(self, event):
        # 8. Entregar notificaciones de CRUD al navegador.
        self.send_json({
            "tipo": "crud",
            "modulo": event["module"],
            "accion": event["action"],
            "actor_id": event["actor_id"],
        })