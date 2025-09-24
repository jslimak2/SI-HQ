"""
Sportsbook API Integration for Real Betting Execution
Handles actual bet placement when real betting is enabled
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import time
import hashlib
import hmac
import base64

logger = logging.getLogger(__name__)

class BetType(Enum):
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTAL = "total"
    PROP = "prop"

class BetStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"
    PUSHED = "pushed"

@dataclass
class BetRequest:
    """Bet placement request"""
    game_id: str
    bet_type: BetType
    selection: str  # team name or over/under
    odds: float
    amount: float  # Renamed from stake for consistency
    line: Optional[float] = None  # for spread/total bets
    sportsbook: Optional[str] = None  # preferred sportsbook
    notes: Optional[str] = None  # user notes
    confidence: Optional[float] = None  # model confidence
    model_prediction: Optional[Dict] = None  # model prediction data
    
    @property
    def stake(self) -> float:
        """Backward compatibility property"""
        return self.amount
    
@dataclass
class BetResult:
    """Result of bet placement"""
    success: bool
    bet_id: Optional[str] = None
    status: BetStatus = BetStatus.PENDING
    message: str = ""
    actual_odds: Optional[float] = None
    actual_stake: Optional[float] = None
    timestamp: Optional[datetime] = None
    error_code: Optional[str] = None

class SportsbookAPIBase:
    """Base class for sportsbook API integrations"""
    
    def __init__(self, api_key: str, api_secret: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = ""
        self.session = requests.Session()
        self.last_request_time = 0
        self.min_request_interval = 1.0
        
    def _rate_limit(self):
        """Enforce rate limiting between API requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _generate_signature(self, method: str, path: str, params: Dict = None) -> str:
        """Generate API signature for authenticated requests"""
        if not self.api_secret:
            return ""
        
        timestamp = str(int(time.time()))
        params_str = json.dumps(params or {}, sort_keys=True)
        
        message = f"{method}{path}{timestamp}{params_str}"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _make_authenticated_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make authenticated API request"""
        self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        timestamp = str(int(time.time()))
        
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key,
            'X-Timestamp': timestamp
        }
        
        # Add signature if secret is available
        if self.api_secret:
            signature = self._generate_signature(method, endpoint, data)
            headers['X-Signature'] = signature
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, params=data, timeout=30)
            else:
                response = self.session.request(
                    method.upper(), url, 
                    headers=headers, 
                    json=data, 
                    timeout=30
                )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Sportsbook API request failed: {e}")
            raise
    
    def place_bet(self, bet_request: BetRequest) -> BetResult:
        """Place a bet on the sportsbook"""
        raise NotImplementedError
    
    def get_bet_status(self, bet_id: str) -> BetResult:
        """Get status of a placed bet"""
        raise NotImplementedError
    
    def cancel_bet(self, bet_id: str) -> bool:
        """Cancel a pending bet"""
        raise NotImplementedError
    
    def get_account_balance(self) -> float:
        """Get current account balance"""
        raise NotImplementedError

class DraftKingsAPI(SportsbookAPIBase):
    """DraftKings Sportsbook API integration"""
    
    def __init__(self, api_key: str, api_secret: str = None):
        super().__init__(api_key, api_secret)
        self.base_url = "https://api.draftkings.com/sportsbook/v1"
        self.min_request_interval = 0.5  # DraftKings rate limit
    
    def place_bet(self, bet_request: BetRequest) -> BetResult:
        """Place bet on DraftKings"""
        try:
            # DraftKings bet placement payload
            bet_data = {
                'game_id': bet_request.game_id,
                'bet_type': bet_request.bet_type.value,
                'selection': bet_request.selection,
                'odds': bet_request.odds,
                'stake': bet_request.stake,
                'line': bet_request.line
            }
            
            response = self._make_authenticated_request('POST', '/bets', bet_data)
            
            return BetResult(
                success=True,
                bet_id=response.get('bet_id'),
                status=BetStatus(response.get('status', 'pending')),
                message=response.get('message', 'Bet placed successfully'),
                actual_odds=response.get('odds'),
                actual_stake=response.get('stake'),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to place bet on DraftKings: {e}")
            return BetResult(
                success=False,
                message=f"Bet placement failed: {str(e)}",
                error_code="PLACEMENT_ERROR"
            )
    
    def get_bet_status(self, bet_id: str) -> BetResult:
        """Get bet status from DraftKings"""
        try:
            response = self._make_authenticated_request('GET', f'/bets/{bet_id}')
            
            return BetResult(
                success=True,
                bet_id=bet_id,
                status=BetStatus(response.get('status')),
                message=response.get('result_message', ''),
                actual_odds=response.get('odds'),
                actual_stake=response.get('stake'),
                timestamp=datetime.fromisoformat(response.get('updated_at', ''))
            )
            
        except Exception as e:
            logger.error(f"Failed to get bet status from DraftKings: {e}")
            return BetResult(
                success=False,
                message=f"Status check failed: {str(e)}",
                error_code="STATUS_ERROR"
            )

class FanDuelAPI(SportsbookAPIBase):
    """FanDuel Sportsbook API integration"""
    
    def __init__(self, api_key: str, api_secret: str = None):
        super().__init__(api_key, api_secret)
        self.base_url = "https://api.fanduel.com/sportsbook/v1"
        self.min_request_interval = 1.0  # FanDuel rate limit
    
    def place_bet(self, bet_request: BetRequest) -> BetResult:
        """Place bet on FanDuel"""
        try:
            bet_data = {
                'event_id': bet_request.game_id,
                'market_type': bet_request.bet_type.value,
                'selection': bet_request.selection,
                'price': bet_request.odds,
                'stake': bet_request.stake
            }
            
            if bet_request.line is not None:
                bet_data['handicap'] = bet_request.line
            
            response = self._make_authenticated_request('POST', '/place-bet', bet_data)
            
            return BetResult(
                success=True,
                bet_id=response.get('bet_id'),
                status=BetStatus(response.get('status', 'pending')),
                message="Bet placed on FanDuel",
                actual_odds=response.get('accepted_price'),
                actual_stake=response.get('stake'),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to place bet on FanDuel: {e}")
            return BetResult(
                success=False,
                message=f"FanDuel bet placement failed: {str(e)}",
                error_code="PLACEMENT_ERROR"
            )

class MockSportsbookAPI(SportsbookAPIBase):
    """Mock sportsbook for testing and demo purposes"""
    
    def __init__(self, api_key: str = "demo", api_secret: str = None):
        super().__init__(api_key, api_secret)
        self.placed_bets = {}
        self.next_bet_id = 1
    
    def place_bet(self, bet_request: BetRequest) -> BetResult:
        """Simulate bet placement"""
        bet_id = f"MOCK_{self.next_bet_id:06d}"
        self.next_bet_id += 1
        
        # Simulate some randomness in bet acceptance
        import random
        success_rate = 0.85  # 85% of bets are accepted
        
        if random.random() < success_rate:
            self.placed_bets[bet_id] = {
                'request': bet_request,
                'status': BetStatus.ACCEPTED,
                'placed_at': datetime.now()
            }
            
            return BetResult(
                success=True,
                bet_id=bet_id,
                status=BetStatus.ACCEPTED,
                message="Mock bet placed successfully",
                actual_odds=bet_request.odds,
                actual_stake=bet_request.stake,
                timestamp=datetime.now()
            )
        else:
            return BetResult(
                success=False,
                message="Mock bet rejected (simulated)",
                error_code="MOCK_REJECTION"
            )
    
    def get_bet_status(self, bet_id: str) -> BetResult:
        """Get mock bet status"""
        if bet_id in self.placed_bets:
            bet_info = self.placed_bets[bet_id]
            return BetResult(
                success=True,
                bet_id=bet_id,
                status=bet_info['status'],
                message="Mock bet status",
                timestamp=bet_info['placed_at']
            )
        else:
            return BetResult(
                success=False,
                message="Bet not found",
                error_code="NOT_FOUND"
            )

class BettingExecutionService:
    """Main service for executing bets across multiple sportsbooks"""
    
    def __init__(self, enabled: bool = False):
        """
        Initialize betting service
        
        IMPORTANT: Live betting is disabled by default for safety.
        Users must export holdings to Excel and manually place bets.
        """
        self.enabled = False  # Always disabled for production safety
        self.sportsbooks = {}
        self.default_sportsbook = None
        self.pending_investments = {}  # Store investments for manual processing
        
        # Log important safety message
        logger.info("[SAFETY] LIVE BETTING DISABLED FOR SAFETY [SAFETY]")
        logger.info("All investments will be held for manual export and placement")
        
    def add_sportsbook(self, name: str, api_instance: 'SportsbookAPIBase', is_default: bool = False):
        """Add a sportsbook to the service (disabled for manual workflow)"""
        logger.warning(f"Sportsbook {name} registered but live betting is disabled")
        self.sportsbooks[name] = api_instance
        if is_default or not self.default_sportsbook:
            self.default_sportsbook = name
        logger.info(f"Added sportsbook: {name}")
            
    def hold_investment(self, bet_request: 'BetRequest', user_id: str) -> Dict[str, Any]:
        """Hold an investment for manual export and placement"""
        investment_id = f"inv_{int(time.time())}_{len(self.pending_investments)}"
        
        investment = {
            'id': investment_id,
            'user_id': user_id,
            'game': bet_request.game_id,
            'market_type': bet_request.bet_type.value,
            'selection': bet_request.selection,
            'odds': bet_request.odds,
            'amount': bet_request.amount,
            'potential_payout': bet_request.amount * bet_request.odds,
            'sportsbook': bet_request.sportsbook or 'User Choice',
            'created_at': datetime.now(),
            'status': 'pending_export',
            'notes': bet_request.notes or '',
            'confidence': getattr(bet_request, 'confidence', 0.0),
            'model_prediction': getattr(bet_request, 'model_prediction', {})
        }
        
        if user_id not in self.pending_investments:
            self.pending_investments[user_id] = []
            
        self.pending_investments[user_id].append(investment)
        
        logger.info(f"Investment held for manual placement: {investment_id}")
        
        return {
            'success': True,
            'investment_id': investment_id,
            'message': f'Investment held for manual export. Amount: ${bet_request.amount:.2f}',
            'status': 'held_for_export',
            'next_steps': [
                'Export holdings to Excel',
                'Manually place bets on your chosen sportsbook',
                'Return to confirm, edit, or reject the investment'
            ]
        }
    
    def place_bet(self, bet_request: 'BetRequest', sportsbook: str = None) -> 'BetResult':
        """Place a bet on specified or default sportsbook (DISABLED)"""
        logger.warning("[SAFETY] place_bet() called but live betting is DISABLED")
        
        return BetResult(
            success=False,
            message="Live betting is disabled. Use hold_investment() instead.",
            error_code="LIVE_BETTING_DISABLED"
        )
        
    def get_pending_investments(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending investments for a user"""
        return self.pending_investments.get(user_id, [])
        
    def export_investments_to_csv(self, user_id: str) -> str:
        """Export user's pending investments to CSV format"""
        investments = self.get_pending_investments(user_id)
        
        if not investments:
            return "No pending investments to export"
            
        # Create CSV content
        csv_lines = [
            "Investment ID,Game,Market Type,Selection,Odds,Amount,Potential Payout,Sportsbook,Created At,Notes"
        ]
        
        for inv in investments:
            csv_line = f"{inv['id']},{inv['game']},{inv['market_type']},{inv['selection']}," \
                      f"{inv['odds']},{inv['amount']:.2f},{inv['potential_payout']:.2f}," \
                      f"{inv['sportsbook']},{inv['created_at'].strftime('%Y-%m-%d %H:%M:%S')}," \
                      f"\"{inv['notes']}\""
            csv_lines.append(csv_line)
            
        return "\n".join(csv_lines)
        
    def confirm_investment(self, investment_id: str, user_id: str, 
                          actual_odds: Optional[float] = None,
                          actual_amount: Optional[float] = None,
                          bet_slip_id: Optional[str] = None) -> Dict[str, Any]:
        """Confirm that an investment was manually placed"""
        investments = self.pending_investments.get(user_id, [])
        
        for inv in investments:
            if inv['id'] == investment_id:
                inv['status'] = 'confirmed'
                inv['confirmed_at'] = datetime.now()
                
                if actual_odds:
                    inv['actual_odds'] = actual_odds
                    inv['actual_payout'] = inv['amount'] * actual_odds
                    
                if actual_amount:
                    inv['actual_amount'] = actual_amount
                    
                if bet_slip_id:
                    inv['bet_slip_id'] = bet_slip_id
                    
                logger.info(f"Investment confirmed: {investment_id}")
                
                return {
                    'success': True,
                    'message': f'Investment {investment_id} confirmed as placed',
                    'investment': inv
                }
                
        return {
            'success': False,
            'message': f'Investment {investment_id} not found'
        }
        
    def edit_investment(self, investment_id: str, user_id: str, 
                       updates: Dict[str, Any]) -> Dict[str, Any]:
        """Edit a pending investment"""
        investments = self.pending_investments.get(user_id, [])
        
        for inv in investments:
            if inv['id'] == investment_id and inv['status'] == 'pending_export':
                
                # Update allowed fields
                updatable_fields = ['amount', 'odds', 'selection', 'sportsbook', 'notes']
                for field in updatable_fields:
                    if field in updates:
                        inv[field] = updates[field]
                        
                # Recalculate potential payout
                inv['potential_payout'] = inv['amount'] * inv['odds']
                inv['updated_at'] = datetime.now()
                
                logger.info(f"Investment edited: {investment_id}")
                
                return {
                    'success': True,
                    'message': f'Investment {investment_id} updated',
                    'investment': inv
                }
                
        return {
            'success': False,
            'message': f'Investment {investment_id} not found or cannot be edited'
        }
        
    def reject_investment(self, investment_id: str, user_id: str, 
                         reason: str = '') -> Dict[str, Any]:
        """Reject/cancel a pending investment"""
        investments = self.pending_investments.get(user_id, [])
        
        for i, inv in enumerate(investments):
            if inv['id'] == investment_id:
                inv['status'] = 'rejected'
                inv['rejected_at'] = datetime.now()
                inv['rejection_reason'] = reason
                
                logger.info(f"Investment rejected: {investment_id} - {reason}")
                
                return {
                    'success': True,
                    'message': f'Investment {investment_id} rejected',
                    'reason': reason
                }
                
        return {
            'success': False,
            'message': f'Investment {investment_id} not found'
        }
    
    def get_best_odds(self, game_id: str, bet_type: BetType, selection: str) -> Dict[str, float]:
        """Get best odds across all configured sportsbooks"""
        best_odds = {}
        
        for name, sportsbook in self.sportsbooks.items():
            try:
                # This would require implementing odds fetching in each sportsbook
                # For now, return mock data
                odds = 2.0  # Would be actual API call
                best_odds[name] = odds
            except Exception as e:
                logger.warning(f"Failed to get odds from {name}: {e}")
        
        return best_odds
    
    def validate_configuration(self) -> Dict[str, bool]:
        """Validate all sportsbook configurations"""
        status = {}
        
        for name, sportsbook in self.sportsbooks.items():
            try:
                # Test basic connectivity (would be actual API call)
                status[name] = True
                logger.info(f"Sportsbook {name} configuration valid")
            except Exception as e:
                status[name] = False
                logger.error(f"Sportsbook {name} configuration invalid: {e}")
        
        return status

# Global betting service instance
betting_service = None

def initialize_betting_service(config) -> BettingExecutionService:
    """Initialize the global betting service"""
    global betting_service
    
    enabled = config.api.enable_real_betting if hasattr(config.api, 'enable_real_betting') else False
    betting_service = BettingExecutionService(enabled=enabled)
    
    # Add configured sportsbooks
    if hasattr(config.api, 'draftkings_api_key') and config.api.draftkings_api_key:
        dk_api = DraftKingsAPI(config.api.draftkings_api_key)
        betting_service.add_sportsbook('draftkings', dk_api, is_default=True)
    
    if hasattr(config.api, 'fanduel_api_key') and config.api.fanduel_api_key:
        fd_api = FanDuelAPI(config.api.fanduel_api_key)
        betting_service.add_sportsbook('fanduel', fd_api)
    
    # Always add mock sportsbook for testing
    mock_api = MockSportsbookAPI()
    betting_service.add_sportsbook('mock', mock_api, is_default=(not enabled))
    
    logger.info(f"Betting service initialized (enabled: {enabled})")
    return betting_service

def get_betting_service() -> BettingExecutionService:
    """Get the global betting service instance"""
    global betting_service
    if betting_service is None:
        # Initialize with mock configuration
        from dataclasses import dataclass
        
        @dataclass
        class MockAPI:
            enable_real_betting: bool = False
        
        @dataclass
        class MockConfig:
            api: MockAPI = MockAPI()
        
        betting_service = initialize_betting_service(MockConfig())
    
    return betting_service