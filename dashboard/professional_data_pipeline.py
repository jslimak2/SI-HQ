"""
Professional Data Processing Infrastructure
Modular pipeline for interchangeable data sources and model training
"""
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
from concurrent.futures import ThreadPoolExecutor, Future
import queue

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """Available data source types"""
    ODDS_API = "odds_api"
    WEATHER_API = "weather_api"
    NBA_STATS = "nba_stats"
    NFL_STATS = "nfl_stats"
    MLB_STATS = "mlb_stats"
    INJURY_REPORTS = "injury_reports"
    HISTORICAL_DATA = "historical_data"
    BETTING_LINES = "betting_lines"
    PLAYER_PROPS = "player_props"
    TEAM_NEWS = "team_news"


class JobStatus(Enum):
    """Job processing status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DataSourceConfig:
    """Configuration for a data source"""
    name: str
    source_type: DataSourceType
    enabled: bool = True
    priority: int = 1  # Higher = more important
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingJob:
    """A data processing job"""
    job_id: str
    sport: str
    model_type: str
    data_sources: List[DataSourceType]
    target_date: datetime
    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    status: JobStatus = JobStatus.PENDING
    progress_percent: int = 0
    error_message: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    estimated_completion: Optional[datetime] = None
    
    def add_log(self, message: str):
        """Add a log entry with timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.logs.append(f"[{timestamp}] {message}")


class DataSource:
    """Base class for data sources"""
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.logger = logging.getLogger(f"DataSource.{config.name}")
        self.last_request_time = 0
        
    def is_enabled(self) -> bool:
        """Check if this data source is enabled"""
        return self.config.enabled
        
    def enforce_rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        min_interval = 60.0 / self.config.rate_limit_per_minute
        
        time_since_last = current_time - self.last_request_time
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
        
    def fetch_data(self, sport: str, game_date: datetime, **kwargs) -> Dict[str, Any]:
        """Fetch data from this source - to be implemented by subclasses"""
        raise NotImplementedError
        
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate fetched data"""
        return data is not None and len(data) > 0


class OddsAPISource(DataSource):
    """The Odds API data source"""
    
    def fetch_data(self, sport: str, game_date: datetime, **kwargs) -> Dict[str, Any]:
        """Fetch odds data from The Odds API"""
        try:
            self.enforce_rate_limit()
            
            # Import The Odds API integration
            from real_sports_api import real_sports_service
            
            if real_sports_service and real_sports_service.odds_provider:
                sport_mapping = {
                    'NBA': 'basketball_nba',
                    'NFL': 'americanfootball_nfl',
                    'MLB': 'baseball_mlb'
                }
                
                api_sport = sport_mapping.get(sport, 'basketball_nba')
                games = real_sports_service.get_current_games(api_sport)
                
                return {
                    'source': 'odds_api',
                    'sport': sport,
                    'games': games,
                    'fetch_time': datetime.now(),
                    'quality_score': 0.9 if games else 0.0
                }
            else:
                # Fallback to mock data
                return {
                    'source': 'odds_api_mock',
                    'sport': sport,
                    'games': self._generate_mock_odds(sport),
                    'fetch_time': datetime.now(),
                    'quality_score': 0.6
                }
                
        except Exception as e:
            self.logger.error(f"Failed to fetch odds data: {e}")
            return {}
            
    def _generate_mock_odds(self, sport: str) -> List[Dict]:
        """Generate mock odds data"""
        import random
        
        teams = {
            'NBA': ['Lakers', 'Warriors', 'Celtics', 'Heat'],
            'NFL': ['Chiefs', 'Bills', 'Cowboys', 'Eagles'],
            'MLB': ['Yankees', 'Dodgers', 'Red Sox', 'Astros']
        }
        
        sport_teams = teams.get(sport, teams['NBA'])
        games = []
        
        for i in range(0, len(sport_teams), 2):
            if i + 1 < len(sport_teams):
                game = {
                    'id': f"mock_{sport}_{i}",
                    'home_team': sport_teams[i],
                    'away_team': sport_teams[i + 1],
                    'home_odds': round(random.uniform(1.5, 3.0), 2),
                    'away_odds': round(random.uniform(1.5, 3.0), 2),
                    'over_under': round(random.uniform(200, 250), 1) if sport == 'NBA' else round(random.uniform(42, 55), 1)
                }
                games.append(game)
                
        return games


class WeatherAPISource(DataSource):
    """Weather API data source"""
    
    def fetch_data(self, sport: str, game_date: datetime, **kwargs) -> Dict[str, Any]:
        """Fetch weather data"""
        try:
            self.enforce_rate_limit()
            
            from weather_api import weather_service
            
            venue = kwargs.get('venue', 'Unknown Venue')
            weather_data = weather_service.get_weather_for_game(venue, game_date)
            
            if weather_data:
                return {
                    'source': 'weather_api',
                    'venue': venue,
                    'weather': weather_data.__dict__,
                    'fetch_time': datetime.now(),
                    'quality_score': 0.8 if not weather_data.is_dome else 0.9
                }
            else:
                return {}
                
        except Exception as e:
            self.logger.error(f"Failed to fetch weather data: {e}")
            return {}


class StatsAPISource(DataSource):
    """Generic sports statistics API source"""
    
    def fetch_data(self, sport: str, game_date: datetime, **kwargs) -> Dict[str, Any]:
        """Fetch team/player statistics"""
        try:
            self.enforce_rate_limit()
            
            # Import real data collection
            from real_data_collection import real_data_collector
            
            if sport == 'NBA':
                end_date = game_date
                start_date = end_date - timedelta(days=30)  # Last 30 days
                dataset = real_data_collector.collect_nba_historical_data(start_date, end_date)
            elif sport == 'NFL':
                dataset = real_data_collector.collect_nfl_historical_data(game_date.year, game_date.year)
            else:
                # Generate synthetic data for other sports
                dataset = real_data_collector._generate_synthetic_nba_data(
                    game_date - timedelta(days=30), game_date
                )
                
            return {
                'source': f'{sport.lower()}_stats',
                'sport': sport,
                'dataset': {
                    'features': dataset.features.to_dict('records') if not dataset.features.empty else [],
                    'targets': dataset.targets.to_dict('records') if not dataset.targets.empty else [],
                    'metadata': dataset.metadata,
                    'quality_score': dataset.quality_score
                },
                'fetch_time': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to fetch stats data: {e}")
            return {}


class InjuryReportsSource(DataSource):
    """Injury reports data source"""
    
    def fetch_data(self, sport: str, game_date: datetime, **kwargs) -> Dict[str, Any]:
        """Fetch injury reports (mock implementation)"""
        try:
            self.enforce_rate_limit()
            
            # Mock injury data - in production, this would connect to injury APIs
            import random
            
            players = ['Player A', 'Player B', 'Player C', 'Player D']
            injuries = []
            
            for player in players:
                if random.random() < 0.3:  # 30% chance of injury
                    injury = {
                        'player': player,
                        'injury_type': random.choice(['Ankle', 'Knee', 'Shoulder', 'Back']),
                        'status': random.choice(['Questionable', 'Doubtful', 'Out']),
                        'expected_return': None if random.random() < 0.5 else (game_date + timedelta(days=random.randint(1, 14))).isoformat()
                    }
                    injuries.append(injury)
                    
            return {
                'source': 'injury_reports',
                'sport': sport,
                'injuries': injuries,
                'fetch_time': datetime.now(),
                'quality_score': 0.7  # Mock data gets lower score
            }
            
        except Exception as e:
            self.logger.error(f"Failed to fetch injury data: {e}")
            return {}


class DataPipelineManager:
    """Main data pipeline manager"""
    
    def __init__(self):
        self.data_sources = {}
        self.jobs = {}
        self.job_queue = queue.PriorityQueue()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.running_jobs = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize default data sources
        self._initialize_default_sources()
        
    def _initialize_default_sources(self):
        """Initialize default data sources"""
        
        # The Odds API
        odds_config = DataSourceConfig(
            name="TheOddsAPI",
            source_type=DataSourceType.ODDS_API,
            enabled=True,
            priority=5,
            rate_limit_per_minute=10,
            api_key=os.getenv('ODDS_API_KEY'),
            base_url="https://api.the-odds-api.com/v4"
        )
        self.register_data_source(OddsAPISource(odds_config))
        
        # Weather API
        weather_config = DataSourceConfig(
            name="WeatherAPI",
            source_type=DataSourceType.WEATHER_API,
            enabled=True,
            priority=3,
            rate_limit_per_minute=60,
            api_key=os.getenv('WEATHER_API_KEY')
        )
        self.register_data_source(WeatherAPISource(weather_config))
        
        # Sports Stats APIs
        for sport in ['NBA', 'NFL', 'MLB']:
            stats_config = DataSourceConfig(
                name=f"{sport}Stats",
                source_type=getattr(DataSourceType, f"{sport}_STATS"),
                enabled=True,
                priority=4,
                rate_limit_per_minute=30
            )
            self.register_data_source(StatsAPISource(stats_config))
            
        # Injury Reports
        injury_config = DataSourceConfig(
            name="InjuryReports",
            source_type=DataSourceType.INJURY_REPORTS,
            enabled=True,
            priority=2,
            rate_limit_per_minute=20
        )
        self.register_data_source(InjuryReportsSource(injury_config))
        
    def register_data_source(self, source: DataSource):
        """Register a data source"""
        source_key = f"{source.config.source_type.value}_{source.config.name}"
        self.data_sources[source_key] = source
        self.logger.info(f"Registered data source: {source.config.name}")
        
    def toggle_data_source(self, source_type: DataSourceType, enabled: bool):
        """Enable/disable a data source type"""
        for key, source in self.data_sources.items():
            if source.config.source_type == source_type:
                source.config.enabled = enabled
                self.logger.info(f"{'Enabled' if enabled else 'Disabled'} data source: {source.config.name}")
                
    def submit_job(self, sport: str, model_type: str, data_sources: List[DataSourceType], 
                   user_id: str, target_date: datetime = None) -> str:
        """Submit a data processing job"""
        
        if target_date is None:
            target_date = datetime.now()
            
        job_id = f"job_{int(time.time())}_{len(self.jobs)}"
        
        job = ProcessingJob(
            job_id=job_id,
            sport=sport,
            model_type=model_type,
            data_sources=data_sources,
            target_date=target_date,
            user_id=user_id,
            estimated_completion=datetime.now() + timedelta(minutes=10)
        )
        
        self.jobs[job_id] = job
        
        # Add to processing queue (priority based on data source priorities)
        max_priority = max([self._get_source_priority(ds) for ds in data_sources], default=1)
        self.job_queue.put((max_priority, time.time(), job_id))
        
        job.add_log(f"Job submitted with {len(data_sources)} data sources")
        self.logger.info(f"Submitted job {job_id} for {sport} {model_type}")
        
        # Start processing if not already running
        self._start_job_processor()
        
        return job_id
        
    def _get_source_priority(self, source_type: DataSourceType) -> int:
        """Get priority for a data source type"""
        for source in self.data_sources.values():
            if source.config.source_type == source_type:
                return source.config.priority
        return 1
        
    def _start_job_processor(self):
        """Start the job processing thread if not already running"""
        if not hasattr(self, '_processor_running') or not self._processor_running:
            self._processor_running = True
            self.executor.submit(self._process_jobs)
            
    def _process_jobs(self):
        """Process jobs from the queue"""
        while True:
            try:
                # Get next job from queue (blocks if empty)
                priority, timestamp, job_id = self.job_queue.get(timeout=30)
                
                if job_id in self.jobs:
                    job = self.jobs[job_id]
                    if job.status == JobStatus.PENDING:
                        self._process_single_job(job)
                        
            except queue.Empty:
                # No jobs for 30 seconds, stop processor
                self._processor_running = False
                break
            except Exception as e:
                self.logger.error(f"Error in job processor: {e}")
                
    def _process_single_job(self, job: ProcessingJob):
        """Process a single job"""
        try:
            job.status = JobStatus.RUNNING
            job.add_log("Starting data collection...")
            
            collected_data = {}
            total_sources = len(job.data_sources)
            completed_sources = 0
            
            for source_type in job.data_sources:
                try:
                    job.add_log(f"Fetching data from {source_type.value}...")
                    
                    # Find enabled source of this type
                    source = self._find_enabled_source(source_type)
                    
                    if source:
                        data = source.fetch_data(
                            sport=job.sport,
                            game_date=job.target_date,
                            job_id=job.job_id
                        )
                        
                        if source.validate_data(data):
                            collected_data[source_type.value] = data
                            job.add_log(f"✓ Successfully fetched {source_type.value}")
                        else:
                            job.add_log(f"⚠ Invalid data from {source_type.value}")
                            
                    else:
                        job.add_log(f"⚠ No enabled source for {source_type.value}")
                        
                    completed_sources += 1
                    job.progress_percent = int((completed_sources / total_sources) * 80)  # 80% for data collection
                    
                except Exception as e:
                    job.add_log(f"✗ Failed to fetch {source_type.value}: {str(e)}")
                    
            # Process collected data
            job.add_log("Processing collected data...")
            processed_data = self._process_collected_data(collected_data, job)
            
            job.results = processed_data
            job.progress_percent = 100
            job.status = JobStatus.COMPLETED
            job.add_log("Job completed successfully!")
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.add_log(f"Job failed: {str(e)}")
            self.logger.error(f"Job {job.job_id} failed: {e}")
            
    def _find_enabled_source(self, source_type: DataSourceType) -> Optional[DataSource]:
        """Find an enabled source of the given type"""
        for source in self.data_sources.values():
            if source.config.source_type == source_type and source.is_enabled():
                return source
        return None
        
    def _process_collected_data(self, collected_data: Dict[str, Any], job: ProcessingJob) -> Dict[str, Any]:
        """Process and combine collected data"""
        
        processed = {
            'job_id': job.job_id,
            'sport': job.sport,
            'model_type': job.model_type,
            'collection_time': datetime.now(),
            'sources_used': list(collected_data.keys()),
            'data_quality_scores': {},
            'combined_features': {},
            'training_ready': False
        }
        
        # Extract quality scores
        for source_name, data in collected_data.items():
            processed['data_quality_scores'][source_name] = data.get('quality_score', 0.0)
            
        # Combine features for model training
        if job.model_type.lower() == 'lstm_weather':
            # For LSTM models, prioritize weather and historical data
            weather_data = collected_data.get('weather_api', {})
            stats_data = collected_data.get(f'{job.sport.lower()}_stats', {})
            
            if weather_data and stats_data:
                processed['combined_features'] = {
                    'weather_features': weather_data.get('weather', {}),
                    'team_stats': stats_data.get('dataset', {}),
                    'feature_count': 20  # Estimated feature count
                }
                processed['training_ready'] = True
                
        elif job.model_type.lower() == 'ensemble':
            # For ensemble models, use all available data
            all_features = {}
            for source_name, data in collected_data.items():
                all_features[source_name] = data
                
            processed['combined_features'] = all_features
            processed['training_ready'] = len(collected_data) >= 2
            
        # Calculate overall data quality
        if processed['data_quality_scores']:
            avg_quality = sum(processed['data_quality_scores'].values()) / len(processed['data_quality_scores'])
            processed['overall_quality'] = avg_quality
        else:
            processed['overall_quality'] = 0.0
            
        return processed
        
    def get_job_status(self, job_id: str) -> Optional[ProcessingJob]:
        """Get the status of a job"""
        return self.jobs.get(job_id)
        
    def get_user_jobs(self, user_id: str) -> List[ProcessingJob]:
        """Get all jobs for a user"""
        return [job for job in self.jobs.values() if job.user_id == user_id]
        
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            if job.status in [JobStatus.PENDING, JobStatus.RUNNING]:
                job.status = JobStatus.CANCELLED
                job.add_log("Job cancelled by user")
                return True
        return False
        
    def get_data_source_status(self) -> Dict[str, Any]:
        """Get status of all data sources"""
        status = {}
        
        for key, source in self.data_sources.items():
            status[key] = {
                'name': source.config.name,
                'type': source.config.source_type.value,
                'enabled': source.config.enabled,
                'priority': source.config.priority,
                'rate_limit': source.config.rate_limit_per_minute,
                'has_api_key': bool(source.config.api_key),
                'last_request': source.last_request_time
            }
            
        return status


# Global pipeline manager instance
pipeline_manager = DataPipelineManager()


def submit_data_job(sport: str, model_type: str, data_sources: List[str], user_id: str) -> str:
    """Convenience function to submit a data processing job"""
    # Convert string source names to enums
    source_enums = []
    for source_name in data_sources:
        try:
            source_enum = DataSourceType(source_name.lower())
            source_enums.append(source_enum)
        except ValueError:
            logger.warning(f"Unknown data source: {source_name}")
            
    return pipeline_manager.submit_job(sport, model_type, source_enums, user_id)


def get_available_data_sources() -> List[str]:
    """Get list of available data source types"""
    return [source.value for source in DataSourceType]


def toggle_data_source(source_name: str, enabled: bool) -> bool:
    """Toggle a data source on/off"""
    try:
        source_type = DataSourceType(source_name.lower())
        pipeline_manager.toggle_data_source(source_type, enabled)
        return True
    except ValueError:
        return False