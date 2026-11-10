import re
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.utils import timezone
from django import forms

#correccion eva 3 --> PM --> Validadores Formularios
# Códigos: letras, números, guion, guion bajo y punto; sin espacios (ej.: ORG-001, DEV_12).
CODE_REGEX = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]*")
# Unidades de medida: kWh, kW, %, °C, m³, V, A, etc.
UNIT_REGEX = re.compile(r"[A-Za-z0-9%°/³²µ.\- ]+")


def validate_code(value, min_len=3):
    """Código/identificador: sin espacios ni símbolos raros, mínimo min_len caracteres."""
    value = (value or "").strip()
    if len(value) < min_len:
        raise ValidationError(f"Ingrese al menos {min_len} caracteres.")
    if not CODE_REGEX.fullmatch(value):
        raise ValidationError(
            "Use solo letras, números, guion (-), guion bajo (_) o punto (.), sin espacios."
        )
    return value


def validate_name(value, min_len=3):
    """Nombre: colapsa espacios repetidos, mínimo min_len y al menos una letra."""
    value = " ".join((value or "").split())
    if len(value) < min_len:
        raise ValidationError(f"Ingrese al menos {min_len} caracteres.")
    if not any(c.isalpha() for c in value):
        raise ValidationError("Debe contener al menos una letra.")
    return value


def validate_optional_text(value, min_len=3):
    """Texto opcional: vacío es válido; si viene, debe tener contenido real."""
    value = " ".join((value or "").split())
    if not value:
        return ""
    return validate_name(value, min_len)


def validate_unit(value):
    value = " ".join((value or "").split())
    if not value:
        raise ValidationError("Ingrese la unidad de medida.")
    if not UNIT_REGEX.fullmatch(value) or not any(c.isalpha() or c == "%" for c in value):
        raise ValidationError("Unidad no válida. Ejemplos: kWh, kW, V, A, °C, %.")
    return value


def _check_min_date(value):
    minimo = timezone.make_aware(datetime(2000, 1, 1))
    if value < minimo:
        raise ValidationError("La fecha no puede ser anterior al año 2000.")


def validate_past_datetime(value, tolerance_minutes=5):
    """Hecho ya ocurrido: entre el año 2000 y ahora (con una tolerancia pequeña)."""
    if value is None:
        return value
    _check_min_date(value)
    if value > timezone.now() + timedelta(minutes=tolerance_minutes):
        raise ValidationError("La fecha no puede ser futura.")
    return value


def validate_planned_datetime(value, max_years=5):
    """Fecha planificada: desde el año 2000 hasta max_years años a futuro."""
    if value is None:
        return value
    _check_min_date(value)
    if value > timezone.now() + timedelta(days=365 * max_years):
        raise ValidationError(f"La fecha no puede superar {max_years} años a futuro.")
    return value


#Corrección Eva 3 --> PM --> Validadores Formularios --> limite formularios.
class FormLimitsMixin:
    """
    Establece un máximo de 500 caracteres en los campos
    de texto de los formularios CRUD.
    """

    text_limits = {}
    number_limits = {}
    default_text_limit = 500

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():

            if isinstance(field, forms.CharField):

                limite_configurado = self.text_limits.get(
                    name,
                    field.max_length or self.default_text_limit,
                )

                # Nunca superar los 500 caracteres.
                limit = min(limite_configurado, 500)

                field.max_length = limit
                field.widget.attrs["maxlength"] = limit

                validator = MaxLengthValidator(limit)

                if not any(
                    isinstance(existing, MaxLengthValidator)
                    and existing.limit_value == limit
                    for existing in field.validators
                ):
                    field.validators.append(validator)

        for name, (minimo, maximo) in self.number_limits.items():
            field = self.fields.get(name)

            if field is None:
                continue

            field.widget.attrs["min"] = minimo
            field.widget.attrs["max"] = maximo

            field.validators.append(MinValueValidator(minimo))
            field.validators.append(MaxValueValidator(maximo))
