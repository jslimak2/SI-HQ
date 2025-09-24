# Post9: Sports Investment Platform - ML Model Management System

## Overview

Post9 is a comprehensive platform that enables users to develop, train, and deploy machine learning models for sports investment strategies. The platform provides end-to-end workflow capabilities from model parameter tuning to automated investor recommendations.

## Key Features Implemented

### 1. Model Parameter Tuning Interface ⚙️

**Location**: ML Dashboard → Model Training Section → Parameter Tuning Panel

**Capabilities**:
- Interactive sliders for adjusting model parameters:
  - Confidence Threshold (50-95%)
  - Maximum Bet Percentage (1-10%)
  - Minimum Expected Value (0-20%)
  - Kelly Criterion Fraction (0.1-1.0)
- Real-time parameter value display
- Apply changes functionality with immediate feedback
- Model performance metrics update after parameter changes

**How to Use**:
1. Navigate to ML Dashboard (`/ml`)
2. Go to "Model Training" section
3. Select a trained model from the dropdown
4. Adjust parameters using sliders
5. Click "Apply Parameter Changes"

### 2. Model Training Center 🎯

**Location**: ML Dashboard → Model Training Section

**Capabilities**:
- Support for multiple model types:
  - Statistical Models (basic correlation-based)
  - Ensemble Models (multiple algorithms combined)
  - Neural Networks (LSTM, Transformer)
- Configurable training parameters:
  - Sport selection (NBA, NFL, MLB)
  - Training sample size (100-10,000)
  - Neural network specific: epochs, batch size
- Real-time training progress tracking
- Training logs with timestamps
- Model performance metrics upon completion

**How to Use**:
1. Select model type and sport
2. Configure training parameters
3. Click "Start Training"
4. Monitor progress in real-time
5. View results and model performance

### 3. Enhanced Model Gallery 🏛️

**Location**: ML Dashboard → Model Gallery Section

**Capabilities**:
- Comprehensive model listing with filtering by sport
- Model performance metrics display:
  - Accuracy percentage
  - Feature count
  - Training samples used
  - Creation date and status
- Action buttons for each model:
  - **Tune**: Load model into parameter tuning interface
  - **Predict**: Use model for making predictions
  - **Save**: Save current model state to gallery
- Create new model functionality

**How to Use**:
1. Navigate to "Model Gallery" section
2. Filter models by sport if needed
3. View model details and performance
4. Use action buttons to interact with models

### 4. Model-Strategy Integration 🔗

**API Endpoints**:
- `POST /api/strategies/model-based` - Create strategies powered by ML models
- `POST /api/investors/<bot_id>/assign-model` - Assign models to investors
- `GET /api/investors/<bot_id>/model-recommendations` - Get ML-powered recommendations

**Capabilities**:
- Create betting strategies that use specific ML models
- Assign trained models to automated investors
- Generate recommendations based on model predictions
- Configure strategy parameters (confidence thresholds, bet sizing)

### 5. Investor Recommendation System 🤖

**Enhanced Features**:
- ML model-powered pick generation
- Confidence-based filtering
- Real-time game analysis using trained models
- Kelly Criterion-based bet sizing
- Integration with existing investor management system

**How It Works**:
1. Assign a trained model to a investor
2. Investor queries model for predictions on current games
3. Model returns predictions with confidence scores
4. Investor filters predictions based on confidence thresholds
5. Investor generates recommended bets with optimal sizing

## API Reference

### Model Management APIs

#### Get Model Gallery
```
GET /api/models/gallery?sport=NBA&type=statistical
```
Returns list of available models with filtering options.

#### Create New Model
```
POST /api/models/create
{
  "sport": "NBA",
  "model_type": "statistical",
  "description": "Custom NBA predictor"
}
```

#### Train Model
```
POST /api/ml/basic/train
{
  "sport": "NBA",
  "num_samples": 1000,
  "model_type": "statistical"
}
```

#### Make Prediction
```
POST /api/ml/demo/predict
{
  "sport": "NBA",
  "home_win_pct": 0.65,
  "away_win_pct": 0.55
}
```

#### Get Model Performance
```
GET /api/models/{model_id}/performance
```

### Strategy-Model Integration APIs

#### Create Model-Based Strategy
```
POST /api/strategies/model-based
{
  "user_id": "user123",
  "model_id": "nba_model_123",
  "name": "ML NBA Strategy",
  "confidence_threshold": 70,
  "max_bet_percentage": 3.0
}
```

#### Assign Model to Investor
```
POST /api/investors/{bot_id}/assign-model
{
  "model_id": "nba_model_123",
  "user_id": "user123"
}
```

#### Get Investor Recommendations
```
GET /api/investors/{bot_id}/model-recommendations?user_id=user123
```

### Analytics APIs

#### Kelly Criterion Calculator
```
POST /api/analytics/kelly
{
  "win_probability": 0.58,
  "odds": 185,
  "bankroll": 1000
}
```

## User Workflow Examples

### Complete Model Development Workflow

1. **Navigate to ML Dashboard**: Go to `/ml`

2. **Train a New Model**:
   - Select "Model Training" section
   - Choose NBA, Statistical model, 1000 samples
   - Click "Start Training"
   - Monitor progress and view results

3. **Tune Model Parameters**:
   - Select trained model from dropdown
   - Adjust confidence threshold to 75%
   - Set max bet percentage to 2.5%
   - Apply changes and view performance update

4. **Create Model-Based Strategy**:
   - Use API or strategy builder to create strategy
   - Link to the trained model
   - Configure strategy parameters

5. **Assign to Investor**:
   - Create or select existing investor
   - Assign the trained model to investor
   - Investor will use model for recommendations

6. **Monitor Performance**:
   - View investor recommendations
   - Track model accuracy
   - Analyze betting performance

### Quick Start for Existing Users

1. **Access Model Gallery**: Navigate to ML Dashboard → Model Gallery
2. **Select Pre-trained Model**: Choose from NBA, NFL, or MLB models
3. **Tune Parameters**: Click "Tune" and adjust settings
4. **Assign to Investor**: Use existing investor management system
5. **Get Recommendations**: Investor will provide ML-powered picks

## Technical Architecture

### Backend Components

- **Flask Application** (`app.py`): Main server with RESTful APIs
- **Model Manager** (`ml/model_manager.py`): Centralized ML model management
- **Basic Predictor** (`ml/basic_predictor.py`): Statistical model implementation
- **Advanced Models** (`models/`): Neural networks and ensemble methods

### Frontend Components

- **Main Dashboard** (`templates/index.html`): Overall platform management
- **ML Dashboard** (`templates/ml_dashboard.html`): Comprehensive ML interface
- **Interactive Components**: Parameter sliders, progress bars, model cards

### Database Integration

- **Firebase Firestore**: User data, investor configurations, strategies
- **Model Storage**: Trained model artifacts and metadata
- **Performance Tracking**: Model metrics and betting results

## Demo Mode

The platform includes comprehensive demo functionality that works without external dependencies:

- **Demo Models**: Pre-configured NBA, NFL, MLB models
- **Simulated Training**: Progress tracking with realistic timelines
- **Mock Predictions**: Consistent prediction results for testing
- **Sample Data**: Representative sports data for model training

## Getting Started

### Prerequisites
- Python 3.8+
- Flask
- NumPy, Pandas
- Optional: TensorFlow, PyTorch for advanced models

### Installation
```bash
cd Post9/dashboard
pip install -r ../requirements.txt
python app.py
```

### Access Points
- Main Dashboard: `http://localhost:5000/`
- ML Dashboard: `http://localhost:5000/ml`
- API Documentation: Available through interactive testing

### Testing
```bash
python test_functionality.py
```

This will test all major functionalities and confirm the system is working correctly.

## Future Enhancements

- **Advanced Neural Networks**: LSTM, Transformer models for complex predictions
- **Real-time Data Integration**: Live sports data feeds
- **Backtesting Framework**: Historical performance analysis
- **Model Ensemble Voting**: Combine multiple models for better accuracy
- **Risk Management Tools**: Advanced position sizing and portfolio management
- **Mobile Interface**: Responsive design for mobile trading
- **Social Features**: Strategy sharing and community insights

## Support

For questions or issues, refer to the codebase documentation or create an issue in the repository.

---

**Post9**: Stop Betting. Start Investing. 🚀

---

**Last Updated**: 9/13/2025