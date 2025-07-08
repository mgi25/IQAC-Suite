from django.shortcuts import render, get_object_or_404
from .models import Student, Participation, AttributeStrengthMap, Role, CharacterStrength, AcademicYear, School, Course
from collections import defaultdict
from django.http import JsonResponse, HttpResponse
from django.template.loader import get_template, render_to_string
from django.urls import reverse
import qrcode
import io
import weasyprint
import base64
import json
import zipfile
from datetime import date

# ─────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────
def home(request):
    years = AcademicYear.objects.all()
    students = Student.objects.select_related('academic_year', 'course__school').all().order_by('name')

    # Create nested dict: year → school → course → students
    student_data = {}
    for student in students:
        year = str(student.academic_year.year)
        school = student.course.school.name
        course = student.course.name

        student_data.setdefault(year, {}).setdefault(school, {}).setdefault(course, []).append({
            'name': student.name,
            'roll_no': student.roll_no
        })

    return render(request, 'transcript_app/home.html', {
        'years': years,
        'student_data': json.dumps(student_data)
    })

# ─────────────────────────────────────────────
# CHECK IF ROLL NUMBER EXISTS (AJAX)
# ─────────────────────────────────────────────
def validate_roll_no(request):
    roll_no = request.GET.get('roll_no')
    exists = Student.objects.filter(roll_no=roll_no).exists()
    return JsonResponse({'exists': exists})

# ─────────────────────────────────────────────
# STRENGTH CALCULATION
# ─────────────────────────────────────────────
def calculate_strength_data(student):
    participations = Participation.objects.filter(student=student)

    strength_scores = defaultdict(float)
    all_participations = Participation.objects.all()
    student_strength_totals = defaultdict(lambda: defaultdict(float))

    for part in participations:
        role_factor = part.role.factor if part.role else 1.0
        for attr in part.event.attributes.all():
            for map in AttributeStrengthMap.objects.filter(graduate_attribute=attr):
                strength_scores[map.character_strength.name] += map.weight * role_factor

    for part in all_participations:
        role_factor = part.role.factor if part.role else 1.0
        for attr in part.event.attributes.all():
            for map in AttributeStrengthMap.objects.filter(graduate_attribute=attr):
                student_strength_totals[part.student.roll_no][map.character_strength.name] += map.weight * role_factor

    all_strengths = CharacterStrength.objects.order_by('name')
    strength_data = []
    for strength_obj in all_strengths:
        name = strength_obj.name
        score = strength_scores.get(name, 0)
        benchmark = max([student_strength_totals[roll].get(name, 0) for roll in student_strength_totals], default=1)
        percentage = (score / benchmark) * 100 if benchmark > 0 else 0

        if percentage >= 90:
            category = "ESTD"
        elif percentage >= 80:
            category = "DEV"
        elif percentage >= 60:
            category = "EMER"
        else:
            category = None

        strength_data.append({
            'name': name,
            'average': round(score, 2),
            'category': category
        })

    strength_data.sort(key=lambda x: x['name'])
    return strength_data, participations

# ─────────────────────────────────────────────
# TRANSCRIPT VIEW
# ─────────────────────────────────────────────
def transcript_view(request, roll_no):
    student = get_object_or_404(Student, roll_no=roll_no)
    strength_data, participations = calculate_strength_data(student)

    sorted_events = sorted(participations, key=lambda p: len(p.event.attributes.all()), reverse=True)
    top_events = [p.event.name for p in sorted_events[:5]]

    student_list = Student.objects.filter(
        course=student.course,
        academic_year=student.academic_year
    ).exclude(roll_no=student.roll_no).order_by('name')

    qr_b64 = None
    if participations.count() > 5:
        all_events_url = request.build_absolute_uri(
            reverse('transcript:all_events', kwargs={'roll_no': student.roll_no})
        )
        qr = qrcode.make(all_events_url)
        buf = io.BytesIO()
        qr.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render(request, 'transcript_app/transcript.html', {
        'student': student,
        'strength_data': strength_data,
        'today': date.today(),
        'top_events': top_events,
        'qr_code': qr_b64,
        'student_list': student_list
    })

# ─────────────────────────────────────────────
# PDF DOWNLOAD VIEW (Single Transcript)
# ─────────────────────────────────────────────
def transcript_pdf(request, roll_no):
    student = get_object_or_404(Student, roll_no=roll_no)
    strength_data, participations = calculate_strength_data(student)

    sorted_events = sorted(participations, key=lambda p: len(p.event.attributes.all()), reverse=True)
    top_events = [p.event.name for p in sorted_events[:5]]

    qr_b64 = None
    if participations.count() > 5:
        all_events_url = request.build_absolute_uri(
            reverse('transcript:all_events', kwargs={'roll_no': student.roll_no})
        )
        qr = qrcode.make(all_events_url)
        buf = io.BytesIO()
        qr.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    template = get_template('transcript_app/pdf.html')
    html = template.render({
        'student': student,
        'strength_data': strength_data,
        'today': date.today(),
        'top_events': top_events,
        'qr_code': qr_b64
    })

    pdf_file = weasyprint.HTML(string=html).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="transcript_{student.roll_no}.pdf"'
    return response

# ─────────────────────────────────────────────
# ALL EVENTS VIEW
# ─────────────────────────────────────────────
def all_events_view(request, roll_no):
    student = get_object_or_404(Student, roll_no=roll_no)
    participations = Participation.objects.filter(student=student)
    all_event_names = [f"{p.event.name} - {p.event.date}" for p in participations]
    return render(request, 'transcript_app/student_events.html', {
        'student': student,
        'all_events': all_event_names
    })

# ─────────────────────────────────────────────
# BULK DOWNLOAD: Combined PDF of All Course Students
# ─────────────────────────────────────────────
def download_course_pdf_combined(request, roll_no):
    current_student = get_object_or_404(Student, roll_no=roll_no)
    course_students = Student.objects.filter(course=current_student.course, academic_year=current_student.academic_year).order_by('name')

    combined_html = ""
    for student in course_students:
        strength_data, participations = calculate_strength_data(student)
        sorted_events = sorted(participations, key=lambda p: len(p.event.attributes.all()), reverse=True)
        top_events = [p.event.name for p in sorted_events[:5]]

        qr_b64 = None
        if participations.count() > 5:
            all_events_url = request.build_absolute_uri(
                reverse('transcript:all_events', kwargs={'roll_no': student.roll_no})
            )
            qr = qrcode.make(all_events_url)
            buf = io.BytesIO()
            qr.save(buf, format='PNG')
            qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        html = render_to_string('transcript_app/pdf.html', {
            'student': student,
            'strength_data': strength_data,
            'today': date.today(),
            'top_events': top_events,
            'qr_code': qr_b64
        })

        combined_html += f'<div style="page-break-after: always;">{html}</div>'

    pdf_file = weasyprint.HTML(string=combined_html).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Course_Transcripts.pdf"'
    return response

# ─────────────────────────────────────────────
# BULK DOWNLOAD: ZIP of Individual PDFs
# ─────────────────────────────────────────────
def download_course_individual_pdfs(request, roll_no):
    current_student = get_object_or_404(Student, roll_no=roll_no)
    course_students = Student.objects.filter(course=current_student.course, academic_year=current_student.academic_year)

    buffer = io.BytesIO()
    zip_file = zipfile.ZipFile(buffer, 'w')

    for student in course_students:
        strength_data, participations = calculate_strength_data(student)
        sorted_events = sorted(participations, key=lambda p: len(p.event.attributes.all()), reverse=True)
        top_events = [p.event.name for p in sorted_events[:5]]

        qr_b64 = None
        if participations.count() > 5:
            all_events_url = request.build_absolute_uri(
                reverse('transcript:all_events', kwargs={'roll_no': student.roll_no})
            )
            qr = qrcode.make(all_events_url)
            buf = io.BytesIO()
            qr.save(buf, format='PNG')
            qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        html = render_to_string('transcript_app/pdf.html', {
            'student': student,
            'strength_data': strength_data,
            'today': date.today(),
            'top_events': top_events,
            'qr_code': qr_b64
        })

        pdf_buffer = io.BytesIO()
        weasyprint.HTML(string=html).write_pdf(target=pdf_buffer)
        zip_file.writestr(f"{student.roll_no}_{student.name}.pdf", pdf_buffer.getvalue())

    zip_file.close()
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="All_Student_PDFs.zip"'
    return response
