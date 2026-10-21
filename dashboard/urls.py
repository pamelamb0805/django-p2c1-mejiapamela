from django.urls import path
from . import views
from devices.views import indicators_view

app_name = "dashboard"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('preference/', views.remember_preference, name='remember_preference'),
    path('indicators/', indicators_view, name='indicators'),
]