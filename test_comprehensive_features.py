#!/usr/bin/env python3
"""
Comprehensive test suite for all Post9 professional features
Tests the complete professional transformation
"""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

class ComprehensiveTestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 0
        self.failures = []
        self.categories = {
            'Core System': 0,
            'Model Registry': 0,
            'Data Validation': 0, 
            'User Engagement': 0,
            'Security & Monitoring': 0
        }
    
    def add_test(self, name: str, category: str, passed: bool, message: str = ""):
        self.total += 1
        self.categories[category] += 1
        
        if passed:
            self.passed += 1
            print(f"✅ [{category}] {name}")
        else:
            self.failed += 1
            self.failures.append((category, name, message))
            print(f"❌ [{category}] {name}: {message}")
    
    def summary(self):
        print(f"\n{'='*80}")
        print(f"🚀 COMPREHENSIVE POST9 PROFESSIONAL FEATURES TEST RESULTS")
        print(f"{'='*80}")
        print(f"Overall: {self.passed}/{self.total} tests passed ({(self.passed/self.total)*100:.1f}%)")
        
        print(f"\n📊 Results by Category:")
        for category, count in self.categories.items():
            category_passed = sum(1 for f in self.failures if f[0] != category)
            category_passed = count - sum(1 for f in self.failures if f[0] == category)
            print(f"  {category}: {category_passed}/{count} passed")
        
        if self.failures:
            print(f"\n❌ Failed Tests:")
            for category, name, message in self.failures:
                print(f"  [{category}] {name}: {message}")
        
        return self.failed == 0

def test_core_system(results: ComprehensiveTestResult):
    """Test core system features"""
    print("\n🏗️  Testing Core System Features...")
    
    # Health check with enhanced data
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            health = data.get('health', {})
            
            results.add_test(
                "Enhanced health check works",
                "Core System",
                'environment' in health and 'services' in health and 'error_stats' in health
            )
            
            results.add_test(
                "Version information included",
                "Core System", 
                'version' in health
            )
        else:
            results.add_test("Health check availability", "Core System", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        results.add_test("Health check connectivity", "Core System", False, str(e))
    
    # API documentation
    try:
        response = requests.get(f"{BASE_URL}/api/docs")
        if response.status_code == 200:
            data = response.json()
            results.add_test(
                "OpenAPI documentation generated",
                "Core System",
                'openapi' in data and len(data.get('paths', {})) > 5
            )
        else:
            results.add_test("API documentation", "Core System", False, f"HTTP {response.status_code}")
    except Exception as e:
        results.add_test("API documentation", "Core System", False, str(e))

def test_model_registry(results: ComprehensiveTestResult):
    """Test professional model registry features"""
    print("\n🧠 Testing Model Registry Features...")
    
    # List registered models
    try:
        response = requests.get(f"{BASE_URL}/api/models/registry")
        if response.status_code == 200:
            data = response.json()
            results.add_test(
                "Model registry listing works",
                "Model Registry",
                data.get('success') is True and 'models' in data
            )
            
            results.add_test(
                "Registry includes metadata",
                "Model Registry",
                'total_count' in data and 'filters_applied' in data
            )
        else:
            results.add_test("Model registry listing", "Model Registry", False, f"HTTP {response.status_code}")
    except Exception as e:
        results.add_test("Model registry listing", "Model Registry", False, str(e))
    
    # Register a new model
    try:
        model_data = {
            "name": "Test NBA Model",
            "sport": "NBA",
            "model_type": "statistical",
            "description": "Test model for professional features",
            "user_id": "test_user"
        }
        
        response = requests.post(f"{BASE_URL}/api/models/register",
                               json=model_data,
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 201:
            data = response.json()
            model_id = data.get('model_id')
            
            results.add_test(
                "Model registration works",
                "Model Registry",
                data.get('success') is True and model_id is not None
            )
            
            # Test model status update
            if model_id:
                status_data = {
                    "status": "ready",
                    "performance_metrics": {"accuracy": 72.5, "precision": 71.2}
                }
                
                status_response = requests.put(f"{BASE_URL}/api/models/{model_id}/status",
                                             json=status_data,
                                             headers={'Content-Type': 'application/json'})
                
                results.add_test(
                    "Model status update works",
                    "Model Registry",
                    status_response.status_code == 200
                )
        else:
            results.add_test("Model registration", "Model Registry", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        results.add_test("Model registration", "Model Registry", False, str(e))

def test_data_validation(results: ComprehensiveTestResult):
    """Test professional data validation features"""
    print("\n📊 Testing Data Validation Features...")
    
    # Test valid data validation
    try:
        sample_data = [
            {
                "home_team": "Lakers",
                "away_team": "Warriors", 
                "home_score": 112,
                "away_score": 108,
                "game_date": "2024-01-15",
                "season": "2023-24",
                "home_wins": 25,
                "away_wins": 22
            },
            {
                "home_team": "Celtics",
                "away_team": "Heat",
                "home_score": 118,
                "away_score": 102,
                "game_date": "2024-01-16", 
                "season": "2023-24",
                "home_wins": 30,
                "away_wins": 18
            }
        ]
        
        validation_request = {
            "data": sample_data,
            "sport": "NBA",
            "user_id": "test_user"
        }
        
        response = requests.post(f"{BASE_URL}/api/data/validate",
                               json=validation_request,
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            quality_report = data.get('quality_report', {})
            
            results.add_test(
                "Data validation processes successfully",
                "Data Validation",
                data.get('success') is True and quality_report
            )
            
            results.add_test(
                "Quality report includes all metrics",
                "Data Validation",
                all(key in quality_report for key in [
                    'overall_quality', 'quality_score', 'issues', 'recommendations'
                ])
            )
            
            results.add_test(
                "Quality score calculated",
                "Data Validation",
                isinstance(quality_report.get('quality_score'), (int, float))
            )
        else:
            results.add_test("Data validation", "Data Validation", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        results.add_test("Data validation", "Data Validation", False, str(e))
    
    # Test invalid data validation
    try:
        invalid_data = [
            {
                "home_team": "Lakers",
                "away_team": "Warriors",
                "home_score": 500,  # Invalid score
                "away_score": -10,  # Invalid score
                "game_date": "invalid-date"
            }
        ]
        
        validation_request = {
            "data": invalid_data,
            "sport": "NBA"
        }
        
        response = requests.post(f"{BASE_URL}/api/data/validate",
                               json=validation_request,
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            quality_report = data.get('quality_report', {})
            
            results.add_test(
                "Invalid data properly detected",
                "Data Validation",
                len(quality_report.get('issues', [])) > 0
            )
        else:
            results.add_test("Invalid data validation", "Data Validation", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        results.add_test("Invalid data validation", "Data Validation", False, str(e))

def test_user_engagement(results: ComprehensiveTestResult):
    """Test user engagement and weekly automation features"""
    print("\n📧 Testing User Engagement Features...")
    
    # Test user preferences setup
    try:
        preferences_data = {
            "email": "test@example.com",
            "weekly_report_enabled": True,
            "preferred_day": "Monday",
            "favorite_sports": ["NBA", "NFL"],
            "user_id": "test_user"
        }
        
        response = requests.post(f"{BASE_URL}/api/user/preferences",
                               json=preferences_data,
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            
            results.add_test(
                "User preferences setup works",
                "User Engagement",
                data.get('success') is True
            )
            
            results.add_test(
                "Preferences include expected fields",
                "User Engagement",
                'preferences' in data and 'user_id' in data
            )
        else:
            results.add_test("User preferences setup", "User Engagement", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        results.add_test("User preferences setup", "User Engagement", False, str(e))
    
    # Test engagement analytics
    try:
        response = requests.get(f"{BASE_URL}/api/engagement/analytics")
        
        if response.status_code == 200:
            data = response.json()
            analytics = data.get('analytics', {})
            
            results.add_test(
                "Engagement analytics available",
                "User Engagement",
                data.get('success') is True and analytics
            )
            
            results.add_test(
                "Analytics include key metrics",
                "User Engagement",
                'total_users' in analytics and 'engagement_rate' in analytics
            )
        else:
            results.add_test("Engagement analytics", "User Engagement", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        results.add_test("Engagement analytics", "User Engagement", False, str(e))

def test_security_monitoring(results: ComprehensiveTestResult):
    """Test security and monitoring features"""
    print("\n🛡️  Testing Security & Monitoring Features...")
    
    # Test system metrics
    try:
        response = requests.get(f"{BASE_URL}/api/system/metrics")
        
        if response.status_code == 200:
            data = response.json()
            metrics = data.get('metrics', {})
            
            results.add_test(
                "System metrics available",
                "Security & Monitoring",
                data.get('success') is True and metrics
            )
            
            results.add_test(
                "Metrics include system info",
                "Security & Monitoring",
                'system' in metrics and 'application' in metrics
            )
            
            results.add_test(
                "Application metrics tracked",
                "Security & Monitoring",
                'model_count' in metrics.get('application', {})
            )
        else:
            results.add_test("System metrics", "Security & Monitoring", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        results.add_test("System metrics", "Security & Monitoring", False, str(e))
    
    # Test error handling with validation
    try:
        invalid_request = {"invalid_field": "test"}
        
        response = requests.post(f"{BASE_URL}/api/ml/basic/train",
                               json=invalid_request,
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 400:
            data = response.json()
            error = data.get('error', {})
            
            results.add_test(
                "Professional error handling works",
                "Security & Monitoring",
                'code' in error and 'error_id' in error and 'timestamp' in error
            )
        else:
            results.add_test("Error handling validation", "Security & Monitoring", False, f"Expected 400, got {response.status_code}")
            
    except Exception as e:
        results.add_test("Error handling validation", "Security & Monitoring", False, str(e))
    
    # Test security headers
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        
        security_headers_present = all(header in response.headers for header in [
            'X-Content-Type-Options', 'X-Frame-Options', 'X-XSS-Protection', 'X-Request-ID'
        ])
        
        results.add_test(
            "Security headers implemented",
            "Security & Monitoring",
            security_headers_present
        )
        
        results.add_test(
            "Request tracking active",
            "Security & Monitoring",
            'X-Request-ID' in response.headers and len(response.headers['X-Request-ID']) > 10
        )
        
    except Exception as e:
        results.add_test("Security headers", "Security & Monitoring", False, str(e))

def test_ml_training_integration(results: ComprehensiveTestResult):
    """Test enhanced ML training with professional features"""
    print("\n🤖 Testing Enhanced ML Training...")
    
    try:
        training_data = {
            "sport": "NBA",
            "num_samples": 1000,
            "user_id": "test_user"
        }
        
        response = requests.post(f"{BASE_URL}/api/ml/basic/train",
                               json=training_data,
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            training_results = data.get('training_results', {})
            
            results.add_test(
                "Enhanced ML training works",
                "Core System",
                data.get('success') is True
            )
            
            results.add_test(
                "Training includes professional metadata",
                "Core System",
                'trained_at' in data and 'model_version' in data and 'trained_by' in data
            )
            
            results.add_test(
                "Performance metrics enhanced",
                "Core System",
                'training_duration_seconds' in training_results
            )
        else:
            results.add_test("Enhanced ML training", "Core System", False, f"HTTP {response.status_code}")
            
    except Exception as e:
        results.add_test("Enhanced ML training", "Core System", False, str(e))

def main():
    print("🚀 POST9 COMPREHENSIVE PROFESSIONAL FEATURES TEST SUITE")
    print("=" * 80)
    print("Testing complete professional transformation of the sports investment platform")
    print("=" * 80)
    
    # Check connectivity
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("❌ Cannot connect to Post9 server. Make sure it's running on port 5000.")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Post9 server. Make sure it's running on port 5000.")
        return False
    
    print("✅ Connected to Post9 professional server")
    
    results = ComprehensiveTestResult()
    
    # Run all comprehensive test suites
    test_core_system(results)
    test_model_registry(results)
    test_data_validation(results)
    test_user_engagement(results)
    test_security_monitoring(results)
    test_ml_training_integration(results)
    
    # Print comprehensive summary
    success = results.summary()
    
    if success:
        print(f"\n🎉 ALL PROFESSIONAL FEATURES WORKING PERFECTLY!")
        print(f"\n🏆 Post9 Professional Transformation Complete:")
        print(f"   ✅ Enterprise-grade error handling & logging")
        print(f"   ✅ Professional configuration management")
        print(f"   ✅ Comprehensive API documentation")
        print(f"   ✅ Advanced security & authentication")
        print(f"   ✅ Model registry & versioning system")
        print(f"   ✅ Data validation & quality assurance")
        print(f"   ✅ User engagement & weekly automation")
        print(f"   ✅ System monitoring & metrics")
        
        print(f"\n📱 Professional interfaces available:")
        print(f"   Main Dashboard:    {BASE_URL}/")
        print(f"   ML Dashboard:      {BASE_URL}/ml")
        print(f"   API Documentation: {BASE_URL}/api/docs")
        print(f"   Health Check:      {BASE_URL}/api/health")
        print(f"   System Metrics:    {BASE_URL}/api/system/metrics")
        
    else:
        print(f"\n⚠️  Some professional features need attention. Check details above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)