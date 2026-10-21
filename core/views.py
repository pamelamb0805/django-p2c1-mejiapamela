from django.shortcuts import render


def home_view(request):
    """Vista para la página de inicio que usa el home.html global de la estructura."""
    return render(request, 'home.html')


# Creación vista que muestra la página 403 personalizada, con status HTTP 403.
# Clase 7 - Alexander
def permission_denied_view(request, exception=None):
    return render(request, "403.html", status=403)
