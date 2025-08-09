import os
import requests
from django.contrib.auth.models import User
from .models import ApprovalStep
from core.models import (
    Organization,
    OrganizationType,
    ApprovalFlowTemplate,
    ApprovalFlowConfig,
)

def build_approval_chain(proposal):
    """Create approval steps for a proposal based on org config and templates."""
    config = ApprovalFlowConfig.objects.filter(
        organization=proposal.organization
    ).first()

    flow = ApprovalFlowTemplate.objects.filter(
        organization=proposal.organization
    ).order_by("step_order")

    steps = []
    idx = 1

    # Track if we've already added faculty in-charge approvals
    fic_first = config and config.require_faculty_incharge_first

    if fic_first:
        for fic in proposal.faculty_incharges.all():
            steps.append(
                ApprovalStep(
                    proposal=proposal,
                    step_order=idx,
                    role_required=ApprovalStep.Role.FACULTY_INCHARGE,
                    assigned_to=fic,
                    status="pending" if idx == 1 else "waiting",
                )
            )
            idx += 1

    for tmpl in flow:
        if getattr(tmpl, 'optional', False):
            continue
        # Skip duplicate faculty in-charge steps if they're already added above
        if fic_first and tmpl.role_required == ApprovalStep.Role.FACULTY_INCHARGE:
            continue

        assigned_to = tmpl.user or User.objects.filter(
            role_assignments__role__name=tmpl.role_required,
            role_assignments__organization=proposal.organization,
        ).first()

        steps.append(
            ApprovalStep(
                proposal=proposal,
                step_order=idx,
                role_required=tmpl.role_required,
                assigned_to=assigned_to,
                status="pending" if idx == 1 else "waiting",
            )
        )
        idx += 1

    ApprovalStep.objects.bulk_create(steps)

# ---------------------------------------------
# generate_report_with_ai remains unchanged!
# ---------------------------------------------
def generate_report_with_ai(event_report):
    """
    Generates a comprehensive event report using the Gemini AI model.

    Args:
        event_report: The EventReport model instance.

    Returns:
        The generated report text as a string, or an error message if something goes wrong.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY or GOOGLE_API_KEY is not set in the .env file."

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    proposal = event_report.proposal

    organizing_body = proposal.organization or "Individual/Self"

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
    - **Stated Objectives:** {proposal.objectives.content if hasattr(proposal, 'objectives') else 'Not provided.'}
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
