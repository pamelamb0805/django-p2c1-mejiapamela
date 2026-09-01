asgiref==3.12.1
Django==6.1
sqlparse==0.6.0
tzdata==2026.3

# EcoEnergy - Backend with Django

## Description and Objective
This project is developed with Python and Django.  
Its main objective is to build the backend foundation for EcoEnergy, focusing on structured development and scalability.

## Prerequisites
- Python 3.x installed
- Git installed
- Django (version defined in `requirements.txt`)

## Repository Cloning
```bash
git clone https://github.com/pamelamb0805/django-p2c1-mejiapamela
cd django-p2c1-mejiapamela

python -m venv .venv
# Activate environment
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows

pip install -r requirements.txt

python manage.py migrate
python manage.py runserver


-------------------------------
EVA 1- parte 1
-------------------------------
- Se utilizo la IA Claude, para el análisis de instrucciones: para evaluar que archivo debe ser modificado, o analisis de instrucciones iniciales.
- Se creo archivos zonas.json y categorias.json
- Registros .json:
    - Se creo 8 registros para dispositivos.json, para atributos "nombre" y "consumo" apoyados con un promt de IA(Copilot).
    - Se creo 3 registros para categorias.json, para atributos "nombre" y "descripcion" apoyados con un promt de IA(Copilot).
    - Se creo 3 registros para categorias.json, para atributo "limite_kwh" apoyados con un promt de IA(Copilot).
-1ra subida a github -actualización archivos .json, n°4--