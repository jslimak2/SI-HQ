# Post*9 Sports Investment Platform - Architecture & System Design

**MAJOR UPDATE - September 14, 2025**: Enhanced with real model training infrastructure, GPU support, weather integration, and professional data pipeline.

## Overview

Post*9 is a sophisticated sports investment platform that combines advanced machine learning with automated trading strategies. The platform enables users to create, test, and deploy data-driven investment strategies across multiple sports markets.

### 🆕 Recent Infrastructure Enhancements

1. **Real Model Training**: GPU infrastructure with TensorFlow/PyTorch support
2. **Weather API Integration**: OpenWeatherMap integration for LSTM weather models
3. **Professional Data Pipeline**: Modular, toggleable data sources with job processing
4. **Safety-First Investment**: Manual export-place-confirm workflow (live betting disabled)
5. **Real Data Collection**: NBA/NFL API integration with synthetic fallbacks

## Core Concepts Explained

### 🤖 What is a Model?

A **Model** in Post*9 is a machine learning algorithm trained to predict sports outcomes and calculate betting probabilities. Models analyze historical data, team statistics, player performance, and even weather conditions to make intelligent predictions.

**Types of Models:**
- **🆕 LSTM + Weather Models**: Now with real weather API integration for outdoor sports
- **🆕 Ensemble Models**: Enhanced with real training data and GPU acceleration
- **🆕 Neural Network Models**: TensorFlow/PyTorch implementation with actual GPU training
- **Statistical Models**: Traditional statistical approaches using real historical data

**Enhanced Model Capabilities:**
- Real NBA/NFL historical data analysis
- Weather impact modeling for outdoor sports
- GPU-accelerated training with performance metrics
- Real-time model evaluation and comparison
- Professional feature engineering pipeline

### 📋 What is a Strategy?

A **Strategy** in Post*9 defines the logic and rules for making investment decisions. It's the "brain" that decides when, how much, and what type of bets to place based on model predictions and market conditions.

**Strategy Components:**
- **Betting Logic**: Rules for when to place bets (e.g., "bet when confidence > 75%")
- **Risk Management**: Position sizing, bankroll management, maximum bet limits
- **Market Selection**: Which types of bets to focus on (spread, totals, moneyline)
- **Filters**: Conditions that must be met before placing bets
- **Kelly Criterion**: Mathematical optimization for bet sizing

**Strategy Examples:**
- "High Confidence Favorites": Only bet on favorites when model confidence exceeds 80%
- "Value Hunter": Target bets where our predicted probability significantly differs from market odds
- "Weather Edge": Focus on outdoor games where weather gives us an informational advantage

### 🚀 What is a Bot/Automated Investor?

A **Bot** (also called an Automated Investor) is the execution engine that brings everything together. It's an automated system that applies a specific strategy using designated models to make real investment decisions.

**Bot Responsibilities:**
- **Execute Strategies**: Automatically apply strategy rules to live market data
- **Monitor Markets**: Continuously scan for betting opportunities
- **Risk Management**: Enforce position limits and bankroll management
- **Performance Tracking**: Record all decisions and track profitability
- **Model Integration**: Use assigned ML models to generate predictions

**Bot Configuration:**
- Assigned to specific sports (NBA, NFL, MLB, etc.)
- Configured for specific markets (spread, totals, moneyline)
- Linked to one strategy and one or more models
- Given a starting balance and risk parameters
- Set with betting frequency and position size limits

## System Architecture

```mermaid
graph TB
    subgraph "User Interface Layer"
        UI[Web Dashboard]
        API[REST API]
        DOC[API Documentation]
    end
    
    subgraph "Application Core"
        AUTH[Authentication & Security]
        CONFIG[Configuration Manager]
        ERROR[Error Handling]
        VALID[Data Validation]
    end
    
    subgraph "Strategy Management"
        STRAT_BUILDER[Visual Strategy Builder]
        STRAT_MANAGER[Strategy Manager]
        STRAT_STORE[Strategy Storage]
    end
    
    subgraph "Bot Management"
        BOT_MANAGER[Bot Manager]
        BOT_ENGINE[Execution Engine]
        BOT_MONITOR[Performance Monitor]
    end
    
    subgraph "ML & Analytics"
        MODEL_REG[Model Registry]
        ML_MANAGER[ML Model Manager]
        NEURAL[Neural Predictor]
        ENSEMBLE[Ensemble Predictor]
        ANALYTICS[Advanced Analytics]
    end
    
    subgraph "Data Layer"
        DATA_PIPELINE[Data Pipeline]
        SPORTS_API[Sports Data APIs]
        WEATHER_API[Weather APIs]
        FIRESTORE[Firebase Firestore]
        CACHE[Redis Cache]
    end
    
    subgraph "Trading & Backtesting"
        BACKTEST[Backtesting Engine]
        SIM[Betting Simulation]
        PERF[Performance Matrix]
    end
    
    UI --> API
    API --> AUTH
    API --> STRAT_MANAGER
    API --> BOT_MANAGER
    API --> ML_MANAGER
    
    STRAT_BUILDER --> STRAT_MANAGER
    STRAT_MANAGER --> STRAT_STORE
    
    BOT_ENGINE --> STRAT_MANAGER
    BOT_ENGINE --> ML_MANAGER
    BOT_ENGINE --> SIM
    
    ML_MANAGER --> MODEL_REG
    ML_MANAGER --> NEURAL
    ML_MANAGER --> ENSEMBLE
    
    DATA_PIPELINE --> SPORTS_API
    DATA_PIPELINE --> WEATHER_API
    DATA_PIPELINE --> FIRESTORE
    DATA_PIPELINE --> CACHE
    
    ANALYTICS --> DATA_PIPELINE
    BACKTEST --> SIM
    BACKTEST --> PERF
    
    BOT_MONITOR --> PERF
```

## Component Architecture

```mermaid
graph LR
    subgraph "Models Layer"
        LSTM[LSTM + Weather Model]
        ENS[Ensemble Model]
        NN[Neural Network]
        STAT[Statistical Model]
    end
    
    subgraph "Strategy Layer"
        RULES[Betting Rules]
        RISK[Risk Management]
        KELLY[Kelly Criterion]
        FILTERS[Market Filters]
    end
    
    subgraph "Bot Execution Layer"
        BOT1[NBA Bot]
        BOT2[NFL Bot]
        BOT3[MLB Bot]
        BOT4[Multi-Sport Bot]
    end
    
    subgraph "Data Sources"
        NBA_API[NBA API]
        NFL_API[NFL API]
        MLB_API[MLB API]
        WEATHER[Weather API]
    end
    
    LSTM --> BOT1
    ENS --> BOT2
    NN --> BOT3
    STAT --> BOT4
    
    RULES --> BOT1
    RULES --> BOT2
    RULES --> BOT3
    RULES --> BOT4
    
    NBA_API --> LSTM
    NFL_API --> ENS
    MLB_API --> NN
    WEATHER --> LSTM
    WEATHER --> ENS
```

## User Flow Diagrams

### Strategy Creation Flow

```mermaid
flowchart TD
    START([User Starts]) --> CHOICE{Strategy Creation Method}
    
    CHOICE -->|Simple| EDIT[Quick Edit Form]
    CHOICE -->|Advanced| BUILDER[Visual Strategy Builder]
    
    EDIT --> PARAMS[Set Parameters:<br/>- Confidence Threshold<br/>- Max Bet %<br/>- Min Expected Value]
    BUILDER --> VISUAL[Drag & Drop Components:<br/>- IF/THEN Logic<br/>- Market Analysis<br/>- Risk Rules]
    
    PARAMS --> VALIDATE[Validate Strategy]
    VISUAL --> VALIDATE
    
    VALIDATE --> SAVE[Save Strategy]
    SAVE --> ASSIGN[Assign to Bot]
    ASSIGN --> ACTIVATE[Activate Bot]
    ACTIVATE --> MONITOR[Monitor Performance]
```

### Bot Trading Flow

```mermaid
flowchart TD
    START([Bot Starts]) --> SCAN[Scan Markets]
    SCAN --> FETCH[Fetch Game Data]
    FETCH --> PREDICT[Generate ML Predictions]
    
    PREDICT --> STRATEGY[Apply Strategy Rules]
    STRATEGY --> DECISION{Bet Criteria Met?}
    
    DECISION -->|No| WAIT[Wait for Next Game]
    DECISION -->|Yes| CALCULATE[Calculate Bet Size]
    
    CALCULATE --> RISK_CHECK{Risk Limits OK?}
    RISK_CHECK -->|No| WAIT
    RISK_CHECK -->|Yes| EXECUTE[Execute Bet]
    
    EXECUTE --> RECORD[Record Transaction]
    RECORD --> UPDATE[Update Balance]
    UPDATE --> WAIT
    
    WAIT --> SCAN
```

### Model Training Workflow

```mermaid
flowchart TD
    START([Initiate Training]) --> SELECT[Select Model Type & Sport]
    SELECT --> COLLECT[Collect Training Data]
    COLLECT --> PROCESS[Data Processing & Feature Engineering]
    
    PROCESS --> SPLIT[Train/Validation/Test Split]
    SPLIT --> TRAIN[Train Model]
    TRAIN --> VALIDATE[Validate Performance]
    
    VALIDATE --> GOOD{Performance Satisfactory?}
    GOOD -->|No| TUNE[Hyperparameter Tuning]
    TUNE --> TRAIN
    
    GOOD -->|Yes| REGISTER[Register in Model Registry]
    REGISTER --> DEPLOY[Deploy to Production]
    DEPLOY --> MONITOR[Monitor Model Performance]
    
    MONITOR --> DRIFT{Performance Drift?}
    DRIFT -->|Yes| RETRAIN[Schedule Retraining]
    DRIFT -->|No| CONTINUE[Continue Monitoring]
    
    RETRAIN --> COLLECT
    CONTINUE --> MONITOR
```

## Data Flow Architecture

```mermaid
flowchart LR
    subgraph "External APIs"
        NBA[NBA API]
        NFL[NFL API]
        MLB[MLB API]
        WEATHER[Weather API]
    end
    
    subgraph "Data Ingestion"
        COLLECTOR[Data Collector]
        VALIDATOR[Data Validator]
        PROCESSOR[Data Processor]
    end
    
    subgraph "Storage"
        FIRESTORE[(Firestore)]
        REDIS[(Redis Cache)]
        MODELS[(Model Storage)]
    end
    
    subgraph "ML Pipeline"
        FEATURE[Feature Engineering]
        TRAINING[Model Training]
        INFERENCE[Real-time Inference]
    end
    
    subgraph "Application Layer"
        BOTS[Trading Bots]
        DASHBOARD[Dashboard]
        ANALYTICS[Analytics Engine]
    end
    
    NBA --> COLLECTOR
    NFL --> COLLECTOR
    MLB --> COLLECTOR
    WEATHER --> COLLECTOR
    
    COLLECTOR --> VALIDATOR
    VALIDATOR --> PROCESSOR
    PROCESSOR --> FIRESTORE
    PROCESSOR --> REDIS
    
    FIRESTORE --> FEATURE
    FEATURE --> TRAINING
    TRAINING --> MODELS
    MODELS --> INFERENCE
    
    REDIS --> INFERENCE
    INFERENCE --> BOTS
    FIRESTORE --> ANALYTICS
    ANALYTICS --> DASHBOARD
    BOTS --> DASHBOARD
```

## Technology Stack

```mermaid
graph TB
    subgraph "Frontend"
        HTML[HTML5]
        CSS[TailwindCSS]
        JS[JavaScript]
        CHARTS[Chart.js/Plotly]
    end
    
    subgraph "Backend"
        FLASK[Flask Web Framework]
        PYTHON[Python 3.12]
        GUNICORN[Gunicorn WSGI]
    end
    
    subgraph "Machine Learning"
        TF[TensorFlow/Keras]
        SKLEARN[Scikit-learn]
        TORCH[PyTorch]
        XGBOOST[XGBoost]
        LIGHTGBM[LightGBM]
    end
    
    subgraph "Data & Analytics"
        PANDAS[Pandas]
        NUMPY[NumPy]
        MATPLOTLIB[Matplotlib]
        SEABORN[Seaborn]
        PLOTLY[Plotly]
    end
    
    subgraph "Database & Storage"
        FIRESTORE[Google Firestore]
        REDIS[Redis Cache]
        FIREBASE[Firebase Admin]
    end
    
    subgraph "APIs & External"
        NBA_API[NBA API]
        NFL_API[NFL Data API]
        WEATHER_API[Weather API]
        REST[REST APIs]
    end
    
    HTML --> FLASK
    CSS --> HTML
    JS --> HTML
    CHARTS --> JS
    
    FLASK --> PYTHON
    GUNICORN --> FLASK
    
    PYTHON --> TF
    PYTHON --> SKLEARN
    PYTHON --> TORCH
    PYTHON --> PANDAS
    
    FLASK --> FIRESTORE
    FLASK --> REDIS
    FIRESTORE --> FIREBASE
    
    FLASK --> NBA_API
    FLASK --> NFL_API
    FLASK --> WEATHER_API
```

## Security Architecture

```mermaid
flowchart TD
    subgraph "Security Layers"
        AUTH[Authentication]
        AUTHZ[Authorization]
        RATE[Rate Limiting]
        VALID[Input Validation]
        SANITIZE[Data Sanitization]
    end
    
    subgraph "External Threats"
        DDoS[DDoS Attacks]
        INJECTION[SQL/NoSQL Injection]
        XSS[Cross-Site Scripting]
        CSRF[CSRF Attacks]
    end
    
    USER[User Request] --> AUTH
    AUTH --> AUTHZ
    AUTHZ --> RATE
    RATE --> VALID
    VALID --> SANITIZE
    SANITIZE --> APP[Application Logic]
    
    DDoS -.->|Blocked by| RATE
    INJECTION -.->|Blocked by| VALID
    XSS -.->|Blocked by| SANITIZE
    CSRF -.->|Blocked by| AUTH
```

## Performance Monitoring

```mermaid
graph LR
    subgraph "Performance Metrics"
        LATENCY[Response Latency]
        THROUGHPUT[Request Throughput]
        ERROR_RATE[Error Rate]
        CPU[CPU Usage]
        MEMORY[Memory Usage]
    end
    
    subgraph "Business Metrics"
        BOT_PERF[Bot Performance]
        MODEL_ACC[Model Accuracy]
        ROI[Return on Investment]
        SHARPE[Sharpe Ratio]
        DRAWDOWN[Max Drawdown]
    end
    
    subgraph "Monitoring Tools"
        DASHBOARD[Performance Dashboard]
        ALERTS[Alert System]
        LOGS[Centralized Logging]
        METRICS[Metrics Collection]
    end
    
    LATENCY --> METRICS
    THROUGHPUT --> METRICS
    ERROR_RATE --> METRICS
    CPU --> METRICS
    MEMORY --> METRICS
    
    BOT_PERF --> DASHBOARD
    MODEL_ACC --> DASHBOARD
    ROI --> DASHBOARD
    SHARPE --> DASHBOARD
    DRAWDOWN --> DASHBOARD
    
    METRICS --> ALERTS
    DASHBOARD --> ALERTS
    LOGS --> ALERTS
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Development"
        DEV[Development Environment]
        TESTING[Testing Environment]
    end
    
    subgraph "Production"
        LOAD_BALANCER[Load Balancer]
        WEB1[Web Server 1]
        WEB2[Web Server 2]
        WEB3[Web Server 3]
    end
    
    subgraph "Data Tier"
        FIRESTORE[Firestore]
        REDIS[Redis Cluster]
        BACKUP[Backup Systems]
    end
    
    subgraph "External Services"
        CDN[Content Delivery Network]
        MONITORING[Monitoring Services]
        LOGGING[Logging Services]
    end
    
    DEV --> TESTING
    TESTING --> LOAD_BALANCER
    
    LOAD_BALANCER --> WEB1
    LOAD_BALANCER --> WEB2
    LOAD_BALANCER --> WEB3
    
    WEB1 --> FIRESTORE
    WEB2 --> FIRESTORE
    WEB3 --> FIRESTORE
    
    WEB1 --> REDIS
    WEB2 --> REDIS
    WEB3 --> REDIS
    
    FIRESTORE --> BACKUP
    
    CDN --> LOAD_BALANCER
    MONITORING --> WEB1
    MONITORING --> WEB2
    MONITORING --> WEB3
```

## Getting Started

### For Developers

1. **Understand the Architecture**: Review the diagrams above to understand how components interact
2. **Set Up Development Environment**: Install dependencies from `requirements.txt`
3. **Explore the Code**: Start with `dashboard/app.py` as the main entry point
4. **Review Models**: Check `dashboard/models/` for ML implementations
5. **Study Strategies**: Look at `dashboard/betting_logic.py` for strategy execution

### For Users

1. **Create Your Strategy**: Use either the Quick Edit form or Visual Strategy Builder
2. **Choose Your Models**: Select appropriate ML models for your target sports
3. **Configure Your Bot**: Set up automated investors with proper risk parameters
4. **Monitor Performance**: Use the dashboard to track your bot's trading performance
5. **Iterate and Improve**: Analyze results and refine your strategies

## Key Files and Directories

- `dashboard/app.py` - Main Flask application
- `dashboard/models/` - ML model implementations
- `dashboard/betting_logic.py` - Strategy execution logic
- `dashboard/analytics/` - Advanced analytics and statistics
- `dashboard/ml/` - Machine learning management
- `dashboard/templates/` - Web interface templates
- `dashboard/static/` - CSS, JavaScript, and assets

## Contributing

When contributing to Post*9, please follow these guidelines:

1. Understand the component you're working on using the architecture diagrams
2. Ensure changes don't break the model → strategy → bot workflow
3. Add appropriate tests for new functionality
4. Update documentation when adding new features
5. Follow the existing code style and patterns

---

**Last Updated**: 9/13/2025