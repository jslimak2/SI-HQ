"""
Data Pipeline and Preprocessing System
Handles data ingestion, cleaning, feature engineering, and validation
"""
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging


class DataSourceType(Enum):
    NBA_API = "nba_api"
    NFL_API = "nfl_api"
    MLB_API = "mlb_api"
    WEATHER_API = "weather_api"
    ODDS_API = "odds_api"
    CSV_FILE = "csv_file"
    DATABASE = "database"


class DataQuality(Enum):
    EXCELLENT = "excellent"  # >95%
    GOOD = "good"           # 85-95%
    FAIR = "fair"           # 70-85%
    POOR = "poor"           # <70%


class DataPipelineConfig:
    """Configuration for data pipeline operations"""
    
    def __init__(self):
        self.data_sources = {
            DataSourceType.NBA_API: {
                'enabled': True,
                'url': 'https://api.nba.com/v1',
                'rate_limit': 100,  # requests per hour
                'retry_attempts': 3,
                'timeout': 30
            },
            DataSourceType.NFL_API: {
                'enabled': True,
                'url': 'https://api.nfl.com/v1',
                'rate_limit': 60,
                'retry_attempts': 3,
                'timeout': 30
            },
            DataSourceType.MLB_API: {
                'enabled': True,
                'url': 'https://api.mlb.com/v1',
                'rate_limit': 80,
                'retry_attempts': 3,
                'timeout': 30
            },
            DataSourceType.WEATHER_API: {
                'enabled': True,
                'url': 'https://api.weather.com/v1',
                'rate_limit': 1000,
                'retry_attempts': 2,
                'timeout': 15
            },
            DataSourceType.ODDS_API: {
                'enabled': True,
                'url': 'https://api.odds.com/v1',
                'rate_limit': 500,
                'retry_attempts': 3,
                'timeout': 30
            }
        }
        
        self.feature_engineering = {
            'rolling_windows': [3, 5, 10],
            'momentum_indicators': True,
            'weather_integration': True,
            'opponent_adjustments': True,
            'venue_effects': True,
            'rest_day_analysis': True
        }
        
        self.data_validation = {
            'min_completeness': 0.90,
            'max_outlier_percentage': 0.05,
            'required_fields': ['team', 'opponent', 'date', 'venue'],
            'date_range_validation': True,
            'logical_consistency_checks': True
        }


class DataIngestionManager:
    """Manages data ingestion from multiple sources"""
    
    def __init__(self, config: DataPipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.ingestion_stats = {}
        
    def ingest_data(self, source_type: DataSourceType, sport: str = None) -> Dict[str, Any]:
        """Ingest data from a specific source"""
        start_time = time.time()
        
        try:
            if source_type == DataSourceType.NBA_API:
                data = self._ingest_nba_data()
            elif source_type == DataSourceType.NFL_API:
                data = self._ingest_nfl_data()
            elif source_type == DataSourceType.MLB_API:
                data = self._ingest_mlb_data()
            elif source_type == DataSourceType.WEATHER_API:
                data = self._ingest_weather_data()
            elif source_type == DataSourceType.ODDS_API:
                data = self._ingest_odds_data()
            else:
                raise ValueError(f"Unsupported data source: {source_type}")
            
            duration = time.time() - start_time
            
            result = {
                'success': True,
                'source': source_type.value,
                'records_count': len(data) if isinstance(data, list) else 1,
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            self.ingestion_stats[source_type.value] = result
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_result = {
                'success': False,
                'source': source_type.value,
                'error': str(e),
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat()
            }
            
            self.ingestion_stats[source_type.value] = error_result
            return error_result
    
    def _ingest_nba_data(self) -> List[Dict]:
        """Simulate NBA data ingestion"""
        # In real implementation, would call NBA API
        return self._generate_demo_nba_data()
    
    def _ingest_nfl_data(self) -> List[Dict]:
        """Simulate NFL data ingestion"""
        return self._generate_demo_nfl_data()
    
    def _ingest_mlb_data(self) -> List[Dict]:
        """Simulate MLB data ingestion"""
        return self._generate_demo_mlb_data()
    
    def _ingest_weather_data(self) -> List[Dict]:
        """Simulate weather data ingestion"""
        return self._generate_demo_weather_data()
    
    def _ingest_odds_data(self) -> List[Dict]:
        """Simulate odds data ingestion"""
        return self._generate_demo_odds_data()
    
    def _generate_demo_nba_data(self) -> List[Dict]:
        """Generate demo NBA data"""
        import random
        
        teams = ['Lakers', 'Warriors', 'Celtics', 'Heat', 'Bulls', 'Knicks']
        games = []
        
        for i in range(100):
            home_team = random.choice(teams)
            away_team = random.choice([t for t in teams if t != home_team])
            
            games.append({
                'game_id': f'nba_game_{i:04d}',
                'date': (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                'home_team': home_team,
                'away_team': away_team,
                'home_score': random.randint(85, 125),
                'away_score': random.randint(85, 125),
                'home_team_ppg': random.uniform(105, 120),
                'away_team_ppg': random.uniform(105, 120),
                'home_win_pct': random.uniform(0.3, 0.8),
                'away_win_pct': random.uniform(0.3, 0.8),
                'venue': f'{home_team} Arena'
            })
        
        return games
    
    def _generate_demo_nfl_data(self) -> List[Dict]:
        """Generate demo NFL data"""
        import random
        
        teams = ['Chiefs', 'Bills', 'Cowboys', 'Eagles', 'Patriots', '49ers']
        games = []
        
        for i in range(50):
            home_team = random.choice(teams)
            away_team = random.choice([t for t in teams if t != home_team])
            
            games.append({
                'game_id': f'nfl_game_{i:04d}',
                'date': (datetime.now() - timedelta(days=random.randint(0, 60))).isoformat(),
                'home_team': home_team,
                'away_team': away_team,
                'home_score': random.randint(10, 35),
                'away_score': random.randint(10, 35),
                'home_team_off_yards': random.randint(250, 450),
                'away_team_off_yards': random.randint(250, 450),
                'home_win_pct': random.uniform(0.2, 0.9),
                'away_win_pct': random.uniform(0.2, 0.9),
                'venue': f'{home_team} Stadium'
            })
        
        return games
    
    def _generate_demo_mlb_data(self) -> List[Dict]:
        """Generate demo MLB data"""
        import random
        
        teams = ['Yankees', 'Red Sox', 'Dodgers', 'Giants', 'Astros', 'Angels']
        games = []
        
        for i in range(150):
            home_team = random.choice(teams)
            away_team = random.choice([t for t in teams if t != home_team])
            
            games.append({
                'game_id': f'mlb_game_{i:04d}',
                'date': (datetime.now() - timedelta(days=random.randint(0, 90))).isoformat(),
                'home_team': home_team,
                'away_team': away_team,
                'home_score': random.randint(2, 12),
                'away_score': random.randint(2, 12),
                'home_team_era': random.uniform(3.0, 5.5),
                'away_team_era': random.uniform(3.0, 5.5),
                'home_win_pct': random.uniform(0.3, 0.7),
                'away_win_pct': random.uniform(0.3, 0.7),
                'venue': f'{home_team} Ballpark'
            })
        
        return games
    
    def _generate_demo_weather_data(self) -> List[Dict]:
        """Generate demo weather data"""
        import random
        
        weather_data = []
        for i in range(50):
            weather_data.append({
                'location': f'Stadium_{i}',
                'date': (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                'temperature': random.uniform(32, 85),
                'humidity': random.uniform(30, 80),
                'wind_speed': random.uniform(0, 20),
                'precipitation': random.choice([0, 0, 0, 0.1, 0.3, 0.5]),
                'visibility': random.uniform(5, 10),
                'pressure': random.uniform(29.5, 30.5)
            })
        
        return weather_data
    
    def _generate_demo_odds_data(self) -> List[Dict]:
        """Generate demo odds data"""
        import random
        
        odds_data = []
        for i in range(200):
            odds_data.append({
                'game_id': f'game_{i:04d}',
                'sportsbook': random.choice(['DraftKings', 'FanDuel', 'BetMGM']),
                'market_type': random.choice(['moneyline', 'spread', 'total']),
                'home_odds': random.uniform(1.5, 3.0),
                'away_odds': random.uniform(1.5, 3.0),
                'timestamp': datetime.now().isoformat()
            })
        
        return odds_data


class FeatureEngineer:
    """Handles feature engineering and data transformation"""
    
    def __init__(self, config: DataPipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def engineer_features(self, raw_data: List[Dict], sport: str) -> List[Dict]:
        """Engineer features from raw data"""
        
        enriched_data = []
        
        for record in raw_data:
            enriched_record = record.copy()
            
            # Add rolling averages
            if self.config.feature_engineering['rolling_windows']:
                enriched_record.update(self._calculate_rolling_averages(record, sport))
            
            # Add momentum indicators
            if self.config.feature_engineering['momentum_indicators']:
                enriched_record.update(self._calculate_momentum_indicators(record))
            
            # Add venue effects
            if self.config.feature_engineering['venue_effects']:
                enriched_record.update(self._calculate_venue_effects(record))
            
            # Add rest day analysis
            if self.config.feature_engineering['rest_day_analysis']:
                enriched_record.update(self._calculate_rest_effects(record))
            
            enriched_data.append(enriched_record)
        
        return enriched_data
    
    def _calculate_rolling_averages(self, record: Dict, sport: str) -> Dict:
        """Calculate rolling averages for key metrics"""
        # Simulate rolling averages
        import random
        
        rolling_features = {}
        
        if sport == 'NBA':
            for window in self.config.feature_engineering['rolling_windows']:
                rolling_features[f'home_ppg_{window}d'] = record.get('home_team_ppg', 100) + random.uniform(-5, 5)
                rolling_features[f'away_ppg_{window}d'] = record.get('away_team_ppg', 100) + random.uniform(-5, 5)
        
        elif sport == 'NFL':
            for window in self.config.feature_engineering['rolling_windows']:
                rolling_features[f'home_yards_{window}d'] = record.get('home_team_off_yards', 350) + random.uniform(-50, 50)
                rolling_features[f'away_yards_{window}d'] = record.get('away_team_off_yards', 350) + random.uniform(-50, 50)
        
        return rolling_features
    
    def _calculate_momentum_indicators(self, record: Dict) -> Dict:
        """Calculate momentum and trend indicators"""
        import random
        
        return {
            'home_momentum_score': random.uniform(-1, 1),
            'away_momentum_score': random.uniform(-1, 1),
            'home_recent_form': random.uniform(0, 1),
            'away_recent_form': random.uniform(0, 1)
        }
    
    def _calculate_venue_effects(self, record: Dict) -> Dict:
        """Calculate venue-specific effects"""
        import random
        
        return {
            'home_field_advantage': random.uniform(0.05, 0.15),
            'venue_scoring_factor': random.uniform(0.9, 1.1),
            'altitude_effect': random.choice([0, 0.02, 0.05])  # Some venues have altitude effects
        }
    
    def _calculate_rest_effects(self, record: Dict) -> Dict:
        """Calculate rest day effects"""
        import random
        
        return {
            'home_rest_days': random.randint(0, 5),
            'away_rest_days': random.randint(0, 5),
            'home_travel_distance': random.randint(0, 3000),
            'away_travel_distance': random.randint(0, 3000),
            'back_to_back_home': random.choice([True, False]),
            'back_to_back_away': random.choice([True, False])
        }


class DataValidator:
    """Validates data quality and integrity"""
    
    def __init__(self, config: DataPipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def validate_data(self, data: List[Dict]) -> Dict[str, Any]:
        """Comprehensive data validation"""
        
        validation_results = {
            'total_records': len(data),
            'valid_records': 0,
            'validation_issues': [],
            'quality_metrics': {},
            'overall_quality': DataQuality.POOR,
            'timestamp': datetime.now().isoformat()
        }
        
        if not data:
            validation_results['validation_issues'].append('No data provided')
            return validation_results
        
        # Check data completeness
        completeness_score = self._check_completeness(data)
        validation_results['quality_metrics']['completeness'] = completeness_score
        
        # Check for outliers
        outlier_percentage = self._check_outliers(data)
        validation_results['quality_metrics']['outlier_percentage'] = outlier_percentage
        
        # Check data consistency
        consistency_score = self._check_consistency(data)
        validation_results['quality_metrics']['consistency'] = consistency_score
        
        # Check required fields
        required_fields_score = self._check_required_fields(data)
        validation_results['quality_metrics']['required_fields'] = required_fields_score
        
        # Calculate valid records
        validation_results['valid_records'] = int(len(data) * min(completeness_score, consistency_score))
        
        # Determine overall quality
        overall_score = (completeness_score + consistency_score + required_fields_score) / 3
        
        if overall_score >= 0.95:
            validation_results['overall_quality'] = DataQuality.EXCELLENT
        elif overall_score >= 0.85:
            validation_results['overall_quality'] = DataQuality.GOOD
        elif overall_score >= 0.70:
            validation_results['overall_quality'] = DataQuality.FAIR
        else:
            validation_results['overall_quality'] = DataQuality.POOR
        
        validation_results['quality_score'] = overall_score
        
        return validation_results
    
    def _check_completeness(self, data: List[Dict]) -> float:
        """Check data completeness"""
        if not data:
            return 0.0
        
        total_fields = 0
        missing_fields = 0
        
        for record in data:
            for key, value in record.items():
                total_fields += 1
                if value is None or value == '' or value == 'N/A':
                    missing_fields += 1
        
        if total_fields == 0:
            return 0.0
        
        completeness = 1 - (missing_fields / total_fields)
        return max(0.0, min(1.0, completeness))
    
    def _check_outliers(self, data: List[Dict]) -> float:
        """Check for outliers in numeric data"""
        import random
        
        # Simulate outlier detection
        # In real implementation, would use statistical methods
        outlier_percentage = random.uniform(0.01, 0.08)
        
        if outlier_percentage > self.config.data_validation['max_outlier_percentage']:
            return outlier_percentage
        
        return outlier_percentage
    
    def _check_consistency(self, data: List[Dict]) -> float:
        """Check data consistency"""
        import random
        
        # Simulate consistency checks
        # In real implementation, would check logical relationships
        consistency_score = random.uniform(0.85, 0.98)
        
        return consistency_score
    
    def _check_required_fields(self, data: List[Dict]) -> float:
        """Check if required fields are present"""
        required_fields = self.config.data_validation['required_fields']
        
        if not data or not required_fields:
            return 1.0
        
        total_records = len(data)
        valid_records = 0
        
        for record in data:
            if all(field in record and record[field] is not None for field in required_fields):
                valid_records += 1
        
        return valid_records / total_records if total_records > 0 else 0.0


class DataPipeline:
    """Main data pipeline orchestrator"""
    
    def __init__(self):
        self.config = DataPipelineConfig()
        self.ingestion_manager = DataIngestionManager(self.config)
        self.feature_engineer = FeatureEngineer(self.config)
        self.validator = DataValidator(self.config)
        self.logger = logging.getLogger(__name__)
        
        self.pipeline_stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'last_run': None,
            'average_duration': 0.0
        }
    
    def run_full_pipeline(self, sport: str = None) -> Dict[str, Any]:
        """Run the complete data pipeline"""
        start_time = time.time()
        
        pipeline_result = {
            'pipeline_id': f"pipeline_{int(time.time())}",
            'start_time': datetime.now().isoformat(),
            'sport': sport,
            'stages': {},
            'success': False,
            'total_duration': 0.0
        }
        
        try:
            # Stage 1: Data Ingestion
            self.logger.info("Starting data ingestion stage")
            ingestion_results = self._run_ingestion_stage(sport)
            pipeline_result['stages']['ingestion'] = ingestion_results
            
            if not ingestion_results['success']:
                raise Exception("Data ingestion failed")
            
            # Stage 2: Feature Engineering
            self.logger.info("Starting feature engineering stage")
            feature_results = self._run_feature_engineering_stage(ingestion_results['data'], sport)
            pipeline_result['stages']['feature_engineering'] = feature_results
            
            # Stage 3: Data Validation
            self.logger.info("Starting data validation stage")
            validation_results = self._run_validation_stage(feature_results['data'])
            pipeline_result['stages']['validation'] = validation_results
            
            # Calculate total duration
            pipeline_result['total_duration'] = time.time() - start_time
            pipeline_result['end_time'] = datetime.now().isoformat()
            pipeline_result['success'] = True
            
            # Update pipeline stats
            self.pipeline_stats['total_runs'] += 1
            self.pipeline_stats['successful_runs'] += 1
            self.pipeline_stats['last_run'] = pipeline_result['end_time']
            
            # Update average duration
            self.pipeline_stats['average_duration'] = (
                (self.pipeline_stats['average_duration'] * (self.pipeline_stats['total_runs'] - 1) + 
                 pipeline_result['total_duration']) / self.pipeline_stats['total_runs']
            )
            
            self.logger.info(f"Pipeline completed successfully in {pipeline_result['total_duration']:.2f}s")
            
        except Exception as e:
            pipeline_result['total_duration'] = time.time() - start_time
            pipeline_result['end_time'] = datetime.now().isoformat()
            pipeline_result['error'] = str(e)
            
            self.pipeline_stats['total_runs'] += 1
            
            self.logger.error(f"Pipeline failed: {e}")
        
        return pipeline_result
    
    def _run_ingestion_stage(self, sport: str = None) -> Dict[str, Any]:
        """Run data ingestion stage"""
        stage_start = time.time()
        
        all_data = []
        ingestion_results = {}
        
        # Determine which sources to use based on sport
        sources_to_ingest = []
        
        if sport:
            if sport.upper() == 'NBA':
                sources_to_ingest = [DataSourceType.NBA_API, DataSourceType.ODDS_API]
            elif sport.upper() == 'NFL':
                sources_to_ingest = [DataSourceType.NFL_API, DataSourceType.WEATHER_API, DataSourceType.ODDS_API]
            elif sport.upper() == 'MLB':
                sources_to_ingest = [DataSourceType.MLB_API, DataSourceType.WEATHER_API, DataSourceType.ODDS_API]
        else:
            # Ingest from all sources
            sources_to_ingest = list(DataSourceType)
        
        # Ingest data from each source
        for source in sources_to_ingest:
            if source in self.config.data_sources and self.config.data_sources[source]['enabled']:
                result = self.ingestion_manager.ingest_data(source, sport)
                ingestion_results[source.value] = result
                
                if result['success']:
                    all_data.extend(result['data'] if isinstance(result['data'], list) else [result['data']])
        
        stage_duration = time.time() - stage_start
        
        return {
            'success': len(all_data) > 0,
            'data': all_data,
            'duration': stage_duration,
            'records_ingested': len(all_data),
            'sources_used': len(ingestion_results),
            'source_results': ingestion_results
        }
    
    def _run_feature_engineering_stage(self, raw_data: List[Dict], sport: str = None) -> Dict[str, Any]:
        """Run feature engineering stage"""
        stage_start = time.time()
        
        enriched_data = self.feature_engineer.engineer_features(raw_data, sport or 'NBA')
        
        stage_duration = time.time() - stage_start
        
        return {
            'success': True,
            'data': enriched_data,
            'duration': stage_duration,
            'records_processed': len(enriched_data),
            'features_added': len(enriched_data[0]) - len(raw_data[0]) if enriched_data and raw_data else 0
        }
    
    def _run_validation_stage(self, data: List[Dict]) -> Dict[str, Any]:
        """Run data validation stage"""
        stage_start = time.time()
        
        validation_results = self.validator.validate_data(data)
        
        stage_duration = time.time() - stage_start
        validation_results['duration'] = stage_duration
        validation_results['success'] = validation_results['overall_quality'] in [DataQuality.EXCELLENT, DataQuality.GOOD]
        
        return validation_results
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status and statistics"""
        return {
            'pipeline_stats': self.pipeline_stats,
            'config': {
                'enabled_sources': [source.value for source, config in self.config.data_sources.items() if config['enabled']],
                'feature_engineering': self.config.feature_engineering,
                'validation_thresholds': self.config.data_validation
            },
            'last_ingestion_stats': self.ingestion_manager.ingestion_stats
        }


# Global data pipeline instance
data_pipeline = DataPipeline()