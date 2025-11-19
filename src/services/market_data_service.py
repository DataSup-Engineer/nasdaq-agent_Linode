"""
Enhanced market data service with caching, error handling, and resilience
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from src.services.yfinance_service import YFinanceService
from src.services.cache_service import CachedYFinanceService, global_cache
from src.models.market_data import MarketData
from src.config.settings import settings

logger = logging.getLogger(__name__)


class MarketDataService:
    """High-level market data service with comprehensive error handling"""
    
    def __init__(self):
        self.yfinance_service = YFinanceService()
        self.cached_service = CachedYFinanceService(self.yfinance_service, global_cache)
        self._circuit_breaker = CircuitBreaker()
    
    async def get_stock_data(self, ticker: str) -> MarketData:
        """Get comprehensive stock data with full error handling and caching"""
        try:
            # Validate ticker format first
            if not self._is_valid_ticker_format(ticker):
                raise ValueError(f"Invalid ticker format: {ticker}")
            
            # Check circuit breaker
            if self._circuit_breaker.is_open():
                logger.warning("Circuit breaker is open, using cached data only")
                return await self._get_cached_data_only(ticker)
            
            # Get comprehensive data through cached service
            try:
                market_data = await self.cached_service.get_comprehensive_data_cached(ticker)
                self._circuit_breaker.record_success()
                return market_data
                
            except Exception as e:
                self._circuit_breaker.record_failure()
                
                # Try to get market status to provide better error context
                market_status = await self._get_market_status_safe()
                
                if not market_status.get('is_open', False):
                    logger.info(f"Market is closed, attempting to return cached data for {ticker}")
                    cached_data = await self._get_cached_data_only(ticker)
                    if cached_data:
                        return cached_data
                
                # If all else fails, raise the original exception
                raise e
        
        except Exception as e:
            logger.error(f"Failed to get stock data for {ticker}: {e}")
            raise
    
    async def validate_ticker(self, ticker: str) -> bool:
        """Validate ticker symbol with caching"""
        try:
            return await self.cached_service.validate_ticker_cached(ticker)
        except Exception as e:
            logger.error(f"Failed to validate ticker {ticker}: {e}")
            return False
    
    async def search_company(self, company_name: str) -> list:
        """Search for ticker by company name"""
        try:
            return await self.yfinance_service.search_ticker_by_name(company_name)
        except Exception as e:
            logger.error(f"Failed to search for company '{company_name}': {e}")
            return []
    
    async def get_market_status(self) -> Dict[str, Any]:
        """Get current market status"""
        try:
            return await self.yfinance_service.get_market_status()
        except Exception as e:
            logger.error(f"Failed to get market status: {e}")
            return {
                'market_state': 'UNKNOWN',
                'is_open': False,
                'last_update': None,
                'timestamp': datetime.utcnow(),
                'error': str(e)
            }
    
    async def _get_market_status_safe(self) -> Dict[str, Any]:
        """Get market status without raising exceptions"""
        try:
            return await self.get_market_status()
        except Exception:
            return {'is_open': False}
    
    async def _get_cached_data_only(self, ticker: str) -> Optional[MarketData]:
        """Attempt to get cached data only (fallback method)"""
        try:
            # Try to get any cached comprehensive data
            cache_key = global_cache._generate_key("comprehensive_data", ticker.upper())
            cached_data = await global_cache.get(cache_key)
            
            if cached_data:
                logger.info(f"Returning cached data for {ticker}")
                return cached_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached data for {ticker}: {e}")
            return None
    
    def _is_valid_ticker_format(self, ticker: str) -> bool:
        """Validate ticker format"""
        return self.yfinance_service._is_valid_ticker_format(ticker)
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get service health status"""
        try:
            # Test basic functionality
            test_ticker = "AAPL"  # Use Apple as a test ticker
            
            health_status = {
                'service': 'MarketDataService',
                'timestamp': datetime.utcnow(),
                'circuit_breaker_status': self._circuit_breaker.get_status(),
                'cache_stats': await self.cached_service.get_cache_stats()
            }
            
            # Test ticker validation
            try:
                is_valid = await asyncio.wait_for(
                    self.validate_ticker(test_ticker),
                    timeout=5.0
                )
                health_status['ticker_validation'] = 'healthy' if is_valid else 'unhealthy'
            except asyncio.TimeoutError:
                health_status['ticker_validation'] = 'timeout'
            except Exception as e:
                health_status['ticker_validation'] = f'error: {e}'
            
            # Test market status
            try:
                market_status = await asyncio.wait_for(
                    self.get_market_status(),
                    timeout=5.0
                )
                health_status['market_status_check'] = 'healthy'
                health_status['market_is_open'] = market_status.get('is_open', False)
            except asyncio.TimeoutError:
                health_status['market_status_check'] = 'timeout'
            except Exception as e:
                health_status['market_status_check'] = f'error: {e}'
            
            # Overall health determination
            checks = [
                health_status.get('ticker_validation') == 'healthy',
                health_status.get('market_status_check') == 'healthy',
                not self._circuit_breaker.is_open()
            ]
            
            health_status['overall_status'] = 'healthy' if all(checks) else 'degraded'
            
            return health_status
            
        except Exception as e:
            return {
                'service': 'MarketDataService',
                'timestamp': datetime.utcnow(),
                'overall_status': 'unhealthy',
                'error': str(e)
            }
    
    async def clear_cache(self) -> None:
        """Clear all cached data"""
        await self.cached_service.clear_cache()


class CircuitBreaker:
    """Circuit breaker pattern for external API calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.state == 'OPEN':
            # Check if we should transition to HALF_OPEN
            if (self.last_failure_time and 
                (datetime.utcnow() - self.last_failure_time).total_seconds() > self.recovery_timeout):
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return False
            return True
        
        return False
    
    def record_success(self):
        """Record a successful operation"""
        if self.state == 'HALF_OPEN':
            self.state = 'CLOSED'
            self.failure_count = 0
            logger.info("Circuit breaker closed after successful operation")
        elif self.state == 'CLOSED':
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record a failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time,
            'is_open': self.is_open()
        }


# Global market data service instance
market_data_service = MarketDataService()