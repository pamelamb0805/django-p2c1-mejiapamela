
from io import BytesIO
from datetime import datetime

from django.http import HttpResponse
from django.utils import timezone

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter


def export_queryset_excel(
    queryset,
    filename,
    sheet_title="Registros",
    extra_columns=None,
):
    """
    Exporta todos los registros de un queryset a Excel.
    No aplica paginación: exporta todos los resultados filtrados.
    """

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_title[:31]

    model = queryset.model

    fields = [
        field
        for field in model._meta.concrete_fields
        if field.name != "deleted_at"
    ]

    columns = [
        (
            str(field.verbose_name).capitalize(),
            lambda obj, f=field: getattr(obj, f.name),
            field,
        )
        for field in fields
    ]

    if extra_columns:
        for header, getter in extra_columns:
            columns.append((header, getter, None))

    headers = [column[0] for column in columns]
    sheet.append(headers)

    for obj in queryset.iterator():
        row = []

        for header, getter, field in columns:
            value = getter(obj)

            if value is None:
                value = ""

            elif isinstance(value, datetime):
                if timezone.is_aware(value):
                    value = timezone.localtime(value).replace(tzinfo=None)

            elif isinstance(value, bool):
                if field and field.name == "status":
                    value = "Activo" if value else "Inactivo"
                else:
                    value = "Sí" if value else "No"

            elif field and field.is_relation:
                value = str(value)

            elif not isinstance(value, (int, float)):
                value = str(value)

            row.append(value)

        sheet.append(row)

    # Formato del encabezado
    for cell in sheet[1]:
        cell.font = Font(
            bold=True,
            color="FFFFFF"
        )
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="034159"
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    sheet.freeze_panes = "A2"

    if sheet.max_row > 1:
        sheet.auto_filter.ref = sheet.dimensions

    # Ajustar anchos
    for column_cells in sheet.columns:
        max_length = 0
        column_index = column_cells[0].column

        for cell in column_cells:
            if cell.value is not None:
                max_length = max(
                    max_length,
                    len(str(cell.value))
                )

        sheet.column_dimensions[
            get_column_letter(column_index)
        ].width = min(max(max_length + 3, 14), 45)

    # Evitar interpretar textos de la base de datos como fórmulas.
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            if isinstance(cell.value, str):
                cell.data_type = "s"

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}.xlsx"'
    )

    return response
