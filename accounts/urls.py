from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('registro/', views.registro, name='registro'),

    # CRUD de usuarios y perfiles (M02): listar, crear, editar y eliminar
    path('users/', views.UserProfileListView.as_view(), name='user_list'),
    path('users/new/', views.UserProfileCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/edit/', views.UserProfileUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', views.UserProfileDeleteView.as_view(), name='user_delete'),
]