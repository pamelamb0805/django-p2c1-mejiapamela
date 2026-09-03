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


