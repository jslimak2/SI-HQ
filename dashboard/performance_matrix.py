"""
Model Performance Matrix and Tracking System
Tracks model performance, parameters, and provides comparison capabilities
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
from dataclasses import dataclass
from enum import Enum


@dataclass
class ModelPerformanceEntry:
    """Single performance entry for a model"""
    model_id: str
    sport: str
    model_type: str
    version: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    total_predictions: int
    correct_predictions: int
    profit_loss: float
    roi_percentage: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    avg_confidence: float
    training_date: datetime
    evaluation_date: datetime
    parameters: Dict[str, Any]
    tags: List[str]
    notes: str = ""


class PerformanceCategory(Enum):
    EXCELLENT = "excellent"  # >75% accuracy
    GOOD = "good"           # 65-75% accuracy  
    AVERAGE = "average"     # 55-65% accuracy
    POOR = "poor"          # <55% accuracy


class ModelPerformanceMatrix:
    """Manages model performance tracking and comparison"""
    
    def __init__(self):
        self.performance_data: List[ModelPerformanceEntry] = []
        self.model_metadata: Dict[str, Dict] = {}
        self.benchmark_metrics: Dict[str, float] = {
            'minimum_accuracy': 0.55,
            'target_accuracy': 0.70,
            'minimum_roi': 0.05,
            'target_roi': 0.15,
            'minimum_sharpe': 1.0,
            'target_sharpe': 2.0
        }
        
    def add_performance_entry(self, entry: ModelPerformanceEntry):
        """Add a new performance entry"""
        self.performance_data.append(entry)
        
        # Update model metadata
        if entry.model_id not in self.model_metadata:
            self.model_metadata[entry.model_id] = {
                'first_evaluation': entry.evaluation_date,
                'total_evaluations': 0,
                'best_accuracy': 0.0,
                'current_version': entry.version
            }
        
        metadata = self.model_metadata[entry.model_id]
        metadata['total_evaluations'] += 1
        metadata['last_evaluation'] = entry.evaluation_date
        metadata['current_version'] = entry.version
        
        if entry.accuracy > metadata['best_accuracy']:
            metadata['best_accuracy'] = entry.accuracy
            metadata['best_performance_date'] = entry.evaluation_date
    
    def get_performance_matrix(self, sport: str = None, model_type: str = None, 
                              days_back: int = 30) -> pd.DataFrame:
        """Get performance matrix as DataFrame"""
        # Filter data
        cutoff_date = datetime.now() - timedelta(days=days_back)
        filtered_data = [
            entry for entry in self.performance_data
            if entry.evaluation_date >= cutoff_date
        ]
        
        if sport:
            filtered_data = [entry for entry in filtered_data if entry.sport == sport]
        
        if model_type:
            filtered_data = [entry for entry in filtered_data if entry.model_type == model_type]
        
        if not filtered_data:
            return pd.DataFrame()
        
        # Convert to DataFrame
        data = []
        for entry in filtered_data:
            data.append({
                'Model ID': entry.model_id,
                'Sport': entry.sport,
                'Model Type': entry.model_type,
                'Version': entry.version,
                'Accuracy': entry.accuracy,
                'Precision': entry.precision,
                'Recall': entry.recall,
                'F1 Score': entry.f1_score,
                'AUC-ROC': entry.auc_roc,
                'Total Predictions': entry.total_predictions,
                'Correct Predictions': entry.correct_predictions,
                'Profit/Loss': entry.profit_loss,
                'ROI %': entry.roi_percentage,
                'Sharpe Ratio': entry.sharpe_ratio,
                'Max Drawdown': entry.max_drawdown,
                'Win Rate': entry.win_rate,
                'Avg Confidence': entry.avg_confidence,
                'Training Date': entry.training_date,
                'Evaluation Date': entry.evaluation_date,
                'Tags': ', '.join(entry.tags),
                'Notes': entry.notes
            })
        
        df = pd.DataFrame(data)
        
        # Sort by accuracy descending
        if not df.empty:
            df = df.sort_values('Accuracy', ascending=False)
        
        return df
    
    def get_model_comparison(self, model_ids: List[str]) -> Dict[str, Any]:
        """Compare specific models side by side"""
        comparison_data = {}
        
        for model_id in model_ids:
            model_entries = [entry for entry in self.performance_data if entry.model_id == model_id]
            
            if not model_entries:
                continue
            
            # Get latest entry
            latest_entry = max(model_entries, key=lambda x: x.evaluation_date)
            
            # Calculate historical performance
            accuracies = [entry.accuracy for entry in model_entries]
            rois = [entry.roi_percentage for entry in model_entries]
            
            comparison_data[model_id] = {
                'latest_performance': {
                    'accuracy': latest_entry.accuracy,
                    'precision': latest_entry.precision,
                    'recall': latest_entry.recall,
                    'f1_score': latest_entry.f1_score,
                    'roi_percentage': latest_entry.roi_percentage,
                    'sharpe_ratio': latest_entry.sharpe_ratio,
                    'win_rate': latest_entry.win_rate
                },
                'historical_stats': {
                    'avg_accuracy': np.mean(accuracies),
                    'accuracy_std': np.std(accuracies),
                    'avg_roi': np.mean(rois),
                    'roi_std': np.std(rois),
                    'total_evaluations': len(model_entries),
                    'consistency_score': 1 - (np.std(accuracies) / np.mean(accuracies)) if np.mean(accuracies) > 0 else 0
                },
                'model_info': {
                    'sport': latest_entry.sport,
                    'model_type': latest_entry.model_type,
                    'version': latest_entry.version,
                    'tags': latest_entry.tags,
                    'parameters': latest_entry.parameters
                },
                'performance_category': self._categorize_performance(latest_entry.accuracy),
                'benchmark_comparison': self._compare_to_benchmarks(latest_entry)
            }
        
        return comparison_data
    
    def get_sport_leaderboard(self, sport: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing models for a specific sport"""
        sport_entries = [entry for entry in self.performance_data if entry.sport == sport]
        
        # Group by model_id and get latest entry for each
        latest_entries = {}
        for entry in sport_entries:
            if (entry.model_id not in latest_entries or 
                entry.evaluation_date > latest_entries[entry.model_id].evaluation_date):
                latest_entries[entry.model_id] = entry
        
        # Sort by accuracy
        sorted_entries = sorted(latest_entries.values(), key=lambda x: x.accuracy, reverse=True)
        
        leaderboard = []
        for i, entry in enumerate(sorted_entries[:limit], 1):
            leaderboard.append({
                'rank': i,
                'model_id': entry.model_id,
                'model_type': entry.model_type,
                'accuracy': entry.accuracy,
                'roi_percentage': entry.roi_percentage,
                'win_rate': entry.win_rate,
                'total_predictions': entry.total_predictions,
                'performance_category': self._categorize_performance(entry.accuracy),
                'tags': entry.tags,
                'evaluation_date': entry.evaluation_date.isoformat()
            })
        
        return leaderboard
    
    def get_model_type_analysis(self) -> Dict[str, Any]:
        """Analyze performance by model type across all sports"""
        analysis = {}
        
        # Group by model type
        by_type = {}
        for entry in self.performance_data:
            if entry.model_type not in by_type:
                by_type[entry.model_type] = []
            by_type[entry.model_type].append(entry)
        
        for model_type, entries in by_type.items():
            accuracies = [entry.accuracy for entry in entries]
            rois = [entry.roi_percentage for entry in entries]
            
            analysis[model_type] = {
                'total_models': len(set(entry.model_id for entry in entries)),
                'total_evaluations': len(entries),
                'avg_accuracy': np.mean(accuracies),
                'accuracy_std': np.std(accuracies),
                'best_accuracy': max(accuracies),
                'worst_accuracy': min(accuracies),
                'avg_roi': np.mean(rois),
                'roi_std': np.std(rois),
                'success_rate': len([acc for acc in accuracies if acc >= self.benchmark_metrics['target_accuracy']]) / len(accuracies),
                'sports_coverage': list(set(entry.sport for entry in entries))
            }
        
        return analysis
    
    def get_parameter_effectiveness(self, model_type: str = None) -> Dict[str, Any]:
        """Analyze which parameters lead to better performance"""
        relevant_entries = self.performance_data
        
        if model_type:
            relevant_entries = [entry for entry in relevant_entries if entry.model_type == model_type]
        
        parameter_analysis = {}
        
        # Collect all unique parameters
        all_params = set()
        for entry in relevant_entries:
            all_params.update(entry.parameters.keys())
        
        for param in all_params:
            param_values = []
            param_accuracies = []
            
            for entry in relevant_entries:
                if param in entry.parameters:
                    param_values.append(entry.parameters[param])
                    param_accuracies.append(entry.accuracy)
            
            if len(param_values) > 1:
                # Calculate correlation between parameter value and accuracy
                if all(isinstance(v, (int, float)) for v in param_values):
                    correlation = np.corrcoef(param_values, param_accuracies)[0, 1]
                    
                    parameter_analysis[param] = {
                        'correlation_with_accuracy': correlation,
                        'sample_size': len(param_values),
                        'value_range': [min(param_values), max(param_values)],
                        'optimal_value': param_values[np.argmax(param_accuracies)],
                        'effectiveness_score': abs(correlation) * min(1.0, len(param_values) / 10)
                    }
        
        # Sort by effectiveness score
        sorted_params = sorted(parameter_analysis.items(), 
                             key=lambda x: x[1]['effectiveness_score'], 
                             reverse=True)
        
        return dict(sorted_params)
    
    def get_trending_models(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get models with improving performance trends"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_entries = [entry for entry in self.performance_data if entry.evaluation_date >= cutoff_date]
        
        # Group by model
        model_trends = {}
        for entry in recent_entries:
            if entry.model_id not in model_trends:
                model_trends[entry.model_id] = []
            model_trends[entry.model_id].append(entry)
        
        trending = []
        for model_id, entries in model_trends.items():
            if len(entries) >= 2:
                # Sort by date
                entries.sort(key=lambda x: x.evaluation_date)
                
                # Calculate trend
                accuracies = [entry.accuracy for entry in entries]
                trend_slope = (accuracies[-1] - accuracies[0]) / len(accuracies)
                
                if trend_slope > 0.01:  # Improving by more than 1%
                    trending.append({
                        'model_id': model_id,
                        'model_type': entries[-1].model_type,
                        'sport': entries[-1].sport,
                        'trend_slope': trend_slope,
                        'current_accuracy': accuracies[-1],
                        'improvement': accuracies[-1] - accuracies[0],
                        'evaluations_count': len(entries),
                        'latest_evaluation': entries[-1].evaluation_date.isoformat()
                    })
        
        # Sort by trend slope
        trending.sort(key=lambda x: x['trend_slope'], reverse=True)
        
        return trending
    
    def _categorize_performance(self, accuracy: float) -> str:
        """Categorize model performance"""
        if accuracy >= 0.75:
            return PerformanceCategory.EXCELLENT.value
        elif accuracy >= 0.65:
            return PerformanceCategory.GOOD.value
        elif accuracy >= 0.55:
            return PerformanceCategory.AVERAGE.value
        else:
            return PerformanceCategory.POOR.value
    
    def _compare_to_benchmarks(self, entry: ModelPerformanceEntry) -> Dict[str, str]:
        """Compare model performance to benchmarks"""
        comparison = {}
        
        comparison['accuracy'] = (
            'above_target' if entry.accuracy >= self.benchmark_metrics['target_accuracy']
            else 'above_minimum' if entry.accuracy >= self.benchmark_metrics['minimum_accuracy']
            else 'below_minimum'
        )
        
        comparison['roi'] = (
            'above_target' if entry.roi_percentage >= self.benchmark_metrics['target_roi']
            else 'above_minimum' if entry.roi_percentage >= self.benchmark_metrics['minimum_roi']
            else 'below_minimum'
        )
        
        comparison['sharpe'] = (
            'above_target' if entry.sharpe_ratio >= self.benchmark_metrics['target_sharpe']
            else 'above_minimum' if entry.sharpe_ratio >= self.benchmark_metrics['minimum_sharpe']
            else 'below_minimum'
        )
        
        return comparison
    
    def generate_demo_data(self):
        """Generate demo performance data for testing"""
        sports = ['NBA', 'NFL', 'MLB', 'NCAAF', 'NCAAB']
        model_types = ['lstm_weather', 'ensemble', 'neural', 'statistical']
        
        # Generate 50 demo entries
        for i in range(50):
            sport = np.random.choice(sports)
            model_type = np.random.choice(model_types)
            model_id = f"{sport.lower()}_{model_type}_{i:03d}"
            
            # Generate realistic performance metrics
            base_accuracy = {
                'lstm_weather': 0.72,
                'ensemble': 0.75,
                'neural': 0.69,
                'statistical': 0.66
            }[model_type]
            
            accuracy = max(0.45, min(0.85, base_accuracy + np.random.normal(0, 0.05)))
            precision = accuracy + np.random.normal(0, 0.02)
            recall = accuracy + np.random.normal(0, 0.02)
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            # Financial metrics
            total_predictions = np.random.randint(50, 200)
            correct_predictions = int(accuracy * total_predictions)
            profit_loss = np.random.uniform(-500, 2000)
            roi_percentage = profit_loss / 1000 * 100  # Assuming $1000 bankroll
            
            # Generate parameters based on model type
            if model_type == 'lstm_weather':
                parameters = {
                    'lstm_units': np.random.choice([32, 64, 128]),
                    'dropout_rate': round(np.random.uniform(0.2, 0.5), 2),
                    'sequence_length': np.random.choice([5, 10, 15]),
                    'learning_rate': round(np.random.uniform(0.0001, 0.01), 4),
                    'weather_features': np.random.choice([4, 7, 10])
                }
            elif model_type == 'ensemble':
                parameters = {
                    'n_models': np.random.choice([3, 4, 5]),
                    'voting_strategy': np.random.choice(['soft', 'hard']),
                    'cv_folds': np.random.choice([5, 10]),
                    'meta_learner': np.random.choice(['logistic', 'neural', 'svm'])
                }
            elif model_type == 'neural':
                parameters = {
                    'hidden_layers': np.random.choice([2, 3, 4]),
                    'neurons_per_layer': np.random.choice([32, 64, 128]),
                    'activation': np.random.choice(['relu', 'tanh', 'sigmoid']),
                    'batch_size': np.random.choice([16, 32, 64]),
                    'epochs': np.random.choice([50, 100, 150])
                }
            else:  # statistical
                parameters = {
                    'regularization': np.random.choice(['l1', 'l2', 'elastic_net']),
                    'cv_method': np.random.choice(['kfold', 'time_series']),
                    'feature_selection': np.random.choice(['rfe', 'univariate', 'tree_based'])
                }
            
            tags = []
            if accuracy > 0.7:
                tags.append('high_performance')
            if roi_percentage > 10:
                tags.append('profitable')
            if model_type == 'lstm_weather' and sport in ['NFL', 'MLB']:
                tags.append('weather_dependent')
            
            entry = ModelPerformanceEntry(
                model_id=model_id,
                sport=sport,
                model_type=model_type,
                version="1.0",
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1_score,
                auc_roc=accuracy + 0.05,
                total_predictions=total_predictions,
                correct_predictions=correct_predictions,
                profit_loss=profit_loss,
                roi_percentage=roi_percentage,
                sharpe_ratio=max(0.5, roi_percentage / 15),
                max_drawdown=abs(profit_loss * 0.3) if profit_loss < 0 else np.random.uniform(50, 200),
                win_rate=accuracy,
                avg_confidence=np.random.uniform(0.6, 0.85),
                training_date=datetime.now() - timedelta(days=np.random.randint(1, 60)),
                evaluation_date=datetime.now() - timedelta(days=np.random.randint(0, 30)),
                parameters=parameters,
                tags=tags,
                notes=f"Demo {model_type} model for {sport}"
            )
            
            self.add_performance_entry(entry)


# Global performance matrix instance
performance_matrix = ModelPerformanceMatrix()