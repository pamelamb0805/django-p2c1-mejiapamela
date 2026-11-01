#eva3 --> Implementación Websocket --> PM
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def publish_crud_event(module, action, actor_id):
    """
    Publica un evento genérico cuando un CRUD termina correctamente.

    No envía datos personales ni el contenido de los formularios.
    """
    channel_layer = get_channel_layer()

    if channel_layer is None:
        logger.warning("No hay un channel layer configurado.")
        return

    try:
        async_to_sync(channel_layer.group_send)(
            "crud_updates",
            {
                "type": "crud.event",
                "module": module,
                "action": action,
                "actor_id": actor_id,
            },
        )
    except Exception:
        # Un fallo de notificación no debe impedir guardar
        # o eliminar registros correctamente.
        logger.exception("No se pudo publicar el evento CRUD.")
