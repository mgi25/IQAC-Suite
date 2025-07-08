# emt/utils.py
from django.contrib.auth.models import User
from .models import ApprovalStep       # <-- keep

def create_approval_steps(proposal):
    """
    Build the linear approval chain …
    """
    steps  = []
    order  = 1
    dept_id = proposal.department_id    # <<<<<<  NEW – use ID once

    # 1️⃣ Faculty in-charges (unchanged)
    for u in proposal.faculty_incharges.all():
        steps.append(ApprovalStep(
            proposal=proposal, step_order=order,
            role_required='faculty', assigned_to=u,
        ))
    if steps:                            # only bump if we added any
        order += 1

    # 2️⃣ Dept-IQAC  <<<<<<  use *_id filters
    iqacs = User.objects.filter(
        role_assignments__role='dept_iqac',
        role_assignments__department_id=dept_id
    ).distinct()
    for u in iqacs:
        steps.append(ApprovalStep(
            proposal=proposal, step_order=order,
            role_required='dept_iqac', assigned_to=u,
        ))
    if iqacs:
        order += 1

    # 3️⃣ HOD
    hods = User.objects.filter(
        role_assignments__role='hod',
        role_assignments__department_id=dept_id
    ).distinct()
    for u in hods:
        steps.append(ApprovalStep(
            proposal=proposal, step_order=order,
            role_required='hod', assigned_to=u,
        ))
    if hods:
        order += 1

    # 4️⃣ Director (finance) – unchanged
    if proposal.needs_finance_approval:
        dirs = User.objects.filter(role_assignments__role='director').distinct()
        for u in dirs:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order,
                role_required='director', assigned_to=u,
            ))
        order += 1

    # 5️⃣ Dean (big event) – unchanged
    if proposal.is_big_event:
        deans = User.objects.filter(role_assignments__role='dean').distinct()
        for u in deans:
            steps.append(ApprovalStep(
                proposal=proposal, step_order=order,
                role_required='dean', assigned_to=u,
            ))

    ApprovalStep.objects.bulk_create(steps)
