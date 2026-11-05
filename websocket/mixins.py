
from websocket.services import publish_crud_event


class WebSocketCrudEventsMixin:
    crud_module = "registros"
    crud_action = None

    def get_crud_organization_id(self):
        """
        Obtiene la organización propietaria del registro.

        La organización puede estar relacionada directamente
        o mediante un dispositivo y su zona.
        """
        obj = getattr(self, "object", None)

        if obj is None:
            return None

        # La organización es el propio registro.
        if self.crud_module == "organizaciones":
            return obj.pk

        # Relaciones directas con organización.
        organization_id = getattr(obj, "organization_id", None)

        if organization_id:
            return organization_id

        # Registros relacionados directamente con una zona.
        zone = getattr(obj, "zone", None)

        if zone is not None:
            organization_id = getattr(zone, "organization_id", None)

            if organization_id:
                return organization_id

        # Registros relacionados con un departamento.
        department = getattr(obj, "department", None)

        if department is not None:
            organization_id = getattr(
                department,
                "organization_id",
                None,
            )

            if organization_id:
                return organization_id

        # Mediciones y alertas: dispositivo -> zona -> organización.
        device = getattr(obj, "device", None)

        if device is not None:
            device_zone = getattr(device, "zone", None)

            if device_zone is not None:
                organization_id = getattr(
                    device_zone,
                    "organization_id",
                    None,
                )

                if organization_id:
                    return organization_id

        # Los registros globales, como categorías y productos,
        # no se difunden a todas las organizaciones.
        return None

    def publish_crud_notification(self, action=None):
        obj = getattr(self, "object", None)

        if obj is None:
            return

        publish_crud_event(
            module=self.crud_module,
            action=action or self.crud_action or "actualizado",
            actor_id=self.request.user.pk,
            organization_id=self.get_crud_organization_id(),
        )

    def form_valid(self, form):
        # Identificar la acción antes de guardar.
        action = self.crud_action

        if action is None:
            action = (
                "actualizado"
                if getattr(self, "object", None) is not None
                else "creado"
            )

        response = super().form_valid(form)

        # Publicar después de guardar correctamente.
        if response.status_code < 400:
            self.publish_crud_notification(action)

        return response
