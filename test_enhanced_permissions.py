#!/usr/bin/env python
"""
Test script for the new dashboard assignment and enhanced permissions system.
Run this to verify that everything is working correctly.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iqac_project.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from core.models import SidebarPermission, DashboardAssignment, RoleAssignment, Organization, OrganizationType

def test_dashboard_assignments():
    """Test the dashboard assignment functionality"""
    print("=" * 50)
    print("TESTING DASHBOARD ASSIGNMENTS")
    print("=" * 50)
    
    # Test admin gets all dashboards
    admin = User.objects.filter(is_superuser=True).first()
    if admin:
        available_dashboards = DashboardAssignment.get_user_dashboards(admin)
        print(f"Admin user {admin.username} dashboards: {len(available_dashboards)} (should be all)")
        for dashboard_key, dashboard_name in available_dashboards:
            print(f"  - {dashboard_key}: {dashboard_name}")
    else:
        print("No admin user found")
    
    # Test regular user with no assignments
    regular_user = User.objects.filter(is_superuser=False).first()
    if regular_user:
        available_dashboards = DashboardAssignment.get_user_dashboards(regular_user)
        print(f"\nRegular user {regular_user.username} dashboards: {len(available_dashboards)}")
        if not available_dashboards:
            print("  - No dashboards assigned (expected)")
        
        # Create a test assignment
        assignment = DashboardAssignment.objects.create(
            user=regular_user,
            dashboard='student'
        )
        print(f"  - Created assignment: {assignment}")
        
        # Test again
        available_dashboards = DashboardAssignment.get_user_dashboards(regular_user)
        print(f"  - After assignment: {len(available_dashboards)} dashboard(s)")
        for dashboard_key, dashboard_name in available_dashboards:
            print(f"    - {dashboard_key}: {dashboard_name}")
    else:
        print("No regular user found")

def test_sidebar_permissions():
    """Test the sidebar permissions functionality"""
    print("\n" + "=" * 50)
    print("TESTING SIDEBAR PERMISSIONS")
    print("=" * 50)
    
    # Test role-based permissions
    student_perm, created = SidebarPermission.objects.get_or_create(
        user=None,
        role='student',
        defaults={'items': ['dashboard', 'events', 'profile']}
    )
    print(f"Student role permissions: {student_perm.items}")
    
    faculty_perm, created = SidebarPermission.objects.get_or_create(
        user=None,
        role='faculty',
        defaults={'items': ['dashboard', 'events', 'cdl', 'pso_psos', 'profile']}
    )
    print(f"Faculty role permissions: {faculty_perm.items}")
    
    # Test context processor
    from django.test import RequestFactory
    from django.contrib.sessions.middleware import SessionMiddleware
    from core.context_processors import sidebar_permissions
    
    factory = RequestFactory()
    
    # Test admin permissions (should be empty = full access)
    admin = User.objects.filter(is_superuser=True).first()
    if admin:
        request = factory.get('/')
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        request.user = admin
        
        result = sidebar_permissions(request)
        print(f"Admin sidebar items: {result['allowed_nav_items']} (empty = full access)")
    
    # Test regular user with session role
    regular_user = User.objects.filter(is_superuser=False).first()
    if regular_user:
        request = factory.get('/')
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        request.user = regular_user
        request.session['role'] = 'student'
        
        result = sidebar_permissions(request)
        print(f"Student user sidebar items: {result['allowed_nav_items']}")

def test_enhanced_permissions_views():
    """Test that the enhanced permissions views work"""
    print("\n" + "=" * 50)
    print("TESTING ENHANCED PERMISSIONS VIEWS")
    print("=" * 50)
    
    from django.test import Client
    
    client = Client()
    
    # Test enhanced permissions page (requires admin login)
    admin = User.objects.filter(is_superuser=True).first()
    if admin:
        login_success = client.login(username=admin.username, password='admin123')  # Adjust password as needed
        if login_success:
            response = client.get('/core-admin/enhanced-permissions/')
            print(f"Enhanced permissions page status: {response.status_code}")
            if response.status_code == 200:
                print("✓ Enhanced permissions page loads successfully")
            else:
                print("✗ Enhanced permissions page failed to load")
        else:
            print("Could not login as admin (check password)")
    else:
        print("No admin user found for testing")

def main():
    """Main test function"""
    print("DASHBOARD ASSIGNMENT & ENHANCED PERMISSIONS TEST")
    print("Time:", django.utils.timezone.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    try:
        test_dashboard_assignments()
        test_sidebar_permissions()
        test_enhanced_permissions_views()
        
        print("\n" + "=" * 50)
        print("✓ ALL TESTS COMPLETED")
        print("=" * 50)
        print("\nTo use the new features:")
        print("1. Start server: python manage.py runserver")
        print("2. Login as admin")
        print("3. Go to: http://localhost:8000/core-admin/enhanced-permissions/")
        print("4. Configure dashboard assignments and sidebar permissions")
        print("5. Test with different user accounts")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
