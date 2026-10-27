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

    # CRUD de Categorías (modelo Catalog) ---> preentrega eva3 PM
    path("catalogs/", views.CatalogListView.as_view(), name="catalog_list"),
    path("catalogs/new/", views.CatalogCreateView.as_view(), name="catalog_create"),
    path("catalogs/<int:pk>/edit/", views.CatalogUpdateView.as_view(), name="catalog_update"),
    path("catalogs/<int:pk>/delete/", views.CatalogDeleteView.as_view(), name="catalog_delete"),

    # Rutas de zonas y mantenimiento (clase 6 - PM)
    path("zones/", views.zone_list, name="zone_list"),
    path("zones/<int:pk>/", views.zone_detail, name="zone_detail"),
    path("maintenance/", views.maintenance_list, name="maintenance_list"),

    # CRUD de Mediciones ---> preentrega eva3 PM
    path("measurements/", views.MeasurementListView.as_view(), name="measurement_list"),
    path("measurements/new/", views.MeasurementCreateView.as_view(), name="measurement_create"),
    path("measurements/<int:pk>/edit/", views.MeasurementUpdateView.as_view(), name="measurement_update"),
    path("measurements/<int:pk>/delete/", views.MeasurementDeleteView.as_view(), name="measurement_delete"),

    # CRUD de Alertas (modelo AlertEvent) ---> preentrega eva3 PM
    path("alerts/", views.AlertListView.as_view(), name="alert_list"),
    path("alerts/new/", views.AlertCreateView.as_view(), name="alert_create"),
    path("alerts/<int:pk>/edit/", views.AlertUpdateView.as_view(), name="alert_update"),
    path("alerts/<int:pk>/delete/", views.AlertDeleteView.as_view(), name="alert_delete"),
    
    path("history/", views.history_list, name="history_list"),
]