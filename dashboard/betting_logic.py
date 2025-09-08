# betting_logic.py
"""
This module contains the core logic for simulating betting scenarios.
It now includes a function for running a full backtest simulation.
"""
import random
import datetime

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
