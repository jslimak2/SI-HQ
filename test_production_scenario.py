#!/usr/bin/env python3
"""
Test script to simulate the production scenario that was failing
"""
import sys
sys.path.insert(0, 'dashboard')

from real_sports_api import RealSportsDataService

def test_production_scenario():
    """Test the exact scenario that was failing in production"""
    
    # Simulate having a sports API key (fake one)
    service = RealSportsDataService(odds_api_key="fake_key_for_testing")
    
    print("Testing production scenario (the one causing errors):")
    print("This simulates what happens when generate_real_bot_recommendations is called")
    
    # Test the exact sports that were causing errors
    sports_to_test = ['NFL', 'NBA']
    
    for sport in sports_to_test:
        print(f"\n�� Testing sport: {sport}")
        try:
            # This is the exact call from generate_real_bot_recommendations -> get_sports_games_data
            games = service.get_current_games(sport)  # This was getting sport.lower() before our fix
            print(f"  ✅ SUCCESS: Retrieved {len(games)} games for {sport}")
            
            # Show a sample game to verify data structure
            if games:
                sample_game = games[0]
                print(f"  📊 Sample game: {sample_game.get('teams', 'N/A')}")
                print(f"  📊 Real data flag: {sample_game.get('real_data', 'N/A')}")
                print(f"  📊 Sport field: {sample_game.get('sport', 'N/A')}")
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            
    print("\n" + "="*60)
    print("✅ Fix validation complete!")
    print("The original error 'is not a valid SportType' should be resolved.")

if __name__ == '__main__':
    test_production_scenario()
