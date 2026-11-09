
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

logger = logging.getLogger(__name__)


def publish_crud_event(
    module,
    action,
    actor_id,
    organization_id=None,
    activity=None,
):
    """
    Publica notificaciones CRUD:
    - A la organización correspondiente.
    - A ROOT, que recibe todos los eventos.
    """

    channel_layer = get_channel_layer()

    if channel_layer is None:
        logger.warning("No hay un channel layer configurado.")
        return

    if activity is None:
        logger.warning("No se recibió el registro de actividad.")
        return

    organization = activity.organization

    payload = {
        "id": activity.pk,
        "module": module,
        "module_display": activity.get_module_display(),
        "action": action,
        "action_display": activity.get_action_display(),
        "actor_id": actor_id,
        "actor_name": activity.actor_name,
        "object_type": activity.object_type,
        "object_label": activity.object_label,
        "object_pk": activity.object_pk,
        "organization_id": organization_id,
        "organization_name": (
            organization.comercial_name
            or organization.legal_name
            if organization else "Global"
        ),
        "created_at": timezone.localtime(
            activity.created_at
        ).strftime("%d/%m/%Y %H:%M"),
    }

    try:
        # 1. Enviar a la organización correspondiente.
        if organization_id:
            async_to_sync(channel_layer.group_send)(
                f"chat_org_{organization_id}",
                {
                    "type": "crud_event",
                    "module": module,
                    "payload": payload,
                    "root_only": False,
                },
            )

        # 2. Enviar todos los eventos a ROOT.
        async_to_sync(channel_layer.group_send)(
            "crud_root",
            {
                "type": "crud_event",
                "module": module,
                "payload": payload,
                "root_only": True,
            },
        )

    except Exception:
        logger.exception("No se pudo publicar el evento CRUD.")
