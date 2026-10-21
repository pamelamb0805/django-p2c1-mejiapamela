from django.urls import path

from . import views

app_name = "devices"

# Rutas del CRUD de dispositivos: listar, crear, editar y eliminar.
# Clase 8 - Alexander
urlpatterns = [
    path("", views.DeviceListView.as_view(), name="device_list"),
    path("new/", views.DeviceCreateView.as_view(), name="device_create"),
    path("<int:pk>/", views.device_detail, name="device_detail"),
    path("<int:pk>/edit/", views.DeviceUpdateView.as_view(), name="device_update"),
    path("<int:pk>/delete/", views.DeviceDeleteView.as_view(), name="device_delete"),

    # Rutas de zonas y mantenimiento (clase 6 - compañera)
    path("zones/", views.zone_list, name="zone_list"),
    path("zones/<int:pk>/", views.zone_detail, name="zone_detail"),
    path("maintenance/", views.maintenance_list, name="maintenance_list"),
]
