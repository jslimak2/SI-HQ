"""
Professional model versioning and registry system for Post9
"""
import json
import os
import pickle
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

# Import the new standardized schemas
from schemas import (
    ModelSchema, ModelStatus, Sport, MarketType, PerformanceMetrics, 
    ModelInputOutput, SchemaValidator, migrate_legacy_model
)

logger = logging.getLogger(__name__)

# Keep legacy ModelMetadata for backward compatibility during migration
@dataclass
class LegacyModelMetadata:
    model_id: str
    name: str
    sport: str
    model_type: str
    version: str
    status: ModelStatus
    created_at: str
    created_by: str
    description: str = ""
    performance_metrics: Dict[str, float] = None
    hyperparameters: Dict[str, Any] = None
    training_config: Dict[str, Any] = None
    file_path: Optional[str] = None
    file_checksum: Optional[str] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if self.hyperparameters is None:
            self.hyperparameters = {}
        if self.training_config is None:
            self.training_config = {}

# For backward compatibility
ModelMetadata = ModelSchema

class ModelRegistry:
    """Professional model registry with versioning and metadata management using standardized schemas"""
    
    def __init__(self, storage_path: str = "./models"):
        self.storage_path = storage_path
        self.metadata_file = os.path.join(storage_path, "registry.json")
        self._ensure_storage_directory()
        self._load_registry()
    
    def _ensure_storage_directory(self):
        """Create storage directory if it doesn't exist"""
        os.makedirs(self.storage_path, exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "artifacts"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "metadata"), exist_ok=True)
    
    def _load_registry(self):
        """Load model registry from disk with schema migration"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    registry_data = json.load(f)
                    
                self.models = {}
                for model_id, model_data in registry_data.items():
                    try:
                        # Try to load as new schema first
                        if 'inputs_outputs' in model_data or 'current_performance' in model_data:
                            # New schema format
                            self.models[model_id] = ModelSchema.from_dict(model_data)
                        else:
                            # Legacy format - migrate
                            logger.info(f"Migrating legacy model {model_id} to new schema")
                            self.models[model_id] = migrate_legacy_model(model_data)
                    except Exception as e:
                        logger.error(f"Failed to load model {model_id}: {e}")
                        # Fall back to creating a minimal model
                        self.models[model_id] = ModelSchema(
                            model_id=model_id,
                            name=model_data.get('name', 'Unknown'),
                            version=model_data.get('version', '1.0.0'),
                            sport=Sport(model_data.get('sport', 'NBA')),
                            model_type=model_data.get('model_type', 'unknown'),
                            created_by=model_data.get('created_by', '')
                        )
            except Exception as e:
                logger.error(f"Failed to load model registry: {e}")
                self.models = {}
        else:
            self.models = {}
    
    def _save_registry(self):
        """Save model registry to disk using new schema format"""
        try:
            registry_data = {
                model_id: model.to_dict() 
                for model_id, model in self.models.items()
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save model registry: {e}")
    
    def register_model(self, 
                      name: str,
                      sport: str, 
                      model_type: str,
                      created_by: str,
                      description: str = "",
                      hyperparameters: Dict[str, Any] = None,
                      inputs: List[str] = None,
                      outputs: List[str] = None) -> str:
        """Register a new model using the standardized schema"""
        
        # Generate model ID
        timestamp = str(int(time.time()))
        model_id = f"{sport.lower()}_{model_type}_{timestamp}"
        
        # Generate version
        version = self._generate_version(name, sport, model_type)
        
        # Create inputs/outputs structure
        inputs_outputs = ModelInputOutput(
            inputs=inputs or [],
            outputs=outputs or ['home_win_probability', 'away_win_probability', 'predicted_outcome']
        )
        
        # Create model using new schema
        model = ModelSchema(
            model_id=model_id,
            name=name,
            version=version,
            sport=Sport(sport.upper()),
            model_type=model_type,
            status=ModelStatus.TRAINING,
            created_by=created_by,
            description=description,
            hyperparameters=hyperparameters or {},
            inputs_outputs=inputs_outputs
        )
        
        # Validate the model
        validation_issues = SchemaValidator.validate_model(model)
        if validation_issues:
            raise ValueError(f"Model validation failed: {', '.join(validation_issues)}")
        
        self.models[model_id] = model
        self._save_registry()
        
        logger.info(f"Registered new model: {model_id} v{version}")
        return model_id
    
    def _generate_version(self, name: str, sport: str, model_type: str) -> str:
        """Generate semantic version for model"""
        # Find existing models with same name, sport, and type
        existing_versions = []
        for metadata in self.models.values():
            if (metadata.name == name and 
                metadata.sport == sport and 
                metadata.model_type == model_type):
                try:
                    version_parts = metadata.version.split('.')
                    if len(version_parts) == 3:
                        existing_versions.append(tuple(map(int, version_parts)))
                except ValueError:
                    continue
        
        if not existing_versions:
            return "1.0.0"
        
        # Get highest version and increment patch
        latest = max(existing_versions)
        return f"{latest[0]}.{latest[1]}.{latest[2] + 1}"
    
    def update_model_status(self, model_id: str, status: ModelStatus, performance_metrics: Dict[str, float] = None):
        """Update model status and performance metrics"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        self.models[model_id].status = status
        self.models[model_id].last_updated = datetime.now().isoformat()
        
        if performance_metrics:
            # Update current performance metrics
            for key, value in performance_metrics.items():
                if hasattr(self.models[model_id].current_performance, key):
                    setattr(self.models[model_id].current_performance, key, value)
            
            # Add to performance log
            new_performance = PerformanceMetrics()
            for key, value in performance_metrics.items():
                if hasattr(new_performance, key):
                    setattr(new_performance, key, value)
            self.models[model_id].performance_log.append(new_performance)
        
        self._save_registry()
        logger.info(f"Updated model {model_id} status to {status.value}")
    
    def save_model_artifact(self, model_id: str, model_object: Any, training_config: Dict[str, Any] = None) -> str:
        """Save model artifact to disk and update metadata"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        # Create file path
        file_path = os.path.join(self.storage_path, "artifacts", f"{model_id}.pkl")
        
        try:
            # Save model object
            with open(file_path, 'wb') as f:
                pickle.dump(model_object, f)
            
            # Calculate checksum
            checksum = self._calculate_file_checksum(file_path)
            
            # Update metadata
            self.models[model_id].file_path = file_path
            self.models[model_id].file_checksum = checksum
            self.models[model_id].last_updated = datetime.now().isoformat()
            
            if training_config:
                self.models[model_id].training_config.update(training_config)
            
            self._save_registry()
            
            logger.info(f"Saved model artifact for {model_id}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save model artifact for {model_id}: {e}")
            raise
    
    def load_model_artifact(self, model_id: str) -> Any:
        """Load model artifact from disk"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model = self.models[model_id]
        
        if not model.file_path or not os.path.exists(model.file_path):
            raise ValueError(f"Model artifact not found for {model_id}")
        
        # Verify checksum
        current_checksum = self._calculate_file_checksum(model.file_path)
        if current_checksum != model.file_checksum:
            logger.warning(f"Checksum mismatch for model {model_id}")
        
        try:
            with open(model.file_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load model artifact for {model_id}: {e}")
            raise
    
    def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def list_models(self, 
                   sport: str = None,
                   model_type: str = None, 
                   status: ModelStatus = None,
                   created_by: str = None) -> List[ModelSchema]:
        """List models with optional filtering"""
        models = list(self.models.values())
        
        if sport:
            models = [m for m in models if m.sport.value.lower() == sport.lower()]
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        if status:
            models = [m for m in models if m.status == status]
        
        if created_by:
            models = [m for m in models if m.created_by == created_by]
        
        # Sort by creation date (newest first)
        models.sort(key=lambda m: m.created_at, reverse=True)
        
        return models
    
    def get_model_metadata(self, model_id: str) -> Optional[ModelSchema]:
        """Get metadata for specific model"""
        return self.models.get(model_id)
    
    def get_latest_model(self, name: str, sport: str, model_type: str, status: ModelStatus = None) -> Optional[ModelSchema]:
        """Get latest version of a model"""
        matching_models = []
        
        for model in self.models.values():
            if (model.name == name and 
                model.sport.value == sport and 
                model.model_type == model_type):
                
                if status is None or model.status == status:
                    matching_models.append(model)
        
        if not matching_models:
            return None
        
        # Sort by version and return latest
        try:
            matching_models.sort(
                key=lambda m: tuple(map(int, m.version.split('.'))), 
                reverse=True
            )
            return matching_models[0]
        except ValueError:
            # Fallback to creation date if version parsing fails
            matching_models.sort(key=lambda m: m.created_at, reverse=True)
            return matching_models[0]
    
    def deprecate_model(self, model_id: str, reason: str = ""):
        """Mark model as deprecated"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        self.models[model_id].status = ModelStatus.DEPRECATED
        self.models[model_id].last_updated = datetime.now().isoformat()
        if reason:
            self.models[model_id].description += f" [DEPRECATED: {reason}]"
        
        self._save_registry()
        logger.info(f"Deprecated model {model_id}: {reason}")
    
    def get_model_lineage(self, model_id: str) -> List[ModelSchema]:
        """Get all versions of a model (lineage)"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        base_model = self.models[model_id]
        
        # Find all models with same name, sport, and type
        lineage = []
        for model in self.models.values():
            if (model.name == base_model.name and 
                model.sport == base_model.sport and 
                model.model_type == base_model.model_type):
                lineage.append(model)
        
        # Sort by version
        try:
            lineage.sort(key=lambda m: tuple(map(int, m.version.split('.'))))
        except ValueError:
            lineage.sort(key=lambda m: m.created_at)
        
        return lineage
    
    def cleanup_old_models(self, keep_latest_n: int = 5):
        """Clean up old model artifacts, keeping only latest N versions of each model"""
        model_groups = {}
        
        # Group models by name, sport, and type
        for model in self.models.values():
            key = (model.name, model.sport.value, model.model_type)
            if key not in model_groups:
                model_groups[key] = []
            model_groups[key].append(model)
        
        cleaned_count = 0
        
        for group in model_groups.values():
            # Sort by version/date and keep only latest N
            try:
                group.sort(key=lambda m: tuple(map(int, m.version.split('.'))), reverse=True)
            except ValueError:
                group.sort(key=lambda m: m.created_at, reverse=True)
            
            # Mark old models for cleanup
            for model in group[keep_latest_n:]:
                if model.status != ModelStatus.DEPLOYED:
                    # Remove artifact file
                    if model.file_path and os.path.exists(model.file_path):
                        try:
                            os.remove(model.file_path)
                            logger.info(f"Removed old model artifact: {model.file_path}")
                        except Exception as e:
                            logger.error(f"Failed to remove {model.file_path}: {e}")
                    
                    # Remove from registry
                    if model.model_id in self.models:
                        del self.models[model.model_id]
                        cleaned_count += 1
        
        if cleaned_count > 0:
            self._save_registry()
            logger.info(f"Cleaned up {cleaned_count} old model artifacts")
        
        return cleaned_count

# Global model registry instance
model_registry = ModelRegistry()