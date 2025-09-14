#!/usr/bin/env python3
"""
Test Real Sports API Integration
Tests the integration between the real sports API and the application
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add dashboard to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dashboard'))

def test_real_sports_api_import():
    """Test that real sports API module can be imported"""
    try:
        from real_sports_api import RealSportsDataService, SportType, GameOdds
        assert True, "Real sports API imported successfully"
    except ImportError as e:
        pytest.fail(f"Failed to import real sports API: {e}")

def test_sports_data_service_initialization():
    """Test that sports data service can be initialized"""
    from real_sports_api import RealSportsDataService
    
    # Test with no API keys (should work for demo mode)
    service = RealSportsDataService()
    assert service is not None
    
    # Test with mock API keys
    service_with_keys = RealSportsDataService(
        odds_api_key="test_odds_key",
        espn_api_key="test_espn_key"
    )
    assert service_with_keys is not None
    assert service_with_keys.odds_provider is not None

def test_game_odds_dataclass():
    """Test GameOdds dataclass functionality"""
    from real_sports_api import GameOdds
    
    game = GameOdds(
        home_team="Lakers",
        away_team="Warriors",
        home_odds=1.85,
        away_odds=2.10,
        over_under=215.5,
        over_odds=1.90,
        under_odds=1.90,
        game_time=datetime.now(),
        sport="NBA",
        sportsbook="test"
    )
    
    assert game.home_team == "Lakers"
    assert game.away_team == "Warriors"
    assert game.home_odds == 1.85
    assert game.over_under == 215.5

@patch('requests.Session.get')
def test_the_odds_api_provider_mock(mock_get):
    """Test The Odds API provider with mocked response"""
    from real_sports_api import TheOddsAPIProvider, SportType
    
    # Mock API response
    mock_response = Mock()
    mock_response.json.return_value = [
        {
            'id': 'test_game_1',
            'home_team': 'Lakers',
            'away_team': 'Warriors',
            'commence_time': '2024-01-15T20:00:00Z',
            'bookmakers': [
                {
                    'title': 'DraftKings',
                    'markets': [
                        {
                            'key': 'h2h',
                            'outcomes': [
                                {'name': 'Lakers', 'price': 1.85},
                                {'name': 'Warriors', 'price': 2.10}
                            ]
                        },
                        {
                            'key': 'totals',
                            'outcomes': [
                                {'name': 'Over', 'price': 1.90, 'point': 215.5},
                                {'name': 'Under', 'price': 1.90, 'point': 215.5}
                            ]
                        }
                    ]
                }
            ]
        }
    ]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    # Test the provider
    provider = TheOddsAPIProvider("test_api_key")
    games = provider.get_games(SportType.NBA)
    
    assert len(games) == 1
    assert games[0].home_team == "Lakers"
    assert games[0].away_team == "Warriors"
    assert games[0].home_odds == 1.85

def test_sports_data_service_get_current_games():
    """Test the main sports data service get_current_games method"""
    from real_sports_api import RealSportsDataService
    
    # Test with no API keys (should return fallback data)
    service = RealSportsDataService()
    games = service.get_current_games('basketball_nba')
    
    assert isinstance(games, list)
    assert len(games) > 0
    
    # Check game structure
    game = games[0]
    required_fields = ['id', 'teams', 'sport', 'odds', 'real_data']
    for field in required_fields:
        assert field in game, f"Missing required field: {field}"

def test_api_connection_validation():
    """Test API connection validation"""
    from real_sports_api import RealSportsDataService
    
    service = RealSportsDataService()
    status = service.validate_api_connection()
    
    assert isinstance(status, dict)
    assert 'odds_api' in status
    assert 'results_api' in status
    assert 'overall' in status
    assert isinstance(status['overall'], bool)

def test_app_integration_with_sports_api():
    """Test that the main app can integrate with sports API"""
    # Mock environment variables
    with patch.dict(os.environ, {
        'SPORTS_API_KEY': 'test_key',
        'DISABLE_DEMO_MODE': 'false'
    }):
        try:
            # Import after setting environment
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dashboard'))
            from real_sports_api import initialize_real_sports_service, get_real_sports_service
            
            # Initialize service
            service = initialize_real_sports_service(odds_api_key='test_key')
            assert service is not None
            
            # Get service instance
            service_instance = get_real_sports_service()
            assert service_instance is not None
            
        except Exception as e:
            pytest.fail(f"App integration failed: {e}")

def test_emergency_fallback_data():
    """Test emergency fallback data functionality"""
    from real_sports_api import RealSportsDataService
    
    service = RealSportsDataService()
    fallback_data = service._get_emergency_fallback_data()
    
    assert isinstance(fallback_data, list)
    assert len(fallback_data) > 0
    
    game = fallback_data[0]
    assert 'teams' in game
    assert 'odds' in game
    assert game['real_data'] == False

def test_configuration_integration():
    """Test integration with configuration system"""
    # Test that config can handle new API fields
    with patch.dict(os.environ, {
        'SPORTS_API_KEY': 'test_sports_key',
        'ODDS_API_KEY': 'test_odds_key',
        'WEATHER_API_KEY': 'test_weather_key',
        'DRAFTKINGS_API_KEY': 'test_dk_key',
        'ENABLE_REAL_BETTING': 'true'
    }):
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dashboard'))
            from config import ConfigManager
            
            config = ConfigManager.load_config()
            
            assert config.api.sports_api_key == 'test_sports_key'
            assert config.api.odds_api_key == 'test_odds_key'
            assert config.api.weather_api_key == 'test_weather_key'
            assert config.api.draftkings_api_key == 'test_dk_key'
            assert config.api.enable_real_betting == True
            
        except Exception as e:
            pytest.fail(f"Configuration integration failed: {e}")

def test_production_readiness_check():
    """Test production readiness validation"""
    print("=== Testing Production Readiness ===")
    
    # Test 1: Real Sports API module exists and works
    try:
        from real_sports_api import RealSportsDataService
        service = RealSportsDataService()
        print("✓ Real Sports API module functional")
    except Exception as e:
        pytest.fail(f"Real Sports API not functional: {e}")
    
    # Test 2: App can handle sports API integration
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dashboard'))
        # Check if app has sports data helper functions
        from app import get_sports_games_data, get_demo_games_data
        
        # Test demo data (should always work)
        demo_games = get_demo_games_data('NBA', 5)
        assert len(demo_games) > 0
        print("✓ Demo games data functional")
        
        # Test sports games data function
        sports_games = get_sports_games_data('NBA', 5)
        assert len(sports_games) > 0
        print("✓ Sports games data function works")
        
    except Exception as e:
        pytest.fail(f"App sports integration not functional: {e}")
    
    # Test 3: Configuration supports all required fields
    try:
        from config import ConfigManager
        config = ConfigManager.load_config()
        
        # Check if config has new API fields
        assert hasattr(config.api, 'sports_api_key')
        assert hasattr(config.api, 'odds_api_key')
        assert hasattr(config.api, 'enable_real_betting')
        print("✓ Configuration supports production API fields")
        
    except Exception as e:
        pytest.fail(f"Configuration not production ready: {e}")
    
    print("✅ Production readiness tests passed!")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])