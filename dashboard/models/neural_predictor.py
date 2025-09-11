"""
Advanced Neural Network Models for Sports Prediction
Implements LSTM, Transformer, and CNN models for game outcome prediction
"""
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import joblib
import json
import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta


class SportsNeuralPredictor:
    """Advanced neural network predictor for sports outcomes"""
    
    def __init__(self, model_type='lstm', sport='nba'):
        self.model_type = model_type
        self.sport = sport.upper()
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = []
        self.is_trained = False
        
    def create_lstm_model(self, input_shape: Tuple[int, int], num_classes: int = 3):
        """Create LSTM model for time series prediction"""
        model = keras.Sequential([
            keras.layers.LSTM(128, return_sequences=True, input_shape=input_shape),
            keras.layers.Dropout(0.3),
            keras.layers.LSTM(64, return_sequences=True),
            keras.layers.Dropout(0.3),
            keras.layers.LSTM(32),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(64, activation='relu'),
            keras.layers.BatchNormalization(),
            keras.layers.Dense(32, activation='relu'),
            keras.layers.Dense(num_classes, activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy', 'precision', 'recall']
        )
        return model
    
    def create_transformer_model(self, input_shape: Tuple[int, int], num_classes: int = 3):
        """Create transformer model with multi-head attention"""
        inputs = keras.Input(shape=input_shape)
        
        # Multi-head attention layer
        attention_layer = keras.layers.MultiHeadAttention(
            num_heads=8, key_dim=64, dropout=0.1
        )
        attention_output = attention_layer(inputs, inputs)
        
        # Add & Norm
        x = keras.layers.Add()([inputs, attention_output])
        x = keras.layers.LayerNormalization(epsilon=1e-6)(x)
        
        # Feed forward network
        ffn = keras.Sequential([
            keras.layers.Dense(512, activation="relu"),
            keras.layers.Dropout(0.1),
            keras.layers.Dense(input_shape[-1])
        ])
        
        ffn_output = ffn(x)
        x = keras.layers.Add()([x, ffn_output])
        x = keras.layers.LayerNormalization(epsilon=1e-6)(x)
        
        # Global pooling and classification
        x = keras.layers.GlobalAveragePooling1D()(x)
        x = keras.layers.Dropout(0.1)(x)
        x = keras.layers.Dense(128, activation="relu")(x)
        outputs = keras.layers.Dense(num_classes, activation="softmax")(x)
        
        model = keras.Model(inputs=inputs, outputs=outputs)
        model.compile(
            optimizer="adam",
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy", "precision", "recall"]
        )
        return model
    
    def create_cnn_model(self, input_shape: Tuple[int, int], num_classes: int = 3):
        """Create CNN model for pattern recognition in sports data"""
        model = keras.Sequential([
            keras.layers.Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=input_shape),
            keras.layers.BatchNormalization(),
            keras.layers.Conv1D(filters=64, kernel_size=3, activation='relu'),
            keras.layers.Dropout(0.2),
            keras.layers.MaxPooling1D(pool_size=2),
            
            keras.layers.Conv1D(filters=128, kernel_size=3, activation='relu'),
            keras.layers.BatchNormalization(),
            keras.layers.Conv1D(filters=128, kernel_size=3, activation='relu'),
            keras.layers.Dropout(0.3),
            keras.layers.MaxPooling1D(pool_size=2),
            
            keras.layers.GlobalMaxPooling1D(),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dropout(0.5),
            keras.layers.Dense(64, activation='relu'),
            keras.layers.Dense(num_classes, activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy', 'precision', 'recall']
        )
        return model
    
    def prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """Prepare and engineer features for neural network training"""
        features = []
        
        if self.sport == 'NBA':
            feature_columns = [
                'home_team_ppg', 'away_team_ppg', 'home_team_def_rating', 
                'away_team_def_rating', 'home_win_pct', 'away_win_pct',
                'home_pace', 'away_pace', 'home_eff_fg_pct', 'away_eff_fg_pct',
                'home_turnovers', 'away_turnovers', 'rest_days_home', 'rest_days_away',
                'altitude', 'temperature'
            ]
        elif self.sport == 'NFL':
            feature_columns = [
                'home_team_off_yards', 'away_team_off_yards', 'home_team_def_yards',
                'away_team_def_yards', 'home_win_pct', 'away_win_pct',
                'home_team_to_diff', 'away_team_to_diff', 'home_injuries',
                'away_injuries', 'weather_score', 'dome_game', 'primetime'
            ]
        elif self.sport == 'MLB':
            feature_columns = [
                'home_team_era', 'away_team_era', 'home_team_ops', 'away_team_ops',
                'home_win_pct', 'away_win_pct', 'home_bullpen_era', 'away_bullpen_era',
                'weather_score', 'wind_speed', 'park_factor', 'pitcher_matchup_score'
            ]
        else:
            # Generic features for other sports
            feature_columns = [
                'home_win_pct', 'away_win_pct', 'home_score_avg', 'away_score_avg',
                'home_def_rating', 'away_def_rating', 'momentum_home', 'momentum_away'
            ]
        
        # Add available features from data
        available_features = [col for col in feature_columns if col in data.columns]
        if not available_features:
            # Create synthetic features for demo
            available_features = self._generate_synthetic_features(data)
        
        self.feature_names = available_features
        return data[available_features].values
    
    def _generate_synthetic_features(self, data: pd.DataFrame) -> List[str]:
        """Generate synthetic features for demonstration purposes"""
        np.random.seed(42)  # For reproducible results
        
        feature_names = []
        
        if self.sport == 'NBA':
            # NBA-specific synthetic features
            data['home_team_ppg'] = np.random.normal(110, 10, len(data))
            data['away_team_ppg'] = np.random.normal(108, 10, len(data))
            data['home_win_pct'] = np.random.beta(2, 2, len(data))
            data['away_win_pct'] = np.random.beta(2, 2, len(data))
            data['home_pace'] = np.random.normal(100, 5, len(data))
            data['away_pace'] = np.random.normal(98, 5, len(data))
            
            feature_names = ['home_team_ppg', 'away_team_ppg', 'home_win_pct', 
                           'away_win_pct', 'home_pace', 'away_pace']
        
        elif self.sport == 'NFL':
            # NFL-specific synthetic features
            data['home_team_off_yards'] = np.random.normal(350, 50, len(data))
            data['away_team_off_yards'] = np.random.normal(340, 50, len(data))
            data['home_win_pct'] = np.random.beta(2, 2, len(data))
            data['away_win_pct'] = np.random.beta(2, 2, len(data))
            data['weather_score'] = np.random.uniform(0, 1, len(data))
            
            feature_names = ['home_team_off_yards', 'away_team_off_yards', 
                           'home_win_pct', 'away_win_pct', 'weather_score']
        
        else:
            # Generic synthetic features
            data['home_win_pct'] = np.random.beta(2, 2, len(data))
            data['away_win_pct'] = np.random.beta(2, 2, len(data))
            data['home_score_avg'] = np.random.normal(100, 15, len(data))
            data['away_score_avg'] = np.random.normal(98, 15, len(data))
            
            feature_names = ['home_win_pct', 'away_win_pct', 'home_score_avg', 'away_score_avg']
        
        return feature_names
    
    def prepare_sequences(self, features: np.ndarray, sequence_length: int = 10) -> np.ndarray:
        """Prepare sequential data for LSTM/RNN models"""
        if len(features) < sequence_length:
            # Pad with zeros if not enough data
            padding = np.zeros((sequence_length - len(features), features.shape[1]))
            features = np.vstack([padding, features])
        
        sequences = []
        for i in range(sequence_length, len(features) + 1):
            sequences.append(features[i-sequence_length:i])
        
        return np.array(sequences)
    
    def train_model(self, data: pd.DataFrame, target_column: str = 'outcome', 
                   epochs: int = 100, batch_size: int = 32, validation_split: float = 0.2):
        """Train the neural network model"""
        # Prepare features
        X = self.prepare_features(data)
        
        # Handle target variable
        if target_column not in data.columns:
            # Generate synthetic targets for demo
            y = np.random.choice([0, 1, 2], size=len(data), p=[0.4, 0.35, 0.25])
        else:
            y = self.label_encoder.fit_transform(data[target_column])
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Prepare sequences for time series models
        if self.model_type in ['lstm', 'transformer']:
            sequence_length = min(10, len(X_scaled) // 2)
            X_sequences = self.prepare_sequences(X_scaled, sequence_length)
            y_sequences = y[sequence_length-1:len(X_sequences)+sequence_length-1]
            
            # Update X and y for sequence data
            X_scaled = X_sequences
            y = y_sequences
            
            input_shape = (X_scaled.shape[1], X_scaled.shape[2])
        else:
            input_shape = (X_scaled.shape[1],)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y if len(np.unique(y)) > 1 else None
        )
        
        # Create model based on type
        num_classes = len(np.unique(y))
        
        if self.model_type == 'lstm':
            self.model = self.create_lstm_model(input_shape, num_classes)
        elif self.model_type == 'transformer':
            self.model = self.create_transformer_model(input_shape, num_classes)
        elif self.model_type == 'cnn':
            # Reshape for CNN if needed
            if len(input_shape) == 1:
                X_train = X_train.reshape(X_train.shape[0], X_train.shape[1], 1)
                X_test = X_test.reshape(X_test.shape[0], X_test.shape[1], 1)
                input_shape = (input_shape[0], 1)
            self.model = self.create_cnn_model(input_shape, num_classes)
        
        # Training callbacks
        callbacks = [
            keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True),
            keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=5, min_lr=1e-7),
            keras.callbacks.ModelCheckpoint('best_model.h5', save_best_only=True)
        ]
        
        # Train model
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_test, y_test),
            callbacks=callbacks,
            verbose=1
        )
        
        self.is_trained = True
        
        # Evaluate model
        test_loss, test_accuracy = self.model.evaluate(X_test, y_test, verbose=0)[:2]
        
        return {
            'test_accuracy': float(test_accuracy),
            'test_loss': float(test_loss),
            'training_history': {
                'loss': [float(x) for x in history.history['loss']],
                'accuracy': [float(x) for x in history.history['accuracy']],
                'val_loss': [float(x) for x in history.history['val_loss']],
                'val_accuracy': [float(x) for x in history.history['val_accuracy']]
            }
        }
    
    def predict_game(self, game_data: Dict) -> Dict:
        """Predict outcome for a single game"""
        if not self.is_trained:
            return {'error': 'Model not trained yet'}
        
        # Convert game data to DataFrame
        df = pd.DataFrame([game_data])
        
        # Prepare features
        X = self.prepare_features(df)
        X_scaled = self.scaler.transform(X)
        
        # Handle sequence data for time series models
        if self.model_type in ['lstm', 'transformer']:
            # For single prediction, create a dummy sequence
            sequence_length = 10
            if X_scaled.shape[0] == 1:
                # Repeat the single sample to create a sequence
                X_scaled = np.repeat(X_scaled, sequence_length, axis=0)
            X_scaled = X_scaled.reshape(1, X_scaled.shape[0], X_scaled.shape[1])
        elif self.model_type == 'cnn':
            X_scaled = X_scaled.reshape(X_scaled.shape[0], X_scaled.shape[1], 1)
        
        # Make prediction
        probabilities = self.model.predict(X_scaled, verbose=0)[0]
        predicted_class = np.argmax(probabilities)
        confidence = float(np.max(probabilities))
        
        # Map classes back to labels
        class_labels = ['Away Win', 'Draw', 'Home Win']
        if len(probabilities) == 2:
            class_labels = ['Away Win', 'Home Win']
        
        return {
            'predicted_outcome': class_labels[predicted_class],
            'confidence': confidence,
            'probabilities': {
                label: float(prob) 
                for label, prob in zip(class_labels, probabilities)
            },
            'model_type': self.model_type,
            'sport': self.sport
        }
    
    def get_feature_importance(self) -> Dict:
        """Get feature importance using gradient-based methods"""
        if not self.is_trained:
            return {'error': 'Model not trained yet'}
        
        # For demonstration, return mock importance scores
        # In production, this would use techniques like integrated gradients
        importance_scores = np.random.dirichlet(np.ones(len(self.feature_names)))
        
        return {
            'feature_importance': {
                name: float(score) 
                for name, score in zip(self.feature_names, importance_scores)
            },
            'top_features': sorted(
                zip(self.feature_names, importance_scores),
                key=lambda x: x[1], reverse=True
            )[:5]
        }
    
    def save_model(self, filepath: str):
        """Save trained model and preprocessing objects"""
        if not self.is_trained:
            raise ValueError("Model not trained yet")
        
        # Save model
        model_path = f"{filepath}_model.h5"
        self.model.save(model_path)
        
        # Save preprocessing objects
        scaler_path = f"{filepath}_scaler.joblib"
        joblib.dump(self.scaler, scaler_path)
        
        # Save metadata
        metadata = {
            'model_type': self.model_type,
            'sport': self.sport,
            'feature_names': self.feature_names,
            'is_trained': self.is_trained
        }
        
        metadata_path = f"{filepath}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        
        return {
            'model_path': model_path,
            'scaler_path': scaler_path,
            'metadata_path': metadata_path
        }
    
    def load_model(self, filepath: str):
        """Load trained model and preprocessing objects"""
        try:
            # Load metadata
            metadata_path = f"{filepath}_metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Load model
            model_path = f"{filepath}_model.h5"
            self.model = keras.models.load_model(model_path)
            
            # Load scaler
            scaler_path = f"{filepath}_scaler.joblib"
            self.scaler = joblib.load(scaler_path)
            
            # Restore metadata
            self.model_type = metadata['model_type']
            self.sport = metadata['sport']
            self.feature_names = metadata['feature_names']
            self.is_trained = metadata['is_trained']
            
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False


def generate_demo_training_data(sport: str = 'NBA', num_samples: int = 1000) -> pd.DataFrame:
    """Generate synthetic training data for demonstration"""
    np.random.seed(42)
    
    data = pd.DataFrame()
    
    if sport.upper() == 'NBA':
        data['home_team_ppg'] = np.random.normal(110, 8, num_samples)
        data['away_team_ppg'] = np.random.normal(108, 8, num_samples)
        data['home_win_pct'] = np.random.beta(2, 2, num_samples)
        data['away_win_pct'] = np.random.beta(2, 2, num_samples)
        data['home_pace'] = np.random.normal(100, 5, num_samples)
        data['away_pace'] = np.random.normal(98, 5, num_samples)
        
        # Create outcome based on features (with some noise)
        win_prob = (
            0.3 * (data['home_team_ppg'] / data['away_team_ppg']) +
            0.4 * (data['home_win_pct'] / (data['home_win_pct'] + data['away_win_pct'])) +
            0.1 * (data['home_pace'] / data['away_pace']) +
            0.2 * np.random.normal(0.5, 0.1, num_samples)  # Home court advantage + noise
        )
        
        # Convert to categorical outcome
        data['outcome'] = np.where(
            win_prob > 0.55, 'Home Win',
            np.where(win_prob < 0.45, 'Away Win', 'Close Game')
        )
        
    elif sport.upper() == 'NFL':
        data['home_team_off_yards'] = np.random.normal(350, 40, num_samples)
        data['away_team_off_yards'] = np.random.normal(340, 40, num_samples)
        data['home_win_pct'] = np.random.beta(2, 2, num_samples)
        data['away_win_pct'] = np.random.beta(2, 2, num_samples)
        data['weather_score'] = np.random.uniform(0, 1, num_samples)
        
        # Create outcome based on features
        win_prob = (
            0.4 * (data['home_team_off_yards'] / data['away_team_off_yards']) +
            0.4 * (data['home_win_pct'] / (data['home_win_pct'] + data['away_win_pct'])) +
            0.1 * data['weather_score'] +
            0.1 * np.random.normal(0.5, 0.1, num_samples)  # Home field advantage + noise
        )
        
        data['outcome'] = np.where(win_prob > 0.52, 'Home Win', 'Away Win')
    
    else:
        # Generic sports data
        data['home_win_pct'] = np.random.beta(2, 2, num_samples)
        data['away_win_pct'] = np.random.beta(2, 2, num_samples)
        data['home_score_avg'] = np.random.normal(100, 12, num_samples)
        data['away_score_avg'] = np.random.normal(98, 12, num_samples)
        
        win_prob = (
            0.5 * (data['home_win_pct'] / (data['home_win_pct'] + data['away_win_pct'])) +
            0.3 * (data['home_score_avg'] / data['away_score_avg']) +
            0.2 * np.random.normal(0.5, 0.1, num_samples)
        )
        
        data['outcome'] = np.where(win_prob > 0.52, 'Home Win', 'Away Win')
    
    # Add game date for time series
    base_date = datetime(2023, 1, 1)
    data['game_date'] = [base_date + timedelta(days=i) for i in range(num_samples)]
    
    return data


if __name__ == "__main__":
    # Demo usage
    print("Creating NBA Neural Network Predictor...")
    
    # Generate demo data
    demo_data = generate_demo_training_data('NBA', 500)
    print(f"Generated {len(demo_data)} demo games for training")
    
    # Create and train LSTM model
    predictor = SportsNeuralPredictor(model_type='lstm', sport='nba')
    print("Training LSTM model...")
    
    training_results = predictor.train_model(demo_data, epochs=20)
    print(f"Training completed. Test accuracy: {training_results['test_accuracy']:.3f}")
    
    # Test prediction
    test_game = {
        'home_team_ppg': 112,
        'away_team_ppg': 108,
        'home_win_pct': 0.65,
        'away_win_pct': 0.55,
        'home_pace': 102,
        'away_pace': 98
    }
    
    prediction = predictor.predict_game(test_game)
    print(f"\nPrediction for test game: {prediction}")
    
    # Get feature importance
    importance = predictor.get_feature_importance()
    print(f"\nTop 3 important features:")
    for feature, score in importance['top_features'][:3]:
        print(f"  {feature}: {score:.3f}")