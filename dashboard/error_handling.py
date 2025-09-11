"""
Professional error handling and response system for Post9
"""
import logging
import traceback
from functools import wraps
from typing import Any, Dict, Optional, Union
from datetime import datetime

from flask import jsonify, request, g

logger = logging.getLogger(__name__)

class Post9Error(Exception):
    """Base exception class for Post9 application"""
    def __init__(self, message: str, error_code: str = None, status_code: int = 500, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()

class ValidationError(Post9Error):
    """Raised when input validation fails"""
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", status_code=400, **kwargs)
        if field:
            self.details['field'] = field

class AuthenticationError(Post9Error):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(message, error_code="AUTHENTICATION_ERROR", status_code=401, **kwargs)

class AuthorizationError(Post9Error):
    """Raised when user lacks permission"""
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(message, error_code="AUTHORIZATION_ERROR", status_code=403, **kwargs)

class ResourceNotFoundError(Post9Error):
    """Raised when requested resource doesn't exist"""
    def __init__(self, resource_type: str, resource_id: str = None, **kwargs):
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message, error_code="RESOURCE_NOT_FOUND", status_code=404, **kwargs)
        self.details['resource_type'] = resource_type
        if resource_id:
            self.details['resource_id'] = resource_id

class ModelError(Post9Error):
    """Raised when ML model operations fail"""
    def __init__(self, message: str, model_id: str = None, **kwargs):
        super().__init__(message, error_code="MODEL_ERROR", status_code=422, **kwargs)
        if model_id:
            self.details['model_id'] = model_id

class ExternalServiceError(Post9Error):
    """Raised when external service calls fail"""
    def __init__(self, service_name: str, message: str = None, **kwargs):
        message = message or f"{service_name} service unavailable"
        super().__init__(message, error_code="EXTERNAL_SERVICE_ERROR", status_code=503, **kwargs)
        self.details['service_name'] = service_name

class RateLimitError(Post9Error):
    """Raised when rate limits are exceeded"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None, **kwargs):
        super().__init__(message, error_code="RATE_LIMIT_ERROR", status_code=429, **kwargs)
        if retry_after:
            self.details['retry_after'] = retry_after

def log_error(error: Exception, request_context: Dict[str, Any] = None):
    """Log error with context information"""
    error_id = f"error_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
    
    error_info = {
        'error_id': error_id,
        'error_type': type(error).__name__,
        'message': str(error),
        'timestamp': datetime.utcnow().isoformat(),
        'request_context': request_context or {}
    }
    
    # Add request context if available
    if hasattr(request, 'method'):
        error_info['request_context'].update({
            'method': request.method,
            'url': request.url,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'ip_address': request.remote_addr,
            'request_id': getattr(g, 'request_id', None)
        })
    
    # Add Post9Error specific details
    if isinstance(error, Post9Error):
        error_info.update({
            'error_code': error.error_code,
            'status_code': error.status_code,
            'details': error.details
        })
        logger.error(f"Post9Error occurred: {error_info}")
    else:
        error_info['traceback'] = traceback.format_exc()
        logger.error(f"Unexpected error occurred: {error_info}")
    
    return error_id

def create_error_response(error: Exception, request_context: Dict[str, Any] = None) -> tuple:
    """Create standardized error response"""
    error_id = log_error(error, request_context)
    
    if isinstance(error, Post9Error):
        response_data = {
            'success': False,
            'error': {
                'code': error.error_code,
                'message': error.message,
                'details': error.details,
                'timestamp': error.timestamp,
                'error_id': error_id
            }
        }
        return jsonify(response_data), error.status_code
    else:
        # Generic error response for unexpected errors
        response_data = {
            'success': False,
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'An unexpected error occurred',
                'error_id': error_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        return jsonify(response_data), 500

def handle_errors(f):
    """Decorator to handle errors in API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Post9Error as e:
            return create_error_response(e)
        except Exception as e:
            return create_error_response(e)
    return decorated_function

def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """Validate that required fields are present in request data"""
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    if missing_fields:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing_fields)}",
            details={'missing_fields': missing_fields}
        )

def validate_user_id(user_id: str) -> None:
    """Validate user ID format"""
    if not user_id or not isinstance(user_id, str) or len(user_id.strip()) == 0:
        raise ValidationError("Invalid user ID", field="user_id")

def validate_model_id(model_id: str) -> None:
    """Validate model ID format"""
    if not model_id or not isinstance(model_id, str) or len(model_id.strip()) == 0:
        raise ValidationError("Invalid model ID", field="model_id")

def validate_pagination_params(page: Any, per_page: Any) -> tuple[int, int]:
    """Validate and convert pagination parameters"""
    try:
        page = int(page) if page is not None else 1
        per_page = int(per_page) if per_page is not None else 20
    except (ValueError, TypeError):
        raise ValidationError("Page and per_page must be integers")
    
    if page < 1:
        raise ValidationError("Page must be >= 1", field="page")
    if per_page < 1 or per_page > 100:
        raise ValidationError("Per page must be between 1 and 100", field="per_page")
    
    return page, per_page

def validate_confidence_threshold(confidence: Any) -> float:
    """Validate confidence threshold parameter"""
    try:
        confidence = float(confidence)
    except (ValueError, TypeError):
        raise ValidationError("Confidence threshold must be a number", field="confidence_threshold")
    
    if not 0 <= confidence <= 1:
        raise ValidationError("Confidence threshold must be between 0 and 1", field="confidence_threshold")
    
    return confidence

def safe_external_api_call(func, service_name: str, *args, **kwargs):
    """Safely call external API with error handling"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"External API call to {service_name} failed: {str(e)}")
        raise ExternalServiceError(service_name, str(e))

class ErrorMonitor:
    """Monitor and track error patterns"""
    
    def __init__(self):
        self.error_counts = {}
        self.last_reset = datetime.utcnow()
    
    def record_error(self, error_code: str, endpoint: str = None):
        """Record error occurrence for monitoring"""
        key = f"{error_code}:{endpoint}" if endpoint else error_code
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # Reset counts hourly
        now = datetime.utcnow()
        if (now - self.last_reset).total_seconds() > 3600:  # 1 hour
            self.error_counts.clear()
            self.last_reset = now
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get current error statistics"""
        return self.error_counts.copy()
    
    def check_error_threshold(self, error_code: str, threshold: int = 10) -> bool:
        """Check if error threshold is exceeded"""
        return self.error_counts.get(error_code, 0) >= threshold

# Global error monitor instance
error_monitor = ErrorMonitor()