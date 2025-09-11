import os
import random
import datetime
import time
import firebase_admin
import requests
import numpy as np
import uuid
from firebase_admin import credentials, firestore, auth # Added 'auth' here
from flask import Flask, request, jsonify, render_template, g

# Professional imports
from config import ConfigManager, setup_logging, validate_config
from error_handling import (
    handle_errors, ValidationError, ResourceNotFoundError, 
    create_error_response, validate_required_fields, error_monitor
)
from api_documentation import validate_endpoint_request, Post9APIDocumentation
from security import SecurityManager, require_authentication, rate_limit, sanitize_request_data

# Import core betting logic to avoid code duplication
from betting_logic import simulate_single_bet, simulate_real_world_bet

# Import advanced ML and analytics components
try:
    import sys
    sys.path.append(os.path.dirname(__file__))
    
    from ml.model_manager import model_manager
    from analytics.advanced_stats import AdvancedSportsAnalyzer, generate_demo_analytics_data
    from models.neural_predictor import SportsNeuralPredictor, generate_demo_training_data
    from models.ensemble_predictor import SportsEnsemblePredictor
    ML_AVAILABLE = True
    print("Advanced ML components loaded successfully")
except ImportError as e:
    print(f"Advanced ML components not available: {e}")
    try:
        # Fallback to basic ML components
        from ml.basic_predictor import BasicSportsPredictor, BasicAnalyzer, generate_demo_data
        ML_AVAILABLE = True
        BASIC_ML_ONLY = True
        print("Basic ML components loaded as fallback")
    except ImportError as e2:
        print(f"Basic ML components also not available: {e2}")
        ML_AVAILABLE = False
        BASIC_ML_ONLY = False

# Load environment variables from .env file
config = ConfigManager.load_config()
logger = setup_logging(config)

# Validate configuration
config_warnings = validate_config(config)
for warning in config_warnings:
    logger.warning(f"Configuration warning: {warning}")

# --- Firebase Initialization ---
# Load the path to the service account key from an environment variable
demo_mode = False
try:
    cred_path = config.database.service_account_path
    if not cred_path or not os.path.exists(cred_path) or 'demo' in cred_path:
        logger.info("Running in demo mode - Firebase features will be limited")
        demo_mode = True
        db = None
    else:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("Firestore client initialized successfully.")
except Exception as e:
    logger.error(f"Firebase initialization failed, running in demo mode: {e}")
    demo_mode = True
    db = None

app = Flask(__name__)
app.secret_key = config.secret_key

# Initialize security manager
app.security_manager = SecurityManager(config.secret_key)

# Load the Firebase App ID for collections from an environment variable
app_id = config.database.firebase_app_id
if not app_id:
    raise ValueError("FIREBASE_APP_ID not found in environment variables.")

# Load the client-side Firebase configuration from environment variables
firebase_config = {
    'apiKey': config.database.firebase_api_key,
    'authDomain': config.database.firebase_auth_domain,
    'projectId': config.database.firebase_project_id,
    'storageBucket': config.database.firebase_storage_bucket,
    'messagingSenderId': config.database.firebase_messaging_sender_id,
    'appId': config.database.firebase_app_id
}

# Load the external sports betting API key
external_api_key = config.api.sports_api_key
if not external_api_key:
    logger.warning("SPORTS_API_KEY is not set. The available investments feature will not work.")

# Professional request tracking middleware
@app.before_request
def before_request():
    """Professional request tracking and security"""
    g.request_id = str(uuid.uuid4())
    g.start_time = time.time()
    
    logger.info(f"Request started: {request.method} {request.path} [ID: {g.request_id}]")

@app.after_request  
def after_request(response):
    """Log request completion and performance metrics"""
    duration = time.time() - g.start_time
    
    logger.info(f"Request completed: {request.method} {request.path} "
               f"[ID: {g.request_id}] [Status: {response.status_code}] "
               f"[Duration: {duration:.3f}s]")
    
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['X-Request-ID'] = g.request_id
    
    return response

# Professional error handlers
@app.errorhandler(ValidationError)
def handle_validation_error(error):
    error_monitor.record_error(error.error_code, request.endpoint)
    return create_error_response(error)

@app.errorhandler(ResourceNotFoundError)
def handle_not_found_error(error):
    error_monitor.record_error(error.error_code, request.endpoint)
    return create_error_response(error)

@app.errorhandler(Exception)
def handle_generic_error(error):
    error_monitor.record_error('INTERNAL_SERVER_ERROR', request.endpoint)
    return create_error_response(error)

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
@app.route('/api/docs')
def api_documentation():
    """API documentation endpoint"""
    try:
        openapi_spec = Post9APIDocumentation.generate_openapi_spec()
        return jsonify(openapi_spec)
    except Exception as e:
        return create_error_response(e)

@app.route('/api/health')
def health_check():
    """Professional health check endpoint"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'environment': config.environment.value,
            'services': {
                'database': 'demo' if demo_mode else 'connected',
                'ml_models': 'available' if ML_AVAILABLE else 'limited',
                'external_api': 'demo' if not external_api_key or 'demo' in external_api_key else 'connected'
            },
            'error_stats': error_monitor.get_error_stats()
        }
        
        return jsonify({
            'success': True,
            'health': health_status
        })
    except Exception as e:
        return create_error_response(e)

@app.route('/terms')
def terms():
    """Terms of Service page"""
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    """Privacy Policy page"""
    return render_template('privacy.html')

@app.route('/demo')
def demo():
    """Renders a demo page showing the new bot functionality."""
    return render_template('demo.html')

@app.route('/ml')
def ml_dashboard():
    """Renders the advanced ML dashboard"""
    return render_template('ml_dashboard.html')

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Page not found', 'success': False}), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors"""
    app.logger.error(f'Server Error: {e}')
    return jsonify({'error': 'Internal server error', 'success': False}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle uncaught exceptions"""
    app.logger.error(f'Unhandled Exception: {e}')
    return jsonify({'error': 'An unexpected error occurred', 'success': False}), 500

@app.route('/')
def home():
    """Renders the main dashboard page."""
    try:
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
    except Exception as e:
        app.logger.error(f'Error in home route: {e}')
        return render_template('index.html',
                               firebase_config=firebase_config,
                               auth_token="demo_auth_token")

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
@handle_errors
@require_authentication
@rate_limit(requests_per_hour=100)
@sanitize_request_data(required_fields=['name', 'initial_balance'], optional_fields=['bet_percentage', 'max_bets_per_week', 'sport'])
def add_bot():
    """Adds a new bot to the Firestore database with professional validation."""
    if not db:
        raise ValidationError("Database not available in demo mode")
    
    try:
        # Get sanitized data
        data = g.sanitized_request_data
        
        # Additional validation
        initial_balance = float(data.get('initial_balance', 1000.0))
        if initial_balance <= 0 or initial_balance > 1000000:
            raise ValidationError("Initial balance must be between $1 and $1,000,000")
        
        bet_percentage = float(data.get('bet_percentage', 2.0))
        if bet_percentage <= 0 or bet_percentage > 20:
            raise ValidationError("Bet percentage must be between 0.1% and 20%")
        
        max_bets_per_week = int(data.get('max_bets_per_week', 5))
        if max_bets_per_week <= 0 or max_bets_per_week > 100:
            raise ValidationError("Max bets per week must be between 1 and 100")
        
        new_bot_ref = bots_collection.document()
        bot_id = new_bot_ref.id
        
        initial_bot_data = {
            'id': bot_id,
            'name': data.get('name'),
            'current_balance': initial_balance,
            'starting_balance': initial_balance,
            'initial_balance': initial_balance,
            'bet_percentage': bet_percentage,
            'max_bets_per_week': max_bets_per_week,
            'sport': data.get('sport', 'NBA'),
            'bet_type': data.get('bet_type', 'Moneyline'),
            'status': 'stopped',
            'strategy_id': data.get('strategy_id', None),
            'linked_strategy_id': data.get('linked_strategy_id', None),
            'total_profit': 0.0,
            'total_bets': 0,
            'total_wins': 0,
            'total_losses': 0,
            'total_wagered': 0.0,
            'open_wagers': [],
            'bets_this_week': 0,
            'week_reset_date': datetime.datetime.now().isoformat(),
            'created_at': datetime.datetime.now().isoformat(),
            'last_updated': datetime.datetime.now().isoformat(),
            'bet_history': [],
            'created_by': g.current_user.get('user_id'),
            'version': '2.0'
        }
        
        new_bot_ref.set(initial_bot_data)
        
        logger.info(f"Bot created successfully: {bot_id} by user {g.current_user.get('user_id')}")
        
        return jsonify({
            'success': True, 
            'message': 'Bot created successfully with enhanced validation.', 
            'bot_id': bot_id,
            'bot_data': initial_bot_data
        }), 201
        
    except ValueError as e:
        raise ValidationError(f"Invalid numeric value: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to add bot: {e}")
        raise ValidationError(f'Failed to add bot: {e}')

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
            'flow_definition': data.get('flow_definition', {}),
            'linked_strategy_id': data.get('linked_strategy_id', None),
            'created_from_template': data.get('created_from_template', None),
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
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
    
    # Expected Value strategy
    if strategy_type == 'expected_value':
        return generate_expected_value_picks(strategy_data, bot_data, max_picks)
    elif strategy_type == 'conservative':
        return generate_conservative_strategy_picks(strategy_data, bot_data, max_picks)
    elif strategy_type == 'aggressive':
        return generate_aggressive_strategy_picks(strategy_data, bot_data, max_picks)
    elif strategy_type == 'recovery':
        return generate_recovery_strategy_picks(bot_data, max_picks)
    elif strategy_type == 'value_hunting':
        return generate_value_hunting_picks(strategy_data, bot_data, max_picks)
    elif strategy_type == 'arbitrage':
        return generate_arbitrage_picks(strategy_data, bot_data, max_picks)
    else:
        return generate_basic_strategy_picks(bot_data, max_picks)

def generate_expected_value_picks(strategy_data, bot_data, max_picks):
    """Generate +eV (Expected Value) strategy picks."""
    picks = []
    
    # Get strategy parameters
    params = strategy_data.get('parameters', {})
    min_ev = params.get('min_expected_value', 5.0)
    max_bet_pct = params.get('max_bet_percentage', 3.0)
    min_confidence = params.get('confidence_threshold', 65)
    max_odds = params.get('max_odds', 3.0)
    kelly_fraction = params.get('kelly_fraction', 0.25)
    
    # Demo games with calculated expected values
    demo_games = [
        {
            'teams': 'Lakers vs Warriors', 
            'sport': 'NBA', 
            'odds': 2.25, 
            'bet_type': 'Moneyline',
            'true_probability': 0.50,  # 50% estimated true probability
            'expected_value': ((2.25 * 0.50) - 1) * 100  # Calculate EV percentage
        },
        {
            'teams': 'Celtics vs Heat', 
            'sport': 'NBA', 
            'odds': 1.85, 
            'bet_type': 'Moneyline',
            'true_probability': 0.60,  # 60% estimated true probability  
            'expected_value': ((1.85 * 0.60) - 1) * 100
        },
        {
            'teams': 'Chiefs vs Bills', 
            'sport': 'NFL', 
            'odds': 2.75, 
            'bet_type': 'Spread',
            'true_probability': 0.42,  # 42% estimated true probability
            'expected_value': ((2.75 * 0.42) - 1) * 100
        },
        {
            'teams': 'Cowboys vs Eagles', 
            'sport': 'NFL', 
            'odds': 1.95, 
            'bet_type': 'Moneyline',
            'true_probability': 0.55,  # 55% estimated true probability
            'expected_value': ((1.95 * 0.55) - 1) * 100
        }
    ]
    
    # Filter games based on +eV criteria
    for game in demo_games:
        ev = game['expected_value']
        confidence = int(game['true_probability'] * 100)
        
        # Check if game meets +eV criteria
        if (ev >= min_ev and 
            confidence >= min_confidence and 
            game['odds'] <= max_odds):
            
            # Calculate bet size using Kelly Criterion fraction
            optimal_fraction = (game['true_probability'] * game['odds'] - 1) / (game['odds'] - 1)
            bet_fraction = min(optimal_fraction * kelly_fraction, max_bet_pct / 100)
            bet_amount = bot_data['current_balance'] * bet_fraction
            
            potential_payout = bet_amount * game['odds']
            
            pick = {
                'teams': game['teams'],
                'sport': game['sport'],
                'bet_type': game['bet_type'],
                'odds': game['odds'],
                'recommended_amount': round(bet_amount, 2),
                'potential_payout': round(potential_payout, 2),
                'confidence': confidence,
                'expected_value': round(ev, 2),
                'strategy_reason': f"+eV: {ev:.1f}% (Kelly: {optimal_fraction:.2%}, Bet: {bet_fraction:.1%})"
            }
            picks.append(pick)
            
            if len(picks) >= max_picks:
                break
    
    return picks

def generate_conservative_strategy_picks(strategy_data, bot_data, max_picks):
    """Generate conservative strategy picks with enhanced logic."""
    params = strategy_data.get('parameters', {})
    min_confidence = params.get('min_confidence', 75)
    max_bet_pct = params.get('max_bet_percentage', 2.0)
    max_odds = params.get('max_odds', 2.0)
    
    basic_picks = generate_basic_strategy_picks(bot_data, max_picks)
    
    # Filter and adjust for conservative parameters
    conservative_picks = []
    for pick in basic_picks:
        if (pick['confidence'] >= min_confidence and 
            pick['odds'] <= max_odds):
            
            # Reduce bet size for conservative approach
            pick['recommended_amount'] = min(
                pick['recommended_amount'], 
                bot_data['current_balance'] * (max_bet_pct / 100)
            )
            pick['potential_payout'] = pick['recommended_amount'] * pick['odds']
            pick['strategy_reason'] = f"Conservative: {pick['confidence']}% confidence, Low odds"
            conservative_picks.append(pick)
    
    return conservative_picks

def generate_aggressive_strategy_picks(strategy_data, bot_data, max_picks):
    """Generate aggressive strategy picks with enhanced logic."""
    params = strategy_data.get('parameters', {})
    min_confidence = params.get('min_confidence', 60)
    max_bet_pct = params.get('max_bet_percentage', 5.0)
    
    basic_picks = generate_basic_strategy_picks(bot_data, max_picks)
    
    # Adjust for aggressive parameters
    for pick in basic_picks:
        if pick['confidence'] >= min_confidence:
            # Increase bet size for aggressive approach
            pick['recommended_amount'] = bot_data['current_balance'] * (max_bet_pct / 100)
            pick['potential_payout'] = pick['recommended_amount'] * pick['odds']
            pick['strategy_reason'] = f"Aggressive: {pick['confidence']}% confidence, High stakes"
    
    return basic_picks

def generate_value_hunting_picks(strategy_data, bot_data, max_picks):
    """Generate value hunting strategy picks."""
    params = strategy_data.get('parameters', {})
    min_odds_edge = params.get('min_odds_edge', 5.0)
    max_bet_pct = params.get('max_bet_percentage', 3.5)
    
    picks = generate_basic_strategy_picks(bot_data, max_picks)
    
    # Add value hunting logic - simulate finding better odds
    for pick in picks:
        # Simulate market comparison (in real implementation, compare across sportsbooks)
        market_average = pick['odds'] * 0.95  # Assume we found 5% better odds
        odds_edge = ((pick['odds'] - market_average) / market_average) * 100
        
        if odds_edge >= min_odds_edge:
            pick['recommended_amount'] = bot_data['current_balance'] * (max_bet_pct / 100)
            pick['potential_payout'] = pick['recommended_amount'] * pick['odds']
            pick['strategy_reason'] = f"Value: {odds_edge:.1f}% better than market average"
    
    return picks

def generate_arbitrage_picks(strategy_data, bot_data, max_picks):
    """Generate arbitrage strategy picks."""
    params = strategy_data.get('parameters', {})
    min_profit = params.get('min_arbitrage_profit', 1.0)
    
    # Simulate arbitrage opportunities (in real implementation, find across sportsbooks)
    arbitrage_picks = []
    
    # Example arbitrage opportunity
    arbitrage_opportunity = {
        'teams': 'Lakers vs Warriors',
        'sport': 'NBA',
        'bet_type': 'Arbitrage',
        'sportsbook_a_odds': 2.10,
        'sportsbook_b_odds': 2.05,
        'arbitrage_profit': 2.4  # 2.4% guaranteed profit
    }
    
    if arbitrage_opportunity['arbitrage_profit'] >= min_profit:
        # Calculate optimal bet distribution
        total_investment = bot_data['current_balance'] * 0.10  # 10% for arbitrage
        
        pick = {
            'teams': arbitrage_opportunity['teams'],
            'sport': arbitrage_opportunity['sport'],
            'bet_type': 'Arbitrage (Both Sides)',
            'odds': arbitrage_opportunity['sportsbook_a_odds'],
            'recommended_amount': round(total_investment, 2),
            'potential_payout': round(total_investment * (1 + arbitrage_opportunity['arbitrage_profit']/100), 2),
            'confidence': 100,  # Risk-free
            'strategy_reason': f"Arbitrage: {arbitrage_opportunity['arbitrage_profit']:.1f}% guaranteed profit"
        }
        arbitrage_picks.append(pick)
    
    return arbitrage_picks

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

# --- ADVANCED ML AND ANALYTICS ENDPOINTS ---

@app.route('/api/ml/models', methods=['GET'])
def list_ml_models():
    """List available ML models"""
    if not ML_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    try:
        sport = request.args.get('sport')
        status = request.args.get('status')
        
        if globals().get('BASIC_ML_ONLY', False):
            # Return basic model info for demo
            return jsonify({
                'success': True,
                'models': [{
                    'id': 'basic_statistical_nba',
                    'sport': 'NBA',
                    'model_type': 'basic_statistical',
                    'status': 'available',
                    'description': 'Basic statistical predictor for NBA games'
                }],
                'total_count': 1,
                'basic_mode': True
            })
        else:
            models = model_manager.list_models(sport=sport, status=status)
            return jsonify({
                'success': True,
                'models': models,
                'total_count': len(models)
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ml/demo/predict', methods=['POST'])
def demo_prediction():
    """Make a demo prediction using any available trained model"""
    if not ML_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    try:
        data = request.json or {}
        sport = data.get('sport', 'NBA')
        
        # Check if we have basic ML only
        if globals().get('BASIC_ML_ONLY', False):
            # Use basic predictor
            from ml.basic_predictor import BasicSportsPredictor, generate_demo_data
            predictor = BasicSportsPredictor(sport)
            
            # Generate and train on demo data
            demo_training_data = generate_demo_data(sport, 1000)
            training_results = predictor.train_model(demo_training_data)
            
            # Generate sample game data
            if sport == 'NBA':
                game_data = {
                    'home_team_ppg': data.get('home_team_ppg', 110),
                    'away_team_ppg': data.get('away_team_ppg', 108),
                    'home_win_pct': data.get('home_win_pct', 0.6),
                    'away_win_pct': data.get('away_win_pct', 0.55),
                    'home_pace': data.get('home_pace', 100),
                    'away_pace': data.get('away_pace', 98)
                }
            elif sport == 'NFL':
                game_data = {
                    'home_team_off_yards': data.get('home_team_off_yards', 350),
                    'away_team_off_yards': data.get('away_team_off_yards', 340),
                    'home_win_pct': data.get('home_win_pct', 0.6),
                    'away_win_pct': data.get('away_win_pct', 0.55)
                }
            else:
                game_data = {
                    'home_win_pct': data.get('home_win_pct', 0.6),
                    'away_win_pct': data.get('away_win_pct', 0.55),
                    'home_score_avg': data.get('home_score_avg', 105),
                    'away_score_avg': data.get('away_score_avg', 100)
                }
            
            # Make prediction
            prediction = predictor.predict_game(game_data)
            
            return jsonify({
                'success': True,
                'prediction': prediction,
                'training_results': training_results,
                'game_data': game_data,
                'sport': sport,
                'model_type': 'basic_statistical'
            })
        
        else:
            # Use advanced ML components (placeholder for when dependencies are available)
            return jsonify({
                'success': False,
                'error': 'Advanced ML components would be used here when dependencies are installed'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/kelly', methods=['POST'])
def calculate_kelly_basic():
    """Calculate Kelly Criterion using basic analytics"""
    try:
        data = request.json
        win_probability = data.get('win_probability')
        odds = data.get('odds')
        bankroll = data.get('bankroll', 1000)
        
        if win_probability is None or odds is None:
            return jsonify({'error': 'win_probability and odds are required'}), 400
        
        if globals().get('BASIC_ML_ONLY', False):
            from ml.basic_predictor import BasicAnalyzer
            kelly_result = BasicAnalyzer.calculate_kelly_criterion(win_probability, odds, bankroll)
        else:
            # Use advanced analyzer when available
            kelly_result = {'error': 'Advanced analytics not available'}
        
        return jsonify({
            'success': True,
            'kelly_analysis': kelly_result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ml/basic/train', methods=['POST'])
@handle_errors
@require_authentication  
@rate_limit(requests_per_hour=20)  # Lower limit for resource-intensive operations
@sanitize_request_data(required_fields=['sport'], optional_fields=['num_samples', 'model_type'])
def train_basic_model():
    """Train a basic statistical model with professional validation"""
    if not ML_AVAILABLE:
        raise ValidationError("ML components not available")
    
    try:
        data = g.sanitized_request_data
        
        # Validate inputs
        sport = data.get('sport')
        if sport not in ['NBA', 'NFL', 'MLB']:
            raise ValidationError("Sport must be one of: NBA, NFL, MLB", field='sport')
        
        num_samples = int(data.get('num_samples', 1000))
        if num_samples < 100 or num_samples > config.ml.max_training_samples:
            raise ValidationError(f"Number of samples must be between 100 and {config.ml.max_training_samples}", field='num_samples')
        
        from ml.basic_predictor import BasicSportsPredictor, generate_demo_data
        
        # Create basic predictor
        predictor = BasicSportsPredictor(sport)
        
        # Generate training data
        training_data = generate_demo_data(sport, num_samples)
        
        # Train model
        training_start = time.time()
        results = predictor.train_model(training_data)
        training_duration = time.time() - training_start
        
        # Get feature importance
        importance = predictor.get_feature_importance()
        
        # Log training completion
        logger.info(f"Model training completed for {sport} with {num_samples} samples "
                   f"in {training_duration:.2f}s by user {g.current_user.get('user_id')}")
        
        return jsonify({
            'success': True,
            'training_results': {
                **results,
                'training_duration_seconds': round(training_duration, 2),
                'samples_used': num_samples
            },
            'feature_importance': importance,
            'sport': sport,
            'model_type': 'basic_statistical',
            'model_version': '2.0',
            'trained_at': datetime.datetime.utcnow().isoformat(),
            'trained_by': g.current_user.get('user_id')
        })
        
    except ValueError as e:
        raise ValidationError(f"Invalid numeric value: {str(e)}")
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        raise ValidationError(f'Model training failed: {e}')

@app.route('/api/analytics/basic', methods=['GET'])
def get_basic_analytics():
    """Get basic analytics without heavy dependencies"""
    try:
        sport = request.args.get('sport', 'NBA')
        
        # Generate demo performance data
        demo_results = []
        np.random.seed(42)
        
        for i in range(50):
            outcome = 'win' if np.random.random() > 0.45 else 'loss'  # 55% win rate
            amount = np.random.uniform(50, 200)
            odds = np.random.uniform(1.5, 3.0)
            profit = amount * (odds - 1) if outcome == 'win' else -amount
            
            demo_results.append({
                'outcome': outcome,
                'amount': amount,
                'odds': odds,
                'profit': profit
            })
        
        # Analyze performance
        if globals().get('BASIC_ML_ONLY', False):
            from ml.basic_predictor import BasicAnalyzer
            performance = BasicAnalyzer.analyze_betting_performance(demo_results)
        else:
            performance = {'error': 'Advanced analytics not available'}
        
        # Kelly analysis for sample bet
        from ml.basic_predictor import BasicAnalyzer
        kelly_sample = BasicAnalyzer.calculate_kelly_criterion(0.58, 1.85, 1000)
        
        return jsonify({
            'success': True,
            'performance_analysis': performance,
            'kelly_sample': kelly_sample,
            'sport': sport,
            'generated_at': datetime.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/models/gallery', methods=['GET'])
def get_model_gallery():
    """Get model gallery with filtering capabilities"""
    try:
        sport = request.args.get('sport', 'all')
        model_type = request.args.get('type', 'all')
        
        # Demo model gallery
        demo_models = [
            {
                'id': 'nba_basic_statistical',
                'name': 'NBA Statistical Predictor',
                'description': 'Basic statistical model using win percentage, scoring averages, and pace',
                'sport': 'NBA',
                'model_type': 'statistical',
                'accuracy': 68.2,
                'features_count': 6,
                'training_samples': 1000,
                'status': 'active',
                'created_at': '2024-01-15T10:30:00Z'
            },
            {
                'id': 'nfl_basic_statistical',
                'name': 'NFL Statistical Predictor',
                'description': 'Basic model for NFL games using offensive yards and win percentage',
                'sport': 'NFL', 
                'model_type': 'statistical',
                'accuracy': 64.8,
                'features_count': 5,
                'training_samples': 800,
                'status': 'active',
                'created_at': '2024-01-10T14:20:00Z'
            },
            {
                'id': 'mlb_basic_statistical',
                'name': 'MLB Statistical Predictor',
                'description': 'Baseball prediction model using ERA, OPS, and win percentage',
                'sport': 'MLB',
                'model_type': 'statistical', 
                'accuracy': 61.5,
                'features_count': 4,
                'training_samples': 600,
                'status': 'active',
                'created_at': '2024-01-05T09:15:00Z'
            }
        ]
        
        # Apply filters
        filtered_models = demo_models
        if sport != 'all':
            filtered_models = [m for m in filtered_models if m['sport'].lower() == sport.lower()]
        if model_type != 'all':
            filtered_models = [m for m in filtered_models if m['model_type'] == model_type]
        
        return jsonify({
            'success': True,
            'models': filtered_models,
            'total_count': len(filtered_models),
            'available_sports': ['NBA', 'NFL', 'MLB'],
            'available_types': ['statistical', 'ensemble', 'neural'],
            'basic_mode': globals().get('BASIC_ML_ONLY', False)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/models/create', methods=['POST'])
def create_model():
    """Create a new ML model"""
    try:
        data = request.json
        user_id = data.get('user_id', 'anonymous')
        
        model_config = {
            'sport': data.get('sport', 'NBA'),
            'model_type': data.get('model_type', 'statistical'),
            'neural_type': data.get('neural_type', 'lstm'),
            'use_neural': data.get('use_neural', True),
            'description': data.get('description', f"Custom {data.get('sport', 'NBA')} model")
        }
        
        if not ML_AVAILABLE:
            # Return demo response
            model_id = f"demo_{model_config['sport']}_{model_config['model_type']}_{int(time.time())}"
            return jsonify({
                'success': True,
                'model_id': model_id,
                'message': 'Model created successfully (demo mode)'
            }), 201
        
        # Use model manager to create model
        model_id = model_manager.create_model(model_config)
        
        return jsonify({
            'success': True,
            'model_id': model_id,
            'message': 'Model created successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/models/train', methods=['POST'])
def train_model():
    """Train a model asynchronously"""
    try:
        data = request.json
        model_id = data.get('model_id')
        
        if not model_id:
            return jsonify({'success': False, 'error': 'Model ID required'}), 400
        
        training_config = {
            'num_samples': data.get('num_samples', 1000),
            'epochs': data.get('epochs', 50),
            'batch_size': data.get('batch_size', 32),
            'optimize_hyperparams': data.get('optimize_hyperparams', True)
        }
        
        if not ML_AVAILABLE:
            # Return demo response with simulated training
            job_id = f"train_job_{int(time.time())}"
            return jsonify({
                'success': True,
                'job_id': job_id,
                'message': 'Training started (demo mode)'
            }), 200
        
        # Start async training
        job_id = model_manager.train_model_async(model_id, training_config)
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Training started'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/models/training/status/<job_id>', methods=['GET'])
def get_training_status(job_id):
    """Get training job status"""
    try:
        if not ML_AVAILABLE:
            # Return demo status
            return jsonify({
                'success': True,
                'status': 'completed',
                'progress': 100,
                'message': 'Training completed (demo mode)'
            }), 200
        
        status = model_manager.get_training_status(job_id)
        
        return jsonify({
            'success': True,
            **status
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/models/<model_id>/predict', methods=['POST'])
def model_predict(model_id):
    """Make prediction using specific model"""
    try:
        data = request.json
        
        if not ML_AVAILABLE:
            # Return demo prediction
            return jsonify({
                'success': True,
                'prediction': {
                    'predicted_outcome': 'Home Win',
                    'confidence': 0.72,
                    'probabilities': {'Home Win': 0.72, 'Away Win': 0.28}
                },
                'model_id': model_id,
                'demo_mode': True
            }), 200
        
        prediction = model_manager.predict_game(model_id, data)
        
        if 'error' in prediction:
            return jsonify({'success': False, 'error': prediction['error']}), 400
        
        return jsonify({
            'success': True,
            'prediction': prediction,
            'model_id': model_id
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/models/<model_id>/performance', methods=['GET'])
def get_model_performance(model_id):
    """Get model performance metrics"""
    try:
        if not ML_AVAILABLE:
            # Return demo performance data
            return jsonify({
                'success': True,
                'performance': {
                    'accuracy': 0.682,
                    'precision': 0.671,
                    'recall': 0.694,
                    'f1_score': 0.682,
                    'predictions_count': 45,
                    'average_confidence': 0.74
                },
                'model_id': model_id,
                'demo_mode': True
            }), 200
        
        performance = model_manager.get_model_performance(model_id)
        
        if 'error' in performance:
            return jsonify({'success': False, 'error': performance['error']}), 400
        
        return jsonify({
            'success': True,
            'performance': performance,
            'model_id': model_id
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/strategies/model-based', methods=['POST'])
def create_model_based_strategy():
    """Create a strategy that uses a specific ML model"""
    try:
        data = request.json
        user_id = data.get('user_id')
        model_id = data.get('model_id')
        
        if not user_id or not model_id:
            return jsonify({'success': False, 'message': 'User ID and Model ID required'}), 400
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
        
        strategies_collection_user = db.collection(f'users/{user_id}/strategies')
        new_strategy_ref = strategies_collection_user.document()
        strategy_id = new_strategy_ref.id
        
        strategy_data = {
            'id': strategy_id,
            'name': data.get('name', f'ML Strategy ({model_id})'),
            'type': 'model_based',
            'description': data.get('description', f'Strategy powered by ML model {model_id}'),
            'model_id': model_id,
            'parameters': {
                'confidence_threshold': data.get('confidence_threshold', 70),
                'max_bet_percentage': data.get('max_bet_percentage', 3.0),
                'kelly_fraction': data.get('kelly_fraction', 0.25),
                **data.get('parameters', {})
            },
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
        
        return jsonify({
            'success': True,
            'message': 'Model-based strategy created successfully',
            'strategy_id': strategy_id
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to create strategy: {e}'}), 500

@app.route('/api/bots/<bot_id>/assign-model', methods=['POST'])
def assign_model_to_bot():
    """Assign a trained model to a bot for recommendations"""
    try:
        data = request.json
        bot_id = data.get('bot_id')
        model_id = data.get('model_id')
        user_id = data.get('user_id')
        
        if not all([bot_id, model_id, user_id]):
            return jsonify({'success': False, 'message': 'Bot ID, Model ID, and User ID required'}), 400
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
        
        # Update bot configuration to use the model
        bot_ref = bots_collection.document(bot_id)
        bot_doc = bot_ref.get()
        
        if not bot_doc.exists:
            return jsonify({'success': False, 'message': 'Bot not found'}), 404
        
        bot_ref.update({
            'assigned_model_id': model_id,
            'model_assigned_at': datetime.datetime.now().isoformat(),
            'last_updated': datetime.datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': f'Model {model_id} assigned to bot {bot_id}',
            'bot_id': bot_id,
            'model_id': model_id
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to assign model: {e}'}), 500

@app.route('/api/bots/<bot_id>/model-recommendations', methods=['GET'])
def get_bot_model_recommendations(bot_id):
    """Get ML model-powered recommendations for a bot"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
        
        # Get bot data
        bot_ref = bots_collection.document(bot_id)
        bot_doc = bot_ref.get()
        
        if not bot_doc.exists:
            return jsonify({'success': False, 'message': 'Bot not found'}), 404
        
        bot_data = bot_doc.to_dict()
        assigned_model_id = bot_data.get('assigned_model_id')
        
        if not assigned_model_id:
            return jsonify({
                'success': True,
                'recommendations': [],
                'message': 'No model assigned to this bot'
            }), 200
        
        # Get current games data (in demo mode, use sample data)
        sample_games = [
            {
                'game_id': 'game_1',
                'teams': 'Lakers vs Warriors',
                'sport': 'NBA',
                'home_team': 'Lakers',
                'away_team': 'Warriors',
                'commence_time': datetime.datetime.now().isoformat()
            },
            {
                'game_id': 'game_2',
                'teams': 'Celtics vs Heat',
                'sport': 'NBA',
                'home_team': 'Celtics',
                'away_team': 'Heat',
                'commence_time': datetime.datetime.now().isoformat()
            }
        ]
        
        recommendations = []
        
        for game in sample_games:
            # Use model manager to get predictions if available
            if ML_AVAILABLE:
                prediction = model_manager.predict_game(assigned_model_id, {
                    'sport': game['sport'],
                    'home_team': game['home_team'],
                    'away_team': game['away_team']
                })
            else:
                # Demo prediction
                prediction = {
                    'predicted_outcome': 'Home Win',
                    'confidence': 0.72,
                    'probabilities': {'Home Win': 0.72, 'Away Win': 0.28}
                }
            
            if 'error' not in prediction:
                confidence = prediction.get('confidence', 0.5) * 100
                
                # Only recommend if confidence meets bot's threshold
                if confidence >= bot_data.get('confidence_threshold', 60):
                    bet_amount = bot_data.get('current_balance', 1000) * (bot_data.get('bet_percentage', 2.0) / 100)
                    
                    recommendations.append({
                        'game': game,
                        'prediction': prediction,
                        'confidence': confidence,
                        'recommended_bet': {
                            'selection': prediction['predicted_outcome'],
                            'amount': round(bet_amount, 2),
                            'reasoning': f"ML Model prediction with {confidence:.1f}% confidence"
                        },
                        'model_id': assigned_model_id
                    })
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'bot_id': bot_id,
            'model_id': assigned_model_id,
            'total_recommendations': len(recommendations)
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get recommendations: {e}'}), 500

if __name__ == '__main__':
    app.run(debug=True)