"""
Backtesting Simulation Engine
Tests model performance against historical data with realistic betting scenarios
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
from dataclasses import dataclass
from enum import Enum


class BettingStrategy(Enum):
    FIXED_AMOUNT = "fixed_amount"
    PERCENTAGE = "percentage"
    KELLY_CRITERION = "kelly_criterion"
    CONFIDENCE_BASED = "confidence_based"


@dataclass
class BacktestConfig:
    """Configuration for backtesting simulation"""
    start_date: datetime
    end_date: datetime
    initial_bankroll: float
    betting_strategy: BettingStrategy
    bet_amount: float  # Fixed amount or percentage
    min_confidence: float
    max_bet_percentage: float
    commission_rate: float
    risk_management: Dict[str, Any]


@dataclass
class BacktestResult:
    """Results from a backtesting simulation"""
    total_bets: int
    winning_bets: int
    losing_bets: int
    win_rate: float
    total_profit_loss: float
    final_bankroll: float
    roi_percentage: float
    max_drawdown: float
    max_drawdown_percentage: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int
    total_commission_paid: float
    total_amount_wagered: float
    daily_returns: List[float]
    equity_curve: List[float]
    bet_history: List[Dict[str, Any]]


class BacktestingEngine:
    """Backtesting engine for sports betting models"""
    
    def __init__(self):
        self.historical_data = {}
        self.odds_data = {}
        
    def load_historical_data(self, sport: str, data: pd.DataFrame):
        """Load historical game data for backtesting"""
        self.historical_data[sport] = data.copy()
        
    def load_odds_data(self, sport: str, odds_data: pd.DataFrame):
        """Load historical odds data"""
        self.odds_data[sport] = odds_data.copy()
        
    def generate_demo_data(self, sport: str, start_date: datetime, end_date: datetime) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Generate demo historical data for backtesting"""
        
        # Generate game schedule
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        games_data = []
        odds_data = []
        
        # Sport-specific parameters
        sport_params = {
            'NBA': {'games_per_day': 8, 'season_length': 180, 'score_range': (85, 125)},
            'NFL': {'games_per_day': 2, 'season_length': 120, 'score_range': (10, 35)},
            'MLB': {'games_per_day': 12, 'season_length': 200, 'score_range': (2, 12)},
            'NCAAF': {'games_per_day': 3, 'season_length': 100, 'score_range': (14, 42)},
            'NCAAB': {'games_per_day': 15, 'season_length': 150, 'score_range': (60, 90)}
        }
        
        params = sport_params.get(sport, sport_params['NBA'])
        
        # Team pools
        teams = {
            'NBA': ['Lakers', 'Warriors', 'Celtics', 'Heat', 'Bulls', 'Knicks', 'Nets', 'Sixers', 'Bucks', 'Rockets'],
            'NFL': ['Chiefs', 'Bills', 'Cowboys', 'Eagles', 'Patriots', '49ers', 'Packers', 'Ravens', 'Steelers', 'Rams'],
            'MLB': ['Yankees', 'Red Sox', 'Dodgers', 'Giants', 'Astros', 'Angels', 'Mets', 'Cubs', 'Braves', 'Phillies'],
            'NCAAF': ['Alabama', 'Georgia', 'Ohio State', 'Michigan', 'Texas', 'USC', 'Notre Dame', 'Oklahoma', 'Florida', 'LSU'],
            'NCAAB': ['Duke', 'UNC', 'Kentucky', 'Kansas', 'UCLA', 'Arizona', 'Syracuse', 'Villanova', 'Gonzaga', 'UConn']
        }
        
        sport_teams = teams.get(sport, teams['NBA'])
        
        game_id = 0
        for date in dates:
            # Simulate games for this date
            num_games = max(1, np.random.poisson(params['games_per_day']))
            
            for _ in range(num_games):
                # Select teams
                home_team = np.random.choice(sport_teams)
                away_team = np.random.choice([t for t in sport_teams if t != home_team])
                
                # Simulate team strengths (win percentages)
                home_strength = np.random.uniform(0.3, 0.8)
                away_strength = np.random.uniform(0.3, 0.8)
                
                # Home field advantage
                home_advantage = np.random.uniform(0.05, 0.15)
                home_win_prob = home_strength / (home_strength + away_strength) + home_advantage
                home_win_prob = min(0.9, max(0.1, home_win_prob))
                
                # Simulate game outcome
                home_wins = np.random.random() < home_win_prob
                
                # Generate scores
                score_min, score_max = params['score_range']
                home_score = np.random.randint(score_min, score_max + 1)
                away_score = np.random.randint(score_min, score_max + 1)
                
                # Adjust scores to match outcome
                if home_wins and home_score <= away_score:
                    home_score = away_score + np.random.randint(1, 8)
                elif not home_wins and away_score <= home_score:
                    away_score = home_score + np.random.randint(1, 8)
                
                # Game features
                game_data = {
                    'game_id': f"{sport}_{game_id:06d}",
                    'date': date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'home_wins': home_wins,
                    'outcome': 1 if home_wins else 0,
                    
                    # Team stats (simulated)
                    'home_win_pct': home_strength,
                    'away_win_pct': away_strength,
                    'home_team_ppg': np.random.uniform(score_min + 10, score_max - 5),
                    'away_team_ppg': np.random.uniform(score_min + 10, score_max - 5),
                    'home_pace': np.random.uniform(95, 105) if sport in ['NBA', 'NCAAB'] else None,
                    'away_pace': np.random.uniform(95, 105) if sport in ['NBA', 'NCAAB'] else None,
                    
                    # Weather (for outdoor sports)
                    'temperature': np.random.uniform(32, 85) if sport in ['NFL', 'NCAAF', 'MLB'] else None,
                    'humidity': np.random.uniform(30, 80) if sport in ['NFL', 'NCAAF', 'MLB'] else None,
                    'wind_speed': np.random.uniform(0, 20) if sport in ['NFL', 'NCAAF', 'MLB'] else None,
                    'precipitation': np.random.choice([0, 0, 0, 0.1, 0.3]) if sport in ['NFL', 'NCAAF', 'MLB'] else None
                }
                
                games_data.append(game_data)
                
                # Generate corresponding odds
                # Odds should reflect true probability with some bookmaker margin
                true_home_prob = home_win_prob
                bookmaker_prob = true_home_prob * 0.95 + 0.025  # Add vig
                
                home_odds = 1 / bookmaker_prob if bookmaker_prob > 0.5 else 1 / (1 - bookmaker_prob)
                away_odds = 1 / (1 - bookmaker_prob) if bookmaker_prob > 0.5 else 1 / bookmaker_prob
                
                # Add some noise to odds
                home_odds *= np.random.uniform(0.95, 1.05)
                away_odds *= np.random.uniform(0.95, 1.05)
                
                odds_entry = {
                    'game_id': game_data['game_id'],
                    'date': date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_odds': home_odds,
                    'away_odds': away_odds,
                    'total_over_odds': np.random.uniform(1.8, 2.2),
                    'total_under_odds': np.random.uniform(1.8, 2.2),
                    'total_line': home_score + away_score + np.random.uniform(-5, 5)
                }
                
                odds_data.append(odds_entry)
                game_id += 1
        
        games_df = pd.DataFrame(games_data)
        odds_df = pd.DataFrame(odds_data)
        
        return games_df, odds_df
    
    def run_backtest(self, model, sport: str, config: BacktestConfig) -> BacktestResult:
        """Run backtesting simulation"""
        
        # Get or generate historical data
        if sport not in self.historical_data:
            games_df, odds_df = self.generate_demo_data(sport, config.start_date, config.end_date)
            self.historical_data[sport] = games_df
            self.odds_data[sport] = odds_df
        else:
            games_df = self.historical_data[sport]
            odds_df = self.odds_data[sport]
        
        # Filter data by date range
        mask = (games_df['date'] >= config.start_date) & (games_df['date'] <= config.end_date)
        games_df = games_df[mask].copy()
        odds_df = odds_df[odds_df['game_id'].isin(games_df['game_id'])].copy()
        
        # Sort by date
        games_df = games_df.sort_values('date').reset_index(drop=True)
        
        # Initialize tracking variables
        bankroll = config.initial_bankroll
        total_bets = 0
        winning_bets = 0
        losing_bets = 0
        total_profit_loss = 0
        total_commission = 0
        total_wagered = 0
        max_bankroll = bankroll
        max_drawdown = 0
        
        bet_history = []
        daily_returns = []
        equity_curve = [bankroll]
        
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        
        wins = []
        losses = []
        
        # Process each game
        for idx, game in games_df.iterrows():
            # Get odds for this game
            game_odds = odds_df[odds_df['game_id'] == game['game_id']]
            if game_odds.empty:
                continue
            
            odds_row = game_odds.iloc[0]
            
            try:
                # Make prediction using the model
                game_features = game.to_dict()
                prediction = model.predict(game_features)
                
                confidence = prediction.get('confidence', 0.5)
                predicted_outcome = prediction.get('predicted_outcome', 'Home Win')
                home_win_prob = prediction.get('home_win_probability', 0.5)
                
                # Check if we should bet based on confidence threshold
                if confidence < config.min_confidence:
                    continue
                
                # Determine bet selection and odds
                if predicted_outcome == 'Home Win':
                    bet_selection = 'home'
                    bet_odds = odds_row['home_odds']
                    win_condition = game['home_wins']
                else:
                    bet_selection = 'away'
                    bet_odds = odds_row['away_odds']
                    win_condition = not game['home_wins']
                
                # Calculate bet amount based on strategy
                bet_amount = self._calculate_bet_amount(
                    config.betting_strategy, 
                    bankroll, 
                    config.bet_amount,
                    confidence, 
                    bet_odds, 
                    home_win_prob if bet_selection == 'home' else (1 - home_win_prob),
                    config.max_bet_percentage
                )
                
                if bet_amount <= 0 or bet_amount > bankroll:
                    continue
                
                # Place bet
                commission = bet_amount * config.commission_rate
                net_bet_amount = bet_amount - commission
                
                total_bets += 1
                total_wagered += bet_amount
                total_commission += commission
                
                # Determine outcome
                if win_condition:
                    # Win
                    payout = net_bet_amount * bet_odds
                    profit = payout - bet_amount
                    bankroll += profit
                    total_profit_loss += profit
                    winning_bets += 1
                    consecutive_wins += 1
                    consecutive_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                    wins.append(profit)
                    
                    bet_result = 'win'
                else:
                    # Loss
                    profit = -bet_amount
                    bankroll += profit
                    total_profit_loss += profit
                    losing_bets += 1
                    consecutive_losses += 1
                    consecutive_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                    losses.append(abs(profit))
                    
                    bet_result = 'loss'
                
                # Track max drawdown
                if bankroll > max_bankroll:
                    max_bankroll = bankroll
                
                current_drawdown = max_bankroll - bankroll
                if current_drawdown > max_drawdown:
                    max_drawdown = current_drawdown
                
                # Record bet
                bet_record = {
                    'date': game['date'].isoformat(),
                    'game_id': game['game_id'],
                    'teams': f"{game['away_team']} @ {game['home_team']}",
                    'bet_selection': bet_selection,
                    'bet_amount': bet_amount,
                    'odds': bet_odds,
                    'confidence': confidence,
                    'predicted_outcome': predicted_outcome,
                    'actual_outcome': 'Home Win' if game['home_wins'] else 'Away Win',
                    'result': bet_result,
                    'profit_loss': profit,
                    'bankroll_after': bankroll,
                    'commission': commission
                }
                
                bet_history.append(bet_record)
                
            except Exception as e:
                # Skip this game if prediction fails
                continue
        
        # Calculate final metrics
        win_rate = winning_bets / total_bets if total_bets > 0 else 0
        roi_percentage = (total_profit_loss / config.initial_bankroll) * 100
        max_drawdown_percentage = (max_drawdown / max_bankroll) * 100 if max_bankroll > 0 else 0
        
        # Calculate ratios
        returns = np.array(daily_returns) if daily_returns else np.array([0])
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        sortino_ratio = self._calculate_sortino_ratio(returns)
        calmar_ratio = roi_percentage / max_drawdown_percentage if max_drawdown_percentage > 0 else 0
        
        profit_factor = sum(wins) / sum(losses) if losses else float('inf') if wins else 0
        
        return BacktestResult(
            total_bets=total_bets,
            winning_bets=winning_bets,
            losing_bets=losing_bets,
            win_rate=win_rate,
            total_profit_loss=total_profit_loss,
            final_bankroll=bankroll,
            roi_percentage=roi_percentage,
            max_drawdown=max_drawdown,
            max_drawdown_percentage=max_drawdown_percentage,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            profit_factor=profit_factor,
            avg_win=np.mean(wins) if wins else 0,
            avg_loss=np.mean(losses) if losses else 0,
            largest_win=max(wins) if wins else 0,
            largest_loss=max(losses) if losses else 0,
            consecutive_wins=max_consecutive_wins,
            consecutive_losses=max_consecutive_losses,
            total_commission_paid=total_commission,
            total_amount_wagered=total_wagered,
            daily_returns=daily_returns,
            equity_curve=equity_curve,
            bet_history=bet_history
        )
    
    def _calculate_bet_amount(self, strategy: BettingStrategy, bankroll: float, 
                             base_amount: float, confidence: float, odds: float,
                             win_probability: float, max_percentage: float) -> float:
        """Calculate bet amount based on strategy"""
        
        if strategy == BettingStrategy.FIXED_AMOUNT:
            return min(base_amount, bankroll * max_percentage)
        
        elif strategy == BettingStrategy.PERCENTAGE:
            return bankroll * (base_amount / 100)
        
        elif strategy == BettingStrategy.KELLY_CRITERION:
            # Kelly formula: f = (bp - q) / b
            # where b = odds - 1, p = win probability, q = 1 - p
            b = odds - 1
            p = win_probability
            q = 1 - p
            
            if b > 0:
                kelly_fraction = (b * p - q) / b
                kelly_fraction = max(0, min(kelly_fraction, max_percentage))  # Cap at max percentage
                return bankroll * kelly_fraction
            else:
                return 0
        
        elif strategy == BettingStrategy.CONFIDENCE_BASED:
            # Scale bet amount by confidence
            confidence_factor = (confidence - 0.5) * 2  # Scale 0.5-1.0 to 0-1.0
            return bankroll * (base_amount / 100) * confidence_factor
        
        return 0
    
    def _calculate_sharpe_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) == 0 or np.std(returns) == 0:
            return 0
        return np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
    
    def _calculate_sortino_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sortino ratio (only considers downside deviation)"""
        if len(returns) == 0:
            return 0
        
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return float('inf') if np.mean(returns) > 0 else 0
        
        downside_deviation = np.std(downside_returns)
        if downside_deviation == 0:
            return 0
        
        return np.mean(returns) / downside_deviation * np.sqrt(252)
    
    def compare_strategies(self, model, sport: str, base_config: BacktestConfig,
                          strategies: List[BettingStrategy]) -> Dict[str, BacktestResult]:
        """Compare different betting strategies"""
        results = {}
        
        for strategy in strategies:
            config = BacktestConfig(
                start_date=base_config.start_date,
                end_date=base_config.end_date,
                initial_bankroll=base_config.initial_bankroll,
                betting_strategy=strategy,
                bet_amount=base_config.bet_amount,
                min_confidence=base_config.min_confidence,
                max_bet_percentage=base_config.max_bet_percentage,
                commission_rate=base_config.commission_rate,
                risk_management=base_config.risk_management
            )
            
            result = self.run_backtest(model, sport, config)
            results[strategy.value] = result
        
        return results


# Global backtesting engine instance
backtesting_engine = BacktestingEngine()