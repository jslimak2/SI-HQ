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
from dataclasses import dataclass, asdict
from enum import Enum
import logging
logger = logging.getLogger(__name__)

class ModelStatus(Enum):
    TRAINING = "training"
    READY = "ready"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    FAILED = "failed"

@dataclass
class ModelMetadata:
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

class ModelRegistry:
    """Professional model registry with versioning and metadata management"""
    
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
        """Load model registry from disk"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    registry_data = json.load(f)
                    self.models = {
                        model_id: ModelMetadata(**model_data) 
                        for model_id, model_data in registry_data.items()
                    }
            except Exception as e:
                logger.error(f"Failed to load model registry: {e}")
                self.models = {}
        else:
            self.models = {}
    
    def _save_registry(self):
        """Save model registry to disk"""
        try:
            registry_data = {
                model_id: asdict(metadata) 
                for model_id, metadata in self.models.items()
            }
            
            # Convert enum to string
            for model_data in registry_data.values():
                if isinstance(model_data['status'], ModelStatus):
                    model_data['status'] = model_data['status'].value
            
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
                      hyperparameters: Dict[str, Any] = None) -> str:
        """Register a new model and return model ID"""
        
        # Generate model ID
        timestamp = str(int(time.time()))
        model_id = f"{sport.lower()}_{model_type}_{timestamp}"
        
        # Generate version
        version = self._generate_version(name, sport, model_type)
        
        metadata = ModelMetadata(
            model_id=model_id,
            name=name,
            sport=sport,
            model_type=model_type,
            version=version,
            status=ModelStatus.TRAINING,
            created_at=datetime.utcnow().isoformat(),
            created_by=created_by,
            description=description,
            hyperparameters=hyperparameters or {}
        )
        
        self.models[model_id] = metadata
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
        
        if performance_metrics:
            self.models[model_id].performance_metrics.update(performance_metrics)
        
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
        
        metadata = self.models[model_id]
        
        if not metadata.file_path or not os.path.exists(metadata.file_path):
            raise ValueError(f"Model artifact not found for {model_id}")
        
        # Verify checksum
        current_checksum = self._calculate_file_checksum(metadata.file_path)
        if current_checksum != metadata.file_checksum:
            logger.warning(f"Checksum mismatch for model {model_id}")
        
        try:
            with open(metadata.file_path, 'rb') as f:
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
                   created_by: str = None) -> List[ModelMetadata]:
        """List models with optional filtering"""
        models = list(self.models.values())
        
        if sport:
            models = [m for m in models if m.sport.lower() == sport.lower()]
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        if status:
            models = [m for m in models if m.status == status]
        
        if created_by:
            models = [m for m in models if m.created_by == created_by]
        
        # Sort by creation date (newest first)
        models.sort(key=lambda m: m.created_at, reverse=True)
        
        return models
    
    def get_model_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        """Get metadata for specific model"""
        return self.models.get(model_id)
    
    def get_latest_model(self, name: str, sport: str, model_type: str, status: ModelStatus = None) -> Optional[ModelMetadata]:
        """Get latest version of a model"""
        matching_models = []
        
        for metadata in self.models.values():
            if (metadata.name == name and 
                metadata.sport == sport and 
                metadata.model_type == model_type):
                
                if status is None or metadata.status == status:
                    matching_models.append(metadata)
        
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
        if reason:
            self.models[model_id].description += f" [DEPRECATED: {reason}]"
        
        self._save_registry()
        logger.info(f"Deprecated model {model_id}: {reason}")
    
    def get_model_lineage(self, model_id: str) -> List[ModelMetadata]:
        """Get all versions of a model (lineage)"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        base_model = self.models[model_id]
        
        # Find all models with same name, sport, and type
        lineage = []
        for metadata in self.models.values():
            if (metadata.name == base_model.name and 
                metadata.sport == base_model.sport and 
                metadata.model_type == base_model.model_type):
                lineage.append(metadata)
        
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
        for metadata in self.models.values():
            key = (metadata.name, metadata.sport, metadata.model_type)
            if key not in model_groups:
                model_groups[key] = []
            model_groups[key].append(metadata)
        
        cleaned_count = 0
        
        for group in model_groups.values():
            # Sort by version/date and keep only latest N
            try:
                group.sort(key=lambda m: tuple(map(int, m.version.split('.'))), reverse=True)
            except ValueError:
                group.sort(key=lambda m: m.created_at, reverse=True)
            
            # Mark old models for cleanup
            for metadata in group[keep_latest_n:]:
                if metadata.status != ModelStatus.DEPLOYED:
                    # Remove artifact file
                    if metadata.file_path and os.path.exists(metadata.file_path):
                        try:
                            os.remove(metadata.file_path)
                            logger.info(f"Removed old model artifact: {metadata.file_path}")
                        except Exception as e:
                            logger.error(f"Failed to remove {metadata.file_path}: {e}")
                    
                    # Remove from registry
                    if metadata.model_id in self.models:
                        del self.models[metadata.model_id]
                        cleaned_count += 1
        
        if cleaned_count > 0:
            self._save_registry()
            logger.info(f"Cleaned up {cleaned_count} old model artifacts")
        
        return cleaned_count

# Global model registry instance
model_registry = ModelRegistry()