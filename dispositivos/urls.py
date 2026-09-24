from django.urls import path
from . import views

app_name = "dispositivos"

urlpatterns = [
    path("", views.inicio, name="inicio"),

    path("dispositivos/", views.catalogo, name="catalogo"),

    path("zonas/", views.zonas, name="zonas"),
    
    path("zonas/<int:zona_id>/", views.zona_id, name="zona_id"),

    path("resumen_zonas/", views.resumen_datos, name="resumen _zonas",)
]