from django.contrib.auth.models import User
from .models import ApprovalStep
from core.models import Association, Club, Center, Cell, Department

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
        assoc = Association.objects.get(id=org_id)
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
        center = Center.objects.get(id=org_id)
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
        club = Club.objects.get(id=org_id)
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
        cell = Cell.objects.get(id=org_id)
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
