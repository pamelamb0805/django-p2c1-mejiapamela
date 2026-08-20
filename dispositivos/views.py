from django.shortcuts import render

from django.http import HttpResponse
def inicio(request):
    return HttpResponse(
        "<h1>EcoEnergy</h1>"
        "<p>Back End en funcionamiento</p>"
    )

# dispositivos/views.py
def dispositivos_zona(request, zona_id):
    if zona_id != 3:
        return HttpResponse(
        "Zona no encontrada", status=404
        )
    return HttpResponse(
        f"Dispositivos de la zona {zona_id}"
    )

#laboratorio: crear nueva ruta
def zona(request, zona_id):
    if zona_id != 8:
        return HttpResponse(
        "Zona no encontrada", status=200
        )
    return HttpResponse(
        f"zona {zona_id}"
    )

