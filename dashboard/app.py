import os
import random
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Import core betting logic to avoid code duplication
from betting_logic import simulate_single_bet, simulate_real_world_bet

# Load environment variables from .env file
load_dotenv()

# --- Firebase Initialization ---
# Load the path to the service account key from an environment variable
try:
    cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not cred_path or not os.path.exists(cred_path):
        raise FileNotFoundError("Service account key file not found. Please set GOOGLE_APPLICATION_CREDENTIALS in your .env.")
    
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firestore client initialized successfully.")
except Exception as e:
    print(f"Failed to initialize Firebase Admin SDK: {e}")
    db = None

app = Flask(__name__)

# Load the Firebase App ID for collections from an environment variable
app_id = os.getenv('FIREBASE_APP_ID')
if not app_id:
    raise ValueError("FIREBASE_APP_ID not found in environment variables.")

# Load the client-side Firebase configuration from environment variables
firebase_config = {
    'apiKey': os.getenv('FIREBASE_API_KEY'),
    'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN'),
    'projectId': os.getenv('FIREBASE_PROJECT_ID'),
    'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET'),
    'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
    'appId': os.getenv('FIREBASE_APP_ID')
}

# Firestore Collection references
bots_collection = db.collection(f'artifacts/{app_id}/public/data/bots')
strategies_collection = db.collection(f'artifacts/{app_id}/public/data/strategies')

# --- API Endpoints ---
@app.route('/')
def home():
    """Renders the main dashboard page."""
    return render_template('index.html')

@app.route('/api/firebase-config', methods=['GET'])
def get_firebase_config():
    """Provides the client-side Firebase config securely."""
    return jsonify(firebase_config)

@app.route('/api/overall-stats', methods=['GET'])
def get_overall_stats():
    """Calculates and returns overall stats for all bots."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    try:
        bots_ref = bots_collection.stream()
        total_profit = 0
        total_bets = 0
        total_wagered = 0
        total_wins = 0
        total_losses = 0

        for bot_doc in bots_ref:
            bot_data = bot_doc.to_dict()
            total_profit += bot_data.get('total_profit', 0)
            total_bets += bot_data.get('total_bets', 0)
            total_wagered += bot_data.get('total_wagered', 0)
            total_wins += bot_data.get('total_wins', 0)
            total_losses += bot_data.get('total_losses', 0)
        
        win_rate = (total_wins / total_bets) * 100 if total_bets > 0 else 0
        
        return jsonify({
            'success': True,
            'stats': {
                'total_profit': round(total_profit, 2),
                'total_bets': total_bets,
                'total_wagered': round(total_wagered, 2),
                'win_rate': round(win_rate, 2),
                'total_wins': total_wins,
                'total_losses': total_losses
            }
        })

    except Exception as e:
        print(f"Failed to get overall stats: {e}")
        return jsonify({'success': False, 'message': f'Failed to get overall stats: {e}'}), 500

@app.route('/api/bots', methods=['POST'])
def add_bot():
    """Adds a new bot to the Firestore database."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    try:
        data = request.json
        new_bot_ref = bots_collection.document()
        bot_id = new_bot_ref.id
        initial_bot_data = {
            'id': bot_id,
            'name': data.get('name', f'Bot-{random.randint(1000, 9999)}'),
            'current_balance': float(data.get('initial_balance', 1000.0)),
            'initial_balance': float(data.get('initial_balance', 1000.0)),
            'bet_percentage': float(data.get('bet_percentage', 2.0)),
            'linked_strategy_id': data.get('linked_strategy_id', None),
            'total_profit': 0.0,
            'total_bets': 0,
            'total_wins': 0,
            'total_losses': 0,
            'total_wagered': 0.0,
            'created_at': datetime.datetime.now().isoformat(),
            'last_updated': datetime.datetime.now().isoformat(),
            'bet_history': []
        }
        
        new_bot_ref.set(initial_bot_data)
        return jsonify({'success': True, 'message': 'Bot added successfully.', 'bot_id': bot_id}), 201
    except Exception as e:
        print(f"Failed to add bot: {e}")
        return jsonify({'success': False, 'message': f'Failed to add bot: {e}'}), 500

@app.route('/api/bots/simulate', methods=['POST'])
def simulate_bot_bet():
    """Simulates a single bet for a bot and updates its record."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    try:
        data = request.json
        bot_id = data.get('bot_id')
        if not bot_id:
            return jsonify({'success': False, 'message': 'Bot ID is required.'}), 400

        bot_ref = bots_collection.document(bot_id)
        bot_doc = bot_ref.get()

        if not bot_doc.exists:
            return jsonify({'success': False, 'message': 'Bot not found.'}), 404

        bot_data = bot_doc.to_dict()
        bet_receipt = simulate_single_bet(bot_data)
        
        updates = {
            'total_bets': firestore.Increment(1),
            'current_balance': bet_receipt['new_balance'],
            'total_wagered': firestore.Increment(bet_receipt['wager']),
            'total_profit': firestore.Increment(bet_receipt['payout']),
            'last_updated': datetime.datetime.now().isoformat()
        }

        if bet_receipt['outcome'] == 'W':
            updates['total_wins'] = firestore.Increment(1)
        else:
            updates['total_losses'] = firestore.Increment(1)
        
        bot_ref.update({
            **updates,
            'bet_history': firestore.ArrayUnion([bet_receipt])
        })
        
        return jsonify({
            'success': True,
            'message': 'Bet simulated successfully.',
            'receipt': bet_receipt
        })

    except Exception as e:
        print(f"Failed to simulate bet: {e}")
        return jsonify({'success': False, 'message': f'Failed to simulate bet: {e}'}), 500

@app.route('/api/strategies', methods=['POST'])
def add_strategy():
    """Adds a new strategy to the Firestore database."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    try:
        data = request.json
        new_strategy_ref = strategies_collection.document()
        strategy_id = new_strategy_ref.id
        initial_strategy_data = {
            'id': strategy_id,
            'name': data.get('name', 'New Strategy'),
            'type': data.get('type', 'basic'),
            'description': data.get('description', 'A custom betting strategy.'),
            'parameters': data.get('parameters', {}),
            'linked_strategy_id': data.get('linked_strategy_id', None),
            'created_at': datetime.datetime.now().isoformat()
        }
        
        new_strategy_ref.set(initial_strategy_data)
        return jsonify({'success': True, 'message': 'Strategy added successfully.', 'strategy_id': strategy_id}), 201
    except Exception as e:
        print(f"Failed to add strategy: {e}")
        return jsonify({'success': False, 'message': f'Failed to add strategy: {e}'}), 500

@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """Retrieves all strategies from the Firestore database."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    try:
        strategies_ref = strategies_collection.stream()
        strategies = [doc.to_dict() for doc in strategies_ref]
        return jsonify({'success': True, 'strategies': strategies}), 200
    except Exception as e:
        print(f"Failed to retrieve strategies: {e}")
        return jsonify({'success': False, 'message': f'Failed to retrieve strategies: {e}'}), 500

@app.route('/api/strategy/<strategy_id>', methods=['PUT'])
def update_strategy(strategy_id):
    """Updates an existing strategy."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    try:
        data = request.json
        strategy_ref = strategies_collection.document(strategy_id)
        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'rules' in data:
            updates['rules'] = data['rules']
        updates['updated_at'] = datetime.datetime.now().isoformat()

        strategy_ref.update(updates)
        return jsonify({'success': True, 'message': 'Strategy updated successfully.'}), 200
    except Exception as e:
        print(f"Failed to update strategy: {e}")
        return jsonify({'success': False, 'message': f'Failed to update strategy: {e}'}), 500

@app.route('/api/strategy/<strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id):
    """Deletes a recovery strategy."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    strategy_ref = strategies_collection.document(strategy_id)
    strategy_doc = strategy_ref.get()

    if not strategy_doc.exists:
        return jsonify({'success': False, 'message': 'Strategy not found.'}), 404

    try:
        strategy_ref.delete()
        return jsonify({'success': True, 'message': 'Strategy deleted successfully.'}), 200
    except Exception as e:
        print(f"Failed to delete strategy: {e}")
        return jsonify({'success': False, 'message': f'Failed to delete strategy: {e}'}), 500

if __name__ == '__main__':
    app.run(debug=True)