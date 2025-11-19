"""
Comprehensive logging service for NASDAQ Stock Agent with file-based logging
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import logging
import traceback
import json
import os
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path
from src.models.analysis import StockAnalysis, AnalysisRequest, AnalysisResponse
from src.config.settings import settings

logger = logging.getLogger(__name__)


class LoggingService:
    """Comprehensive logging service with file-based storage"""
    
    def __init__(self):
        self.logs_dir = Path("logs")
        self.analyses_logger = None
        self.errors_logger = None
        self._setup_file_loggers()
    
    def _setup_file_loggers(self):
        """Setup file-based loggers with rotation"""
        try:
            # Ensure logs directory exists
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Setup analyses logger
            self.analyses_logger = logging.getLogger('analyses')
            self.analyses_logger.setLevel(logging.INFO)
            self.analyses_logger.propagate = False
            
            analyses_handler = RotatingFileHandler(
                self.logs_dir / 'analyses.jsonl',
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            analyses_handler.setFormatter(logging.Formatter('%(message)s'))
            self.analyses_logger.addHandler(analyses_handler)
            
            # Setup errors logger
            self.errors_logger = logging.getLogger('errors')
            self.errors_logger.setLevel(logging.ERROR)
            self.errors_logger.propagate = False
            
            errors_handler = RotatingFileHandler(
                self.logs_dir / 'errors.jsonl',
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            errors_handler.setFormatter(logging.Formatter('%(message)s'))
            self.errors_logger.addHandler(errors_handler)
            
            logger.info("File-based logging initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup file loggers: {e}")
            raise
    
    async def log_analysis_request(self, request: AnalysisRequest, response: AnalysisResponse) -> str:
        """Log a complete analysis request and response"""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "analysis_id": response.analysis_id,
                "user_query": request.query,
                "ticker_symbol": response.ticker,
                "company_name": response.company_name,
                "recommendation": response.recommendation,
                "confidence_score": response.confidence_score,
                "processing_time_ms": response.processing_time_ms
            }
            
            # Write JSON line to file
            self.analyses_logger.info(json.dumps(log_entry))
            
            logger.info(f"Analysis logged: {response.analysis_id} for {response.ticker}")
            return response.analysis_id
            
        except Exception as e:
            logger.error(f"Failed to log analysis request: {e}")
            # Fallback to console logging
            logger.error(f"Analysis data: {response.analysis_id} - {response.ticker}")
            return "failed_to_log"
    
    async def log_stock_analysis(self, stock_analysis: StockAnalysis) -> str:
        """Log a StockAnalysis object"""
        try:
            if not stock_analysis.recommendation:
                # Create a default log entry for failed analysis
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "analysis_id": stock_analysis.analysis_id,
                    "user_query": stock_analysis.query_text,
                    "ticker_symbol": stock_analysis.ticker,
                    "company_name": stock_analysis.company_name,
                    "recommendation": "Error",
                    "confidence_score": 0.0,
                    "processing_time_ms": stock_analysis.processing_time_ms
                }
            else:
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "analysis_id": stock_analysis.analysis_id,
                    "user_query": stock_analysis.query_text,
                    "ticker_symbol": stock_analysis.ticker,
                    "company_name": stock_analysis.company_name,
                    "recommendation": stock_analysis.recommendation.recommendation.value,
                    "confidence_score": stock_analysis.recommendation.confidence_score,
                    "processing_time_ms": stock_analysis.processing_time_ms
                }
            
            # Write JSON line to file
            self.analyses_logger.info(json.dumps(log_entry))
            
            logger.info(f"Stock analysis logged: {stock_analysis.analysis_id}")
            return stock_analysis.analysis_id
            
        except Exception as e:
            logger.error(f"Failed to log stock analysis: {e}")
            # Fallback to console logging
            logger.error(f"Stock analysis data: {stock_analysis.analysis_id} - {stock_analysis.ticker}")
            return "failed_to_log"
    
    async def log_error(self, error: Exception, context: Dict[str, Any] = None) -> str:
        """Log an error with context information"""
        try:
            error_id = str(uuid.uuid4())
            
            error_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "error_id": error_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "stack_trace": traceback.format_exc(),
                "context": context or {}
            }
            
            # Write JSON line to file
            self.errors_logger.error(json.dumps(error_entry))
            
            logger.error(f"Error logged: {error_id} - {error_entry['error_message']}")
            return error_id
            
        except Exception as e:
            # If we can't log to file, at least log to application logger
            logger.critical(f"Failed to log error to file: {e}. Original error: {error}")
            return "failed_to_log"
    
    async def log_api_request(self, endpoint: str, method: str, request_data: Dict[str, Any], 
                             response_data: Dict[str, Any], status_code: int, 
                             processing_time_ms: int) -> str:
        """Log API request and response"""
        try:
            log_id = str(uuid.uuid4())
            
            # Create a custom log entry for API requests
            api_log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'log_id': log_id,
                'log_type': 'api_request',
                'endpoint': endpoint,
                'method': method,
                'request_data': request_data,
                'response_data': response_data,
                'status_code': status_code,
                'processing_time_ms': processing_time_ms
            }
            
            # Write JSON line to file
            self.errors_logger.info(json.dumps(api_log_entry))
            
            logger.info(f"API request logged: {method} {endpoint} - {status_code} ({processing_time_ms}ms)")
            return log_id
            
        except Exception as e:
            logger.error(f"Failed to log API request: {e}")
            return "failed_to_log"


# Global logging service instance
logging_service = LoggingService()
