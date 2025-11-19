"""
In-memory caching service for NASDAQ Stock Agent
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, TypeVar, Generic
import logging
import json
import hashlib
from dataclasses import asdict
from src.config.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheEntry(Generic[T]):
    """Cache entry with TTL support"""
    
    def __init__(self, data: T, ttl_seconds: int):
        self.data = data
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.utcnow() > self.expires_at
    
    def get_age_seconds(self) -> int:
        """Get age of cache entry in seconds"""
        return int((datetime.utcnow() - self.created_at).total_seconds())


class InMemoryCache:
    """Thread-safe in-memory cache with TTL support"""
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        # NOTE: Do NOT start background tasks at import time. The event loop
        # may not be running when this module is imported (e.g. when the
        # application is being imported). Provide explicit lifecycle methods
        # (start/shutdown) that should be called when an event loop is running.
    
    def _start_cleanup_task(self):
        """(Deprecated) kept for compatibility. Use async start() instead."""
        # Kept as a no-op to avoid accidental task creation from non-running
        # event loop contexts.
        return

    async def start(self):
        """Start the background cleanup task.

        This must be called from a running event loop (for example during
        application startup). It creates an asyncio.Task that runs the
        periodic cleanup coroutine.
        """
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Periodically clean up expired entries"""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    async def _cleanup_expired(self):
        """Remove expired entries from cache"""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        # Create a string representation of all arguments
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        
        # Hash for consistent key length
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                return None
            
            if entry.is_expired():
                del self._cache[key]
                return None
            
            return entry.data
    
    async def set(self, key: str, value: Any, ttl_seconds: int = None) -> None:
        """Set value in cache with TTL"""
        if ttl_seconds is None:
            ttl_seconds = settings.cache_ttl_seconds
        
        async with self._lock:
            self._cache[key] = CacheEntry(value, ttl_seconds)
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())
            
            return {
                'total_entries': total_entries,
                'active_entries': total_entries - expired_entries,
                'expired_entries': expired_entries,
                'cache_hit_ratio': getattr(self, '_hit_ratio', 0.0)
            }
    
    async def shutdown(self):
        """Shutdown cache and cleanup task.

        Cancels the background cleanup task and awaits its completion. This
        should be called during application shutdown while the event loop is
        still running.
        """
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


class CachedYFinanceService:
    """Yahoo Finance service with caching and error handling"""
    
    def __init__(self, yfinance_service, cache: InMemoryCache = None):
        self.yfinance_service = yfinance_service
        self.cache = cache or InMemoryCache()
        self.retry_attempts = 3
        self.retry_delay = 1.0  # seconds
    
    async def get_current_data_cached(self, ticker: str) -> Dict[str, Any]:
        """Get current data with caching"""
        cache_key = self.cache._generate_key("current_data", ticker.upper())
        
        # Try cache first
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for current data: {ticker}")
            cached_data['from_cache'] = True
            cached_data['cache_age_seconds'] = (
                datetime.utcnow() - cached_data['timestamp']
            ).total_seconds()
            return cached_data
        
        # Cache miss - fetch from API with retry logic
        try:
            data = await self._retry_operation(
                self.yfinance_service.get_current_data,
                ticker
            )
            
            # Cache the result
            await self.cache.set(
                cache_key, 
                data, 
                ttl_seconds=300  # 5 minutes for current data
            )
            
            data['from_cache'] = False
            logger.info(f"Fetched and cached current data for {ticker}")
            return data
            
        except Exception as e:
            # Try to return stale cached data if available
            stale_data = await self._get_stale_cached_data(cache_key)
            if stale_data:
                logger.warning(f"Returning stale cached data for {ticker} due to error: {e}")
                stale_data['from_cache'] = True
                stale_data['is_stale'] = True
                return stale_data
            
            raise
    
    async def get_historical_data_cached(self, ticker: str, months: int = 6) -> list:
        """Get historical data with caching"""
        cache_key = self.cache._generate_key("historical_data", ticker.upper(), months)
        
        # Try cache first
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for historical data: {ticker}")
            return cached_data
        
        # Cache miss - fetch from API with retry logic
        try:
            data = await self._retry_operation(
                self.yfinance_service.get_historical_data,
                ticker,
                months
            )
            
            # Cache the result for longer (historical data changes less frequently)
            await self.cache.set(
                cache_key,
                data,
                ttl_seconds=3600  # 1 hour for historical data
            )
            
            logger.info(f"Fetched and cached historical data for {ticker}")
            return data
            
        except Exception as e:
            # Try to return stale cached data if available
            stale_data = await self._get_stale_cached_data(cache_key)
            if stale_data:
                logger.warning(f"Returning stale cached historical data for {ticker} due to error: {e}")
                return stale_data
            
            raise
    
    async def get_comprehensive_data_cached(self, ticker: str):
        """Get comprehensive data with caching"""
        cache_key = self.cache._generate_key("comprehensive_data", ticker.upper())
        
        # Try cache first
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for comprehensive data: {ticker}")
            return cached_data
        
        # Cache miss - fetch from API with retry logic
        try:
            data = await self._retry_operation(
                self.yfinance_service.get_comprehensive_data,
                ticker
            )
            
            # Cache the result
            await self.cache.set(
                cache_key,
                data,
                ttl_seconds=600  # 10 minutes for comprehensive data
            )
            
            logger.info(f"Fetched and cached comprehensive data for {ticker}")
            return data
            
        except Exception as e:
            # Try to return stale cached data if available
            stale_data = await self._get_stale_cached_data(cache_key)
            if stale_data:
                logger.warning(f"Returning stale cached comprehensive data for {ticker} due to error: {e}")
                return stale_data
            
            raise
    
    async def validate_ticker_cached(self, ticker: str) -> bool:
        """Validate ticker with caching"""
        cache_key = self.cache._generate_key("ticker_validation", ticker.upper())
        
        # Try cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for ticker validation: {ticker}")
            return cached_result
        
        # Cache miss - validate with API
        try:
            is_valid = await self._retry_operation(
                self.yfinance_service.validate_ticker_exists,
                ticker
            )
            
            # Cache the result for a long time (ticker validity doesn't change often)
            await self.cache.set(
                cache_key,
                is_valid,
                ttl_seconds=86400  # 24 hours
            )
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Failed to validate ticker {ticker}: {e}")
            return False
    
    async def _retry_operation(self, operation, *args, **kwargs):
        """Retry operation with exponential backoff"""
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                return await operation(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Operation failed (attempt {attempt + 1}/{self.retry_attempts}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Operation failed after {self.retry_attempts} attempts: {e}")
        
        raise last_exception
    
    async def _get_stale_cached_data(self, cache_key: str) -> Optional[Any]:
        """Get stale cached data (ignoring TTL) for fallback"""
        # This is a simplified implementation
        # In a production system, you might want to store stale data separately
        return None
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return await self.cache.get_stats()
    
    async def clear_cache(self) -> None:
        """Clear all cached data"""
        await self.cache.clear()
        logger.info("Cache cleared")


# Global cache instance
global_cache = InMemoryCache()