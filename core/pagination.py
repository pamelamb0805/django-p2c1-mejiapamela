#Entrega Eva3 --> PM --> corrección paginador
#ordenamiento de paginadores: más antiguo, más nuevo, alfabético, numérico
PAGE_SIZE_OPTIONS = (5, 10, 15)
DEFAULT_PAGE_SIZE = 10

ORDER_OPTIONS = (
    ("reciente", "Más nuevo a más antiguo"),
    ("antiguo", "Más antiguo a más nuevo"),
    ("alfabetico", "Orden alfabético (A-Z)"),
    ("numerico", "Orden numérico (ID menor a mayor)"),
)


def get_page_size(request, session_key):
    raw = request.GET.get("page_size")

    if raw:
        try:
            selected = int(raw)
        except (TypeError, ValueError):
            selected = None

        if selected in PAGE_SIZE_OPTIONS:
            request.session[session_key] = selected

    saved = request.session.get(session_key, DEFAULT_PAGE_SIZE)
    return saved if saved in PAGE_SIZE_OPTIONS else DEFAULT_PAGE_SIZE


def get_order_option(request):
    selected = request.GET.get("orden", "reciente")
    valid_options = {value for value, label in ORDER_OPTIONS}
    return selected if selected in valid_options else "reciente"


class PageSizeMixin:
    page_size_session_key = "page_size"

    def get_paginate_by(self, queryset):
        return get_page_size(self.request, self.page_size_session_key)

    def apply_ordering(self, queryset, alphabetical_field):
        """
        Ordena el queryset según el parámetro GET 'orden'.
        El orden predeterminado es por fecha de creación descendente.
        """
        orden = get_order_option(self.request)

        if orden == "antiguo":
            return queryset.order_by("created_at", "pk")

        if orden == "alfabetico":
            return queryset.order_by(alphabetical_field, "pk")

        if orden == "numerico":
            return queryset.order_by("pk")

        return queryset.order_by("-created_at", "-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_size"] = get_page_size(
            self.request,
            self.page_size_session_key,
        )
        context["page_size_options"] = PAGE_SIZE_OPTIONS
        context["orden_seleccionado"] = get_order_option(self.request)
        context["orden_options"] = ORDER_OPTIONS

        return context
