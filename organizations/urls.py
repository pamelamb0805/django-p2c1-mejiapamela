from django.urls import path
from . import views

app_name = "organizations"

urlpatterns = [
    # URLS CRUD Organozaciones --> preentrega eva 3 - PM
    path('', views.OrganizationListView.as_view(), name='organization_list'),
    path('new/', views.OrganizationCreateView.as_view(), name='organization_create'),
    path('<int:pk>/edit/', views.OrganizationUpdateView.as_view(), name='organization_update'),
    path('<int:pk>/delete/', views.OrganizationDeleteView.as_view(), name='organization_delete'),
    
    # Departamentos o unidades internas de la organización (RF-02) --> actualizacion enlaces preentrega eva 3 - PM
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('departments/new/', views.DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<int:pk>/edit/', views.DepartmentUpdateView.as_view(), name='department_update'),
    path('departments/<int:pk>/delete/', views.DepartmentDeleteView.as_view(), name='department_delete'),
    
    # Zonas físicas de la organización (sala, bodega, oficina) (RF-03)
    # URLS CRUD Zonas físicas (RF-03) --> preentrega eva 3 - PM
    path('zones/', views.ZoneListView.as_view(), name='zone_list'),
    path('zones/new/', views.ZoneCreateView.as_view(), name='zone_create'),
    path('zones/<int:pk>/edit/', views.ZoneUpdateView.as_view(), name='zone_update'),
    path('zones/<int:pk>/delete/', views.ZoneDeleteView.as_view(), name='zone_delete'),
]