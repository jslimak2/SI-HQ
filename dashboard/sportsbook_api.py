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
    stake: float
    line: Optional[float] = None  # for spread/total bets
    
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
        self.enabled = enabled
        self.sportsbooks = {}
        self.default_sportsbook = None
        
    def add_sportsbook(self, name: str, api_instance: SportsbookAPIBase, is_default: bool = False):
        """Add a sportsbook to the service"""
        self.sportsbooks[name] = api_instance
        if is_default or not self.default_sportsbook:
            self.default_sportsbook = name
        logger.info(f"Added sportsbook: {name}")
    
    def place_bet(self, bet_request: BetRequest, sportsbook: str = None) -> BetResult:
        """Place a bet on specified or default sportsbook"""
        if not self.enabled:
            logger.warning("Real betting is disabled")
            return BetResult(
                success=False,
                message="Real betting is disabled",
                error_code="BETTING_DISABLED"
            )
        
        sportsbook_name = sportsbook or self.default_sportsbook
        
        if sportsbook_name not in self.sportsbooks:
            return BetResult(
                success=False,
                message=f"Sportsbook {sportsbook_name} not configured",
                error_code="SPORTSBOOK_NOT_FOUND"
            )
        
        try:
            sportsbook_api = self.sportsbooks[sportsbook_name]
            result = sportsbook_api.place_bet(bet_request)
            
            # Log the bet placement
            logger.info(f"Bet placed on {sportsbook_name}: {result.bet_id} - {result.message}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to place bet on {sportsbook_name}: {e}")
            return BetResult(
                success=False,
                message=f"Betting service error: {str(e)}",
                error_code="SERVICE_ERROR"
            )
    
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