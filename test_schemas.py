#!/usr/bin/env python3
"""
Test suite for the new standardized schemas in SI-HQ
Tests all schema classes, validation, and migration functionality
"""

import pytest
import json
import tempfile
import os
from datetime import datetime

# Import the schemas and data services
from dashboard.schemas import (
    ModelSchema, BotSchema, StrategySchema, PerformanceMetrics, 
    RiskManagement, TransactionLog, OpenWager, ModelInputOutput,
    ModelStatus, BotStatus, StrategyType, Sport, MarketType, BetOutcome,
    SchemaValidator, migrate_legacy_model, migrate_legacy_bot, migrate_legacy_strategy
)
from dashboard.data_service import DataService
from dashboard.model_registry import ModelRegistry


class TestSchemas:
    """Test the schema classes and their functionality"""
    
    def test_model_schema_creation(self):
        """Test creating a model with the new schema"""
        model = ModelSchema(
            model_id="test_model_001",
            name="Test NBA Model",
            version="1.0.0",
            sport=Sport.NBA,
            model_type="neural_network",
            created_by="test_user"
        )
        
        assert model.model_id == "test_model_001"
        assert model.sport == Sport.NBA
        assert model.status == ModelStatus.TRAINING
        assert isinstance(model.current_performance, PerformanceMetrics)
    
    def test_model_schema_to_dict(self):
        """Test converting model schema to dictionary"""
        model = ModelSchema(
            model_id="test_model_002",
            name="Test NFL Model",
            version="1.0.0",
            sport=Sport.NFL,
            model_type="ensemble"
        )
        
        model_dict = model.to_dict()
        
        assert model_dict['sport'] == 'NFL'
        assert model_dict['status'] == 'training'
        assert 'current_performance' in model_dict
        assert 'inputs_outputs' in model_dict
    
    def test_model_schema_from_dict(self):
        """Test creating model schema from dictionary"""
        model_data = {
            'model_id': 'test_model_003',
            'name': 'Test MLB Model',
            'version': '1.0.0',
            'sport': 'MLB',
            'model_type': 'statistical',
            'status': 'ready',
            'created_by': 'test_user'
        }
        
        model = ModelSchema.from_dict(model_data)
        
        assert model.sport == Sport.MLB
        assert model.status == ModelStatus.READY
    
    def test_bot_schema_creation(self):
        """Test creating a bot with the new schema"""
        risk_mgmt = RiskManagement(
            max_bet_percentage=3.0,
            max_bets_per_week=5,
            minimum_confidence=70.0
        )
        
        bot = BotSchema(
            bot_id="test_bot_001",
            name="Test Bot",
            current_balance=1000.0,
            starting_balance=1000.0,
            sport_filter=Sport.NBA,
            risk_management=risk_mgmt,
            created_by="test_user"
        )
        
        assert bot.bot_id == "test_bot_001"
        assert bot.sport_filter == Sport.NBA
        assert bot.risk_management.max_bet_percentage == 3.0
        assert bot.active_status == BotStatus.STOPPED
    
    def test_strategy_schema_creation(self):
        """Test creating a strategy with the new schema"""
        strategy = StrategySchema(
            strategy_id="test_strategy_001",
            name="Test Strategy",
            strategy_type=StrategyType.EXPECTED_VALUE,
            created_by="test_user"
        )
        
        assert strategy.strategy_id == "test_strategy_001"
        assert strategy.strategy_type == StrategyType.EXPECTED_VALUE
        assert strategy.is_active == True
        assert isinstance(strategy.performance_metrics, PerformanceMetrics)
    
    def test_transaction_log_creation(self):
        """Test creating transaction log entries"""
        transaction = TransactionLog(
            transaction_id="tx_001",
            timestamp=datetime.now().isoformat(),
            game_id="game_001",
            teams="Lakers vs Warriors",
            sport=Sport.NBA,
            market_type=MarketType.MONEYLINE,
            bet_type="Home Win",
            amount=50.0,
            odds=1.85,
            predicted_outcome="Lakers Win",
            result=BetOutcome.WIN,
            profit_loss=42.50,
            confidence=75.0
        )
        
        assert transaction.sport == Sport.NBA
        assert transaction.result == BetOutcome.WIN
        assert transaction.profit_loss == 42.50
    
    def test_schema_validation(self):
        """Test schema validation functionality"""
        # Test valid model
        valid_model = ModelSchema(
            model_id="valid_model",
            name="Valid Model",
            version="1.0.0",
            sport=Sport.NBA,
            created_by="test_user"
        )
        
        issues = SchemaValidator.validate_model(valid_model)
        assert len(issues) == 0
        
        # Test invalid model
        invalid_model = ModelSchema(
            model_id="",  # Empty model ID should fail validation
            name="",      # Empty name should fail validation
            version="1.0.0",
            sport=Sport.NBA,
            created_by="test_user"
        )
        
        issues = SchemaValidator.validate_model(invalid_model)
        assert len(issues) > 0
        assert any("Model ID is required" in issue for issue in issues)
        assert any("Model name is required" in issue for issue in issues)


class TestDataService:
    """Test the data service functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.data_service = DataService(self.temp_dir)
    
    def test_create_bot(self):
        """Test creating a bot through data service"""
        bot_data = {
            'name': 'Test Bot',
            'current_balance': 1000.0,
            'starting_balance': 1000.0,
            'created_by': 'test_user',
            'sport_filter': 'NBA'
        }
        
        bot_id = self.data_service.create_bot(bot_data)
        assert bot_id is not None
        
        # Retrieve the bot
        bot = self.data_service.get_bot(bot_id)
        assert bot is not None
        assert bot.name == 'Test Bot'
        assert bot.sport_filter == Sport.NBA
    
    def test_create_strategy(self):
        """Test creating a strategy through data service"""
        strategy_data = {
            'name': 'Test Strategy',
            'strategy_type': 'expected_value',
            'created_by': 'test_user',
            'description': 'A test strategy'
        }
        
        strategy_id = self.data_service.create_strategy(strategy_data)
        assert strategy_id is not None
        
        # Retrieve the strategy
        strategy = self.data_service.get_strategy(strategy_id)
        assert strategy is not None
        assert strategy.name == 'Test Strategy'
        assert strategy.strategy_type == StrategyType.EXPECTED_VALUE
    
    def test_bot_transaction_logging(self):
        """Test adding transactions to a bot"""
        # Create a bot
        bot_data = {
            'name': 'Transaction Test Bot',
            'current_balance': 1000.0,
            'created_by': 'test_user'
        }
        
        bot_id = self.data_service.create_bot(bot_data)
        
        # Add a transaction
        transaction = TransactionLog(
            transaction_id="test_tx_001",
            timestamp=datetime.now().isoformat(),
            game_id="test_game_001",
            teams="Lakers vs Warriors",
            sport=Sport.NBA,
            market_type=MarketType.MONEYLINE,
            bet_type="Home Win",
            amount=50.0,
            odds=1.85,
            predicted_outcome="Lakers Win",
            result=BetOutcome.WIN,
            profit_loss=42.50,
            confidence=75.0
        )
        
        self.data_service.add_bot_transaction(bot_id, transaction)
        
        # Verify the transaction was added
        bot = self.data_service.get_bot(bot_id)
        assert len(bot.transaction_log) == 1
        assert bot.transaction_log[0].transaction_id == "test_tx_001"
        assert bot.current_balance == 1042.50  # Original + profit
        assert bot.profit_loss.total_bets == 1
        assert bot.profit_loss.winning_bets == 1
    
    def test_bot_performance_summary(self):
        """Test getting bot performance summary"""
        # Create a bot
        bot_data = {
            'name': 'Performance Test Bot',
            'current_balance': 1200.0,
            'starting_balance': 1000.0,
            'created_by': 'test_user'
        }
        
        bot_id = self.data_service.create_bot(bot_data)
        
        # Get performance summary
        summary = self.data_service.get_bot_performance_summary(bot_id)
        
        assert summary['name'] == 'Performance Test Bot'
        assert summary['current_balance'] == 1200.0
        assert summary['profit_loss'] == 200.0
        assert summary['roi_percentage'] == 20.0


class TestLegacyMigration:
    """Test migration from legacy schemas"""
    
    def test_migrate_legacy_model(self):
        """Test migrating legacy model data"""
        legacy_data = {
            'id': 'legacy_model_001',
            'name': 'Legacy Model',
            'sport': 'NBA',
            'model_type': 'neural_network',
            'status': 'ready',
            'created_by': 'test_user',
            'performance_metrics': {
                'accuracy': 0.75,
                'precision': 0.73
            }
        }
        
        migrated_model = migrate_legacy_model(legacy_data)
        
        assert migrated_model.model_id == 'legacy_model_001'
        assert migrated_model.sport == Sport.NBA
        assert migrated_model.status == ModelStatus.READY
        assert migrated_model.current_performance.accuracy == 0.75
    
    def test_migrate_legacy_bot(self):
        """Test migrating legacy bot data"""
        legacy_data = {
            'id': 'legacy_bot_001',
            'name': 'Legacy Bot',
            'current_balance': 1500.0,
            'initial_balance': 1000.0,
            'status': 'active',
            'sport': 'NBA',
            'bet_percentage': 3.0,
            'max_bets_per_week': 7,
            'created_by': 'test_user'
        }
        
        migrated_bot = migrate_legacy_bot(legacy_data)
        
        assert migrated_bot.bot_id == 'legacy_bot_001'
        assert migrated_bot.active_status == BotStatus.ACTIVE
        assert migrated_bot.sport_filter == Sport.NBA
        assert migrated_bot.risk_management.max_bet_percentage == 3.0
    
    def test_migrate_legacy_strategy(self):
        """Test migrating legacy strategy data"""
        legacy_data = {
            'id': 'legacy_strategy_001',
            'name': 'Legacy Strategy',
            'type': 'expected_value',
            'description': 'Old strategy format',
            'created_by': 'test_user',
            'parameters': {
                'min_confidence': 70.0,
                'max_bet_percentage': 4.0
            }
        }
        
        migrated_strategy = migrate_legacy_strategy(legacy_data)
        
        assert migrated_strategy.strategy_id == 'legacy_strategy_001'
        assert migrated_strategy.strategy_type == StrategyType.EXPECTED_VALUE
        assert migrated_strategy.parameters.min_confidence == 70.0


class TestModelRegistry:
    """Test the updated model registry with new schemas"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(self.temp_dir)
    
    def test_register_model_with_new_schema(self):
        """Test registering a model with the new schema"""
        model_id = self.registry.register_model(
            name="Test Registry Model",
            sport="NBA",
            model_type="neural_network",
            created_by="test_user",
            description="Test model for registry",
            inputs=["home_win_pct", "away_win_pct", "home_pace"],
            outputs=["home_win_probability", "away_win_probability"]
        )
        
        assert model_id is not None
        
        # Retrieve the model
        model = self.registry.get_model_metadata(model_id)
        assert model is not None
        assert model.sport == Sport.NBA
        assert len(model.inputs_outputs.inputs) == 3
        assert len(model.inputs_outputs.outputs) == 2
    
    def test_update_model_performance(self):
        """Test updating model performance with new schema"""
        # Register a model
        model_id = self.registry.register_model(
            name="Performance Test Model",
            sport="NFL",
            model_type="ensemble",
            created_by="test_user"
        )
        
        # Update performance
        performance_metrics = {
            'accuracy': 0.78,
            'precision': 0.76,
            'recall': 0.80,
            'f1_score': 0.78
        }
        
        self.registry.update_model_status(
            model_id, 
            ModelStatus.READY, 
            performance_metrics
        )
        
        # Verify the update
        model = self.registry.get_model_metadata(model_id)
        assert model.status == ModelStatus.READY
        assert model.current_performance.accuracy == 0.78
        assert len(model.performance_log) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])