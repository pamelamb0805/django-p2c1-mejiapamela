from django.contrib import admin
from .models import UserProfile

# Register your models here.
#creacion perfiles y roles - EVA2 - PM --ppt4

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "department", "employee_code")
    search_fields = ("user__username", "employee_code", "organization__legal_name")
    list_filter = ("organization",)
    list_select_related = ("user", "organization", "department")
    ordering = ("user__username",)