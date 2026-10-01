from django.contrib import admin
from .models import UserProfile
from .forms import UserProfileAdminForm

# Register your models here.
#creacion perfiles y roles - EVA2 - PM --ppt4

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    #correccion eva2-n3
    form = UserProfileAdminForm
    list_display = ("user", "organization", "department", "employee_code")
    search_fields = ("user__username", "employee_code", "organization__legal_name")
    list_filter = ("organization",)
    list_select_related = ("user", "organization", "department")
    ordering = ("user__username",)

