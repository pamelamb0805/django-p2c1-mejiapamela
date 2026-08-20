# dispositivos/urls.py
from django.urls import path
from . import views
app_name = "dispositivos"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path(
    "zonas/<int:zona_id>/dispositivos/",
    views.dispositivos_zona,
    name="por_zona",
    ),
    #crear nueva
    path(
        "zonas/<int:zona_id>/zona/",
        views.zona,
        name="por_zona",
        )
]

