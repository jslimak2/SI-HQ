# SI-HQ Schema Documentation v2.0

## Overview

The SI-HQ platform now uses a comprehensive, standardized schema system for all data models. This ensures consistency, type safety, and proper validation across the entire application.

## Core Schema Components

### 1. Model Schema (`ModelSchema`)

The enhanced model schema provides complete tracking for machine learning models:

```python
ModelSchema(
    model_id: str              # Unique identifier
    name: str                  # Human-readable name
    version: str               # Semantic version (e.g., "1.2.0")
    sport: Sport               # Target sport (NBA, NFL, MLB, etc.)
    markets: List[MarketType]  # Supported betting markets
    model_type: str            # Type of model (neural_network, ensemble, etc.)
    inputs_outputs: ModelInputOutput  # Structured I/O definition
    status: ModelStatus        # Current status (training, ready, deployed)
    current_performance: PerformanceMetrics  # Latest performance
    performance_log: List[PerformanceMetrics]  # Historical performance
    hyperparameters: Dict[str, Any]  # Model configuration
    training_config: Dict[str, Any]  # Training setup
    created_by: str            # Creator user ID
    created_at: str            # Creation timestamp
    last_updated: str          # Last modification timestamp
)
```

**Key Features:**
- ✅ Comprehensive performance tracking with multiple metrics
- ✅ Structured input/output definitions with descriptions
- ✅ Version control and lineage tracking
- ✅ Multiple market support per model
- ✅ Training configuration preservation

### 2. Bot Schema (`BotSchema`)

The enhanced bot schema includes comprehensive risk management:

```python
BotSchema(
    bot_id: str                    # Unique identifier
    name: str                      # Human-readable name
    active_status: BotStatus       # Current status (active, stopped, paused)
    current_balance: float         # Current account balance
    starting_balance: float        # Initial balance
    initial_balance: float         # Original starting amount
    sport_filter: Optional[Sport]  # Sport focus (or None for all)
    market_filters: List[MarketType]  # Allowed betting markets
    assigned_model_id: Optional[str]  # Linked ML model
    assigned_strategy_id: Optional[str]  # Linked strategy
    risk_management: RiskManagement    # Risk configuration
    transaction_log: List[TransactionLog]  # All transactions
    open_wagers: List[OpenWager]       # Current open bets
    profit_loss: PerformanceMetrics   # Performance tracking
    created_by: str                # Creator user ID
    created_at: str                # Creation timestamp
    last_updated: str              # Last modification timestamp
)
```

**Risk Management Configuration:**
```python
RiskManagement(
    max_bet_percentage: float = 2.0      # Max % of balance per bet
    max_bets_per_week: int = 5           # Weekly bet limit
    max_bets_per_day: int = 2            # Daily bet limit
    stop_loss_percentage: float = 10.0   # Auto-pause threshold
    take_profit_percentage: float = 50.0 # Take profit level
    minimum_confidence: float = 60.0     # Min model confidence
    maximum_odds: float = 3.0            # Max acceptable odds
    kelly_fraction: float = 0.25         # Kelly Criterion fraction
    drawdown_limit_percentage: float = 20.0  # Max drawdown
)
```

### 3. Strategy Schema (`StrategySchema`)

The enhanced strategy schema supports complex betting logic:

```python
StrategySchema(
    strategy_id: str              # Unique identifier
    name: str                     # Human-readable name
    strategy_type: StrategyType   # Type (expected_value, conservative, etc.)
    performance_metrics: PerformanceMetrics  # Historical performance
    parameters: StrategyParameters    # Strategy configuration
    bets_per_week_allowed: int       # Weekly bet limit
    flow_definition: Dict[str, Any]  # Complex logic definition
    model_requirements: List[str]    # Required model types
    created_by: str               # Creator user ID
    is_active: bool               # Active status
    version: str                  # Strategy version
)
```

**Strategy Parameters:**
```python
StrategyParameters(
    min_confidence: float = 65.0           # Minimum model confidence
    max_bet_percentage: float = 3.0        # Max bet size
    kelly_criterion: KellyCriterionConfig  # Kelly settings
    min_odds: float = 1.5                  # Minimum acceptable odds
    max_odds: float = 3.0                  # Maximum acceptable odds
    min_expected_value: float = 5.0        # Min +EV percentage
    batch_betting_enabled: bool = False    # Batch betting mode
    batch_volume: int = 3                  # Bets per batch
)
```

## Performance Metrics System

All schemas use a standardized `PerformanceMetrics` class:

```python
PerformanceMetrics(
    accuracy: float = 0.0         # Prediction accuracy
    precision: float = 0.0        # Precision score
    recall: float = 0.0           # Recall score
    f1_score: float = 0.0         # F1 score
    auc_roc: float = 0.0          # AUC-ROC score
    win_rate: float = 0.0         # Betting win rate
    total_bets: int = 0           # Total bets placed
    winning_bets: int = 0         # Winning bets
    losing_bets: int = 0          # Losing bets
    total_profit: float = 0.0     # Total profit/loss
    total_wagered: float = 0.0    # Total amount wagered
    roi_percentage: float = 0.0   # Return on investment
    max_drawdown: float = 0.0     # Maximum drawdown
    sharpe_ratio: float = 0.0     # Risk-adjusted return
    sortino_ratio: float = 0.0    # Downside deviation ratio
    profit_factor: float = 0.0    # Gross profit / gross loss
)
```

## Enums and Type Safety

The schema system uses comprehensive enums for type safety:

### Sports
```python
class Sport(Enum):
    NBA = "NBA"
    NFL = "NFL"
    MLB = "MLB"
    NCAAF = "NCAAF"
    NCAAB = "NCAAB"
    NHL = "NHL"
```

### Bot Status
```python
class BotStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
```

### Strategy Types
```python
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
```

### Market Types
```python
class MarketType(Enum):
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTALS = "totals"
    PROP_BETS = "prop_bets"
    FUTURES = "futures"
```

## Validation System

The `SchemaValidator` class provides comprehensive validation:

```python
# Validate a model
issues = SchemaValidator.validate_model(model)
if issues:
    print(f"Validation failed: {issues}")

# Validate a bot
issues = SchemaValidator.validate_bot(bot)
if issues:
    print(f"Bot validation failed: {issues}")

# Validate a strategy
issues = SchemaValidator.validate_strategy(strategy)
if issues:
    print(f"Strategy validation failed: {issues}")
```

## Legacy Migration

The system provides automatic migration from legacy data formats:

```python
# Migrate legacy model data
legacy_model_data = {
    'id': 'old_model_001',
    'name': 'Old Model',
    'sport': 'NBA',
    'performance_metrics': {'accuracy': 0.75}
}
migrated_model = migrate_legacy_model(legacy_model_data)

# Migrate legacy bot data
legacy_bot_data = {
    'id': 'old_bot_001',
    'name': 'Old Bot',
    'status': 'active',
    'bet_percentage': 3.0
}
migrated_bot = migrate_legacy_bot(legacy_bot_data)
```

## Data Service Integration

The `DataService` class provides centralized data management:

```python
from dashboard.data_service import data_service

# Create a bot
bot_id = data_service.create_bot({
    'name': 'My Bot',
    'current_balance': 1000.0,
    'sport_filter': 'NBA',
    'created_by': 'user123'
})

# Retrieve a bot
bot = data_service.get_bot(bot_id)

# Update a bot
updated_bot = data_service.update_bot(bot_id, {
    'current_balance': 1200.0
})

# Add a transaction
transaction = TransactionLog(
    transaction_id='tx_001',
    timestamp=datetime.now().isoformat(),
    game_id='game_001',
    teams='Lakers vs Warriors',
    sport=Sport.NBA,
    market_type=MarketType.MONEYLINE,
    bet_type='Home Win',
    amount=50.0,
    odds=1.85,
    predicted_outcome='Lakers Win',
    result=BetOutcome.WIN,
    profit_loss=42.50
)
data_service.add_bot_transaction(bot_id, transaction)
```

## API Integration

New API endpoints support schema operations:

### Schema Validation
```
POST /api/schema/validate
{
    "schema_type": "bot",
    "data": {
        "bot_id": "test_bot",
        "name": "Test Bot",
        "current_balance": 1000.0,
        "created_by": "user123"
    }
}
```

### Schema Information
```
GET /api/schema/info
```

Returns information about available schemas, required fields, and enums.

## Best Practices

### 1. Always Use Schema Classes
```python
# ✅ Good
bot = BotSchema(
    bot_id="bot_001",
    name="My Bot",
    current_balance=1000.0,
    created_by="user123"
)

# ❌ Avoid raw dictionaries
bot_data = {
    'id': 'bot_001',
    'name': 'My Bot',
    'balance': 1000.0
}
```

### 2. Validate Before Storing
```python
# Always validate before saving
issues = SchemaValidator.validate_bot(bot)
if issues:
    raise ValueError(f"Invalid bot: {issues}")

# Then save
bot_id = data_service.create_bot(bot.to_dict())
```

### 3. Use Enums for Type Safety
```python
# ✅ Good
bot.active_status = BotStatus.ACTIVE
bot.sport_filter = Sport.NBA

# ❌ Avoid strings
bot.status = "active"  # Could have typos
bot.sport = "nba"      # Inconsistent casing
```

### 4. Leverage Performance Metrics
```python
# Update performance metrics properly
performance = PerformanceMetrics(
    total_bets=100,
    winning_bets=68,
    total_profit=2500.0,
    total_wagered=10000.0
)
performance.win_rate = performance.winning_bets / performance.total_bets
performance.roi_percentage = (performance.total_profit / performance.total_wagered) * 100
```

## Migration Guide

### From Legacy to v2.0 Schema

1. **Identify Legacy Data**: Look for dictionaries with old field names
2. **Use Migration Functions**: Apply `migrate_legacy_*` functions
3. **Validate Results**: Always validate migrated data
4. **Update Storage**: Save using new schema format
5. **Update UI**: Ensure frontend handles new field names

### Example Migration
```python
# Legacy data
legacy_data = {
    'id': 'bot_001',
    'status': 'active',
    'balance': 1500.0,
    'bet_percentage': 3.0
}

# Migrate
migrated_bot = migrate_legacy_bot(legacy_data)

# Validate
issues = SchemaValidator.validate_bot(migrated_bot)
if not issues:
    # Save new format
    data_service.create_bot(migrated_bot.to_dict())
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure relative imports (`from .schemas import ...`)
2. **Enum Validation**: Check enum values match exactly
3. **Type Mismatches**: Validate data types before creating schemas
4. **Missing Fields**: Use schema validation to identify required fields

### Debugging

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check schema structure
print(bot.to_dict())

# Validate step by step
issues = SchemaValidator.validate_bot(bot)
for issue in issues:
    print(f"Issue: {issue}")
```

## Future Enhancements

- **GraphQL Integration**: Add GraphQL schema generation
- **API Versioning**: Support multiple schema versions simultaneously
- **Real-time Validation**: WebSocket-based live validation
- **Schema Evolution**: Automated schema migration tools
- **Performance Optimization**: Caching and indexing for large datasets

---

**Schema Version**: 2.0.0  
**Last Updated**: December 2024  
**Compatibility**: SI-HQ v2.0+