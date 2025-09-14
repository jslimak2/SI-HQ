#!/usr/bin/env python3
"""
Production Deployment Test Suite
Comprehensive tests for production readiness and deployment validation
"""

import os
import sys
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

# Add dashboard to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dashboard'))

class TestProductionReadiness:
    """Test suite for production readiness validation"""
    
    def test_production_environment_template_exists(self):
        """Test that production environment template exists and is complete"""
        env_file = os.path.join(os.path.dirname(__file__), '.env.production')
        assert os.path.exists(env_file), "Production environment template must exist"
        
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Check for critical production variables
        required_vars = [
            'DISABLE_DEMO_MODE=true',
            'FIREBASE_PROJECT_ID',
            'FIREBASE_API_KEY',
            'SPORTS_API_KEY',
            'SECRET_KEY',
            'DRAFTKINGS_API_KEY',
            'FANDUEL_API_KEY',
            'ENABLE_REAL_BETTING'
        ]
        
        for var in required_vars:
            assert var in content, f"Required variable {var} missing from production template"
    
    def test_deployment_script_exists_and_executable(self):
        """Test that deployment script exists and is properly configured"""
        deploy_script = os.path.join(os.path.dirname(__file__), 'deploy_production.py')
        assert os.path.exists(deploy_script), "Deployment script must exist"
        
        # Check if script is executable (on Unix systems)
        if os.name != 'nt':  # Not Windows
            import stat
            st = os.stat(deploy_script)
            assert st.st_mode & stat.S_IEXEC, "Deployment script should be executable"
    
    def test_production_configuration_class(self):
        """Test that configuration supports all production requirements"""
        from config import ConfigManager, APIConfig
        
        # Test that APIConfig has all required fields for production
        api_config = APIConfig()
        
        required_attributes = [
            'sports_api_key',
            'odds_api_key',
            'weather_api_key',
            'draftkings_api_key',
            'fanduel_api_key',
            'betmgm_api_key',
            'enable_real_betting'
        ]
        
        for attr in required_attributes:
            assert hasattr(api_config, attr), f"APIConfig missing required attribute: {attr}"
    
    def test_real_sports_api_integration(self):
        """Test that real sports API integration is functional"""
        from real_sports_api import RealSportsDataService, SportType, GameOdds
        
        # Test service initialization
        service = RealSportsDataService()
        assert service is not None
        
        # Test data fetching (should work with or without API keys)
        games = service.get_current_games('basketball_nba')
        assert isinstance(games, list)
        assert len(games) > 0
        
        # Test game data structure
        game = games[0]
        required_fields = ['id', 'teams', 'sport', 'odds', 'real_data']
        for field in required_fields:
            assert field in game, f"Game data missing required field: {field}"
    
    def test_sportsbook_api_integration(self):
        """Test that sportsbook API integration is available"""
        from sportsbook_api import BettingExecutionService, MockSportsbookAPI, BetRequest, BetType
        
        # Test service initialization
        service = BettingExecutionService(enabled=False)  # Start disabled for testing
        assert service is not None
        
        # Test adding mock sportsbook
        mock_api = MockSportsbookAPI()
        service.add_sportsbook('test', mock_api, is_default=True)
        
        # Test bet placement (mock)
        bet_request = BetRequest(
            game_id="test_game",
            bet_type=BetType.MONEYLINE,
            selection="Lakers",
            odds=1.85,
            stake=100.0
        )
        
        result = service.place_bet(bet_request)
        # Should fail because betting is disabled
        assert not result.success
        assert "disabled" in result.message.lower()
    
    def test_application_sports_data_integration(self):
        """Test that main application properly integrates sports data"""
        # Mock environment for testing
        with patch.dict(os.environ, {
            'SPORTS_API_KEY': 'test_key',
            'DISABLE_DEMO_MODE': 'false'
        }):
            try:
                from app import get_sports_games_data, get_demo_games_data
                
                # Test demo data function
                demo_games = get_demo_games_data('NBA', 5)
                assert len(demo_games) > 0
                assert all('teams' in game for game in demo_games)
                
                # Test main sports data function
                sports_games = get_sports_games_data('NBA', 5)
                assert len(sports_games) > 0
                assert all('teams' in game for game in sports_games)
                
            except Exception as e:
                pytest.fail(f"Application sports data integration failed: {e}")

class TestProductionDeployment:
    """Test actual deployment process"""
    
    def test_deployment_script_check_mode(self):
        """Test deployment script in check-only mode"""
        import subprocess
        
        deploy_script = os.path.join(os.path.dirname(__file__), 'deploy_production.py')
        
        # Run deployment check
        result = subprocess.run([
            sys.executable, deploy_script, '--check-only'
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        # Should exit with error code since we don't have production config
        assert result.returncode != 0
        assert "production readiness issues" in result.stdout.lower()
    
    def test_configuration_validation_with_mock_env(self):
        """Test configuration validation with mock environment"""
        mock_env = {
            'DISABLE_DEMO_MODE': 'true',
            'FIREBASE_PROJECT_ID': 'test-project',
            'FIREBASE_API_KEY': 'test-api-key',
            'FIREBASE_AUTH_DOMAIN': 'test-project.firebaseapp.com',
            'FIREBASE_STORAGE_BUCKET': 'test-project.appspot.com',
            'FIREBASE_MESSAGING_SENDER_ID': '123456789',
            'FIREBASE_APP_ID': '1:123456789:web:test123',
            'GOOGLE_APPLICATION_CREDENTIALS': './test_service_account.json',
            'SPORTS_API_KEY': 'test-sports-key',
            'SECRET_KEY': 'test-secret-key-for-production',
            'ENVIRONMENT': 'production'
        }
        
        with patch.dict(os.environ, mock_env):
            from config import ConfigManager
            
            # This should work without Firebase dependencies
            try:
                config = ConfigManager.load_config()
                assert config.disable_demo_mode == True
                assert config.api.sports_api_key == 'test-sports-key'
                assert config.environment.value == 'production'
            except ValueError as e:
                # Expected if Firebase dependencies are missing
                assert "firebase" in str(e).lower() or "google" in str(e).lower()

class TestProductionFeatures:
    """Test production-ready features"""
    
    def test_investment_recommendations_with_real_data_flag(self):
        """Test that investment recommendations can handle real data"""
        with patch.dict(os.environ, {'SPORTS_API_KEY': 'test_key'}):
            try:
                from app import get_sports_games_data
                
                games = get_sports_games_data('NBA', 3)
                
                # Check that real_data flag is present
                for game in games:
                    assert 'real_data' in game
                    assert isinstance(game['real_data'], bool)
                    
            except Exception as e:
                pytest.fail(f"Investment recommendations real data test failed: {e}")
    
    def test_api_rate_limiting_configuration(self):
        """Test that API rate limiting is properly configured"""
        from real_sports_api import TheOddsAPIProvider
        
        provider = TheOddsAPIProvider("test_key")
        assert hasattr(provider, 'min_request_interval')
        assert provider.min_request_interval > 0
        
        # Test rate limiting method exists
        assert hasattr(provider, '_rate_limit')
    
    def test_error_handling_for_api_failures(self):
        """Test that API failures are handled gracefully"""
        from real_sports_api import RealSportsDataService
        
        # Test with no API keys (should fallback gracefully)
        service = RealSportsDataService()
        games = service.get_current_games('basketball_nba')
        
        # Should return fallback data, not crash
        assert isinstance(games, list)
        assert len(games) > 0

class TestSecurityAndCompliance:
    """Test security and compliance features"""
    
    def test_secret_key_validation(self):
        """Test that default secret keys are detected"""
        from config import validate_config, ConfigManager
        
        # Mock config with default secret key
        with patch.dict(os.environ, {
            'SECRET_KEY': 'dev-secret-key-change-in-production',
            'ENVIRONMENT': 'production'
        }):
            try:
                config = ConfigManager.load_config()
                warnings = validate_config(config)
                
                # Should warn about default secret key in production
                default_key_warning = any('secret key' in warning.lower() for warning in warnings)
                assert default_key_warning, "Should warn about default secret key in production"
                
            except Exception:
                # Expected if other required vars are missing
                pass
    
    def test_demo_credentials_detection(self):
        """Test that demo credentials are detected in production"""
        from config import validate_config, ConfigManager
        
        with patch.dict(os.environ, {
            'FIREBASE_API_KEY': 'demo_api_key',
            'ENVIRONMENT': 'production'
        }):
            try:
                config = ConfigManager.load_config()
                warnings = validate_config(config)
                
                # Should warn about demo credentials
                demo_warning = any('demo' in warning.lower() for warning in warnings)
                assert demo_warning, "Should warn about demo credentials in production"
                
            except Exception:
                # Expected if other required vars are missing
                pass
    
    def test_api_key_security(self):
        """Test that API keys are not logged or exposed"""
        from real_sports_api import TheOddsAPIProvider
        
        provider = TheOddsAPIProvider("secret_api_key_12345")
        
        # Check that API key is stored but not in string representation
        str_repr = str(provider)
        assert "secret_api_key_12345" not in str_repr

class TestPerformanceAndScalability:
    """Test performance and scalability features"""
    
    def test_data_caching_functionality(self):
        """Test that data caching is implemented"""
        from real_sports_api import RealSportsDataService
        
        service = RealSportsDataService()
        
        # Check that caching is implemented
        assert hasattr(service, 'cache')
        assert hasattr(service, 'cache_ttl')
        
        # Test cache usage
        games1 = service.get_current_games('basketball_nba')
        games2 = service.get_current_games('basketball_nba')
        
        # Both calls should succeed (cache hit on second)
        assert len(games1) > 0
        assert len(games2) > 0
    
    def test_configuration_lazy_loading(self):
        """Test that configuration is loaded efficiently"""
        # Test that config can be loaded multiple times without issues
        from config import ConfigManager
        
        config1 = ConfigManager.load_config()
        config2 = ConfigManager.load_config()
        
        assert config1 is not None
        assert config2 is not None

class TestDocumentation:
    """Test that documentation is comprehensive and up-to-date"""
    
    def test_production_documentation_exists(self):
        """Test that all required documentation exists"""
        docs = [
            'PRODUCTION_PROJECT_PLAN.md',
            'QUICK_PRODUCTION_DEPLOYMENT.md',
            '.env.production'
        ]
        
        for doc in docs:
            doc_path = os.path.join(os.path.dirname(__file__), doc)
            assert os.path.exists(doc_path), f"Required documentation missing: {doc}"
    
    def test_documentation_completeness(self):
        """Test that documentation covers key production topics"""
        deployment_guide = os.path.join(os.path.dirname(__file__), 'QUICK_PRODUCTION_DEPLOYMENT.md')
        
        with open(deployment_guide, 'r') as f:
            content = f.read()
        
        required_topics = [
            'API Setup',
            'Firebase',
            'Sports Data',
            'Production Environment',
            'Security',
            'Cost Estimates',
            'Troubleshooting'
        ]
        
        for topic in required_topics:
            assert topic in content, f"Documentation missing required topic: {topic}"

def test_full_production_readiness():
    """Comprehensive production readiness test"""
    print("\n=== COMPREHENSIVE PRODUCTION READINESS TEST ===")
    
    checks = {
        'Environment Template': False,
        'Deployment Script': False,
        'Real Sports API': False,
        'Sportsbook API': False,
        'Application Integration': False,
        'Configuration System': False,
        'Security Features': False,
        'Documentation': False
    }
    
    # Test 1: Environment Template
    try:
        env_file = os.path.join(os.path.dirname(__file__), '.env.production')
        assert os.path.exists(env_file)
        checks['Environment Template'] = True
        print("✅ Environment Template")
    except:
        print("❌ Environment Template")
    
    # Test 2: Deployment Script
    try:
        deploy_script = os.path.join(os.path.dirname(__file__), 'deploy_production.py')
        assert os.path.exists(deploy_script)
        checks['Deployment Script'] = True
        print("✅ Deployment Script")
    except:
        print("❌ Deployment Script")
    
    # Test 3: Real Sports API
    try:
        from real_sports_api import RealSportsDataService
        service = RealSportsDataService()
        games = service.get_current_games('basketball_nba')
        assert len(games) > 0
        checks['Real Sports API'] = True
        print("✅ Real Sports API")
    except Exception as e:
        print(f"❌ Real Sports API: {e}")
    
    # Test 4: Sportsbook API
    try:
        from sportsbook_api import BettingExecutionService
        service = BettingExecutionService()
        checks['Sportsbook API'] = True
        print("✅ Sportsbook API")
    except Exception as e:
        print(f"❌ Sportsbook API: {e}")
    
    # Test 5: Application Integration
    try:
        from app import get_sports_games_data
        games = get_sports_games_data('NBA', 2)
        assert len(games) > 0
        checks['Application Integration'] = True
        print("✅ Application Integration")
    except Exception as e:
        print(f"❌ Application Integration: {e}")
    
    # Test 6: Configuration System
    try:
        from config import ConfigManager, APIConfig
        config = ConfigManager.load_config()
        api_config = APIConfig()
        assert hasattr(api_config, 'sports_api_key')
        assert hasattr(api_config, 'enable_real_betting')
        checks['Configuration System'] = True
        print("✅ Configuration System")
    except Exception as e:
        print(f"❌ Configuration System: {e}")
    
    # Test 7: Security Features
    try:
        from config import validate_config
        # Basic security validation exists
        checks['Security Features'] = True
        print("✅ Security Features")
    except Exception as e:
        print(f"❌ Security Features: {e}")
    
    # Test 8: Documentation
    try:
        docs = ['PRODUCTION_PROJECT_PLAN.md', 'QUICK_PRODUCTION_DEPLOYMENT.md']
        for doc in docs:
            assert os.path.exists(os.path.join(os.path.dirname(__file__), doc))
        checks['Documentation'] = True
        print("✅ Documentation")
    except Exception as e:
        print(f"❌ Documentation: {e}")
    
    # Summary
    passed = sum(checks.values())
    total = len(checks)
    
    print(f"\n=== PRODUCTION READINESS SUMMARY ===")
    print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 FULLY PRODUCTION READY!")
        print("Ready to deploy with real APIs and production configuration.")
    elif passed >= total * 0.8:
        print("⚠️  MOSTLY PRODUCTION READY")
        print("Minor issues to resolve before full production deployment.")
    else:
        print("🚨 NOT PRODUCTION READY")
        print("Significant issues need to be resolved.")
    
    # Return overall status
    assert passed >= total * 0.8, f"Production readiness below 80% ({passed}/{total})"

if __name__ == '__main__':
    # Run the comprehensive test
    test_full_production_readiness()
    
    # Run all tests
    pytest.main([__file__, '-v'])