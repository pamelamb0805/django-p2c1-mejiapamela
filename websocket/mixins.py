from core.models import ActivityLog
from websocket.services import publish_crud_event


class WebSocketCrudEventsMixin:

    crud_module = "registros"
    crud_action = None

    def get_crud_organization_id(self):
        """
        Obtiene la organización propietaria del registro.

        Considera relaciones directas y relaciones mediante
        departamento, zona o dispositivo.
        """

        obj = getattr(self, "object", None)

        if obj is None:
            return None

        # La organización es el propio registro.
        if self.crud_module == "organizaciones":
            return obj.pk

        # Relación directa con organización.
        organization_id = getattr(
            obj,
            "organization_id",
            None
        )

        if organization_id:
            return organization_id

        # Relación mediante zona.
        zone = getattr(obj, "zone", None)

        if zone is not None:
            organization_id = getattr(
                zone,
                "organization_id",
                None
            )

            if organization_id:
                return organization_id

        # Relación mediante departamento.
        department = getattr(obj, "department", None)

        if department is not None:
            organization_id = getattr(
                department,
                "organization_id",
                None
            )

            if organization_id:
                return organization_id

        # Relación mediante dispositivo.
        device = getattr(obj, "device", None)

        if device is not None:
            device_zone = getattr(device, "zone", None)

            if device_zone is not None:
                organization_id = getattr(
                    device_zone,
                    "organization_id",
                    None
                )

                if organization_id:
                    return organization_id

        # Los catálogos y productos globales no tienen organización.
        return None

    def save_crud_activity(self, action=None):
        """
        Guarda una operación CRUD en la bitácora permanente.
        """

        obj = getattr(self, "object", None)

        if obj is None:
            return

        action = (
            action
            or self.crud_action
            or "actualizado"
        )

        user = self.request.user

        organization_id = self.get_crud_organization_id()

        ActivityLog.objects.create(
            actor=user,
            actor_name=(
                user.get_full_name()
                or user.username
            ),
            organization_id=organization_id,
            module=self.crud_module,
            action=action,
            object_type=str(
                obj._meta.verbose_name
            ),
            object_label=str(obj)[:255],
            object_pk=str(obj.pk),
        )

    def publish_crud_notification(self, action=None):
        """
        Guarda la actividad y después publica la notificación WebSocket.
        """

        obj = getattr(self, "object", None)

        if obj is None:
            return

        action = (
            action
            or self.crud_action
            or "actualizado"
        )

        organization_id = self.get_crud_organization_id()

        # 1. Guardar permanentemente la operación.
        self.save_crud_activity(action)

        # 2. Mantener el comportamiento WebSocket existente.
        # Los registros globales no se envían a grupos de organizaciones.
        if organization_id:
            publish_crud_event(
                module=self.crud_module,
                action=action,
                actor_id=self.request.user.pk,
                organization_id=organization_id,
            )

    def form_valid(self, form):
        """
        Registra automáticamente las creaciones y modificaciones
        después de guardar correctamente el formulario.
        """

        action = self.crud_action

        if action is None:
            action = (
                "actualizado"
                if getattr(self, "object", None) is not None
                else "creado"
            )

        response = super().form_valid(form)

        if response.status_code < 400:
            self.publish_crud_notification(action)

        return response