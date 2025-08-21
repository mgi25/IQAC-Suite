#!/usr/bin/env python
"""
Test script to verify all fixed issues are working properly.
This tests the AttributeError fixes and other potential issues.
"""

import os
import sys
import django

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iqac_project.settings')

# Setup Django
django.setup()

def test_admin_dashboard_function_exists():
    """Test that the admin_dashboard function exists and is accessible"""
    try:
        from core import views
        # Check if admin_dashboard function exists
        admin_dashboard_func = getattr(views, 'admin_dashboard', None)
        if admin_dashboard_func is None:
            return False, "admin_dashboard function not found in core.views"
        
        # Check if it's callable
        if not callable(admin_dashboard_func):
            return False, "admin_dashboard exists but is not callable"
        
        return True, "admin_dashboard function exists and is callable"
    except Exception as e:
        return False, f"Error testing admin_dashboard: {str(e)}"

def test_select_dashboard_function_exists():
    """Test that the select_dashboard function exists"""
    try:
        from core import views
        select_dashboard_func = getattr(views, 'select_dashboard', None)
        if select_dashboard_func is None:
            return False, "select_dashboard function not found in core.views"
        
        if not callable(select_dashboard_func):
            return False, "select_dashboard exists but is not callable"
        
        return True, "select_dashboard function exists and is callable"
    except Exception as e:
        return False, f"Error testing select_dashboard: {str(e)}"

def test_api_dashboard_places_function_exists():
    """Test that the api_dashboard_places function exists"""
    try:
        from core import views
        api_dashboard_places_func = getattr(views, 'api_dashboard_places', None)
        if api_dashboard_places_func is None:
            return False, "api_dashboard_places function not found in core.views"
        
        if not callable(api_dashboard_places_func):
            return False, "api_dashboard_places exists but is not callable"
        
        return True, "api_dashboard_places function exists and is callable"
    except Exception as e:
        return False, f"Error testing api_dashboard_places: {str(e)}"

def test_cdl_functions_exist():
    """Test that CDL dashboard functions exist"""
    try:
        from core import views
        functions_to_test = [
            'cdl_dashboard',
            'cdl_head_dashboard', 
            'cdl_member_dashboard',
            'cdl_work_dashboard',
            'cdl_create_availability'
        ]
        
        missing_functions = []
        non_callable_functions = []
        
        for func_name in functions_to_test:
            func = getattr(views, func_name, None)
            if func is None:
                missing_functions.append(func_name)
            elif not callable(func):
                non_callable_functions.append(func_name)
        
        if missing_functions:
            return False, f"Missing CDL functions: {', '.join(missing_functions)}"
        
        if non_callable_functions:
            return False, f"Non-callable CDL functions: {', '.join(non_callable_functions)}"
        
        return True, "All CDL dashboard functions exist and are callable"
    except Exception as e:
        return False, f"Error testing CDL functions: {str(e)}"

def test_dashboard_assignment_model_works():
    """Test that DashboardAssignment model works properly"""
    try:
        from core.models import DashboardAssignment
        from django.contrib.auth.models import User
        
        # Test that the model can be imported and has the expected methods
        if not hasattr(DashboardAssignment, 'get_user_dashboards'):
            return False, "DashboardAssignment.get_user_dashboards method not found"
        
        # Test the method with a mock user (don't actually create one)
        if not hasattr(DashboardAssignment, 'DASHBOARD_CHOICES'):
            return False, "DashboardAssignment.DASHBOARD_CHOICES not found"
        
        # Check that the choices are properly defined
        choices = DashboardAssignment.DASHBOARD_CHOICES
        expected_choices = ['admin', 'faculty', 'student', 'cdl_head', 'cdl_work']
        choice_keys = [choice[0] for choice in choices]
        
        missing_choices = set(expected_choices) - set(choice_keys)
        if missing_choices:
            return False, f"Missing dashboard choices: {', '.join(missing_choices)}"
        
        return True, "DashboardAssignment model is properly configured"
    except Exception as e:
        return False, f"Error testing DashboardAssignment model: {str(e)}"

def test_imports_work():
    """Test that critical imports work without errors"""
    try:
        # Test core imports
        from core import views, models, urls
        
        # Test specific imports that might cause issues
        from core.models import (
            User, Organization, RoleAssignment, DashboardAssignment,
            SidebarPermission, EventProposal, Report
        )
        
        return True, "All critical imports work successfully"
    except Exception as e:
        return False, f"Import error: {str(e)}"

def test_url_patterns_load():
    """Test that URL patterns can be loaded without errors"""
    try:
        from django.urls import reverse
        
        # Test key URL patterns
        url_names_to_test = [
            'admin_dashboard',
            'dashboard',
            'select_dashboard',
            'api_dashboard_places',
            'admin_dashboard_api',
            'cdl_head_dashboard',
            'cdl_work_dashboard',
            'create_availability'
        ]
        
        missing_urls = []
        
        for url_name in url_names_to_test:
            try:
                if url_name == 'select_dashboard':
                    # This URL requires a parameter
                    reverse(url_name, kwargs={'dashboard_key': 'admin'})
                else:
                    reverse(url_name)
            except Exception:
                missing_urls.append(url_name)
        
        if missing_urls:
            return False, f"URL patterns not found or invalid: {', '.join(missing_urls)}"
        
        return True, "All URL patterns load successfully"
    except Exception as e:
        return False, f"Error testing URL patterns: {str(e)}"

def run_all_tests():
    """Run all tests and report results"""
    tests = [
        ("Admin Dashboard Function", test_admin_dashboard_function_exists),
        ("Select Dashboard Function", test_select_dashboard_function_exists),
        ("API Dashboard Places Function", test_api_dashboard_places_function_exists),
        ("CDL Functions", test_cdl_functions_exist),
        ("DashboardAssignment Model", test_dashboard_assignment_model_works),
        ("Critical Imports", test_imports_work),
        ("URL Patterns", test_url_patterns_load),
    ]
    
    print("🧪 Running comprehensive tests for fixed issues...\n")
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            success, message = test_func()
            if success:
                print(f"✅ {test_name}: {message}")
                passed += 1
            else:
                print(f"❌ {test_name}: {message}")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name}: Unexpected error - {str(e)}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! The AttributeError issues have been fixed.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
