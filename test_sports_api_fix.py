#!/usr/bin/env python3
"""
Test script to directly test the SportType enum fix
"""
import sys
sys.path.insert(0, 'dashboard')

from real_sports_api import RealSportsDataService, SportType

def test_sport_normalization():
    """Test the sport name normalization fix"""
    service = RealSportsDataService()
    
    # Test cases that were causing the error
    test_cases = [
        'nfl',
        'nba',
        'NFL',
        'NBA',
        'basketball_nba',
        'americanfootball_nfl'
    ]
    
    print("Testing sport name normalization:")
    for sport in test_cases:
        try:
            normalized = service._normalize_sport_name(sport)
            print(f"  ✅ '{sport}' -> {normalized.value}")
        except Exception as e:
            print(f"  ❌ '{sport}' -> ERROR: {e}")
    
    print("\nTesting get_current_games method:")
    for sport in ['nfl', 'nba']:
        try:
            games = service.get_current_games(sport)
            print(f"  ✅ get_current_games('{sport}') -> {len(games)} games")
        except Exception as e:
            print(f"  ❌ get_current_games('{sport}') -> ERROR: {e}")

if __name__ == '__main__':
    test_sport_normalization()
