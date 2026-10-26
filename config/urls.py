from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core.views import home_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    # Cambiado 'accounts-custom/' por 'accounts/'
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('devices/', include('devices.urls')),
    path('organizations/', include('organizations.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('chat/', include('websocket.urls')),
]


# Linea que le dice a Django que cuando una vista lance PermissionDenied use la vista creada en core/views.py
# Clase 7 - Alexander
handler403 = "core.views.permission_denied_view"
