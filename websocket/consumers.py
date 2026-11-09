
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist


MODULE_PERMISSIONS = {
    "organizaciones": "organizations.view_organization",
    "departamentos": "organizations.view_department",
    "zonas": "organizations.view_zone",
    "usuarios": "accounts.view_userprofile",
    "categorias": "devices.view_catalog",
    "catalogos": "devices.view_catalog",
    "productos": "devices.view_product",
    "dispositivos": "devices.view_device",
    "mediciones": "devices.view_measurement",
    "alertas": "devices.view_alertevent",
    "mantenimiento": "devices.view_maintenancerequest",
}


class ChatConsumer(JsonWebsocketConsumer):

    def connect(self):
        user = self.scope["user"]

        if not user.is_authenticated:
            self.close()
            return

        # Obtener la organización del usuario.
        try:
            organization_id = user.profile.organization_id
        except (ObjectDoesNotExist, AttributeError):
            organization_id = None

        # ROOT puede conectarse aunque no tenga perfil.
        if not organization_id and not user.is_superuser:
            self.close()
            return

        # Grupo de chat.
        if organization_id:
            self.group_name = f"chat_org_{organization_id}"
        else:
            self.group_name = "chat_root"

        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name,
        )

        # Grupo global de notificaciones exclusivo de ROOT.
        if user.is_superuser:
            async_to_sync(self.channel_layer.group_add)(
                "crud_root",
                self.channel_name,
            )

        self.accept()

    def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name,
                self.channel_name,
            )

        if self.scope["user"].is_superuser:
            async_to_sync(self.channel_layer.group_discard)(
                "crud_root",
                self.channel_name,
            )

    def receive_json(self, content, **kwargs):
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
        self.send_json(event["payload"])

    def crud_event(self, event):
        user = self.scope["user"]

        # ROOT recibe solamente la copia enviada a su grupo global.
        # Evita notificaciones duplicadas si tiene perfil de organización.
        if user.is_superuser and not event.get("root_only"):
            return

        if not user.is_superuser and event.get("root_only"):
            return

        # Comprobar permisos del módulo.
        permission = MODULE_PERMISSIONS.get(event.get("module"))

        if not user.is_superuser:
            if not permission or not user.has_perm(permission):
                return

        self.send_json({
            "type": "crud_update",
            **event["payload"],
        })
