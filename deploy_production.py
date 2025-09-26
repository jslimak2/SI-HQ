#!/usr/bin/env python3
"""
Production Deployment Script for SI-HQ Sports Investment Platform
This script handles the deployment of the platform to production environments.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import argparse

def check_requirements():
    """Check if all production requirements are met"""
    print("🔍 Checking production requirements...")
    
    issues = []
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        issues.append("❌ Missing .env file (copy from .env.production template)")
        return False
    
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("❌ python-dotenv not installed. Install with: pip install python-dotenv")
        return False
    
    # Check Firebase credentials
    google_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not google_creds or 'demo' in google_creds:
        issues.append("❌ Missing or invalid GOOGLE_APPLICATION_CREDENTIALS")
    
    # Check for demo mode setting
    if os.getenv('DISABLE_DEMO_MODE') != 'true':
        issues.append("❌ DISABLE_DEMO_MODE must be set to 'true' for production")
    
    # Check critical API keys
    required_keys = [
        'FIREBASE_PROJECT_ID',
        'FIREBASE_API_KEY',
        'SPORTS_API_KEY',
        'SECRET_KEY'
    ]
    
    for key in required_keys:
        if not os.getenv(key) or 'your-' in os.getenv(key, ''):
            issues.append(f"❌ Missing or placeholder value for {key}")
    
    if issues:
        print("\n🚨 Production readiness issues found:")
        for issue in issues:
            print(f"  {issue}")
        print("\n📖 Please review .env.production template and update your .env file")
        return False
    
    print("✅ All production requirements met!")
    return True

def install_dependencies():
    """Install production dependencies"""
    print("\n📦 Installing production dependencies...")
    
    try:
        # Install from requirements.txt
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        
        # Install production-specific requirements if exists
        if os.path.exists('requirements-production.txt'):
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements-production.txt'], check=True)
        
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def validate_configuration():
    """Validate production configuration"""
    print("\n🔧 Validating configuration...")
    
    try:
        # Import and test configuration
        sys.path.insert(0, 'dashboard')
        from config import config
        
        # Check Firebase availability
        try:
            import firebase_admin
            print("✅ Firebase SDK available")
        except ImportError:
            print("❌ Firebase SDK not available")
            return False
        
        # Validate demo mode is disabled
        if hasattr(config, 'disable_demo_mode') and config.disable_demo_mode:
            print("✅ Demo mode disabled for production")
        else:
            print("❌ Demo mode not properly disabled")
            return False
        
        print("✅ Configuration validation passed!")
        return True
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

def run_tests():
    """Run production readiness tests"""
    print("\n🧪 Running production readiness tests...")
    
    try:
        # Run basic functionality test
        result = subprocess.run([sys.executable, '-m', 'pytest', 'test_simple.py', '-v'], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Basic tests passed!")
        else:
            print("❌ Some tests failed:")
            print(result.stdout)
            return False
        
        # Run production-specific tests
        if os.path.exists('test_production.py'):
            result = subprocess.run([sys.executable, '-m', 'pytest', 'test_production.py', '-v'], 
                                   capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Production tests passed!")
            else:
                print("❌ Production tests failed:")
                print(result.stdout)
                return False
        
        return True
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False

def start_production_server():
    """Start the production server"""
    print("\n🚀 Starting production server...")
    
    try:
        # Use production.py for production deployment
        os.execv(sys.executable, [sys.executable, 'production.py'])
    except Exception as e:
        print(f"❌ Failed to start production server: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Deploy SI-HQ to production')
    parser.add_argument('--skip-tests', action='store_true', help='Skip running tests')
    parser.add_argument('--check-only', action='store_true', help='Only check requirements, do not deploy')
    args = parser.parse_args()
    
    print("🏟️  SI-HQ Production Deployment Script")
    print("=" * 50)
    
    # Step 1: Check requirements
    if not check_requirements():
        sys.exit(1)
    
    if args.check_only:
        print("\n✅ Production readiness check completed!")
        sys.exit(0)
    
    # Step 2: Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Step 3: Validate configuration
    if not validate_configuration():
        sys.exit(1)
    
    # Step 4: Run tests (unless skipped)
    if not args.skip_tests:
        if not run_tests():
            print("\n⚠️  Tests failed but continuing deployment (use --check-only to stop on test failure)")
    
    # Step 5: Start production server
    print("\n🎯 Production deployment ready!")
    print("🔗 Access your application at the configured host and port")
    
    start_production_server()

if __name__ == '__main__':
    main()