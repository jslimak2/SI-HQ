# betting_logic.py
"""
This module contains the core logic for simulating betting scenarios.
It now includes a function for running a full backtest simulation and Expected Value calculations.
"""
import random
import datetime
import math

def simulate_single_bet(bot_data):
    """
    Simulates a single bet using a simple probability model.

    Args:
        bot_data (dict): The dictionary containing a single bot's data.

    Returns:
        dict: A dictionary with the result of the bet simulation.
    """
    
    # A simple probability-based model. We'll use a fixed 52% win probability to simulate a slight edge.
    win_probability = 0.52 
    
    # A payout multiplier to represent odds. A 1.8x payout is common for sports bets.
    payout_multiplier = 1.8 
    
    # Generate mock teams for the receipt
    teams = [
        ("Steelhawks", "Wildcats"), ("Falcons", "Eagles"), 
        ("Ravens", "Hawks"), ("Lions", "Tigers"), 
        ("Bears", "Grizzlies")
    ]
    team1, team2 = random.choice(teams)
    
    # Calculate the bet amount based on the bot's configured bet percentage
    bet_amount = bot_data['current_balance'] * (bot_data['bet_percentage'] / 100)
    
    # Ensure there's enough balance to make the bet
    if bet_amount > bot_data['current_balance']:
        bet_amount = bot_data['current_balance']

    outcome = 'L'
    payout = -bet_amount
    
    # Simulate the outcome
    if random.random() < win_probability:
        outcome = 'W'
        payout = bet_amount * (payout_multiplier - 1)
        
    # Update the bot's balance
    bot_data['current_balance'] += payout
    
    # Generate a unique receipt for this bet
    bet_receipt = {
        'timestamp': datetime.datetime.now(),
        'teams': f"{team1} vs {team2}",
        'wager': bet_amount,
        'odds': payout_multiplier,
        'payout': payout,
        'outcome': outcome,
    }

    return bet_receipt

def simulate_real_world_bet(bot_data, num_bets):
    """
    Simulates a series of bets and generates a report.
    
    Args:
        bot_data (dict): The bot's configuration data.
        num_bets (int): The number of bets to simulate.

    Returns:
        dict: A report with simulation results.
    """
    
    initial_balance = bot_data['current_balance']
    bankroll_history = [{'bet_number': 0, 'balance': initial_balance}]
    current_balance = initial_balance
    total_wagered = 0.0
    total_profit = 0.0
    total_wins = 0
    total_losses = 0

    # Ensure we don't modify the original bot data during the simulation
    simulation_bot = bot_data.copy()
    simulation_bot['current_balance'] = initial_balance
    
    for i in range(num_bets):
        # Simulate a single bet and get the updated bot data
        bet_receipt = simulate_single_bet(simulation_bot)
        
        # Update our tracking variables
        total_wagered += bet_receipt['wager']
        total_profit += bet_receipt['payout']
        
        if bet_receipt['outcome'] == 'W':
            total_wins += 1
        else:
            total_losses += 1
            
        current_balance = simulation_bot['current_balance']
        bankroll_history.append({'bet_number': i + 1, 'balance': current_balance})
        
    win_rate = total_wins / num_bets if num_bets > 0 else 0
    
    # Final report
    report = {
        'initial_bankroll': initial_balance,
        'final_bankroll': current_balance,
        'total_profit': total_profit,
        'total_bets': num_bets,
        'total_wagered': total_wagered,
        'total_wins': total_wins,
        'total_losses': total_losses,
        'win_rate': win_rate,
        'bankroll_history': bankroll_history,
        'bets_history': [] # This is for the live bot, not simulation
    }

    return report

def calculate_implied_probability(odds):
    """
    Calculate implied probability from American odds.
    
    Args:
        odds (int): American odds (e.g. -110, +150)
        
    Returns:
        float: Implied probability (0.0 to 1.0)
    """
    if odds > 0:
        # Positive odds: implied_prob = 100 / (odds + 100)
        return 100 / (odds + 100)
    else:
        # Negative odds: implied_prob = abs(odds) / (abs(odds) + 100)
        return abs(odds) / (abs(odds) + 100)

def calculate_expected_value(true_prob, odds, bet_amount):
    """
    Calculate the expected value of a bet.
    
    Args:
        true_prob (float): True probability of winning (0.0 to 1.0)
        odds (int): American odds
        bet_amount (float): Amount to bet
        
    Returns:
        float: Expected value of the bet
    """
    if odds > 0:
        # Positive odds payout calculation
        win_amount = bet_amount * (odds / 100)
    else:
        # Negative odds payout calculation  
        win_amount = bet_amount * (100 / abs(odds))
    
    # EV = (probability of win * amount won) - (probability of loss * amount lost)
    ev = (true_prob * win_amount) - ((1 - true_prob) * bet_amount)
    return ev

def estimate_true_probability(game_data, market_type='moneyline'):
    """
    Estimate the true probability of an outcome.
    This is a simplified model - in production this would use complex ML models.
    
    Args:
        game_data (dict): Information about the game
        market_type (str): Type of bet (moneyline, spread, totals)
        
    Returns:
        float: Estimated true probability (0.0 to 1.0)
    """
    # This is a simplified model for demonstration
    # In a real system, this would analyze:
    # - Historical team performance
    # - Player injuries/status
    # - Weather conditions
    # - Home field advantage
    # - Recent form/momentum
    # - Head-to-head records
    
    base_probability = 0.5  # Start with 50/50
    
    # Add some simulated factors that create edge opportunities
    sport = game_data.get('sport', 'NBA')
    teams = game_data.get('teams', '')
    
    # Simulate some edge scenarios based on team names (for demo purposes)
    if 'Lakers' in teams or 'Warriors' in teams:
        # Popular teams might be overvalued by public
        base_probability -= 0.03  # 3% public overvaluation
    
    if 'Chiefs' in teams or 'Cowboys' in teams:
        # Popular NFL teams often overvalued
        base_probability -= 0.04
        
    if sport == 'MLB':
        # Baseball has more variance, creates more +EV opportunities
        base_probability += random.uniform(-0.08, 0.08)
    elif sport == 'NBA':
        # Basketball favorites can be undervalued late season
        base_probability += random.uniform(-0.05, 0.05)
    elif sport in ['NFL', 'NCAAF']:
        # Football spreads can have value
        base_probability += random.uniform(-0.06, 0.06)
    
    # Ensure probability stays within valid range
    return max(0.1, min(0.9, base_probability))

def find_positive_ev_bets(games_data, min_ev_threshold=0.02):
    """
    Analyze games to find bets with positive expected value.
    
    Args:
        games_data (list): List of game data with odds
        min_ev_threshold (float): Minimum EV% required to recommend bet
        
    Returns:
        list: List of +EV betting opportunities
    """
    ev_bets = []
    
    for game in games_data:
        # Analyze each market type for this game
        for market_type in ['moneyline', 'spreads', 'totals']:
            
            # Get odds for this market (simplified - using random odds for demo)
            if market_type == 'moneyline':
                odds_options = [
                    {'selection': game['teams'].split(' vs ')[0], 'odds': random.randint(-200, 250)},
                    {'selection': game['teams'].split(' vs ')[1], 'odds': random.randint(-200, 250)}
                ]
            elif market_type == 'spreads':
                spread = random.uniform(-10, 10)
                odds_options = [
                    {'selection': game['teams'].split(' vs ')[0], 'odds': random.randint(-120, 120), 'spread': spread},
                    {'selection': game['teams'].split(' vs ')[1], 'odds': random.randint(-120, 120), 'spread': -spread}
                ]
            else:  # totals
                total_points = random.randint(45, 65) if game.get('sport') in ['NFL', 'NCAAF'] else random.randint(200, 250)
                odds_options = [
                    {'selection': 'Over', 'odds': random.randint(-120, 120), 'total': total_points},
                    {'selection': 'Under', 'odds': random.randint(-120, 120), 'total': total_points}
                ]
            
            # Analyze each betting option
            for option in odds_options:
                # Estimate true probability for this outcome
                true_prob = estimate_true_probability(game, market_type)
                
                # If analyzing the second option (away team, under, etc.), use complement probability
                if option == odds_options[1] and market_type in ['moneyline']:
                    true_prob = 1 - true_prob
                
                # Calculate implied probability from odds
                implied_prob = calculate_implied_probability(option['odds'])
                
                # Calculate EV for a standard bet amount
                standard_bet = 100
                expected_value = calculate_expected_value(true_prob, option['odds'], standard_bet)
                ev_percentage = (expected_value / standard_bet) * 100
                
                # Check if this is a +EV opportunity
                if ev_percentage >= min_ev_threshold * 100:  # Convert threshold to percentage
                    ev_opportunity = {
                        'game_id': game.get('id', ''),
                        'teams': game['teams'],
                        'sport': game.get('sport', 'Unknown'),
                        'market_type': market_type,
                        'selection': option['selection'],
                        'odds': option['odds'],
                        'true_probability': round(true_prob, 3),
                        'implied_probability': round(implied_prob, 3),
                        'edge_percentage': round((true_prob - implied_prob) * 100, 2),
                        'expected_value_per_100': round(expected_value, 2),
                        'ev_percentage': round(ev_percentage, 2),
                        'confidence': min(95, max(55, 70 + (ev_percentage * 2)))  # Scale confidence with EV
                    }
                    
                    # Add market-specific data
                    if 'spread' in option:
                        ev_opportunity['spread'] = option['spread']
                    if 'total' in option:
                        ev_opportunity['total'] = option['total']
                    
                    ev_bets.append(ev_opportunity)
    
    # Sort by EV percentage (highest first)
    ev_bets.sort(key=lambda x: x['ev_percentage'], reverse=True)
    
    return ev_bets
