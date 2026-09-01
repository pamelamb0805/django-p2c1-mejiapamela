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
        "zonas/",
        views.zona,
        name="por_zona",
        ),
    # path para que funcione catalogo
    path("dispositivos/", views.catalogo, name="catalogo")
]

#ej: de otra aplicación : reportes