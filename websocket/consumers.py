#import json
#from channels.generic.websocket import AsyncWebsocketConsumer

#class ChatConsumer(AsyncWebsocketConsumer):
    #async def connect(self):
        #await self.accept()

    #async def disconnect(self, close_code):
        #pass

    #async def receive(self, text_data):
        #data = json.loads(text_data)
        #message = data['message']

        #await self.send(text_data=json.dumps({
            #'message': message
        #}))

#Eva3 --> Implementación Websocket --> PM
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist

class ChatConsumer(JsonWebsocketConsumer):
    def connect(self):
        user = self.scope["user"]
        # 1. Validar autenticación
        if not user.is_authenticated:
            self.close()
            return
        # 2. Identificar organización
        try:
            org_id = user.profile.organization_id
        except ObjectDoesNotExist:
            self.close()
            return
        if org_id is None:
            self.close()
            return
        # 3. Crear nombre del grupo
        self.group_name = f"chat_org_{org_id}"
        # 4. Unirse al grupo
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        self.accept()


    def disconnect(self, close_code):
    if hasattr(self, "group_name"):
        async_to_sync(
        self.channel_layer.group_discard
    )(
        self.group_name,
        self.channel_name
    )
    # 5. Recibir mensaje del navegador
    def receive_json(self, content):
        mensaje = content.get("mensaje", "")
        if not isinstance(mensaje, str):
            return
    mensaje = mensaje.strip()
    if not mensaje or len(mensaje) > 500:
        return
    # 6. Enviar mensaje al grupo
    async_to_sync(self.channel_layer.group_send)(
        self.group_name,
    {
        "type": "chat_event",
        "payload": {
        "mensaje": mensaje,
        "usuario": self.scope["user"].username
            }
        }
    )
    # 7. Entregar evento al navegador
    def chat_event(self, event):
        self.send_json(event["payload"])