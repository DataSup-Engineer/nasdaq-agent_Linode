"""
Request validation middleware and utilities for NASDAQ Stock Agent
"""
import re
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from pydantic import BaseModel, validator, ValidationError
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation and sanitization"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        self.blocked_patterns = [
            r'<script.*?>.*?</script>',  # XSS prevention
            r'javascript:',
            r'on\w+\s*=',  # Event handlers
            r'eval\s*\(',
            r'expression\s*\('
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Validate and sanitize incoming requests"""
        try:
            # Check request size
            content_length = request.headers.get('content-length')
            if content_length and int(content_length) > self.max_request_size:
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error_code": "REQUEST_TOO_LARGE",
                        "error_message": f"Request size exceeds maximum allowed size of {self.max_request_size} bytes",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            
            # Validate request path
            if not self._is_valid_path(request.url.path):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "INVALID_PATH",
                        "error_message": "Request path contains invalid characters",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            
            # Process request
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Validation middleware error: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error_code": "VALIDATION_ERROR",
                    "error_message": "Request validation failed",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    def _is_valid_path(self, path: str) -> bool:
        """Validate request path for security"""
        # Check for path traversal attempts
        if '..' in path or '//' in path:
            return False
        
        # Check for suspicious patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return False
        
        return True


class QueryValidator:
    """Validator for stock analysis queries"""
    
    @staticmethod
    def validate_stock_query(query: str) -> Dict[str, Any]:
        """Validate and sanitize stock analysis query"""
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        
        # Remove leading/trailing whitespace
        query = query.strip()
        
        # Check length limits
        if len(query) < 1:
            raise ValueError("Query cannot be empty")
        
        if len(query) > 500:
            raise ValueError("Query exceeds maximum length of 500 characters")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'eval\s*\(',
            r'expression\s*\(',
            r'<.*?>',  # HTML tags
            r'DROP\s+TABLE',  # SQL injection
            r'DELETE\s+FROM',
            r'INSERT\s+INTO',
            r'UPDATE\s+.*SET'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValueError(f"Query contains potentially malicious content")
        
        # Sanitize query
        sanitized_query = QueryValidator._sanitize_query(query)
        
        return {
            "original_query": query,
            "sanitized_query": sanitized_query,
            "is_valid": True,
            "validation_timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def _sanitize_query(query: str) -> str:
        """Sanitize query string"""
        # Remove HTML tags
        query = re.sub(r'<[^>]+>', '', query)
        
        # Remove excessive whitespace
        query = re.sub(r'\s+', ' ', query)
        
        # Remove control characters
        query = ''.join(char for char in query if ord(char) >= 32 or char in '\t\n\r')
        
        return query.strip()
    
    @staticmethod
    def validate_ticker_symbol(ticker: str) -> bool:
        """Validate ticker symbol format"""
        if not ticker or not isinstance(ticker, str):
            return False
        
        ticker = ticker.strip().upper()
        
        # Basic ticker validation: 1-10 characters, letters/numbers/dots/hyphens
        if not re.match(r'^[A-Z0-9.-]{1,10}$', ticker):
            return False
        
        return True


class ParameterValidator:
    """Validator for API parameters"""
    
    @staticmethod
    def validate_limit_parameter(limit: Optional[int], max_limit: int = 1000) -> int:
        """Validate and normalize limit parameter"""
        if limit is None:
            return 100  # Default limit
        
        if not isinstance(limit, int):
            raise ValueError("Limit must be an integer")
        
        if limit < 1:
            return 1
        
        if limit > max_limit:
            return max_limit
        
        return limit
    
    @staticmethod
    def validate_date_range(start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict[str, Any]:
        """Validate date range parameters"""
        validation_result = {
            "start_date": start_date,
            "end_date": end_date,
            "is_valid": True,
            "warnings": []
        }
        
        if start_date and end_date:
            if start_date > end_date:
                raise ValueError("Start date cannot be after end date")
            
            # Check if date range is too large (more than 1 year)
            if (end_date - start_date).days > 365:
                validation_result["warnings"].append("Date range exceeds 1 year, results may be limited")
        
        # Check if dates are in the future
        now = datetime.utcnow()
        if start_date and start_date > now:
            validation_result["warnings"].append("Start date is in the future")
        
        if end_date and end_date > now:
            validation_result["warnings"].append("End date is in the future")
        
        return validation_result
    
    @staticmethod
    def validate_analysis_id(analysis_id: str) -> bool:
        """Validate analysis ID format"""
        if not analysis_id or not isinstance(analysis_id, str):
            return False
        
        # Check for UUID format or similar
        if len(analysis_id) < 8 or len(analysis_id) > 100:
            return False
        
        # Allow alphanumeric characters, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', analysis_id):
            return False
        
        return True


def create_validation_error_response(error: ValidationError) -> Dict[str, Any]:
    """Create standardized validation error response"""
    errors = []
    
    for error_detail in error.errors():
        field = " -> ".join(str(loc) for loc in error_detail["loc"])
        message = error_detail["msg"]
        error_type = error_detail["type"]
        
        errors.append({
            "field": field,
            "message": message,
            "type": error_type
        })
    
    return {
        "error_code": "VALIDATION_ERROR",
        "error_message": "Request validation failed",
        "validation_errors": errors,
        "timestamp": datetime.utcnow().isoformat()
    }


def create_custom_error_response(error_code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create standardized custom error response"""
    response = {
        "error_code": error_code,
        "error_message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        response.update(details)
    
    return response


class RateLimitValidator:
    """Rate limiting validation"""
    
    def __init__(self):
        self.request_counts = {}  # Simple in-memory rate limiting
        self.rate_limit = 100  # requests per minute
        self.time_window = 60  # seconds
    
    def check_rate_limit(self, client_ip: str) -> bool:
        """Check if client has exceeded rate limit"""
        now = datetime.utcnow().timestamp()
        
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        # Remove old requests outside time window
        self.request_counts[client_ip] = [
            timestamp for timestamp in self.request_counts[client_ip]
            if now - timestamp < self.time_window
        ]
        
        # Check if rate limit exceeded
        if len(self.request_counts[client_ip]) >= self.rate_limit:
            return False
        
        # Add current request
        self.request_counts[client_ip].append(now)
        return True
    
    def get_rate_limit_info(self, client_ip: str) -> Dict[str, Any]:
        """Get rate limit information for client"""
        now = datetime.utcnow().timestamp()
        
        if client_ip not in self.request_counts:
            return {
                "requests_made": 0,
                "requests_remaining": self.rate_limit,
                "reset_time": now + self.time_window
            }
        
        # Clean old requests
        self.request_counts[client_ip] = [
            timestamp for timestamp in self.request_counts[client_ip]
            if now - timestamp < self.time_window
        ]
        
        requests_made = len(self.request_counts[client_ip])
        
        return {
            "requests_made": requests_made,
            "requests_remaining": max(0, self.rate_limit - requests_made),
            "reset_time": now + self.time_window
        }


# Global rate limiter instance
rate_limiter = RateLimitValidator()