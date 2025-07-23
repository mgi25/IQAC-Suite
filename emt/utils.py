# emt/utils.py

import os
import requests
from django.contrib.auth.models import User
from .models import ApprovalStep
from core.models import Association, Club, Center, Cell, Department

# (The build_approval_chain function remains unchanged)
def build_approval_chain(proposal):
    """
    Build a dynamic approval chain based on org type, escalation, and flags.
    Only the first step is 'pending', others are 'waiting'.
    """
    steps = []
    order = 1
    org_type = None
    org_id = None

    # Detect organization type from proposal (Association/Center/Club/Cell/Department/Individual)
    if proposal.association_id:
        org_type, org_id = 'association', proposal.association_id
    elif proposal.center_id:
        org_type, org_id = 'center', proposal.center_id
    elif proposal.club_id:
        org_type, org_id = 'club', proposal.club_id
    elif proposal.cell_id:
        org_type, org_id = 'cell', proposal.cell_id
    elif proposal.department_id:
        org_type, org_id = 'department', proposal.department_id
    else:
        org_type = 'individual'

    # 1️⃣ ASSOCIATION PROPOSAL
    if org_type == 'association':
        try:
            assoc = Association.objects.get(id=org_id, is_active=True)
        except Association.DoesNotExist:
            # Skip if association is inactive
            return []
        head = User.objects.filter(role_assignments__role='association_head', role_assignments__association=assoc).first()
        if head:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required='association_head', assigned_to=head
            ))
            order += 1
        iqac = User.objects.filter(role_assignments__role='dept_iqac', role_assignments__department=assoc.department).first()
        if iqac:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required='dept_iqac', assigned_to=iqac
            ))
            order += 1
        hod = User.objects.filter(role_assignments__role='hod', role_assignments__department=assoc.department).first()
        if hod:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required='hod', assigned_to=hod
            ))
            order += 1

    # 2️⃣ CENTER PROPOSAL
    elif org_type == 'center':
        try:
            center = Center.objects.get(id=org_id, is_active=True)
        except Center.DoesNotExist:
            # Skip if center is inactive
            return []
        head = User.objects.filter(role_assignments__role='center_head', role_assignments__center=center).first()
        if head:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required='center_head', assigned_to=head
            ))
            order += 1
        uni_iqac = User.objects.filter(role_assignments__role='uni_iqac').first()
        if uni_iqac:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required='uni_iqac', assigned_to=uni_iqac
            ))
            order += 1

    # 3️⃣ CLUB PROPOSAL
    elif org_type == 'club':
        try:
            club = Club.objects.get(id=org_id, is_active=True)
        except Club.DoesNotExist:
            # Skip if club is inactive
            return []
        head = User.objects.filter(role_assignments__role='club_head', role_assignments__club=club).first()
        if head:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required='club_head', assigned_to=head
            ))
            order += 1
        uni_club_head = User.objects.filter(role_assignments__role='university_club_head').first()
        if uni_club_head:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required='university_club_head', assigned_to=uni_club_head
            ))
            order += 1

    # 4️⃣ CELL PROPOSAL
    elif org_type == 'cell':
        try:
            cell = Cell.objects.get(id=org_id, is_active=True)
        except Cell.DoesNotExist:
            # Skip if cell is inactive
            return []
        head = User.objects.filter(role_assignments__role='cell_head', role_assignments__cell=cell).first()
        if head:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required='cell_head', assigned_to=head
            ))
            order += 1
        uni_iqac = User.objects.filter(role_assignments__role='uni_iqac').first()
        if uni_iqac:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required='uni_iqac', assigned_to=uni_iqac
            ))
            order += 1

    # 5️⃣ DEPARTMENT PROPOSAL (No Association/Center/Club/Cell)
    elif org_type == 'department':
        faculty_users = proposal.faculty_incharges.all()
        for fac in faculty_users:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required='faculty', assigned_to=fac
            ))
            order += 1
        dept_iqac = User.objects.filter(role_assignments__role='dept_iqac', role_assignments__department=proposal.department).first()
        if dept_iqac:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required='dept_iqac', assigned_to=dept_iqac
            ))
            order += 1
        hod = User.objects.filter(role_assignments__role='hod', role_assignments__department=proposal.department).first()
        if hod:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required='hod', assigned_to=hod
            ))
            order += 1

    # 6️⃣ INDIVIDUAL PROPOSAL (No org attached)
    else:  # org_type == 'individual'
        acad_coord = User.objects.filter(role_assignments__role='academic_coordinator').first()
        dean = User.objects.filter(role_assignments__role='dean').first()
        assigned = acad_coord or dean
        if assigned:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order, role_required=assigned.role_assignments.first().role, assigned_to=assigned
            ))

    # Set only the first step as 'pending', others as 'waiting'
    for i, step in enumerate(steps):
        step.status = 'pending' if i == 0 else 'waiting'
    ApprovalStep.objects.bulk_create(steps)


def generate_report_with_ai(event_report):
    """
    Generates a comprehensive event report using the Gemini AI model.

    Args:
        event_report: The EventReport model instance.

    Returns:
        The generated report text as a string, or an error message if something goes wrong.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY is not set in the .env file."

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    proposal = event_report.proposal

    # --- FIX 2: Get a clean name for the organizing body ---
    organizing_body = (
        proposal.department or
        proposal.association or
        proposal.club or
        proposal.center or
        proposal.cell or
        "Individual/Self"
    )

    # --- FIX 1: Safely format the date ---
    event_date_str = "Not specified"
    if proposal.event_datetime:
        event_date_str = proposal.event_datetime.strftime('%B %d, %Y')


    prompt = f"""
    Generate a formal event report using Markdown formatting based on the following details.
    The report should be well-structured, professional, and comprehensive.

    **Event Title:** {proposal.event_title}
    **Organizing Body:** {organizing_body}
    **Event Date:** {event_date_str}
    **Venue:** {proposal.venue}

    **1. Event Summary:**
    {event_report.summary}

    **2. Objectives & Outcomes:**
    - **Stated Objectives:** {proposal.eventobjectives.content if hasattr(proposal, 'eventobjectives') else 'Not provided.'}
    - **Achieved Outcomes:** {event_report.outcomes}

    **3. Participation & Engagement:**
    - **Target Audience:** {proposal.target_audience}
    - **Number of Participants:** {event_report.num_participants}
    - **Student Volunteers:** {event_report.num_student_volunteers}

    **4. Innovations and Best Practices:**
    {event_report.innovations_best_practices}

    **5. Impact on Stakeholders:**
    {event_report.impact_on_stakeholders}

    **Task:**
    Synthesize the information above into a coherent report. The report should include the following sections:
    - **Introduction:** Briefly introduce the event, its purpose, and the organizing body.
    - **Execution Summary:** Describe how the event was conducted.
    - **Participation Analysis:** Detail participant engagement.
    - **Outcomes and Impact:** Analyze how objectives were met and the overall impact.
    - **Conclusion and Recommendations:** Conclude the report and suggest improvements.
    """

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}]
    }

    try:
        response = requests.post(api_url, json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        result = response.json()

        if 'candidates' in result and result['candidates'][0]['content']['parts'][0]['text']:
            return result['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            error_detail = result.get('error', {}).get('message', 'No content found.')
            return f"Error: AI response was malformed. Details: {error_detail}"

    except requests.exceptions.RequestException as e:
        return f"Error: Could not connect to the AI service. Details: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"