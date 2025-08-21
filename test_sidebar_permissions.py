#!/usr/bin/env python
"""
Test script to demonstrate sidebar permissions functionality.
Run this after setting up some permissions via the admin interface.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iqac_project.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from core.models import SidebarPermission, RoleAssignment, Organization, OrganizationType

def create_test_users():
    """Create test users and roles"""
    print("Creating test users...")
    
    # Create test students
    student1, created = User.objects.get_or_create(
        username='student1',
        defaults={
            'email': 'student1@christuniversity.in',
            'first_name': 'John',
            'last_name': 'Student'
        }
    )
    if created:
        student1.set_password('password123')
        student1.save()
    
    # Create test faculty
    faculty1, created = User.objects.get_or_create(
        username='faculty1',
        defaults={
            'email': 'faculty1@christuniversity.in',
            'first_name': 'Jane',
            'last_name': 'Faculty'
        }
    )
    if created:
        faculty1.set_password('password123')
        faculty1.save()
    
    print(f"Student user: {student1.username} (ID: {student1.id})")
    print(f"Faculty user: {faculty1.username} (ID: {faculty1.id})")
    
    return student1, faculty1

def setup_permissions():
    """Setup test permissions"""
    print("\nSetting up permissions...")
    
    # Give students only dashboard and events access
    student_perm, created = SidebarPermission.objects.get_or_create(
        user=None,
        role='student',
        defaults={'items': ['dashboard', 'events']}
    )
    if not created:
        student_perm.items = ['dashboard', 'events']
        student_perm.save()
    
    # Give faculty dashboard, events, CDL, and PO/PSO management
    faculty_perm, created = SidebarPermission.objects.get_or_create(
        user=None,
        role='faculty',
        defaults={'items': ['dashboard', 'events', 'cdl', 'pso_psos']}
    )
    if not created:
        faculty_perm.items = ['dashboard', 'events', 'cdl', 'pso_psos']
        faculty_perm.save()
    
    print(f"Student permissions: {student_perm.items}")
    print(f"Faculty permissions: {faculty_perm.items}")

def test_context_processor():
    """Test the sidebar permissions context processor"""
    print("\nTesting context processor...")
    
    from django.test import RequestFactory
    from django.contrib.sessions.middleware import SessionMiddleware
    from core.context_processors import sidebar_permissions
    
    factory = RequestFactory()
    
    # Test student permissions
    student = User.objects.get(username='student1')
    request = factory.get('/')
    
    # Add session support
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    request.user = student
    request.session['role'] = 'student'
    
    result = sidebar_permissions(request)
    print(f"Student sidebar items: {result['allowed_nav_items']}")
    
    # Test faculty permissions
    faculty = User.objects.get(username='faculty1')
    request.user = faculty
    request.session['role'] = 'faculty'
    
    result = sidebar_permissions(request)
    print(f"Faculty sidebar items: {result['allowed_nav_items']}")
    
    # Test admin permissions (should be empty = full access)
    admin = User.objects.filter(is_superuser=True).first()
    if admin:
        request.user = admin
        result = sidebar_permissions(request)
        print(f"Admin sidebar items: {result['allowed_nav_items']} (empty = full access)")

def main():
    """Main test function"""
    print("=" * 50)
    print("SIDEBAR PERMISSIONS TEST")
    print("=" * 50)
    
    # Create test users
    student, faculty = create_test_users()
    
    # Setup permissions
    setup_permissions()
    
    # Test context processor
    test_context_processor()
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("\nTo test the UI:")
    print("1. Run: python manage.py runserver")
    print("2. Login as admin and go to: http://localhost:8000/core-admin/sidebar-permissions/")
    print("3. Login as student1 or faculty1 with password 'password123'")
    print("4. Check that only permitted sidebar items are visible")
    print("=" * 50)

if __name__ == '__main__':
    main()
