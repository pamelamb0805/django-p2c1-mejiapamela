from django.urls import path
from . import views

app_name = "dashboard"

url_patterns = [
    path("",views.dashboard, name = "dashboard"),
    path("preference/", views.remember_preference, name="remember_preference")
]