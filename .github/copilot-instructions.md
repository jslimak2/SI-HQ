# SI-HQ (Post*9) Copilot Instructions

## Project Overview

**SI-HQ** (Post*9) is a professional sports investment platform that merges sports analytics with data science to provide intelligent betting strategies. The platform transforms traditional sports betting into strategic investment through AI-powered predictions, automated investors, and sophisticated risk management.

### Core Philosophy
**"Stop Betting. Start Investing."** - This platform treats sports outcomes as investment opportunities using data-driven approaches rather than gambling.

## Architecture & Key Concepts

### Three-Tier System Architecture

1. **Models** 🤖 - AI-powered prediction engines for sports outcomes
   - Neural networks, ensemble models, XGBoost, LightGBM
   - Located in: `dashboard/models/`
   - Registry: `dashboard/models/registry.json`

2. **Strategies** 📋 - Intelligent rules for when and how to invest
   - Conservative, aggressive, Kelly criterion, value hunting
   - Implementation: `dashboard/betting_logic.py`
   - Types: Basic, Expected Value, Model-based, etc.

3. **Investors** 🚀 - Automated investors that execute strategies 24/7
   - Risk management, bankroll management, automated execution
   - Schema: `BotSchema` in `dashboard/schemas.py`
   - Management: `dashboard/data_service.py`

## Technology Stack

### Backend (Python/Flask)
- **Main Application**: `dashboard/app.py` - Core Flask application with API endpoints
- **Data Layer**: `dashboard/data_service.py` - Centralized data management
- **ML Pipeline**: `dashboard/ml/` - Model training and inference
- **Schemas**: `dashboard/schemas.py` - Comprehensive data models with v2.0 standardization

### Frontend (Web Interface)
- **Templates**: `dashboard/templates/` - Jinja2 HTML templates
- **Static Assets**: `dashboard/static/` - CSS, JavaScript, images
- **Main Script**: `dashboard/static/scripts/scripts.js` - Client-side logic

### Data & External Services
- **Firebase Integration**: Optional Firestore database (with mock fallback)
- **Sports APIs**: Real-time sports data collection (`dashboard/real_sports_api.py`)
- **Weather API**: Environmental factors (`dashboard/weather_api.py`)

## Key Files & Directories

### Core Application Files
```
dashboard/
├── app.py                     # Main Flask application (6000+ lines)
├── schemas.py                 # v2.0 data models and validation
├── data_service.py           # Centralized data management
├── betting_logic.py          # Strategy execution logic
├── model_registry.py         # ML model management
└── config.py                 # Application configuration
```

### ML & Analytics
```
dashboard/
├── models/                   # ML model implementations
│   ├── neural_predictor.py  # Neural network models
│   ├── ensemble_predictor.py # Ensemble models
│   └── registry.json        # Model registry
├── ml/                      # ML management
│   └── model_manager.py     # Model lifecycle management
└── analytics/               # Performance analytics
```

### Documentation (Comprehensive)
- `README.md` - Main project overview
- `SCHEMA_DOCUMENTATION.md` - **v2.0** Complete schema reference
- `ARCHITECTURE_AND_SYSTEM_DESIGN.md` - Technical architecture with Mermaid diagrams
- `QUICK_REFERENCE_GUIDE.md` - 5-minute getting started guide
- `DEPLOYMENT.md` - Production deployment instructions

## Schema System (v2.0)

### Core Schema Classes
```python
# Key schemas in dashboard/schemas.py
- ModelSchema: ML model tracking with performance metrics
- BotSchema: Comprehensive investor management (renamed from "bot")
- StrategySchema: Advanced strategy configuration
- TransactionLog: Complete transaction tracking
- RiskManagement: Risk controls and limits
```

### Schema Best Practices
1. **Always use schema classes** instead of raw dictionaries
2. **Validate before storing** using `SchemaValidator`
3. **Use enums for type safety** (Sport, MarketType, BetOutcome)
4. **Leverage performance metrics** for tracking ROI and win rates

## Development Patterns

### Code Style & Conventions
- **Investor terminology**: Use "investor" instead of "bot" in new code
- **Schema-first approach**: Always use schema classes for data modeling
- **Error handling**: Comprehensive error handling with `dashboard/error_handling.py`
- **Demo vs Production**: Support both modes with clear indicators

### Common Workflows
1. **Creating an Investor**: Schema → Validation → DataService → Storage
2. **Model Training**: Data Pipeline → Feature Engineering → Training Queue → Registry
3. **Strategy Execution**: Strategy Parameters → Risk Assessment → Bet Placement → Tracking

### Testing & Quality
- **Demo Mode**: Safe testing environment with mock data
- **Production Mode**: Set `DISABLE_DEMO_MODE=true` for real data
- **Validation**: Extensive schema validation and error checking
- **Performance Tracking**: Built-in metrics and analytics

## API Design Patterns

### RESTful Endpoints
```python
# Common patterns in dashboard/app.py
@app.route('/api/strategies', methods=['POST'])
@handle_errors
@require_authentication
def create_strategy():
    # Schema validation → Business logic → Response
```

### Response Format
```python
{
    "success": boolean,
    "data": {...},
    "message": string,
    "error_details": {...}  # if applicable
}
```

## Database & Data Management

### Data Service Pattern
```python
from dashboard.data_service import data_service

# Centralized data operations
investor_id = data_service.create_bot(investor_data)
investor = data_service.get_bot(investor_id)
data_service.update_bot(investor_id, updates)
```

### Firestore Integration
- **Production**: Real Firestore database
- **Development**: Mock Firestore for testing
- **Fallback**: JSON file storage when Firebase unavailable

## Security & Production Considerations

### Authentication & Authorization
- User authentication required for sensitive operations
- Role-based access control for different user types
- API key management for external services

### Production Features
- **Environment Variables**: Secure configuration management
- **Error Monitoring**: Comprehensive logging and error tracking
- **Performance Optimization**: Caching with Redis
- **Rate Limiting**: API rate limiting and abuse prevention

## Development Guidelines

### When Working on This Codebase

1. **Understand the Domain**: Sports investment != gambling. Focus on data-driven decisions.

2. **Use Existing Patterns**: 
   - Follow the three-tier architecture (Models → Strategies → Investors)
   - Use schema classes for all data operations
   - Implement proper error handling and validation

3. **Key Considerations**:
   - Always validate user inputs and financial calculations
   - Maintain demo/production mode compatibility
   - Follow the established naming conventions
   - Update documentation when making architectural changes

4. **Common Tasks**:
   - Adding new ML models: Use `model_registry.py` patterns
   - Creating new strategies: Follow `betting_logic.py` patterns
   - Adding API endpoints: Use existing decorator patterns
   - Schema changes: Update `schemas.py` and validation logic

### Testing Approach
- Test with demo data first
- Validate schema changes thoroughly
- Test both authenticated and unauthenticated flows
- Verify financial calculations and risk management logic

## External Dependencies & APIs

### Sports Data
- NBA API, NFL Data, real-time sports feeds
- Weather API for environmental factors
- Sportsbook API integration for odds

### ML & Analytics
- TensorFlow, PyTorch, XGBoost, LightGBM
- Scikit-learn for traditional ML
- SHAP for model explainability

### Infrastructure
- Firebase for database and authentication
- Redis for caching and performance
- Flask for web framework

## File Naming & Organization

- **Models**: `dashboard/models/[model_type]_predictor.py`
- **Strategies**: Defined in `betting_logic.py`, typed in `schemas.py`
- **Templates**: `dashboard/templates/[feature]/[page].html`
- **Static Assets**: `dashboard/static/[type]/[files]`
- **Documentation**: `[FEATURE]_[TYPE].md` (e.g., `SCHEMA_DOCUMENTATION.md`)

This platform represents a sophisticated intersection of sports analytics, machine learning, and financial technology. When contributing, maintain the professional standards and data-driven approach that defines the project.