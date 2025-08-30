from django.shortcuts import render, get_object_or_404
from .models import Student, Participation, AttributeStrengthMap, Role, CharacterStrength, AcademicYear, School, Course
from collections import defaultdict
from django.http import JsonResponse, HttpResponse, Http404
from django.template.loader import get_template, render_to_string
from django.urls import reverse
import qrcode
import io
from xhtml2pdf import pisa
import base64
import json
import zipfile
from datetime import date
from urllib.parse import unquote
from django.db.models import Prefetch, Prefetch, Q, F

# ─────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────
def home(request):
    years = AcademicYear.objects.all().order_by('year')
    
    # DEBUG: Print what we're sending to template
    print("=== DEBUG: Years being sent to template ===")
    for year in years:
        print(f"Year: {year.year}")
    print("=== END DEBUG ===")
    
    students = Student.objects.select_related('academic_year', 'course__school').all().order_by('name')
    
    student_data = {}
    for student in students:
        # Add safety checks to prevent errors
        if student.academic_year and student.course and student.course.school:
            year = str(student.academic_year.year)
            school = student.course.school.name
            course = student.course.name
            
            student_data.setdefault(year, {}).setdefault(school, {}).setdefault(course, []).append({
                'name': student.name,
                'roll_no': student.roll_no
            })
    
    # DEBUG: Print student data structure
    print("=== DEBUG: Student data keys ===")
    print(f"Years in student_data: {list(student_data.keys())}")
    for year_key, schools in student_data.items():
        print(f"  {year_key}: {list(schools.keys())}")
    print("=== END DEBUG ===")
    
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
    participations = Participation.objects.select_related('role', 'event').prefetch_related('event__attributes').filter(student=student)

    strength_scores = defaultdict(float)
    student_strength_totals = defaultdict(lambda: defaultdict(float))

    attribute_strength_map = AttributeStrengthMap.objects.select_related('graduate_attribute', 'character_strength')
    attr_map = defaultdict(list)
    for asm in attribute_strength_map:
        attr_map[asm.graduate_attribute_id].append((asm.character_strength.name, asm.weight))

    all_participations = Participation.objects.select_related('student', 'role', 'event').prefetch_related('event__attributes')

    for part in participations:
        role_factor = part.role.factor if part.role else 1.0
        for attr in part.event.attributes.all():
            for strength_name, weight in attr_map[attr.id]:
                strength_scores[strength_name] += weight * role_factor

    for part in all_participations:
        role_factor = part.role.factor if part.role else 1.0
        for attr in part.event.attributes.all():
            for strength_name, weight in attr_map[attr.id]:
                student_strength_totals[part.student.roll_no][strength_name] += weight * role_factor

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

    # Prepare top 5 strengths based on average score for sidebar (non-destructive)
    strength_scores_for_sidebar = []
    for s in strength_data:
        if s['average'] > 0:
            strength_scores_for_sidebar.append({
                'name': s['name'],
                'score': s['average']
            })

    # Sort by score descending and pick top 5
    top_5_strengths = sorted(strength_scores_for_sidebar, key=lambda x: x['score'], reverse=True)[:5]

    # Normalize scores to percentage (optional, you can skip if score is already percentage)
    max_score = max([s['score'] for s in top_5_strengths], default=1)
    for s in top_5_strengths:
        s['score'] = round((s['score'] / max_score) * 100, 2) if max_score > 0 else 0

    sorted_events = sorted(participations, key=lambda p: len(p.event.attributes.all()), reverse=True)
    top_events = [(p.event.name, p.role.name if p.role else "Participant") for p in sorted_events[:5]]


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
        'strength_data': strength_data,  # Unmodified
        'top_5_strengths': top_5_strengths,  # Added
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
    top_events = [(p.event.name, p.role.name if p.role else "Participant") for p in sorted_events[:5]]


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
    response['Content-Disposition'] = f'attachment; filename="transcript_{student.roll_no}.pdf"'
    return response

# ─────────────────────────────────────────────
# ALL EVENTS VIEW
# ─────────────────────────────────────────────
def all_events_view(request, roll_no):
    student = get_object_or_404(Student, roll_no=roll_no)
    participations = Participation.objects.filter(student=student)

    # Create a clean list of events with role and date.
    all_event_data = []
    for p in participations:
        all_event_data.append({
            'name': p.event.name,
            'date': p.event.date.strftime("%d %b %Y"),  # Optional: format date like "15 Jul 2025"
            'role': p.role.name if p.role else 'Participant'
        })

    # Strength calculations (same as transcript).
    strength_data, _ = calculate_strength_data(student)

    # Top five strengths for sidebar.
    top_5_strengths = [
        {'name': s['name'], 'score': s['average']}
        for s in strength_data if s['average'] > 0
    ]
    top_5_strengths = sorted(top_5_strengths, key=lambda x: x['score'], reverse=True)[:5]

    max_score = max([s['score'] for s in top_5_strengths], default=1)
    for s in top_5_strengths:
        s['score'] = round((s['score'] / max_score) * 100, 2) if max_score > 0 else 0

    return render(request, 'transcript_app/student_events.html', {
        'student': student,
        'all_events': all_event_data,  # Updated
        'strength_data': strength_data,
        'top_5_strengths': top_5_strengths
    })


# ─────────────────────────────────────────────
# BULK DOWNLOAD HANDLER (PDF or ZIP via ?type=pdf|zip)
# ─────────────────────────────────────────────
def bulk_download_handler(request):
    year = request.GET.get('year')
    school = unquote(request.GET.get('school', ''))
    course = unquote(request.GET.get('course', ''))
    download_type = request.GET.get('type', 'pdf')

    students = Student.objects.filter(
        academic_year__year=year,
        course__name=course,
        course__school__name=school
    ).order_by('name')

    if not students.exists():
        raise Http404("No students found")

    if download_type == 'zip':
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zip_file:
            for student in students:
                strength_data, participations = calculate_strength_data(student)
                sorted_events = sorted(participations, key=lambda p: len(p.event.attributes.all()), reverse=True)
                top_events = [(p.event.name, p.role.name if p.role else "Participant") for p in sorted_events[:5]]


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

        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="All_Student_PDFs.zip"'

        return response

    else:
        combined_html = ""
        for student in students:
            strength_data, participations = calculate_strength_data(student)
            sorted_events = sorted(participations, key=lambda p: len(p.event.attributes.all()), reverse=True)
            top_events = [(p.event.name, p.role.name if p.role else "Participant") for p in sorted_events[:5]]


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

        pdf_buffer = io.BytesIO()
        pisa.CreatePDF(combined_html, dest=pdf_buffer)
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Course_Transcripts.pdf"'

        return response