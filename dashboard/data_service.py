"""
Data service for managing bot and strategy schemas in the SI-HQ platform.
Provides standardized data access and manipulation for bots and strategies.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from schemas import (
    BotSchema, StrategySchema, InvestorStatus, StrategyType, 
    TransactionLog, OpenWager, PerformanceMetrics, RiskManagement,
    SchemaValidator, migrate_legacy_bot, migrate_legacy_strategy
)

logger = logging.getLogger(__name__)


class DataService:
    """Centralized data service for bot and strategy management"""
    
    def __init__(self, storage_path: str = "./data"):
        self.storage_path = storage_path
        self.bots_file = os.path.join(storage_path, "bots.json")
        self.strategies_file = os.path.join(storage_path, "strategies.json")
        self._ensure_storage_directory()
        self._load_data()
    
    def _ensure_storage_directory(self):
        """Create storage directory if it doesn't exist"""
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _load_data(self):
        """Load bots and strategies from storage"""
        self._load_bots()
        self._load_strategies()
    
    def _load_bots(self):
        """Load bots with schema migration support"""
        self.bots = {}
        
        if os.path.exists(self.bots_file):
            try:
                with open(self.bots_file, 'r') as f:
                    bots_data = json.load(f)
                
                for bot_id, bot_data in bots_data.items():
                    try:
                        # Check if it's new schema format
                        if 'risk_management' in bot_data or 'profit_loss' in bot_data:
                            # New schema format
                            self.bots[bot_id] = BotSchema.from_dict(bot_data)
                        else:
                            # Legacy format - migrate
                            logger.info(f"Migrating legacy bot {bot_id} to new schema")
                            self.bots[bot_id] = migrate_legacy_bot(bot_data)
                    except Exception as e:
                        logger.error(f"Failed to load bot {bot_id}: {e}")
                        # Create minimal bot for recovery
                        self.bots[bot_id] = BotSchema(
                            bot_id=bot_id,
                            name=bot_data.get('name', 'Unknown Bot'),
                            current_balance=bot_data.get('current_balance', 1000.0),
                            created_by=bot_data.get('created_by', '')
                        )
            except Exception as e:
                logger.error(f"Failed to load bots file: {e}")
                self.bots = {}
    
    def _load_strategies(self):
        """Load strategies with schema migration support"""
        self.strategies = {}
        
        if os.path.exists(self.strategies_file):
            try:
                with open(self.strategies_file, 'r') as f:
                    strategies_data = json.load(f)
                
                for strategy_id, strategy_data in strategies_data.items():
                    try:
                        # Check if it's new schema format
                        if 'parameters' in strategy_data or 'performance_metrics' in strategy_data:
                            # New schema format
                            self.strategies[strategy_id] = StrategySchema.from_dict(strategy_data)
                        else:
                            # Legacy format - migrate
                            logger.info(f"Migrating legacy strategy {strategy_id} to new schema")
                            self.strategies[strategy_id] = migrate_legacy_strategy(strategy_data)
                    except Exception as e:
                        logger.error(f"Failed to load strategy {strategy_id}: {e}")
                        # Create minimal strategy for recovery
                        self.strategies[strategy_id] = StrategySchema(
                            strategy_id=strategy_id,
                            name=strategy_data.get('name', 'Unknown Strategy'),
                            strategy_type=StrategyType.BASIC,
                            created_by=strategy_data.get('created_by', '')
                        )
            except Exception as e:
                logger.error(f"Failed to load strategies file: {e}")
                self.strategies = {}
    
    def _save_bots(self):
        """Save bots to storage"""
        try:
            bots_data = {
                bot_id: bot.to_dict() 
                for bot_id, bot in self.bots.items()
            }
            
            with open(self.bots_file, 'w') as f:
                json.dump(bots_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save bots: {e}")
    
    def _save_strategies(self):
        """Save strategies to storage"""
        try:
            strategies_data = {
                strategy_id: strategy.to_dict() 
                for strategy_id, strategy in self.strategies.items()
            }
            
            with open(self.strategies_file, 'w') as f:
                json.dump(strategies_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save strategies: {e}")
    
    # Bot management methods
    
    def create_bot(self, bot_data: Dict[str, Any]) -> str:
        """Create a new bot using standardized schema"""
        # Generate bot ID if not provided
        if 'bot_id' not in bot_data:
            timestamp = str(int(datetime.now().timestamp()))
            bot_data['bot_id'] = f"bot_{timestamp}"
        
        # Create bot instance
        bot = BotSchema.from_dict(bot_data)
        
        # Validate bot
        validation_issues = SchemaValidator.validate_bot(bot)
        if validation_issues:
            raise ValueError(f"Bot validation failed: {', '.join(validation_issues)}")
        
        # Store bot
        self.bots[bot.bot_id] = bot
        self._save_bots()
        
        logger.info(f"Created bot: {bot.bot_id}")
        return bot.bot_id
    
    def get_bot(self, bot_id: str) -> Optional[BotSchema]:
        """Get bot by ID"""
        return self.bots.get(bot_id)
    
    def update_bot(self, bot_id: str, updates: Dict[str, Any]) -> BotSchema:
        """Update bot with new data"""
        if bot_id not in self.bots:
            raise ValueError(f"Bot {bot_id} not found")
        
        bot = self.bots[bot_id]
        
        # Update timestamp
        updates['last_updated'] = datetime.now().isoformat()
        
        # Apply updates by recreating the bot
        bot_data = bot.to_dict()
        bot_data.update(updates)
        
        updated_bot = BotSchema.from_dict(bot_data)
        
        # Validate updated bot
        validation_issues = SchemaValidator.validate_bot(updated_bot)
        if validation_issues:
            raise ValueError(f"Bot validation failed: {', '.join(validation_issues)}")
        
        self.bots[bot_id] = updated_bot
        self._save_bots()
        
        return updated_bot
    
    def list_bots(self, filters: Dict[str, Any] = None) -> List[BotSchema]:
        """List bots with optional filtering"""
        bots = list(self.bots.values())
        
        if filters:
            if 'created_by' in filters:
                bots = [b for b in bots if b.created_by == filters['created_by']]
            
            if 'active_status' in filters:
                status = InvestorStatus(filters['active_status'])
                bots = [b for b in bots if b.active_status == status]
            
            if 'sport_filter' in filters and filters['sport_filter']:
                from schemas import Sport
                sport = Sport(filters['sport_filter'])
                bots = [b for b in bots if b.sport_filter == sport]
        
        # Sort by creation date (newest first)
        bots.sort(key=lambda b: b.created_at, reverse=True)
        
        return bots
    
    def delete_bot(self, bot_id: str) -> bool:
        """Delete a bot"""
        if bot_id in self.bots:
            del self.bots[bot_id]
            self._save_bots()
            logger.info(f"Deleted bot: {bot_id}")
            return True
        return False
    
    def add_bot_transaction(self, bot_id: str, transaction: TransactionLog):
        """Add a transaction to a bot's log"""
        if bot_id not in self.bots:
            raise ValueError(f"Bot {bot_id} not found")
        
        bot = self.bots[bot_id]
        bot.transaction_log.append(transaction)
        bot.last_updated = datetime.now().isoformat()
        
        # Update performance metrics
        if transaction.result != "PENDING":
            bot.profit_loss.total_bets += 1
            bot.profit_loss.total_wagered += transaction.amount
            
            if transaction.result == "W":
                bot.profit_loss.winning_bets += 1
                bot.profit_loss.total_profit += transaction.profit_loss
            elif transaction.result == "L":
                bot.profit_loss.losing_bets += 1
                bot.profit_loss.total_profit += transaction.profit_loss  # Should be negative
            
            # Recalculate win rate and ROI
            if bot.profit_loss.total_bets > 0:
                bot.profit_loss.win_rate = bot.profit_loss.winning_bets / bot.profit_loss.total_bets
            
            if bot.profit_loss.total_wagered > 0:
                bot.profit_loss.roi_percentage = (bot.profit_loss.total_profit / bot.profit_loss.total_wagered) * 100
        
        # Update current balance
        bot.current_balance += transaction.profit_loss
        
        self._save_bots()
    
    def add_bot_open_wager(self, bot_id: str, wager: OpenWager):
        """Add an open wager to a bot"""
        if bot_id not in self.bots:
            raise ValueError(f"Bot {bot_id} not found")
        
        bot = self.bots[bot_id]
        bot.open_wagers.append(wager)
        bot.last_updated = datetime.now().isoformat()
        
        self._save_bots()
    
    def close_bot_wager(self, bot_id: str, wager_id: str, result: str, profit_loss: float):
        """Close an open wager and move to transaction log"""
        if bot_id not in self.bots:
            raise ValueError(f"Bot {bot_id} not found")
        
        bot = self.bots[bot_id]
        
        # Find and remove the open wager
        wager_to_close = None
        for i, wager in enumerate(bot.open_wagers):
            if wager.wager_id == wager_id:
                wager_to_close = bot.open_wagers.pop(i)
                break
        
        if not wager_to_close:
            raise ValueError(f"Open wager {wager_id} not found for bot {bot_id}")
        
        # Create transaction log entry
        from schemas import BetOutcome
        transaction = TransactionLog(
            transaction_id=wager_id,
            timestamp=datetime.now().isoformat(),
            game_id=wager_to_close.game_id,
            teams=wager_to_close.teams,
            sport=wager_to_close.sport,
            market_type=wager_to_close.market_type,
            bet_type=wager_to_close.bet_type,
            amount=wager_to_close.amount,
            odds=wager_to_close.odds,
            predicted_outcome=wager_to_close.predicted_outcome,
            actual_outcome=result,
            result=BetOutcome(result) if result in ['W', 'L', 'P'] else BetOutcome.PENDING,
            profit_loss=profit_loss,
            confidence=wager_to_close.confidence,
            model_used=wager_to_close.model_used,
            strategy_used=wager_to_close.strategy_used
        )
        
        # Add to transaction log
        self.add_bot_transaction(bot_id, transaction)
    
    # Strategy management methods
    
    def create_strategy(self, strategy_data: Dict[str, Any]) -> str:
        """Create a new strategy using standardized schema"""
        # Generate strategy ID if not provided
        if 'strategy_id' not in strategy_data:
            timestamp = str(int(datetime.now().timestamp()))
            strategy_data['strategy_id'] = f"strategy_{timestamp}"
        
        # Create strategy instance
        strategy = StrategySchema.from_dict(strategy_data)
        
        # Validate strategy
        validation_issues = SchemaValidator.validate_strategy(strategy)
        if validation_issues:
            raise ValueError(f"Strategy validation failed: {', '.join(validation_issues)}")
        
        # Store strategy
        self.strategies[strategy.strategy_id] = strategy
        self._save_strategies()
        
        logger.info(f"Created strategy: {strategy.strategy_id}")
        return strategy.strategy_id
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategySchema]:
        """Get strategy by ID"""
        return self.strategies.get(strategy_id)
    
    def update_strategy(self, strategy_id: str, updates: Dict[str, Any]) -> StrategySchema:
        """Update strategy with new data"""
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        strategy = self.strategies[strategy_id]
        
        # Update timestamp
        updates['last_updated'] = datetime.now().isoformat()
        
        # Apply updates by recreating the strategy
        strategy_data = strategy.to_dict()
        strategy_data.update(updates)
        
        updated_strategy = StrategySchema.from_dict(strategy_data)
        
        # Validate updated strategy
        validation_issues = SchemaValidator.validate_strategy(updated_strategy)
        if validation_issues:
            raise ValueError(f"Strategy validation failed: {', '.join(validation_issues)}")
        
        self.strategies[strategy_id] = updated_strategy
        self._save_strategies()
        
        return updated_strategy
    
    def list_strategies(self, filters: Dict[str, Any] = None) -> List[StrategySchema]:
        """List strategies with optional filtering"""
        strategies = list(self.strategies.values())
        
        if filters:
            if 'created_by' in filters:
                strategies = [s for s in strategies if s.created_by == filters['created_by']]
            
            if 'strategy_type' in filters:
                strategy_type = StrategyType(filters['strategy_type'])
                strategies = [s for s in strategies if s.strategy_type == strategy_type]
            
            if 'is_active' in filters:
                strategies = [s for s in strategies if s.is_active == filters['is_active']]
        
        # Sort by creation date (newest first)
        strategies.sort(key=lambda s: s.created_at, reverse=True)
        
        return strategies
    
    def delete_strategy(self, strategy_id: str) -> bool:
        """Delete a strategy"""
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            self._save_strategies()
            logger.info(f"Deleted strategy: {strategy_id}")
            return True
        return False
    
    def update_strategy_performance(self, strategy_id: str, performance_data: Dict[str, Any]):
        """Update strategy performance metrics"""
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        strategy = self.strategies[strategy_id]
        
        # Update individual performance metrics
        for key, value in performance_data.items():
            if hasattr(strategy.performance_metrics, key):
                setattr(strategy.performance_metrics, key, value)
        
        # Update average performance (simple average of key metrics)
        key_metrics = ['win_rate', 'roi_percentage', 'profit_factor']
        valid_metrics = []
        for metric in key_metrics:
            if hasattr(strategy.performance_metrics, metric):
                value = getattr(strategy.performance_metrics, metric)
                if value > 0:
                    valid_metrics.append(value)
        
        if valid_metrics:
            strategy.average_performance = sum(valid_metrics) / len(valid_metrics)
        
        strategy.last_updated = datetime.now().isoformat()
        self._save_strategies()
    
    # Utility methods
    
    def get_bot_performance_summary(self, bot_id: str) -> Dict[str, Any]:
        """Get comprehensive performance summary for a bot"""
        bot = self.get_bot(bot_id)
        if not bot:
            raise ValueError(f"Bot {bot_id} not found")
        
        return {
            'bot_id': bot_id,
            'name': bot.name,
            'current_balance': bot.current_balance,
            'profit_loss': bot.current_balance - bot.starting_balance,
            'roi_percentage': ((bot.current_balance - bot.starting_balance) / bot.starting_balance * 100) if bot.starting_balance > 0 else 0,
            'performance_metrics': bot.profit_loss.to_dict(),
            'open_wagers_count': len(bot.open_wagers),
            'total_transactions': len(bot.transaction_log),
            'last_activity': bot.last_activity or bot.last_updated,
            'status': bot.active_status.value
        }
    
    def get_strategy_performance_summary(self, strategy_id: str) -> Dict[str, Any]:
        """Get comprehensive performance summary for a strategy"""
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        # Count bots using this strategy
        bots_using_strategy = len([bot for bot in self.bots.values() if bot.assigned_strategy_id == strategy_id])
        
        return {
            'strategy_id': strategy_id,
            'name': strategy.name,
            'type': strategy.strategy_type.value,
            'average_performance': strategy.average_performance,
            'performance_metrics': strategy.performance_metrics.to_dict(),
            'bots_using_strategy': bots_using_strategy,
            'bets_per_week_allowed': strategy.bets_per_week_allowed,
            'parameters': strategy.parameters.to_dict(),
            'is_active': strategy.is_active,
            'last_updated': strategy.last_updated
        }


# Global data service instance
data_service = DataService()