"""
Real Sports Data Collection and Historical Data Pipeline
Implements actual data collection for model training and evaluation
"""
import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass
import json

# Import actual sports APIs
try:
    import nba_api
    from nba_api.stats.endpoints import teamgamelog, leaguegamefinder
    NBA_API_AVAILABLE = True
except ImportError:
    NBA_API_AVAILABLE = False

try:
    import nfl_data_py as nfl
    NFL_API_AVAILABLE = True
except ImportError:
    NFL_API_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class GameData:
    """Real game data structure for training"""
    game_id: str
    date: datetime
    home_team: str
    away_team: str
    sport: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    game_state: str = "scheduled"  # scheduled, in_progress, completed
    
    # Team statistics
    home_stats: Optional[Dict] = None
    away_stats: Optional[Dict] = None
    
    # Weather data (for outdoor sports)
    weather: Optional[Dict] = None
    
    # Betting odds
    odds: Optional[Dict] = None


@dataclass
class HistoricalDataset:
    """Container for historical training data"""
    games: List[GameData]
    features: pd.DataFrame
    targets: pd.DataFrame
    metadata: Dict[str, Any]
    quality_score: float
    collection_date: datetime


class RealDataCollector:
    """Collects real historical and current sports data for model training"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.cache_dir = "./data_cache"
        self.ensure_cache_directory()
        
    def ensure_cache_directory(self):
        """Create cache directory if it doesn't exist"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
    def collect_nba_historical_data(self, start_date: datetime, end_date: datetime) -> HistoricalDataset:
        """Collect real NBA historical data for training"""
        games = []
        
        if not NBA_API_AVAILABLE:
            self.logger.warning("NBA API not available, generating synthetic data")
            return self._generate_synthetic_nba_data(start_date, end_date)
            
        try:
            # Get game logs for the specified period
            game_finder = leaguegamefinder.LeagueGameFinder(
                date_from_nullable=start_date.strftime('%m/%d/%Y'),
                date_to_nullable=end_date.strftime('%m/%d/%Y')
            )
            
            game_logs = game_finder.get_data_frames()[0]
            
            for _, game in game_logs.iterrows():
                game_data = GameData(
                    game_id=str(game['GAME_ID']),
                    date=pd.to_datetime(game['GAME_DATE']),
                    home_team=game['MATCHUP'].split(' vs. ')[0] if ' vs. ' in game['MATCHUP'] else game['TEAM_NAME'],
                    away_team=game['MATCHUP'].split(' @ ')[1] if ' @ ' in game['MATCHUP'] else "Unknown",
                    sport="NBA",
                    home_score=game.get('PTS', 0),
                    away_score=0,  # Will need opponent data
                    game_state="completed",
                    home_stats={
                        'points': game.get('PTS', 0),
                        'rebounds': game.get('REB', 0),
                        'assists': game.get('AST', 0),
                        'fg_pct': game.get('FG_PCT', 0.0),
                        'plus_minus': game.get('PLUS_MINUS', 0)
                    }
                )
                games.append(game_data)
                
            # Convert to features DataFrame
            features_df = self._convert_nba_games_to_features(games)
            targets_df = self._extract_nba_targets(games)
            
            return HistoricalDataset(
                games=games,
                features=features_df,
                targets=targets_df,
                metadata={
                    'sport': 'NBA',
                    'start_date': start_date,
                    'end_date': end_date,
                    'total_games': len(games),
                    'data_source': 'NBA_API'
                },
                quality_score=0.85,  # Real data gets high quality score
                collection_date=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect NBA data: {e}")
            return self._generate_synthetic_nba_data(start_date, end_date)
            
    def collect_nfl_historical_data(self, start_year: int, end_year: int) -> HistoricalDataset:
        """Collect real NFL historical data for training"""
        games = []
        
        if not NFL_API_AVAILABLE:
            self.logger.warning("NFL API not available, generating synthetic data")
            return self._generate_synthetic_nfl_data(start_year, end_year)
            
        try:
            # Get NFL schedule and game data
            for year in range(start_year, end_year + 1):
                schedule = nfl.import_schedules([year])
                
                for _, game in schedule.iterrows():
                    game_data = GameData(
                        game_id=f"{game['game_id']}",
                        date=pd.to_datetime(game['gameday']),
                        home_team=game['home_team'],
                        away_team=game['away_team'],
                        sport="NFL",
                        home_score=game.get('home_score', 0),
                        away_score=game.get('away_score', 0),
                        game_state="completed" if pd.notna(game.get('home_score')) else "scheduled",
                        home_stats={
                            'home_score': game.get('home_score', 0),
                            'spread_line': game.get('spread_line', 0.0),
                            'total_line': game.get('total_line', 0.0)
                        }
                    )
                    games.append(game_data)
                    
            # Convert to features DataFrame
            features_df = self._convert_nfl_games_to_features(games)
            targets_df = self._extract_nfl_targets(games)
            
            return HistoricalDataset(
                games=games,
                features=features_df,
                targets=targets_df,
                metadata={
                    'sport': 'NFL',
                    'start_year': start_year,
                    'end_year': end_year,
                    'total_games': len(games),
                    'data_source': 'NFL_DATA_PY'
                },
                quality_score=0.88,
                collection_date=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect NFL data: {e}")
            return self._generate_synthetic_nfl_data(start_year, end_year)
            
    def _convert_nba_games_to_features(self, games: List[GameData]) -> pd.DataFrame:
        """Convert NBA game data to feature matrix for ML training"""
        features = []
        
        for game in games:
            if game.home_stats:
                feature_row = {
                    'game_id': game.game_id,
                    'home_team': game.home_team,
                    'away_team': game.away_team,
                    'date': game.date,
                    'home_points': game.home_stats.get('points', 0),
                    'home_rebounds': game.home_stats.get('rebounds', 0),
                    'home_assists': game.home_stats.get('assists', 0),
                    'home_fg_pct': game.home_stats.get('fg_pct', 0.0),
                    'home_plus_minus': game.home_stats.get('plus_minus', 0),
                    'day_of_week': game.date.weekday(),
                    'month': game.date.month,
                    'is_back_to_back': 0,  # Would need to calculate
                }
                features.append(feature_row)
                
        return pd.DataFrame(features)
        
    def _extract_nba_targets(self, games: List[GameData]) -> pd.DataFrame:
        """Extract prediction targets from NBA games"""
        targets = []
        
        for game in games:
            if game.home_score is not None and game.away_score is not None:
                target_row = {
                    'game_id': game.game_id,
                    'home_win': 1 if game.home_score > game.away_score else 0,
                    'total_points': game.home_score + game.away_score,
                    'home_score': game.home_score,
                    'away_score': game.away_score,
                    'point_differential': game.home_score - game.away_score
                }
                targets.append(target_row)
                
        return pd.DataFrame(targets)
        
    def _convert_nfl_games_to_features(self, games: List[GameData]) -> pd.DataFrame:
        """Convert NFL game data to feature matrix for ML training"""
        features = []
        
        for game in games:
            feature_row = {
                'game_id': game.game_id,
                'home_team': game.home_team,
                'away_team': game.away_team,
                'date': game.date,
                'week': game.date.isocalendar()[1],
                'month': game.date.month,
                'is_playoff': 0,  # Would need to determine
                'spread_line': game.home_stats.get('spread_line', 0.0) if game.home_stats else 0.0,
                'total_line': game.home_stats.get('total_line', 0.0) if game.home_stats else 0.0,
            }
            features.append(feature_row)
            
        return pd.DataFrame(features)
        
    def _extract_nfl_targets(self, games: List[GameData]) -> pd.DataFrame:
        """Extract prediction targets from NFL games"""
        targets = []
        
        for game in games:
            if game.home_score is not None and game.away_score is not None:
                target_row = {
                    'game_id': game.game_id,
                    'home_win': 1 if game.home_score > game.away_score else 0,
                    'total_points': game.home_score + game.away_score,
                    'home_score': game.home_score,
                    'away_score': game.away_score,
                    'point_differential': game.home_score - game.away_score,
                    'spread_cover': 1 if (game.home_score - game.away_score) > game.home_stats.get('spread_line', 0) else 0
                }
                targets.append(target_row)
                
        return pd.DataFrame(targets)
        
    def _generate_synthetic_nba_data(self, start_date: datetime, end_date: datetime) -> HistoricalDataset:
        """Generate synthetic NBA data when real API is not available"""
        games = []
        teams = ['Lakers', 'Warriors', 'Celtics', 'Heat', 'Nets', 'Bucks', 'Suns', 'Clippers']
        
        current_date = start_date
        while current_date <= end_date:
            for i in range(0, len(teams), 2):
                if i + 1 < len(teams):
                    home_score = np.random.randint(95, 130)
                    away_score = np.random.randint(95, 130)
                    
                    game_data = GameData(
                        game_id=f"synthetic_{current_date.strftime('%Y%m%d')}_{i}",
                        date=current_date,
                        home_team=teams[i],
                        away_team=teams[i + 1],
                        sport="NBA",
                        home_score=home_score,
                        away_score=away_score,
                        game_state="completed",
                        home_stats={
                            'points': home_score,
                            'rebounds': np.random.randint(35, 55),
                            'assists': np.random.randint(20, 35),
                            'fg_pct': np.random.uniform(0.40, 0.55),
                            'plus_minus': home_score - away_score
                        }
                    )
                    games.append(game_data)
                    
            current_date += timedelta(days=1)
            
        # Convert to features and targets
        features_df = self._convert_nba_games_to_features(games)
        targets_df = self._extract_nba_targets(games)
        
        return HistoricalDataset(
            games=games,
            features=features_df,
            targets=targets_df,
            metadata={
                'sport': 'NBA',
                'start_date': start_date,
                'end_date': end_date,
                'total_games': len(games),
                'data_source': 'SYNTHETIC'
            },
            quality_score=0.60,  # Synthetic data gets lower quality score
            collection_date=datetime.now()
        )
        
    def _generate_synthetic_nfl_data(self, start_year: int, end_year: int) -> HistoricalDataset:
        """Generate synthetic NFL data when real API is not available"""
        games = []
        teams = ['Chiefs', 'Bills', 'Bengals', 'Ravens', 'Cowboys', 'Eagles', 'Giants', 'Commanders']
        
        for year in range(start_year, end_year + 1):
            week_start = datetime(year, 9, 1)  # Approximate NFL season start
            for week in range(1, 18):  # 17 weeks in NFL season
                game_date = week_start + timedelta(weeks=week-1)
                
                for i in range(0, len(teams), 2):
                    if i + 1 < len(teams):
                        home_score = np.random.randint(14, 35)
                        away_score = np.random.randint(14, 35)
                        
                        game_data = GameData(
                            game_id=f"synthetic_{year}_w{week}_{i}",
                            date=game_date,
                            home_team=teams[i],
                            away_team=teams[i + 1],
                            sport="NFL",
                            home_score=home_score,
                            away_score=away_score,
                            game_state="completed",
                            home_stats={
                                'home_score': home_score,
                                'spread_line': np.random.uniform(-7.5, 7.5),
                                'total_line': np.random.uniform(42.5, 55.5)
                            }
                        )
                        games.append(game_data)
                        
        # Convert to features and targets
        features_df = self._convert_nfl_games_to_features(games)
        targets_df = self._extract_nfl_targets(games)
        
        return HistoricalDataset(
            games=games,
            features=features_df,
            targets=targets_df,
            metadata={
                'sport': 'NFL',
                'start_year': start_year,
                'end_year': end_year,
                'total_games': len(games),
                'data_source': 'SYNTHETIC'
            },
            quality_score=0.65,
            collection_date=datetime.now()
        )
        
    def save_dataset(self, dataset: HistoricalDataset, filename: str):
        """Save historical dataset to cache"""
        cache_path = os.path.join(self.cache_dir, f"{filename}.json")
        
        # Convert to serializable format
        dataset_dict = {
            'metadata': dataset.metadata,
            'quality_score': dataset.quality_score,
            'collection_date': dataset.collection_date.isoformat(),
            'features_csv': dataset.features.to_csv(index=False),
            'targets_csv': dataset.targets.to_csv(index=False),
            'total_games': len(dataset.games)
        }
        
        with open(cache_path, 'w') as f:
            json.dump(dataset_dict, f, indent=2)
            
        self.logger.info(f"Saved dataset with {len(dataset.games)} games to {cache_path}")
        
    def load_dataset(self, filename: str) -> Optional[HistoricalDataset]:
        """Load historical dataset from cache"""
        cache_path = os.path.join(self.cache_dir, f"{filename}.json")
        
        if not os.path.exists(cache_path):
            return None
            
        try:
            with open(cache_path, 'r') as f:
                dataset_dict = json.load(f)
                
            features_df = pd.read_csv(pd.StringIO(dataset_dict['features_csv']))
            targets_df = pd.read_csv(pd.StringIO(dataset_dict['targets_csv']))
            
            return HistoricalDataset(
                games=[],  # Games not stored in cache for performance
                features=features_df,
                targets=targets_df,
                metadata=dataset_dict['metadata'],
                quality_score=dataset_dict['quality_score'],
                collection_date=datetime.fromisoformat(dataset_dict['collection_date'])
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load dataset {filename}: {e}")
            return None


# Global instance
real_data_collector = RealDataCollector()


def get_training_data(sport: str, start_date: datetime = None, end_date: datetime = None) -> HistoricalDataset:
    """Convenience function to get training data for a sport"""
    if start_date is None:
        start_date = datetime.now() - timedelta(days=365 * 2)  # 2 years of data
    if end_date is None:
        end_date = datetime.now()
        
    if sport.upper() == 'NBA':
        return real_data_collector.collect_nba_historical_data(start_date, end_date)
    elif sport.upper() == 'NFL':
        start_year = start_date.year
        end_year = end_date.year
        return real_data_collector.collect_nfl_historical_data(start_year, end_year)
    else:
        # For other sports, generate synthetic data for now
        return real_data_collector._generate_synthetic_nba_data(start_date, end_date)