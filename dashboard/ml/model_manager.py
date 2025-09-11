"""
ML Model Management System
Handles training, deployment, and monitoring of ML models
"""
import os
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import threading
import time

# Try to import ML components with fallback
try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.neural_predictor import SportsNeuralPredictor, generate_demo_training_data
    from models.ensemble_predictor import SportsEnsemblePredictor
    from analytics.advanced_stats import AdvancedSportsAnalyzer
    ML_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"ML imports not available in model_manager: {e}")
    ML_IMPORTS_AVAILABLE = False


class MLModelManager:
    """Centralized ML model management system"""
    
    def __init__(self, models_dir: str = "saved_models"):
        self.models_dir = models_dir
        self.active_models = {}
        self.model_metadata = {}
        self.training_jobs = {}
        self.performance_history = {}
        
        if ML_IMPORTS_AVAILABLE:
            self.analyzer = AdvancedSportsAnalyzer()
        else:
            self.analyzer = None
            print("Warning: Advanced analytics not available")
        
        # Create models directory if it doesn't exist
        os.makedirs(models_dir, exist_ok=True)
        
        # Load existing models
        self._load_existing_models()
    
    def _load_existing_models(self):
        """Load existing trained models from disk"""
        try:
            metadata_file = os.path.join(self.models_dir, "models_metadata.json")
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    self.model_metadata = json.load(f)
                
                # Load active models
                for model_id, metadata in self.model_metadata.items():
                    if metadata.get('status') == 'active':
                        self._load_model(model_id)
        except Exception as e:
            print(f"Error loading existing models: {e}")
    
    def _load_model(self, model_id: str) -> bool:
        """Load a specific model"""
        try:
            metadata = self.model_metadata.get(model_id, {})
            model_type = metadata.get('model_type', 'ensemble')
            sport = metadata.get('sport', 'NBA')
            
            model_path = os.path.join(self.models_dir, model_id)
            
            if model_type == 'neural':
                model = SportsNeuralPredictor(
                    model_type=metadata.get('neural_type', 'lstm'), 
                    sport=sport
                )
                if model.load_model(model_path):
                    self.active_models[model_id] = model
                    return True
            else:
                model = SportsEnsemblePredictor(
                    sport=sport, 
                    use_neural=metadata.get('use_neural', True)
                )
                if model.load_ensemble(model_path):
                    self.active_models[model_id] = model
                    return True
            
            return False
        except Exception as e:
            print(f"Error loading model {model_id}: {e}")
            return False
    
    def create_model(self, model_config: Dict[str, Any]) -> str:
        """Create a new ML model"""
        model_id = f"{model_config['sport']}_{model_config['model_type']}_{int(time.time())}"
        
        try:
            if model_config['model_type'] == 'neural':
                model = SportsNeuralPredictor(
                    model_type=model_config.get('neural_type', 'lstm'),
                    sport=model_config['sport']
                )
            else:
                model = SportsEnsemblePredictor(
                    sport=model_config['sport'],
                    use_neural=model_config.get('use_neural', True)
                )
            
            # Store model metadata
            self.model_metadata[model_id] = {
                'id': model_id,
                'sport': model_config['sport'],
                'model_type': model_config['model_type'],
                'neural_type': model_config.get('neural_type', 'lstm'),
                'use_neural': model_config.get('use_neural', True),
                'created_at': datetime.now().isoformat(),
                'status': 'created',
                'description': model_config.get('description', ''),
                'training_history': [],
                'performance_metrics': {}
            }
            
            # Save metadata
            self._save_metadata()
            
            return model_id
            
        except Exception as e:
            raise Exception(f"Failed to create model: {e}")
    
    def train_model_async(self, model_id: str, training_config: Dict[str, Any]) -> str:
        """Start asynchronous model training"""
        if model_id in self.training_jobs:
            if self.training_jobs[model_id]['status'] == 'training':
                raise Exception("Model is already being trained")
        
        job_id = f"train_{model_id}_{int(time.time())}"
        
        # Initialize training job
        self.training_jobs[job_id] = {
            'model_id': model_id,
            'status': 'queued',
            'progress': 0,
            'start_time': datetime.now().isoformat(),
            'error': None,
            'logs': []
        }
        
        # Start training in background thread
        training_thread = threading.Thread(
            target=self._train_model_background,
            args=(job_id, model_id, training_config)
        )
        training_thread.daemon = True
        training_thread.start()
        
        return job_id
    
    def _train_model_background(self, job_id: str, model_id: str, training_config: Dict[str, Any]):
        """Background model training process"""
        try:
            self.training_jobs[job_id]['status'] = 'training'
            self.training_jobs[job_id]['progress'] = 10
            
            metadata = self.model_metadata[model_id]
            
            # Generate or load training data
            if 'training_data' in training_config:
                training_data = pd.DataFrame(training_config['training_data'])
            else:
                # Generate demo data
                num_samples = training_config.get('num_samples', 1000)
                training_data = generate_demo_training_data(metadata['sport'], num_samples)
            
            self.training_jobs[job_id]['progress'] = 30
            self.training_jobs[job_id]['logs'].append(f"Generated {len(training_data)} training samples")
            
            # Create model instance
            if metadata['model_type'] == 'neural':
                model = SportsNeuralPredictor(
                    model_type=metadata.get('neural_type', 'lstm'),
                    sport=metadata['sport']
                )
                
                # Train neural model
                training_results = model.train_model(
                    training_data,
                    epochs=training_config.get('epochs', 50),
                    batch_size=training_config.get('batch_size', 32)
                )
                
            else:
                model = SportsEnsemblePredictor(
                    sport=metadata['sport'],
                    use_neural=metadata.get('use_neural', True)
                )
                
                # Train ensemble model
                training_results = model.train_ensemble(
                    training_data,
                    optimize_hyperparams=training_config.get('optimize_hyperparams', True)
                )
            
            self.training_jobs[job_id]['progress'] = 80
            
            # Save trained model
            model_path = os.path.join(self.models_dir, model_id)
            if metadata['model_type'] == 'neural':
                model.save_model(model_path)
            else:
                model.save_ensemble(model_path)
            
            # Update metadata
            self.model_metadata[model_id]['status'] = 'trained'
            self.model_metadata[model_id]['trained_at'] = datetime.now().isoformat()
            self.model_metadata[model_id]['performance_metrics'] = training_results
            self.model_metadata[model_id]['training_history'].append({
                'job_id': job_id,
                'training_config': training_config,
                'results': training_results,
                'timestamp': datetime.now().isoformat()
            })
            
            # Store model in active models
            self.active_models[model_id] = model
            
            # Save metadata
            self._save_metadata()
            
            self.training_jobs[job_id]['status'] = 'completed'
            self.training_jobs[job_id]['progress'] = 100
            self.training_jobs[job_id]['end_time'] = datetime.now().isoformat()
            self.training_jobs[job_id]['logs'].append("Training completed successfully")
            
        except Exception as e:
            self.training_jobs[job_id]['status'] = 'failed'
            self.training_jobs[job_id]['error'] = str(e)
            self.training_jobs[job_id]['logs'].append(f"Training failed: {e}")
            print(f"Training failed for model {model_id}: {e}")
    
    def get_training_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of training job"""
        if job_id not in self.training_jobs:
            return {'error': 'Job not found'}
        
        return self.training_jobs[job_id]
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get detailed information about a model"""
        if model_id not in self.model_metadata:
            return {'error': 'Model not found'}
        
        metadata = self.model_metadata[model_id].copy()
        
        # Add runtime information
        metadata['is_loaded'] = model_id in self.active_models
        metadata['last_prediction'] = self.performance_history.get(model_id, {}).get('last_prediction')
        
        return metadata
    
    def list_models(self, sport: str = None, status: str = None) -> List[Dict[str, Any]]:
        """List available models with optional filtering"""
        models = []
        
        for model_id, metadata in self.model_metadata.items():
            if sport and metadata.get('sport') != sport.upper():
                continue
            if status and metadata.get('status') != status:
                continue
            
            model_info = metadata.copy()
            model_info['is_loaded'] = model_id in self.active_models
            models.append(model_info)
        
        return models
    
    def predict_game(self, model_id: str, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make prediction using specified model"""
        if model_id not in self.active_models:
            # Try to load the model
            if not self._load_model(model_id):
                return {'error': 'Model not available'}
        
        try:
            model = self.active_models[model_id]
            prediction = model.predict_game(game_data)
            
            # Log prediction for performance tracking
            if model_id not in self.performance_history:
                self.performance_history[model_id] = {
                    'predictions': [],
                    'last_prediction': datetime.now().isoformat()
                }
            
            self.performance_history[model_id]['predictions'].append({
                'game_data': game_data,
                'prediction': prediction,
                'timestamp': datetime.now().isoformat()
            })
            self.performance_history[model_id]['last_prediction'] = datetime.now().isoformat()
            
            # Keep only last 100 predictions
            if len(self.performance_history[model_id]['predictions']) > 100:
                self.performance_history[model_id]['predictions'] = \
                    self.performance_history[model_id]['predictions'][-100:]
            
            return prediction
            
        except Exception as e:
            return {'error': f'Prediction failed: {e}'}
    
    def get_model_performance(self, model_id: str) -> Dict[str, Any]:
        """Get model performance metrics and history"""
        if model_id not in self.model_metadata:
            return {'error': 'Model not found'}
        
        metadata = self.model_metadata[model_id]
        performance_data = self.performance_history.get(model_id, {})
        
        # Calculate recent performance metrics
        recent_predictions = performance_data.get('predictions', [])[-50:]  # Last 50 predictions
        
        if recent_predictions:
            # This would be enhanced with actual outcome data in production
            confidence_scores = [p['prediction'].get('confidence', 0) for p in recent_predictions]
            avg_confidence = np.mean(confidence_scores)
            
            performance_metrics = {
                'recent_predictions_count': len(recent_predictions),
                'average_confidence': avg_confidence,
                'prediction_frequency': len(recent_predictions) / max(1, 
                    (datetime.now() - datetime.fromisoformat(recent_predictions[0]['timestamp'])).days
                ) if recent_predictions else 0
            }
        else:
            performance_metrics = {
                'recent_predictions_count': 0,
                'average_confidence': 0,
                'prediction_frequency': 0
            }
        
        return {
            'model_id': model_id,
            'training_metrics': metadata.get('performance_metrics', {}),
            'runtime_metrics': performance_metrics,
            'training_history': metadata.get('training_history', []),
            'status': metadata.get('status', 'unknown')
        }
    
    def delete_model(self, model_id: str) -> bool:
        """Delete a model and its associated files"""
        try:
            # Remove from active models
            if model_id in self.active_models:
                del self.active_models[model_id]
            
            # Remove files
            model_path = os.path.join(self.models_dir, model_id)
            if os.path.exists(model_path):
                import shutil
                if os.path.isdir(model_path):
                    shutil.rmtree(model_path)
                else:
                    os.remove(model_path)
            
            # Remove metadata
            if model_id in self.model_metadata:
                del self.model_metadata[model_id]
            
            # Remove performance history
            if model_id in self.performance_history:
                del self.performance_history[model_id]
            
            # Save updated metadata
            self._save_metadata()
            
            return True
            
        except Exception as e:
            print(f"Error deleting model {model_id}: {e}")
            return False
    
    def get_feature_importance(self, model_id: str) -> Dict[str, Any]:
        """Get feature importance for a model"""
        if model_id not in self.active_models:
            if not self._load_model(model_id):
                return {'error': 'Model not available'}
        
        try:
            model = self.active_models[model_id]
            
            if hasattr(model, 'get_feature_importance_ensemble'):
                return model.get_feature_importance_ensemble()
            elif hasattr(model, 'get_feature_importance'):
                return model.get_feature_importance()
            else:
                return {'error': 'Feature importance not available for this model type'}
                
        except Exception as e:
            return {'error': f'Failed to get feature importance: {e}'}
    
    def compare_models(self, model_ids: List[str], test_games: List[Dict] = None) -> Dict[str, Any]:
        """Compare performance of multiple models"""
        if not model_ids:
            return {'error': 'No models specified'}
        
        comparison_results = {}
        
        for model_id in model_ids:
            if model_id not in self.active_models:
                if not self._load_model(model_id):
                    comparison_results[model_id] = {'error': 'Model not available'}
                    continue
            
            try:
                model = self.active_models[model_id]
                metadata = self.model_metadata[model_id]
                
                # Get training metrics
                training_metrics = metadata.get('performance_metrics', {})
                
                # Test on sample games if provided
                test_results = {}
                if test_games:
                    predictions = []
                    confidences = []
                    
                    for game in test_games:
                        pred = model.predict_game(game)
                        if 'error' not in pred:
                            predictions.append(pred)
                            confidences.append(pred.get('confidence', 0))
                    
                    test_results = {
                        'test_predictions': len(predictions),
                        'average_confidence': np.mean(confidences) if confidences else 0,
                        'confidence_std': np.std(confidences) if confidences else 0
                    }
                
                comparison_results[model_id] = {
                    'model_info': {
                        'sport': metadata.get('sport'),
                        'model_type': metadata.get('model_type'),
                        'created_at': metadata.get('created_at'),
                        'status': metadata.get('status')
                    },
                    'training_metrics': training_metrics,
                    'test_results': test_results
                }
                
            except Exception as e:
                comparison_results[model_id] = {'error': f'Comparison failed: {e}'}
        
        # Add summary statistics
        successful_models = [k for k, v in comparison_results.items() if 'error' not in v]
        
        if successful_models and test_games:
            confidences = []
            for model_id in successful_models:
                avg_conf = comparison_results[model_id]['test_results'].get('average_confidence', 0)
                if avg_conf > 0:
                    confidences.append(avg_conf)
            
            summary = {
                'models_compared': len(model_ids),
                'successful_comparisons': len(successful_models),
                'average_confidence_range': {
                    'min': min(confidences) if confidences else 0,
                    'max': max(confidences) if confidences else 0,
                    'mean': np.mean(confidences) if confidences else 0
                }
            }
        else:
            summary = {
                'models_compared': len(model_ids),
                'successful_comparisons': len(successful_models)
            }
        
        return {
            'comparison_results': comparison_results,
            'summary': summary
        }
    
    def _save_metadata(self):
        """Save model metadata to disk"""
        try:
            metadata_file = os.path.join(self.models_dir, "models_metadata.json")
            with open(metadata_file, 'w') as f:
                json.dump(self.model_metadata, f, indent=2)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def get_model_recommendations(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get recommendations from multiple models for a game"""
        sport = game_data.get('sport', 'NBA').upper()
        
        # Find relevant models for this sport
        relevant_models = [
            model_id for model_id, metadata in self.model_metadata.items()
            if metadata.get('sport') == sport and metadata.get('status') == 'trained'
        ]
        
        if not relevant_models:
            return {
                'sport': sport,
                'recommendations': [],
                'message': f'No trained models available for {sport}'
            }
        
        recommendations = {}
        successful_predictions = 0
        
        for model_id in relevant_models:
            try:
                prediction = self.predict_game(model_id, game_data)
                
                if 'error' not in prediction:
                    recommendations[model_id] = {
                        'model_info': {
                            'id': model_id,
                            'type': self.model_metadata[model_id].get('model_type'),
                            'description': self.model_metadata[model_id].get('description', '')
                        },
                        'prediction': prediction
                    }
                    successful_predictions += 1
                
            except Exception as e:
                print(f"Error getting recommendation from model {model_id}: {e}")
        
        # Calculate consensus if multiple models agree
        consensus = self._calculate_consensus(recommendations)
        
        return {
            'sport': sport,
            'game_data': game_data,
            'recommendations': recommendations,
            'consensus': consensus,
            'models_consulted': len(relevant_models),
            'successful_predictions': successful_predictions
        }
    
    def _calculate_consensus(self, recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate consensus prediction from multiple models"""
        if not recommendations:
            return {}
        
        predictions = []
        confidences = []
        model_types = []
        
        for model_id, rec in recommendations.items():
            pred = rec['prediction']
            if 'ensemble_prediction' in pred:
                predictions.append(pred['ensemble_prediction'])
            elif 'predicted_outcome' in pred:
                predictions.append(pred['predicted_outcome'])
            
            confidences.append(pred.get('confidence', 0))
            model_types.append(rec['model_info']['type'])
        
        if not predictions:
            return {}
        
        # Find most common prediction
        from collections import Counter
        prediction_counts = Counter(predictions)
        consensus_prediction = prediction_counts.most_common(1)[0][0]
        consensus_count = prediction_counts[consensus_prediction]
        
        # Calculate average confidence for consensus prediction
        consensus_confidences = [
            conf for pred, conf in zip(predictions, confidences)
            if pred == consensus_prediction
        ]
        
        return {
            'prediction': consensus_prediction,
            'agreement_ratio': consensus_count / len(predictions),
            'average_confidence': np.mean(consensus_confidences) if consensus_confidences else 0,
            'model_count': len(predictions),
            'consensus_models': consensus_count,
            'model_types_agreeing': list(set([
                mt for pred, mt in zip(predictions, model_types)
                if pred == consensus_prediction
            ]))
        }


# Global model manager instance
model_manager = MLModelManager()