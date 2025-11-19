"""
Logging middleware and monitoring for NASDAQ Stock Agent
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Callable, Optional
import json
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from src.services.logging_service import logging_service
from src.config.settings import settings

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic request/response logging"""
    
    def __init__(self, app: ASGIApp, log_requests: bool = True, log_responses: bool = True):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.excluded_paths = {'/health', '/docs', '/openapi.json', '/favicon.ico'}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details"""
        start_time = time.time()
        
        # Skip logging for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Capture request details
        request_data = await self._capture_request_data(request)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Capture response details
            response_data = self._capture_response_data(response)
            
            # Log the request/response asynchronously
            if self.log_requests or self.log_responses:
                asyncio.create_task(self._log_request_response(
                    request.url.path,
                    request.method,
                    request_data,
                    response_data,
                    response.status_code,
                    processing_time_ms
                ))
            
            return response
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Log the error
            asyncio.create_task(logging_service.log_error(e, {
                'context': 'request_processing',
                'path': request.url.path,
                'method': request.method,
                'processing_time_ms': processing_time_ms,
                'request_data': request_data
            }))
            
            raise
    
    async def _capture_request_data(self, request: Request) -> Dict[str, Any]:
        """Capture relevant request data for logging"""
        try:
            request_data = {
                'method': request.method,
                'url': str(request.url),
                'path': request.url.path,
                'query_params': dict(request.query_params),
                'headers': dict(request.headers),
                'client_ip': request.client.host if request.client else None,
                'user_agent': request.headers.get('user-agent'),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Capture request body for POST requests (with size limit)
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    body = await request.body()
                    if len(body) < 10000:  # Limit to 10KB
                        try:
                            request_data['body'] = json.loads(body.decode('utf-8'))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            request_data['body'] = body.decode('utf-8', errors='ignore')[:1000]
                    else:
                        request_data['body'] = f"<body too large: {len(body)} bytes>"
                except Exception:
                    request_data['body'] = "<could not read body>"
            
            # Remove sensitive headers
            sensitive_headers = {'authorization', 'cookie', 'x-api-key'}
            for header in sensitive_headers:
                if header in request_data['headers']:
                    request_data['headers'][header] = '<redacted>'
            
            return request_data
            
        except Exception as e:
            logger.error(f"Failed to capture request data: {e}")
            return {'error': 'failed_to_capture_request_data'}
    
    def _capture_response_data(self, response: Response) -> Dict[str, Any]:
        """Capture relevant response data for logging"""
        try:
            response_data = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Note: We don't capture response body here as it would require
            # intercepting the response stream, which is complex and may affect performance
            
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to capture response data: {e}")
            return {'error': 'failed_to_capture_response_data'}
    
    async def _log_request_response(self, endpoint: str, method: str, 
                                  request_data: Dict[str, Any], response_data: Dict[str, Any],
                                  status_code: int, processing_time_ms: int):
        """Log request/response data asynchronously"""
        try:
            await logging_service.log_api_request(
                endpoint=endpoint,
                method=method,
                request_data=request_data,
                response_data=response_data,
                status_code=status_code,
                processing_time_ms=processing_time_ms
            )
        except Exception as e:
            logger.error(f"Failed to log request/response: {e}")


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics = {
            'request_count': 0,
            'total_processing_time_ms': 0,
            'error_count': 0,
            'analysis_count': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'start_time': datetime.utcnow()
        }
        self.endpoint_metrics = {}
        self._lock = asyncio.Lock()
    
    async def record_request(self, endpoint: str, method: str, processing_time_ms: int, status_code: int):
        """Record request metrics"""
        async with self._lock:
            self.metrics['request_count'] += 1
            self.metrics['total_processing_time_ms'] += processing_time_ms
            
            if status_code >= 400:
                self.metrics['error_count'] += 1
            
            # Track per-endpoint metrics
            endpoint_key = f"{method} {endpoint}"
            if endpoint_key not in self.endpoint_metrics:
                self.endpoint_metrics[endpoint_key] = {
                    'count': 0,
                    'total_time_ms': 0,
                    'error_count': 0,
                    'avg_time_ms': 0
                }
            
            endpoint_stats = self.endpoint_metrics[endpoint_key]
            endpoint_stats['count'] += 1
            endpoint_stats['total_time_ms'] += processing_time_ms
            endpoint_stats['avg_time_ms'] = endpoint_stats['total_time_ms'] / endpoint_stats['count']
            
            if status_code >= 400:
                endpoint_stats['error_count'] += 1
    
    async def record_analysis(self):
        """Record successful analysis"""
        async with self._lock:
            self.metrics['analysis_count'] += 1
    
    async def record_cache_hit(self):
        """Record cache hit"""
        async with self._lock:
            self.metrics['cache_hits'] += 1
    
    async def record_cache_miss(self):
        """Record cache miss"""
        async with self._lock:
            self.metrics['cache_misses'] += 1
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        async with self._lock:
            uptime_seconds = (datetime.utcnow() - self.metrics['start_time']).total_seconds()
            
            metrics = self.metrics.copy()
            metrics.update({
                'uptime_seconds': uptime_seconds,
                'avg_processing_time_ms': (
                    self.metrics['total_processing_time_ms'] / self.metrics['request_count']
                    if self.metrics['request_count'] > 0 else 0
                ),
                'error_rate': (
                    self.metrics['error_count'] / self.metrics['request_count']
                    if self.metrics['request_count'] > 0 else 0
                ),
                'cache_hit_rate': (
                    self.metrics['cache_hits'] / (self.metrics['cache_hits'] + self.metrics['cache_misses'])
                    if (self.metrics['cache_hits'] + self.metrics['cache_misses']) > 0 else 0
                ),
                'requests_per_second': (
                    self.metrics['request_count'] / uptime_seconds
                    if uptime_seconds > 0 else 0
                ),
                'endpoint_metrics': self.endpoint_metrics.copy(),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return metrics
    
    async def reset_metrics(self):
        """Reset all metrics"""
        async with self._lock:
            self.metrics = {
                'request_count': 0,
                'total_processing_time_ms': 0,
                'error_count': 0,
                'analysis_count': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'start_time': datetime.utcnow()
            }
            self.endpoint_metrics.clear()


class HealthMonitor:
    """System health monitoring"""
    
    def __init__(self):
        self.health_checks = {}
        self.last_check_time = None
        self.check_interval_seconds = 300  # 5 minutes
    
    async def register_health_check(self, name: str, check_function: Callable):
        """Register a health check function"""
        self.health_checks[name] = check_function
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks"""
        try:
            health_status = {
                'overall_status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'checks': {}
            }
            
            # Run each health check
            for name, check_function in self.health_checks.items():
                try:
                    check_result = await check_function()
                    health_status['checks'][name] = check_result
                    
                    # Update overall status if any check is unhealthy
                    if isinstance(check_result, dict) and check_result.get('status') != 'healthy':
                        health_status['overall_status'] = 'degraded'
                        
                except Exception as e:
                    health_status['checks'][name] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
                    health_status['overall_status'] = 'unhealthy'
            
            self.last_check_time = datetime.utcnow()
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'overall_status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        try:
            # Get performance metrics
            performance_metrics = await performance_monitor.get_metrics()
            
            # Run health checks if needed
            if (not self.last_check_time or 
                (datetime.utcnow() - self.last_check_time).total_seconds() > self.check_interval_seconds):
                health_checks = await self.run_health_checks()
            else:
                health_checks = {'status': 'cached', 'last_check': self.last_check_time.isoformat()}
            
            return {
                'service': 'NASDAQ Stock Agent',
                'version': '1.0.0',
                'status': health_checks.get('overall_status', 'unknown'),
                'performance_metrics': performance_metrics,
                'health_checks': health_checks,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                'service': 'NASDAQ Stock Agent',
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


# Global monitoring instances
performance_monitor = PerformanceMonitor()
health_monitor = HealthMonitor()


class MonitoringService:
    """Comprehensive monitoring service"""
    
    def __init__(self):
        self.performance_monitor = performance_monitor
        self.health_monitor = health_monitor
        self.logging_service = logging_service
    
    async def initialize_monitoring(self):
        """Initialize monitoring with health checks"""
        try:
            # Register health checks for various services
            # Database health checks removed - no longer using MongoDB
            
            logger.info("Monitoring service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring: {e}")
    
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return await self.health_monitor.get_system_health()


# Global monitoring service instance
monitoring_service = MonitoringService()