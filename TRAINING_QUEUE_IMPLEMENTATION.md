# Training Queue and Multiple Model Types Implementation

This implementation adds comprehensive training queue management and multiple model types per sport to the SI-HQ sports investing dashboard.

## 🔥 Training Queue System

### Features
- **Real-time GPU resource monitoring** with memory usage and utilization tracking
- **Job queue management** supporting queued, running, and completed states
- **Progress tracking** with epoch-by-epoch updates and completion estimates
- **Interactive UI** with tabs for different job views
- **Job cancellation** for both queued and active training jobs

### API Endpoints
- `GET /api/training/queue` - Get current training queue status
- `POST /api/training/submit` - Submit new training job
- `GET /api/training/job/<job_id>` - Get specific job status
- `POST /api/training/job/<job_id>/cancel` - Cancel training job
- `GET /api/training/user-jobs` - Get all jobs for current user
- `GET /api/training/gpu-stats` - Get GPU resource statistics

### Usage
1. Navigate to "🔥 Training Queue" tab in the dashboard
2. Click "🚀 Submit Training Job" to queue new model training
3. Monitor progress in real-time across different tabs
4. View GPU utilization and resource allocation

## 🤖 Multiple Model Types per Sport

### Supported Model Types

#### 1. LSTM + Weather Models
- **Purpose**: Time-series analysis with weather integration
- **Best for**: Outdoor sports (NFL, NCAAF, MLB) where weather affects performance
- **Features**: 
  - Sequential game analysis
  - Weather impact modeling (temperature, humidity, wind, precipitation)
  - Temporal pattern recognition

#### 2. Ensemble Models
- **Purpose**: Combines multiple algorithms for robust predictions
- **Components**: Random Forest, XGBoost, Logistic Regression, Neural Networks
- **Best for**: All sports where multiple perspectives improve accuracy
- **Features**:
  - Voting strategies (soft/hard)
  - Meta-learner optimization
  - Model agreement scoring

#### 3. Neural Network Models
- **Purpose**: Deep learning for complex pattern recognition
- **Architecture**: Sport-specific hidden layer configurations
- **Best for**: Sports with complex, non-linear relationships
- **Features**:
  - Batch normalization
  - Dropout regularization
  - Sport-optimized architectures

#### 4. Statistical Models
- **Purpose**: Traditional sports analytics approach
- **Methods**: Linear regression, Poisson regression, Bayesian inference
- **Best for**: Baseline comparisons and interpretable results
- **Features**:
  - Feature selection algorithms
  - Cross-validation strategies
  - Statistical significance testing

### Sport-Specific Configurations

#### NBA/NCAAB Features
- Points per game, pace, offensive/defensive ratings
- Rebounds, field goal percentages
- Conference strength (NCAAB)

#### NFL/NCAAF Features  
- Offensive/defensive yards, points for/against
- Turnover differential, sacks
- Strength of schedule (NCAAF)
- Weather data integration

#### MLB Features
- ERA, WHIP, OPS, batting averages
- Runs per game, team statistics
- Weather effects on outdoor games

### API Endpoints
- `POST /api/models/create-sport-model` - Create sport-specific model
- `GET /api/models/sport-features/<sport>/<model_type>` - Get features for sport/model combination

## 📊 Performance Matrix & Tracking

### Features
- **Comprehensive comparison matrix** with sortable metrics
- **Parameter effectiveness analysis** showing optimal hyperparameters
- **Trending model detection** identifying improving performance
- **Sport-specific leaderboards** for performance ranking
- **Model metadata tracking** with tags and version control

### Key Metrics Tracked
- Accuracy, Precision, Recall, F1-Score, AUC-ROC
- Financial metrics: ROI, Profit/Loss, Sharpe Ratio
- Model-specific: Confidence, Predictions count
- Performance trends over time

### API Endpoints
- `GET /api/performance/matrix` - Get performance comparison matrix
- `POST /api/performance/compare` - Compare specific models
- `GET /api/performance/leaderboard/<sport>` - Get sport leaderboard
- `GET /api/performance/model-types` - Analyze by model type
- `GET /api/performance/parameters` - Parameter effectiveness analysis
- `GET /api/performance/trending` - Get trending models

## 🔧 Data Pipeline & Preprocessing

### Pipeline Stages
1. **Data Ingestion**: Multi-source API integration
2. **Feature Engineering**: Rolling averages, momentum indicators
3. **Data Validation**: Quality scoring and outlier detection
4. **Preprocessing**: Normalization and cleaning

### Features
- **Multi-source support**: NBA API, NFL API, MLB API, Weather API, Odds API
- **Quality monitoring**: Completeness, accuracy, consistency scoring
- **Feature engineering**: Sport-specific transformations
- **Pipeline orchestration**: Stage-by-stage execution with error handling

### API Endpoints
- `GET /api/data/pipeline/status` - Get pipeline status
- `POST /api/data/pipeline/run` - Execute full pipeline
- `GET /api/data/preprocessing/config` - Get preprocessing configuration
- `GET /api/data/features/explain` - Explain model features

## 📈 Backtesting Simulation Engine

### Features
- **Historical performance testing** with realistic market simulation
- **Multiple betting strategies**: Fixed amount, percentage, Kelly Criterion, confidence-based
- **Risk metrics**: Sharpe ratio, Sortino ratio, Calmar ratio, maximum drawdown
- **Strategy comparison** across different approaches
- **Detailed results**: Equity curves, bet history, win/loss analysis

### Betting Strategies
1. **Fixed Amount**: Consistent bet size
2. **Percentage**: Fixed percentage of bankroll
3. **Kelly Criterion**: Optimal bet sizing based on edge
4. **Confidence-Based**: Bet size scales with model confidence

### API Endpoints
- `POST /api/backtest/run` - Run backtesting simulation
- `POST /api/backtest/compare-strategies` - Compare betting strategies

## 🎯 Getting Started

### 1. Access Training Queue
```javascript
// Navigate to Training Queue tab
showPage('training-queue-page');

// Submit new training job
const jobData = {
    model_id: 'nba_ensemble_v1',
    sport: 'NBA',
    model_type: 'ensemble',
    epochs: 50,
    batch_size: 32,
    learning_rate: 0.001
};

fetch('/api/training/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(jobData)
});
```

### 2. Create Sport-Specific Models
```javascript
// Create LSTM weather model for NFL
const modelConfig = {
    sport: 'NFL',
    model_type: 'lstm_weather',
    model_name: 'NFL Weather LSTM v1'
};

fetch('/api/models/create-sport-model', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(modelConfig)
});
```

### 3. Run Backtesting
```javascript
// Backtest model performance
const backtestConfig = {
    model_id: 'nba_ensemble_v1',
    sport: 'NBA',
    start_date: '2024-01-01',
    end_date: '2024-02-01',
    initial_bankroll: 1000,
    betting_strategy: 'kelly_criterion',
    min_confidence: 0.65
};

fetch('/api/backtest/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(backtestConfig)
});
```

### 4. Monitor Performance
```javascript
// Get performance matrix
fetch('/api/performance/matrix?sport=NBA&days_back=30')
    .then(response => response.json())
    .then(data => {
        console.log('Performance matrix:', data.matrix);
        console.log('Summary stats:', data.summary);
    });
```

## 🔧 Configuration

### Training Queue Configuration
- Maximum concurrent jobs: 2 (configurable)
- GPU memory: 8GB (GPU 0), 6GB (GPU 1)
- Auto-refresh interval: 30 seconds
- Job retention: 7 days for completed jobs

### Model Training Defaults
- LSTM: 64 units, 2 layers, 0.3 dropout
- Ensemble: 4 models with soft voting
- Neural: Sport-specific architectures
- Statistical: L2 regularization, 5-fold CV

### Performance Thresholds
- Minimum accuracy: 55%
- Target accuracy: 70%
- Minimum ROI: 5%
- Target ROI: 15%

## 🚀 Next Steps

1. **GPU Integration**: Connect to actual GPU resources for real training
2. **Model Persistence**: Implement model saving/loading from storage
3. **Real-time Updates**: WebSocket connections for live progress
4. **Advanced Backtesting**: Monte Carlo simulations, walk-forward analysis
5. **Model Deployment**: Automated deployment pipeline for production models

## 📝 Notes

- All components include comprehensive error handling and logging
- Demo data is generated when external APIs are unavailable
- The system is designed to scale horizontally with additional GPUs
- Performance metrics are automatically tracked and stored
- UI updates in real-time with automatic refresh capabilities

This implementation provides a solid foundation for professional sports betting model development with enterprise-grade training queue management and comprehensive model performance tracking.