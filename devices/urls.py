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
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/new/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),

    # CRUD de Productos (modelo Product) ---> preentrega eva3 PM
        path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/new/", views.ProductCreateView.as_view(), name="product_create"),
    path("products/<int:pk>/edit/", views.ProductUpdateView.as_view(), name="product_update"),
    path("products/<int:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),
    
    # Rutas de zonas y mantenimiento (clase 6 - PM)
    path("zones/", views.zone_list, name="zone_list"),
    path("zones/<int:pk>/", views.zone_detail, name="zone_detail"),

    # CRUD de Mantenimiento (modelo MaintenanceRequest) ---> preentrega eva3 PM
    path("maintenance/", views.MaintenanceListView.as_view(), name="maintenance_list"),
    path("maintenance/new/", views.MaintenanceCreateView.as_view(), name="maintenance_create"),
    path("maintenance/<int:pk>/edit/", views.MaintenanceUpdateView.as_view(), name="maintenance_update"),
    path("maintenance/<int:pk>/delete/", views.MaintenanceDeleteView.as_view(), name="maintenance_delete"),

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