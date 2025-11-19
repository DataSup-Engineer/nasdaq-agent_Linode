"""
Logging models for NASDAQ Stock Agent
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid


@dataclass
class AnalysisLogEntry:
    """Log entry for stock analysis operations"""
    analysis_id: str
    user_query: str
    ticker_symbol: str
    company_name: str
    recommendation: str
    confidence_score: float
    processing_time_ms: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    
    def __post_init__(self):
        """Validate log entry"""
        if not self.analysis_id or not self.analysis_id.strip():
            raise ValueError("Analysis ID cannot be empty")
        if not self.user_query or not self.user_query.strip():
            raise ValueError("User query cannot be empty")
        if not self.ticker_symbol or not self.ticker_symbol.strip():
            raise ValueError("Ticker symbol cannot be empty")
        if not self.company_name or not self.company_name.strip():
            raise ValueError("Company name cannot be empty")
        if not self.recommendation or not self.recommendation.strip():
            raise ValueError("Recommendation cannot be empty")
        if not 0 <= self.confidence_score <= 100:
            raise ValueError("Confidence score must be between 0 and 100")
        if self.processing_time_ms < 0:
            raise ValueError("Processing time cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            "analysis_id": self.analysis_id,
            "user_query": self.user_query,
            "ticker_symbol": self.ticker_symbol,
            "company_name": self.company_name,
            "recommendation": self.recommendation,
            "confidence_score": self.confidence_score,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp,
            "expires_at": self.expires_at
        }


@dataclass
class ErrorLogEntry:
    """Log entry for system errors"""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_type: str = ""
    error_message: str = ""
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    
    def __post_init__(self):
        """Validate error log entry"""
        if not self.error_type or not self.error_type.strip():
            raise ValueError("Error type cannot be empty")
        if not self.error_message or not self.error_message.strip():
            raise ValueError("Error message cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "timestamp": self.timestamp,
            "expires_at": self.expires_at
        }


class LogQueryRequest(BaseModel):
    """Request model for querying logs"""
    analysis_id: Optional[str] = Field(None, description="Specific analysis ID to retrieve")
    start_date: Optional[datetime] = Field(None, description="Start date for log query")
    end_date: Optional[datetime] = Field(None, description="End date for log query")
    ticker_symbol: Optional[str] = Field(None, description="Filter by ticker symbol")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LogQueryResponse(BaseModel):
    """Response model for log queries"""
    total_count: int
    entries: list
    query_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }