#!/usr/bin/env python3
"""
Integration Test for SI-HQ Improvements
Tests the consolidated app functionality
"""

import re
import os

def test_file_exists(filepath, description):
    """Test if a file exists"""
    if os.path.exists(filepath):
        print(f"✅ {description}")
        return True
    else:
        print(f"❌ {description}")
        return False

def test_string_in_file(filepath, search_string, description):
    """Test if a string exists in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if search_string in content:
                print(f"✅ {description}")
                return True
            else:
                print(f"❌ {description}")
                return False
    except Exception as e:
        print(f"❌ {description} - Error: {e}")
        return False

def test_string_not_in_file(filepath, search_string, description):
    """Test if a string does NOT exist in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if search_string not in content:
                print(f"✅ {description}")
                return True
            else:
                print(f"❌ {description}")
                return False
    except Exception as e:
        print(f"❌ {description} - Error: {e}")
        return False

def test_function_defined(filepath, function_name, description):
    """Test if a JavaScript function is defined"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            pattern = rf'function\s+{function_name}\s*\('
            if re.search(pattern, content):
                print(f"✅ {description}")
                return True
            else:
                print(f"❌ {description}")
                return False
    except Exception as e:
        print(f"❌ {description} - Error: {e}")
        return False

def main():
    print("🧪 SI-HQ Integration Test Suite")
    print("="*50)
    
    base_path = "/home/runner/work/SI-HQ/SI-HQ/dashboard"
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Check if main files exist
    print("\n📁 File Existence Tests:")
    tests = [
        (f"{base_path}/templates/index.html", "Main dashboard template exists"),
        (f"{base_path}/templates/ml_dashboard.html", "ML dashboard (redirect) exists"),
        (f"{base_path}/static/scripts/scripts.js", "Main JavaScript file exists"),
        (f"{base_path}/app.py", "Main Flask app exists"),
    ]
    
    for filepath, desc in tests:
        total_tests += 1
        if test_file_exists(filepath, desc):
            tests_passed += 1
    
    # Test 2: Check integration changes
    print("\n🔗 Integration Tests:")
    
    # Check that ML prediction tool was removed from analytics
    total_tests += 1
    if test_string_not_in_file(f"{base_path}/static/scripts/scripts.js", 
                               "Add ML prediction tool to analytics page", 
                               "ML prediction tool removed from analytics page"):
        tests_passed += 1
    
    # Check that Predictive Analytics page exists
    total_tests += 1
    if test_string_in_file(f"{base_path}/templates/index.html", 
                           "predictive-analytics-page", 
                           "Predictive Analytics page added to main app"):
        tests_passed += 1
    
    # Check navigation update
    total_tests += 1
    if test_string_in_file(f"{base_path}/templates/index.html", 
                           "🔮 Predictive Analytics", 
                           "Navigation updated to Predictive Analytics"):
        tests_passed += 1
    
    # Check that old ML Dashboard reference is removed from navigation
    total_tests += 1
    if test_string_not_in_file(f"{base_path}/templates/index.html", 
                               "window.open('/ml', '_blank')", 
                               "Removed separate ML Dashboard link"):
        tests_passed += 1
    
    # Test 3: Check new functionality
    print("\n⚙️ Functionality Tests:")
    
    # Check that new functions are defined
    js_functions = [
        ("showPredictiveTab", "Predictive tab switching function"),
        ("makePrediction", "Make prediction function"),
        ("calculateKellyOptimal", "Kelly calculator function"),
        ("refreshPredictiveModels", "Model refresh function"),
    ]
    
    for func_name, desc in js_functions:
        total_tests += 1
        if test_function_defined(f"{base_path}/static/scripts/scripts.js", func_name, desc):
            tests_passed += 1
    
    # Check that train-model-modal exists
    total_tests += 1
    if test_string_in_file(f"{base_path}/templates/index.html", 
                           'id="train-model-modal"', 
                           "Train model modal added"):
        tests_passed += 1
    
    # Test 4: Check terminology updates
    print("\n📝 Terminology Tests:")
    
    # Check footer link update
    total_tests += 1
    if test_string_in_file(f"{base_path}/templates/index.html", 
                           "Predictive Analytics", 
                           "Footer updated to Predictive Analytics"):
        tests_passed += 1
    
    # Test 5: Check backend integration
    print("\n🖥️ Backend Tests:")
    
    # Check that /ml route is updated
    total_tests += 1
    if test_string_in_file(f"{base_path}/app.py", 
                           "ml_dashboard_redirect", 
                           "ML dashboard route updated for redirect"):
        tests_passed += 1
    
    # Summary
    print("\n" + "="*50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Integration successful.")
        return True
    else:
        print(f"⚠️ {total_tests - tests_passed} test(s) failed. Review above for details.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)