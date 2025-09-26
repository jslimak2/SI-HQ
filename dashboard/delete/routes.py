import json
import os
import random
from flask import Flask, render_template, request, jsonify
import datetime

app = Flask(__name__)

# Helper function to get the absolute path for data files
def get_data_filepath(filename):
    """Constructs the absolute path to a data file."""
    return os.path.join(os.path.dirname(__file__), '..', 'data', filename)

# File paths for the data
bots_filepath = get_data_filepath('investors.json')
strategies_filepath = get_data_filepath('strategies.json')

def load_json(filepath, default_value=None):
    """Safely loads a JSON file, returning a default value if not found."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_value if default_value is not None else []

def save_json(filepath, data):
    """Safely saves data to a JSON file."""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except IOError as e:
        print(f"Error saving file {filepath}: {e}")
        return False

# Betting Logic - consolidated into this file
def simulate_real_world_bet(bot_data):
    """
    Simulates a single bet using a simple probability model.
    """
    win_probability = 0.52
    payout_multiplier = 1.8
    teams = [
        ("Steelhawks", "Wildcats"), ("Falcons", "Eagles"),
        ("Ravens", "Hawks"), ("Lions", "Tigers"),
        ("Bears", "Grizzlies")
    ]
    team1, team2 = random.choice(teams)
    
    bet_amount = bot_data['current_balance'] * (bot_data['bet_percentage'] / 100)
    
    winnings = 0.0
    is_win = random.random() < win_probability
    
    if is_win:
        winnings = bet_amount * payout_multiplier
        bot_data['current_balance'] += winnings
        bot_data['career_wins'] += 1
    else:
        winnings = -bet_amount
        bot_data['current_balance'] -= bet_amount
        bot_data['career_losses'] += 1

    bet_receipt = {
        'timestamp': datetime.datetime.now().isoformat(),
        'teams': f"{team1} vs {team2}",
        'wager': bet_amount,
        'odds': f"+{int((payout_multiplier - 1) * 100)}" if payout_multiplier > 1 else 'Even',
        'payout': winnings,
        'outcome': 'W' if is_win else 'L',
    }
    bot_data['bet_history'].append(bet_receipt)
    return bot_data

# Routes
@app.route('/')
def index():
    """Renders the main dashboard page."""
    return render_template('index.html')

@app.route('/api/investors', methods=['GET'])
def get_bots():
    """Returns a list of all investors."""
    investors = load_json(bots_filepath, [])
    strategies = load_json(strategies_filepath, [])
    
    # Ensure all investors have the required fields for data consistency
    for investor in investors:
        if 'bet_history' not in investor:
            investor['bet_history'] = []
        if 'fund_history' not in investor:
            investor['fund_history'] = []
            
    # Enrich investors with strategy names
    for investor in investors:
        strategy = next((s for s in strategies if s['id'] == investor['linked_strategy_id']), None)
        investor['strategy_name'] = strategy['name'] if strategy else 'Unknown'
    
    return jsonify(investors)

@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """Returns a list of all strategies."""
    strategies = load_json(strategies_filepath, [])
    return jsonify(strategies)

@app.route('/api/manage-investors', methods=['POST'])
def manage_bots():
    """Handles adding or deleting a investor."""
    action = request.form.get('action')
    bots_list = load_json(bots_filepath)
    
    if action == 'create':
        new_bot_id = max([b['id'] for b in bots_list], default=0) + 1
        
        # New investor data structure with transaction arrays
        new_bot = {
            'id': new_bot_id,
            'name': request.form['name'],
            'starting_bankroll': float(request.form['starting_bankroll']),
            'current_balance': float(request.form['starting_bankroll']),
            'bet_percentage': float(request.form['bet_percentage']),
            'linked_strategy_id': int(request.form['linked_strategy_id']),
            'career_wins': 0,
            'career_losses': 0,
            'bet_history': [],
            'fund_history': [],
        }
        bots_list.append(new_bot)
        if save_json(bots_filepath, bots_list):
            return jsonify({'success': True, 'message': 'Investor added successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save investor.'}), 500

    elif action == 'delete':
        bot_id = int(request.form['id'])
        bots_list = [b for b in bots_list if b['id'] != bot_id]
        if save_json(bots_filepath, bots_list):
            return jsonify({'success': True, 'message': 'Investor deleted successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete investor.'}), 500
    
    return jsonify({'success': False, 'message': 'Invalid action.'}), 400

@app.route('/api/manage-strategies', methods=['POST'])
def manage_strategies():
    """Handles adding or deleting a strategy."""
    action = request.form.get('action')
    strategies_list = load_json(strategies_filepath)
    
    if action == 'create':
        new_strategy_id = max([s['id'] for s in strategies_list], default=0) + 1
        linked_strategy_id = request.form.get('linked_strategy_id')
        if linked_strategy_id:
            linked_strategy_id = int(linked_strategy_id)
        
        new_strategy = {
            'id': new_strategy_id,
            'name': request.form['name'],
            'type': request.form['type'],
        }
        strategies_list.append(new_strategy)
        if save_json(strategies_filepath, strategies_list):
            return jsonify({'success': True, 'message': 'Strategy added successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save strategy.'}), 500

    elif action == 'delete':
        strategy_id = int(request.form['id'])
        strategies_list = [s for s in strategies_list if s['id'] != strategy_id]
        if save_json(strategies_filepath, strategies_list):
            return jsonify({'success': True, 'message': 'Strategy deleted successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete strategy.'}), 500
    
    return jsonify({'success': False, 'message': 'Invalid action.'}), 400

@app.route('/api/run-backtest', methods=['POST'])
def run_backtest():
    """Simulates a series of bets for a selected investor."""
    data = request.json
    bot_id = data.get('botId')
    num_bets = data.get('numBets')
    
    bots_list = load_json(bots_filepath)
    investor = next((b for b in bots_list if b['id'] == bot_id), None)
    
    if not investor:
        return jsonify({'success': False, 'message': 'Investor not found.'}), 404

    initial_balance = investor['current_balance']
    bankroll_history = [{'bet_number': 0, 'balance': initial_balance}]
    
    for i in range(1, num_bets + 1):
        investor = simulate_real_world_bet(investor)
        bankroll_history.append({'bet_number': i, 'balance': investor['current_balance']})
    
    final_balance = investor['current_balance']
    total_profit = final_balance - initial_balance
    total_bets = investor['career_wins'] + investor['career_losses']
    win_rate = (investor['career_wins'] / total_bets) * 100 if total_bets > 0 else 0
    roi = (total_profit / initial_balance) * 100 if initial_balance > 0 else 0

    if save_json(bots_filepath, bots_list):
        report = {
            'initial_bankroll': initial_balance,
            'final_bankroll': final_balance,
            'total_profit': total_profit,
            'total_bets': total_bets,
            'win_rate': win_rate,
            'roi': roi,
        }
        return jsonify({'success': True, 'message': 'Backtest simulation complete.', 'report': report, 'bankroll_history': bankroll_history})
    else:
        return jsonify({'success': False, 'message': 'Failed to save investor data after backtest.'}), 500

@app.route('/api/import-bets', methods=['POST'])
def import_bets():
    """
    Imports bet results from a CSV file.
    """
    file = request.files.get('file')
    if not file or not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'message': 'Invalid file format. Please upload a CSV file.'}), 400

    bets = []
    try:
        content = file.stream.read().decode("utf-8")
        lines = content.splitlines()
        for line in lines:
            if not line.strip(): continue
            parts = line.strip().split(',')
            if len(parts) == 3:
                bets.append({
                    'bot_id': int(parts[0]),
                    'outcome': parts[1].strip(),
                    'amount': float(parts[2]),
                })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error reading CSV file: {e}'}), 400

    bots_list = load_json(bots_filepath)
    
    for bet in bets:
        investor = next((b for b in bots_list if b['id'] == bet['bot_id']), None)
        if investor:
            winnings = 0.0
            if bet['outcome'].lower() == 'win':
                winnings = bet['amount']
                investor['current_balance'] += winnings
                investor['career_wins'] += 1
            elif bet['outcome'].lower() == 'loss':
                winnings = -bet['amount']
                investor['current_balance'] += winnings
                investor['career_losses'] += 1

            bet_receipt = {
                'timestamp': datetime.datetime.now().isoformat(),
                'teams': 'Imported',
                'wager': abs(bet['amount']),
                'odds': 'Imported',
                'payout': winnings,
                'outcome': bet['outcome'].upper(),
            }
            investor['bet_history'].append(bet_receipt)
        else:
            print(f"Warning: Investor with ID {bet['bot_id']} not found.")

    if save_json(bots_filepath, bots_list):
        return jsonify({'success': True, 'message': 'Bets imported successfully!'})
    else:
        return jsonify({'success': False, 'message': 'Failed to save investor data after import.'}), 500

@app.route('/api/manage-funds', methods=['POST'])
def manage_funds():
    """Handles deposits and withdrawals for a specific investor."""
    data = request.json
    bot_id = data.get('botId')
    amount = data.get('amount')
    fund_type = data.get('type')

    bots_list = load_json(bots_filepath)
    investor = next((b for b in bots_list if b['id'] == bot_id), None)

    if not investor:
        return jsonify({'success': False, 'message': 'Investor not found.'}), 404
    
    if fund_type == 'deposit':
        investor['current_balance'] += amount
        transaction_amount = amount
        message = f"Successfully deposited ${amount:.2f} to {investor['name']}'s bankroll."
    elif fund_type == 'withdraw':
        if investor['current_balance'] < amount:
            return jsonify({'success': False, 'message': 'Insufficient funds for withdrawal.'}), 400
        investor['current_balance'] -= amount
        transaction_amount = -amount
        message = f"Successfully withdrew ${amount:.2f} from {investor['name']}'s bankroll."
    else:
        return jsonify({'success': False, 'message': 'Invalid fund type.'}), 400

    fund_receipt = {
        'timestamp': datetime.datetime.now().isoformat(),
        'type': fund_type,
        'amount': transaction_amount,
    }
    investor['fund_history'].append(fund_receipt)

    if save_json(bots_filepath, bots_list):
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': 'Failed to save funds transaction.'}), 500

if __name__ == '__main__':
    # Ensure the data directory exists
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    # Create empty data files if they don't exist
    if not os.path.exists(bots_filepath):
        save_json(bots_filepath, [])
    if not os.path.exists(strategies_filepath):
        save_json(strategies_filepath, [])

    app.run(debug=True, port=5000)
