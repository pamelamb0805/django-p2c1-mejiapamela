from django.urls import path
from . import views

app_name = "organizations"

urlpatterns = [
    # URLS CRUD Organozaciones --> preentrega eva 3 - PM
    path('', views.OrganizationListView.as_view(), name='organization_list'),
    path('new/', views.OrganizationCreateView.as_view(), name='organization_create'),
    path('<int:pk>/edit/', views.OrganizationUpdateView.as_view(), name='organization_update'),
    path('<int:pk>/delete/', views.OrganizationDeleteView.as_view(), name='organization_delete'),
    
    # Departamentos o unidades internas de la organización (RF-02)
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    
    # Zonas físicas de la organización (sala, bodega, oficina) (RF-03)
    path('zones/', views.zone_list, name='zone_list'),
    path('zones/create/', views.zone_create, name='zone_create'),
]