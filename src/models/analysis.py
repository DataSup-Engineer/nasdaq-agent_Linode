"""
Analysis and recommendation models for NASDAQ Stock Agent
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
import uuid
from enum import Enum


class RecommendationType(str, Enum):
    """Investment recommendation types"""
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"


@dataclass
class InvestmentRecommendation:
    """AI-generated investment recommendation"""
    recommendation: RecommendationType
    confidence_score: float  # 0-100
    reasoning: str
    key_factors: List[str]
    risk_assessment: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate investment recommendation"""
        if not isinstance(self.recommendation, RecommendationType):
            raise ValueError("Recommendation must be Buy, Hold, or Sell")
        if not 0 <= self.confidence_score <= 100:
            raise ValueError("Confidence score must be between 0 and 100")
        if not self.reasoning or not self.reasoning.strip():
            raise ValueError("Reasoning cannot be empty")
        if not self.key_factors or len(self.key_factors) == 0:
            raise ValueError("Key factors cannot be empty")
        if not self.risk_assessment or not self.risk_assessment.strip():
            raise ValueError("Risk assessment cannot be empty")


@dataclass
class StockAnalysis:
    """Complete stock analysis result"""
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str = ""
    company_name: str = ""
    query_text: str = ""
    market_data: Optional[object] = None  # MarketData object
    recommendation: Optional[InvestmentRecommendation] = None
    summary: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_time_ms: int = 0
    
    def __post_init__(self):
        """Validate stock analysis"""
        if not self.analysis_id:
            self.analysis_id = str(uuid.uuid4())
        if self.processing_time_ms < 0:
            raise ValueError("Processing time cannot be negative")


@dataclass
class AgentFactCard:
    """Agent fact card for registry"""
    agent_id: str
    agent_name: str
    agent_domain: str
    agent_specialization: str
    agent_description: str
    agent_capabilities: List[str]
    registry_url: str
    public_url: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate agent fact card"""
        if not self.agent_id or not self.agent_id.strip():
            raise ValueError("Agent ID cannot be empty")
        if not self.agent_name or not self.agent_name.strip():
            raise ValueError("Agent name cannot be empty")
        if not self.agent_domain or not self.agent_domain.strip():
            raise ValueError("Agent domain cannot be empty")
        if not self.agent_specialization or not self.agent_specialization.strip():
            raise ValueError("Agent specialization cannot be empty")
        if not self.agent_description or not self.agent_description.strip():
            raise ValueError("Agent description cannot be empty")
        if not self.agent_capabilities or len(self.agent_capabilities) == 0:
            raise ValueError("Agent capabilities cannot be empty")
        if not self.registry_url or not self.registry_url.strip():
            raise ValueError("Registry URL cannot be empty")
        if not self.public_url or not self.public_url.strip():
            raise ValueError("Public URL cannot be empty")


class AnalysisRequest(BaseModel):
    """Request model for stock analysis API"""
    query: str = Field(..., description="Natural language query about a stock", min_length=1, max_length=500)
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


class AnalysisResponse(BaseModel):
    """Response model for stock analysis API"""
    analysis_id: str
    ticker: str
    company_name: str
    current_price: float
    price_change_percentage: float
    recommendation: str
    confidence_score: float
    reasoning: str
    key_factors: List[str]
    risk_assessment: str
    summary: str
    processing_time_ms: int
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    error_code: str
    error_message: str
    details: Optional[dict] = None
    suggestions: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }