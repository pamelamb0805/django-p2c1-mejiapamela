#eva3 --> Implementación Websocket --> PM
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

# Clase 11 --> PM: largo máximo de un mensaje del chat. Se usa en la vista, en el Consumer y en el HTML.
CHAT_MAX_LENGTH = 300


def publish_chat_message(user, org_id, message):
    """
    Publica un mensaje del chat al grupo de la organización.
    La vista valida; este servicio publica; el Consumer distribuye; JavaScript presenta.
    """
    layer = get_channel_layer()
    if layer is None:
        raise RuntimeError("Channel layer no configurado")

    async_to_sync(layer.group_send)(
        f"chat_org_{org_id}",
        {
            # "type" selecciona el método chat_event() del Consumer.
            "type": "chat_event",
            # "payload.type" le indica a JavaScript cómo tratar el contenido.
            "payload": {
                "type": "chat_message",
                "username": user.get_username(),
                "message": message,
            },
        },
    )


def publish_crud_event(module, action, actor_id, organization_id=None):
    """
    Publica un evento CRUD exclusivamente a los usuarios
    conectados a la organización correspondiente.
    """
    if not organization_id:
        logger.warning(
            "No se publicó el evento CRUD de %s: falta organization_id.",
            module,
        )
        return

    channel_layer = get_channel_layer()

    if channel_layer is None:
        logger.warning("No hay un channel layer configurado.")
        return

    try:
        async_to_sync(channel_layer.group_send)(
            f"chat_org_{organization_id}",
            {
                "type": "crud_event",
                "module": module,
                "action": action,
                "actor_id": actor_id,
            },
        )

    except Exception:
        logger.exception("No se pudo publicar el evento CRUD.")