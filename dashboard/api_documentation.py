"""
API documentation and validation system for Post9
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import json

from error_handling import ValidationError

class FieldType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    EMAIL = "email"
    UUID = "uuid"

@dataclass
class APIField:
    name: str
    field_type: FieldType
    required: bool = False
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    description: str = ""

@dataclass 
class APIEndpoint:
    path: str
    method: str
    description: str
    request_fields: List[APIField]
    response_fields: List[APIField]
    tags: List[str] = None
    example_request: Dict[str, Any] = None
    example_response: Dict[str, Any] = None

class APIValidator:
    """Professional API request validation"""
    
    @staticmethod
    def validate_field(value: Any, field: APIField) -> Any:
        """Validate a single field value"""
        # Check required fields
        if field.required and (value is None or value == ""):
            raise ValidationError(f"Field '{field.name}' is required", field=field.name)
        
        # Skip validation for None values on optional fields
        if value is None and not field.required:
            return value
        
        # Type validation and conversion
        validated_value = APIValidator._validate_type(value, field)
        
        # Range validation
        APIValidator._validate_range(validated_value, field)
        
        # Length validation
        APIValidator._validate_length(validated_value, field)
        
        # Pattern validation
        APIValidator._validate_pattern(validated_value, field)
        
        # Allowed values validation
        APIValidator._validate_allowed_values(validated_value, field)
        
        return validated_value
    
    @staticmethod
    def _validate_type(value: Any, field: APIField) -> Any:
        """Validate and convert field type"""
        try:
            if field.field_type == FieldType.STRING:
                return str(value)
            elif field.field_type == FieldType.INTEGER:
                return int(value)
            elif field.field_type == FieldType.FLOAT:
                return float(value)
            elif field.field_type == FieldType.BOOLEAN:
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            elif field.field_type == FieldType.ARRAY:
                if isinstance(value, list):
                    return value
                raise ValueError("Must be an array")
            elif field.field_type == FieldType.OBJECT:
                if isinstance(value, dict):
                    return value
                raise ValueError("Must be an object")
            elif field.field_type == FieldType.EMAIL:
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, str(value)):
                    raise ValueError("Invalid email format")
                return str(value)
            elif field.field_type == FieldType.UUID:
                import uuid
                return str(uuid.UUID(str(value)))
            else:
                return value
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid {field.field_type.value} for field '{field.name}': {str(e)}", field=field.name)
    
    @staticmethod
    def _validate_range(value: Any, field: APIField):
        """Validate numeric range"""
        if field.min_value is not None and isinstance(value, (int, float)) and value < field.min_value:
            raise ValidationError(f"Field '{field.name}' must be >= {field.min_value}", field=field.name)
        
        if field.max_value is not None and isinstance(value, (int, float)) and value > field.max_value:
            raise ValidationError(f"Field '{field.name}' must be <= {field.max_value}", field=field.name)
    
    @staticmethod
    def _validate_length(value: Any, field: APIField):
        """Validate string/array length"""
        if hasattr(value, '__len__'):
            length = len(value)
            if field.min_length is not None and length < field.min_length:
                raise ValidationError(f"Field '{field.name}' must have at least {field.min_length} characters", field=field.name)
            
            if field.max_length is not None and length > field.max_length:
                raise ValidationError(f"Field '{field.name}' must have at most {field.max_length} characters", field=field.name)
    
    @staticmethod
    def _validate_pattern(value: Any, field: APIField):
        """Validate string pattern"""
        if field.pattern and isinstance(value, str):
            import re
            if not re.match(field.pattern, value):
                raise ValidationError(f"Field '{field.name}' does not match required pattern", field=field.name)
    
    @staticmethod
    def _validate_allowed_values(value: Any, field: APIField):
        """Validate allowed values"""
        if field.allowed_values and value not in field.allowed_values:
            raise ValidationError(f"Field '{field.name}' must be one of: {field.allowed_values}", field=field.name)

    @staticmethod
    def validate_request(data: Dict[str, Any], fields: List[APIField]) -> Dict[str, Any]:
        """Validate entire request against field definitions"""
        validated_data = {}
        
        for field in fields:
            value = data.get(field.name)
            validated_data[field.name] = APIValidator.validate_field(value, field)
        
        return validated_data

# API Documentation
class Post9APIDocumentation:
    """Complete API documentation for Post9"""
    
    @staticmethod
    def get_model_endpoints() -> List[APIEndpoint]:
        """ML Model management endpoints"""
        return [
            APIEndpoint(
                path="/api/models/gallery",
                method="GET",
                description="Get list of available ML models with filtering",
                request_fields=[
                    APIField("sport", FieldType.STRING, allowed_values=["NBA", "NFL", "MLB", "all"], description="Filter by sport"),
                    APIField("type", FieldType.STRING, allowed_values=["statistical", "neural", "ensemble", "all"], description="Filter by model type"),
                    APIField("page", FieldType.INTEGER, min_value=1, description="Page number for pagination"),
                    APIField("per_page", FieldType.INTEGER, min_value=1, max_value=100, description="Items per page")
                ],
                response_fields=[
                    APIField("success", FieldType.BOOLEAN, required=True),
                    APIField("models", FieldType.ARRAY, required=True),
                    APIField("total_count", FieldType.INTEGER, required=True)
                ],
                tags=["models"],
                example_request={"sport": "NBA", "type": "statistical"},
                example_response={
                    "success": True,
                    "models": [{"id": "nba_model_1", "name": "NBA Predictor", "accuracy": 68.2}],
                    "total_count": 1
                }
            ),
            APIEndpoint(
                path="/api/models/create",
                method="POST",
                description="Create a new ML model",
                request_fields=[
                    APIField("sport", FieldType.STRING, required=True, allowed_values=["NBA", "NFL", "MLB"]),
                    APIField("model_type", FieldType.STRING, required=True, allowed_values=["statistical", "neural", "ensemble"]),
                    APIField("description", FieldType.STRING, max_length=500),
                    APIField("user_id", FieldType.STRING, required=True, min_length=1)
                ],
                response_fields=[
                    APIField("success", FieldType.BOOLEAN, required=True),
                    APIField("model_id", FieldType.STRING, required=True),
                    APIField("message", FieldType.STRING, required=True)
                ],
                tags=["models"],
                example_request={
                    "sport": "NBA",
                    "model_type": "statistical", 
                    "description": "Custom NBA predictor",
                    "user_id": "user123"
                }
            ),
            APIEndpoint(
                path="/api/ml/basic/train",
                method="POST", 
                description="Train a basic statistical model",
                request_fields=[
                    APIField("sport", FieldType.STRING, required=True, allowed_values=["NBA", "NFL", "MLB"]),
                    APIField("num_samples", FieldType.INTEGER, min_value=100, max_value=10000),
                    APIField("model_type", FieldType.STRING, allowed_values=["statistical"])
                ],
                response_fields=[
                    APIField("success", FieldType.BOOLEAN, required=True),
                    APIField("training_results", FieldType.OBJECT, required=True),
                    APIField("model_type", FieldType.STRING, required=True)
                ],
                tags=["training"],
                example_request={"sport": "NBA", "num_samples": 1000}
            )
        ]
    
    @staticmethod
    def get_strategy_endpoints() -> List[APIEndpoint]:
        """Strategy management endpoints"""
        return [
            APIEndpoint(
                path="/api/strategies",
                method="POST",
                description="Create a new betting strategy",
                request_fields=[
                    APIField("user_id", FieldType.STRING, required=True, min_length=1),
                    APIField("name", FieldType.STRING, required=True, min_length=1, max_length=100),
                    APIField("type", FieldType.STRING, required=True, allowed_values=["basic", "expected_value", "conservative", "aggressive", "model_based"]),
                    APIField("description", FieldType.STRING, max_length=500),
                    APIField("parameters", FieldType.OBJECT)
                ],
                response_fields=[
                    APIField("success", FieldType.BOOLEAN, required=True),
                    APIField("strategy_id", FieldType.STRING, required=True),
                    APIField("message", FieldType.STRING, required=True)
                ],
                tags=["strategies"]
            ),
            APIEndpoint(
                path="/api/strategies/model-based",
                method="POST",
                description="Create a strategy powered by ML model",
                request_fields=[
                    APIField("user_id", FieldType.STRING, required=True, min_length=1),
                    APIField("model_id", FieldType.STRING, required=True, min_length=1),
                    APIField("name", FieldType.STRING, required=True, min_length=1, max_length=100),
                    APIField("confidence_threshold", FieldType.FLOAT, min_value=0.0, max_value=1.0),
                    APIField("max_bet_percentage", FieldType.FLOAT, min_value=0.1, max_value=10.0)
                ],
                response_fields=[
                    APIField("success", FieldType.BOOLEAN, required=True),
                    APIField("strategy_id", FieldType.STRING, required=True),
                    APIField("message", FieldType.STRING, required=True)
                ],
                tags=["strategies", "models"]
            )
        ]
    
    @staticmethod
    def get_analytics_endpoints() -> List[APIEndpoint]:
        """Analytics endpoints"""
        return [
            APIEndpoint(
                path="/api/analytics/kelly",
                method="POST",
                description="Calculate Kelly Criterion for optimal bet sizing",
                request_fields=[
                    APIField("win_probability", FieldType.FLOAT, required=True, min_value=0.0, max_value=1.0),
                    APIField("odds", FieldType.FLOAT, required=True, min_value=1.0),
                    APIField("bankroll", FieldType.FLOAT, required=True, min_value=1.0)
                ],
                response_fields=[
                    APIField("success", FieldType.BOOLEAN, required=True),
                    APIField("kelly_analysis", FieldType.OBJECT, required=True)
                ],
                tags=["analytics"],
                example_request={
                    "win_probability": 0.58,
                    "odds": 1.85,
                    "bankroll": 1000
                }
            )
        ]
    
    @staticmethod
    def get_all_endpoints() -> List[APIEndpoint]:
        """Get all API endpoints"""
        return (
            Post9APIDocumentation.get_model_endpoints() +
            Post9APIDocumentation.get_strategy_endpoints() +
            Post9APIDocumentation.get_analytics_endpoints()
        )
    
    @staticmethod
    def generate_openapi_spec() -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification"""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Post9 Sports Investment API",
                "version": "1.0.0",
                "description": "Professional sports investment platform with ML-powered predictions"
            },
            "paths": {}
        }
        
        for endpoint in Post9APIDocumentation.get_all_endpoints():
            path_key = endpoint.path
            if path_key not in spec["paths"]:
                spec["paths"][path_key] = {}
            
            method_key = endpoint.method.lower()
            spec["paths"][path_key][method_key] = {
                "summary": endpoint.description,
                "tags": endpoint.tags or [],
                "parameters": [],
                "responses": {
                    "200": {"description": "Success"},
                    "400": {"description": "Validation Error"},
                    "500": {"description": "Internal Server Error"}
                }
            }
            
            # Add request body for POST endpoints
            if endpoint.method.upper() == "POST" and endpoint.request_fields:
                spec["paths"][path_key][method_key]["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    }
                }
                
                properties = spec["paths"][path_key][method_key]["requestBody"]["content"]["application/json"]["schema"]["properties"]
                required = spec["paths"][path_key][method_key]["requestBody"]["content"]["application/json"]["schema"]["required"]
                
                for field in endpoint.request_fields:
                    properties[field.name] = {
                        "type": field.field_type.value,
                        "description": field.description
                    }
                    if field.required:
                        required.append(field.name)
        
        return spec

def validate_endpoint_request(endpoint_path: str, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate request data against endpoint specification"""
    endpoints = Post9APIDocumentation.get_all_endpoints()
    
    # Find matching endpoint
    matching_endpoint = None
    for endpoint in endpoints:
        if endpoint.path == endpoint_path and endpoint.method.upper() == method.upper():
            matching_endpoint = endpoint
            break
    
    if not matching_endpoint:
        raise ValidationError(f"Endpoint not found: {method} {endpoint_path}")
    
    return APIValidator.validate_request(data, matching_endpoint.request_fields)