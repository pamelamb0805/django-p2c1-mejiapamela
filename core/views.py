#creacion vista que muestra la página 403 personalizada, con status HTTP 403.
#Clase 7 -Alexander
from django.shortcuts import render


def permission_denied_view(request, exception=None):
    return render(request, "403.html", status=403)