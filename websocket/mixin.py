#eva3 --> Implementación Websocket --> PM

from .services import publish_crud_event


class WebSocketCrudEventsMixin:
    """
    Publica eventos después de crear, editar o eliminar
    un registro mediante una vista genérica de Django.
    """

    crud_module = "registros"

    def form_valid(self, form):
        # En UpdateView, el objeto ya está cargado.
        # En CreateView, todavía no existe.
        action = (
            "actualizado"
            if getattr(self, "object", None) is not None
            else "creado"
        )

        response = super().form_valid(form)

        if response.status_code < 400:
            publish_crud_event(
                module=self.crud_module,
                action=action,
                actor_id=self.request.user.pk,
            )

        return response

    def delete(self, request, *args, **kwargs):
        # Conservar el módulo antes de eliminar el registro.
        self.object = self.get_object()

        response = super().delete(request, *args, **kwargs)

        if response.status_code < 400:
            publish_crud_event(
                module=self.crud_module,
                action="eliminado",
                actor_id=request.user.pk,
            )

        return response
