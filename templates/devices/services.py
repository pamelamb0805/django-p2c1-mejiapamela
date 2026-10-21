import json
from django.conf import settings

def load_json(file_name):
    #valida que el archivo de data sea una lista
    path = settings.BASE_DIR /"data"/ file_name
    with path.open(encoding="urf-8") as file:
        data = json.load(file)
    if not isinstance(data,list):
        raise ValueError(f"{file_name} debe contener una lista.")
    return data

def find_by_id(collection, identifier):
    return next((item for item in collection
                 if item["id"] == identifier, None))

def get_zone_summary(zone_id):
    zone = find_by_id(load_json("zones.json"), zone_id)
    if zone is None:
        return None

    categories = load_json("categoriess.json")
    devices = []
    for item in load_json("devices.json"):
        if item["zone_id"] != zone_id:
            continue
        category =