from django.shortcuts import render, get_object_or_404
from .models import Student, Participation, AttributeStrengthMap, Role, CharacterStrength
from collections import defaultdict
from datetime import date
from django.http import HttpResponse
from django.template.loader import get_template
from django.urls import reverse
import qrcode
import io
import weasyprint
import base64

def home(request):
    return render(request, 'transcript_app/home.html')

def transcript_view(request):
    roll_no = request.GET.get('roll_no')
    if not roll_no:
        return HttpResponse("Roll number not provided", status=400)
    student = get_object_or_404(Student, roll_no=roll_no)
    participations = Participation.objects.filter(student=student)

    strength_scores = defaultdict(float)
    benchmark_scores = defaultdict(float)

    for part in participations:
        role_factor = part.role.factor if part.role else 1.0
        for attr in part.event.attributes.all():
            mappings = AttributeStrengthMap.objects.filter(graduate_attribute=attr)
            for map in mappings:
                weighted_score = map.weight * role_factor
                strength_scores[map.character_strength.name] += weighted_score

    all_participations = Participation.objects.all()
    student_strength_totals = defaultdict(lambda: defaultdict(float))

    for part in all_participations:
        role_factor = part.role.factor if part.role else 1.0
        for attr in part.event.attributes.all():
            mappings = AttributeStrengthMap.objects.filter(graduate_attribute=attr)
            for map in mappings:
                student_strength_totals[part.student.roll_no][map.character_strength.name] += map.weight * role_factor

    strength_data = []
    all_strengths = CharacterStrength.objects.order_by('name')
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

    sorted_events = sorted(participations, key=lambda p: len(p.event.attributes.all()), reverse=True)
    top_events = [p.event.name for p in sorted_events[:5]]

    qr_b64 = None
    if participations.count() > 5:
        scheme = 'https' if request.is_secure() else 'http'
        base_url = f"{scheme}://{request.get_host()}"
        all_events_url = base_url + reverse('transcript:all_events', kwargs={'roll_no': student.roll_no})
        qr = qrcode.make(all_events_url)
        buf = io.BytesIO()
        qr.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render(request, 'transcript_app/transcript.html', {
        'student': student,
        'strength_data': strength_data,
        'today': date.today(),
        'top_events': top_events,
        'qr_code': qr_b64
    })

def transcript_pdf(request, roll_no):
    student = get_object_or_404(Student, roll_no=roll_no)
    participations = Participation.objects.filter(student=student)

    strength_scores = defaultdict(float)
    benchmark_scores = defaultdict(float)

    for part in participations:
        role_factor = part.role.factor if part.role else 1.0
        for attr in part.event.attributes.all():
            mappings = AttributeStrengthMap.objects.filter(graduate_attribute=attr)
            for map in mappings:
                weighted_score = map.weight * role_factor
                strength_scores[map.character_strength.name] += weighted_score

    all_participations = Participation.objects.all()
    student_strength_totals = defaultdict(lambda: defaultdict(float))

    for part in all_participations:
        role_factor = part.role.factor if part.role else 1.0
        for attr in part.event.attributes.all():
            mappings = AttributeStrengthMap.objects.filter(graduate_attribute=attr)
            for map in mappings:
                student_strength_totals[part.student.roll_no][map.character_strength.name] += map.weight * role_factor

    strength_data = []
    all_strengths = CharacterStrength.objects.order_by('name')
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

    sorted_events = sorted(participations, key=lambda p: len(p.event.attributes.all()), reverse=True)
    top_events = [p.event.name for p in sorted_events[:5]]

    qr_b64 = None
    if participations.count() > 5:
        scheme = 'https' if request.is_secure() else 'http'
        base_url = f"{scheme}://{request.get_host()}"
        all_events_url = base_url + reverse('transcript:all_events', kwargs={'roll_no': student.roll_no})
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

def all_events_view(request, roll_no):
    student = get_object_or_404(Student, roll_no=roll_no)
    participations = Participation.objects.filter(student=student)
    all_event_names = [f"{p.event.name} - {p.event.date}" for p in participations]
    return render(request, 'transcript_app/student_events.html', {
        'student': student,
        'all_events': all_event_names
    })
