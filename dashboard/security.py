"""
Professional security and authentication system for Post9
"""
import hashlib
import hmac
import jwt
import time
import secrets
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Optional, Any

from flask import request, g, current_app
from error_handling import AuthenticationError, AuthorizationError, ValidationError

logger = logging.getLogger(__name__)

class SecurityManager:
    """Centralized security management"""
    
    def __init__(self, secret_key: str, token_expiry_hours: int = 24):
        self.secret_key = secret_key
        self.token_expiry_hours = token_expiry_hours
        self.rate_limiter = RateLimiter()
    
    def generate_api_key(self, user_id: str, permissions: list = None) -> str:
        """Generate secure API key for user"""
        payload = {
            'user_id': user_id,
            'permissions': permissions or ['read'],
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=365)).isoformat()
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        logger.info(f"Generated API key for user {user_id}")
        return token
    
    def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Validate API key and return user info"""
        try:
            payload = jwt.decode(api_key, self.secret_key, algorithms=['HS256'])
            
            # Check expiration
            expires_at = datetime.fromisoformat(payload.get('expires_at', ''))
            if datetime.utcnow() > expires_at:
                raise AuthenticationError("API key expired")
            
            return payload
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid API key: {str(e)}")
            raise AuthenticationError("Invalid API key")
    
    def create_session_token(self, user_id: str, user_data: Dict[str, Any] = None) -> str:
        """Create secure session token"""
        payload = {
            'user_id': user_id,
            'user_data': user_data or {},
            'issued_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(hours=self.token_expiry_hours)).isoformat(),
            'session_id': secrets.token_urlsafe(32)
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def validate_session_token(self, token: str) -> Dict[str, Any]:
        """Validate session token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Check expiration
            expires_at = datetime.fromisoformat(payload.get('expires_at', ''))
            if datetime.utcnow() > expires_at:
                raise AuthenticationError("Session expired")
            
            return payload
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid session token")
    
    def hash_password(self, password: str) -> str:
        """Hash password securely"""
        salt = secrets.token_bytes(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return salt.hex() + ':' + password_hash.hex()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            salt_hex, hash_hex = hashed.split(':')
            salt = bytes.fromhex(salt_hex)
            stored_hash = bytes.fromhex(hash_hex)
            
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            return hmac.compare_digest(stored_hash, password_hash)
        except ValueError:
            return False

class RateLimiter:
    """Rate limiting for API endpoints"""
    
    def __init__(self):
        self.requests = {}  # In production, use Redis
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()
    
    def is_allowed(self, identifier: str, limit: int, window: int) -> bool:
        """Check if request is within rate limit"""
        now = time.time()
        
        # Cleanup old entries periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
            self.last_cleanup = now
        
        # Get request history for identifier
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        request_times = self.requests[identifier]
        
        # Remove requests outside the window
        cutoff = now - window
        request_times[:] = [t for t in request_times if t > cutoff]
        
        # Check if under limit
        if len(request_times) < limit:
            request_times.append(now)
            return True
        
        return False
    
    def _cleanup_old_entries(self):
        """Remove old rate limit entries"""
        now = time.time()
        cutoff = now - 3600  # Keep last hour only
        
        for identifier in list(self.requests.keys()):
            self.requests[identifier] = [
                t for t in self.requests[identifier] if t > cutoff
            ]
            
            # Remove empty entries
            if not self.requests[identifier]:
                del self.requests[identifier]

class InputSanitizer:
    """Sanitize and validate user inputs"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        # Enforce length limit
        if len(sanitized) > max_length:
            raise ValidationError(f"String too long (max {max_length} characters)")
        
        return sanitized
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        import os
        import re
        
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # Remove leading dots
        filename = filename.lstrip('.')
        
        if not filename:
            raise ValidationError("Invalid filename")
        
        return filename
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validate and sanitize email address"""
        import re
        
        email = InputSanitizer.sanitize_string(email, 254)
        
        # Basic email regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValidationError("Invalid email format")
        
        return email.lower()

def require_authentication(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key in headers
        api_key = request.headers.get('X-API-Key')
        auth_header = request.headers.get('Authorization', '')
        
        if api_key:
            try:
                user_info = current_app.security_manager.validate_api_key(api_key)
                g.current_user = user_info
                g.auth_method = 'api_key'
            except AuthenticationError:
                raise AuthenticationError("Invalid API key")
        elif auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            try:
                user_info = current_app.security_manager.validate_session_token(token)
                g.current_user = user_info
                g.auth_method = 'session_token'
            except AuthenticationError:
                raise AuthenticationError("Invalid session token")
        else:
            # For demo purposes, allow anonymous access with user_id from request
            request_data = request.get_json() or {}
            user_id = request_data.get('user_id') or request.args.get('user_id', 'anonymous')
            
            g.current_user = {
                'user_id': user_id,
                'permissions': ['read', 'write'],
                'auth_method': 'demo'
            }
            g.auth_method = 'demo'
        
        return f(*args, **kwargs)
    return decorated_function

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                raise AuthenticationError("Authentication required")
            
            permissions = g.current_user.get('permissions', [])
            if permission not in permissions and 'admin' not in permissions:
                raise AuthorizationError(f"Permission '{permission}' required")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit(requests_per_hour: int = 1000):
    """Decorator to apply rate limiting"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get identifier (user ID or IP address)
            identifier = getattr(g, 'current_user', {}).get('user_id') or request.remote_addr
            
            rate_limiter = current_app.security_manager.rate_limiter
            
            if not rate_limiter.is_allowed(identifier, requests_per_hour, 3600):
                logger.warning(f"Rate limit exceeded for {identifier}")
                raise AuthenticationError("Rate limit exceeded")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_request_data(required_fields: list = None, optional_fields: list = None):
    """Decorator to sanitize request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.is_json:
                data = request.get_json() or {}
                sanitized_data = {}
                
                # Sanitize required fields
                for field in (required_fields or []):
                    if field not in data:
                        raise ValidationError(f"Required field '{field}' missing")
                    
                    value = data[field]
                    if isinstance(value, str):
                        sanitized_data[field] = InputSanitizer.sanitize_string(value)
                    else:
                        sanitized_data[field] = value
                
                # Sanitize optional fields
                for field in (optional_fields or []):
                    if field in data:
                        value = data[field]
                        if isinstance(value, str):
                            sanitized_data[field] = InputSanitizer.sanitize_string(value)
                        else:
                            sanitized_data[field] = value
                
                # Store sanitized data
                g.sanitized_request_data = sanitized_data
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_request_fingerprint() -> str:
    """Generate unique fingerprint for request tracking"""
    components = [
        request.remote_addr,
        request.headers.get('User-Agent', ''),
        str(time.time())
    ]
    
    fingerprint_data = '|'.join(components)
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]

def log_security_event(event_type: str, details: Dict[str, Any] = None):
    """Log security-related events"""
    event_data = {
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown'),
        'user_id': getattr(g, 'current_user', {}).get('user_id'),
        'request_fingerprint': get_request_fingerprint(),
        'details': details or {}
    }
    
    logger.info(f"Security event: {event_data}")
    
    # In production, send to security monitoring system
    # security_monitor.record_event(event_data)