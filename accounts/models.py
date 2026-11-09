from django.conf import settings
from django.db import models
from core.models import BaseModel
from django.core.exceptions import ValidationError
from django.utils import timezone

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
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)

    # Perfil de usuario con foto (Clase 9: archivos e imágenes) --> PM
    # avatar (ImageField): foto de perfil. En la BD se guarda solo la ruta relativa; el archivo queda en MEDIA_ROOT.
    # upload_to ordena las fotos por año y mes. blank=True porque la foto es opcional (los perfiles ya creados no se rompen).
    avatar = models.ImageField(
        upload_to="accounts/avatars/%Y/%m/",
        blank=True,
        verbose_name="Foto de perfil",
        help_text="Formato de imagen (JPG, PNG, WEBP). Máximo 2 MB.",
    )

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

#EVA3 -- Recuperar contrasenia --> PM
class PasswordResetCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_codes"
    )
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Código de recuperación"
        verbose_name_plural = "Códigos de recuperación"

    def __str__(self):
        return f"Código de recuperación de {self.user}"
