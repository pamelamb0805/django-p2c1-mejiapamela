from websocket.services import publish_crud_event


class WebSocketCrudEventsMixin:
    crud_module = "registros"
    crud_action = None

    def get_crud_organization_id(self):
        """
        Obtiene la organización asociada al objeto.
        Contempla registros con organización directa o mediante
        zona/departamento.
        """
        obj = getattr(self, "object", None)

        if obj is None:
            return None

        # Organización: el propio objeto representa la organización.
        if self.crud_module == "organizaciones":
            return obj.pk

        # Departamento, zona u otros modelos con FK organization.
        organization_id = getattr(obj, "organization_id", None)

        if organization_id:
            return organization_id

        # Dispositivos u otros registros vinculados mediante zona.
        zone = getattr(obj, "zone", None)
        if zone and getattr(zone, "organization_id", None):
            return zone.organization_id

        # Registros vinculados mediante departamento.
        department = getattr(obj, "department", None)
        if department and getattr(department, "organization_id", None):
            return department.organization_id

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
        # En CreateView self.object todavía es None antes de guardar.
        # En UpdateView ya contiene el objeto que se está modificando.
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