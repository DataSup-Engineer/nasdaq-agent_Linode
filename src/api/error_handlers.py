"""
Comprehensive error handling for NASDAQ Stock Agent API
"""
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
from datetime import datetime
from typing import Dict, Any, Union
from src.api.middleware.validation import create_validation_error_response, create_custom_error_response
from src.services.logging_service import logging_service

logger = logging.getLogger(__name__)


class APIErrorHandler:
    """Centralized API error handling"""
    
    @staticmethod
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle Pydantic validation errors"""
        logger.warning(f"Validation error in {request.method} {request.url}: {exc}")
        
        # Log validation error
        try:
            await logging_service.log_error(exc, {
                'context': 'request_validation',
                'method': request.method,
                'path': str(request.url.path),
                'query_params': dict(request.query_params)
            })
        except Exception as log_error:
            logger.error(f"Failed to log validation error: {log_error}")
        
        # Create detailed validation error response
        error_response = create_validation_error_response(exc)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response
        )
    
    @staticmethod
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions"""
        logger.warning(f"HTTP exception in {request.method} {request.url}: {exc.status_code} - {exc.detail}")
        
        # Log HTTP error if it's a server error
        if exc.status_code >= 500:
            try:
                await logging_service.log_error(Exception(f"HTTP {exc.status_code}: {exc.detail}"), {
                    'context': 'http_exception',
                    'status_code': exc.status_code,
                    'method': request.method,
                    'path': str(request.url.path)
                })
            except Exception as log_error:
                logger.error(f"Failed to log HTTP error: {log_error}")
        
        # Ensure detail is properly formatted
        if isinstance(exc.detail, dict):
            detail = exc.detail
        else:
            detail = {
                "error_code": f"HTTP_{exc.status_code}",
                "error_message": str(exc.detail),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return JSONResponse(
            status_code=exc.status_code,
            content=detail
        )
    
    @staticmethod
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle general unhandled exceptions"""
        logger.error(f"Unhandled exception in {request.method} {request.url}: {exc}", exc_info=True)
        
        # Log the error
        try:
            await logging_service.log_error(exc, {
                'context': 'unhandled_exception',
                'method': request.method,
                'path': str(request.url.path),
                'query_params': dict(request.query_params)
            })
        except Exception as log_error:
            logger.error(f"Failed to log unhandled error: {log_error}")
        
        # Return generic error response
        error_response = create_custom_error_response(
            "INTERNAL_SERVER_ERROR",
            "An internal server error occurred. Please try again later.",
            {
                "path": str(request.url.path),
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )
    
    @staticmethod
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle ValueError exceptions"""
        logger.warning(f"Value error in {request.method} {request.url}: {exc}")
        
        # Log value error
        try:
            await logging_service.log_error(exc, {
                'context': 'value_error',
                'method': request.method,
                'path': str(request.url.path)
            })
        except Exception as log_error:
            logger.error(f"Failed to log value error: {log_error}")
        
        error_response = create_custom_error_response(
            "INVALID_INPUT",
            str(exc),
            {
                "suggestions": [
                    "Check your input parameters",
                    "Ensure all required fields are provided",
                    "Verify data formats and types"
                ]
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response
        )
    
    @staticmethod
    async def timeout_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle timeout errors"""
        logger.error(f"Timeout error in {request.method} {request.url}: {exc}")
        
        # Log timeout error
        try:
            await logging_service.log_error(exc, {
                'context': 'timeout_error',
                'method': request.method,
                'path': str(request.url.path)
            })
        except Exception as log_error:
            logger.error(f"Failed to log timeout error: {log_error}")
        
        error_response = create_custom_error_response(
            "REQUEST_TIMEOUT",
            "The request timed out. Please try again later.",
            {
                "suggestions": [
                    "Try again in a few moments",
                    "Check if the service is experiencing high load",
                    "Consider simplifying your query"
                ]
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            content=error_response
        )


class BusinessLogicErrorHandler:
    """Handle business logic specific errors"""
    
    @staticmethod
    def create_stock_not_found_error(query: str) -> HTTPException:
        """Create error for stock not found"""
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_custom_error_response(
                "STOCK_NOT_FOUND",
                f"Could not find stock information for '{query}'",
                {
                    "query": query,
                    "suggestions": [
                        "Try using the full company name (e.g., 'Apple' instead of 'Apl')",
                        "Use the official ticker symbol (e.g., 'AAPL')",
                        "Check if the company is listed on NASDAQ",
                        "Verify the spelling of the company name"
                    ]
                }
            )
        )
    
    @staticmethod
    def create_market_data_error(ticker: str, reason: str = None) -> HTTPException:
        """Create error for market data retrieval failure"""
        message = f"Failed to retrieve market data for {ticker}"
        if reason:
            message += f": {reason}"
        
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_custom_error_response(
                "MARKET_DATA_UNAVAILABLE",
                message,
                {
                    "ticker": ticker,
                    "suggestions": [
                        "Try again in a few moments",
                        "Check if markets are currently open",
                        "Verify the ticker symbol is correct"
                    ]
                }
            )
        )
    
    @staticmethod
    def create_analysis_error(ticker: str, reason: str = None) -> HTTPException:
        """Create error for analysis failure"""
        message = f"Failed to analyze stock {ticker}"
        if reason:
            message += f": {reason}"
        
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_custom_error_response(
                "ANALYSIS_FAILED",
                message,
                {
                    "ticker": ticker,
                    "suggestions": [
                        "Try again with a different query",
                        "Check if the stock is actively traded",
                        "Contact support if the problem persists"
                    ]
                }
            )
        )
    
    @staticmethod
    def create_rate_limit_error(reset_time: float) -> HTTPException:
        """Create error for rate limit exceeded"""
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=create_custom_error_response(
                "RATE_LIMIT_EXCEEDED",
                "Too many requests. Please slow down.",
                {
                    "reset_time": reset_time,
                    "suggestions": [
                        "Wait before making another request",
                        "Reduce the frequency of your requests",
                        "Consider caching responses on your end"
                    ]
                }
            )
        )
    
    @staticmethod
    def create_invalid_query_error(query: str, suggestions: list = None) -> HTTPException:
        """Create error for invalid query"""
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_custom_error_response(
                "INVALID_QUERY",
                f"Invalid query: '{query}'",
                {
                    "query": query,
                    "suggestions": suggestions or [
                        "Use a company name like 'Apple' or 'Microsoft'",
                        "Use a ticker symbol like 'AAPL' or 'MSFT'",
                        "Ask a question like 'What do you think about Tesla?'"
                    ]
                }
            )
        )


def setup_error_handlers(app):
    """Setup all error handlers for the FastAPI app"""
    
    # Validation errors
    app.add_exception_handler(
        RequestValidationError,
        APIErrorHandler.validation_exception_handler
    )
    
    # HTTP exceptions
    app.add_exception_handler(
        HTTPException,
        APIErrorHandler.http_exception_handler
    )
    
    # Value errors
    app.add_exception_handler(
        ValueError,
        APIErrorHandler.value_error_handler
    )
    
    # Timeout errors
    app.add_exception_handler(
        TimeoutError,
        APIErrorHandler.timeout_error_handler
    )
    
    # General exceptions (catch-all)
    app.add_exception_handler(
        Exception,
        APIErrorHandler.general_exception_handler
    )
    
    logger.info("Error handlers configured successfully")


# Error response templates
ERROR_RESPONSES = {
    400: {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "example": {
                    "error_code": "INVALID_INPUT",
                    "error_message": "Invalid input provided",
                    "suggestions": ["Check your input parameters"],
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
        }
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/json": {
                "example": {
                    "error_code": "STOCK_NOT_FOUND",
                    "error_message": "Could not find stock information",
                    "suggestions": ["Try using the full company name"],
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
        }
    },
    422: {
        "description": "Validation Error",
        "content": {
            "application/json": {
                "example": {
                    "error_code": "VALIDATION_ERROR",
                    "error_message": "Request validation failed",
                    "validation_errors": [
                        {
                            "field": "query",
                            "message": "field required",
                            "type": "value_error.missing"
                        }
                    ],
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
        }
    },
    429: {
        "description": "Too Many Requests",
        "content": {
            "application/json": {
                "example": {
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "error_message": "Too many requests. Please slow down.",
                    "reset_time": 1640995200.0,
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
        }
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "error_message": "An internal server error occurred",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
        }
    },
    503: {
        "description": "Service Unavailable",
        "content": {
            "application/json": {
                "example": {
                    "error_code": "MARKET_DATA_UNAVAILABLE",
                    "error_message": "Market data service is temporarily unavailable",
                    "suggestions": ["Try again in a few moments"],
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
        }
    }
}