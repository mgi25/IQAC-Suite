import json
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.forms import inlineformset_factory
from django.test import RequestFactory, TestCase

from core.adapters import SchoolSocialAccountAdapter
from core.models import (ApprovalFlowTemplate, Organization, OrganizationRole,
                         OrganizationType, RoleAssignment)
from core.views import RoleAssignmentForm, RoleAssignmentFormSet


class OrganizationModelTests(TestCase):
    def test_create_organization(self):
        org_type = OrganizationType.objects.create(name="Department")
        org = Organization.objects.create(name="Math", org_type=org_type)

        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(org.org_type.name, "Department")


class UserRoleAssignmentTests(TestCase):
    def setUp(self):
        ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Math", org_type=ot)
        self.student_role = OrganizationRole.objects.create(
            organization=self.org, name="student"
        )
        self.faculty_role = OrganizationRole.objects.create(
            organization=self.org, name="faculty"
        )

    def _login(self, username, password):
        session = self.client.session
        session["org_id"] = self.org.id
        session.save()
        success = self.client.login(username=username, password=password)
        self.assertTrue(success)

    def test_student_role_assigned_on_login(self):
        user = User.objects.create_user(
            "stud", email="stud@example.com", password="pass", is_active=False
        )
        RoleAssignment.objects.create(
            user=user, organization=self.org, role=self.student_role
        )
        self._login("stud", "pass")
        user.refresh_from_db()
        self.assertEqual(user.profile.role, "student")

    def test_faculty_role_assigned_on_login(self):
        user = User.objects.create_user(
            "fac", email="fac@example.com", password="pass", is_active=False
        )
        RoleAssignment.objects.create(
            user=user, organization=self.org, role=self.faculty_role
        )
        self._login("fac", "pass")
        user.refresh_from_db()
        self.assertEqual(user.profile.role, "faculty")

    def test_api_auth_me_returns_profile_role(self):
        user = User.objects.create_user(
            username="stud2",
            email="stud2@example.com",
            password="pass",
            first_name="Stu",
            last_name="Dent",
            is_active=False,
        )
        RoleAssignment.objects.create(
            user=user, organization=self.org, role=self.student_role
        )
        self._login("stud2", "pass")
        resp = self.client.get("/core-admin/api/auth/me")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["role"], "student")


class ApprovalFlowViewTests(TestCase):
    def test_delete_approval_flow(self):
        ot = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Math", org_type=ot)
        ApprovalFlowTemplate.objects.create(
            organization=org, step_order=1, role_required="faculty"
        )

        admin = User.objects.create_superuser("admin", "a@x.com", "pass")
        self.client.force_login(admin)

        resp = self.client.post(f"/core-admin/approval-flow/{org.id}/delete/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ApprovalFlowTemplate.objects.count(), 0)

    def test_admin_approval_flow_list_includes_status_annotations(self):
        ot = OrganizationType.objects.create(name="Dept")
        org_with_flow = Organization.objects.create(name="Math", org_type=ot)
        org_without_flow = Organization.objects.create(name="Physics", org_type=ot)

        ApprovalFlowTemplate.objects.create(
            organization=org_with_flow,
            step_order=1,
            role_required="faculty",
        )
        archived = ApprovalFlowTemplate.objects.create(
            organization=org_with_flow,
            step_order=2,
            role_required="hod",
        )
        archived.archive()

        admin = User.objects.create_superuser("admin", "a@x.com", "pass")
        self.client.force_login(admin)

        resp = self.client.get("/core-admin/approval-flow/")
        self.assertEqual(resp.status_code, 200)

        orgs = {o.name: o for o in resp.context["orgs_by_type"][ot.name]}
        self.assertTrue(orgs["Math"].has_approval_flow)
        self.assertEqual(orgs["Math"].approval_step_count, 1)
        self.assertFalse(orgs["Physics"].has_approval_flow)
        self.assertEqual(orgs["Physics"].approval_step_count, 0)

    def test_save_approval_flow_forbidden_for_non_superuser(self):
        ot = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Math", org_type=ot)
        user = User.objects.create_user("user", "u@x.com", "pass", is_active=False)
        role = OrganizationRole.objects.create(organization=org, name="Member")
        RoleAssignment.objects.create(user=user, role=role, organization=org)
        self.assertTrue(self.client.login(username="user", password="pass"))

        resp = self.client.post(
            f"/core-admin/approval-flow/{org.id}/save/",
            data=json.dumps({"steps": []}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


class SaveApprovalFlowTests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Math", org_type=self.ot)

    def test_save_approval_flow_creates_steps(self):
        admin = User.objects.create_superuser("admin", "a@x.com", "pass")
        user1 = User.objects.create(username="u1")
        self.client.force_login(admin)

        steps = [
            {"role_required": "faculty"},
            {"role_required": "hod", "user_id": user1.id, "optional": True},
        ]

        resp = self.client.post(
            f"/core-admin/approval-flow/{self.org.id}/save/",
            data=json.dumps({"steps": steps}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        templates = list(
            ApprovalFlowTemplate.objects.filter(organization=self.org).order_by(
                "step_order"
            )
        )
        self.assertEqual(len(templates), 2)
        self.assertEqual(templates[0].step_order, 1)
        self.assertEqual(templates[0].role_required, "faculty")
        self.assertIsNone(templates[0].user)
        self.assertFalse(templates[0].optional)
        self.assertEqual(templates[1].step_order, 2)
        self.assertEqual(templates[1].role_required, "hod")
        self.assertEqual(templates[1].user, user1)
        self.assertTrue(templates[1].optional)

    def test_save_approval_flow_forbidden_for_non_superuser(self):
        user = User.objects.create_user("user", "u@x.com", "pass", is_active=False)
        role = OrganizationRole.objects.create(organization=self.org, name="Member")
        RoleAssignment.objects.create(user=user, role=role, organization=self.org)
        self.assertTrue(self.client.login(username="user", password="pass"))

        resp = self.client.post(
            f"/core-admin/approval-flow/{self.org.id}/save/",
            data=json.dumps({"steps": []}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


class RoleManagementTests(TestCase):
    def test_add_role(self):
        ot = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Math", org_type=ot)
        admin = User.objects.create_superuser("admin", "a@x.com", "pass")
        self.client.force_login(admin)

        resp = self.client.post(
            "/core-admin/user-roles/add/", {"org_id": org.id, "name": "Coordinator"}
        )

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            OrganizationRole.objects.filter(
                organization=org, name="Coordinator"
            ).count(),
            1,
        )

    def test_add_role_to_org_type(self):
        ot = OrganizationType.objects.create(name="Club")
        _ = Organization.objects.create(name="Art", org_type=ot)
        _ = Organization.objects.create(name="Music", org_type=ot)
        admin = User.objects.create_superuser("admin", "a@x.com", "pass")
        self.client.force_login(admin)

        resp = self.client.post(
            "/core-admin/user-roles/add/",
            {
                "org_type_id": ot.id,
                "name": "Coordinator",
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            OrganizationRole.objects.filter(
                organization__org_type=ot, name="Coordinator"
            ).count(),
            2,
        )

    def test_duplicate_role_assignments_rejected(self):
        user = User.objects.create(username="u1")
        ot = OrganizationType.objects.create(name="Dept")
        org = Organization.objects.create(name="Math", org_type=ot)
        role_obj = OrganizationRole.objects.create(organization=org, name="hod")
        RoleAssignment.objects.create(user=user, role=role_obj, organization=org)

        RoleFormSet = inlineformset_factory(
            User,
            RoleAssignment,
            form=RoleAssignmentForm,
            formset=RoleAssignmentFormSet,
            fields=("role", "organization"),
            extra=0,
            can_delete=True,
        )

        data = {
            "role_assignments-TOTAL_FORMS": "2",
            "role_assignments-INITIAL_FORMS": "1",
            "role_assignments-MIN_NUM_FORMS": "0",
            "role_assignments-MAX_NUM_FORMS": "1000",
            "role_assignments-0-id": str(RoleAssignment.objects.first().id),
            "role_assignments-0-role": str(role_obj.id),
            "role_assignments-0-organization": str(org.id),
            "role_assignments-1-role": str(role_obj.id),
            "role_assignments-1-organization": str(org.id),
        }
        formset = RoleFormSet(data, instance=user)
        self.assertFalse(formset.is_valid())
        self.assertIn("Duplicate role assignment", formset.non_form_errors()[0])


class SearchUsersTests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Math", org_type=self.ot)
        self.role_obj = OrganizationRole.objects.create(
            organization=self.org, name="Faculty"
        )
        self.user = User.objects.create(
            username="u1", first_name="Alpha", email="alpha@example.com"
        )
        RoleAssignment.objects.create(
            user=self.user, role=self.role_obj, organization=self.org
        )
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(self.admin)

    def test_search_users_by_role(self):
        resp = self.client.get(
            "/core-admin/api/search-users/",
            {
                "role": "Faculty",
                "org_id": self.org.id,
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data.get("users", [])), 1)
        self.assertEqual(data["users"][0]["id"], self.user.id)


class ApprovalFlowTemplateDisplayTests(TestCase):
    def setUp(self):
        self.ot = OrganizationType.objects.create(name="Dept")
        self.org = Organization.objects.create(name="Math", org_type=self.ot)

    def test_get_role_required_display_uses_org_role(self):
        OrganizationRole.objects.create(organization=self.org, name="Faculty")
        step = ApprovalFlowTemplate.objects.create(
            organization=self.org, step_order=1, role_required="faculty"
        )
        self.assertEqual(step.get_role_required_display(), "Faculty")

    def test_get_role_required_display_formats_fallback(self):
        step = ApprovalFlowTemplate.objects.create(
            organization=self.org,
            step_order=1,
            role_required="committee_member",
        )
        self.assertEqual(step.get_role_required_display(), "Committee Member")

    def test_get_approval_flow_endpoint_returns_display(self):
        OrganizationRole.objects.create(organization=self.org, name="Faculty")
        ApprovalFlowTemplate.objects.create(
            organization=self.org, step_order=1, role_required="faculty"
        )
        resp = self.client.get(f"/core-admin/approval-flow/{self.org.id}/get/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["steps"][0]["role_display"], "Faculty")
        self.assertIn("optional", data["steps"][0])


class SocialLoginAccessTests(TestCase):
    """Ensure only existing users can authenticate via social login."""

    def setUp(self):
        self.factory = RequestFactory()
        self.adapter = SchoolSocialAccountAdapter()

    def _build_request(self):
        request = self.factory.get("/")
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)
        return request

    def _sociallogin(self, email):
        username = email.split("@")[0]

        class DummySocialLogin(SimpleNamespace):
            def connect(self, request, user):
                self.user = user

        return DummySocialLogin(user=User(username=username, email=email))

    def test_unknown_email_allowed(self):
        request = self._build_request()
        email = "unknown@example.com"
        sociallogin = self._sociallogin(email)
        # Should not raise and should not create a user automatically
        self.adapter.pre_social_login(request, sociallogin)
        self.assertFalse(User.objects.filter(email=email).exists())

    def test_existing_user_allowed(self):
        _ = User.objects.create_user(
            "known", "known@example.com", "pass", is_active=False
        )
        request = self._build_request()
        sociallogin = self._sociallogin("known@example.com")
        self.adapter.pre_social_login(request, sociallogin)
        self.assertEqual(User.objects.filter(email="known@example.com").count(), 1)
