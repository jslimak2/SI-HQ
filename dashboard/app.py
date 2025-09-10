import os
import random
import datetime
import firebase_admin
import requests
from firebase_admin import credentials, firestore, auth # Added 'auth' here
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Import core betting logic to avoid code duplication
from betting_logic import simulate_single_bet, simulate_real_world_bet

# Load environment variables from .env file
load_dotenv()

# --- Firebase Initialization ---
# Load the path to the service account key from an environment variable
demo_mode = False
try:
    cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not cred_path or not os.path.exists(cred_path) or 'demo' in cred_path:
        print("Running in demo mode - Firebase features will be limited")
        demo_mode = True
        db = None
    else:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firestore client initialized successfully.")
except Exception as e:
    print(f"Firebase initialization failed, running in demo mode: {e}")
    demo_mode = True
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

# Load the external sports betting API key
external_api_key = os.getenv('SPORTS_API_KEY')
if not external_api_key:
    print("Warning: SPORTS_API_KEY is not set in your .env file. The available investments feature will not work.")

# Firestore Collection references
if not demo_mode and db:
    bots_collection = db.collection(f'artifacts/{app_id}/public/data/bots')
    strategies_collection = db.collection(f'artifacts/{app_id}/public/data/strategies')
else:
    bots_collection = None
    strategies_collection = None

# User-specific collections for the new caching functionality
def get_user_collections(user_id):
    """Get user-specific collection references"""
    if demo_mode or not db:
        return None
    return {
        'cached_investments': db.collection(f'users/{user_id}/cached_investments'),
        'user_settings': db.collection(f'users/{user_id}/settings'),
        'bets': db.collection(f'users/{user_id}/bets')
    }

# --- API Endpoints ---
@app.route('/demo')
def demo():
    """Renders a demo page showing the new bot functionality."""
    return render_template('demo.html')

@app.route('/')
def home():
    """Renders the main dashboard page."""
    auth_token = None
    
    if not demo_mode and firebase_admin._apps:
        # Create a custom token for anonymous sign-in
        # For a production app, you'd want to handle user authentication more securely
        uid = f"anon-user-{random.randint(1000, 9999)}"
        auth_token = auth.create_custom_token(uid)
        auth_token_str = auth_token.decode('utf-8') if auth_token else None
    else:
        # Demo mode - provide a dummy token
        auth_token_str = "demo_auth_token"

    # Pass the Firebase config and auth token to the template
    return render_template('index.html',
                           firebase_config=firebase_config,
                           auth_token=auth_token_str)

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
            'starting_balance': float(data.get('initial_balance', 1000.0)),  # Frontend expects this field name
            'initial_balance': float(data.get('initial_balance', 1000.0)),
            'bet_percentage': float(data.get('bet_percentage', 2.0)),
            'max_bets_per_week': int(data.get('max_bets_per_week', 5)),
            'sport': data.get('sport', 'NBA'),  # Add sport field
            'bet_type': data.get('bet_type', 'Moneyline'),  # Add bet type field
            'status': 'stopped',  # Default status
            'strategy_id': data.get('strategy_id', None),  # Use strategy_id instead of linked_strategy_id
            'linked_strategy_id': data.get('linked_strategy_id', None),
            'total_profit': 0.0,
            'total_bets': 0,
            'total_wins': 0,
            'total_losses': 0,
            'total_wagered': 0.0,
            'open_wagers': [],  # List of current open wagers
            'bets_this_week': 0,  # Counter for bets placed this week
            'week_reset_date': datetime.datetime.now().isoformat(),  # Track when to reset weekly counter
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
    """Adds a new strategy to the Firestore database (user-specific)."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    try:
        data = request.json
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required.'}), 400
        strategies_collection_user = db.collection(f'users/{user_id}/strategies')
        new_strategy_ref = strategies_collection_user.document()
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
    """Retrieves all strategies from the Firestore database (user-specific)."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID is required.'}), 400
    try:
        strategies_collection_user = db.collection(f'users/{user_id}/strategies')
        strategies_ref = strategies_collection_user.stream()
        strategies = [doc.to_dict() for doc in strategies_ref]
        return jsonify({'success': True, 'strategies': strategies}), 200
    except Exception as e:
        print(f"Failed to retrieve strategies: {e}")
        return jsonify({'success': False, 'message': f'Failed to retrieve strategies: {e}'}), 500

@app.route('/api/strategy/<strategy_id>', methods=['PUT'])
def update_strategy(strategy_id):
    """Updates an existing strategy (user-specific)."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID is required.'}), 400
    try:
        strategies_collection_user = db.collection(f'users/{user_id}/strategies')
        strategy_ref = strategies_collection_user.document(strategy_id)
        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'rules' in data:
            updates['rules'] = data['rules']
        if 'description' in data:
            updates['description'] = data['description']
        if 'parameters' in data:
            updates['parameters'] = data['parameters']
        updates['updated_at'] = datetime.datetime.now().isoformat()
        strategy_ref.update(updates)
        return jsonify({'success': True, 'message': 'Strategy updated successfully.'}), 200
    except Exception as e:
        print(f"Failed to update strategy: {e}")
        return jsonify({'success': False, 'message': f'Failed to update strategy: {e}'}), 500

@app.route('/api/strategy/<strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id):
    """Deletes a recovery strategy (user-specific)."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID is required.'}), 400
    strategies_collection_user = db.collection(f'users/{user_id}/strategies')
    strategy_ref = strategies_collection_user.document(strategy_id)
    strategy_doc = strategy_ref.get()
    if not strategy_doc.exists:
        return jsonify({'success': False, 'message': 'Strategy not found.'}), 404
    try:
        strategy_ref.delete()
        return jsonify({'success': True, 'message': 'Strategy deleted successfully.'}), 200
    except Exception as e:
        print(f"Failed to delete strategy: {e}")
        return jsonify({'success': False, 'message': f'Failed to delete strategy: {e}'}), 500
        
@app.route('/api/strategy/<strategy_id>/picks', methods=['GET'])
def get_strategy_picks(strategy_id):
    """Get recommended investments from a strategy for a bot (user-specific)."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    
    user_id = request.args.get('user_id')
    bot_id = request.args.get('bot_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID is required.'}), 400
    if not bot_id:
        return jsonify({'success': False, 'message': 'Bot ID is required.'}), 400
    
    try:
        # Get user-specific bot data
        bot_ref = db.collection(f'users/{user_id}/bots').document(bot_id)
        bot_doc = bot_ref.get()
        if not bot_doc.exists:
            return jsonify({'success': False, 'message': 'Bot not found.'}), 404
        bot_data = bot_doc.to_dict()
        # Fetch strategy from user-specific collection
        strategy_ref = db.collection(f'users/{user_id}/strategies').document(strategy_id)
        strategy_doc = strategy_ref.get()
        if not strategy_doc.exists:
            return jsonify({'success': False, 'message': 'Strategy not found.'}), 404
        strategy_data = strategy_doc.to_dict()
        # Check if bot has reached max bets for the week
        max_bets = bot_data.get('max_bets_per_week', 5)
        bets_this_week = bot_data.get('bets_this_week', 0)
        if bets_this_week >= max_bets:
            return jsonify({
                'success': True,
                'picks': [],
                'message': f'Bot has reached maximum bets for this week ({max_bets})',
                'remaining_bets': 0
            })
        picks = generate_strategy_picks(strategy_data, bot_data, max_bets - bets_this_week)
        return jsonify({
            'success': True,
            'picks': picks,
            'remaining_bets': max_bets - bets_this_week,
            'strategy_name': strategy_data.get('name', 'Unknown Strategy')
        })
    except Exception as e:
        print(f"Failed to get strategy picks: {e}")
        return jsonify({'success': False, 'message': f'Failed to get picks: {e}'}), 500

def generate_strategy_picks(strategy_data, bot_data, max_picks):
    """Generate betting picks based on strategy type."""
    strategy_type = strategy_data.get('type', 'basic')
    
    # Basic strategy: randomly select games with simple criteria
    if strategy_type == 'basic' or strategy_type == 'normal':
        return generate_basic_strategy_picks(bot_data, max_picks)
    elif strategy_type == 'recovery':
        return generate_recovery_strategy_picks(bot_data, max_picks)
    else:
        return generate_basic_strategy_picks(bot_data, max_picks)

def generate_basic_strategy_picks(bot_data, max_picks):
    """Generate basic strategy picks - simple random selection with some logic."""
    picks = []
    
    # Use demo games for now since we're in demo mode
    demo_games = [
        {'teams': 'Lakers vs Warriors', 'sport': 'NBA', 'odds': 1.85, 'bet_type': 'Moneyline'},
        {'teams': 'Celtics vs Heat', 'sport': 'NBA', 'odds': 2.10, 'bet_type': 'Moneyline'},
        {'teams': 'Chiefs vs Bills', 'sport': 'NFL', 'odds': 1.90, 'bet_type': 'Spread'},
        {'teams': 'Cowboys vs Eagles', 'sport': 'NFL', 'odds': 1.95, 'bet_type': 'Moneyline'},
        {'teams': 'Yankees vs Red Sox', 'sport': 'MLB', 'odds': 1.75, 'bet_type': 'Moneyline'},
    ]
    
    # Filter by bot's preferred sport if specified
    bot_sport = bot_data.get('sport')
    if bot_sport and bot_sport != 'All':
        filtered_games = [g for g in demo_games if g['sport'] == bot_sport]
        if filtered_games:
            demo_games = filtered_games
    
    # Randomly select games up to max_picks
    import random
    selected_games = random.sample(demo_games, min(len(demo_games), max_picks))
    
    for game in selected_games:
        bet_amount = bot_data['current_balance'] * (bot_data['bet_percentage'] / 100)
        potential_payout = bet_amount * game['odds']
        
        pick = {
            'teams': game['teams'],
            'sport': game['sport'],
            'bet_type': game['bet_type'],
            'odds': game['odds'],
            'recommended_amount': round(bet_amount, 2),
            'potential_payout': round(potential_payout, 2),
            'confidence': random.randint(60, 85)  # Basic confidence score
        }
        picks.append(pick)
    
    return picks

def generate_recovery_strategy_picks(bot_data, max_picks):
    """Generate recovery strategy picks - more aggressive to recover losses."""
    basic_picks = generate_basic_strategy_picks(bot_data, max_picks)
    
    # If bot is down, increase bet amounts and focus on higher odds
    current_balance = bot_data.get('current_balance', 0)
    starting_balance = bot_data.get('starting_balance', current_balance)
    
    if current_balance < starting_balance:
        # Increase bet percentage for recovery
        for pick in basic_picks:
            pick['recommended_amount'] = pick['recommended_amount'] * 1.5  # 50% more aggressive
            pick['potential_payout'] = pick['recommended_amount'] * pick['odds']
            pick['confidence'] = pick['confidence'] - 10  # Lower confidence due to higher risk
    
    return basic_picks

@app.route('/api/investments', methods=["GET"])
def get_available_investments():
    """
    Fetches and returns available sports games and odds.
    Supports caching with 'refresh' parameter.
    """
    user_id = request.args.get('user_id', 'anonymous')
    refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    # Demo mode handling
    if demo_mode or not db:
        return jsonify({
            'success': True,
            'investments': generate_demo_investments(),
            'cached': False,
            'last_refresh': datetime.datetime.now().isoformat(),
            'api_calls_made': 0,
            'demo_mode': True
        }), 200
    
    collections = get_user_collections(user_id)
    if not collections:
        return jsonify({'success': False, 'message': 'Database not available.'}), 500
    
    # If not refreshing, try to get cached data first
    if not refresh:
        try:
            cached_doc_ref = collections['cached_investments'].document('latest')
            cached_doc = cached_doc_ref.get()
            
            if cached_doc.exists:
                cached_data = cached_doc.to_dict()
                # Check if cache is not too old (optional: add expiration logic here)
                return jsonify({
                    'success': True,
                    'investments': cached_data.get('investments', []),
                    'cached': True,
                    'last_refresh': cached_data.get('timestamp', ''),
                    'api_calls_saved': len(cached_data.get('investments', []))
                }), 200
        except Exception as e:
            print(f"Error fetching cached investments: {e}")
            # Continue to fetch fresh data if cache fails
    
    # Fetch fresh data from API
    if not external_api_key or 'demo' in external_api_key:
        return jsonify({
            'success': True,
            'investments': generate_demo_investments(),
            'cached': False,
            'last_refresh': datetime.datetime.now().isoformat(),
            'api_calls_made': 0,
            'demo_mode': True,
            'message': 'Demo mode: Using simulated data. Set SPORTS_API_KEY for real data.'
        }), 200

    # These are the sports leagues we will be fetching data for
    sports = ['basketball_nba', 'americanfootball_nfl', 'baseball_mlb', 'americanfootball_ncaaf', 'basketball_ncaab']
    all_games = []
    api_calls_made = 0

    try:
        # Fetch data for each sport sequentially
        for sport in sports:
            odds_response = requests.get(
                f'https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={external_api_key}&regions=us&markets=h2h,spreads,totals&oddsFormat=american&dateFormat=iso'
            )
            api_calls_made += 1
            odds_response.raise_for_status()
            games = odds_response.json()
            all_games.extend(games)

        # Fetch user's placed bets
        placed_bets = []
        try:
            placed_bets_snapshot = collections['bets'].get()
            placed_bets = [bet.to_dict() for bet in placed_bets_snapshot]
        except Exception as e:
            print(f"Error fetching placed bets: {e}")

        investments = []
        for game in all_games:
            # Check for placed bets on this game
            game_bets = [
                bet for bet in placed_bets
                if bet.get('teams', '') == f"{game.get('away_team')} vs {game.get('home_team')}"
            ]
            
            # Include ALL bookmakers and their markets, not just the first one
            bookmakers = game.get('bookmakers', [])
            if not bookmakers:
                continue

            investments.append({
                'id': game['id'],
                'sport': game['sport_title'],
                'teams': f"{game.get('away_team')} vs {game.get('home_team')}",
                'commence_time': game['commence_time'],
                'bookmakers': bookmakers,  # Include all bookmakers with all their markets
                'placed_bets': game_bets
            })
        
        # Cache the fresh data
        try:
            cache_data = {
                'investments': investments,
                'timestamp': datetime.datetime.now().isoformat(),
                'api_calls_made': api_calls_made,
                'total_games': len(investments)
            }
            collections['cached_investments'].document('latest').set(cache_data)
        except Exception as e:
            print(f"Error caching investments: {e}")
            
        return jsonify({
            'success': True,
            'investments': investments,
            'cached': False,
            'last_refresh': datetime.datetime.now().isoformat(),
            'api_calls_made': api_calls_made
        }), 200

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error fetching sports data: {e}")
        return jsonify({'success': False, 'message': f'HTTP Error: {e.response.text}'}), e.response.status_code
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({'success': False, 'message': f'An unexpected error occurred: {e}'}), 500

def generate_demo_investments():
    """Generate demo investment data for testing"""
    import random
    from datetime import datetime, timedelta
    
    demo_games = [
        {'sport': 'NBA', 'team1': 'Lakers', 'team2': 'Warriors'},
        {'sport': 'NBA', 'team1': 'Celtics', 'team2': 'Heat'},
        {'sport': 'NFL', 'team1': 'Chiefs', 'team2': 'Bills'},
        {'sport': 'NFL', 'team1': 'Cowboys', 'team2': 'Eagles'},
        {'sport': 'MLB', 'team1': 'Yankees', 'team2': 'Red Sox'},
        {'sport': 'NCAAF', 'team1': 'Alabama', 'team2': 'Georgia'},  # Test college football
        {'sport': 'NCAAB', 'team1': 'Duke', 'team2': 'UNC'},        # Test college basketball
    ]
    
    # Demo sportsbooks
    sportsbooks = ['DraftKings', 'FanDuel', 'BetMGM', 'Caesars', 'PointsBet']
    
    investments = []
    for i, game in enumerate(demo_games):
        commence_time = datetime.now() + timedelta(hours=random.randint(1, 72))
        
        # Generate multiple sportsbooks for each game
        bookmakers = []
        for sportsbook in sportsbooks:
            # Generate realistic odds for each market type
            
            # Moneyline odds
            team1_ml = random.randint(-200, 150)
            team2_ml = -team1_ml + random.randint(-50, 50)  # Make it somewhat realistic
            
            # Spread odds  
            spread_points = random.uniform(-10.5, 10.5)
            team1_spread = random.randint(-120, 120)
            team2_spread = random.randint(-120, 120)
            
            # Total odds
            total_points = random.randint(200, 250) if game['sport'] in ['NBA', 'NCAAB'] else random.randint(40, 60)
            over_odds = random.randint(-120, 120)
            under_odds = random.randint(-120, 120)
            
            markets = [
                {
                    'key': 'h2h',
                    'name': 'Moneyline',
                    'outcomes': [
                        {'name': game['team1'], 'price': team1_ml},
                        {'name': game['team2'], 'price': team2_ml}
                    ]
                },
                {
                    'key': 'spreads', 
                    'name': 'Spreads',
                    'outcomes': [
                        {'name': game['team1'], 'price': team1_spread, 'point': spread_points},
                        {'name': game['team2'], 'price': team2_spread, 'point': -spread_points}
                    ]
                },
                {
                    'key': 'totals',
                    'name': 'Totals', 
                    'outcomes': [
                        {'name': 'Over', 'price': over_odds, 'point': total_points},
                        {'name': 'Under', 'price': under_odds, 'point': total_points}
                    ]
                }
            ]
            
            bookmakers.append({
                'key': sportsbook.lower().replace(' ', ''),
                'title': sportsbook,
                'markets': markets
            })
        
        investments.append({
            'id': f'demo_game_{i}',
            'sport': game['sport'],
            'teams': f"{game['team1']} vs {game['team2']}",
            'commence_time': commence_time.isoformat(),
            'bookmakers': bookmakers,  # New structure with all sportsbooks
            'placed_bets': []
        })
    
    return investments

@app.route('/api/user-settings', methods=['GET'])
def get_user_settings():
    """Get user settings for preferences like auto-refresh"""
    user_id = request.args.get('user_id', 'anonymous')
    
    # Demo mode handling
    if demo_mode or not db:
        return jsonify({
            'success': True,
            'settings': {
                'auto_refresh_on_login': True,
                'cache_expiry_minutes': 30,
                'demo_mode': True
            }
        }), 200
    
    collections = get_user_collections(user_id)
    if not collections:
        return jsonify({'success': False, 'message': 'Database not available.'}), 500
    
    try:
        settings_doc = collections['user_settings'].document('preferences').get()
        
        if settings_doc.exists:
            settings = settings_doc.to_dict()
        else:
            # Default settings
            settings = {
                'auto_refresh_on_login': True,
                'cache_expiry_minutes': 30,
                'created_at': datetime.datetime.now().isoformat()
            }
            # Save default settings
            collections['user_settings'].document('preferences').set(settings)
            
        return jsonify({
            'success': True,
            'settings': settings
        }), 200
        
    except Exception as e:
        print(f"Error fetching user settings: {e}")
        return jsonify({'success': False, 'message': f'Failed to fetch settings: {e}'}), 500

@app.route('/api/user-settings', methods=['POST'])
def update_user_settings():
    """Update user settings"""
    user_id = request.json.get('user_id', 'anonymous')
    settings_update = request.json.get('settings', {})
    
    # Demo mode handling
    if demo_mode or not db:
        return jsonify({
            'success': True,
            'message': 'Settings saved (demo mode - not persistent)'
        }), 200
    
    collections = get_user_collections(user_id)
    if not collections:
        return jsonify({'success': False, 'message': 'Database not available.'}), 500
    
    try:
        # Add update timestamp
        settings_update['updated_at'] = datetime.datetime.now().isoformat()
        
        # Update settings document
        collections['user_settings'].document('preferences').update(settings_update)
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully'
        }), 200
        
    except Exception as e:
        print(f"Error updating user settings: {e}")
        return jsonify({'success': False, 'message': f'Failed to update settings: {e}'}), 500

@app.route('/api/investments/stats', methods=['GET'])
def get_investment_stats():
    """Get statistics about cached investments"""
    user_id = request.args.get('user_id', 'anonymous')
    
    # Demo mode handling
    if demo_mode or not db:
        return jsonify({
            'success': True,
            'has_cache': False,
            'last_refresh': datetime.datetime.now().isoformat(),
            'total_games': 5,
            'api_calls_saved': 0,
            'demo_mode': True
        }), 200
    
    collections = get_user_collections(user_id)
    if not collections:
        return jsonify({'success': False, 'message': 'Database not available.'}), 500
    
    try:
        cached_doc = collections['cached_investments'].document('latest').get()
        
        if cached_doc.exists:
            cached_data = cached_doc.to_dict()
            return jsonify({
                'success': True,
                'has_cache': True,
                'last_refresh': cached_data.get('timestamp', ''),
                'total_games': cached_data.get('total_games', 0),
                'api_calls_saved': cached_data.get('api_calls_made', 0)
            }), 200
        else:
            return jsonify({
                'success': True,
                'has_cache': False,
                'last_refresh': None,
                'total_games': 0,
                'api_calls_saved': 0
            }), 200
            
    except Exception as e:
        print(f"Error fetching investment stats: {e}")
        return jsonify({'success': False, 'message': f'Failed to fetch stats: {e}'}), 500

@app.route('/api/bot-recommendations', methods=['GET'])
def get_bot_recommendations():
    """Get bot recommendations for current investment opportunities"""
    user_id = request.args.get('user_id', 'anonymous')
    
    try:
        # In demo mode, generate mock recommendations
        if demo_mode or not db:
            recommendations = generate_demo_bot_recommendations()
            return jsonify({
                'success': True,
                'recommendations': recommendations,
                'demo_mode': True
            }), 200
        
        # Get user's bots
        collections = get_user_collections(user_id)
        if not collections:
            return jsonify({'success': False, 'message': 'Database not available'}), 500
        
        # For now, use demo recommendations even in non-demo mode
        # In a real implementation, this would:
        # 1. Fetch user's active bots
        # 2. Get current investment data
        # 3. Run each bot's strategy against current games
        # 4. Return recommendations with confidence levels
        
        recommendations = generate_demo_bot_recommendations()
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'demo_mode': False
        }), 200
        
    except Exception as e:
        print(f"Error getting bot recommendations: {e}")
        return jsonify({'success': False, 'message': f'Failed to get recommendations: {str(e)}'}), 500

def generate_demo_bot_recommendations():
    """Generate demo bot recommendations for testing"""
    import random
    
    # Demo bots with different characteristics
    demo_bots = [
        {
            'id': 'demo_bot_1',
            'name': 'Value Hunter',
            'strategy': 'Finds undervalued bets',
            'confidence_style': 'conservative',  # 60-75% confidence range
            'preferred_odds_range': [150, 300],  # Prefers higher odds for value
            'color': '#10B981'  # green
        },
        {
            'id': 'demo_bot_2', 
            'name': 'Safe Bet',
            'strategy': 'Low risk, steady gains',
            'confidence_style': 'safe',  # 70-85% confidence range
            'preferred_odds_range': [-150, 150],  # Prefers lower odds
            'color': '#3B82F6'  # blue
        },
        {
            'id': 'demo_bot_3',
            'name': 'High Roller',
            'strategy': 'High risk, high reward',
            'confidence_style': 'aggressive',  # 55-90% confidence range
            'preferred_odds_range': [200, 500],  # Prefers high odds
            'color': '#F59E0B'  # amber
        }
    ]
    
    recommendations = {}
    
    # Demo games that match what we show in investments
    demo_games = [
        {
            'game_id': 'demo_game_0',
            'teams': 'Lakers vs Warriors',
            'sport': 'NBA'
        },
        {
            'game_id': 'demo_game_1', 
            'teams': 'Celtics vs Heat',
            'sport': 'NBA'
        }
    ]
    
    # Generate recommendations for each game
    for game in demo_games:
        game_recommendations = []
        
        for bot in demo_bots:
            # Each bot might recommend different markets/selections
            if random.random() < 0.7:  # 70% chance bot has a recommendation
                
                # Determine confidence based on bot's style
                if bot['confidence_style'] == 'conservative':
                    confidence = random.randint(60, 75)
                elif bot['confidence_style'] == 'safe':
                    confidence = random.randint(70, 85)
                else:  # aggressive
                    confidence = random.randint(55, 90)
                
                # Generate recommendation for random sportsbook and market
                sportsbooks = ['DraftKings', 'FanDuel', 'BetMGM', 'Caesars', 'PointsBet']
                markets = [
                    {'key': 'h2h', 'name': 'Moneyline', 'selections': ['Lakers', 'Warriors'] if 'Lakers' in game['teams'] else ['Celtics', 'Heat']},
                    {'key': 'spreads', 'name': 'Spreads', 'selections': ['Lakers', 'Warriors'] if 'Lakers' in game['teams'] else ['Celtics', 'Heat']},
                    {'key': 'totals', 'name': 'Totals', 'selections': ['Over', 'Under']}
                ]
                
                selected_sportsbook = random.choice(sportsbooks)
                selected_market = random.choice(markets)
                selected_selection = random.choice(selected_market['selections'])
                
                # Generate bet amount (typically 1-5% of a demo balance)
                demo_balance = random.randint(800, 1200)
                bet_percentage = random.uniform(1.5, 4.0)
                recommended_amount = round((demo_balance * bet_percentage / 100), 2)
                
                recommendation = {
                    'bot_id': bot['id'],
                    'bot_name': bot['name'],
                    'bot_strategy': bot['strategy'],
                    'bot_color': bot['color'],
                    'sportsbook': selected_sportsbook,
                    'market_key': selected_market['key'],
                    'market_name': selected_market['name'],
                    'selection': selected_selection,
                    'confidence': confidence,
                    'recommended_amount': recommended_amount,
                    'reasoning': f"{bot['strategy']} - {confidence}% confidence",
                    'status': 'recommended'  # vs 'placed'
                }
                
                game_recommendations.append(recommendation)
        
        recommendations[game['game_id']] = game_recommendations
    
    return recommendations

@app.route('/api/place-bets', methods=['POST'])
def place_bets():
    """Place multiple bets from the cart"""
    data = request.json
    user_id = data.get('user_id', 'anonymous')
    bets = data.get('bets', [])
    
    if not bets:
        return jsonify({'success': False, 'message': 'No bets provided'}), 400
    
    try:
        # In demo mode, just return success
        if demo_mode or not db:
            return jsonify({
                'success': True,
                'message': f'Demo mode: {len(bets)} bets placed successfully',
                'placed_bets': bets
            }), 200
        
        # For real implementation, you would:
        # 1. Validate each bet
        # 2. Check user balance/permissions
        # 3. Submit bets to actual sportsbooks
        # 4. Store bet records in database
        # 5. Update user balance/statistics
        
        collections = get_user_collections(user_id)
        if not collections:
            return jsonify({'success': False, 'message': 'Database not available'}), 500
        
        placed_bets = []
        for bet in bets:
            # Create bet record
            bet_record = {
                'id': bet.get('id'),
                'user_id': user_id,
                'game_id': bet.get('gameId'),
                'teams': bet.get('teams'),
                'sport': bet.get('sport'),
                'sportsbook': bet.get('sportsbook'),
                'market_type': bet.get('marketType'),
                'selection': bet.get('selection'),
                'odds': bet.get('odds'),
                'bet_amount': bet.get('betAmount'),
                'potential_payout': bet.get('potentialPayout'),
                'status': 'pending',
                'placed_at': datetime.datetime.now().isoformat(),
                'commence_time': bet.get('commenceTime')
            }
            
            # Add to database
            collections['bets'].add(bet_record)
            placed_bets.append(bet_record)
        
        return jsonify({
            'success': True,
            'message': f'Successfully placed {len(bets)} bet(s)',
            'placed_bets': placed_bets
        }), 200
        
    except Exception as e:
        print(f"Error placing bets: {e}")
        return jsonify({'success': False, 'message': f'Failed to place bets: {str(e)}'}), 500

@app.route('/api/api-status', methods=['GET'])
def get_api_status():
    """Get current API usage status from the sports API."""
    if not external_api_key or 'demo' in external_api_key:
        return jsonify({
            'success': True,
            'remaining_requests': 'N/A (Demo Mode)',
            'used_requests': 'N/A (Demo Mode)',
            'demo_mode': True,
            'message': 'Demo mode active. Set SPORTS_API_KEY for real API usage tracking.'
        }), 200
    
    try:
        # Make a simple request to get header information
        url = f'https://api.the-odds-api.com/v4/sports/basketball_ncaab/odds?apiKey={external_api_key}&regions=us'
        response = requests.get(url)
        
        # Extract API usage from headers
        remaining_requests = response.headers.get('X-Requests-Remaining', 'Unknown')
        used_requests = response.headers.get('X-Requests-Used', 'Unknown')
        
        return jsonify({
            'success': True,
            'remaining_requests': remaining_requests,
            'used_requests': used_requests,
            'demo_mode': False
        }), 200
        
    except Exception as e:
        print(f"Error getting API status: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to get API status: {e}',
            'remaining_requests': 'Error',
            'used_requests': 'Error'
        }), 500

# --- NEW STRATEGY BUILDER AND MODEL GALLERY ENDPOINTS ---

@app.route('/api/strategies/visual', methods=['POST'])
def create_visual_strategy():
    """Create a new visual flow-based strategy"""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    
    try:
        data = request.json
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required.'}), 400
            
        strategies_collection_user = db.collection(f'users/{user_id}/strategies')
        new_strategy_ref = strategies_collection_user.document()
        strategy_id = new_strategy_ref.id
        
        strategy_data = {
            'id': strategy_id,
            'name': data.get('name', 'Visual Strategy'),
            'type': 'visual_flow',
            'description': data.get('description', ''),
            'flow_definition': data.get('flow_definition', {}),
            'parameters': data.get('parameters', {}),
            'performance': {
                'total_bets': 0,
                'won_bets': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'roi': 0.0
            },
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        new_strategy_ref.set(strategy_data)
        return jsonify({'success': True, 'message': 'Visual strategy created successfully.', 'strategy_id': strategy_id}), 201
        
    except Exception as e:
        print(f"Failed to create visual strategy: {e}")
        return jsonify({'success': False, 'message': f'Failed to create strategy: {e}'}), 500

@app.route('/api/models', methods=['GET'])
def list_models():
    """List available ML models with filtering"""
    try:
        sport_filter = request.args.get('sport', 'all')
        model_type_filter = request.args.get('type', 'all') 
        performance_filter = request.args.get('performance', 'all')
        
        # Demo models data (in production this would come from model registry)
        demo_models = [
            {
                'id': 'nfl_totals_lstm',
                'name': 'NFL Total Points Predictor',
                'description': 'LSTM model predicting NFL game total points using weather, team stats, and historical data',
                'model_type': 'lstm',
                'sport': 'nfl',
                'market_type': 'totals',
                'version': '1.2.3',
                'framework': 'tensorflow',
                'performance': {
                    'accuracy': 68.2,
                    'precision': 67.1,
                    'recall': 69.4,
                    'f1_score': 68.2,
                    'profit_over_time': [120, 340, 567, 823, 1045],
                    'last_30_day_roi': 12.4
                },
                'status': 'active',
                'created_at': '2024-01-01T00:00:00Z'
            },
            {
                'id': 'nba_moneyline_transformer',
                'name': 'NBA Moneyline Predictor',
                'description': 'Advanced transformer model for NBA moneyline predictions',
                'model_type': 'transformer',
                'sport': 'nba',
                'market_type': 'moneyline',
                'version': '2.1.0',
                'framework': 'pytorch',
                'performance': {
                    'accuracy': 71.5,
                    'precision': 70.8,
                    'recall': 72.2,
                    'f1_score': 71.5,
                    'profit_over_time': [89, 234, 445, 612, 789],
                    'last_30_day_roi': 8.9
                },
                'status': 'active',
                'created_at': '2024-01-15T00:00:00Z'
            },
            {
                'id': 'mlb_runline_rf',
                'name': 'MLB Run Line Model',
                'description': 'Random forest model specializing in MLB run line betting',
                'model_type': 'random_forest',
                'sport': 'mlb',
                'market_type': 'runline',
                'version': '1.5.2',
                'framework': 'scikit-learn',
                'performance': {
                    'accuracy': 66.8,
                    'precision': 65.4,
                    'recall': 68.2,
                    'f1_score': 66.8,
                    'profit_over_time': [156, 387, 612, 834, 1152],
                    'last_30_day_roi': 15.2
                },
                'status': 'active',
                'created_at': '2024-01-10T00:00:00Z'
            }
        ]
        
        # Apply filters
        filtered_models = demo_models
        
        if sport_filter != 'all':
            filtered_models = [m for m in filtered_models if m['sport'] == sport_filter]
            
        if model_type_filter != 'all':
            filtered_models = [m for m in filtered_models if m['model_type'] == model_type_filter]
            
        if performance_filter != 'all':
            if performance_filter == 'high':
                filtered_models = [m for m in filtered_models if m['performance']['accuracy'] > 70]
            elif performance_filter == 'medium':
                filtered_models = [m for m in filtered_models if 60 <= m['performance']['accuracy'] <= 70]
            elif performance_filter == 'low':
                filtered_models = [m for m in filtered_models if m['performance']['accuracy'] < 60]
        
        return jsonify({
            'success': True,
            'models': filtered_models,
            'total_count': len(filtered_models)
        }), 200
        
    except Exception as e:
        print(f"Error listing models: {e}")
        return jsonify({'success': False, 'message': f'Failed to list models: {e}'}), 500

@app.route('/api/analytics/performance', methods=['GET'])
def get_performance_analytics():
    """Get detailed performance analytics"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        time_period = request.args.get('period', '30d')  # 7d, 30d, 90d, 1y
        
        # Generate demo analytics data
        analytics_data = {
            'summary_metrics': {
                'total_profit': 1247.50,
                'total_bets': 89,
                'win_rate': 68.4,
                'roi': 12.3,
                'sharpe_ratio': 1.45,
                'max_drawdown': -234.80,
                'avg_bet_size': 45.60
            },
            'strategy_breakdown': {
                'nfl_over_under': {'profit': 487.20, 'bets': 23, 'win_rate': 69.6},
                'nba_moneyline': {'profit': 312.40, 'bets': 18, 'win_rate': 66.7},
                'arbitrage': {'profit': 223.80, 'bets': 12, 'win_rate': 100.0},
                'recovery': {'profit': -73.50, 'bets': 8, 'win_rate': 37.5}
            },
            'cohort_analysis': {
                'by_day_of_week': {
                    'monday': {'profit': 156.7, 'win_rate': 72.0},
                    'tuesday': {'profit': 89.3, 'win_rate': 65.0},
                    'wednesday': {'profit': 234.5, 'win_rate': 78.0},
                    'thursday': {'profit': 198.2, 'win_rate': 71.0},
                    'friday': {'profit': 167.8, 'win_rate': 69.0},
                    'saturday': {'profit': 289.1, 'win_rate': 75.0},
                    'sunday': {'profit': 111.9, 'win_rate': 63.0}
                }
            },
            'alerts': [
                {
                    'id': 'alert_1',
                    'type': 'warning',
                    'title': 'NFL Model Performance Drop',
                    'message': 'NFL model accuracy dropped below 65% in last 10 predictions',
                    'timestamp': '2024-01-20T14:30:00Z',
                    'severity': 'medium'
                },
                {
                    'id': 'alert_2', 
                    'type': 'danger',
                    'title': 'Losing Streak Detected',
                    'message': 'Current losing streak of 5 consecutive bets',
                    'timestamp': '2024-01-20T10:15:00Z',
                    'severity': 'high'
                }
            ]
        }
        
        return jsonify({
            'success': True,
            'analytics': analytics_data,
            'period': time_period,
            'generated_at': datetime.datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error getting performance analytics: {e}")
        return jsonify({'success': False, 'message': f'Analytics failed: {e}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
