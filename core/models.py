from django.db import models

# Create your models here.
#Eva2 verbose_name --> esp
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    verbose_name="Fecha de eliminación")

    class Meta:
        abstract = True

