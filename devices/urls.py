#	Ruta de la lista de dispositivos
#correccion eva2-n3
from django.urls import path

from . import views

app_name = "devices"

urlpatterns = [
    path("", views.device_list, name="device_list"),
    path("zones/", views.zone_list, name="zone_list"),
    path("zones/<int:zone_id>/", views.zone_detail, name="zone_detail"),
    path("maintenance/", views.maintenance_list, name="maintenance_list"), 
]