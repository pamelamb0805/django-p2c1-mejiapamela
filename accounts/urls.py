from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Registro
    path(
        'registro/',
        views.registro,
        name='registro'
    ),

    # Recuperación de contraseña (viene de eva3_dashboard)
    path(
        'recuperar-password/',
        views.recuperar_password,
        name='recuperar_password'
    ),
    path(
        'verificar-codigo-reset/',
        views.verificar_codigo_reset,
        name='verificar_codigo_reset'
    ),
    path(
        'confirmar-password-reset/',
        views.confirmar_password_reset,
        name='confirmar_password_reset'
    ),

    # Perfil de usuario con foto (Clase 9) --> PM: ruta /accounts/perfil/
    path(
        'perfil/',
        views.perfil,
        name='perfil'
    ),
    # Editar mi perfil (datos, foto con Croppr y contraseña) --> PM (viene de main)
    path(
        'perfil/editar/',
        views.perfil_editar,
        name='perfil_editar'
    ),

    # CRUD de usuarios y perfiles
    path(
        'users/',
        views.UserProfileListView.as_view(),
        name='user_list'
    ),
    path(
        'users/new/',
        views.UserProfileCreateView.as_view(),
        name='user_create'
    ),
    path(
        'users/<int:pk>/edit/',
        views.UserProfileUpdateView.as_view(),
        name='user_update'
    ),
    path(
        'users/<int:pk>/delete/',
        views.UserProfileDeleteView.as_view(),
        name='user_delete'
    ),
]