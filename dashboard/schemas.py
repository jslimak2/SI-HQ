"""
Comprehensive data schemas for the SI-HQ sports investment platform.
This module defines the standardized data models used throughout the application.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
import json


class ModelStatus(Enum):
    TRAINING = "training"
    READY = "ready"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class InvestorStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class StrategyType(Enum):
    BASIC = "basic"
    EXPECTED_VALUE = "expected_value"
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"
    RECOVERY = "recovery"
    VALUE_HUNTING = "value_hunting"
    ARBITRAGE = "arbitrage"
    MODEL_BASED = "model_based"
    KELLY_CRITERION = "kelly_criterion"


class Sport(Enum):
    NBA = "NBA"
    NFL = "NFL"
    MLB = "MLB"
    NCAAF = "NCAAF"
    NCAAB = "NCAAB"
    NHL = "NHL"


class MarketType(Enum):
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTALS = "totals"
    PROP_BETS = "prop_bets"
    FUTURES = "futures"


class BetOutcome(Enum):
    WIN = "W"
    LOSS = "L"
    PUSH = "P"
    PENDING = "PENDING"
    CANCELLED = "C"


@dataclass
class PerformanceMetrics:
    """Standardized performance tracking metrics"""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    auc_roc: float = 0.0
    win_rate: float = 0.0
    total_bets: int = 0
    winning_bets: int = 0
    losing_bets: int = 0
    total_profit: float = 0.0
    total_wagered: float = 0.0
    roi_percentage: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    profit_factor: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceMetrics':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ModelInputOutput:
    """Defines model inputs and outputs structure"""
    inputs: List[str] = field(default_factory=list)
    input_types: Dict[str, str] = field(default_factory=dict)
    input_descriptions: Dict[str, str] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    output_types: Dict[str, str] = field(default_factory=dict)
    output_descriptions: Dict[str, str] = field(default_factory=dict)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelInputOutput':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ModelSchema:
    """Complete model data schema"""
    # Core identification
    model_id: str
    name: str
    version: str
    
    # Sport and market information
    sport: Sport
    markets: List[MarketType] = field(default_factory=list)
    
    # Model structure
    model_type: str = ""
    inputs_outputs: ModelInputOutput = field(default_factory=ModelInputOutput)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    description: str = ""
    
    # Training and performance
    timestamp_trained: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    performance_log: List[PerformanceMetrics] = field(default_factory=list)
    current_performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    
    # Status and lifecycle
    status: ModelStatus = ModelStatus.TRAINING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = ""
    
    # Technical details
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    training_config: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None
    file_checksum: Optional[str] = None
    architecture: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with enum handling"""
        data = asdict(self)
        # Convert enums to their values
        data['sport'] = self.sport.value
        data['markets'] = [market.value for market in self.markets]
        data['status'] = self.status.value
        data['current_performance'] = self.current_performance.to_dict()
        data['performance_log'] = [perf.to_dict() for perf in self.performance_log]
        data['inputs_outputs'] = self.inputs_outputs.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelSchema':
        """Create from dictionary with enum handling"""
        # Handle enums
        if 'sport' in data and isinstance(data['sport'], str):
            data['sport'] = Sport(data['sport'])
        if 'markets' in data and isinstance(data['markets'], list):
            data['markets'] = [MarketType(market) for market in data['markets']]
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = ModelStatus(data['status'])
        
        # Handle complex objects
        if 'current_performance' in data and isinstance(data['current_performance'], dict):
            data['current_performance'] = PerformanceMetrics.from_dict(data['current_performance'])
        if 'performance_log' in data and isinstance(data['performance_log'], list):
            data['performance_log'] = [PerformanceMetrics.from_dict(perf) for perf in data['performance_log']]
        if 'inputs_outputs' in data and isinstance(data['inputs_outputs'], dict):
            data['inputs_outputs'] = ModelInputOutput.from_dict(data['inputs_outputs'])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RiskManagement:
    """Risk management configuration"""
    max_bet_percentage: float = 2.0
    max_bets_per_week: int = 5
    max_bets_per_day: int = 2
    stop_loss_percentage: float = 10.0
    take_profit_percentage: float = 50.0
    minimum_confidence: float = 60.0
    maximum_odds: float = 3.0
    kelly_fraction: float = 0.25
    drawdown_limit_percentage: float = 20.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RiskManagement':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TransactionLog:
    """Individual transaction/bet record"""
    transaction_id: str
    timestamp: str
    game_id: str
    teams: str
    sport: Sport
    market_type: MarketType
    bet_type: str
    amount: float
    odds: float
    predicted_outcome: str
    actual_outcome: Optional[str] = None
    result: BetOutcome = BetOutcome.PENDING
    profit_loss: float = 0.0
    confidence: float = 0.0
    model_used: Optional[str] = None
    strategy_used: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['sport'] = self.sport.value
        data['market_type'] = self.market_type.value
        data['result'] = self.result.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionLog':
        if 'sport' in data and isinstance(data['sport'], str):
            data['sport'] = Sport(data['sport'])
        if 'market_type' in data and isinstance(data['market_type'], str):
            data['market_type'] = MarketType(data['market_type'])
        if 'result' in data and isinstance(data['result'], str):
            data['result'] = BetOutcome(data['result'])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class OpenWager:
    """Currently open/pending wager"""
    wager_id: str
    timestamp_placed: str
    game_id: str
    teams: str
    sport: Sport
    market_type: MarketType
    bet_type: str
    amount: float
    odds: float
    predicted_outcome: str
    expected_return: float
    confidence: float
    model_used: Optional[str] = None
    strategy_used: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['sport'] = self.sport.value
        data['market_type'] = self.market_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OpenWager':
        if 'sport' in data and isinstance(data['sport'], str):
            data['sport'] = Sport(data['sport'])
        if 'market_type' in data and isinstance(data['market_type'], str):
            data['market_type'] = MarketType(data['market_type'])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class BotSchema:
    """Complete automated investor/bot data schema"""
    # Core identification
    bot_id: str
    name: str
    
    # Status and control
    active_status: InvestorStatus = InvestorStatus.STOPPED
    
    # Financial tracking
    current_balance: float = 1000.0
    starting_balance: float = 1000.0
    initial_balance: float = 1000.0
    
    # Transaction and performance history
    transaction_log: List[TransactionLog] = field(default_factory=list)
    open_wagers: List[OpenWager] = field(default_factory=list)
    profit_loss: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    
    # Strategy and model assignments
    assigned_model_id: Optional[str] = None
    assigned_strategy_id: Optional[str] = None
    
    # Configuration
    sport_filter: Optional[Sport] = None
    market_filters: List[MarketType] = field(default_factory=list)
    risk_management: RiskManagement = field(default_factory=RiskManagement)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = ""
    tags: List[str] = field(default_factory=list)
    description: str = ""
    
    # Operational tracking
    bets_this_week: int = 0
    week_reset_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['active_status'] = self.active_status.value
        data['sport_filter'] = self.sport_filter.value if self.sport_filter else None
        data['market_filters'] = [market.value for market in self.market_filters]
        data['risk_management'] = self.risk_management.to_dict()
        data['profit_loss'] = self.profit_loss.to_dict()
        data['transaction_log'] = [tx.to_dict() for tx in self.transaction_log]
        data['open_wagers'] = [wager.to_dict() for wager in self.open_wagers]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BotSchema':
        # Handle enums
        if 'active_status' in data and isinstance(data['active_status'], str):
            data['active_status'] = InvestorStatus(data['active_status'])
        if 'sport_filter' in data and data['sport_filter'] and isinstance(data['sport_filter'], str):
            data['sport_filter'] = Sport(data['sport_filter'])
        if 'market_filters' in data and isinstance(data['market_filters'], list):
            data['market_filters'] = [MarketType(market) for market in data['market_filters']]
        
        # Handle complex objects
        if 'risk_management' in data and isinstance(data['risk_management'], dict):
            data['risk_management'] = RiskManagement.from_dict(data['risk_management'])
        if 'profit_loss' in data and isinstance(data['profit_loss'], dict):
            data['profit_loss'] = PerformanceMetrics.from_dict(data['profit_loss'])
        if 'transaction_log' in data and isinstance(data['transaction_log'], list):
            data['transaction_log'] = [TransactionLog.from_dict(tx) for tx in data['transaction_log']]
        if 'open_wagers' in data and isinstance(data['open_wagers'], list):
            data['open_wagers'] = [OpenWager.from_dict(wager) for wager in data['open_wagers']]
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class KellyCriterionConfig:
    """Kelly Criterion configuration parameters"""
    enabled: bool = True
    fractional_kelly: float = 0.25  # Use 25% of full Kelly by default
    max_kelly_bet: float = 0.05  # Never bet more than 5% even if Kelly says so
    min_edge: float = 0.02  # Minimum 2% edge required
    confidence_adjustment: bool = True  # Adjust based on model confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KellyCriterionConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StrategyParameters:
    """Flexible strategy parameters"""
    min_confidence: float = 65.0
    max_bet_percentage: float = 3.0
    kelly_criterion: KellyCriterionConfig = field(default_factory=KellyCriterionConfig)
    min_odds: float = 1.5
    max_odds: float = 3.0
    min_expected_value: float = 5.0
    batch_betting_enabled: bool = False
    batch_volume: int = 3
    additional_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['kelly_criterion'] = self.kelly_criterion.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyParameters':
        if 'kelly_criterion' in data and isinstance(data['kelly_criterion'], dict):
            data['kelly_criterion'] = KellyCriterionConfig.from_dict(data['kelly_criterion'])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StrategySchema:
    """Complete strategy data schema"""
    # Core identification
    strategy_id: str
    name: str
    strategy_type: StrategyType
    
    # Performance tracking
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    average_performance: float = 0.0  # Simplified average for quick access
    
    # Betting configuration
    parameters: StrategyParameters = field(default_factory=StrategyParameters)
    bets_per_week_allowed: int = 7
    
    # Advanced configuration
    flow_definition: Dict[str, Any] = field(default_factory=dict)  # For complex strategy logic
    model_requirements: List[str] = field(default_factory=list)  # Required model types
    
    # Metadata
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Lifecycle management
    is_active: bool = True
    version: str = "1.0.0"
    parent_strategy_id: Optional[str] = None  # For strategy evolution
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['strategy_type'] = self.strategy_type.value
        data['performance_metrics'] = self.performance_metrics.to_dict()
        data['parameters'] = self.parameters.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategySchema':
        # Handle enums
        if 'strategy_type' in data and isinstance(data['strategy_type'], str):
            data['strategy_type'] = StrategyType(data['strategy_type'])
        
        # Handle complex objects
        if 'performance_metrics' in data and isinstance(data['performance_metrics'], dict):
            data['performance_metrics'] = PerformanceMetrics.from_dict(data['performance_metrics'])
        if 'parameters' in data and isinstance(data['parameters'], dict):
            data['parameters'] = StrategyParameters.from_dict(data['parameters'])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SchemaValidator:
    """Validates schema objects and provides helpful error messages"""
    
    @staticmethod
    def validate_model(model: ModelSchema) -> List[str]:
        """Validate model schema and return list of issues"""
        issues = []
        
        if not model.model_id:
            issues.append("Model ID is required")
        if not model.name:
            issues.append("Model name is required")
        if not model.version:
            issues.append("Model version is required")
        if not model.sport:
            issues.append("Model sport is required")
        if model.current_performance.accuracy < 0 or model.current_performance.accuracy > 1:
            issues.append("Model accuracy must be between 0 and 1")
        
        return issues
    
    @staticmethod
    def validate_bot(bot: BotSchema) -> List[str]:
        """Validate bot schema and return list of issues"""
        issues = []
        
        if not bot.bot_id:
            issues.append("Bot ID is required")
        if not bot.name:
            issues.append("Bot name is required")
        if bot.current_balance < 0:
            issues.append("Bot balance cannot be negative")
        if bot.risk_management.max_bet_percentage <= 0 or bot.risk_management.max_bet_percentage > 100:
            issues.append("Max bet percentage must be between 0.1 and 100")
        if bot.risk_management.max_bets_per_week <= 0:
            issues.append("Max bets per week must be positive")
        
        return issues
    
    @staticmethod
    def validate_strategy(strategy: StrategySchema) -> List[str]:
        """Validate strategy schema and return list of issues"""
        issues = []
        
        if not strategy.strategy_id:
            issues.append("Strategy ID is required")
        if not strategy.name:
            issues.append("Strategy name is required")
        if not strategy.strategy_type:
            issues.append("Strategy type is required")
        if strategy.parameters.min_confidence < 0 or strategy.parameters.min_confidence > 100:
            issues.append("Min confidence must be between 0 and 100")
        if strategy.bets_per_week_allowed <= 0:
            issues.append("Bets per week allowed must be positive")
        
        return issues


# Utility functions for schema management
def migrate_legacy_model(legacy_data: Dict[str, Any]) -> ModelSchema:
    """Migrate legacy model data to new schema"""
    # Map legacy fields to new schema
    model_data = {
        'model_id': legacy_data.get('id', legacy_data.get('model_id', '')),
        'name': legacy_data.get('name', ''),
        'version': legacy_data.get('version', '1.0.0'),
        'sport': Sport(legacy_data.get('sport', 'NBA')),
        'model_type': legacy_data.get('model_type', 'unknown'),
        'status': ModelStatus(legacy_data.get('status', 'training')),
        'created_by': legacy_data.get('created_by', ''),
        'description': legacy_data.get('description', ''),
        'hyperparameters': legacy_data.get('hyperparameters', {}),
        'training_config': legacy_data.get('training_config', {}),
        'created_at': legacy_data.get('created_at', datetime.now().isoformat()),
        'last_updated': legacy_data.get('last_updated', datetime.now().isoformat())
    }
    
    # Handle performance metrics
    if 'performance_metrics' in legacy_data:
        model_data['current_performance'] = PerformanceMetrics.from_dict(legacy_data['performance_metrics'])
    
    return ModelSchema.from_dict(model_data)


def migrate_legacy_bot(legacy_data: Dict[str, Any]) -> BotSchema:
    """Migrate legacy bot data to new schema"""
    bot_data = {
        'bot_id': legacy_data.get('id', legacy_data.get('bot_id', '')),
        'name': legacy_data.get('name', ''),
        'current_balance': legacy_data.get('current_balance', 1000.0),
        'starting_balance': legacy_data.get('starting_balance', legacy_data.get('initial_balance', 1000.0)),
        'initial_balance': legacy_data.get('initial_balance', 1000.0),
        'assigned_model_id': legacy_data.get('assigned_model_id'),
        'assigned_strategy_id': legacy_data.get('strategy_id', legacy_data.get('linked_strategy_id')),
        'created_by': legacy_data.get('created_by', ''),
        'created_at': legacy_data.get('created_at', datetime.now().isoformat()),
        'last_updated': legacy_data.get('last_updated', datetime.now().isoformat())
    }
    
    # Handle status mapping
    if 'status' in legacy_data:
        status_mapping = {
            'active': InvestorStatus.ACTIVE,
            'stopped': InvestorStatus.STOPPED,
            'paused': InvestorStatus.PAUSED
        }
        bot_data['active_status'] = status_mapping.get(legacy_data['status'], InvestorStatus.STOPPED)
    
    # Handle sport filter
    if 'sport' in legacy_data and legacy_data['sport']:
        try:
            bot_data['sport_filter'] = Sport(legacy_data['sport'])
        except ValueError:
            pass  # Invalid sport, leave as None
    
    # Handle risk management from legacy fields
    risk_data = {}
    if 'bet_percentage' in legacy_data:
        risk_data['max_bet_percentage'] = legacy_data['bet_percentage']
    if 'max_bets_per_week' in legacy_data:
        risk_data['max_bets_per_week'] = legacy_data['max_bets_per_week']
    
    if risk_data:
        bot_data['risk_management'] = RiskManagement.from_dict(risk_data)
    
    return BotSchema.from_dict(bot_data)


def migrate_legacy_strategy(legacy_data: Dict[str, Any]) -> StrategySchema:
    """Migrate legacy strategy data to new schema"""
    strategy_data = {
        'strategy_id': legacy_data.get('id', legacy_data.get('strategy_id', '')),
        'name': legacy_data.get('name', ''),
        'description': legacy_data.get('description', ''),
        'created_by': legacy_data.get('created_by', ''),
        'created_at': legacy_data.get('created_at', datetime.now().isoformat()),
        'last_updated': legacy_data.get('updated_at', legacy_data.get('last_updated', datetime.now().isoformat()))
    }
    
    # Handle strategy type
    type_mapping = {
        'basic': StrategyType.BASIC,
        'expected_value': StrategyType.EXPECTED_VALUE,
        'conservative': StrategyType.CONSERVATIVE,
        'aggressive': StrategyType.AGGRESSIVE,
        'recovery': StrategyType.RECOVERY,
        'value_hunting': StrategyType.VALUE_HUNTING,
        'arbitrage': StrategyType.ARBITRAGE,
        'model_based': StrategyType.MODEL_BASED
    }
    strategy_data['strategy_type'] = type_mapping.get(legacy_data.get('type', 'basic'), StrategyType.BASIC)
    
    # Handle parameters
    if 'parameters' in legacy_data:
        strategy_data['parameters'] = StrategyParameters.from_dict(legacy_data['parameters'])
    
    # Handle flow definition
    if 'flow_definition' in legacy_data:
        strategy_data['flow_definition'] = legacy_data['flow_definition']
    
    return StrategySchema.from_dict(strategy_data)