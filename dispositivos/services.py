import json
from django.conf import settings
def cargar_dispositivos():
    ruta = settings.BASE_DIR / "data" / "dispositivos.json"
    with ruta.open(encoding="utf-8") as archivo:
        datos = json.load(archivo)
    if not isinstance(datos, list):
        raise ValueError("Se esperaba una lista de dispositivos")
    return datos

def cargar_categorias():
    ruta = settings.BASE_DIR / "data" / "categorias.json"
    with ruta.open(encoding="utf-8") as archivo:
        datos = json.load(archivo)
    if not isinstance(datos, list):
        raise ValueError("Se esperaba una lista de categorias")
    return datos

def cargar_zonas():
    ruta = settings.BASE_DIR / "data" / "zonas.json"
    with ruta.open(encoding="utf-8") as archivo:
        datos = json.load(archivo)
    if not isinstance(datos, list):
        raise ValueError("Se esperaba una lista de zonas")
    return datos

def obtener_zona(zona_id):
    zonas = cargar_zonas()
    for zona in zonas:
        if zona["id"] == zona_id:
            return zona
    return None

def obtener_dispositivos_zona(zona_id):
    dispositivos = cargar_dispositivos()
    categorias = cargar_categorias()

    dispositivos_zona = [d for d in dispositivos if d["zona_id"] == zona_id]

    resultado = []
    for disp in dispositivos_zona:
        categoria = next(
            (c for c in categorias if c["id"] == disp["categoria_id"]),
            None
        )
        disp_con_categoria = dict(disp)
        disp_con_categoria["categoria_nombre"] = categoria["nombre"] if categoria else "Sin categoria"
        resultado.append(disp_con_categoria)

    return resultado

def calcular_resumen_zona(zona, dispositivos_de_zona):
    consumo_total = sum(d["consumo_kwh"] for d in dispositivos_de_zona)
    estado = "LIMITE SUPERADO" if consumo_total > zona["limite_kwh"] else "DENTRO DEL LIMITE"
    return {
        "consumo_total": consumo_total,
        "estado": estado,
    }

def contar_dispositivos_zona(zona_id):
    dispositivos = cargar_dispositivos()
    return len([d for d in dispositivos if d["zona_id"] == zona_id])

