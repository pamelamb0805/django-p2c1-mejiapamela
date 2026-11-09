from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de actualización"
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de eliminación"
    )

    class Meta:
        abstract = True


class ActivityLog(models.Model):
    """
    Bitácora permanente de las operaciones realizadas
    en los CRUD y mantenedores de EcoEnergy.
    """

    MODULE_CHOICES = [
        ("organizaciones", "Organizaciones"),
        ("departamentos", "Departamentos"),
        ("zonas", "Zonas"),
        ("usuarios", "Usuarios y perfiles"),
        ("categorias", "Categorías"),
        ("catalogos", "Catálogos"),
        ("productos", "Productos"),
        ("dispositivos", "Dispositivos"),
        ("mediciones", "Mediciones"),
        ("alertas", "Alertas"),
        ("mantenimiento", "Mantenimiento"),
    ]

    ACTION_CHOICES = [
        ("creado", "Creación"),
        ("actualizado", "Modificación"),
        ("eliminado", "Eliminación"),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
        verbose_name="Usuario responsable"
    )

    actor_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        verbose_name="Nombre del responsable"
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
        verbose_name="Organización"
    )

    module = models.CharField(
        max_length=40,
        choices=MODULE_CHOICES,
        verbose_name="Módulo"
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name="Acción"
    )

    object_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Tipo de registro"
    )

    object_label = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Registro afectado"
    )

    object_pk = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="Identificador del registro"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de operación"
    )

    class Meta:
        verbose_name = "Registro de actividad"
        verbose_name_plural = "Registros de actividad"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.get_action_display()} - "
            f"{self.get_module_display()} - "
            f"{self.object_label}"
        )