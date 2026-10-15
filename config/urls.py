from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.urls

#?? flujo paso 1 ppt1 u2

urlpatterns = [
    path('admin/', admin.site.urls),
    #U3 PPT-6 -Autenticacion sesion -PM 
    #path logig, logout, u otras por agregar. (Rutas por defecto)
    #ruta por defecto accounts
    path("accounts/", include("django.contrib.auth.urls")),
    path("devices/", include("devices.urls")),
    path("organization/", include("organization.urls")),
    path("login/", include("login.urls")),
    path("recover_password/", include("recover.urls")),
    path("dashboard/", include("dashboard.urls"))
]



