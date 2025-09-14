"""
Professional configuration management for Post9 application
"""
import os
import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class DatabaseConfig:
    firebase_project_id: str
    firebase_app_id: str
    firebase_api_key: str
    firebase_auth_domain: str
    firebase_storage_bucket: str
    firebase_messaging_sender_id: str
    service_account_path: Optional[str] = None

@dataclass
class APIConfig:
    sports_api_key: Optional[str] = None
    odds_api_key: Optional[str] = None
    weather_api_key: Optional[str] = None
    # Sportsbook APIs for real betting
    draftkings_api_key: Optional[str] = None
    fanduel_api_key: Optional[str] = None
    betmgm_api_key: Optional[str] = None
    rate_limit_per_hour: int = 500
    timeout_seconds: int = 30
    enable_real_betting: bool = False

@dataclass
class MLConfig:
    model_storage_path: str = "./models"
    max_training_samples: int = 10000
    default_confidence_threshold: float = 0.65
    enable_model_caching: bool = True

@dataclass
class AppConfig:
    environment: Environment
    debug: bool
    secret_key: str
    database: DatabaseConfig
    api: APIConfig
    ml: MLConfig
    host: str = "127.0.0.1"
    port: int = 5000
    log_level: str = "INFO"
    disable_demo_mode: bool = False

class ConfigManager:
    """Professional configuration management with validation"""
    
    @staticmethod
    def load_config() -> AppConfig:
        """Load configuration from environment variables with validation"""
        from dotenv import load_dotenv
        load_dotenv()
        
        # Determine environment
        env_str = os.getenv('ENVIRONMENT', 'development').lower()
        try:
            environment = Environment(env_str)
        except ValueError:
            environment = Environment.DEVELOPMENT
            
        # Validate required environment variables for production
        if environment == Environment.PRODUCTION:
            required_vars = [
                'FIREBASE_PROJECT_ID', 'FIREBASE_APP_ID', 'FIREBASE_API_KEY',
                'SECRET_KEY', 'GOOGLE_APPLICATION_CREDENTIALS'
            ]
            missing = [var for var in required_vars if not os.getenv(var)]
            if missing:
                raise ValueError(f"Missing required environment variables for production: {missing}")
        
        # Database configuration
        database = DatabaseConfig(
            firebase_project_id=os.getenv('FIREBASE_PROJECT_ID', 'demo-project'),
            firebase_app_id=os.getenv('FIREBASE_APP_ID', '1:123456789:web:demo123'),
            firebase_api_key=os.getenv('FIREBASE_API_KEY', 'demo_api_key'),
            firebase_auth_domain=os.getenv('FIREBASE_AUTH_DOMAIN', 'demo.firebaseapp.com'),
            firebase_storage_bucket=os.getenv('FIREBASE_STORAGE_BUCKET', 'demo-project.appspot.com'),
            firebase_messaging_sender_id=os.getenv('FIREBASE_MESSAGING_SENDER_ID', '123456789'),
            service_account_path=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        )
        
        # API configuration
        api = APIConfig(
            sports_api_key=os.getenv('SPORTS_API_KEY'),
            odds_api_key=os.getenv('ODDS_API_KEY'),
            weather_api_key=os.getenv('WEATHER_API_KEY'),
            draftkings_api_key=os.getenv('DRAFTKINGS_API_KEY'),
            fanduel_api_key=os.getenv('FANDUEL_API_KEY'),
            betmgm_api_key=os.getenv('BETMGM_API_KEY'),
            rate_limit_per_hour=int(os.getenv('RATE_LIMIT_PER_HOUR', '500')),
            timeout_seconds=int(os.getenv('API_TIMEOUT_SECONDS', '30')),
            enable_real_betting=os.getenv('ENABLE_REAL_BETTING', 'false').lower() == 'true'
        )
        
        # ML configuration
        ml = MLConfig(
            model_storage_path=os.getenv('MODEL_STORAGE_PATH', './models'),
            max_training_samples=int(os.getenv('MAX_TRAINING_SAMPLES', '10000')),
            default_confidence_threshold=float(os.getenv('DEFAULT_CONFIDENCE_THRESHOLD', '0.65')),
            enable_model_caching=os.getenv('ENABLE_MODEL_CACHING', 'true').lower() == 'true'
        )
        
        return AppConfig(
            environment=environment,
            debug=environment != Environment.PRODUCTION,
            secret_key=os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
            host=os.getenv('HOST', '127.0.0.1'),
            port=int(os.getenv('PORT', '5000')),
            database=database,
            api=api,
            ml=ml,
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            disable_demo_mode=os.getenv('DISABLE_DEMO_MODE', 'false').lower() == 'true'
        )

def setup_logging(config: AppConfig):
    """Set up professional logging configuration"""
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
    )
    simple_formatter = logging.Formatter(log_format)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format=log_format,
        handlers=[]
    )
    
    # File handler for all logs
    file_handler = logging.FileHandler('logs/post9.log')
    file_handler.setFormatter(detailed_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Error file handler
    error_handler = logging.FileHandler('logs/post9_errors.log')
    error_handler.setFormatter(detailed_formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(getattr(logging, config.log_level))
    
    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

def validate_config(config: AppConfig) -> list[str]:
    """Validate configuration and return list of warnings/errors"""
    warnings = []
    
    # Check for demo/development settings in production
    if config.environment == Environment.PRODUCTION:
        if 'demo' in config.database.firebase_api_key.lower():
            warnings.append("Production environment using demo Firebase credentials")
        if config.api.sports_api_key and 'demo' in config.api.sports_api_key.lower():
            warnings.append("Production environment using demo Sports API key")
        if config.secret_key == 'dev-secret-key-change-in-production':
            warnings.append("Production environment using default secret key")
    
    # Check ML configuration
    if not os.path.exists(config.ml.model_storage_path):
        try:
            os.makedirs(config.ml.model_storage_path, exist_ok=True)
        except Exception as e:
            warnings.append(f"Cannot create model storage directory: {e}")
    
    return warnings