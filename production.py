#!/usr/bin/env python3
"""
Production server configuration for Post9
"""

import os
import sys
from pathlib import Path

# Suppress TensorFlow oneDNN verbose messages
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Add the dashboard directory to Python path
dashboard_dir = Path(__file__).parent / "dashboard"
sys.path.insert(0, str(dashboard_dir))

from app import app
import logging
from logging.handlers import RotatingFileHandler

def setup_production_logging():
    """Setup production-level logging"""
    if not app.debug:
        # Ensure logs directory exists
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Setup file handler with rotation
        file_handler = RotatingFileHandler(
            'logs/sihq.log', 
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Post9 startup')

def create_production_app():
    """Create production-ready Flask app"""
    # Set production environment
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    setup_production_logging()
    return app

if __name__ == '__main__':
    # Only run for development testing
    production_app = create_production_app()
    production_app.run(host='0.0.0.0', port=5000)
else:
    # For WSGI servers like Gunicorn
    application = create_production_app()