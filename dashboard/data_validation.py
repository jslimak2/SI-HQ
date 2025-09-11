"""
Professional data validation and processing pipeline for Post9
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from error_handling import ValidationError

logger = logging.getLogger(__name__)

class DataQualityLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"  
    LOW = "low"
    INVALID = "invalid"

@dataclass
class DataQualityReport:
    """Report on data quality assessment"""
    overall_quality: DataQualityLevel
    total_records: int
    valid_records: int
    missing_data_percentage: float
    outlier_percentage: float
    duplicate_percentage: float
    quality_score: float
    issues: List[str]
    recommendations: List[str]
    timestamp: str

class DataValidator:
    """Professional data validation for sports and betting data"""
    
    def __init__(self):
        self.sport_schemas = self._load_sport_schemas()
        self.validation_rules = self._load_validation_rules()
    
    def _load_sport_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Define expected data schemas for different sports"""
        return {
            'NBA': {
                'required_fields': [
                    'home_team', 'away_team', 'home_score', 'away_score',
                    'game_date', 'season'
                ],
                'optional_fields': [
                    'home_wins', 'away_wins', 'home_losses', 'away_losses',
                    'home_ppg', 'away_ppg', 'home_pace', 'away_pace',
                    'home_fg_pct', 'away_fg_pct', 'home_three_pct', 'away_three_pct'
                ],
                'numeric_fields': [
                    'home_score', 'away_score', 'home_wins', 'away_wins',
                    'home_ppg', 'away_ppg', 'home_pace', 'away_pace'
                ],
                'score_range': (0, 200),
                'ppg_range': (70, 150),
                'pace_range': (85, 110)
            },
            'NFL': {
                'required_fields': [
                    'home_team', 'away_team', 'home_score', 'away_score',
                    'game_date', 'season', 'week'
                ],
                'optional_fields': [
                    'home_wins', 'away_wins', 'home_losses', 'away_losses',
                    'home_yards', 'away_yards', 'home_turnovers', 'away_turnovers'
                ],
                'numeric_fields': [
                    'home_score', 'away_score', 'week', 'home_wins', 'away_wins',
                    'home_yards', 'away_yards', 'home_turnovers', 'away_turnovers'
                ],
                'score_range': (0, 70),
                'yards_range': (100, 700),
                'week_range': (1, 18)
            },
            'MLB': {
                'required_fields': [
                    'home_team', 'away_team', 'home_score', 'away_score',
                    'game_date', 'season'
                ],
                'optional_fields': [
                    'home_wins', 'away_wins', 'home_era', 'away_era',
                    'home_hits', 'away_hits', 'home_errors', 'away_errors'
                ],
                'numeric_fields': [
                    'home_score', 'away_score', 'home_wins', 'away_wins',
                    'home_era', 'away_era', 'home_hits', 'away_hits'
                ],
                'score_range': (0, 30),
                'era_range': (1.0, 10.0),
                'hits_range': (0, 25)
            }
        }
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Define validation rules for different data types"""
        return {
            'betting_odds': {
                'decimal_range': (1.01, 100.0),
                'american_range': (-10000, 10000),
                'fractional_pattern': r'^\d+/\d+$'
            },
            'probability': {
                'range': (0.0, 1.0)
            },
            'currency': {
                'range': (0.01, 1000000.0)
            },
            'team_names': {
                'known_teams': {
                    'NBA': ['Lakers', 'Warriors', 'Celtics', 'Heat', 'Bulls', 'Knicks'],
                    'NFL': ['Chiefs', 'Bills', 'Cowboys', 'Eagles', 'Patriots'],
                    'MLB': ['Yankees', 'Red Sox', 'Dodgers', 'Giants', 'Cubs']
                }
            }
        }
    
    def validate_sports_data(self, data: Union[pd.DataFrame, List[Dict]], sport: str) -> DataQualityReport:
        """Comprehensive validation of sports data"""
        logger.info(f"Starting data validation for {sport} data")
        
        # Convert to DataFrame if needed
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()
        
        issues = []
        recommendations = []
        
        if sport not in self.sport_schemas:
            raise ValidationError(f"Unknown sport: {sport}")
        
        schema = self.sport_schemas[sport]
        total_records = len(df)
        
        if total_records == 0:
            return DataQualityReport(
                overall_quality=DataQualityLevel.INVALID,
                total_records=0,
                valid_records=0,
                missing_data_percentage=100.0,
                outlier_percentage=0.0,
                duplicate_percentage=0.0,
                quality_score=0.0,
                issues=["No data provided"],
                recommendations=["Provide valid data"],
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Check required fields
        missing_required = [field for field in schema['required_fields'] if field not in df.columns]
        if missing_required:
            issues.append(f"Missing required fields: {missing_required}")
            recommendations.append(f"Add missing required fields: {missing_required}")
        
        # Calculate missing data percentage
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isnull().sum().sum()
        missing_percentage = (missing_cells / total_cells) * 100
        
        if missing_percentage > 20:
            issues.append(f"High missing data rate: {missing_percentage:.1f}%")
            recommendations.append("Improve data collection to reduce missing values")
        
        # Check for duplicates
        duplicate_count = df.duplicated().sum()
        duplicate_percentage = (duplicate_count / total_records) * 100
        
        if duplicate_percentage > 5:
            issues.append(f"High duplicate rate: {duplicate_percentage:.1f}%")
            recommendations.append("Remove duplicate records")
        
        # Validate numeric fields and detect outliers
        outlier_count = 0
        for field in schema.get('numeric_fields', []):
            if field in df.columns:
                outliers = self._detect_outliers(df[field], field, schema)
                outlier_count += len(outliers)
                
                if len(outliers) > 0:
                    outlier_pct = (len(outliers) / total_records) * 100
                    issues.append(f"Outliers in {field}: {len(outliers)} records ({outlier_pct:.1f}%)")
        
        outlier_percentage = (outlier_count / total_records) * 100 if total_records > 0 else 0
        
        # Validate team names
        if sport in self.validation_rules['team_names']['known_teams']:
            known_teams = self.validation_rules['team_names']['known_teams'][sport]
            for team_field in ['home_team', 'away_team']:
                if team_field in df.columns:
                    unknown_teams = set(df[team_field].dropna()) - set(known_teams)
                    if unknown_teams:
                        issues.append(f"Unknown teams in {team_field}: {list(unknown_teams)}")
                        recommendations.append(f"Verify team names in {team_field}")
        
        # Calculate valid records (records without major issues)
        valid_records = total_records - duplicate_count
        for field in schema['required_fields']:
            if field in df.columns:
                valid_records -= df[field].isnull().sum()
        valid_records = max(0, valid_records)
        
        # Calculate overall quality score
        quality_score = self._calculate_quality_score(
            valid_records / total_records if total_records > 0 else 0,
            missing_percentage,
            outlier_percentage,
            duplicate_percentage
        )
        
        # Determine overall quality level
        if quality_score >= 85:
            overall_quality = DataQualityLevel.HIGH
        elif quality_score >= 70:
            overall_quality = DataQualityLevel.MEDIUM
        elif quality_score >= 50:
            overall_quality = DataQualityLevel.LOW
        else:
            overall_quality = DataQualityLevel.INVALID
        
        logger.info(f"Data validation completed. Quality: {overall_quality.value}, Score: {quality_score:.1f}")
        
        return DataQualityReport(
            overall_quality=overall_quality,
            total_records=total_records,
            valid_records=valid_records,
            missing_data_percentage=missing_percentage,
            outlier_percentage=outlier_percentage,
            duplicate_percentage=duplicate_percentage,
            quality_score=quality_score,
            issues=issues,
            recommendations=recommendations,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def _detect_outliers(self, series: pd.Series, field_name: str, schema: Dict) -> List[int]:
        """Detect outliers in numeric data"""
        outliers = []
        
        # Check against expected ranges
        if field_name == 'home_score' or field_name == 'away_score':
            score_range = schema.get('score_range', (0, 300))
            outliers.extend(series[(series < score_range[0]) | (series > score_range[1])].index.tolist())
        
        elif 'ppg' in field_name and 'ppg_range' in schema:
            ppg_range = schema['ppg_range']
            outliers.extend(series[(series < ppg_range[0]) | (series > ppg_range[1])].index.tolist())
        
        elif 'pace' in field_name and 'pace_range' in schema:
            pace_range = schema['pace_range']
            outliers.extend(series[(series < pace_range[0]) | (series > pace_range[1])].index.tolist())
        
        # Statistical outlier detection (IQR method)
        if len(series.dropna()) > 10:  # Only if enough data
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            statistical_outliers = series[(series < lower_bound) | (series > upper_bound)].index.tolist()
            outliers.extend(statistical_outliers)
        
        return list(set(outliers))  # Remove duplicates
    
    def _calculate_quality_score(self, completeness: float, missing_pct: float, 
                                outlier_pct: float, duplicate_pct: float) -> float:
        """Calculate overall data quality score (0-100)"""
        
        # Weights for different quality aspects
        completeness_weight = 0.4
        missing_weight = 0.3
        outlier_weight = 0.2
        duplicate_weight = 0.1
        
        # Calculate component scores (0-100)
        completeness_score = completeness * 100
        missing_score = max(0, 100 - missing_pct)
        outlier_score = max(0, 100 - outlier_pct * 2)  # Penalize outliers more
        duplicate_score = max(0, 100 - duplicate_pct * 3)  # Penalize duplicates heavily
        
        # Weighted average
        quality_score = (
            completeness_score * completeness_weight +
            missing_score * missing_weight +
            outlier_score * outlier_weight +
            duplicate_score * duplicate_weight
        )
        
        return min(100, max(0, quality_score))
    
    def validate_betting_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate betting-specific data"""
        issues = []
        
        # Validate odds
        if 'odds' in data:
            odds = data['odds']
            try:
                odds_float = float(odds)
                rules = self.validation_rules['betting_odds']
                
                if not (rules['decimal_range'][0] <= odds_float <= rules['decimal_range'][1]):
                    issues.append(f"Odds {odds} outside valid range {rules['decimal_range']}")
            except ValueError:
                issues.append(f"Invalid odds format: {odds}")
        
        # Validate probabilities
        for field in ['win_probability', 'confidence']:
            if field in data:
                try:
                    prob = float(data[field])
                    prob_range = self.validation_rules['probability']['range']
                    if not (prob_range[0] <= prob <= prob_range[1]):
                        issues.append(f"{field} {prob} outside valid range {prob_range}")
                except ValueError:
                    issues.append(f"Invalid {field} format: {data[field]}")
        
        # Validate currency amounts
        for field in ['bet_amount', 'payout', 'balance']:
            if field in data:
                try:
                    amount = float(data[field])
                    currency_range = self.validation_rules['currency']['range']
                    if not (currency_range[0] <= amount <= currency_range[1]):
                        issues.append(f"{field} {amount} outside valid range {currency_range}")
                except ValueError:
                    issues.append(f"Invalid {field} format: {data[field]}")
        
        return len(issues) == 0, issues
    
    def sanitize_data(self, data: Union[pd.DataFrame, Dict], data_type: str = "sports") -> Union[pd.DataFrame, Dict]:
        """Sanitize data by removing/fixing common issues"""
        
        if isinstance(data, dict):
            return self._sanitize_dict(data, data_type)
        elif isinstance(data, pd.DataFrame):
            return self._sanitize_dataframe(data, data_type)
        else:
            raise ValidationError("Unsupported data type for sanitization")
    
    def _sanitize_dict(self, data: Dict, data_type: str) -> Dict:
        """Sanitize dictionary data"""
        sanitized = {}
        
        for key, value in data.items():
            # Remove null bytes and control characters from strings
            if isinstance(value, str):
                sanitized[key] = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r').strip()
            
            # Ensure numeric fields are proper numbers
            elif isinstance(value, (int, float)):
                if np.isnan(value) or np.isinf(value):
                    sanitized[key] = None
                else:
                    sanitized[key] = value
            
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_dataframe(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Sanitize DataFrame"""
        df_clean = df.copy()
        
        # Remove completely empty rows
        df_clean = df_clean.dropna(how='all')
        
        # Remove duplicate rows
        df_clean = df_clean.drop_duplicates()
        
        # Clean string columns
        for col in df_clean.select_dtypes(include=['object']).columns:
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].astype(str).apply(
                    lambda x: ''.join(char for char in x if ord(char) >= 32 or char in '\t\n\r').strip()
                    if x and x != 'nan' else None
                )
        
        # Handle infinite values in numeric columns
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        df_clean[numeric_cols] = df_clean[numeric_cols].replace([np.inf, -np.inf], np.nan)
        
        return df_clean

class DataProcessor:
    """Professional data processing pipeline"""
    
    def __init__(self):
        self.validator = DataValidator()
    
    def process_training_data(self, raw_data: List[Dict], sport: str) -> Tuple[pd.DataFrame, DataQualityReport]:
        """Process raw training data into clean format"""
        logger.info(f"Processing training data for {sport}")
        
        # Convert to DataFrame
        df = pd.DataFrame(raw_data)
        
        # Validate data quality
        quality_report = self.validator.validate_sports_data(df, sport)
        
        if quality_report.overall_quality == DataQualityLevel.INVALID:
            raise ValidationError(f"Data quality too low for training: {quality_report.issues}")
        
        # Sanitize data
        df_clean = self.validator.sanitize_data(df, "sports")
        
        # Sport-specific processing
        if sport == 'NBA':
            df_clean = self._process_nba_data(df_clean)
        elif sport == 'NFL':
            df_clean = self._process_nfl_data(df_clean)
        elif sport == 'MLB':
            df_clean = self._process_mlb_data(df_clean)
        
        logger.info(f"Data processing completed. {len(df_clean)} records ready for training")
        
        return df_clean, quality_report
    
    def _process_nba_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """NBA-specific data processing"""
        # Calculate derived features
        if 'home_score' in df.columns and 'away_score' in df.columns:
            df['total_score'] = df['home_score'] + df['away_score']
            df['score_difference'] = df['home_score'] - df['away_score']
            df['home_win'] = (df['home_score'] > df['away_score']).astype(int)
        
        # Calculate win percentages if wins/losses available
        if 'home_wins' in df.columns and 'home_losses' in df.columns:
            df['home_win_pct'] = df['home_wins'] / (df['home_wins'] + df['home_losses'])
        
        if 'away_wins' in df.columns and 'away_losses' in df.columns:
            df['away_win_pct'] = df['away_wins'] / (df['away_wins'] + df['away_losses'])
        
        return df
    
    def _process_nfl_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """NFL-specific data processing"""
        # Calculate derived features
        if 'home_score' in df.columns and 'away_score' in df.columns:
            df['total_score'] = df['home_score'] + df['away_score']
            df['score_difference'] = df['home_score'] - df['away_score']
            df['home_win'] = (df['home_score'] > df['away_score']).astype(int)
        
        # Add scoring categories
        if 'total_score' in df.columns:
            df['high_scoring'] = (df['total_score'] > 45).astype(int)
            df['low_scoring'] = (df['total_score'] < 35).astype(int)
        
        return df
    
    def _process_mlb_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """MLB-specific data processing"""
        # Calculate derived features
        if 'home_score' in df.columns and 'away_score' in df.columns:
            df['total_score'] = df['home_score'] + df['away_score']
            df['score_difference'] = df['home_score'] - df['away_score']
            df['home_win'] = (df['home_score'] > df['away_score']).astype(int)
        
        # Pitching performance indicators
        if 'home_era' in df.columns and 'away_era' in df.columns:
            df['era_advantage'] = df['away_era'] - df['home_era']  # Positive means home has advantage
        
        return df

# Global instances
data_validator = DataValidator()
data_processor = DataProcessor()