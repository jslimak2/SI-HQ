# betting_logic.py
"""
This module contains the core logic for simulating betting scenarios.
It now includes a function for running a full backtest simulation.
"""
import random
import datetime

def simulate_real_world_bet(bot_data):
    """
    Simulates a single bet using a simple probability model.

    Args:
        bot_data (dict): The dictionary containing a single bot's data.

    Returns:
        dict: The updated bot_data dictionary.
    """
    
    # Simple probability-based model
    # Win probability can be adjusted based on desired simulation realism.
    # For this example, we'll use a fixed 52% win probability to simulate a slight edge.
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
    
    winnings = 0.0
    
    # Simulate the outcome of the bet
    is_win = random.random() < win_probability
    
    # Update bot stats based on the outcome
    if is_win:
        winnings = bet_amount * payout_multiplier
        bot_data['current_balance'] += winnings
        bot_data['current_win_streak'] += 1
        bot_data['current_loss_streak'] = 0
        bot_data['career_wins'] += 1
    else:
        winnings = -bet_amount
        bot_data['current_balance'] -= bet_amount
        bot_data['current_loss_streak'] += 1
        bot_data['current_win_streak'] = 0
        bot_data['career_losses'] += 1

    # Record the bet history with new fields
    bet_receipt = {
        'timestamp': datetime.datetime.now().isoformat(),
        'teams': f"{team1} vs {team2}",
        'wager': bet_amount,
        # Convert payout multiplier to implied odds for display (e.g., +180)
        'odds': f"+{int((payout_multiplier - 1) * 100)}" if payout_multiplier > 1 else 'Even',
        'payout': winnings,
        'outcome': 'W' if is_win else 'L'
    }
    
    bot_data['bet_history'].append(bet_receipt)
    
    return bot_data

def run_backtest_simulation(bot_data, num_bets):
    """
    Runs a full backtest simulation for a given bot over a number of bets.

    Args:
        bot_data (dict): The bot to simulate.
        num_bets (int): The number of bets to simulate.
    
    Returns:
        dict: A dictionary containing the final report and bankroll history.
    """
    initial_balance = bot_data['starting_bankroll']
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
        updated_bot = simulate_real_world_bet(simulation_bot)
        
        # Update our tracking variables
        total_wagered += updated_bot['bet_history'][-1]['wager']
        total_profit += updated_bot['bet_history'][-1]['payout']
        
        if updated_bot['bet_history'][-1]['outcome'] == 'W':
            total_wins += 1
        else:
            total_losses += 1
            
        current_balance = updated_bot['current_balance']
        bankroll_history.append({'bet_number': i + 1, 'balance': current_balance})
        
    # Final report
    report = {
        'initial_bankroll': initial_balance,
        'final_bankroll': current_balance,
        'total_profit': total_profit,
        'total_wagered': total_wagered,
        'total_bets': num_bets,
        'win_rate': (total_wins / num_bets) * 100 if num_bets > 0 else 0,
        'roi': (total_profit / total_wagered) * 100 if total_wagered > 0 else 0
    }
    
    return {
        'report': report,
        'bankroll_history': bankroll_history
    }