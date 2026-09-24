from django.shortcuts import render
from django.http import HttpResponse
from .services import cargar_dispositivos, cargar_zonas, cargar_categorias

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

def zonas(request):

    zonas = cargar_zonas()
    dispositivos = cargar_dispositivos()

    for zona in zonas:
        dispositivos_de_zona = []
        total_dispositivos = 0

        for dispositivo in dispositivos:
            if dispositivo.get("zona_id") == zona["id"]:
                dispositivos_de_zona.append(dispositivo)
                total_dispositivos += 1
        zona["dispositivos"] = dispositivos_de_zona
        zona["total_dispositivos"] = total_dispositivos
    
    contexto = {
        "zonas": zonas,
        "total": len(zonas)
    }

    return render(request, "dispositivos/zona.html", contexto)

def zonas(request):
    zonas = cargar_zonas()
    dispositivos = cargar_dispositivos()

    for zona in zonas:
        dispositivos_de_zona = []
        total_dispositivos = 0

        for dispositivo in dispositivos:
            if dispositivo.get("zona_id") == zona["id"]:
                dispositivos_de_zona.append(dispositivo)
                total_dispositivos += 1
        zona["dispositivos"] = dispositivos_de_zona
        zona["total_dispositivos"] = total_dispositivos
    
    contexto = {
        "zonas": zonas,
        "total": len(zonas)
    }

    return render(request, "dispositivos/zona.html", contexto)

def zona_id(request, zona_id):
    zonas = cargar_zonas()
    dispositivos = cargar_dispositivos()
    categorias = cargar_categorias()

    zona_encontrada = None

    for zona in zonas:
        if zona["id"] == zona_id:
            zona_encontrada = zona

    if zona_encontrada is None:
        return HttpResponse("Zona no encontrada", status=404)

    categorias_zona = []
    consumo_total = 0

    for categoria in categorias:
        dispositivos_categoria = []

        for dispositivo in dispositivos:

            if dispositivo["zona_id"] == zona_id:
                if dispositivo["categoria_id"] == categoria["id"]:
                    dispositivos_categoria.append(dispositivo)
                    consumo_total = consumo_total + dispositivo["consumo_kwh"]

        if len(dispositivos_categoria) > 0:
            categoria["dispositivos"] = dispositivos_categoria
            categorias_zona.append(categoria)

    total_dispositivos = 0

    for categoria in categorias_zona:
        total_dispositivos = total_dispositivos + len(categoria["dispositivos"])

    if consumo_total > zona_encontrada["limite_kwh"]:
        estado = "ALERTA"
    else:
        estado = "NORMAL"

    zona_encontrada["categorias"] = categorias_zona
    zona_encontrada["total_dispositivos"] = total_dispositivos
    zona_encontrada["consumo_total"] = consumo_total
    zona_encontrada["estado"] = estado

    contexto = {
        "zona": zona_encontrada
    }

    return render(request, f"dispositivos/zona_{zona_id}.html", contexto)

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


def resumen_datos(request):
    zonas = cargar_zonas()
    dispositivos = cargar_dispositivos()

    zonas_totales = len(zonas)
    dispositivos_totales = len(dispositivos)

    for zona in zonas:
        dispositivos_de_zona = []
        consumo_total = 0

        for dispositivo in dispositivos:
            if dispositivo.get("zona_id") == zona["id"]:
                dispositivos_de_zona.append(dispositivo)
                consumo_total += dispositivo.get("consumo_kwh", 0)

        if consumo_total > zona.get("limite_kwh", 0):
            estado = "ALERTA"
        else:
            estado = "Normal"

        zona["dispositivos"] = dispositivos_de_zona
        zona["total_dispositivos"] = len(dispositivos_de_zona)
        zona["consumo_total"] = consumo_total
        zona["estado"] = estado

    contexto = {
        "zonas": zonas,  
        "zonas_totales": zonas_totales,
        "dispositivos_totales": dispositivos_totales,
    }

    return render(request, "dispositivos/resumen_zonas.html", contexto)
    


        