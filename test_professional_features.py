#!/usr/bin/env python3
"""
Professional test suite for Post9 application
Tests all professional improvements including error handling, validation, security
"""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 0
        self.failures = []
    
    def add_test(self, name: str, passed: bool, message: str = ""):
        self.total += 1
        if passed:
            self.passed += 1
            print(f"✅ {name}")
        else:
            self.failed += 1
            self.failures.append((name, message))
            print(f"❌ {name}: {message}")
    
    def summary(self):
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{self.total} passed")
        print(f"Pass rate: {(self.passed/self.total)*100:.1f}%")
        
        if self.failures:
            print(f"\nFailures:")
            for name, message in self.failures:
                print(f"  - {name}: {message}")
        
        return self.failed == 0

def test_health_check(results: TestResult):
    """Test professional health check endpoint"""
    print("\n🏥 Testing Health Check...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check response structure
            results.add_test(
                "Health endpoint returns success",
                data.get('success') is True
            )
            
            health = data.get('health', {})
            results.add_test(
                "Health status is healthy",
                health.get('status') == 'healthy'
            )
            
            results.add_test(
                "Health includes environment info",
                'environment' in health and 'version' in health
            )
            
            results.add_test(
                "Health includes service status",
                'services' in health and isinstance(health['services'], dict)
            )
            
            results.add_test(
                "Health includes error stats",
                'error_stats' in health
            )
            
        else:
            results.add_test(
                "Health endpoint accessibility",
                False,
                f"HTTP {response.status_code}"
            )
            
    except Exception as e:
        results.add_test("Health endpoint connectivity", False, str(e))

def test_api_documentation(results: TestResult):
    """Test API documentation endpoint"""
    print("\n📚 Testing API Documentation...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/docs")
        
        if response.status_code == 200:
            data = response.json()
            
            results.add_test(
                "API docs endpoint accessible",
                True
            )
            
            results.add_test(
                "OpenAPI spec structure",
                'openapi' in data and 'info' in data and 'paths' in data
            )
            
            results.add_test(
                "API docs include paths",
                len(data.get('paths', {})) > 0
            )
            
        else:
            results.add_test(
                "API docs accessibility",
                False,
                f"HTTP {response.status_code}"
            )
            
    except Exception as e:
        results.add_test("API docs connectivity", False, str(e))

def test_error_handling(results: TestResult):
    """Test professional error handling"""
    print("\n🚨 Testing Error Handling...")
    
    # Test validation error
    try:
        response = requests.post(f"{BASE_URL}/api/ml/basic/train", 
                               json={"sport": "INVALID_SPORT"},
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 400:
            data = response.json()
            
            results.add_test(
                "Validation error returns 400",
                True
            )
            
            results.add_test(
                "Error response has proper structure",
                'success' in data and data['success'] is False and 'error' in data
            )
            
            error = data.get('error', {})
            results.add_test(
                "Error includes code and message",
                'code' in error and 'message' in error
            )
            
            results.add_test(
                "Error includes timestamp and ID",
                'timestamp' in error and 'error_id' in error
            )
            
        else:
            results.add_test(
                "Validation error handling",
                False,
                f"Expected 400, got {response.status_code}"
            )
            
    except Exception as e:
        results.add_test("Error handling test", False, str(e))

def test_input_validation(results: TestResult):
    """Test input validation and sanitization"""
    print("\n🔍 Testing Input Validation...")
    
    # Test required field validation
    try:
        response = requests.post(f"{BASE_URL}/api/ml/basic/train",
                               json={},  # Missing required fields
                               headers={'Content-Type': 'application/json'})
        
        results.add_test(
            "Missing required fields rejected",
            response.status_code == 400
        )
        
    except Exception as e:
        results.add_test("Required field validation test", False, str(e))
    
    # Test invalid data types
    try:
        response = requests.post(f"{BASE_URL}/api/ml/basic/train",
                               json={
                                   "sport": "NBA",
                                   "num_samples": "invalid_number"
                               },
                               headers={'Content-Type': 'application/json'})
        
        results.add_test(
            "Invalid data types rejected",
            response.status_code == 400
        )
        
    except Exception as e:
        results.add_test("Data type validation test", False, str(e))

def test_authentication_system(results: TestResult):
    """Test authentication and authorization"""
    print("\n🔐 Testing Authentication...")
    
    # Test endpoint without authentication (should work in demo mode)
    try:
        response = requests.get(f"{BASE_URL}/api/models/gallery")
        
        results.add_test(
            "Public endpoints accessible",
            response.status_code == 200
        )
        
    except Exception as e:
        results.add_test("Public endpoint access test", False, str(e))
    
    # Test that authentication headers are processed (demo mode allows through)
    try:
        headers = {
            'X-API-Key': 'demo_api_key',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(f"{BASE_URL}/api/ml/basic/train",
                               json={"sport": "NBA", "num_samples": 500},
                               headers=headers)
        
        results.add_test(
            "API key header processed",
            response.status_code in [200, 400]  # Either success or validation error, not auth error
        )
        
    except Exception as e:
        results.add_test("API key processing test", False, str(e))

def test_security_headers(results: TestResult):
    """Test security headers in responses"""
    print("\n🛡️  Testing Security Headers...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'X-Request-ID': True  # Should exist
        }
        
        for header, expected_value in security_headers.items():
            if expected_value is True:
                results.add_test(
                    f"Security header {header} present",
                    header in response.headers
                )
            else:
                results.add_test(
                    f"Security header {header} correct",
                    response.headers.get(header) == expected_value
                )
                
    except Exception as e:
        results.add_test("Security headers test", False, str(e))

def test_request_tracking(results: TestResult):
    """Test request tracking and logging"""
    print("\n📝 Testing Request Tracking...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        
        results.add_test(
            "Request ID in response headers",
            'X-Request-ID' in response.headers
        )
        
        # Make multiple requests to test unique IDs
        response1 = requests.get(f"{BASE_URL}/api/health")
        response2 = requests.get(f"{BASE_URL}/api/health")
        
        id1 = response1.headers.get('X-Request-ID')
        id2 = response2.headers.get('X-Request-ID')
        
        results.add_test(
            "Request IDs are unique",
            id1 != id2 and id1 is not None and id2 is not None
        )
        
    except Exception as e:
        results.add_test("Request tracking test", False, str(e))

def test_ml_training_with_validation(results: TestResult):
    """Test ML training with professional validation"""
    print("\n🧠 Testing ML Training Validation...")
    
    # Test valid training request
    try:
        response = requests.post(f"{BASE_URL}/api/ml/basic/train",
                               json={
                                   "sport": "NBA",
                                   "num_samples": 500,
                                   "user_id": "test_user"
                               },
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            
            results.add_test(
                "Valid ML training request succeeds",
                data.get('success') is True
            )
            
            training_results = data.get('training_results', {})
            results.add_test(
                "Training results include duration",
                'training_duration_seconds' in training_results
            )
            
            results.add_test(
                "Training results include metadata",
                'trained_at' in data and 'model_version' in data
            )
            
        else:
            results.add_test(
                "Valid ML training request",
                False,
                f"HTTP {response.status_code}: {response.text}"
            )
            
    except Exception as e:
        results.add_test("ML training validation test", False, str(e))
    
    # Test invalid training parameters
    try:
        response = requests.post(f"{BASE_URL}/api/ml/basic/train",
                               json={
                                   "sport": "NBA", 
                                   "num_samples": 50000  # Too many samples
                               },
                               headers={'Content-Type': 'application/json'})
        
        results.add_test(
            "Invalid training parameters rejected",
            response.status_code == 400
        )
        
    except Exception as e:
        results.add_test("ML training parameter validation test", False, str(e))

def test_configuration_system(results: TestResult):
    """Test configuration management"""
    print("\n⚙️  Testing Configuration System...")
    
    # Test that configuration is loaded properly (check through health endpoint)
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        
        if response.status_code == 200:
            data = response.json()
            health = data.get('health', {})
            
            results.add_test(
                "Environment configuration loaded",
                'environment' in health
            )
            
            results.add_test(
                "Service configuration available", 
                'services' in health and len(health['services']) > 0
            )
            
        else:
            results.add_test("Configuration test via health endpoint", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        results.add_test("Configuration system test", False, str(e))

def main():
    print("🚀 Post9 Professional Features Test Suite")
    print("=" * 60)
    
    # Check connectivity
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("❌ Cannot connect to Post9 server. Make sure it's running on port 5000.")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Post9 server. Make sure it's running on port 5000.")
        return False
    
    print("✅ Connected to Post9 server")
    
    results = TestResult()
    
    # Run all test suites
    test_health_check(results)
    test_api_documentation(results)
    test_error_handling(results)
    test_input_validation(results)
    test_authentication_system(results)
    test_security_headers(results)
    test_request_tracking(results)
    test_ml_training_with_validation(results)
    test_configuration_system(results)
    
    # Print summary
    success = results.summary()
    
    if success:
        print("\n🎉 All professional features are working correctly!")
        print("\n📱 Enhanced interfaces available at:")
        print(f"   Main Dashboard: {BASE_URL}/")
        print(f"   ML Dashboard:   {BASE_URL}/ml")
        print(f"   API Docs:       {BASE_URL}/api/docs")
        print(f"   Health Check:   {BASE_URL}/api/health")
    else:
        print(f"\n⚠️  {results.failed} test(s) failed. Check the output above for details.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)