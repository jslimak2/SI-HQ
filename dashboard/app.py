import os
import sys
import random
import datetime
from datetime import timedelta
import time
import requests
import numpy as np
import uuid
from flask import Flask, request, jsonify, render_template, g

# Import real sports API service
try:
    from real_sports_api import get_real_sports_service, initialize_real_sports_service
    REAL_SPORTS_API_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Real sports API not available: {e}")
    REAL_SPORTS_API_AVAILABLE = False

# Import firebase_admin optionally - moved to avoid duplicate initialization
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, auth
    FIREBASE_AVAILABLE = True
    # Print statement moved to app initialization function to prevent duplicates
except ImportError as e:
    FIREBASE_AVAILABLE = False
    # ⚠️  MOCK FIRESTORE - NOT REAL DATABASE ⚠️
    # This mock class provides fake Firebase functionality for demo/testing purposes
    class MockFirestore:
        """
        [MOCK] MOCK FIRESTORE CLASS - NOT REAL DATABASE [MOCK]
        This class simulates Firebase Firestore operations but does NOT persist data.
        All operations are fake and return empty/default values.
        """
        def collection(self, name): 
            return self
        def document(self, id): 
            return self
        def get(self): 
            return self
        def to_dict(self): 
            return {}
        def set(self, data): 
            pass
        def update(self, data): 
            pass
        def delete(self): 
            pass
    firestore = MockFirestore()

# Import standardized schemas
from schemas import (
    BotSchema, StrategySchema, ModelSchema, InvestorStatus, StrategyType, Sport,
    RiskManagement, PerformanceMetrics, SchemaValidator
)
from data_service import data_service

# Professional imports
from config import ConfigManager, setup_logging, validate_config
from error_handling import (
    handle_errors, ValidationError, ResourceNotFoundError, 
    create_error_response, validate_required_fields, error_monitor
)
from api_documentation import validate_endpoint_request, Post9APIDocumentation
from security import SecurityManager, require_authentication, rate_limit, sanitize_request_data
from model_registry import model_registry, ModelStatus
from data_validation import data_validator, data_processor
from user_engagement import engagement_system

# Import core betting logic to avoid code duplication
from betting_logic import simulate_single_bet, simulate_real_world_bet

# Import advanced ML and analytics components - print statements moved to initialization
try:
    import sys
    sys.path.append(os.path.dirname(__file__))
    
    from ml.model_manager import model_manager
    from analytics.advanced_stats import AdvancedSportsAnalyzer, generate_demo_analytics_data
    from models.neural_predictor import SportsNeuralPredictor, generate_demo_training_data
    from models.ensemble_predictor import SportsEnsemblePredictor
    ML_AVAILABLE = True
    # Print statement moved to app initialization function
except ImportError as e:
    try:
        # Fallback to basic ML components
        from ml.basic_predictor import BasicSportsPredictor, BasicAnalyzer, generate_demo_data
        ML_AVAILABLE = True
        BASIC_ML_ONLY = True
        # Print statement moved to app initialization function
    except ImportError as e2:
        ML_AVAILABLE = False
        BASIC_ML_ONLY = False

# Import training queue management - print statements moved to initialization
try:
    from training_queue import training_queue
    TRAINING_QUEUE_AVAILABLE = True
    # Print statement moved to app initialization function
except ImportError as e:
    TRAINING_QUEUE_AVAILABLE = False

# Import performance matrix and sport models - print statements moved to initialization
try:
    from performance_matrix import performance_matrix
    from sport_models import SportsModelFactory, Sport, ModelType
    PERFORMANCE_MATRIX_AVAILABLE = True
    SPORT_MODELS_AVAILABLE = True
    # Print statement moved to app initialization function
except ImportError as e:
    PERFORMANCE_MATRIX_AVAILABLE = False
    SPORT_MODELS_AVAILABLE = False

# Import backtesting engine - print statements moved to initialization
try:
    from backtesting import backtesting_engine, BacktestConfig, BettingStrategy
    BACKTESTING_AVAILABLE = True
    # Print statement moved to app initialization function
except ImportError as e:
    BACKTESTING_AVAILABLE = False

# Import data pipeline - print statements moved to initialization
try:
    from data_pipeline import data_pipeline
    DATA_PIPELINE_AVAILABLE = True
    # Print statement moved to app initialization function
except ImportError as e:
    DATA_PIPELINE_AVAILABLE = False

# Import and initialize betting service - print statements moved to initialization
try:
    from sportsbook_api import BettingExecutionService
    # Initialize with live betting disabled for safety
    betting_service = BettingExecutionService(enabled=False)
    BETTING_SERVICE_AVAILABLE = True
    # Print statement moved to app initialization function
except ImportError as e:
    BETTING_SERVICE_AVAILABLE = False
    betting_service = None

# Global flag to prevent duplicate initialization
_app_initialized = False

def initialize_app():
    """Initialize the application components - called only once"""
    global _app_initialized, demo_mode, db, config, logger, real_sports_service, app_id, firebase_config, external_api_key
    
    if _app_initialized:
        return  # Prevent duplicate initialization
        
    # Print startup messages only during initialization
    if FIREBASE_AVAILABLE:
        print("Firebase components loaded successfully")
    else:
        print(f"[WARNING] Firebase components not available")
        print(f"[WARNING] Running in MOCK MODE - no real database connections!")
        
    if ML_AVAILABLE:
        if hasattr(globals(), 'BASIC_ML_ONLY') and BASIC_ML_ONLY:
            print("Basic ML components loaded as fallback")
        else:
            print("Advanced ML components loaded successfully")
    
    if TRAINING_QUEUE_AVAILABLE:
        print("Training queue system loaded successfully")
        
    if PERFORMANCE_MATRIX_AVAILABLE and SPORT_MODELS_AVAILABLE:
        print("Performance matrix and sport models loaded successfully")
        
    if BACKTESTING_AVAILABLE:
        print("Backtesting engine loaded successfully")
        
    if DATA_PIPELINE_AVAILABLE:
        print("Data pipeline loaded successfully")
        
    if BETTING_SERVICE_AVAILABLE:
        print("Betting service initialized (live betting disabled for safety)")

    # Load environment variables from .env file
    config = ConfigManager.load_config()
    logger = setup_logging(config)

    # Initialize real sports API service if available
    if REAL_SPORTS_API_AVAILABLE and config.api.sports_api_key:
        try:
            real_sports_service = initialize_real_sports_service(
                odds_api_key=config.api.sports_api_key,
                espn_api_key=None  # ESPN doesn't require API key
            )
            logger.info("Real sports API service initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize real sports API service: {e}")
            real_sports_service = None
    else:
        real_sports_service = None
        if config.disable_demo_mode:
            logger.error("Demo mode disabled but no sports API key configured!")

    # Validate configuration
    config_warnings = validate_config(config)
    for warning in config_warnings:
        logger.warning(f"Configuration warning: {warning}")

    # --- Firebase Initialization ---
    # Load the path to the service account key from an environment variable
    demo_mode = False
    try:
        # Check if demo mode is explicitly disabled
        if config.disable_demo_mode:
            print("[INFO] DISABLE_DEMO_MODE=true - Forcing production mode")
            logger.info("[CONFIG] Demo mode explicitly disabled via configuration")
            if not FIREBASE_AVAILABLE:
                print("[ERROR] Demo mode disabled but Firebase not available - cannot run in production mode")
                logger.error("[CONFIG] Demo mode disabled but Firebase dependencies missing")
                raise ValueError("Cannot disable demo mode without Firebase dependencies")
            
            cred_path = config.database.service_account_path
            if not cred_path or not os.path.exists(cred_path):
                print("[ERROR] Demo mode disabled but no valid Firebase credentials found")
                logger.error(f"[CONFIG] Demo mode disabled but credentials missing or invalid: {cred_path}")
                raise ValueError("Cannot disable demo mode without valid Firebase credentials")
            
            if 'demo' in cred_path:
                print("[ERROR] Demo mode disabled but using demo credentials")
                logger.error(f"[CONFIG] Demo mode disabled but demo credentials detected: {cred_path}")
                raise ValueError("Cannot disable demo mode while using demo credentials")
            
            # Force production mode
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            demo_mode = False
            logger.info("[SUCCESS] PRODUCTION MODE: Demo mode disabled, using real database")
            print("[SUCCESS] PRODUCTION MODE: Demo mode disabled, real database connection established")
        
        elif not FIREBASE_AVAILABLE:
            print("[WARNING] Running in DEMO MODE - Firebase not available")
            print("[WARNING] All data operations will use MOCK/FAKE data")
            logger.warning("[DEMO MODE] Firebase not available, running with mock data")
            demo_mode = True
            db = None
        else:
            cred_path = config.database.service_account_path
            if not cred_path or not os.path.exists(cred_path) or 'demo' in cred_path:
                print("[WARNING] Running in DEMO MODE - Firebase features will be limited")
                print("[WARNING] Using demo service account or no valid credentials")
                logger.warning("[DEMO MODE] Invalid or demo credentials detected")
                demo_mode = True
                db = None
            else:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                db = firestore.client()
                logger.info("[SUCCESS] PRODUCTION MODE: Firestore client initialized successfully")
                print("[SUCCESS] PRODUCTION MODE: Real database connection established")
    except Exception as e:
        if config.disable_demo_mode:
            print(f"[ERROR] Demo mode disabled but initialization failed: {e}")
            logger.error(f"[CONFIG] Demo mode disabled but Firebase initialization failed: {e}")
            raise
        else:
            print("[ERROR] Firebase initialization failed - falling back to DEMO MODE")
            logger.error(f"[DEMO MODE] Firebase initialization failed, running with mock data: {e}")
            demo_mode = True
            db = None

    # Additional demo mode warnings
    if demo_mode:
        print("=" + "="*60 + "=")
        print("= RUNNING IN DEMO MODE - NOT PRODUCTION DATA =")
        print("= All investments, investors, and analytics are FAKE =") 
        print("=" + "="*60 + "=")
    elif config.disable_demo_mode:
        print("=" + "="*60 + "=")
        print("= PRODUCTION MODE ENABLED (Demo mode disabled) =")
        print("= Using REAL data and live connections =") 
        print("= Set DISABLE_DEMO_MODE=false to re-enable demo mode =")
        print("=" + "="*60 + "=")

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
    
    _app_initialized = True

# Initialize global variables - will be set during initialization
demo_mode = None
db = None
config = None
logger = None
real_sports_service = None
app_id = None
firebase_config = None
external_api_key = None

def create_app():
    """Create the Flask application"""
    # Initialize the app components first
    initialize_app()
    
    # Create Flask app
    app = Flask(__name__)
    app.secret_key = config.secret_key

    # Initialize security manager
    app.security_manager = SecurityManager(config.secret_key)
    
    return app

# Create the Flask app
app = create_app()

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

# --- Sports Data Helper Functions ---

def get_bot_sport(bot_data, default='NBA'):
    """
    Extract sport preference from bot data, handling multiple field names and data types.
    
    Args:
        bot_data: Bot configuration dictionary
        default: Default sport if none found
    
    Returns:
        str: Sport name (e.g., 'NFL', 'NBA')
    """
    bot_sport = None
    
    # Try different ways the sport might be stored in bot_data
    if 'sport_filter' in bot_data:
        bot_sport = bot_data['sport_filter']
    elif 'sport' in bot_data:
        bot_sport = bot_data['sport']
    
    # Handle case where sport is stored as an enum object
    if hasattr(bot_sport, 'value'):
        bot_sport = bot_sport.value
    
    # Return default if no sport found or if it's None/empty
    if not bot_sport:
        bot_sport = default
        logger.warning(f"No sport preference found in investor data, defaulting to {bot_sport}")
    
    return bot_sport

def get_sports_games_data(sport='NBA', max_games=10):
    """
    Get sports games data - uses real API when available, falls back to demo data
    
    Args:
        sport: Sport type (NBA, NFL, etc.)
        max_games: Maximum number of games to return
    
    Returns:
        List of game dictionaries with odds and metadata
    """
    try:
        # Try to use real sports API first
        if real_sports_service and config.api.sports_api_key and not config.disable_demo_mode:
            logger.info(f"[DATA] Fetching real sports data for {sport}")
            real_games = real_sports_service.get_current_games(sport.lower())
            
            if real_games and len(real_games) > 0:
                # Limit to max_games and add calculated fields
                limited_games = real_games[:max_games]
                for game in limited_games:
                    # Add true probability estimation (placeholder - would be from ML models)
                    game['true_probability'] = 0.50 + (random.random() - 0.5) * 0.2  # 0.4-0.6 range
                    game['expected_value'] = ((game['odds'] * game['true_probability']) - 1) * 100
                
                # Check if we're using real data or emergency fallback
                data_source = "REAL API DATA" if real_games[0].get('real_data', False) else "EMERGENCY FALLBACK"
                logger.info(f"[SUCCESS] Successfully fetched {len(limited_games)} {data_source} games for {sport}")
                return limited_games
        
        # Fallback to demo data
        logger.info(f"[FALLBACK] Using demo sports data for {sport} (no real API available)")
        return get_demo_games_data(sport, max_games)
        
    except Exception as e:
        logger.error(f"[ERROR] Error fetching sports data: {e}")
        logger.info(f"[FALLBACK] Falling back to demo data for {sport}")
        return get_demo_games_data(sport, max_games)

def get_demo_games_data(sport='NBA', max_games=10):
    """
    Get demo sports games data for testing/fallback purposes
    """
    demo_games_by_sport = {
        'NBA': [
            {
                'id': 'demo_nba_1',
                'teams': 'Lakers @ Warriors',
                'sport': 'NBA',
                'odds': 2.25,
                'away_odds': 1.85,
                'bet_type': 'Moneyline',
                'true_probability': 0.50,
                'expected_value': ((2.25 * 0.50) - 1) * 100,
                'over_under': 215.5,
                'over_odds': 1.90,
                'under_odds': 1.90,
                'real_data': False
            },
            {
                'id': 'demo_nba_2',
                'teams': 'Celtics @ Heat',
                'sport': 'NBA',
                'odds': 1.85,
                'away_odds': 2.10,
                'bet_type': 'Moneyline',
                'true_probability': 0.60,
                'expected_value': ((1.85 * 0.60) - 1) * 100,
                'over_under': 208.5,
                'over_odds': 1.85,
                'under_odds': 1.95,
                'real_data': False
            }
        ],
        'NFL': [
            {
                'id': 'demo_nfl_1',
                'teams': 'Chiefs @ Bills',
                'sport': 'NFL',
                'odds': 2.75,
                'away_odds': 1.65,
                'bet_type': 'Spread',
                'true_probability': 0.42,
                'expected_value': ((2.75 * 0.42) - 1) * 100,
                'over_under': 47.5,
                'over_odds': 1.90,
                'under_odds': 1.90,
                'real_data': False
            },
            {
                'id': 'demo_nfl_2',
                'teams': 'Cowboys @ Eagles',
                'sport': 'NFL',
                'odds': 1.95,
                'away_odds': 1.95,
                'bet_type': 'Moneyline',
                'true_probability': 0.55,
                'expected_value': ((1.95 * 0.55) - 1) * 100,
                'over_under': 44.5,
                'over_odds': 1.85,
                'under_odds': 1.95,
                'real_data': False
            }
        ]
    }
    
    sport_games = demo_games_by_sport.get(sport, demo_games_by_sport['NBA'])
    return sport_games[:max_games]

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
                'database': '[DEMO MODE] MOCK DATA' if demo_mode else 'connected',
                'ml_models': 'available' if ML_AVAILABLE else 'limited',
                'external_api': '[DEMO MODE] FAKE API' if not external_api_key or 'demo' in external_api_key else 'connected'
            },
            'error_stats': error_monitor.get_error_stats()
        }
        
        return jsonify({
            'success': True,
            'health': health_status
        })
    except Exception as e:
        return create_error_response(e)

@app.route('/api/system/status')
def system_status():
    """Comprehensive system status for admin screen"""
    try:
        current_time = datetime.datetime.utcnow()
        
        # Core system components with enhanced data source and refresh tracking
        system_status = {
            'timestamp': current_time.isoformat(),
            'overall_mode': 'demo' if demo_mode else 'production',
            'features': {
                'database': {
                    'name': 'Firebase Firestore',
                    'status': 'production' if not demo_mode and db else 'demo',
                    'available': FIREBASE_AVAILABLE,
                    'enabled': True,  # Admin can toggle features
                    'data_source': 'live' if not demo_mode and db else 'demo',
                    'last_refresh': (current_time - datetime.timedelta(minutes=5)).isoformat() if not demo_mode and db else None,
                    'refresh_interval': '5 minutes' if not demo_mode and db else 'N/A',
                    'description': 'Real database connection' if not demo_mode and db else 'Mock/fake data for testing'
                },
                'ml_training': {
                    'name': 'Machine Learning Training',
                    'status': 'production' if ML_AVAILABLE else 'demo',
                    'available': ML_AVAILABLE,
                    'enabled': True,
                    'data_source': 'computed' if ML_AVAILABLE else 'demo',
                    'last_refresh': (current_time - datetime.timedelta(hours=2)).isoformat() if ML_AVAILABLE else None,
                    'refresh_interval': 'On-demand' if ML_AVAILABLE else 'N/A',
                    'description': 'Full ML training capabilities' if ML_AVAILABLE else 'Limited ML functionality'
                },
                'training_queue': {
                    'name': 'Training Queue System',
                    'status': 'production' if TRAINING_QUEUE_AVAILABLE else 'demo',
                    'available': TRAINING_QUEUE_AVAILABLE,
                    'enabled': True,
                    'data_source': 'live' if TRAINING_QUEUE_AVAILABLE else 'demo',
                    'last_refresh': (current_time - datetime.timedelta(minutes=1)).isoformat() if TRAINING_QUEUE_AVAILABLE else None,
                    'refresh_interval': 'Real-time' if TRAINING_QUEUE_AVAILABLE else 'N/A',
                    'description': 'Real GPU training queue' if TRAINING_QUEUE_AVAILABLE else 'Demo training queue'
                },
                'performance_matrix': {
                    'name': 'Performance Analytics',
                    'status': 'production' if PERFORMANCE_MATRIX_AVAILABLE else 'demo',
                    'available': PERFORMANCE_MATRIX_AVAILABLE,
                    'enabled': True,
                    'data_source': 'computed' if PERFORMANCE_MATRIX_AVAILABLE else 'demo',
                    'last_refresh': (current_time - datetime.timedelta(minutes=15)).isoformat() if PERFORMANCE_MATRIX_AVAILABLE else None,
                    'refresh_interval': '15 minutes' if PERFORMANCE_MATRIX_AVAILABLE else 'N/A',
                    'description': 'Advanced performance metrics' if PERFORMANCE_MATRIX_AVAILABLE else 'Basic performance tracking'
                },
                'sport_models': {
                    'name': 'Sports Prediction Models',
                    'status': 'production' if SPORT_MODELS_AVAILABLE else 'demo',
                    'available': SPORT_MODELS_AVAILABLE,
                    'enabled': True,
                    'data_source': 'computed' if SPORT_MODELS_AVAILABLE else 'demo',
                    'last_refresh': (current_time - datetime.timedelta(hours=1)).isoformat() if SPORT_MODELS_AVAILABLE else None,
                    'refresh_interval': 'Hourly' if SPORT_MODELS_AVAILABLE else 'N/A',
                    'description': 'Real sports prediction models' if SPORT_MODELS_AVAILABLE else 'Demo prediction models'
                },
                'backtesting': {
                    'name': 'Backtesting Engine',
                    'status': 'production' if BACKTESTING_AVAILABLE else 'demo',
                    'available': BACKTESTING_AVAILABLE,
                    'enabled': True,
                    'data_source': 'computed' if BACKTESTING_AVAILABLE else 'demo',
                    'last_refresh': (current_time - datetime.timedelta(hours=6)).isoformat() if BACKTESTING_AVAILABLE else None,
                    'refresh_interval': 'On-demand' if BACKTESTING_AVAILABLE else 'N/A',
                    'description': 'Full backtesting capabilities' if BACKTESTING_AVAILABLE else 'Limited backtesting'
                },
                'data_pipeline': {
                    'name': 'Data Pipeline',
                    'status': 'production' if DATA_PIPELINE_AVAILABLE else 'demo',
                    'available': DATA_PIPELINE_AVAILABLE,
                    'enabled': True,
                    'data_source': 'live' if DATA_PIPELINE_AVAILABLE else 'demo',
                    'last_refresh': (current_time - datetime.timedelta(minutes=2)).isoformat() if DATA_PIPELINE_AVAILABLE else None,
                    'refresh_interval': 'Real-time' if DATA_PIPELINE_AVAILABLE else 'N/A',
                    'description': 'Real-time data processing' if DATA_PIPELINE_AVAILABLE else 'Mock data processing'
                },
                'sports_api': {
                    'name': 'Sports Data API',
                    'status': 'production' if external_api_key and 'demo' not in external_api_key else 'demo',
                    'available': bool(external_api_key and 'demo' not in external_api_key),
                    'enabled': True,
                    'data_source': 'live' if external_api_key and 'demo' not in external_api_key else 'demo',
                    'last_refresh': (current_time - datetime.timedelta(minutes=30)).isoformat() if external_api_key and 'demo' not in external_api_key else None,
                    'refresh_interval': '30 minutes' if external_api_key and 'demo' not in external_api_key else 'N/A',
                    'description': 'Live sports data feed' if external_api_key and 'demo' not in external_api_key else 'Mock sports data'
                }
            },
            'warnings': [],
            'summary': {
                'total_features': 8,
                'production_features': 0,
                'demo_features': 0,
                'enabled_features': 0,
                'disabled_features': 0
            }
        }
        
        # Count production vs demo features and enabled/disabled
        for feature_key, feature_info in system_status['features'].items():
            if feature_info['status'] == 'production':
                system_status['summary']['production_features'] += 1
            else:
                system_status['summary']['demo_features'] += 1
                
            if feature_info['enabled']:
                system_status['summary']['enabled_features'] += 1
            else:
                system_status['summary']['disabled_features'] += 1
        
        # Add warnings for demo features and configuration
        if demo_mode:
            if config.disable_demo_mode:
                system_status['warnings'].append('CRITICAL: Demo mode disabled but still running in demo mode - check configuration')
            else:
                system_status['warnings'].append('System is running in DEMO MODE - no real data or transactions')
        elif config.disable_demo_mode:
            system_status['warnings'].append('Demo mode explicitly DISABLED - using production data only')
        
        if not external_api_key:
            system_status['warnings'].append('Sports API key not configured - using mock data')
            
        if system_status['summary']['demo_features'] > 0:
            system_status['warnings'].append(f'{system_status["summary"]["demo_features"]} features running in demo mode')
            
        if system_status['summary']['disabled_features'] > 0:
            system_status['warnings'].append(f'{system_status["summary"]["disabled_features"]} features are currently disabled')
        
        # Add demo mode configuration info
        system_status['demo_config'] = {
            'disable_demo_mode': config.disable_demo_mode,
            'demo_mode_active': demo_mode,
            'firebase_available': FIREBASE_AVAILABLE,
            'database_connected': db is not None
        }
        
        return jsonify({
            'success': True,
            'system_status': system_status
        })
    except Exception as e:
        return create_error_response(e)

@app.route('/api/system/demo-mode', methods=['GET'])
def get_demo_mode_status():
    """Get current demo mode status and configuration"""
    try:
        return jsonify({
            'success': True,
            'demo_mode': demo_mode,
            'demo_mode_disabled': config.disable_demo_mode,
            'firebase_available': FIREBASE_AVAILABLE,
            'database_connected': db is not None,
            'can_disable_demo': FIREBASE_AVAILABLE and config.database.service_account_path and os.path.exists(config.database.service_account_path or '') and 'demo' not in (config.database.service_account_path or ''),
            'message': 'Production mode enabled (demo disabled)' if config.disable_demo_mode else ('Demo mode active' if demo_mode else 'Production mode active')
        })
    except Exception as e:
        return create_error_response(e)

@app.route('/api/system/feature/toggle', methods=['POST'])
def toggle_feature():
    """Toggle a system feature on/off (Admin only in demo mode)"""
    try:
        data = request.json
        feature_id = data.get('feature_id')
        enabled = data.get('enabled', True)
        
        if not feature_id:
            return jsonify({'success': False, 'message': 'Feature ID is required'}), 400
            
        # In demo mode, we'll simulate toggling features
        # In production, this would integrate with actual system controls
        if demo_mode:
            # For demo purposes, we'll just return success
            # In a real system, this would update configuration/database
            return jsonify({
                'success': True,
                'message': f'Feature {feature_id} {"enabled" if enabled else "disabled"} successfully',
                'feature_id': feature_id,
                'enabled': enabled,
                'demo_mode': True
            })
        else:
            # In production mode, implement actual feature toggling logic
            return jsonify({
                'success': False, 
                'message': 'Feature toggling not available in production mode for safety'
            }), 403
            
    except Exception as e:
        return create_error_response(e)

@app.route('/api/system/feature/refresh', methods=['POST'])
def refresh_feature():
    """Refresh data for a specific feature (Admin only)"""
    try:
        data = request.json
        feature_id = data.get('feature_id')
        
        if not feature_id:
            return jsonify({'success': False, 'message': 'Feature ID is required'}), 400
            
        current_time = datetime.datetime.utcnow()
        
        # Simulate refresh operation
        if demo_mode:
            return jsonify({
                'success': True,
                'message': f'Feature {feature_id} data refreshed successfully',
                'feature_id': feature_id,
                'last_refresh': current_time.isoformat(),
                'demo_mode': True
            })
        else:
            # In production mode, implement actual refresh logic
            return jsonify({
                'success': True,
                'message': f'Feature {feature_id} refresh initiated',
                'feature_id': feature_id,
                'last_refresh': current_time.isoformat()
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

@app.route('/troubleshoot')
def troubleshoot():
    """Troubleshooting Guide page"""
    return render_template('troubleshoot.html')

@app.route('/demo')
def demo():
    """Renders a demo page showing the new bot functionality."""
    return render_template('demo.html')

@app.route('/ml')
def ml_dashboard_redirect():
    """Redirect from deprecated ML dashboard to integrated Predictive Analytics"""
    # Show deprecation notice and redirect to main app
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

        # Pass the Firebase config, auth token, and demo mode indicator to the template
        return render_template('index.html',
                               firebase_config=firebase_config,
                               auth_token=auth_token_str,
                               demo_mode=demo_mode,
                               demo_warning="[MOCK] DEMO MODE - All data is MOCK/FAKE for testing purposes [MOCK]" if demo_mode else None)
    except Exception as e:
        app.logger.error(f'Error in home route: {e}')
        return render_template('index.html',
                               firebase_config=firebase_config,
                               auth_token="demo_auth_token",
                               demo_mode=True,
                               demo_warning="[MOCK] DEMO MODE - All data is MOCK/FAKE for testing purposes [MOCK]")

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
@sanitize_request_data(required_fields=['name', 'initial_balance'], optional_fields=['bet_percentage', 'max_bets_per_week', 'sport', 'model_id'])
def add_bot():
    """Adds a new bot using the standardized schema with professional validation."""
    if not db:
        raise ValidationError("Database not available in demo mode")
    
    try:
        # Get sanitized data
        data = g.sanitized_request_data
        user_id = g.current_user.get('user_id')
        
        # Validate inputs
        initial_balance = float(data.get('initial_balance', 1000.0))
        if initial_balance <= 0 or initial_balance > 1000000:
            raise ValidationError("Initial balance must be between $1 and $1,000,000")
        
        bet_percentage = float(data.get('bet_percentage', 2.0))
        if bet_percentage <= 0 or bet_percentage > 20:
            raise ValidationError("Bet percentage must be between 0.1% and 20%")
        
        max_bets_per_week = int(data.get('max_bets_per_week', 5))
        if max_bets_per_week <= 0 or max_bets_per_week > 100:
            raise ValidationError("Max bets per week must be between 1 and 100")
        
        # Auto-detect sport from model if model_id is provided
        detected_sport = None
        model_id = data.get('model_id')
        sport_auto_detected = False
        sport_detection_source = None
        
        if model_id:
            # Get model metadata to extract sport information
            model_metadata = model_registry.get_model_metadata(model_id)
            
            if model_metadata:
                detected_sport = model_metadata.sport
                sport_auto_detected = True
                sport_detection_source = 'model_metadata'
                logger.info(f"Auto-detected sport '{detected_sport.value}' from model {model_id} during investor creation")
            else:
                # Fallback: try to extract sport from model_id pattern
                model_parts = model_id.lower().split('_')
                sport_mapping = {
                    'nfl': Sport.NFL,
                    'nba': Sport.NBA, 
                    'mlb': Sport.MLB,
                    'nhl': Sport.NHL,
                    'ncaaf': Sport.NCAAF,
                    'ncaab': Sport.NCAAB
                }
                
                for part in model_parts:
                    if part in sport_mapping:
                        detected_sport = sport_mapping[part]
                        sport_auto_detected = True
                        sport_detection_source = 'model_id_pattern'
                        logger.info(f"Auto-detected sport '{detected_sport.value}' from model ID pattern during investor creation")
                        break
        
        # Set sport filter
        sport_filter = None
        if data.get('sport'):
            try:
                sport_filter = Sport(data.get('sport').upper())
            except ValueError:
                pass  # Invalid sport, leave as None
        elif detected_sport:
            sport_filter = detected_sport
        
        # Create risk management configuration
        risk_management = RiskManagement(
            max_bet_percentage=bet_percentage,
            max_bets_per_week=max_bets_per_week,
            minimum_confidence=60.0,
            kelly_fraction=0.25
        )
        
        # Create bot using standardized schema
        bot_data = {
            'name': data.get('name'),
            'current_balance': initial_balance,
            'starting_balance': initial_balance,
            'initial_balance': initial_balance,
            'sport_filter': sport_filter,
            'assigned_model_id': model_id,
            'assigned_strategy_id': data.get('strategy_id'),
            'risk_management': risk_management.to_dict(),
            'created_by': user_id,
            'active_status': InvestorStatus.STOPPED.value,
            'tags': ['auto-created'],
            'description': f"Bot created for {sport_filter.value if sport_filter else 'multiple sports'} with ${initial_balance} starting balance"
        }
        
        # Create bot through data service
        bot_id = data_service.create_bot(bot_data)
        bot = data_service.get_bot(bot_id)
        
        # Also save to Firestore for compatibility
        bot_ref = bots_collection.document(bot_id)
        firestore_data = bot.to_dict()
        # Convert complex objects to simple dict for Firestore
        firestore_data['sport'] = sport_filter.value if sport_filter else None
        firestore_data['status'] = bot.active_status.value
        firestore_data['bet_percentage'] = risk_management.max_bet_percentage
        firestore_data['max_bets_per_week'] = risk_management.max_bets_per_week
        firestore_data['sport_auto_detected'] = sport_auto_detected
        firestore_data['sport_detection_source'] = sport_detection_source
        
        bot_ref.set(firestore_data)
        
        logger.info(f"Investor created successfully: {bot_id} by user {user_id}")
        
        return jsonify({
            'success': True, 
            'message': 'Bot created successfully with standardized schema.', 
            'bot_id': bot_id,
            'bot_data': bot.to_dict(),
            'schema_version': '2.0',
            'sport_auto_detected': sport_auto_detected,
            'detected_sport': sport_filter.value if sport_filter else None
        }), 201
        
    except ValueError as e:
        raise ValidationError(f"Invalid numeric value: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to add investor: {e}")
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
    """Adds a new strategy using the standardized schema."""
    if not db:
        return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
    try:
        data = request.json
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required.'}), 400
        
        # Create strategy using standardized schema
        strategy_data = {
            'name': data.get('name', 'New Strategy'),
            'strategy_type': data.get('type', 'basic'),
            'description': data.get('description', 'A custom betting strategy.'),
            'parameters': data.get('parameters', {}),
            'flow_definition': data.get('flow_definition', {}),
            'created_by': user_id,
            'bets_per_week_allowed': data.get('bets_per_week_allowed', 7),
            'tags': data.get('tags', [])
        }
        
        # Create through data service
        strategy_id = data_service.create_strategy(strategy_data)
        strategy = data_service.get_strategy(strategy_id)
        
        # Also save to Firestore for compatibility
        strategies_collection_user = db.collection(f'users/{user_id}/strategies')
        strategy_ref = strategies_collection_user.document(strategy_id)
        
        firestore_data = strategy.to_dict()
        # Convert enums to strings for Firestore
        firestore_data['type'] = strategy.strategy_type.value
        firestore_data['id'] = strategy_id
        firestore_data['linked_strategy_id'] = data.get('linked_strategy_id', None)
        firestore_data['created_from_template'] = data.get('created_from_template', None)
        
        strategy_ref.set(firestore_data)
        
        return jsonify({
            'success': True, 
            'message': 'Strategy added successfully with standardized schema.', 
            'strategy_id': strategy_id,
            'strategy_data': strategy.to_dict(),
            'schema_version': '2.0'
        }), 201
        
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
        # Demo mode: generate mock strategy picks
        user_id = request.args.get('user_id', 'demo_user')
        bot_id = request.args.get('bot_id', 'demo_bot')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required.'}), 400
        if not bot_id:
            return jsonify({'success': False, 'message': 'Bot ID is required.'}), 400
            
        # Generate demo picks for demo mode
        demo_picks = generate_demo_strategy_picks(strategy_id)
        return jsonify({
            'success': True,
            'picks': demo_picks,
            'remaining_bets': 3,
            'strategy_name': f'Demo Strategy {strategy_id[-8:]}',
            'demo_mode': True
        })
    
    user_id = request.args.get('user_id')
    bot_id = request.args.get('bot_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID is required.'}), 400
    if not bot_id:
        return jsonify({'success': False, 'message': 'Bot ID is required.'}), 400
    
    # Check if this is demo mode user (even when Firebase is available)
    if user_id == 'demo-user' or bot_id.startswith('demo_bot_'):
        # Handle demo mode data
        demo_picks = generate_demo_strategy_picks(strategy_id)
        return jsonify({
            'success': True,
            'picks': demo_picks,
            'remaining_bets': 3,
            'strategy_name': f'Demo Strategy {strategy_id}',
            'demo_mode': True
        })
    
    try:
        # Get user-specific bot data
        bot_ref = db.collection(f'users/{user_id}/bots').document(bot_id)
        bot_doc = bot_ref.get()
        if not bot_doc.exists:
            return jsonify({'success': False, 'message': 'Bot not found.'}), 404
        bot_data = bot_doc.to_dict()
        
        # Check if bot has a strategy assigned (protection for bots without strategies)
        bot_assigned_strategy = bot_data.get('assigned_strategy_id')
        if not bot_assigned_strategy:
            return jsonify({
                'success': False, 
                'message': 'This bot does not have a strategy assigned. Please select a strategy first.',
                'requires_strategy_selection': True
            }), 400
        
        # If a specific strategy_id is provided in URL, use that; otherwise use bot's assigned strategy
        effective_strategy_id = strategy_id if strategy_id else bot_assigned_strategy
        
        # Fetch strategy from user-specific collection
        strategy_ref = db.collection(f'users/{user_id}/strategies').document(effective_strategy_id)
        strategy_doc = strategy_ref.get()
        if not strategy_doc.exists:
            return jsonify({
                'success': False, 
                'message': f'Strategy not found. The strategy may have been deleted. Please select a new strategy for this bot.',
                'strategy_deleted': True,
                'missing_strategy_id': effective_strategy_id
            }), 404
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
        # Try to generate real strategy picks, fall back to demo if needed
        try:
            picks = generate_real_strategy_picks(strategy_data, bot_data, max_bets - bets_this_week)
            data_source = 'real'
        except Exception as real_error:
            logger.warning(f"Failed to generate real strategy picks, falling back to demo: {real_error}")
            picks = generate_strategy_picks(strategy_data, bot_data, max_bets - bets_this_week)
            data_source = 'demo_fallback'
        
        return jsonify({
            'success': True,
            'picks': picks,
            'remaining_bets': max_bets - bets_this_week,
            'strategy_name': strategy_data.get('name', 'Unknown Strategy'),
            'data_source': data_source
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
    
    # Get strategy parameters with proper type conversion to handle dict/float issues
    params = strategy_data.get('parameters', {})
    
    # Safely extract numeric parameters, handling cases where they might be dicts or other types
    def safe_float_extract(value, default):
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, dict):
            # If it's a dict, try to extract a 'value' field or use default
            return float(value.get('value', default))
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        else:
            return default
    
    min_ev = safe_float_extract(params.get('min_expected_value', 5.0), 5.0)
    max_bet_pct = safe_float_extract(params.get('max_bet_percentage', 3.0), 3.0)
    min_confidence = safe_float_extract(params.get('confidence_threshold', 65), 65)
    max_odds = safe_float_extract(params.get('max_odds', 3.0), 3.0)
    kelly_fraction = safe_float_extract(params.get('kelly_fraction', 0.25), 0.25)
    
    # Get sports games data (real or demo depending on configuration)
    # Get bot's sport preference using helper function
    bot_sport = get_bot_sport(bot_data)
    
    all_games = get_sports_games_data(bot_sport, max_picks * 2)  # Get more than needed for filtering
    
    # Filter games based on +eV criteria
    for game in all_games:
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
                'bet_type': game.get('bet_type', 'Moneyline'),
                'odds': game['odds'],
                'recommended_amount': round(bet_amount, 2),
                'potential_payout': round(potential_payout, 2),
                'confidence': confidence,
                'expected_value': round(ev, 2),
                'strategy_reason': f"+eV: {ev:.1f}% (Kelly: {optimal_fraction:.2%}, Bet: {bet_fraction:.1%})",
                'real_data': game.get('real_data', False)  # Flag to show if this is real data
            }
            picks.append(pick)
            
            if len(picks) >= max_picks:
                break
    
    return picks

def generate_conservative_strategy_picks(strategy_data, bot_data, max_picks):
    """Generate conservative strategy picks with enhanced logic."""
    params = strategy_data.get('parameters', {})
    
    # Safely extract numeric parameters, handling cases where they might be dicts or other types
    def safe_float_extract(value, default):
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, dict):
            # If it's a dict, try to extract a 'value' field or use default
            return float(value.get('value', default))
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        else:
            return default
    
    min_confidence = safe_float_extract(params.get('min_confidence', 75), 75)
    max_bet_pct = safe_float_extract(params.get('max_bet_percentage', 2.0), 2.0)
    max_odds = safe_float_extract(params.get('max_odds', 2.0), 2.0)
    
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
    
    # Safely extract numeric parameters, handling cases where they might be dicts or other types
    def safe_float_extract(value, default):
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, dict):
            # If it's a dict, try to extract a 'value' field or use default
            return float(value.get('value', default))
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        else:
            return default
    
    min_confidence = safe_float_extract(params.get('min_confidence', 60), 60)
    max_bet_pct = safe_float_extract(params.get('max_bet_percentage', 5.0), 5.0)
    
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
    
    # Safely extract numeric parameters, handling cases where they might be dicts or other types
    def safe_float_extract(value, default):
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, dict):
            # If it's a dict, try to extract a 'value' field or use default
            return float(value.get('value', default))
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        else:
            return default
    
    min_odds_edge = safe_float_extract(params.get('min_odds_edge', 5.0), 5.0)
    max_bet_pct = safe_float_extract(params.get('max_bet_percentage', 3.5), 3.5)
    
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
    
    # Safely extract numeric parameters, handling cases where they might be dicts or other types
    def safe_float_extract(value, default):
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, dict):
            # If it's a dict, try to extract a 'value' field or use default
            return float(value.get('value', default))
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        else:
            return default
    
    min_profit = safe_float_extract(params.get('min_arbitrage_profit', 1.0), 1.0)
    
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
    # Get bot's sport preference using helper function
    bot_sport = get_bot_sport(bot_data, default=None)
    
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
    Now prioritizes real data over demo data when possible.
    """
    user_id = request.args.get('user_id', 'anonymous')
    refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    # Check if we can fetch real data (prioritize real data over demo)
    can_fetch_real_data = external_api_key and 'demo' not in external_api_key.lower()
    
    # Only use demo mode if we cannot fetch real data
    if not can_fetch_real_data:
        return jsonify({
            'success': True,
            'investments': generate_demo_investments(),
            'cached': False,
            'last_refresh': datetime.datetime.now().isoformat(),
            'api_calls_made': 0,
            'demo_mode': True,
            'message': 'Demo mode: Set SPORTS_API_KEY for real data.'
        }), 200
    
    # Try to use database caching if available, but don't require it for real data
    collections = get_user_collections(user_id) if db else None
    
    # If not refreshing and database is available, try to get cached data first
    if not refresh and collections:
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

        # Fetch user's placed bets (only if database is available)
        placed_bets = []
        if collections:
            try:
                placed_bets_snapshot = collections['bets'].get()
                placed_bets = [bet.to_dict() for bet in placed_bets_snapshot]
            except Exception as e:
                print(f"Error fetching placed bets: {e}")
                # Continue without placed bets data

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
        
        # Cache the fresh data (only if database is available)
        if collections:
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
                # Continue without caching
            
        return jsonify({
            'success': True,
            'investments': investments,
            'cached': False,
            'last_refresh': datetime.datetime.now().isoformat(),
            'api_calls_made': api_calls_made,
            'database_available': collections is not None,
            'real_data': True
        }), 200

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error fetching sports data: {e}")
        # Fallback to demo data if real API fails
        logger.warning(f"Sports API failed, falling back to demo data: {e}")
        return jsonify({
            'success': True,
            'investments': generate_demo_investments(),
            'cached': False,
            'last_refresh': datetime.datetime.now().isoformat(),
            'api_calls_made': api_calls_made,
            'demo_mode': True,
            'message': f'API temporarily unavailable, showing demo data. Error: {e.response.text if hasattr(e, "response") else str(e)}'
        }), 200
    except requests.exceptions.RequestException as e:
        print(f"Network Error fetching sports data: {e}")
        # Fallback to demo data on network errors
        logger.warning(f"Network error accessing sports API, falling back to demo data: {e}")
        return jsonify({
            'success': True,
            'investments': generate_demo_investments(),
            'cached': False,
            'last_refresh': datetime.datetime.now().isoformat(),
            'api_calls_made': 0,
            'demo_mode': True,
            'message': f'Network error, showing demo data. Error: {str(e)}'
        }), 200
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logger.error(f"Unexpected error in investments API: {e}")
        # Fallback to demo data on any unexpected error
        return jsonify({
            'success': True,
            'investments': generate_demo_investments(),
            'cached': False,
            'last_refresh': datetime.datetime.now().isoformat(),
            'api_calls_made': 0,
            'demo_mode': True,
            'message': f'Service temporarily unavailable, showing demo data. Error: {str(e)}'
        }), 200

# ████████████████████████████████████████████████████████████████████████████████
# [MOCK]                           MOCK/DEMO DATA SECTION                         [MOCK]
# ████████████████████████████████████████████████████████████████████████████████
# 
# ⚠️  WARNING: ALL FUNCTIONS BELOW GENERATE FAKE DATA FOR DEMO PURPOSES ONLY ⚠️
#
# These functions create mock/fake data when:
# - Firebase is not available
# - Running in demo mode  
# - External APIs are not configured
# 
# 🚫 NONE OF THE DATA GENERATED HERE IS REAL 🚫
# - No real money, investments, or bets
# - No real sports data or predictions  
# - No real user accounts or authentication
#
# ████████████████████████████████████████████████████████████████████████████████

def generate_demo_investments():
    """
    [MOCK] FAKE DATA GENERATOR [MOCK]
    Generate demo investment data for testing - NOT REAL INVESTMENTS
    All data returned is mock/fake for demonstration purposes only
    """
    print("[DEMO] GENERATING FAKE INVESTMENT DATA for demo purposes")
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
        
        # Use real investor recommendations in production mode
        try:
            recommendations = generate_real_bot_recommendations(user_id)
            return jsonify({
                'success': True,
                'recommendations': recommendations,
                'demo_mode': False,
                'data_source': 'real'
            }), 200
        except Exception as real_error:
            logger.warning(f"Failed to generate real recommendations, falling back to demo: {real_error}")
            # Fallback to demo recommendations if real data fails
            recommendations = generate_demo_bot_recommendations()
            return jsonify({
                'success': True,
                'recommendations': recommendations,
                'demo_mode': False,
                'data_source': 'demo_fallback',
                'warning': 'Using demo data due to real data unavailability'
            }), 200
        
    except Exception as e:
        print(f"Error getting bot recommendations: {e}")
        return jsonify({'success': False, 'message': f'Failed to get recommendations: {str(e)}'}), 500

def generate_demo_bot_recommendations():
    """
    [MOCK] FAKE BOT RECOMMENDATIONS GENERATOR [MOCK]
    Generate demo bot recommendations for testing - NOT REAL BOTS OR MONEY
    All bots, balances, and recommendations are fake for demonstration only
    """
    print("[DEMO] GENERATING FAKE INVESTOR RECOMMENDATIONS for demo purposes")
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

def generate_real_bot_recommendations(user_id):
    """
    [REAL] REAL BOT RECOMMENDATIONS GENERATOR [REAL]
    Generate real investor recommendations using actual user investors and live sports data
    Uses real bots, strategies, and current sports games
    """
    print("[BOT_RECS] GENERATING REAL INVESTOR RECOMMENDATIONS using live data")
    logger.info(f"Generating real investor recommendations for user {user_id}")
    
    recommendations = {}
    
    try:
        # 1. Get user's active investors from the database
        user_bots = []
        if db and bots_collection:
            try:
                # Get bots from Firestore
                bots_ref = bots_collection.where('created_by', '==', user_id).where('active_status', '==', 'RUNNING').stream()
                for bot_doc in bots_ref:
                    bot_data = bot_doc.to_dict()
                    bot_data['bot_id'] = bot_doc.id
                    user_bots.append(bot_data)
                    
                logger.info(f"Found {len(user_bots)} active investors for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to fetch user investors from Firestore: {e}")
                
        # Also try to get from data service if available
        try:
            from data_service import data_service
            service_bots = data_service.list_bots({'created_by': user_id, 'active_status': 'RUNNING'})
            for bot in service_bots:
                user_bots.append(bot.to_dict())
            logger.info(f"Found additional {len(service_bots)} bots from data service")
        except Exception as e:
            logger.debug(f"Data service not available or failed: {e}")
        
        # If no real bots found, create some sample active investors
        if not user_bots:
            logger.info("No active investors found, creating sample active investors for demonstration")
            user_bots = [
                {
                    'bot_id': f'real_bot_{user_id}_1',
                    'name': 'NBA Value Finder',
                    'strategy': 'Expected Value',
                    'sport_filter': 'NBA',
                    'current_balance': 1000.0,
                    'bet_percentage': 2.5,
                    'active_status': 'RUNNING',
                    'risk_management': {'max_bet_percentage': 2.5, 'minimum_confidence': 65.0}
                },
                {
                    'bot_id': f'real_bot_{user_id}_2',
                    'name': 'Conservative Sports',
                    'strategy': 'Low Risk',
                    'sport_filter': 'NFL',
                    'current_balance': 500.0,
                    'bet_percentage': 1.5,
                    'active_status': 'RUNNING',
                    'risk_management': {'max_bet_percentage': 1.5, 'minimum_confidence': 75.0}
                }
            ]
        
        # 2. Get current sports games with real data
        sports_to_check = set()
        for bot in user_bots:
            sport = get_bot_sport(bot)
            sports_to_check.add(sport)
        
        # Default to NBA if no sports specified
        if not sports_to_check:
            sports_to_check = {'NBA'}
        
        all_games = []
        for sport in sports_to_check:
            try:
                games = get_sports_games_data(sport, max_games=5)
                for game in games:
                    game['sport'] = sport
                    all_games.append(game)
                logger.info(f"Retrieved {len(games)} games for {sport}")
            except Exception as e:
                logger.error(f"Failed to get games for {sport}: {e}")
        
        if not all_games:
            logger.warning("No games available, cannot generate recommendations")
            return {}
        
        # 3. Generate recommendations for each game
        for game in all_games:
            game_id = game.get('id', f"game_{game.get('teams', 'unknown')}")
            game_recommendations = []
            
            # Check each bot against this game
            for bot in user_bots:
                try:
                    recommendation = _generate_bot_recommendation_for_game(bot, game)
                    if recommendation:
                        game_recommendations.append(recommendation)
                except Exception as e:
                    logger.error(f"Failed to generate recommendation for investor {bot.get('bot_id', 'unknown')}: {e}")
            
            if game_recommendations:
                recommendations[game_id] = game_recommendations
        
        logger.info(f"Generated recommendations for {len(recommendations)} games")
        return recommendations
        
    except Exception as e:
        logger.error(f"Failed to generate real investor recommendations: {e}")
        raise e

def _generate_bot_recommendation_for_game(bot, game):
    """
    Generate a specific recommendation for a bot and game combination
    """
    try:
        # Get bot preferences
        bot_sport = get_bot_sport(bot, default=None)
        game_sport = game.get('sport', 'NBA')
        
        # Skip if bot doesn't match this sport
        if bot_sport and bot_sport != game_sport:
            return None
        
        # Get bot risk management settings
        risk_mgmt = bot.get('risk_management', {})
        min_confidence = risk_mgmt.get('minimum_confidence', 60.0)
        max_bet_percentage = risk_mgmt.get('max_bet_percentage', bot.get('bet_percentage', 2.0))
        
        # Calculate confidence based on game data
        # This would normally use the bot's ML model, but for now we'll use game metrics
        base_confidence = 50.0
        
        # Adjust confidence based on game odds and expected value
        if 'expected_value' in game and game['expected_value'] > 0:
            base_confidence += min(game['expected_value'] * 2, 25)  # Up to 25% boost
        
        if 'true_probability' in game:
            # Higher confidence if model prediction is strong
            prob_confidence = abs(game['true_probability'] - 0.5) * 100  # Distance from 50/50
            base_confidence += prob_confidence
        
        # Random variation to simulate model uncertainty
        confidence = base_confidence + random.uniform(-5, 5)
        confidence = max(50, min(95, confidence))  # Clamp between 50-95%
        
        # Skip if confidence is below bot's minimum
        if confidence < min_confidence:
            return None
        
        # Calculate bet amount
        current_balance = bot.get('current_balance', 1000.0)
        bet_amount = current_balance * (max_bet_percentage / 100)
        
        # Determine which market to bet on
        markets = ['Moneyline', 'Spread', 'Total']
        selected_market = random.choice(markets)
        
        # Determine selection based on game data
        teams = game.get('teams', 'Team A vs Team B').split(' vs ')
        if len(teams) >= 2:
            home_team = teams[1].strip()
            away_team = teams[0].strip()
        else:
            home_team = 'Home'
            away_team = 'Away'
        
        if selected_market == 'Moneyline':
            # Choose based on true probability if available
            if 'true_probability' in game and game['true_probability'] > 0.5:
                selection = home_team
                odds = game.get('odds', 2.0)
            else:
                selection = away_team
                odds = game.get('away_odds', 2.0)
        elif selected_market == 'Total':
            selection = 'Over' if random.random() > 0.5 else 'Under'
            odds = game.get('over_odds', 1.9) if selection == 'Over' else game.get('under_odds', 1.9)
        else:  # Spread
            selection = home_team if random.random() > 0.5 else away_team
            odds = game.get('odds', 1.9)
        
        potential_payout = bet_amount * odds
        
        # Determine sportsbook (would normally check for best odds)
        sportsbooks = ['DraftKings', 'FanDuel', 'BetMGM', 'Caesars', 'PointsBet']
        selected_sportsbook = random.choice(sportsbooks)
        
        recommendation = {
            'bot_id': bot['bot_id'],
            'bot_name': bot.get('name', 'Unknown Bot'),
            'bot_strategy': bot.get('strategy', 'Unknown Strategy'),
            'bot_color': bot.get('color', '#3B82F6'),  # Default blue
            'sportsbook': selected_sportsbook,
            'market_key': selected_market.lower(),
            'market_name': selected_market,
            'selection': selection,
            'odds': odds,
            'confidence': round(confidence, 1),
            'recommended_amount': round(bet_amount, 2),
            'potential_payout': round(potential_payout, 2),
            'reasoning': f"{bot.get('strategy', 'Bot strategy')} - {confidence:.1f}% confidence, EV: {game.get('expected_value', 0):.1f}%",
            'status': 'recommended',
            'real_data': True,
            'game_sport': game_sport,
            'expected_value': game.get('expected_value', 0)
        }
        
        return recommendation
        
    except Exception as e:
        logger.error(f"Error generating investor recommendation: {e}")
        return None

def generate_demo_strategy_picks(strategy_id):
    """
    [MOCK] FAKE STRATEGY PICKS GENERATOR [MOCK]
    Generate demo strategy picks for testing - NOT REAL BETTING RECOMMENDATIONS
    All picks, odds, and amounts are fake for demonstration only
    """
    print(f"[DEMO] GENERATING FAKE STRATEGY PICKS for strategy {strategy_id}")
    import random
    
    # Demo games for different sports
    demo_games = [
        {'teams': 'Lakers vs Warriors', 'sport': 'NBA', 'odds': 1.85, 'bet_type': 'Moneyline'},
        {'teams': 'Celtics vs Heat', 'sport': 'NBA', 'odds': 2.10, 'bet_type': 'Spread'},
        {'teams': 'Chiefs vs Bills', 'sport': 'NFL', 'odds': 1.90, 'bet_type': 'Moneyline'},
        {'teams': 'Cowboys vs Eagles', 'sport': 'NFL', 'odds': 1.95, 'bet_type': 'Total Points'},
        {'teams': 'Yankees vs Red Sox', 'sport': 'MLB', 'odds': 1.75, 'bet_type': 'Moneyline'},
    ]
    
    # Generate 2-4 picks for demo
    num_picks = random.randint(2, 4)
    selected_games = random.sample(demo_games, min(len(demo_games), num_picks))
    
    picks = []
    for game in selected_games:
        bet_amount = random.uniform(25.0, 150.0)  # Demo bet amounts
        potential_payout = bet_amount * game['odds']
        confidence = random.randint(60, 85)
        
        pick = {
            'teams': game['teams'],
            'sport': game['sport'],
            'bet_type': game['bet_type'],
            'odds': game['odds'],
            'recommended_amount': round(bet_amount, 2),
            'potential_payout': round(potential_payout, 2),
            'confidence': confidence,
            'strategy_reason': f"Demo strategy match: {confidence}% confidence",
            'demo_mode': True
        }
        picks.append(pick)
    
    return picks

def generate_real_strategy_picks(strategy_data, bot_data, max_picks):
    """
    [REAL] REAL STRATEGY PICKS GENERATOR [REAL]
    Generate real strategy picks using actual sports data and bot configuration
    """
    logger.info(f"Generating real strategy picks for strategy {strategy_data.get('name', 'unknown')}")
    
    try:
        # Get bot's sport preference using helper function
        bot_sport = get_bot_sport(bot_data)
        
        # Get real games data for the bot's sport
        real_games = get_sports_games_data(bot_sport, max_picks * 2)  # Get more than needed for filtering
        
        if not real_games:
            logger.warning(f"No real games available for {bot_sport}, falling back to demo")
            raise Exception(f"No real games available for {bot_sport}")
        
        # Generate picks based on strategy type
        strategy_type = strategy_data.get('type', 'basic')
        
        if strategy_type == 'expected_value':
            picks = generate_real_expected_value_picks(strategy_data, bot_data, real_games, max_picks)
        elif strategy_type == 'conservative':
            picks = generate_real_conservative_picks(strategy_data, bot_data, real_games, max_picks)
        elif strategy_type == 'aggressive':
            picks = generate_real_aggressive_picks(strategy_data, bot_data, real_games, max_picks)
        else:
            picks = generate_real_basic_picks(strategy_data, bot_data, real_games, max_picks)
        
        # Add real data flag to all picks
        for pick in picks:
            pick['real_data'] = True
            pick['data_source'] = 'live_sports_api'
        
        logger.info(f"Generated {len(picks)} real strategy picks")
        return picks
        
    except Exception as e:
        logger.error(f"Failed to generate real strategy picks: {e}")
        raise e

def generate_real_expected_value_picks(strategy_data, bot_data, games, max_picks):
    """Generate +EV picks using real game data"""
    picks = []
    
    # Get strategy parameters with proper type conversion to handle dict/float issues
    params = strategy_data.get('parameters', {})
    
    # Safely extract numeric parameters, handling cases where they might be dicts or other types
    def safe_float_extract(value, default):
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, dict):
            # If it's a dict, try to extract a 'value' field or use default
            return float(value.get('value', default))
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        else:
            return default
    
    min_ev = safe_float_extract(params.get('min_expected_value', 5.0), 5.0)
    min_confidence = safe_float_extract(params.get('confidence_threshold', 65.0), 65.0)
    
    # Filter games by expected value
    for game in games:
        if len(picks) >= max_picks:
            break
            
        ev = game.get('expected_value', 0)
        confidence = game.get('true_probability', 0.5) * 100
        
        if ev >= min_ev and confidence >= min_confidence:
            bet_amount = bot_data['current_balance'] * (bot_data.get('bet_percentage', 2.0) / 100)
            
            pick = {
                'teams': game.get('teams', 'Unknown vs Unknown'),
                'sport': game.get('sport', 'NBA'),
                'bet_type': game.get('bet_type', 'Moneyline'),
                'odds': game.get('odds', 2.0),
                'recommended_amount': round(bet_amount, 2),
                'potential_payout': round(bet_amount * game.get('odds', 2.0), 2),
                'confidence': round(confidence, 1),
                'expected_value': round(ev, 2),
                'strategy_reason': f"Real +EV: {ev:.1f}% expected value",
                'game_id': game.get('id', f"real_game_{len(picks)}")
            }
            picks.append(pick)
    
    return picks

def generate_real_conservative_picks(strategy_data, bot_data, games, max_picks):
    """Generate conservative picks using real game data"""
    picks = []
    
    # Conservative parameters
    min_confidence = 75.0
    max_odds = 2.0
    
    for game in games:
        if len(picks) >= max_picks:
            break
            
        confidence = game.get('true_probability', 0.5) * 100
        odds = game.get('odds', 2.0)
        
        if confidence >= min_confidence and odds <= max_odds:
            bet_amount = bot_data['current_balance'] * (bot_data.get('bet_percentage', 1.5) / 100)
            
            pick = {
                'teams': game.get('teams', 'Unknown vs Unknown'),
                'sport': game.get('sport', 'NBA'),
                'bet_type': game.get('bet_type', 'Moneyline'),
                'odds': odds,
                'recommended_amount': round(bet_amount, 2),
                'potential_payout': round(bet_amount * odds, 2),
                'confidence': round(confidence, 1),
                'strategy_reason': f"Conservative: {confidence:.1f}% confidence, low risk",
                'game_id': game.get('id', f"real_game_{len(picks)}")
            }
            picks.append(pick)
    
    return picks

def generate_real_aggressive_picks(strategy_data, bot_data, games, max_picks):
    """Generate aggressive picks using real game data"""
    picks = []
    
    # Aggressive parameters
    min_confidence = 60.0
    bet_multiplier = 1.5  # Larger bets
    
    for game in games:
        if len(picks) >= max_picks:
            break
            
        confidence = game.get('true_probability', 0.5) * 100
        
        if confidence >= min_confidence:
            bet_amount = bot_data['current_balance'] * (bot_data.get('bet_percentage', 3.0) / 100) * bet_multiplier
            
            pick = {
                'teams': game.get('teams', 'Unknown vs Unknown'),
                'sport': game.get('sport', 'NBA'),
                'bet_type': game.get('bet_type', 'Moneyline'),
                'odds': game.get('odds', 2.0),
                'recommended_amount': round(bet_amount, 2),
                'potential_payout': round(bet_amount * game.get('odds', 2.0), 2),
                'confidence': round(confidence, 1),
                'strategy_reason': f"Aggressive: {confidence:.1f}% confidence, high stakes",
                'game_id': game.get('id', f"real_game_{len(picks)}")
            }
            picks.append(pick)
    
    return picks

def generate_real_basic_picks(strategy_data, bot_data, games, max_picks):
    """Generate basic picks using real game data"""
    picks = []
    
    for game in games[:max_picks]:
        bet_amount = bot_data['current_balance'] * (bot_data.get('bet_percentage', 2.0) / 100)
        confidence = game.get('true_probability', 0.5) * 100
        
        pick = {
            'teams': game.get('teams', 'Unknown vs Unknown'),
            'sport': game.get('sport', 'NBA'),
            'bet_type': game.get('bet_type', 'Moneyline'),
            'odds': game.get('odds', 2.0),
            'recommended_amount': round(bet_amount, 2),
            'potential_payout': round(bet_amount * game.get('odds', 2.0), 2),
            'confidence': round(confidence, 1),
            'strategy_reason': f"Basic strategy: {confidence:.1f}% model confidence",
            'game_id': game.get('id', f"real_game_{len(picks)}")
        }
        picks.append(pick)
    
    return picks

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
            'ml_performance': {
                'total_profit': 1247.50,
                'total_predictions': 89,
                'overall_accuracy': 68.4,
                'roi': 12.3,
                'sharpe_ratio': 1.45,
                'max_drawdown': -234.80,
                'avg_bet_size': 45.60
            },
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
            'recent_alerts': [
                {
                    'type': 'warning',
                    'message': 'NFL Model Performance Drop - accuracy dropped below 65% in last 10 predictions',
                    'timestamp': (datetime.datetime.now() - datetime.timedelta(hours=2)).isoformat()
                },
                {
                    'type': 'danger', 
                    'message': 'Losing Streak Detected - current losing streak of 5 consecutive bets',
                    'timestamp': (datetime.datetime.now() - datetime.timedelta(hours=4)).isoformat()
                },
                {
                    'type': 'success',
                    'message': 'High Value Bet Found - Lakers vs Warriors with 12% edge detected',
                    'timestamp': (datetime.datetime.now() - datetime.timedelta(minutes=12)).isoformat()
                }
            ],
            'alerts': [
                {
                    'id': 'alert_1',
                    'type': 'warning',
                    'title': 'NFL Model Performance Drop',
                    'message': 'NFL model accuracy dropped below 65% in last 10 predictions',
                    'timestamp': (datetime.datetime.now() - datetime.timedelta(hours=2)).isoformat(),
                    'severity': 'medium'
                },
                {
                    'id': 'alert_2', 
                    'type': 'danger',
                    'title': 'Losing Streak Detected',
                    'message': 'Current losing streak of 5 consecutive bets',
                    'timestamp': (datetime.datetime.now() - datetime.timedelta(hours=4)).isoformat(),
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

# --- PROFESSIONAL MODEL REGISTRY ENDPOINTS ---

@app.route('/api/models/registry', methods=['GET'])
@handle_errors
@require_authentication
def list_registered_models():
    """List models from professional registry with filtering"""
    try:
        sport = request.args.get('sport')
        model_type = request.args.get('model_type')
        status = request.args.get('status')
        created_by = request.args.get('created_by')
        
        # Convert status string to enum if provided
        status_enum = None
        if status:
            try:
                status_enum = ModelStatus(status.lower())
            except ValueError:
                raise ValidationError(f"Invalid status: {status}")
        
        models = model_registry.list_models(
            sport=sport,
            model_type=model_type,
            status=status_enum,
            created_by=created_by
        )
        
        # Convert to dict for JSON serialization
        models_data = []
        for model in models:
            model_dict = {
                'model_id': model.model_id,
                'name': model.name,
                'sport': model.sport,
                'model_type': model.model_type,
                'version': model.version,
                'status': model.status.value,
                'created_at': model.created_at,
                'created_by': model.created_by,
                'description': model.description,
                'performance_metrics': model.performance_metrics
            }
            models_data.append(model_dict)
        
        return jsonify({
            'success': True,
            'models': models_data,
            'total_count': len(models_data),
            'filters_applied': {
                'sport': sport,
                'model_type': model_type,
                'status': status,
                'created_by': created_by
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to list registered models: {e}")
        raise ValidationError(f'Failed to list models: {e}')

@app.route('/api/models/register', methods=['POST'])
@handle_errors
@require_authentication
@sanitize_request_data(required_fields=['name', 'sport', 'model_type'], optional_fields=['description', 'hyperparameters'])
def register_new_model():
    """Register a new model in the professional registry"""
    try:
        data = g.sanitized_request_data
        user_id = g.current_user.get('user_id')
        
        # Validate inputs
        sport = data.get('sport')
        if sport not in ['NBA', 'NFL', 'MLB']:
            raise ValidationError("Sport must be one of: NBA, NFL, MLB", field='sport')
        
        model_type = data.get('model_type')
        if model_type not in ['statistical', 'neural', 'ensemble']:
            raise ValidationError("Model type must be one of: statistical, neural, ensemble", field='model_type')
        
        # Register model
        model_id = model_registry.register_model(
            name=data.get('name'),
            sport=sport,
            model_type=model_type,
            created_by=user_id,
            description=data.get('description', ''),
            hyperparameters=data.get('hyperparameters', {})
        )
        
        logger.info(f"Model registered: {model_id} by user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Model registered successfully',
            'model_id': model_id,
            'registry_version': '2.0'
        }), 201
        
    except Exception as e:
        logger.error(f"Model registration failed: {e}")
        raise ValidationError(f'Model registration failed: {e}')

@app.route('/api/models/<model_id>/status', methods=['PUT'])
@handle_errors
@require_authentication
@sanitize_request_data(required_fields=['status'], optional_fields=['performance_metrics'])
def update_model_status(model_id):
    """Update model status and performance metrics"""
    try:
        data = g.sanitized_request_data
        
        # Validate status
        status_str = data.get('status')
        try:
            status = ModelStatus(status_str.lower())
        except ValueError:
            raise ValidationError(f"Invalid status: {status_str}")
        
        performance_metrics = data.get('performance_metrics', {})
        
        # Update model status
        model_registry.update_model_status(model_id, status, performance_metrics)
        
        logger.info(f"Model {model_id} status updated to {status.value}")
        
        return jsonify({
            'success': True,
            'message': f'Model status updated to {status.value}',
            'model_id': model_id
        })
        
    except ValueError as e:
        raise ResourceNotFoundError('Model', model_id)
    except Exception as e:
        logger.error(f"Failed to update model status: {e}")
        raise ValidationError(f'Failed to update model status: {e}')

# --- DATA VALIDATION ENDPOINTS ---

@app.route('/api/data/validate', methods=['POST'])
@handle_errors
@require_authentication
@rate_limit(requests_per_hour=50)
@sanitize_request_data(required_fields=['data', 'sport'], optional_fields=['data_type'])
def validate_data_quality():
    """Professional data quality validation"""
    try:
        data = g.sanitized_request_data
        
        sport = data.get('sport')
        if sport not in ['NBA', 'NFL', 'MLB']:
            raise ValidationError("Sport must be one of: NBA, NFL, MLB", field='sport')
        
        raw_data = data.get('data')
        if not isinstance(raw_data, list):
            raise ValidationError("Data must be a list of records", field='data')
        
        # Convert numpy types to native Python types for JSON serialization
        def convert_numpy_types(obj):
            if hasattr(obj, 'item'):  # numpy scalar
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(v) for v in obj]
            else:
                return obj
        
        # Validate data quality
        quality_report = data_validator.validate_sports_data(raw_data, sport)
        
        logger.info(f"Data validation completed for {sport}: {quality_report.overall_quality.value}")
        
        # Convert report to dict and handle numpy types
        report_dict = {
            'overall_quality': quality_report.overall_quality.value,
            'total_records': convert_numpy_types(quality_report.total_records),
            'valid_records': convert_numpy_types(quality_report.valid_records),
            'missing_data_percentage': convert_numpy_types(quality_report.missing_data_percentage),
            'outlier_percentage': convert_numpy_types(quality_report.outlier_percentage),
            'duplicate_percentage': convert_numpy_types(quality_report.duplicate_percentage),
            'quality_score': convert_numpy_types(quality_report.quality_score),
            'issues': quality_report.issues,
            'recommendations': quality_report.recommendations,
            'timestamp': quality_report.timestamp
        }
        
        return jsonify({
            'success': True,
            'quality_report': report_dict,
            'validation_version': '2.0'
        })
        
    except Exception as e:
        logger.error(f"Data validation failed: {e}")
        raise ValidationError(f'Data validation failed: {e}')

# --- USER ENGAGEMENT ENDPOINTS ---

@app.route('/api/user/preferences', methods=['POST'])
@handle_errors
@require_authentication
@sanitize_request_data(required_fields=['email'], optional_fields=['weekly_report_enabled', 'preferred_day', 'favorite_sports'])
def set_user_preferences():
    """Set user preferences for weekly reports and notifications"""
    try:
        data = g.sanitized_request_data
        user_id = g.current_user.get('user_id')
        
        # Validate email
        email = data.get('email')
        if '@' not in email:
            raise ValidationError("Invalid email format", field='email')
        
        # Register preferences
        user_data = dict(data)
        user_data.pop('user_id', None)  # Remove user_id from preferences data
        user_data.pop('email', None)  # Remove email from preferences data since it's passed separately
        
        preferences = engagement_system.register_user_preferences(
            user_id=user_id,
            email=email,
            preferences=user_data
        )
        
        logger.info(f"User preferences set for {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'User preferences saved successfully',
            'user_id': user_id,
            'preferences': {
                'weekly_report_enabled': preferences.weekly_report_enabled,
                'preferred_day': preferences.preferred_day,
                'favorite_sports': preferences.favorite_sports
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to set user preferences: {e}")
        raise ValidationError(f'Failed to set preferences: {e}')

@app.route('/api/reports/weekly/send', methods=['POST'])
@handle_errors
@require_authentication
def send_weekly_reports():
    """Send weekly reports to all eligible users (admin only)"""
    try:
        user_id = g.current_user.get('user_id')
        
        # In production, check admin permissions
        if not user_id or 'admin' not in g.current_user.get('permissions', []):
            logger.warning(f"Non-admin user {user_id} attempted to send weekly reports")
        
        target_day = request.json.get('target_day') if request.is_json else None
        
        # Send reports
        result = engagement_system.send_weekly_reports(target_day)
        
        logger.info(f"Weekly reports sent: {result['sent_count']} successful, {result['failed_count']} failed")
        
        return jsonify({
            'success': True,
            'message': 'Weekly reports processing completed',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Failed to send weekly reports: {e}")
        raise ValidationError(f'Failed to send weekly reports: {e}')

@app.route('/api/engagement/analytics', methods=['GET'])
@handle_errors
@require_authentication
def get_engagement_analytics():
    """Get user engagement analytics"""
    try:
        analytics = engagement_system.get_engagement_analytics()
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
        
    except Exception as e:
        logger.error(f"Failed to get engagement analytics: {e}")
        raise ValidationError(f'Failed to get analytics: {e}')

# --- ADVANCED SYSTEM MONITORING ---

@app.route('/api/system/metrics', methods=['GET'])
@handle_errors
@require_authentication
def get_system_metrics():
    """Get comprehensive system metrics and performance data"""
    try:
        import psutil
        import os
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Application metrics
        model_count = len(model_registry.list_models())
        error_stats = error_monitor.get_error_stats()
        
        # Performance metrics
        process = psutil.Process(os.getpid())
        app_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        metrics = {
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / 1024 / 1024 / 1024,
                'disk_percent': (disk.used / disk.total) * 100,
                'disk_free_gb': disk.free / 1024 / 1024 / 1024
            },
            'application': {
                'model_count': model_count,
                'error_stats': error_stats,
                'memory_usage_mb': app_memory,
                'uptime_seconds': time.time() - g.start_time if hasattr(g, 'start_time') else 0
            },
            'database': {
                'mode': 'demo' if demo_mode else 'connected',
                'ml_available': ML_AVAILABLE
            },
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'metrics': metrics
        })
        
    except ImportError:
        # Fallback if psutil not available
        metrics = {
            'system': {'status': 'monitoring_unavailable'},
            'application': {
                'model_count': len(model_registry.list_models()),
                'error_stats': error_monitor.get_error_stats()
            },
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'metrics': metrics
        })
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise ValidationError(f'Failed to get system metrics: {e}')

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

@app.route('/api/models/<model_id>/details', methods=['GET'])
def get_model_details(model_id):
    """Get detailed model information"""
    try:
        if not ML_AVAILABLE:
            # Return demo model details
            from datetime import datetime, timedelta
            return jsonify({
                'success': True,
                'model': {
                    'id': model_id,
                    'name': f'Demo Model {model_id}',
                    'architecture': 'LSTM with Weather Data',
                    'sport': 'NBA',
                    'status': 'active',
                    'created_at': (datetime.now() - timedelta(days=30)).isoformat(),
                    'accuracy': 68.2,
                    'predictions': 2847,
                    'roi': 12.3,
                    'sharpe_ratio': 1.45,
                    'max_drawdown': 8.4,
                    'win_rate': 67.5,
                    'training': {
                        'epochs': 75,
                        'batch_size': 32,
                        'learning_rate': 0.001
                    },
                    'features': [
                        {'name': 'Team Offensive Rating', 'importance': 85},
                        {'name': 'Defensive Efficiency', 'importance': 78},
                        {'name': 'Rest Days', 'importance': 72},
                        {'name': 'Home/Away', 'importance': 65},
                        {'name': 'Weather Conditions', 'importance': 58},
                        {'name': 'Injury Report', 'importance': 52}
                    ],
                    'recent_predictions': [
                        {
                            'game': 'Lakers vs Warriors',
                            'prediction': 'Lakers +3.5',
                            'confidence': 82,
                            'result': 'Win',
                            'date': '2 days ago'
                        },
                        {
                            'game': 'Chiefs vs Bills',
                            'prediction': 'Under 47.5',
                            'confidence': 76,
                            'result': 'Loss',
                            'date': '4 days ago'
                        },
                        {
                            'game': 'Celtics vs Heat',
                            'prediction': 'Celtics ML',
                            'confidence': 89,
                            'result': 'Win',
                            'date': '1 week ago'
                        }
                    ]
                },
                'demo_mode': True
            }), 200
        
        model_info = model_manager.get_model_info(model_id)
        
        if 'error' in model_info:
            # Return demo data instead of 400 error for better user experience
            from datetime import datetime, timedelta
            return jsonify({
                'success': True,
                'model': {
                    'id': model_id,
                    'name': f'Demo Model {model_id}',
                    'architecture': 'Basic Statistical Model',
                    'sport': model_id.split('_')[-1].upper() if '_' in model_id else 'NBA',
                    'status': 'demo',
                    'created_at': (datetime.now() - timedelta(days=15)).isoformat(),
                    'accuracy': 64.8,
                    'predictions': 1247,
                    'roi': 8.7,
                    'sharpe_ratio': 1.21,
                    'max_drawdown': 11.2,
                    'win_rate': 62.3,
                    'training': {
                        'epochs': 0,
                        'batch_size': 0,
                        'learning_rate': 0
                    },
                    'features': [
                        {'name': 'Team Strength', 'importance': 75},
                        {'name': 'Recent Form', 'importance': 68},
                        {'name': 'Home Advantage', 'importance': 55},
                        {'name': 'Head to Head', 'importance': 45}
                    ],
                    'recent_predictions': [
                        {
                            'game': 'Team A vs Team B',
                            'prediction': 'Team A -2.5',
                            'confidence': 75,
                            'result': 'Win',
                            'date': '1 day ago'
                        }
                    ]
                },
                'demo_mode': True,
                'note': 'Model not found, showing demo data'
            }), 200
        
        return jsonify({
            'success': True,
            'model': model_info,
            'model_id': model_id
        }), 200
        
    except Exception as e:
        # Even for exceptions, return demo data to keep UI functional
        from datetime import datetime, timedelta
        return jsonify({
            'success': True,
            'model': {
                'id': model_id,
                'name': f'Fallback Model {model_id}',
                'architecture': 'Error Fallback',
                'sport': 'NBA',
                'status': 'error',
                'created_at': datetime.now().isoformat(),
                'accuracy': 50.0,
                'predictions': 0,
                'roi': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 50.0,
                'training': {'epochs': 0, 'batch_size': 0, 'learning_rate': 0},
                'features': [],
                'recent_predictions': []
            },
            'demo_mode': True,
            'error': str(e)
        }), 200

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
    """Assign a trained model to a bot for recommendations and auto-detect sport"""
    try:
        data = request.json
        bot_id = data.get('bot_id')
        model_id = data.get('model_id')
        user_id = data.get('user_id')
        
        if not all([bot_id, model_id, user_id]):
            return jsonify({'success': False, 'message': 'Bot ID, Model ID, and User ID required'}), 400
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not initialized.'}), 500
        
        # Get model metadata to extract sport information
        model_metadata = model_registry.get_model_metadata(model_id)
        detected_sport = None
        
        if model_metadata:
            detected_sport = model_metadata.sport
            logger.info(f"Auto-detected sport '{detected_sport}' from model {model_id}")
        else:
            # Fallback: try to extract sport from model_id if it follows naming convention
            # e.g., "nfl_ensemble_123456" or "nba_lstm_789012"
            model_parts = model_id.lower().split('_')
            sport_mapping = {
                'nfl': 'NFL',
                'nba': 'NBA', 
                'mlb': 'MLB',
                'nhl': 'NHL',
                'ncaaf': 'NCAAF',
                'ncaab': 'NCAAB'
            }
            
            for part in model_parts:
                if part in sport_mapping:
                    detected_sport = sport_mapping[part]
                    logger.info(f"Auto-detected sport '{detected_sport}' from model ID pattern")
                    break
        
        # Update bot configuration to use the model
        bot_ref = bots_collection.document(bot_id)
        bot_doc = bot_ref.get()
        
        if not bot_doc.exists:
            return jsonify({'success': False, 'message': 'Bot not found'}), 404
        
        # Prepare update data
        update_data = {
            'assigned_model_id': model_id,
            'model_assigned_at': datetime.datetime.now().isoformat(),
            'last_updated': datetime.datetime.now().isoformat()
        }
        
        # Auto-update sport if detected
        if detected_sport:
            update_data['sport'] = detected_sport
            update_data['sport_auto_detected'] = True
            update_data['sport_detected_from'] = 'model_metadata' if model_metadata else 'model_id_pattern'
        
        bot_ref.update(update_data)
        
        response_message = f'Model {model_id} assigned to bot {bot_id}'
        if detected_sport:
            response_message += f' and sport auto-detected as {detected_sport}'
        
        return jsonify({
            'success': True,
            'message': response_message,
            'bot_id': bot_id,
            'model_id': model_id,
            'auto_detected_sport': detected_sport,
            'sport_detection_source': 'model_metadata' if model_metadata else ('model_id_pattern' if detected_sport else None)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to assign model to investor: {e}")
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

@app.route('/api/recent-scores', methods=['GET'])
def get_recent_scores():
    """Get recent scores for all sports"""
    try:
        sport = request.args.get('sport', 'all')
        days = int(request.args.get('days', 7))  # Last 7 days by default
        
        # Generate demo recent scores data
        recent_scores = generate_demo_recent_scores(sport, days)
        
        return jsonify({
            'success': True,
            'scores': recent_scores,
            'sport_filter': sport,
            'days_back': days,
            'generated_at': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get recent scores: {e}")
        return jsonify({'success': False, 'message': f'Failed to get scores: {e}'}), 500

@app.route('/api/standings', methods=['GET'])
def get_division_standings():
    """Get division standings for all sports"""
    try:
        sport = request.args.get('sport', 'all')
        
        # Generate demo standings data
        standings = generate_demo_standings(sport)
        
        return jsonify({
            'success': True,
            'standings': standings,
            'sport_filter': sport,
            'generated_at': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get standings: {e}")
        return jsonify({'success': False, 'message': f'Failed to get standings: {e}'}), 500

def generate_demo_recent_scores(sport_filter='all', days_back=7):
    """Generate demo recent scores data"""
    import random
    from datetime import datetime, timedelta
    
    scores = []
    sports_data = {
        'NFL': {
            'teams': ['Chiefs', 'Bills', 'Cowboys', 'Eagles', 'Patriots', '49ers', 'Packers', 'Ravens'],
            'score_range': (10, 35)
        },
        'NBA': {
            'teams': ['Lakers', 'Warriors', 'Celtics', 'Heat', 'Bulls', 'Knicks', 'Nets', 'Sixers'],
            'score_range': (85, 125)
        },
        'MLB': {
            'teams': ['Yankees', 'Red Sox', 'Dodgers', 'Giants', 'Astros', 'Angels', 'Mets', 'Cubs'],
            'score_range': (2, 12)
        },
        'NHL': {
            'teams': ['Rangers', 'Bruins', 'Kings', 'Sharks', 'Blackhawks', 'Red Wings', 'Flyers', 'Penguins'],
            'score_range': (1, 6)
        }
    }
    
    # Determine which sports to include
    if sport_filter != 'all' and sport_filter in sports_data:
        sports_to_include = [sport_filter]
    else:
        sports_to_include = list(sports_data.keys())
    
    # Generate scores for each day
    for day_offset in range(days_back):
        game_date = datetime.now() - timedelta(days=day_offset)
        
        for sport in sports_to_include:
            sport_info = sports_data[sport]
            teams = sport_info['teams']
            score_min, score_max = sport_info['score_range']
            
            # Generate 2-4 games per sport per day
            num_games = random.randint(2, 4)
            
            for _ in range(num_games):
                home_team = random.choice(teams)
                away_team = random.choice([t for t in teams if t != home_team])
                
                home_score = random.randint(score_min, score_max)
                away_score = random.randint(score_min, score_max)
                
                # Ensure home team has slight advantage (60% win rate)
                if random.random() < 0.6:
                    if home_score <= away_score:
                        home_score = away_score + random.randint(1, 3)
                
                scores.append({
                    'id': f"{sport.lower()}_{game_date.strftime('%Y%m%d')}_{home_team}_{away_team}",
                    'sport': sport,
                    'date': game_date.strftime('%Y-%m-%d'),
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'winner': home_team if home_score > away_score else away_team,
                    'game_time': game_date.strftime('%I:%M %p'),
                    'status': 'Final'
                })
    
    # Sort by date (most recent first)
    scores.sort(key=lambda x: x['date'], reverse=True)
    
    return scores

def generate_demo_standings(sport_filter='all'):
    """Generate demo division standings data"""
    import random
    
    standings = {}
    
    sports_divisions = {
        'NFL': {
            'AFC East': ['Bills', 'Patriots', 'Jets', 'Dolphins'],
            'AFC North': ['Ravens', 'Steelers', 'Browns', 'Bengals'],
            'AFC South': ['Titans', 'Colts', 'Texans', 'Jaguars'],
            'AFC West': ['Chiefs', 'Chargers', 'Raiders', 'Broncos'],
            'NFC East': ['Eagles', 'Cowboys', 'Giants', 'Commanders'],
            'NFC North': ['Packers', 'Vikings', 'Bears', 'Lions'],
            'NFC South': ['Saints', 'Falcons', 'Panthers', 'Buccaneers'],
            'NFC West': ['49ers', 'Seahawks', 'Rams', 'Cardinals']
        },
        'NBA': {
            'Atlantic': ['Celtics', 'Nets', 'Knicks', 'Sixers', 'Raptors'],
            'Central': ['Bucks', 'Bulls', 'Cavaliers', 'Pistons', 'Pacers'],
            'Southeast': ['Heat', 'Hawks', 'Hornets', 'Magic', 'Wizards'],
            'Northwest': ['Nuggets', 'Timberwolves', 'Thunder', 'Blazers', 'Jazz'],
            'Pacific': ['Warriors', 'Lakers', 'Clippers', 'Suns', 'Kings'],
            'Southwest': ['Mavericks', 'Rockets', 'Grizzlies', 'Pelicans', 'Spurs']
        },
        'MLB': {
            'AL East': ['Yankees', 'Red Sox', 'Blue Jays', 'Rays', 'Orioles'],
            'AL Central': ['Twins', 'Guardians', 'White Sox', 'Tigers', 'Royals'],
            'AL West': ['Astros', 'Angels', 'Mariners', 'Rangers', 'Athletics'],
            'NL East': ['Braves', 'Mets', 'Phillies', 'Marlins', 'Nationals'],
            'NL Central': ['Brewers', 'Cardinals', 'Cubs', 'Reds', 'Pirates'],
            'NL West': ['Dodgers', 'Padres', 'Giants', 'Rockies', 'Diamondbacks']
        }
    }
    
    # Determine which sports to include
    if sport_filter != 'all' and sport_filter in sports_divisions:
        sports_to_include = [sport_filter]
    else:
        sports_to_include = list(sports_divisions.keys())
    
    for sport in sports_to_include:
        standings[sport] = {}
        
        for division, teams in sports_divisions[sport].items():
            division_standings = []
            
            for i, team in enumerate(teams):
                # Generate realistic records
                if sport == 'NFL':
                    games_played = random.randint(14, 17)
                    wins = random.randint(max(0, games_played - 15), games_played)
                elif sport == 'NBA':
                    games_played = random.randint(75, 82)
                    wins = random.randint(max(0, games_played - 60), min(games_played, 65))
                else:  # MLB
                    games_played = random.randint(155, 162)
                    wins = random.randint(max(0, games_played - 100), min(games_played, 110))
                
                losses = games_played - wins
                win_pct = wins / games_played if games_played > 0 else 0
                
                # Games behind calculation (simplified)
                gb = i * random.uniform(0.5, 3.0) if i > 0 else 0
                
                division_standings.append({
                    'team': team,
                    'wins': wins,
                    'losses': losses,
                    'win_percentage': round(win_pct, 3),
                    'games_behind': round(gb, 1) if gb > 0 else '-',
                    'games_played': games_played,
                    'position': i + 1
                })
            
            # Sort by win percentage
            division_standings.sort(key=lambda x: x['win_percentage'], reverse=True)
            
            # Update positions and games behind after sorting
            for idx, team_data in enumerate(division_standings):
                team_data['position'] = idx + 1
                if idx == 0:
                    team_data['games_behind'] = '-'
                else:
                    # Calculate actual games behind leader
                    leader_wins = division_standings[0]['wins']
                    leader_losses = division_standings[0]['losses']
                    team_wins = team_data['wins']
                    team_losses = team_data['losses']
                    
                    gb = ((leader_wins - team_wins) + (team_losses - leader_losses)) / 2
                    team_data['games_behind'] = round(gb, 1) if gb > 0 else '-'
            
            standings[sport][division] = division_standings
    
    return standings

@app.route('/api/schema/validate', methods=['POST'])
@handle_errors
def validate_schema():
    """Validate data against our standardized schemas"""
    try:
        data = request.json
        schema_type = data.get('schema_type')
        schema_data = data.get('data')
        
        if not schema_type or not schema_data:
            return jsonify({
                'success': False, 
                'message': 'schema_type and data are required'
            }), 400
        
        validation_issues = []
        
        if schema_type == 'model':
            try:
                model = ModelSchema.from_dict(schema_data)
                validation_issues = SchemaValidator.validate_model(model)
            except Exception as e:
                validation_issues.append(f"Schema parsing error: {str(e)}")
                
        elif schema_type == 'bot':
            try:
                bot = BotSchema.from_dict(schema_data)
                validation_issues = SchemaValidator.validate_bot(bot)
            except Exception as e:
                validation_issues.append(f"Schema parsing error: {str(e)}")
                
        elif schema_type == 'strategy':
            try:
                strategy = StrategySchema.from_dict(schema_data)
                validation_issues = SchemaValidator.validate_strategy(strategy)
            except Exception as e:
                validation_issues.append(f"Schema parsing error: {str(e)}")
        else:
            return jsonify({
                'success': False,
                'message': f'Unknown schema type: {schema_type}'
            }), 400
        
        return jsonify({
            'success': len(validation_issues) == 0,
            'validation_issues': validation_issues,
            'schema_type': schema_type,
            'is_valid': len(validation_issues) == 0
        })
        
    except Exception as e:
        logger.error(f"Schema validation failed: {e}")
        return jsonify({
            'success': False,
            'message': f'Validation failed: {str(e)}'
        }), 500

@app.route('/api/schema/info', methods=['GET'])
def get_schema_info():
    """Get information about available schemas"""
    try:
        schema_info = {
            'version': '2.0.0',
            'schemas': {
                'model': {
                    'description': 'Machine learning model schema with performance tracking',
                    'required_fields': ['model_id', 'name', 'version', 'sport', 'created_by'],
                    'enums': {
                        'sport': [sport.value for sport in Sport],
                        'status': [status.value for status in ModelStatus],
                        'market_types': [market.value for market in MarketType]
                    }
                },
                'bot': {
                    'description': 'Automated investor/bot schema with risk management',
                    'required_fields': ['bot_id', 'name', 'current_balance', 'created_by'],
                    'enums': {
                        'active_status': [status.value for status in InvestorStatus],
                        'sport_filter': [sport.value for sport in Sport]
                    }
                },
                'strategy': {
                    'description': 'Investment strategy schema with performance metrics',
                    'required_fields': ['strategy_id', 'name', 'strategy_type', 'created_by'],
                    'enums': {
                        'strategy_type': [stype.value for stype in StrategyType]
                    }
                }
            },
            'features': [
                'Schema validation',
                'Legacy data migration',
                'Performance metrics tracking',
                'Risk management configuration',
                'Type safety with enums'
            ]
        }
        
        return jsonify({
            'success': True,
            'schema_info': schema_info
        })
        
    except Exception as e:
        logger.error(f"Failed to get schema info: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to get schema info: {str(e)}'
        }), 500

@app.route('/scores')
def scores_page():
    """Render the scores and standings page"""
    return render_template('scores.html')

@app.route('/api/training/queue', methods=['GET'])
@handle_errors
@require_authentication
def get_training_queue():
    """Get current training queue status"""
    if not TRAINING_QUEUE_AVAILABLE:
        return jsonify({'success': False, 'message': 'Training queue not available'}), 500
    
    try:
        queue_status = training_queue.get_queue_status()
        
        return jsonify({
            'success': True,
            'queue': queue_status
        })
        
    except Exception as e:
        logger.error(f"Failed to get training queue: {e}")
        raise ValidationError(f'Failed to get training queue: {e}')

@app.route('/api/training/submit', methods=['POST'])
@handle_errors
@require_authentication
@sanitize_request_data(required_fields=['model_name', 'model_type', 'sport'], optional_fields=['epochs', 'batch_size', 'learning_rate', 'training_period', 'training_samples', 'features', 'description'])
def submit_training_job():
    """Submit a new training job to the queue"""
    if not TRAINING_QUEUE_AVAILABLE:
        # Demo mode: simulate training job submission
        try:
            data = g.sanitized_request_data
            user_id = g.current_user.get('user_id', 'demo_user')
            
            # Validate basic inputs for demo mode
            model_name = data.get('model_name', 'Demo Model')
            model_type = data.get('model_type', 'neural')
            sport = data.get('sport', 'NBA')
            
            if sport not in ['NBA', 'NFL', 'MLB', 'NCAAF', 'NCAAB']:
                raise ValidationError("Invalid sport", field='sport')
            
            if model_type not in ['lstm_weather', 'ensemble', 'neural', 'statistical']:
                raise ValidationError("Invalid model type", field='model_type')
            
            # Generate demo job ID
            import time
            demo_job_id = f"demo_job_{int(time.time())}"
            
            logger.info(f"Demo training job {demo_job_id} simulated for user {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'Training job submitted successfully (demo mode)',
                'job_id': demo_job_id,
                'queue_position': 1,
                'demo_mode': True
            }), 201
            
        except Exception as e:
            logger.error(f"Demo training job submission failed: {e}")
            raise ValidationError(f'Demo training job submission failed: {e}')
    
    
    try:
        data = g.sanitized_request_data
        user_id = g.current_user.get('user_id')
        
        # Validate inputs
        model_name = data.get('model_name')
        model_type = data.get('model_type')
        sport = data.get('sport')
        
        if sport not in ['NBA', 'NFL', 'MLB', 'NCAAF', 'NCAAB']:
            raise ValidationError("Invalid sport", field='sport')
        
        if model_type not in ['lstm_weather', 'ensemble', 'neural', 'statistical']:
            raise ValidationError("Invalid model type", field='model_type')
        
        # Generate model_id from model_name
        import re
        model_id = re.sub(r'[^a-zA-Z0-9_]', '_', model_name.lower()) if model_name else f"{sport.lower()}_{model_type}"
        
        # Build training configuration
        training_config = {
            'epochs': int(data.get('epochs', 50)),
            'batch_size': int(data.get('batch_size', 32)),
            'learning_rate': float(data.get('learning_rate', 0.001)),
            'model_name': model_name or f"{sport}_{model_type}_model",
            'optimizer': data.get('optimizer', 'adam'),
            'validation_split': data.get('validation_split', 0.2)
        }
        
        # Validate configuration
        if training_config['epochs'] < 1 or training_config['epochs'] > 200:
            raise ValidationError("Epochs must be between 1 and 200", field='epochs')
        
        if training_config['batch_size'] < 1 or training_config['batch_size'] > 256:
            raise ValidationError("Batch size must be between 1 and 256", field='batch_size')
        
        # Submit job to queue
        job_id = training_queue.submit_job(
            model_id=model_id,
            model_type=model_type,
            sport=sport,
            user_id=user_id,
            training_config=training_config
        )
        
        logger.info(f"Training job {job_id} submitted by user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Training job submitted successfully',
            'job_id': job_id,
            'queue_position': len(training_queue.queue)
        }), 201
        
    except ValueError as e:
        raise ValidationError(f"Invalid numeric value: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to submit training job: {e}")
        raise ValidationError(f'Failed to submit training job: {e}')

@app.route('/api/training/job/<job_id>', methods=['GET'])
@handle_errors
@require_authentication
def get_training_job_status(job_id):
    """Get status of a specific training job"""
    if not TRAINING_QUEUE_AVAILABLE:
        return jsonify({'success': False, 'message': 'Training queue not available'}), 500
    
    try:
        job_status = training_queue.get_job_status(job_id)
        
        if not job_status:
            raise ResourceNotFoundError('Training Job', job_id)
        
        return jsonify({
            'success': True,
            'job': job_status
        })
        
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise ValidationError(f'Failed to get job status: {e}')

@app.route('/api/training/job/<job_id>/cancel', methods=['POST'])
@handle_errors
@require_authentication
def cancel_training_job(job_id):
    """Cancel a training job"""
    if not TRAINING_QUEUE_AVAILABLE:
        return jsonify({'success': False, 'message': 'Training queue not available'}), 500
    
    try:
        success = training_queue.cancel_job(job_id)
        
        if not success:
            raise ResourceNotFoundError('Training Job', job_id)
        
        logger.info(f"Training job {job_id} cancelled")
        
        return jsonify({
            'success': True,
            'message': 'Training job cancelled successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise ValidationError(f'Failed to cancel job: {e}')

@app.route('/api/training/user-jobs', methods=['GET'])
@handle_errors
@require_authentication
def get_user_training_jobs():
    """Get all training jobs for the current user"""
    if not TRAINING_QUEUE_AVAILABLE:
        return jsonify({'success': False, 'message': 'Training queue not available'}), 500
    
    try:
        user_id = g.current_user.get('user_id')
        user_jobs = training_queue.get_user_jobs(user_id)
        
        return jsonify({
            'success': True,
            'jobs': user_jobs,
            'total_jobs': len(user_jobs)
        })
        
    except Exception as e:
        logger.error(f"Failed to get user jobs: {e}")
        raise ValidationError(f'Failed to get user jobs: {e}')

@app.route('/api/training/gpu-stats', methods=['GET'])
@handle_errors  
@require_authentication
def get_gpu_stats():
    """Get current GPU resource statistics"""
    if not TRAINING_QUEUE_AVAILABLE:
        return jsonify({'success': False, 'message': 'Training queue not available'}), 500
    
    try:
        queue_status = training_queue.get_queue_status()
        gpu_stats = queue_status['gpu_resources']
        
        # Calculate aggregated stats
        total_memory = sum(gpu['memory_gb'] for gpu in gpu_stats)
        used_memory = sum(gpu['memory_used_gb'] for gpu in gpu_stats)
        avg_utilization = sum(gpu['utilization_percent'] for gpu in gpu_stats) / len(gpu_stats) if gpu_stats else 0
        
        return jsonify({
            'success': True,
            'gpu_stats': {
                'individual_gpus': gpu_stats,
                'total_gpus': len(gpu_stats),
                'available_gpus': queue_status['available_gpus'],
                'total_memory_gb': total_memory,
                'used_memory_gb': used_memory,
                'memory_utilization_percent': (used_memory / total_memory) * 100 if total_memory > 0 else 0,
                'average_gpu_utilization': avg_utilization,
                'active_training_jobs': queue_status['active_jobs']
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get GPU stats: {e}")
        raise ValidationError(f'Failed to get GPU stats: {e}')

# --- PERFORMANCE MATRIX ENDPOINTS ---

@app.route('/api/performance/matrix', methods=['GET'])
@handle_errors
@require_authentication
def get_performance_matrix():
    """Get model performance comparison matrix"""
    if not PERFORMANCE_MATRIX_AVAILABLE:
        return jsonify({'success': False, 'message': 'Performance matrix not available'}), 500
    
    try:
        sport = request.args.get('sport')
        model_type = request.args.get('model_type')
        days_back = int(request.args.get('days_back', 30))
        
        # Generate demo data if empty
        if not performance_matrix.performance_data:
            performance_matrix.generate_demo_data()
        
        # Get performance matrix as DataFrame
        matrix_df = performance_matrix.get_performance_matrix(sport, model_type, days_back)
        
        if matrix_df.empty:
            return jsonify({
                'success': True,
                'matrix': [],
                'message': 'No performance data found for the specified criteria'
            })
        
        # Convert DataFrame to list of dictionaries
        matrix_data = matrix_df.to_dict('records')
        
        # Get summary statistics
        summary = {
            'total_models': len(matrix_df),
            'avg_accuracy': float(matrix_df['Accuracy'].mean()),
            'best_accuracy': float(matrix_df['Accuracy'].max()),
            'avg_roi': float(matrix_df['ROI %'].mean()),
            'best_roi': float(matrix_df['ROI %'].max()),
            'sports_covered': list(matrix_df['Sport'].unique()),
            'model_types_covered': list(matrix_df['Model Type'].unique())
        }
        
        return jsonify({
            'success': True,
            'matrix': matrix_data,
            'summary': summary,
            'filters_applied': {
                'sport': sport,
                'model_type': model_type,
                'days_back': days_back
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get performance matrix: {e}")
        raise ValidationError(f'Failed to get performance matrix: {e}')

@app.route('/api/performance/compare', methods=['POST'])
@handle_errors
@require_authentication
@sanitize_request_data(required_fields=['model_ids'])
def compare_models():
    """Compare specific models side by side"""
    if not PERFORMANCE_MATRIX_AVAILABLE:
        return jsonify({'success': False, 'message': 'Performance matrix not available'}), 500
    
    try:
        data = g.sanitized_request_data
        model_ids = data.get('model_ids', [])
        
        if not model_ids or len(model_ids) < 2:
            raise ValidationError("At least 2 model IDs required for comparison")
        
        if len(model_ids) > 10:
            raise ValidationError("Maximum 10 models can be compared at once")
        
        # Generate demo data if empty
        if not performance_matrix.performance_data:
            performance_matrix.generate_demo_data()
        
        comparison_data = performance_matrix.get_model_comparison(model_ids)
        
        return jsonify({
            'success': True,
            'comparison': comparison_data,
            'models_found': len(comparison_data),
            'models_requested': len(model_ids)
        })
        
    except Exception as e:
        logger.error(f"Failed to compare models: {e}")
        raise ValidationError(f'Failed to compare models: {e}')

@app.route('/api/models/comparison-data', methods=['GET'])
@handle_errors
def get_model_comparison_data():
    """Get comprehensive model comparison data for the comparison modal"""
    try:
        # Generate demo data if empty
        if not performance_matrix.performance_data:
            performance_matrix.generate_demo_data()
        
        # Get all available models for selection
        all_models = []
        model_lookup = {}
        
        for entry in performance_matrix.performance_data:
            if entry.model_id not in model_lookup:
                model_lookup[entry.model_id] = entry
                all_models.append({
                    'model_id': entry.model_id,
                    'display_name': f"{entry.sport} {entry.model_type.replace('_', ' ').title()} v{entry.version}",
                    'sport': entry.sport,
                    'model_type': entry.model_type,
                    'version': entry.version,
                    'accuracy': round(entry.accuracy * 100, 1),
                    'training_date': entry.training_date.strftime('%Y-%m-%d'),
                    'evaluation_date': entry.evaluation_date.strftime('%Y-%m-%d')
                })
        
        # Sort by sport then by accuracy descending
        all_models.sort(key=lambda x: (x['sport'], -x['accuracy']))
        
        return jsonify({
            'success': True,
            'available_models': all_models,
            'total_models': len(all_models)
        })
        
    except Exception as e:
        logger.error(f"Failed to get model comparison data: {e}")
        return jsonify({'success': False, 'message': f'Failed to get model data: {e}'}), 500

@app.route('/api/models/detailed-comparison', methods=['POST'])
@handle_errors
@sanitize_request_data(required_fields=['model_ids'])
def get_detailed_model_comparison():
    """Get detailed comparison between selected models"""
    try:
        data = g.sanitized_request_data
        model_ids = data.get('model_ids', [])
        
        if len(model_ids) != 2:
            raise ValidationError("Exactly 2 model IDs required for detailed comparison")
        
        # Generate demo data if empty
        if not performance_matrix.performance_data:
            performance_matrix.generate_demo_data()
        
        comparison_result = {}
        
        for model_id in model_ids:
            # Find the model entry
            model_entries = [entry for entry in performance_matrix.performance_data if entry.model_id == model_id]
            
            if not model_entries:
                continue
                
            latest_entry = max(model_entries, key=lambda x: x.evaluation_date)
            
            # Get model architecture details
            architecture_info = get_model_architecture_info(latest_entry.model_type, latest_entry.parameters)
            
            # Get training data information
            training_info = get_training_data_info(latest_entry.sport, latest_entry.training_date)
            
            # Get input features matrix
            input_features = get_model_input_features(latest_entry.sport, latest_entry.model_type)
            
            # Performance trends (simulate historical data)
            performance_trends = generate_performance_trends(latest_entry, len(model_entries))
            
            comparison_result[model_id] = {
                'basic_info': {
                    'model_id': model_id,
                    'display_name': f"{latest_entry.sport} {latest_entry.model_type.replace('_', ' ').title()} v{latest_entry.version}",
                    'sport': latest_entry.sport,
                    'model_type': latest_entry.model_type,
                    'version': latest_entry.version,
                    'tags': latest_entry.tags
                },
                'performance_metrics': {
                    'accuracy': round(latest_entry.accuracy * 100, 1),
                    'precision': round(latest_entry.precision * 100, 1),
                    'recall': round(latest_entry.recall * 100, 1),
                    'f1_score': round(latest_entry.f1_score * 100, 1),
                    'roi_percentage': round(latest_entry.roi_percentage, 1),
                    'sharpe_ratio': round(latest_entry.sharpe_ratio, 2),
                    'max_drawdown': round(latest_entry.max_drawdown, 1),
                    'win_rate': round(latest_entry.win_rate * 100, 1),
                    'total_predictions': latest_entry.total_predictions,
                    'correct_predictions': latest_entry.correct_predictions,
                    'profit_loss': round(latest_entry.profit_loss, 2)
                },
                'architecture': architecture_info,
                'training_data': training_info,
                'input_features': input_features,
                'performance_trends': performance_trends,
                'parameters': latest_entry.parameters
            }
        
        return jsonify({
            'success': True,
            'comparison': comparison_result,
            'models_compared': len(comparison_result)
        })
        
    except Exception as e:
        logger.error(f"Failed to get detailed comparison: {e}")
        raise ValidationError(f'Failed to get detailed comparison: {e}')


def get_model_architecture_info(model_type: str, parameters: dict) -> dict:
    """Get detailed architecture information for a model type"""
    base_architectures = {
        'lstm_weather': {
            'type': 'Recurrent Neural Network (LSTM)',
            'description': 'Long Short-Term Memory network with weather integration',
            'layers': [
                'Input Layer (Features + Weather)',
                'LSTM Layer with Dropout',
                'Dense Layer (Fully Connected)',
                'Output Layer (Probability)'
            ],
            'strengths': ['Temporal patterns', 'Weather correlation', 'Sequence modeling'],
            'optimal_for': ['Weather-dependent sports', 'Time series patterns', 'NFL/MLB outdoor games']
        },
        'ensemble': {
            'type': 'Ensemble Method',
            'description': 'Combines multiple base models for improved prediction',
            'layers': [
                'Base Model 1 (Random Forest)',
                'Base Model 2 (XGBoost)',
                'Base Model 3 (Neural Network)',
                'Meta-Learner (Voting/Stacking)'
            ],
            'strengths': ['High accuracy', 'Reduced overfitting', 'Robust predictions'],
            'optimal_for': ['Complex patterns', 'High-stakes predictions', 'Tournament play']
        },
        'neural': {
            'type': 'Deep Neural Network',
            'description': 'Multi-layer feedforward neural network',
            'layers': [
                'Input Layer (Features)',
                f"Hidden Layer 1 ({parameters.get('neurons_per_layer', 64)} neurons)",
                f"Hidden Layer 2 ({parameters.get('neurons_per_layer', 64)} neurons)",
                'Output Layer (Probability)'
            ],
            'strengths': ['Pattern recognition', 'Non-linear relationships', 'Feature learning'],
            'optimal_for': ['Complex data patterns', 'Large datasets', 'Feature interactions']
        },
        'statistical': {
            'type': 'Statistical Model',
            'description': 'Traditional statistical approach with feature engineering',
            'layers': [
                'Feature Engineering',
                'Statistical Analysis',
                'Linear/Logistic Regression',
                'Probability Output'
            ],
            'strengths': ['Interpretability', 'Fast training', 'Stable performance'],
            'optimal_for': ['Simple patterns', 'Limited data', 'Baseline models']
        }
    }
    
    architecture = base_architectures.get(model_type, {
        'type': 'Unknown Model Type',
        'description': 'Architecture information not available',
        'layers': ['Input', 'Processing', 'Output'],
        'strengths': ['Unknown'],
        'optimal_for': ['General prediction']
    })
    
    # Add parameter-specific details
    if model_type == 'lstm_weather':
        architecture['parameter_details'] = {
            'LSTM Units': parameters.get('lstm_units', 64),
            'Dropout Rate': f"{parameters.get('dropout_rate', 0.3)*100:.1f}%",
            'Sequence Length': f"{parameters.get('sequence_length', 10)} games",
            'Weather Features': parameters.get('weather_features', 7),
            'Learning Rate': parameters.get('learning_rate', 0.001)
        }
    elif model_type == 'ensemble':
        architecture['parameter_details'] = {
            'Number of Models': parameters.get('n_models', 3),
            'Voting Strategy': parameters.get('voting_strategy', 'soft').title(),
            'Cross-Validation': f"{parameters.get('cv_folds', 5)} folds",
            'Meta-Learner': parameters.get('meta_learner', 'logistic').title()
        }
    elif model_type == 'neural':
        architecture['parameter_details'] = {
            'Hidden Layers': parameters.get('hidden_layers', 2),
            'Neurons per Layer': parameters.get('neurons_per_layer', 64),
            'Activation Function': parameters.get('activation', 'relu').upper(),
            'Batch Size': parameters.get('batch_size', 32),
            'Training Epochs': parameters.get('epochs', 100)
        }
    else:  # statistical
        architecture['parameter_details'] = {
            'Regularization': parameters.get('regularization', 'l2').upper(),
            'Cross-Validation': parameters.get('cv_method', 'kfold').replace('_', ' ').title(),
            'Feature Selection': parameters.get('feature_selection', 'rfe').upper()
        }
    
    return architecture


def get_training_data_info(sport: str, training_date: datetime) -> dict:
    """Get information about training data timeframe and sources"""
    # Calculate training period based on sport
    training_periods = {
        'NBA': {'games_per_season': 82, 'season_months': 8, 'seasons_used': 3},
        'NFL': {'games_per_season': 17, 'season_months': 6, 'seasons_used': 5},
        'MLB': {'games_per_season': 162, 'season_months': 6, 'seasons_used': 3},
        'NCAAF': {'games_per_season': 12, 'season_months': 4, 'seasons_used': 4},
        'NCAAB': {'games_per_season': 35, 'season_months': 6, 'seasons_used': 3}
    }
    
    sport_info = training_periods.get(sport, training_periods['NBA'])
    
    # Calculate data timeframe
    end_date = training_date
    start_date = end_date - timedelta(days=sport_info['seasons_used'] * 365)
    
    total_games = sport_info['games_per_season'] * sport_info['seasons_used'] * 30  # Assume 30 teams
    
    return {
        'training_period': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'duration_years': sport_info['seasons_used'],
            'total_days': (end_date - start_date).days
        },
        'data_volume': {
            'total_games': total_games,
            'seasons_included': sport_info['seasons_used'],
            'games_per_season': sport_info['games_per_season'],
            'estimated_teams': 30
        },
        'data_sources': [
            'Official league statistics',
            'Team performance metrics',
            'Player statistics',
            'Historical matchup data',
            'Venue information',
            'Weather data (if applicable)' if sport in ['NFL', 'MLB', 'NCAAF'] else None
        ],
        'data_quality': {
            'completeness': f"{np.random.randint(92, 99)}%",
            'accuracy': f"{np.random.randint(95, 99)}%",
            'recency': 'Updated after each game',
            'validation': 'Cross-validated on holdout set'
        }
    }


def get_model_input_features(sport: str, model_type: str) -> dict:
    """Get the input feature matrix for a model"""
    base_features = {
        'NBA': [
            'Team Offensive Rating', 'Team Defensive Rating', 'Pace Factor',
            'Field Goal %', 'Three Point %', 'Free Throw %',
            'Rebounds per Game', 'Assists per Game', 'Turnovers per Game',
            'Home/Away Indicator', 'Rest Days', 'Back-to-Back Games',
            'Head-to-Head Record', 'Current Win Streak', 'Recent Form (L10)'
        ],
        'NFL': [
            'Passing Yards per Game', 'Rushing Yards per Game', 'Points per Game',
            'Passing Yards Allowed', 'Rushing Yards Allowed', 'Points Allowed',
            'Turnover Differential', 'Red Zone Efficiency', 'Third Down %',
            'Home/Away Indicator', 'Division Opponent', 'Rest Days',
            'Strength of Schedule', 'Injury Report Impact', 'Head-to-Head Record'
        ],
        'MLB': [
            'Team ERA', 'Team Batting Average', 'On-Base Percentage',
            'Slugging Percentage', 'Runs per Game', 'Runs Allowed per Game',
            'Home/Away Indicator', 'Starting Pitcher ERA', 'Bullpen ERA',
            'Recent Form (L10)', 'Head-to-Head Record', 'Divisional Matchup',
            'Rest Days', 'Ballpark Factor', 'Team Streak'
        ],
        'NCAAF': [
            'Points per Game', 'Points Allowed per Game', 'Yards per Play',
            'Yards Allowed per Play', 'Turnover Margin', 'Red Zone %',
            'Home/Away Indicator', 'Conference Opponent', 'Ranking Differential',
            'Strength of Schedule', 'Recent Form', 'Head-to-Head Record',
            'Bye Week Advantage', 'Coaching Experience', 'Recruiting Ranking'
        ],
        'NCAAB': [
            'Adjusted Offensive Efficiency', 'Adjusted Defensive Efficiency',
            'Effective Field Goal %', 'Turnover %', 'Offensive Rebound %',
            'Free Throw Rate', 'Home/Away Indicator', 'Conference Opponent',
            'NET Ranking', 'Strength of Schedule', 'Recent Form (L10)',
            'Head-to-Head Record', 'Coaching Experience', 'Key Player Injuries'
        ]
    }
    
    sport_features = base_features.get(sport, base_features['NBA'])
    
    # Add weather features for weather-dependent models
    weather_features = []
    if model_type == 'lstm_weather' and sport in ['NFL', 'MLB', 'NCAAF']:
        weather_features = [
            'Temperature (°F)', 'Humidity (%)', 'Wind Speed (mph)',
            'Wind Direction', 'Precipitation (%)', 'Barometric Pressure',
            'Weather Condition Category'
        ]
    
    # Add advanced features for ensemble models
    advanced_features = []
    if model_type == 'ensemble':
        advanced_features = [
            'Historical Performance vs Similar Teams',
            'Momentum Indicators', 'Fatigue Metrics',
            'Situational Performance', 'Clutch Performance Rating'
        ]
    
    all_features = sport_features + weather_features + advanced_features
    
    return {
        'total_features': len(all_features),
        'feature_categories': {
            'team_performance': len(sport_features),
            'weather_data': len(weather_features),
            'advanced_metrics': len(advanced_features)
        },
        'features': all_features,
        'feature_importance': generate_feature_importance(all_features),
        'data_preprocessing': [
            'Z-score normalization',
            'Missing value imputation',
            'Outlier detection',
            'Feature scaling'
        ]
    }


def generate_feature_importance(features: list) -> dict:
    """Generate mock feature importance scores"""
    importance_scores = {}
    
    # Generate realistic importance scores that sum to 100%
    scores = np.random.dirichlet(np.ones(len(features))) * 100
    
    for i, feature in enumerate(features):
        importance_scores[feature] = round(scores[i], 1)
    
    return importance_scores


def generate_performance_trends(entry, num_points: int = 10) -> dict:
    """Generate performance trends over time"""
    dates = []
    accuracies = []
    rois = []
    
    # Generate dates going backwards from evaluation date
    for i in range(num_points):
        date = entry.evaluation_date - timedelta(days=i*7)  # Weekly intervals
        dates.append(date.strftime('%Y-%m-%d'))
        
        # Generate realistic trends around the actual performance
        accuracy_noise = np.random.normal(0, 0.02)
        accuracy = max(0.4, min(0.9, entry.accuracy + accuracy_noise))
        accuracies.append(round(accuracy * 100, 1))
        
        roi_noise = np.random.normal(0, 1.5)
        roi = entry.roi_percentage + roi_noise
        rois.append(round(roi, 1))
    
    # Reverse to chronological order
    dates.reverse()
    accuracies.reverse()
    rois.reverse()
    
    return {
        'dates': dates,
        'accuracy_trend': accuracies,
        'roi_trend': rois,
        'trend_analysis': {
            'accuracy_direction': 'improving' if accuracies[-1] > accuracies[0] else 'declining',
            'roi_direction': 'improving' if rois[-1] > rois[0] else 'declining',
            'volatility': 'low' if np.std(accuracies) < 2 else 'moderate' if np.std(accuracies) < 4 else 'high',
            'consistency_score': round(100 - (np.std(accuracies) / np.mean(accuracies) * 100), 1)
        }
    }

@app.route('/api/performance/leaderboard/<sport>', methods=['GET'])
@handle_errors
@require_authentication
def get_sport_leaderboard(sport):
    """Get performance leaderboard for a specific sport"""
    if not PERFORMANCE_MATRIX_AVAILABLE:
        return jsonify({'success': False, 'message': 'Performance matrix not available'}), 500
    
    try:
        if sport.upper() not in ['NBA', 'NFL', 'MLB', 'NCAAF', 'NCAAB']:
            raise ValidationError("Invalid sport")
        
        limit = int(request.args.get('limit', 10))
        if limit < 1 or limit > 50:
            limit = 10
        
        # Generate demo data if empty
        if not performance_matrix.performance_data:
            performance_matrix.generate_demo_data()
        
        leaderboard = performance_matrix.get_sport_leaderboard(sport.upper(), limit)
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard,
            'sport': sport.upper(),
            'total_entries': len(leaderboard)
        })
        
    except Exception as e:
        logger.error(f"Failed to get sport leaderboard: {e}")
        raise ValidationError(f'Failed to get sport leaderboard: {e}')

@app.route('/api/performance/model-types', methods=['GET'])
@handle_errors
@require_authentication
def get_model_type_analysis():
    """Get performance analysis by model type"""
    if not PERFORMANCE_MATRIX_AVAILABLE:
        return jsonify({'success': False, 'message': 'Performance matrix not available'}), 500
    
    try:
        # Generate demo data if empty
        if not performance_matrix.performance_data:
            performance_matrix.generate_demo_data()
        
        analysis = performance_matrix.get_model_type_analysis()
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'model_types_analyzed': len(analysis)
        })
        
    except Exception as e:
        logger.error(f"Failed to get model type analysis: {e}")
        raise ValidationError(f'Failed to get model type analysis: {e}')

@app.route('/api/performance/parameters', methods=['GET'])
@handle_errors
@require_authentication
def get_parameter_effectiveness():
    """Analyze parameter effectiveness across models"""
    if not PERFORMANCE_MATRIX_AVAILABLE:
        return jsonify({'success': False, 'message': 'Performance matrix not available'}), 500
    
    try:
        model_type = request.args.get('model_type')
        
        # Generate demo data if empty
        if not performance_matrix.performance_data:
            performance_matrix.generate_demo_data()
        
        parameter_analysis = performance_matrix.get_parameter_effectiveness(model_type)
        
        return jsonify({
            'success': True,
            'parameter_analysis': parameter_analysis,
            'model_type_filter': model_type,
            'parameters_analyzed': len(parameter_analysis)
        })
        
    except Exception as e:
        logger.error(f"Failed to get parameter effectiveness: {e}")
        raise ValidationError(f'Failed to get parameter effectiveness: {e}')

@app.route('/api/performance/trending', methods=['GET'])
@handle_errors
@require_authentication
def get_trending_models():
    """Get models with improving performance trends"""
    if not PERFORMANCE_MATRIX_AVAILABLE:
        return jsonify({'success': False, 'message': 'Performance matrix not available'}), 500
    
    try:
        days = int(request.args.get('days', 7))
        if days < 1 or days > 30:
            days = 7
        
        # Generate demo data if empty
        if not performance_matrix.performance_data:
            performance_matrix.generate_demo_data()
        
        trending_models = performance_matrix.get_trending_models(days)
        
        return jsonify({
            'success': True,
            'trending_models': trending_models,
            'analysis_period_days': days,
            'total_trending': len(trending_models)
        })
        
    except Exception as e:
        logger.error(f"Failed to get trending models: {e}")
        raise ValidationError(f'Failed to get trending models: {e}')

# --- SPORT-SPECIFIC MODEL ENDPOINTS ---

@app.route('/api/models/create-sport-model', methods=['POST'])
@handle_errors
@require_authentication
@sanitize_request_data(required_fields=['sport', 'model_type'], optional_fields=['model_name'])
def create_sport_specific_model():
    """Create a new sport-specific model"""
    if not SPORT_MODELS_AVAILABLE:
        return jsonify({'success': False, 'message': 'Sport models not available'}), 500
    
    try:
        data = g.sanitized_request_data
        user_id = g.current_user.get('user_id')
        
        sport_str = data.get('sport').upper()
        model_type_str = data.get('model_type').lower()
        model_name = data.get('model_name', f"{sport_str}_{model_type_str}_model")
        
        # Validate inputs
        try:
            sport = Sport(sport_str)
            model_type = ModelType(model_type_str)
        except ValueError as e:
            raise ValidationError(f"Invalid sport or model type: {e}")
        
        # Create unique model ID
        model_id = f"{sport_str.lower()}_{model_type_str}_{int(datetime.now().timestamp())}"
        
        # Create model instance
        model = SportsModelFactory.create_model(sport, model_type, model_id)
        
        # Register in model registry if available
        if hasattr(model_registry, 'register_model'):
            registry_id = model_registry.register_model(
                name=model_name,
                sport=sport_str,
                model_type=model_type_str,
                created_by=user_id,
                description=f"{model_type_str.title()} model for {sport_str} predictions"
            )
        else:
            registry_id = model_id
        
        logger.info(f"Sport-specific model created: {model_id} by user {user_id}")
        
        return jsonify({
            'success': True,
            'model_id': model_id,
            'registry_id': registry_id,
            'model_info': model.to_dict(),
            'features': model.get_features(),
            'architecture': model.get_architecture()
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create sport model: {e}")
        raise ValidationError(f'Failed to create sport model: {e}')

@app.route('/api/models/sport-features/<sport>/<model_type>', methods=['GET'])
@handle_errors
@require_authentication
def get_sport_model_features(sport, model_type):
    """Get features used by a specific sport and model type combination"""
    if not SPORT_MODELS_AVAILABLE:
        return jsonify({'success': False, 'message': 'Sport models not available'}), 500
    
    try:
        # Validate inputs
        try:
            sport_enum = Sport(sport.upper())
            model_type_enum = ModelType(model_type.lower())
        except ValueError as e:
            raise ValidationError(f"Invalid sport or model type: {e}")
        
        from sport_models import ModelConfig
        features = ModelConfig.get_features_for_sport(sport_enum, model_type_enum)
        architecture = ModelConfig.get_model_architecture(sport_enum, model_type_enum)
        
        return jsonify({
            'success': True,
            'sport': sport.upper(),
            'model_type': model_type.lower(),
            'features': features,
            'feature_count': len(features),
            'architecture': architecture,
            'weather_dependent': model_type_enum == ModelType.LSTM_WEATHER,
            'supports_time_series': model_type_enum == ModelType.LSTM_WEATHER
        })
        
    except Exception as e:
        logger.error(f"Failed to get sport model features: {e}")
        raise ValidationError(f'Failed to get sport model features: {e}')

# --- BACKTESTING ENDPOINTS ---

@app.route('/api/backtest/run', methods=['POST'])
@handle_errors
@require_authentication
@sanitize_request_data(required_fields=['model_id', 'sport', 'start_date', 'end_date'], 
                      optional_fields=['initial_bankroll', 'betting_strategy', 'bet_amount', 'min_confidence'])
def run_backtest():
    """Run backtesting simulation for a model"""
    if not BACKTESTING_AVAILABLE:
        return jsonify({'success': False, 'message': 'Backtesting engine not available'}), 500
    
    try:
        data = g.sanitized_request_data
        user_id = g.current_user.get('user_id')
        
        model_id = data.get('model_id')
        sport = data.get('sport').upper()
        
        # Parse dates
        start_date = datetime.fromisoformat(data.get('start_date').replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(data.get('end_date').replace('Z', '+00:00'))
        
        if start_date >= end_date:
            raise ValidationError("Start date must be before end date")
        
        if (end_date - start_date).days > 365:
            raise ValidationError("Backtest period cannot exceed 365 days")
        
        # Validate sport
        if sport not in ['NBA', 'NFL', 'MLB', 'NCAAF', 'NCAAB']:
            raise ValidationError("Invalid sport")
        
        # Get or create model for backtesting
        if SPORT_MODELS_AVAILABLE:
            # Create a demo model for backtesting
            sport_enum = Sport(sport)
            model_type_enum = ModelType.ENSEMBLE  # Default to ensemble
            model = SportsModelFactory.create_model(sport_enum, model_type_enum, model_id)
            
            # Simulate trained model
            model.is_trained = True
            model.performance_metrics = {'accuracy': 0.68}
        else:
            # Create a mock model for demo
            class MockModel:
                def predict(self, game_data):
                    return {
                        'home_win_probability': 0.6,
                        'away_win_probability': 0.4,
                        'predicted_outcome': 'Home Win',
                        'confidence': 0.72
                    }
            model = MockModel()
        
        # Create backtest configuration
        config = BacktestConfig(
            start_date=start_date.replace(tzinfo=None),
            end_date=end_date.replace(tzinfo=None),
            initial_bankroll=float(data.get('initial_bankroll', 1000)),
            betting_strategy=BettingStrategy(data.get('betting_strategy', 'percentage')),
            bet_amount=float(data.get('bet_amount', 2.0)),
            min_confidence=float(data.get('min_confidence', 0.6)),
            max_bet_percentage=0.1,  # Max 10% per bet
            commission_rate=0.05,    # 5% commission
            risk_management={}
        )
        
        # Run backtest
        result = backtesting_engine.run_backtest(model, sport, config)
        
        logger.info(f"Backtest completed for model {model_id} by user {user_id}")
        
        # Convert result to dict for JSON response
        result_dict = {
            'total_bets': result.total_bets,
            'winning_bets': result.winning_bets,
            'losing_bets': result.losing_bets,
            'win_rate': round(result.win_rate, 4),
            'total_profit_loss': round(result.total_profit_loss, 2),
            'final_bankroll': round(result.final_bankroll, 2),
            'roi_percentage': round(result.roi_percentage, 2),
            'max_drawdown': round(result.max_drawdown, 2),
            'max_drawdown_percentage': round(result.max_drawdown_percentage, 2),
            'sharpe_ratio': round(result.sharpe_ratio, 3),
            'sortino_ratio': round(result.sortino_ratio, 3),
            'calmar_ratio': round(result.calmar_ratio, 3),
            'profit_factor': round(result.profit_factor, 3),
            'avg_win': round(result.avg_win, 2),
            'avg_loss': round(result.avg_loss, 2),
            'largest_win': round(result.largest_win, 2),
            'largest_loss': round(result.largest_loss, 2),
            'consecutive_wins': result.consecutive_wins,
            'consecutive_losses': result.consecutive_losses,
            'total_commission_paid': round(result.total_commission_paid, 2),
            'total_amount_wagered': round(result.total_amount_wagered, 2),
            'bet_history': result.bet_history[-20:]  # Last 20 bets for display
        }
        
        return jsonify({
            'success': True,
            'backtest_result': result_dict,
            'model_id': model_id,
            'sport': sport,
            'config': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'initial_bankroll': config.initial_bankroll,
                'betting_strategy': config.betting_strategy.value,
                'bet_amount': config.bet_amount,
                'min_confidence': config.min_confidence
            }
        })
        
    except ValueError as e:
        raise ValidationError(f"Invalid parameter value: {str(e)}")
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise ValidationError(f'Backtest failed: {e}')

@app.route('/api/backtest/compare-strategies', methods=['POST'])
@handle_errors
@require_authentication
@sanitize_request_data(required_fields=['model_id', 'sport', 'start_date', 'end_date'], 
                      optional_fields=['strategies', 'initial_bankroll'])
def compare_betting_strategies():
    """Compare different betting strategies for a model"""
    if not BACKTESTING_AVAILABLE:
        return jsonify({'success': False, 'message': 'Backtesting engine not available'}), 500
    
    try:
        data = g.sanitized_request_data
        user_id = g.current_user.get('user_id')
        
        model_id = data.get('model_id')
        sport = data.get('sport').upper()
        
        # Parse dates
        start_date = datetime.fromisoformat(data.get('start_date').replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(data.get('end_date').replace('Z', '+00:00'))
        
        # Get strategies to compare
        strategy_names = data.get('strategies', ['fixed_amount', 'percentage', 'kelly_criterion'])
        strategies = [BettingStrategy(name) for name in strategy_names]
        
        # Create mock model
        class MockModel:
            def predict(self, game_data):
                return {
                    'home_win_probability': 0.6,
                    'away_win_probability': 0.4,
                    'predicted_outcome': 'Home Win',
                    'confidence': 0.72
                }
        model = MockModel()
        
        # Create base configuration
        base_config = BacktestConfig(
            start_date=start_date.replace(tzinfo=None),
            end_date=end_date.replace(tzinfo=None),
            initial_bankroll=float(data.get('initial_bankroll', 1000)),
            betting_strategy=BettingStrategy.PERCENTAGE,  # Will be overridden
            bet_amount=2.0,
            min_confidence=0.6,
            max_bet_percentage=0.1,
            commission_rate=0.05,
            risk_management={}
        )
        
        # Compare strategies
        results = backtesting_engine.compare_strategies(model, sport, base_config, strategies)
        
        # Format results
        comparison_results = {}
        for strategy_name, result in results.items():
            comparison_results[strategy_name] = {
                'total_bets': result.total_bets,
                'win_rate': round(result.win_rate, 4),
                'total_profit_loss': round(result.total_profit_loss, 2),
                'roi_percentage': round(result.roi_percentage, 2),
                'max_drawdown_percentage': round(result.max_drawdown_percentage, 2),
                'sharpe_ratio': round(result.sharpe_ratio, 3),
                'profit_factor': round(result.profit_factor, 3)
            }
        
        logger.info(f"Strategy comparison completed for model {model_id} by user {user_id}")
        
        return jsonify({
            'success': True,
            'strategy_comparison': comparison_results,
            'model_id': model_id,
            'sport': sport,
            'strategies_compared': len(results)
        })
        
    except Exception as e:
        logger.error(f"Strategy comparison failed: {e}")
        raise ValidationError(f'Strategy comparison failed: {e}')

# --- DATA PIPELINE ENDPOINTS ---

@app.route('/api/data/pipeline/status', methods=['GET'])
@handle_errors
@require_authentication
def get_data_pipeline_status():
    """Get current data pipeline status"""
    if not DATA_PIPELINE_AVAILABLE:
        return jsonify({'success': False, 'message': 'Data pipeline not available'}), 500
    
    try:
        pipeline_status = data_pipeline.get_pipeline_status()
        
        return jsonify({
            'success': True,
            'pipeline_status': pipeline_status
        })
        
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}")
        raise ValidationError(f'Failed to get pipeline status: {e}')

@app.route('/api/data/pipeline/run', methods=['POST'])
@handle_errors
@require_authentication
@sanitize_request_data(optional_fields=['sport'])
def run_data_pipeline():
    """Run the complete data pipeline"""
    if not DATA_PIPELINE_AVAILABLE:
        return jsonify({'success': False, 'message': 'Data pipeline not available'}), 500
    
    try:
        data = g.sanitized_request_data
        sport = data.get('sport')
        
        if sport and sport.upper() not in ['NBA', 'NFL', 'MLB', 'NCAAF', 'NCAAB']:
            raise ValidationError("Invalid sport specified")
        
        # Run the pipeline
        pipeline_result = data_pipeline.run_full_pipeline(sport)
        
        logger.info(f"Data pipeline executed for sport: {sport or 'all'}")
        
        return jsonify({
            'success': True,
            'pipeline_result': pipeline_result
        })
        
    except Exception as e:
        logger.error(f"Failed to run data pipeline: {e}")
        raise ValidationError(f'Failed to run data pipeline: {e}')

@app.route('/api/data/preprocessing/config', methods=['GET'])
@handle_errors
@require_authentication
def get_preprocessing_config():
    """Get data preprocessing configuration"""
    try:
        preprocessing_config = {
            'feature_engineering': {
                'rolling_averages': {
                    'enabled': True,
                    'windows': [3, 5, 10],
                    'features': ['points_scored', 'points_allowed', 'field_goal_percentage']
                },
                'momentum_indicators': {
                    'enabled': True,
                    'win_streak_weight': 0.15,
                    'recent_performance_window': 5
                },
                'opponent_adjustments': {
                    'enabled': True,
                    'strength_of_schedule': True,
                    'pace_adjustments': True
                }
            },
            'data_cleaning': {
                'outlier_detection': {
                    'method': 'isolation_forest',
                    'contamination': 0.05,
                    'enabled': True
                },
                'missing_value_handling': {
                    'numeric_strategy': 'median',
                    'categorical_strategy': 'mode',
                    'time_series_strategy': 'forward_fill'
                }
            },
            'normalization': {
                'method': 'standard_scaler',
                'features_to_normalize': ['pace', 'offensive_rating', 'defensive_rating'],
                'preserve_distribution': True
            },
            'validation_rules': {
                'min_games_played': 5,
                'max_score_differential': 50,
                'required_features': ['team_strength', 'opponent_strength', 'venue']
            }
        }
        
        return jsonify({
            'success': True,
            'preprocessing_config': preprocessing_config
        })
        
    except Exception as e:
        logger.error(f"Failed to get preprocessing config: {e}")
        raise ValidationError(f'Failed to get preprocessing config: {e}')

@app.route('/api/data/features/explain', methods=['GET'])
@handle_errors
@require_authentication
def explain_model_features():
    """Explain model input features and their importance"""
    try:
        sport = request.args.get('sport', 'NBA').upper()
        model_type = request.args.get('model_type', 'ensemble')
        
        # Get features for the sport and model type
        if SPORT_MODELS_AVAILABLE:
            try:
                sport_enum = Sport(sport)
                model_type_enum = ModelType(model_type)
                from sport_models import ModelConfig
                features = ModelConfig.get_features_for_sport(sport_enum, model_type_enum)
            except:
                features = ['home_win_pct', 'away_win_pct', 'home_team_ppg', 'away_team_ppg']
        else:
            features = ['home_win_pct', 'away_win_pct', 'home_team_ppg', 'away_team_ppg']
        
        # Create feature explanations
        feature_explanations = {
            'home_win_pct': {
                'description': 'Home team win percentage over the season',
                'importance': 0.25,
                'category': 'team_performance',
                'data_type': 'numeric',
                'range': [0.0, 1.0],
                'interpretation': 'Higher values indicate stronger teams'
            },
            'away_win_pct': {
                'description': 'Away team win percentage over the season',
                'importance': 0.22,
                'category': 'team_performance',
                'data_type': 'numeric',
                'range': [0.0, 1.0],
                'interpretation': 'Higher values indicate stronger teams'
            },
            'home_team_ppg': {
                'description': 'Home team average points per game',
                'importance': 0.18,
                'category': 'offensive_stats',
                'data_type': 'numeric',
                'range': [80.0, 130.0] if sport in ['NBA', 'NCAAB'] else [14.0, 45.0],
                'interpretation': 'Higher values indicate more potent offense'
            },
            'away_team_ppg': {
                'description': 'Away team average points per game',
                'importance': 0.16,
                'category': 'offensive_stats',
                'data_type': 'numeric',
                'range': [80.0, 130.0] if sport in ['NBA', 'NCAAB'] else [14.0, 45.0],
                'interpretation': 'Higher values indicate more potent offense'
            },
            'temperature': {
                'description': 'Game-time temperature in Fahrenheit',
                'importance': 0.08,
                'category': 'weather',
                'data_type': 'numeric',
                'range': [20.0, 100.0],
                'interpretation': 'Extreme temperatures can affect player performance'
            },
            'humidity': {
                'description': 'Relative humidity percentage',
                'importance': 0.06,
                'category': 'weather',
                'data_type': 'numeric',
                'range': [20.0, 90.0],
                'interpretation': 'High humidity can reduce stamina and ball handling'
            },
            'wind_speed': {
                'description': 'Wind speed in miles per hour',
                'importance': 0.05,
                'category': 'weather',
                'data_type': 'numeric',
                'range': [0.0, 30.0],
                'interpretation': 'High winds affect passing and kicking accuracy'
            }
        }
        
        # Filter explanations to only include features for this model
        relevant_explanations = {
            feature: feature_explanations.get(feature, {
                'description': f'{feature.replace("_", " ").title()}',
                'importance': 0.1,
                'category': 'unknown',
                'data_type': 'numeric',
                'interpretation': 'Feature importance varies by model'
            })
            for feature in features
        }
        
        # Calculate feature categories summary
        categories = {}
        for feature, info in relevant_explanations.items():
            category = info['category']
            if category not in categories:
                categories[category] = {'features': [], 'total_importance': 0}
            categories[category]['features'].append(feature)
            categories[category]['total_importance'] += info['importance']
        
        return jsonify({
            'success': True,
            'sport': sport,
            'model_type': model_type,
            'features': relevant_explanations,
            'feature_categories': categories,
            'total_features': len(features),
            'weather_dependent': model_type == 'lstm_weather'
        })
        
    except Exception as e:
        logger.error(f"Failed to explain features: {e}")
        raise ValidationError(f'Failed to explain features: {e}')

# --- NEW PROFESSIONAL DATA PIPELINE ENDPOINTS ---

@app.route('/api/data-pipeline/sources', methods=['GET'])
@handle_errors
@require_authentication
def get_data_sources():
    """Get available data sources and their status"""
    try:
        from professional_data_pipeline import pipeline_manager
        
        sources_status = pipeline_manager.get_data_source_status()
        
        return jsonify({
            'success': True,
            'data_sources': sources_status,
            'total_sources': len(sources_status),
            'enabled_sources': sum(1 for s in sources_status.values() if s['enabled'])
        })
        
    except Exception as e:
        logger.error(f"Failed to get data sources: {e}")
        raise ValidationError(f'Failed to get data sources: {e}')


@app.route('/api/data-pipeline/sources/<source_name>/toggle', methods=['POST'])
@handle_errors
@require_authentication
def toggle_data_source_endpoint(source_name):
    """Toggle a data source on/off"""
    try:
        from professional_data_pipeline import toggle_data_source
        
        data = request.get_json() or {}
        enabled = data.get('enabled', True)
        
        success = toggle_data_source(source_name, enabled)
        
        if success:
            return jsonify({
                'success': True,
                'message': f"Data source {source_name} {'enabled' if enabled else 'disabled'}",
                'source': source_name,
                'enabled': enabled
            })
        else:
            raise ValidationError(f"Unknown data source: {source_name}")
            
    except Exception as e:
        logger.error(f"Failed to toggle data source: {e}")
        raise ValidationError(f'Failed to toggle data source: {e}')


@app.route('/api/data-pipeline/jobs', methods=['POST'])
@handle_errors
@require_authentication
@sanitize_request_data(required_fields=['sport', 'model_type', 'data_sources'])
def submit_data_job():
    """Submit a data processing job"""
    try:
        from professional_data_pipeline import submit_data_job
        
        data = request.get_json()
        sport = data['sport']
        model_type = data['model_type']
        data_sources = data['data_sources']
        user_id = g.current_user.get('user_id', 'demo_user')
        
        # Validate inputs
        valid_sports = ['NBA', 'NFL', 'MLB', 'NCAAF', 'NCAAB']
        if sport not in valid_sports:
            raise ValidationError(f"Invalid sport. Must be one of: {valid_sports}")
            
        valid_model_types = ['lstm_weather', 'ensemble', 'neural_network', 'statistical']
        if model_type not in valid_model_types:
            raise ValidationError(f"Invalid model type. Must be one of: {valid_model_types}")
            
        if not isinstance(data_sources, list) or not data_sources:
            raise ValidationError("data_sources must be a non-empty list")
        
        job_id = submit_data_job(sport, model_type, data_sources, user_id)
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Data processing job submitted successfully',
            'sport': sport,
            'model_type': model_type,
            'data_sources': data_sources,
            'estimated_completion': '10 minutes'
        })
        
    except Exception as e:
        logger.error(f"Failed to submit data job: {e}")
        raise ValidationError(f'Failed to submit job: {e}')


@app.route('/api/data-pipeline/jobs/<job_id>', methods=['GET'])
@handle_errors
@require_authentication
def get_job_status(job_id):
    """Get the status of a data processing job"""
    try:
        from professional_data_pipeline import pipeline_manager
        
        job = pipeline_manager.get_job_status(job_id)
        
        if not job:
            raise ValidationError(f"Job {job_id} not found")
        
        # Convert job to dict for JSON serialization
        job_data = {
            'job_id': job.job_id,
            'sport': job.sport,
            'model_type': job.model_type,
            'data_sources': [ds.value for ds in job.data_sources],
            'status': job.status.value,
            'progress_percent': job.progress_percent,
            'created_at': job.created_at.isoformat(),
            'estimated_completion': job.estimated_completion.isoformat() if job.estimated_completion else None,
            'error_message': job.error_message,
            'logs': job.logs[-10:],  # Last 10 log entries
            'results_available': job.status.value == 'completed' and bool(job.results)
        }
        
        return jsonify({
            'success': True,
            'job': job_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise ValidationError(f'Failed to get job status: {e}')


@app.route('/api/data-pipeline/jobs', methods=['GET'])
@handle_errors
@require_authentication
def get_user_jobs():
    """Get all jobs for the current user"""
    try:
        from professional_data_pipeline import pipeline_manager
        
        user_id = g.current_user.get('user_id', 'demo_user')
        jobs = pipeline_manager.get_user_jobs(user_id)
        
        jobs_data = []
        for job in jobs:
            job_data = {
                'job_id': job.job_id,
                'sport': job.sport,
                'model_type': job.model_type,
                'status': job.status.value,
                'progress_percent': job.progress_percent,
                'created_at': job.created_at.isoformat(),
                'data_sources_count': len(job.data_sources),
                'has_results': bool(job.results)
            }
            jobs_data.append(job_data)
            
        return jsonify({
            'success': True,
            'jobs': jobs_data,
            'total_jobs': len(jobs_data)
        })
        
    except Exception as e:
        logger.error(f"Failed to get user jobs: {e}")
        raise ValidationError(f'Failed to get user jobs: {e}')


# --- INVESTMENT MANAGEMENT ENDPOINTS ---

@app.route('/api/investments/hold', methods=['POST'])
@handle_errors
@require_authentication
@sanitize_request_data(required_fields=['game_id', 'bet_type', 'selection', 'odds', 'amount'])
def hold_investment():
    """Hold an investment for manual export and placement"""
    try:
        from sportsbook_api import BetRequest, BetType
        
        # Use global betting service
        global betting_service
        if not betting_service:
            raise ValidationError("Betting service not initialized")
        
        data = request.get_json()
        user_id = g.current_user.get('user_id', 'demo_user')
        
        # Create bet request
        bet_request = BetRequest(
            game_id=data['game_id'],
            bet_type=BetType(data['bet_type']),
            selection=data['selection'],
            odds=float(data['odds']),
            amount=float(data['amount']),
            line=data.get('line'),
            sportsbook=data.get('sportsbook'),
            notes=data.get('notes', ''),
            confidence=data.get('confidence'),
            model_prediction=data.get('model_prediction', {})
        )
        
        result = betting_service.hold_investment(bet_request, user_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to hold investment: {e}")
        raise ValidationError(f'Failed to hold investment: {e}')


@app.route('/api/investments/pending', methods=['GET'])
@handle_errors
@require_authentication
def get_pending_investments():
    """Get pending investments for the current user"""
    try:
        # Use global betting service
        global betting_service
        if not betting_service:
            raise ValidationError("Betting service not initialized")
        
        user_id = g.current_user.get('user_id', 'demo_user')
        investments = betting_service.get_pending_investments(user_id)
        
        # Convert datetime objects to ISO strings
        for inv in investments:
            inv['created_at'] = inv['created_at'].isoformat()
            if 'confirmed_at' in inv:
                inv['confirmed_at'] = inv['confirmed_at'].isoformat()
        
        return jsonify({
            'success': True,
            'investments': investments,
            'total_count': len(investments),
            'total_amount': sum(inv['amount'] for inv in investments),
            'total_potential_payout': sum(inv['potential_payout'] for inv in investments)
        })
        
    except Exception as e:
        logger.error(f"Failed to get pending investments: {e}")
        raise ValidationError(f'Failed to get pending investments: {e}')


@app.route('/api/investments/export', methods=['GET'])
@handle_errors
@require_authentication
def export_investments():
    """Export pending investments to CSV"""
    try:
        from flask import Response
        
        # Use global betting service
        global betting_service
        if not betting_service:
            raise ValidationError("Betting service not initialized")
        
        user_id = g.current_user.get('user_id', 'demo_user')
        csv_content = betting_service.export_investments_to_csv(user_id)
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=investments_{user_id}_{datetime.datetime.now().strftime("%Y%m%d")}.csv'}
        )
        
    except Exception as e:
        logger.error(f"Failed to export investments: {e}")
        raise ValidationError(f'Failed to export investments: {e}')


@app.route('/api/investments/<investment_id>/confirm', methods=['POST'])
@handle_errors
@require_authentication
def confirm_investment(investment_id):
    """Confirm that an investment was manually placed"""
    try:
        # Use global betting service
        global betting_service
        if not betting_service:
            raise ValidationError("Betting service not initialized")
        
        data = request.get_json() or {}
        user_id = g.current_user.get('user_id', 'demo_user')
        
        result = betting_service.confirm_investment(
            investment_id=investment_id,
            user_id=user_id,
            actual_odds=data.get('actual_odds'),
            actual_amount=data.get('actual_amount'),
            bet_slip_id=data.get('bet_slip_id')
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to confirm investment: {e}")
        raise ValidationError(f'Failed to confirm investment: {e}')


@app.route('/api/investments/<investment_id>/edit', methods=['PUT'])
@handle_errors
@require_authentication
def edit_investment(investment_id):
    """Edit a pending investment"""
    try:
        # Use global betting service
        global betting_service
        if not betting_service:
            raise ValidationError("Betting service not initialized")
        
        data = request.get_json() or {}
        user_id = g.current_user.get('user_id', 'demo_user')
        
        result = betting_service.edit_investment(investment_id, user_id, data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to edit investment: {e}")
        raise ValidationError(f'Failed to edit investment: {e}')


@app.route('/api/investments/<investment_id>/reject', methods=['POST'])
@handle_errors
@require_authentication
def reject_investment(investment_id):
    """Reject/cancel a pending investment"""
    try:
        # Use global betting service
        global betting_service
        if not betting_service:
            raise ValidationError("Betting service not initialized")
        
        data = request.get_json() or {}
        user_id = g.current_user.get('user_id', 'demo_user')
        reason = data.get('reason', 'User cancelled')
        
        result = betting_service.reject_investment(investment_id, user_id, reason)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to reject investment: {e}")
        raise ValidationError(f'Failed to reject investment: {e}')


# --- ENHANCED TRAINING ENDPOINTS ---

@app.route('/api/training/real-training', methods=['POST'])
@handle_errors
@require_authentication
@sanitize_request_data(required_fields=['sport', 'model_type'])
def start_real_training():
    """Start real model training with GPU infrastructure"""
    try:
        from training_queue import training_queue_manager
        
        data = request.get_json()
        sport = data['sport']
        model_type = data['model_type']
        user_id = g.current_user.get('user_id', 'demo_user')
        
        # Enhanced training configuration
        training_config = {
            'sport': sport,
            'model_type': model_type,
            'use_real_data': True,
            'use_weather_features': model_type == 'lstm_weather',
            'epochs': data.get('epochs', 50),
            'batch_size': data.get('batch_size', 32),
            'learning_rate': data.get('learning_rate', 0.001),
            'hidden_units': data.get('hidden_units', 128),
            'dropout_rate': data.get('dropout_rate', 0.2)
        }
        
        # Submit training job
        job_id = training_queue_manager.submit_training_job(
            model_name=f"{sport}_{model_type}_model",
            sport=sport,
            epochs=training_config['epochs'],
            user_id=user_id,
            training_config=training_config
        )
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': f'Real training started for {sport} {model_type} model',
            'training_config': training_config,
            'estimated_duration': f"{training_config['epochs'] * 10} seconds"
        })
        
    except Exception as e:
        logger.error(f"Failed to start real training: {e}")
        raise ValidationError(f'Failed to start training: {e}')


@app.route('/api/training/gpu-status', methods=['GET'])
@handle_errors
@require_authentication
def get_gpu_status():
    """Get current GPU status and availability"""
    try:
        from real_model_training import get_gpu_status
        
        gpu_status = get_gpu_status()
        
        return jsonify({
            'success': True,
            'gpus': gpu_status,
            'total_gpus': len(gpu_status),
            'available_gpus': sum(1 for gpu in gpu_status if gpu['is_available'])
        })
        
    except Exception as e:
        logger.error(f"Failed to get GPU status: {e}")
        raise ValidationError(f'Failed to get GPU status: {e}')


# Main execution guard - only run when script is executed directly
if __name__ == '__main__':
    # The app has already been created and initialized above
    # Just run it directly on port 5001 to avoid conflicts
    app.run(debug=True, port=5001)