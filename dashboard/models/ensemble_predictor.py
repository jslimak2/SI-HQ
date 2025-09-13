"""
Ensemble Model System for Sports Prediction
Combines multiple ML approaches for superior accuracy
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import xgboost as xgb
import lightgbm as lgb
import joblib
import json
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

from neural_predictor import SportsNeuralPredictor, generate_demo_training_data


class SportsEnsemblePredictor:
    """Advanced ensemble predictor combining multiple ML approaches"""
    
    def __init__(self, sport: str = 'NBA', use_neural: bool = True):
        self.sport = sport.upper()
        self.use_neural = use_neural
        self.models = {}
        self.ensemble_model = None
        self.neural_predictor = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = []
        self.is_trained = False
        
        # Initialize neural network if requested
        if self.use_neural:
            self.neural_predictor = SportsNeuralPredictor(model_type='lstm', sport=sport)
    
    def create_base_models(self) -> Dict:
        """Create base models for ensemble"""
        models = {
            'random_forest': RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1
            ),
            'gradient_boost': GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            ),
            'xgboost': xgb.XGBClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42,
                eval_metric='logloss'
            ),
            'lightgbm': lgb.LGBMClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42,
                verbose=-1
            ),
            'logistic_regression': LogisticRegression(
                random_state=42,
                max_iter=1000
            ),
            'svm': SVC(
                probability=True,
                random_state=42
            )
        }
        
        return models
    
    def optimize_hyperparameters(self, X_train: np.ndarray, y_train: np.ndarray) -> Dict:
        """Optimize hyperparameters for each model"""
        optimized_models = {}
        
        # Random Forest optimization
        rf_params = {
            'n_estimators': [50, 100, 200],
            'max_depth': [5, 10, 15, None],
            'min_samples_split': [2, 5, 10]
        }
        
        rf_grid = GridSearchCV(
            RandomForestClassifier(random_state=42, n_jobs=-1),
            rf_params,
            cv=3,
            scoring='accuracy',
            n_jobs=-1
        )
        rf_grid.fit(X_train, y_train)
        optimized_models['random_forest'] = rf_grid.best_estimator_
        
        # XGBoost optimization
        xgb_params = {
            'n_estimators': [50, 100, 200],
            'learning_rate': [0.05, 0.1, 0.2],
            'max_depth': [3, 6, 9]
        }
        
        xgb_grid = GridSearchCV(
            xgb.XGBClassifier(random_state=42, eval_metric='logloss'),
            xgb_params,
            cv=3,
            scoring='accuracy',
            n_jobs=-1
        )
        xgb_grid.fit(X_train, y_train)
        optimized_models['xgboost'] = xgb_grid.best_estimator_
        
        # Add other models with default parameters
        optimized_models['gradient_boost'] = GradientBoostingClassifier(
            n_estimators=100, learning_rate=0.1, max_depth=6, random_state=42
        )
        optimized_models['lightgbm'] = lgb.LGBMClassifier(
            n_estimators=100, learning_rate=0.1, max_depth=6, random_state=42, verbose=-1
        )
        optimized_models['logistic_regression'] = LogisticRegression(
            random_state=42, max_iter=1000
        )
        
        return optimized_models
    
    def prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """Prepare features for ensemble models"""
        features = []
        
        if self.sport == 'NBA':
            feature_columns = [
                'home_team_ppg', 'away_team_ppg', 'home_win_pct', 'away_win_pct',
                'home_pace', 'away_pace', 'home_def_rating', 'away_def_rating',
                'home_eff_fg_pct', 'away_eff_fg_pct', 'home_turnovers', 'away_turnovers'
            ]
        elif self.sport == 'NFL':
            feature_columns = [
                'home_team_off_yards', 'away_team_off_yards', 'home_team_def_yards',
                'away_team_def_yards', 'home_win_pct', 'away_win_pct', 'weather_score'
            ]
        else:
            feature_columns = [
                'home_win_pct', 'away_win_pct', 'home_score_avg', 'away_score_avg'
            ]
        
        # Add available features from data
        available_features = [col for col in feature_columns if col in data.columns]
        if not available_features:
            # Generate synthetic features for demo
            available_features = self._generate_synthetic_features(data)
        
        self.feature_names = available_features
        return data[available_features].values
    
    def _generate_synthetic_features(self, data: pd.DataFrame) -> List[str]:
        """Generate synthetic features for demonstration"""
        np.random.seed(42)
        
        if self.sport == 'NBA':
            data['home_team_ppg'] = np.random.normal(110, 8, len(data))
            data['away_team_ppg'] = np.random.normal(108, 8, len(data))
            data['home_win_pct'] = np.random.beta(2, 2, len(data))
            data['away_win_pct'] = np.random.beta(2, 2, len(data))
            data['home_pace'] = np.random.normal(100, 5, len(data))
            data['away_pace'] = np.random.normal(98, 5, len(data))
            
            return ['home_team_ppg', 'away_team_ppg', 'home_win_pct', 
                   'away_win_pct', 'home_pace', 'away_pace']
        
        elif self.sport == 'NFL':
            data['home_team_off_yards'] = np.random.normal(350, 40, len(data))
            data['away_team_off_yards'] = np.random.normal(340, 40, len(data))
            data['home_win_pct'] = np.random.beta(2, 2, len(data))
            data['away_win_pct'] = np.random.beta(2, 2, len(data))
            data['weather_score'] = np.random.uniform(0, 1, len(data))
            
            return ['home_team_off_yards', 'away_team_off_yards', 
                   'home_win_pct', 'away_win_pct', 'weather_score']
        
        else:
            data['home_win_pct'] = np.random.beta(2, 2, len(data))
            data['away_win_pct'] = np.random.beta(2, 2, len(data))
            data['home_score_avg'] = np.random.normal(100, 12, len(data))
            data['away_score_avg'] = np.random.normal(98, 12, len(data))
            
            return ['home_win_pct', 'away_win_pct', 'home_score_avg', 'away_score_avg']
    
    def train_ensemble(self, data: pd.DataFrame, target_column: str = 'outcome',
                      optimize_hyperparams: bool = True, test_size: float = 0.2):
        """Train the ensemble model"""
        # Prepare features
        X = self.prepare_features(data)
        
        # Handle target variable
        if target_column not in data.columns:
            # Generate synthetic targets for demo
            if self.sport == 'NBA':
                y = np.random.choice(['Home Win', 'Away Win', 'Close Game'], 
                                   size=len(data), p=[0.45, 0.45, 0.1])
            else:
                y = np.random.choice(['Home Win', 'Away Win'], 
                                   size=len(data), p=[0.52, 0.48])
        else:
            y = data[target_column]
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_encoded, test_size=test_size, random_state=42, stratify=y_encoded
        )
        
        # Create and train base models
        if optimize_hyperparams:
            print("Optimizing hyperparameters...")
            self.models = self.optimize_hyperparameters(X_train, y_train)
        else:
            self.models = self.create_base_models()
        
        # Train each model
        print("Training base models...")
        model_scores = {}
        
        for name, model in self.models.items():
            print(f"Training {name}...")
            model.fit(X_train, y_train)
            
            # Cross-validation score
            cv_scores = cross_val_score(model, X_train, y_train, cv=5)
            model_scores[name] = {
                'cv_mean': np.mean(cv_scores),
                'cv_std': np.std(cv_scores),
                'test_score': model.score(X_test, y_test)
            }
        
        # Train neural network if enabled
        if self.use_neural and self.neural_predictor:
            print("Training neural network...")
            neural_data = data.copy()
            # Ensure neural predictor gets the same features
            for feature in self.feature_names:
                if feature not in neural_data.columns:
                    neural_data[feature] = X[:, self.feature_names.index(feature)]
            
            neural_results = self.neural_predictor.train_model(neural_data, target_column, epochs=20)
            model_scores['neural_network'] = {
                'cv_mean': neural_results['test_accuracy'],
                'cv_std': 0.0,  # Not available for neural networks
                'test_score': neural_results['test_accuracy']
            }
        
        # Create ensemble using voting classifier
        ensemble_models = [(name, model) for name, model in self.models.items()]
        
        self.ensemble_model = VotingClassifier(
            estimators=ensemble_models,
            voting='soft',  # Use probabilities
            n_jobs=-1
        )
        
        print("Training ensemble...")
        self.ensemble_model.fit(X_train, y_train)
        
        # Evaluate ensemble
        ensemble_score = self.ensemble_model.score(X_test, y_test)
        y_pred = self.ensemble_model.predict(X_test)
        
        # Generate detailed evaluation
        evaluation_results = {
            'ensemble_accuracy': float(ensemble_score),
            'individual_model_scores': model_scores,
            'classification_report': classification_report(
                y_test, y_pred, 
                target_names=self.label_encoder.classes_,
                output_dict=True
            ),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
        }
        
        # ROC AUC for binary classification
        if len(self.label_encoder.classes_) == 2:
            y_proba = self.ensemble_model.predict_proba(X_test)[:, 1]
            evaluation_results['roc_auc'] = float(roc_auc_score(y_test, y_proba))
        
        self.is_trained = True
        
        return evaluation_results
    
    def predict_game(self, game_data: Dict) -> Dict:
        """Predict outcome for a single game using ensemble"""
        if not self.is_trained:
            return {'error': 'Model not trained yet'}
        
        # Convert to DataFrame
        df = pd.DataFrame([game_data])
        
        # Prepare features
        X = self.prepare_features(df)
        X_scaled = self.scaler.transform(X)
        
        # Get ensemble prediction
        ensemble_proba = self.ensemble_model.predict_proba(X_scaled)[0]
        ensemble_pred = self.ensemble_model.predict(X_scaled)[0]
        
        # Get individual model predictions
        individual_predictions = {}
        for name, model in self.models.items():
            try:
                pred_proba = model.predict_proba(X_scaled)[0]
                individual_predictions[name] = {
                    'probabilities': pred_proba.tolist(),
                    'predicted_class': int(model.predict(X_scaled)[0])
                }
            except:
                pass  # Skip models that might have issues
        
        # Get neural network prediction if available
        if self.use_neural and self.neural_predictor and self.neural_predictor.is_trained:
            try:
                neural_pred = self.neural_predictor.predict_game(game_data)
                if 'error' not in neural_pred:
                    individual_predictions['neural_network'] = neural_pred
            except:
                pass
        
        # Map prediction back to label
        predicted_label = self.label_encoder.inverse_transform([ensemble_pred])[0]
        confidence = float(np.max(ensemble_proba))
        
        return {
            'ensemble_prediction': predicted_label,
            'confidence': confidence,
            'ensemble_probabilities': {
                label: float(prob) 
                for label, prob in zip(self.label_encoder.classes_, ensemble_proba)
            },
            'individual_predictions': individual_predictions,
            'sport': self.sport,
            'model_type': 'ensemble'
        }
    
    def get_feature_importance_ensemble(self) -> Dict:
        """Get feature importance from ensemble models"""
        if not self.is_trained:
            return {'error': 'Model not trained yet'}
        
        importance_scores = {}
        
        # Get importance from tree-based models
        tree_models = ['random_forest', 'gradient_boost', 'xgboost', 'lightgbm']
        
        for model_name in tree_models:
            if model_name in self.models:
                model = self.models[model_name]
                if hasattr(model, 'feature_importances_'):
                    importance_scores[model_name] = model.feature_importances_
        
        # Average importance across tree models
        if importance_scores:
            avg_importance = np.mean(list(importance_scores.values()), axis=0)
        else:
            # Fallback to random importance for demo
            avg_importance = np.random.dirichlet(np.ones(len(self.feature_names)))
        
        # Get neural network importance if available
        neural_importance = None
        if self.use_neural and self.neural_predictor and self.neural_predictor.is_trained:
            try:
                neural_imp = self.neural_predictor.get_feature_importance()
                if 'error' not in neural_imp:
                    neural_importance = neural_imp
            except:
                pass
        
        return {
            'ensemble_feature_importance': {
                name: float(score) 
                for name, score in zip(self.feature_names, avg_importance)
            },
            'individual_model_importance': {
                name: scores.tolist() 
                for name, scores in importance_scores.items()
            },
            'neural_importance': neural_importance,
            'top_features': sorted(
                zip(self.feature_names, avg_importance),
                key=lambda x: x[1], reverse=True
            )[:5]
        }
    
    def compare_models(self, test_data: pd.DataFrame = None) -> Dict:
        """Compare performance of different models in the ensemble"""
        if not self.is_trained:
            return {'error': 'Model not trained yet'}
        
        if test_data is None:
            # Generate test data
            test_data = generate_demo_training_data(self.sport, 100)
        
        X_test = self.prepare_features(test_data)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Handle target
        if 'outcome' in test_data.columns:
            y_true = self.label_encoder.transform(test_data['outcome'])
        else:
            # Generate synthetic targets
            y_true = np.random.choice(range(len(self.label_encoder.classes_)), size=len(test_data))
        
        comparison_results = {}
        
        # Compare individual models
        for name, model in self.models.items():
            try:
                accuracy = model.score(X_test_scaled, y_true)
                y_pred = model.predict(X_test_scaled)
                
                comparison_results[name] = {
                    'accuracy': float(accuracy),
                    'precision': float(np.mean([
                        np.sum((y_pred == i) & (y_true == i)) / np.sum(y_pred == i) if np.sum(y_pred == i) > 0 else 0
                        for i in range(len(self.label_encoder.classes_))
                    ])),
                    'recall': float(np.mean([
                        np.sum((y_pred == i) & (y_true == i)) / np.sum(y_true == i) if np.sum(y_true == i) > 0 else 0
                        for i in range(len(self.label_encoder.classes_))
                    ]))
                }
            except:
                comparison_results[name] = {'error': 'Failed to evaluate model'}
        
        # Ensemble performance
        try:
            ensemble_accuracy = self.ensemble_model.score(X_test_scaled, y_true)
            y_ensemble_pred = self.ensemble_model.predict(X_test_scaled)
            
            comparison_results['ensemble'] = {
                'accuracy': float(ensemble_accuracy),
                'precision': float(np.mean([
                    np.sum((y_ensemble_pred == i) & (y_true == i)) / np.sum(y_ensemble_pred == i) 
                    if np.sum(y_ensemble_pred == i) > 0 else 0
                    for i in range(len(self.label_encoder.classes_))
                ])),
                'recall': float(np.mean([
                    np.sum((y_ensemble_pred == i) & (y_true == i)) / np.sum(y_true == i) 
                    if np.sum(y_true == i) > 0 else 0
                    for i in range(len(self.label_encoder.classes_))
                ]))
            }
        except:
            comparison_results['ensemble'] = {'error': 'Failed to evaluate ensemble'}
        
        return comparison_results
    
    def save_ensemble(self, filepath: str):
        """Save the entire ensemble system"""
        if not self.is_trained:
            raise ValueError("Ensemble not trained yet")
        
        # Save ensemble model
        ensemble_path = f"{filepath}_ensemble.joblib"
        joblib.dump(self.ensemble_model, ensemble_path)
        
        # Save individual models
        models_path = f"{filepath}_models.joblib"
        joblib.dump(self.models, models_path)
        
        # Save preprocessors
        scaler_path = f"{filepath}_scaler.joblib"
        joblib.dump(self.scaler, scaler_path)
        
        encoder_path = f"{filepath}_encoder.joblib"
        joblib.dump(self.label_encoder, encoder_path)
        
        # Save neural network if exists
        neural_paths = None
        if self.use_neural and self.neural_predictor and self.neural_predictor.is_trained:
            neural_paths = self.neural_predictor.save_model(f"{filepath}_neural")
        
        # Save metadata
        metadata = {
            'sport': self.sport,
            'use_neural': self.use_neural,
            'feature_names': self.feature_names,
            'is_trained': self.is_trained,
            'label_classes': self.label_encoder.classes_.tolist()
        }
        
        metadata_path = f"{filepath}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        
        return {
            'ensemble_path': ensemble_path,
            'models_path': models_path,
            'scaler_path': scaler_path,
            'encoder_path': encoder_path,
            'neural_paths': neural_paths,
            'metadata_path': metadata_path
        }
    
    def load_ensemble(self, filepath: str):
        """Load the entire ensemble system"""
        try:
            # Load metadata
            metadata_path = f"{filepath}_metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Load models
            ensemble_path = f"{filepath}_ensemble.joblib"
            self.ensemble_model = joblib.load(ensemble_path)
            
            models_path = f"{filepath}_models.joblib"
            self.models = joblib.load(models_path)
            
            # Load preprocessors
            scaler_path = f"{filepath}_scaler.joblib"
            self.scaler = joblib.load(scaler_path)
            
            encoder_path = f"{filepath}_encoder.joblib"
            self.label_encoder = joblib.load(encoder_path)
            
            # Restore metadata
            self.sport = metadata['sport']
            self.use_neural = metadata['use_neural']
            self.feature_names = metadata['feature_names']
            self.is_trained = metadata['is_trained']
            
            # Load neural network if exists
            if self.use_neural:
                self.neural_predictor = SportsNeuralPredictor(sport=self.sport)
                try:
                    self.neural_predictor.load_model(f"{filepath}_neural")
                except:
                    print("Neural network model not found or failed to load")
                    self.neural_predictor = None
            
            return True
        except Exception as e:
            print(f"Error loading ensemble: {e}")
            return False


if __name__ == "__main__":
    # Demo usage
    print("Creating NBA Ensemble Predictor...")
    
    # Generate demo data
    demo_data = generate_demo_training_data('NBA', 1000)
    print(f"Generated {len(demo_data)} demo games for training")
    
    # Create ensemble predictor
    ensemble = SportsEnsemblePredictor(sport='NBA', use_neural=True)
    
    # Train ensemble
    print("Training ensemble models...")
    results = ensemble.train_ensemble(demo_data, optimize_hyperparams=False)  # Skip optimization for demo speed
    
    print(f"\nEnsemble Training Results:")
    print(f"Ensemble Accuracy: {results['ensemble_accuracy']:.3f}")
    print("\nIndividual Model Scores:")
    for model_name, scores in results['individual_model_scores'].items():
        print(f"  {model_name}: CV={scores['cv_mean']:.3f} (+/- {scores['cv_std']:.3f}), Test={scores['test_score']:.3f}")
    
    # Test prediction
    test_game = {
        'home_team_ppg': 115,
        'away_team_ppg': 108,
        'home_win_pct': 0.7,
        'away_win_pct': 0.5,
        'home_pace': 105,
        'away_pace': 98
    }
    
    prediction = ensemble.predict_game(test_game)
    print(f"\nEnsemble prediction: {prediction['ensemble_prediction']}")
    print(f"Confidence: {prediction['confidence']:.3f}")
    
    # Feature importance
    importance = ensemble.get_feature_importance_ensemble()
    print(f"\nTop 3 important features:")
    for feature, score in importance['top_features'][:3]:
        print(f"  {feature}: {score:.3f}")
    
    # Model comparison
    comparison = ensemble.compare_models()
    print(f"\nModel Comparison:")
    for model_name, metrics in comparison.items():
        if 'error' not in metrics:
            print(f"  {model_name}: Accuracy={metrics['accuracy']:.3f}")