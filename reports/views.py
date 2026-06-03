from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from patients.models import Patient
import pandas as pd
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import json

@login_required
def export_patients(request, format):
    patients = Patient.objects.all().values(
        'nombres', 'apellidos', 'documento', 'edad', 'sexo', 
        'imc', 'glucosa', 'presion_sistolica', 'riesgo'
    )
    df = pd.DataFrame(list(patients))

    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="pacientes.csv"'
        df.to_csv(path_or_buf=response, index=False)
        return response

    elif format == 'xlsx':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Pacientes')
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="pacientes.xlsx"'
        return response

    elif format == 'json':
        data = list(patients)
        return JsonResponse(data, safe=False, json_dumps_params={'indent': 4})

    elif format == 'pdf':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph("Reporte General de Pacientes - Keisy Medical", styles['Title']))
        
        # Preparar tabla
        data = [df.columns.tolist()] + df.values.tolist()
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.dodgerblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)
        doc.build(elements)
        
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="pacientes.pdf"'
        return response

    return HttpResponse("Formato no válido", status=400)
