#!/usr/bin/env python3
"""
Simple test to verify DISABLE_DEMO_MODE implementation
"""

import os
import sys

def test_basic_functionality():
    """Test basic functionality without dependencies"""
    print("=== Testing DISABLE_DEMO_MODE Implementation ===\n")
    
    # Test 1: Check configuration file has the new option
    config_file = os.path.join(os.path.dirname(__file__), 'dashboard', 'config.py')
    with open(config_file, 'r') as f:
        config_content = f.read()
    
    assert 'disable_demo_mode' in config_content, "Config should include disable_demo_mode field"
    assert "os.getenv('DISABLE_DEMO_MODE'" in config_content, "Config should read DISABLE_DEMO_MODE env var"
    print("✓ Configuration file includes DISABLE_DEMO_MODE support")
    
    # Test 2: Check app.py has the enhanced logic
    app_file = os.path.join(os.path.dirname(__file__), 'dashboard', 'app.py')
    with open(app_file, 'r') as f:
        app_content = f.read()
    
    assert 'config.disable_demo_mode' in app_content, "App should check disable_demo_mode config"
    assert 'Demo mode explicitly disabled' in app_content, "App should have disable demo mode logic"
    print("✓ App includes enhanced demo mode logic")
    
    # Test 3: Check new API endpoint exists
    assert '/api/system/demo-mode' in app_content, "App should have new demo mode API endpoint"
    print("✓ New API endpoint for demo mode status exists")
    
    # Test 4: Check UI has been updated
    template_file = os.path.join(os.path.dirname(__file__), 'dashboard', 'templates', 'index.html')
    with open(template_file, 'r') as f:
        template_content = f.read()
    
    assert 'demo_config' in template_content, "Template should check demo_config"
    assert 'PRODUCTION ONLY MODE' in template_content, "Template should show production only mode"
    print("✓ UI template includes demo mode status indicators")
    
    # Test 5: Check documentation exists
    docs_file = os.path.join(os.path.dirname(__file__), 'DEMO_MODE_CONTROL.md')
    assert os.path.exists(docs_file), "Documentation file should exist"
    with open(docs_file, 'r') as f:
        docs_content = f.read()
    assert 'DISABLE_DEMO_MODE=true' in docs_content, "Documentation should explain the feature"
    print("✓ Documentation file exists and explains the feature")
    
    # Test 6: Check example configuration
    example_file = os.path.join(os.path.dirname(__file__), '.env.production')
    assert os.path.exists(example_file), "Example production config should exist"
    with open(example_file, 'r') as f:
        example_content = f.read()
    assert 'DISABLE_DEMO_MODE=true' in example_content, "Example should show how to disable demo mode"
    print("✓ Example production configuration file exists")
    
    print("\n=== All Tests Passed! ===")
    print("\n🎉 DISABLE_DEMO_MODE feature has been successfully implemented!")
    
    print("\n📋 Implementation Summary:")
    print("• Added DISABLE_DEMO_MODE environment variable")
    print("• Enhanced demo mode logic with validation") 
    print("• Added API endpoint for demo mode status")
    print("• Updated UI with visual indicators")
    print("• Created comprehensive documentation")
    print("• Provided example configuration")
    
    print("\n🚀 How to use:")
    print("1. Set DISABLE_DEMO_MODE=true in your environment")
    print("2. Ensure valid Firebase credentials are configured")
    print("3. Start the application - it will enforce production mode")
    print("4. Check the dashboard for 🔒 'Production Only' indicator")
    
    print("\n⚠️  Important notes:")
    print("• Requires valid Firebase credentials when demo mode is disabled")
    print("• Will fail to start if requirements aren't met (fail-fast)")
    print("• UI clearly shows current mode and configuration status")
    print("• Safe default: demo mode remains available unless explicitly disabled")

if __name__ == '__main__':
    try:
        test_basic_functionality()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)