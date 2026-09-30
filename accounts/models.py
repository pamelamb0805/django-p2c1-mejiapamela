
from django.conf import settings
from django.db import models
from core.models import BaseModel
from django.core.exceptions import ValidationError

# Create your models here.
# accounts/models.py
#creacion perfiles y roles - EVA2 - PM --ppt4
class UserProfile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="user_profiles",
    )
    department = models.ForeignKey(
        "organizations.Department",
        on_delete=models.PROTECT,
        related_name="user_profiles",
        null=True,
        blank=True,
    )
    employee_code = models.CharField(max_length=30, unique=True)
    phone = models.CharField(max_length=20, blank=True)

        # ... campos anteriores ...
        #clean (ppt4) ---> valida pertenencia entre organizacion --> departamento
    def clean(self):
        super().clean()
        if (
            self.department_id
            and self.department.organization_id
            != self.organization_id
        ):
            raise ValidationError({
            "department": (
                "El departamento debe pertenecer "
                "a la organización seleccionada."
            )
        })

    def __str__(self):
        return f"{self.user.username} · {self.organization}"

