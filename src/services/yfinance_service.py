"""
Yahoo Finance integration service for NASDAQ Stock Agent
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
from src.models.market_data import MarketData, PricePoint
from src.config.settings import settings

logger = logging.getLogger(__name__)


class YFinanceService:
    """Service for fetching market data from Yahoo Finance"""
    
    def __init__(self):
        self.timeout = settings.yfinance_timeout
        
    async def get_current_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch current market data for a ticker symbol"""
        try:
            ticker = ticker.upper().strip()
            
            # Validate ticker format
            if not self._is_valid_ticker_format(ticker):
                raise ValueError(f"Invalid ticker format: {ticker}")
            
            # Create yfinance Ticker object
            stock = yf.Ticker(ticker)
            
            # Get current info
            info = stock.info
            
            if not info or 'regularMarketPrice' not in info:
                raise ValueError(f"No data found for ticker: {ticker}")
            
            # Extract current market data
            current_data = {
                'ticker': ticker,
                'company_name': info.get('longName', info.get('shortName', ticker)),
                'current_price': float(info.get('regularMarketPrice', 0)),
                'daily_high': float(info.get('dayHigh', info.get('regularMarketDayHigh', 0))),
                'daily_low': float(info.get('dayLow', info.get('regularMarketDayLow', 0))),
                'volume': int(info.get('volume', info.get('regularMarketVolume', 0))),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'previous_close': float(info.get('previousClose', 0)),
                'open_price': float(info.get('open', info.get('regularMarketOpen', 0))),
                'timestamp': datetime.utcnow()
            }
            
            logger.info(f"Retrieved current data for {ticker}: ${current_data['current_price']}")
            return current_data
            
        except Exception as e:
            logger.error(f"Failed to fetch current data for {ticker}: {e}")
            raise
    
    async def get_historical_data(self, ticker: str, months: int = 6) -> List[Dict[str, Any]]:
        """Fetch historical market data for specified number of months"""
        try:
            ticker = ticker.upper().strip()
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)  # Approximate months to days
            
            # Create yfinance Ticker object
            stock = yf.Ticker(ticker)
            
            # Get historical data
            hist_data = stock.history(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval='1d'
            )
            
            if hist_data.empty:
                raise ValueError(f"No historical data found for ticker: {ticker}")
            
            # Convert to list of dictionaries
            historical_prices = []
            for date, row in hist_data.iterrows():
                price_point = {
                    'date': date.to_pydatetime(),
                    'open_price': float(row['Open']),
                    'close_price': float(row['Close']),
                    'high_price': float(row['High']),
                    'low_price': float(row['Low']),
                    'volume': int(row['Volume'])
                }
                historical_prices.append(price_point)
            
            logger.info(f"Retrieved {len(historical_prices)} historical data points for {ticker}")
            return historical_prices
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data for {ticker}: {e}")
            raise
    
    async def get_comprehensive_data(self, ticker: str) -> MarketData:
        """Get both current and historical data combined into MarketData object"""
        try:
            # Fetch current and historical data concurrently
            current_data = await self.get_current_data(ticker)
            historical_data = await self.get_historical_data(ticker, months=6)
            
            # Convert historical data to PricePoint objects
            historical_prices = []
            for price_data in historical_data:
                price_point = PricePoint(
                    date=price_data['date'],
                    open_price=price_data['open_price'],
                    close_price=price_data['close_price'],
                    high_price=price_data['high_price'],
                    low_price=price_data['low_price'],
                    volume=price_data['volume']
                )
                historical_prices.append(price_point)
            
            # Create MarketData object
            market_data = MarketData(
                ticker=current_data['ticker'],
                company_name=current_data['company_name'],
                current_price=current_data['current_price'],
                daily_high=current_data['daily_high'],
                daily_low=current_data['daily_low'],
                volume=current_data['volume'],
                historical_prices=historical_prices,
                market_cap=current_data['market_cap'],
                pe_ratio=current_data['pe_ratio'],
                timestamp=current_data['timestamp']
            )
            
            logger.info(f"Retrieved comprehensive data for {ticker}")
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to fetch comprehensive data for {ticker}: {e}")
            raise
    
    async def validate_ticker_exists(self, ticker: str) -> bool:
        """Validate that a ticker symbol exists and has data"""
        try:
            ticker = ticker.upper().strip()
            
            # Basic format validation
            if not self._is_valid_ticker_format(ticker):
                return False
            
            # Try to fetch basic info
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Check if we got valid data
            if not info or len(info) < 5:  # Minimal info should have more than 5 fields
                return False
            
            # Check for essential fields
            essential_fields = ['regularMarketPrice', 'longName', 'shortName']
            has_essential = any(field in info for field in essential_fields)
            
            return has_essential
            
        except Exception as e:
            logger.warning(f"Ticker validation failed for {ticker}: {e}")
            return False
    
    def _is_valid_ticker_format(self, ticker: str) -> bool:
        """Validate ticker symbol format"""
        if not ticker or not isinstance(ticker, str):
            return False
        
        ticker = ticker.strip().upper()
        
        # Basic validation: 1-5 characters, letters only (for most stocks)
        # Some tickers may have numbers or special characters, but this covers most cases
        if len(ticker) < 1 or len(ticker) > 10:
            return False
        
        # Allow letters, numbers, and some special characters common in tickers
        allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-')
        return all(c in allowed_chars for c in ticker)
    
    async def search_ticker_by_name(self, company_name: str) -> List[Dict[str, str]]:
        """Search for ticker symbols by company name (basic implementation)"""
        try:
            # This is a simplified implementation
            # In a production system, you might want to use a more comprehensive database
            # or API for company name to ticker mapping
            
            company_name = company_name.strip().lower()
            
            # Common company name to ticker mappings for NASDAQ stocks
            common_mappings = {
                'apple': 'AAPL',
                'microsoft': 'MSFT',
                'amazon': 'AMZN',
                'google': 'GOOGL',
                'alphabet': 'GOOGL',
                'tesla': 'TSLA',
                'meta': 'META',
                'facebook': 'META',
                'netflix': 'NFLX',
                'nvidia': 'NVDA',
                'intel': 'INTC',
                'cisco': 'CSCO',
                'oracle': 'ORCL',
                'salesforce': 'CRM',
                'adobe': 'ADBE',
                'paypal': 'PYPL',
                'zoom': 'ZM',
                'slack': 'WORK',
                'spotify': 'SPOT',
                'uber': 'UBER',
                'lyft': 'LYFT',
                'airbnb': 'ABNB',
                'doordash': 'DASH',
                'snowflake': 'SNOW',
                'palantir': 'PLTR',
                'robinhood': 'HOOD'
            }
            
            results = []
            
            # Direct match
            if company_name in common_mappings:
                ticker = common_mappings[company_name]
                if await self.validate_ticker_exists(ticker):
                    results.append({
                        'ticker': ticker,
                        'company_name': company_name.title(),
                        'match_type': 'exact'
                    })
            
            # Partial matches
            for name, ticker in common_mappings.items():
                if company_name in name or name in company_name:
                    if await self.validate_ticker_exists(ticker):
                        results.append({
                            'ticker': ticker,
                            'company_name': name.title(),
                            'match_type': 'partial'
                        })
            
            # Remove duplicates
            seen_tickers = set()
            unique_results = []
            for result in results:
                if result['ticker'] not in seen_tickers:
                    seen_tickers.add(result['ticker'])
                    unique_results.append(result)
            
            logger.info(f"Found {len(unique_results)} ticker matches for '{company_name}'")
            return unique_results[:5]  # Return top 5 matches
            
        except Exception as e:
            logger.error(f"Failed to search ticker for company name '{company_name}': {e}")
            return []
    
    async def get_market_status(self) -> Dict[str, Any]:
        """Get current market status (open/closed)"""
        try:
            # Use a major index to determine market status
            spy = yf.Ticker("SPY")  # S&P 500 ETF
            info = spy.info
            
            # Get market state
            market_state = info.get('marketState', 'UNKNOWN')
            
            # Get market times
            regular_market_time = info.get('regularMarketTime')
            
            status = {
                'market_state': market_state,
                'is_open': market_state == 'REGULAR',
                'last_update': datetime.fromtimestamp(regular_market_time) if regular_market_time else None,
                'timestamp': datetime.utcnow()
            }
            
            logger.info(f"Market status: {market_state}")
            return status
            
        except Exception as e:
            logger.error(f"Failed to get market status: {e}")
            return {
                'market_state': 'UNKNOWN',
                'is_open': False,
                'last_update': None,
                'timestamp': datetime.utcnow()
            }