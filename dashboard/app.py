import os
import random
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify

# --- Firebase Initialization ---
try:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firestore client initialized successfully.")
except Exception as e:
    print(f"Failed to initialize Firebase Admin SDK: {e}")
    db = None

app = Flask(__name__)

# Firestore Collection references
app_id = "1:945213178297:web:40f6e200fd00148754b668"
bots_collection = db.collection(f'artifacts/{app_id}/public/data/bots')
strategies_collection = db.collection(f'artifacts/{app_id}/public/data/strategies')

# --- Helper Functions ---
def simulate_real_world_bet(bot_data):
    """
    Simulates a single bet using a simple probability model.

    Args:
        bot_data (dict): The dictionary containing a single bot's data.

    Returns:
        dict: The updated bot_data dictionary.
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
        bot_data['career_wins'] = bot_data.get('career_wins', 0) + 1
    else:
        winnings = -bet_amount
        bot_data['current_balance'] -= bet_amount
        bot_data['career_losses'] = bot_data.get('career_losses', 0) + 1

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

# --- API Endpoints ---
@app.route('/')
def index():
    """Renders the main dashboard page."""
    return "The Python backend is running. Please access the front-end via index.html."

@app.route('/api/overall-stats', methods=['GET'])
def get_overall_stats():
    """Calculates and returns overall statistics across all bots."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    
    try:
        bots_docs = bots_collection.stream()
        
        total_profit = 0.0
        total_wagered = 0.0
        total_wins = 0
        total_losses = 0
        
        # To calculate average P/L, and find best/worst bot
        all_profit_losses = []
        
        for doc in bots_docs:
            bot = doc.to_dict()
            bot_profit_loss = 0.0
            
            # The 'bet_history' is an array in the document. We sum up the 'payout' for each bet.
            if 'bet_history' in bot and bot['bet_history']:
                for bet in bot['bet_history']:
                    total_profit += bet['payout']
                    total_wagered += bet['wager']
                    bot_profit_loss += bet['payout']
                    if bet['outcome'] == 'W':
                        total_wins += 1
                    else:
                        total_losses += 1
                        
            all_profit_losses.append({'name': bot.get('name', 'N/A'), 'profit_loss': bot_profit_loss})

        total_bets = total_wins + total_losses
        win_rate = (total_wins / total_bets) * 100 if total_bets > 0 else 0
        average_profit_loss_per_bot = sum(item['profit_loss'] for item in all_profit_losses) / len(all_profit_losses) if all_profit_losses else 0
        
        # Find best and worst performing bots
        best_bot = max(all_profit_losses, key=lambda item: item['profit_loss']) if all_profit_losses else {'name': 'N/A', 'profit_loss': 0}
        worst_bot = min(all_profit_losses, key=lambda item: item['profit_loss']) if all_profit_losses else {'name': 'N/A', 'profit_loss': 0}

        stats = {
            'total_profit': total_profit,
            'total_wagered': total_wagered,
            'total_wins': total_wins,
            'total_losses': total_losses,
            'total_bets': total_bets,
            'win_rate': win_rate,
            'average_profit_loss_per_bot': average_profit_loss_per_bot,
            'best_bot': best_bot,
            'worst_bot': worst_bot
        }
        
        return jsonify({'success': True, 'stats': stats}), 200

    except Exception as e:
        print(f"Failed to get overall stats: {e}")
        return jsonify({'success': False, 'message': f'Failed to get overall stats: {e}'}), 500

@app.route('/api/run-backtest', methods=['POST'])
def run_backtest():
    """Simulates a series of bets for a selected bot."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500

    data = request.json
    bot_id = data.get('botId')
    num_bets = data.get('numBets')

    bot_ref = bots_collection.document(str(bot_id))
    bot_doc = bot_ref.get()

    if not bot_doc.exists:
        return jsonify({'success': False, 'message': 'Bot not found.'}), 404

    bot = bot_doc.to_dict()
    
    initial_balance = bot['current_balance']
    bankroll_history = [{'bet_number': 0, 'balance': initial_balance}]
    
    if 'bet_history' not in bot:
        bot['bet_history'] = []
    
    initial_bets_count = len(bot['bet_history'])
    
    for i in range(num_bets):
        bot = simulate_real_world_bet(bot)
        bankroll_history.append({'bet_number': initial_bets_count + i + 1, 'balance': bot['current_balance']})
    
    final_balance = bot['current_balance']
    total_profit = final_balance - initial_balance
    total_wagered = sum(bet['wager'] for bet in bot['bet_history'][-num_bets:])
    total_bets_after_test = len(bot['bet_history'])
    
    try:
        bot_ref.update({
            'current_balance': final_balance,
            'career_wins': bot['career_wins'],
            'career_losses': bot['career_losses'],
            'bet_history': firestore.ArrayUnion(bot['bet_history'][-num_bets:])
        })
        
        report = {
            'initial_bankroll': initial_balance,
            'final_bankroll': final_balance,
            'total_profit': total_profit,
            'total_wagered': total_wagered,
            'total_bets': num_bets,
            'win_rate': (bot['career_wins'] / (bot['career_wins'] + bot['career_losses'])) * 100 if (bot['career_wins'] + bot['career_losses']) > 0 else 0,
            'roi': (total_profit / initial_balance) * 100 if initial_balance > 0 else 0,
        }
    
        return jsonify({
            'success': True,
            'report': report,
            'bankroll_history': bankroll_history
        }), 200
    except Exception as e:
        print(f"Failed to update bot data after backtest: {e}")
        return jsonify({'success': False, 'message': f'Failed to update bot data after backtest: {e}'}), 500

@app.route('/api/manage-funds', methods=['POST'])
def manage_funds():
    """Handles deposits and withdrawals for a specific bot."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500

    data = request.json
    bot_id = data.get('botId')
    amount = data.get('amount')
    fund_type = data.get('type')

    bot_ref = bots_collection.document(str(bot_id))
    bot_doc = bot_ref.get()

    if not bot_doc.exists:
        return jsonify({'success': False, 'message': 'Bot not found.'}), 404

    bot = bot_doc.to_dict()
    transaction_amount = 0
    message = ''

    if fund_type == 'deposit':
        transaction_amount = amount
        bot['current_balance'] += amount
        message = f"Successfully deposited ${amount:.2f} to {bot['name']}'s bankroll."
    elif fund_type == 'withdraw':
        if bot['current_balance'] < amount:
            return jsonify({'success': False, 'message': 'Insufficient funds for withdrawal.'}), 400
        transaction_amount = -amount
        bot['current_balance'] -= amount
        message = f"Successfully withdrew ${amount:.2f} from {bot['name']}'s bankroll."
    else:
        return jsonify({'success': False, 'message': 'Invalid fund type.'}), 400

    fund_receipt = {
        'timestamp': datetime.datetime.now().isoformat(),
        'type': fund_type,
        'amount': transaction_amount,
    }
    
    try:
        bot_ref.update({
            'current_balance': bot['current_balance'],
            'fund_history': firestore.ArrayUnion([fund_receipt])
        })
        return jsonify({'success': True, 'message': message}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to save funds transaction: {e}'}), 500

if __name__ == '__main__':
    if db:
        app.run(debug=True, port=5000)
    else:
        print("Application cannot start without a database connection. Please check your service account key.")