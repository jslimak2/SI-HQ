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
    
    # Decide the outcome of the bet
    if random.random() < win_probability:
        # Win scenario
        payout = bet_amount * payout_multiplier
        outcome = 'W'
    else:
        # Loss scenario
        payout = -bet_amount
        outcome = 'L'
        
    # Update the bot's current balance
    bot_data['current_balance'] += payout
    
    # Create a receipt of the bet
    bet_receipt = {
        'timestamp': datetime.datetime.now().isoformat(),
        'outcome': outcome,
        'wager': bet_amount,
        'payout': payout,
        'matchup': f"{team1} vs {team2}"
    }

    # Add the receipt to the bot's bet history
    bot_data.setdefault('bet_history', []).append(bet_receipt)
    
    return bet_receipt

def run_backtest(bot_data, num_bets):
    """
    Runs a full backtest simulation over a specified number of bets.

    Args:
        bot_data (dict): The dictionary containing a single bot's data.
        num_bets (int): The number of bets to simulate.

    Returns:
        tuple: A tuple containing the final report and bankroll history.
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
        'total_wagered': total_wagered,
        'total_bets': num_bets,
        'total_wins': total_wins,
        'total_losses': total_losses,
        'win_rate': win_rate
    }
    
    return report, bankroll_history
