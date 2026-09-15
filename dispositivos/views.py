from django.shortcuts import render

from django.http import HttpResponse, Http404
from django.shortcuts import render
from .services import (cargar_dispositivos, cargar_categorias, cargar_zonas, obtener_zona, obtener_dispositivos_zona,calcular_resumen_zona,contar_dispositivos_zona)

def inicio(request):
    contexto = {
    "sistema": "EcoEnergy",
    "mensaje": "Monitoreo energetico responsable",
    "asignatura": "Programacion Back End",
    }
    return render(
    request,
    "dispositivos/inicio.html",
    contexto,
    )

# dispositivos/views.py --> usaba http Response
def dispositivos_zona(request, zona_id):
    if zona_id != 3:
        return HttpResponse(
        "Zona no encontrada", status=404
        )
    return HttpResponse(
        f"Dispositivos 7mde la zona {zona_id}"
    )

#EVA1
def zonas_listado(request):
    zonas = cargar_zonas()
    zonas_conteo = []
    for zona in zonas:
        zona_info = dict(zona)
        zona_info["cantidad_dispositivos"] = contar_dispositivos_zona(zona["id"])
        zonas_conteo.append(zona_info)

    contexto = {
        "zonas": zonas_conteo
    }
    return render(request, "dispositivos/zonas_listado.html", contexto)

def catalogo(request):
    dispositivos = cargar_dispositivos()
    contexto = {"dispositivos": dispositivos}
    return render(request, "dispositivos/catalogo.html", contexto)

def zonas_detalle(request, zona_id):
    zona = obtener_zona(zona_id)
    if zona is None:
        raise Http404("Zona no encontrada")

    dispositivos = obtener_dispositivos_zona(zona_id)
    resumen = calcular_resumen_zona(zona, dispositivos)

    contexto = {
        "zona": zona,
        "dispositivos": dispositivos,
        "consumo_total": resumen["consumo_total"],
        "estado": resumen["estado"],
    }
    return render(request, "dispositivos/zonas_detalle.html", contexto)


#Resumen consumo por zona
def resumen_zonas(request, zona_id):
    zona = obtener_zona(zona_id)
    if zona is None:
        raise Http404("Resumen de zona no encontrado")

    dispositivos = obtener_dispositivos_zona(zona_id)
    resumen_zonas = calcular_resumen_consumo_zona(zona, dispositivos)

    contexto = {
        "id" : id,
        "zona": zona,
        "dispositivos": dispositivos,
        "dispositivos_total" : contar_dispositivos_zona,
        "consumo_total": resumen["consumo_total"],
        "estado": resumen["estado"],
    }
    return render(request, "dispositivos/resumen_zonas.html", contexto)

