from django.urls import path
from . import views

app_name = "organizations"

urlpatterns = [
    # Listado de organizaciones (para el Administrador de plataforma)
    path('', views.organization_list, name='organization_list'),
    
    # Detalle, creación y actualización de organizaciones (RF-01)
    path('create/', views.organization_create, name='organization_create'),
    path('<int:pk>/', views.organization_detail, name='organization_detail'),
    path('<int:pk>/update/', views.organization_update, name='organization_update'),
    
    # Departamentos o unidades internas de la organización (RF-02)
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    
    # Zonas físicas de la organización (sala, bodega, oficina) (RF-03)
    path('zones/', views.zone_list, name='zone_list'),
    path('zones/create/', views.zone_create, name='zone_create'),
]