"""
Market data models for NASDAQ Stock Agent
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
import uuid


@dataclass
class PricePoint:
    """Individual price point with OHLCV data"""
    date: datetime
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    volume: int
    
    def __post_init__(self):
        """Validate price point data"""
        if self.high_price < max(self.open_price, self.close_price):
            raise ValueError("High price cannot be less than open or close price")
        if self.low_price > min(self.open_price, self.close_price):
            raise ValueError("Low price cannot be greater than open or close price")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")


@dataclass
class MarketData:
    """Comprehensive market data for a stock"""
    ticker: str
    company_name: str
    current_price: float
    daily_high: float
    daily_low: float
    volume: int
    historical_prices: List[PricePoint]
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate market data"""
        if not self.ticker or not self.ticker.strip():
            raise ValueError("Ticker symbol cannot be empty")
        if not self.company_name or not self.company_name.strip():
            raise ValueError("Company name cannot be empty")
        if self.current_price <= 0:
            raise ValueError("Current price must be positive")
        if self.daily_high < self.current_price:
            raise ValueError("Daily high cannot be less than current price")
        if self.daily_low > self.current_price:
            raise ValueError("Daily low cannot be greater than current price")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")
        if len(self.historical_prices) == 0:
            raise ValueError("Historical prices cannot be empty")
    
    def get_price_change_percentage(self) -> float:
        """Calculate price change percentage from previous close"""
        if not self.historical_prices:
            return 0.0
        
        # Get the most recent historical price (previous day's close)
        previous_close = self.historical_prices[-1].close_price
        return ((self.current_price - previous_close) / previous_close) * 100
    
    def get_average_volume(self, days: int = 30) -> float:
        """Calculate average volume over specified days"""
        if not self.historical_prices:
            return 0.0
        
        recent_prices = self.historical_prices[-days:] if len(self.historical_prices) >= days else self.historical_prices
        total_volume = sum(price_point.volume for price_point in recent_prices)
        return total_volume / len(recent_prices)


class MarketDataRequest(BaseModel):
    """Request model for market data API"""
    company_name: str = Field(..., description="Company name or ticker symbol", min_length=1, max_length=100)
    
    @validator('company_name')
    def validate_company_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Company name cannot be empty')
        return v.strip()


class MarketDataResponse(BaseModel):
    """Response model for market data API"""
    ticker: str
    company_name: str
    current_price: float
    daily_high: float
    daily_low: float
    volume: int
    price_change_percentage: float
    average_volume_30d: float
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }