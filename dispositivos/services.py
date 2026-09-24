import json
from django.conf import settings

import json
from django.conf import settings

def cargar_json(nombre_archivo):
    ruta = settings.BASE_DIR / "data" / nombre_archivo
    
    if not ruta.exists():
        return []

    with ruta.open(encoding="utf-8") as archivo:
        contenido = archivo.read().strip()
        if not contenido:
            return []
        
        try:
            datos = json.loads(contenido)
            return datos if isinstance(datos, list) else []
        except json.JSONDecodeError:
            return []

def cargar_dispositivos():
    return cargar_json("dispositivos.json")

def cargar_zonas():
    return cargar_json("zonas.json")

def cargar_categorias():
    return cargar_json("categorias.json")