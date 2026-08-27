from django.shortcuts import render

from django.http import HttpResponse
from django.shortcuts import render
from .services import cargar_dispositivos

def inicio(request):
    contexto = {
    "sistema": "EcoEnergy",
    "mensaje": "Monitoreo energético responsable",
    "asignatura": "Programación Back End",
    }
    return render(
    request,
    "dispositivos/inicio.html",
    contexto,
    )

# dispositivos/views.py --> usaba hhttp Response
def dispositivos_zona(request, zona_id):
    if zona_id != 3:
        return HttpResponse(
        "Zona no encontrada", status=404
        )
    return HttpResponse(
        f"Dispositivos de la zona {zona_id}"
    )

#laboratorio1: crear nueva ruta --> hhtp response
def zona(request, zona_id):
    if zona_id != 8:
        return HttpResponse(
        "Zona no encontrada", status=200
        )
    return HttpResponse(
        f"zona {zona_id}"
    )

#laboratorio 2: con los def if zona_id usando el template.

#def catalogo
def catalogo(request):
    dispositivos = cargar_dispositivos()
    activos = sum(
        1 for item in dispositivos
        if item["estado"] == "Activo"
    )
    contexto = {
        "dispositivos": dispositivos,
        "total": len(dispositivos),
        "total_activos": activos,
    }
    return render(
        request, "dispositivos/catalogo.html", contexto
    )

