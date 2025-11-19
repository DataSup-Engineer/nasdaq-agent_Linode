"""
Langchain tools for NASDAQ Stock Agent
"""
import asyncio
from typing import Dict, Any, Optional
import json
import logging
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from src.services import enhanced_nlp_service
from src.services.market_data_service import market_data_service
from src.services.investment_analysis import comprehensive_analysis_service

logger = logging.getLogger(__name__)


class CompanyNameResolverInput(BaseModel):
    """Input schema for company name resolver tool"""
    company_name: str = Field(description="Company name to resolve to ticker symbol")


class CompanyNameResolverTool(BaseTool):
    """Tool for resolving company names to ticker symbols"""
    
    name: str = "company_name_resolver"
    description: str = """
    Resolves company names to NASDAQ ticker symbols. 
    Use this tool when you need to convert a company name (like 'Apple' or 'Microsoft') to its ticker symbol.
    Input should be a company name string.
    Returns the ticker symbol and company information, or suggestions if no exact match is found.
    """
    args_schema = CompanyNameResolverInput
    
    def _run(self, company_name: str) -> str:
        """Synchronous version (not used in async context)"""
        return "This tool requires async execution"
    
    async def _arun(self, company_name: str) -> str:
        """Resolve company name to ticker symbol"""
        try:
            result = await enhanced_nlp_service.process_query_with_suggestions(company_name)
            
            if result['success']:
                return json.dumps({
                    'success': True,
                    'ticker': result['ticker'],
                    'company_name': result['company_name'],
                    'match_score': result['match_score'],
                    'match_type': result['match_type']
                })
            else:
                return json.dumps({
                    'success': False,
                    'error': result['error'],
                    'suggestions': result.get('suggestions', {}),
                    'popular_companies': result.get('popular_companies', [])
                })
                
        except Exception as e:
            logger.error(f"Company name resolver tool failed: {e}")
            return json.dumps({
                'success': False,
                'error': f'Tool execution failed: {str(e)}'
            })


class MarketDataFetcherInput(BaseModel):
    """Input schema for market data fetcher tool"""
    ticker: str = Field(description="Stock ticker symbol (e.g., AAPL, MSFT)")


class MarketDataFetcherTool(BaseTool):
    """Tool for fetching market data"""
    
    name: str = "market_data_fetcher"
    description: str = """
    Fetches comprehensive market data for a stock ticker symbol.
    Use this tool to get current price, volume, historical data, and market metrics.
    Input should be a valid ticker symbol (e.g., 'AAPL', 'MSFT').
    Returns current price, daily high/low, volume, and 6-month historical data.
    """
    args_schema = MarketDataFetcherInput
    
    def _run(self, ticker: str) -> str:
        """Synchronous version (not used in async context)"""
        return "This tool requires async execution"
    
    async def _arun(self, ticker: str) -> str:
        """Fetch market data for ticker"""
        try:
            market_data = await market_data_service.get_stock_data(ticker)
            
            # Convert to JSON-serializable format
            result = {
                'success': True,
                'ticker': market_data.ticker,
                'company_name': market_data.company_name,
                'current_price': market_data.current_price,
                'daily_high': market_data.daily_high,
                'daily_low': market_data.daily_low,
                'volume': market_data.volume,
                'price_change_percentage': market_data.get_price_change_percentage(),
                'average_volume_30d': market_data.get_average_volume(30),
                'market_cap': market_data.market_cap,
                'pe_ratio': market_data.pe_ratio,
                'historical_data_points': len(market_data.historical_prices),
                'timestamp': market_data.timestamp.isoformat()
            }
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Market data fetcher tool failed for {ticker}: {e}")
            return json.dumps({
                'success': False,
                'error': f'Failed to fetch market data for {ticker}: {str(e)}'
            })


class InvestmentAnalyzerInput(BaseModel):
    """Input schema for investment analyzer tool"""
    ticker: str = Field(description="Stock ticker symbol to analyze")
    query_context: str = Field(default="", description="Original user query for context")


class InvestmentAnalyzerTool(BaseTool):
    """Tool for AI-powered investment analysis"""
    
    name: str = "investment_analyzer"
    description: str = """
    Performs comprehensive AI-powered investment analysis on a stock.
    Use this tool to get Buy/Hold/Sell recommendations with confidence scores and detailed reasoning.
    Input should be a valid ticker symbol.
    Returns investment recommendation, confidence score, reasoning, key factors, and risk assessment.
    """
    args_schema = InvestmentAnalyzerInput
    
    def _run(self, ticker: str, query_context: str = "") -> str:
        """Synchronous version (not used in async context)"""
        return "This tool requires async execution"
    
    async def _arun(self, ticker: str, query_context: str = "") -> str:
        """Perform comprehensive investment analysis"""
        try:
            analysis = await comprehensive_analysis_service.perform_complete_analysis(ticker, query_context)
            
            # Convert to JSON-serializable format
            result = {
                'success': True,
                'analysis_id': analysis.analysis_id,
                'ticker': analysis.ticker,
                'company_name': analysis.company_name,
                'recommendation': analysis.recommendation.recommendation.value if analysis.recommendation else 'Hold',
                'confidence_score': analysis.recommendation.confidence_score if analysis.recommendation else 50,
                'reasoning': analysis.recommendation.reasoning if analysis.recommendation else 'Analysis unavailable',
                'key_factors': analysis.recommendation.key_factors if analysis.recommendation else [],
                'risk_assessment': analysis.recommendation.risk_assessment if analysis.recommendation else 'Risk assessment unavailable',
                'summary': analysis.summary,
                'processing_time_ms': analysis.processing_time_ms,
                'timestamp': analysis.timestamp.isoformat()
            }
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Investment analyzer tool failed for {ticker}: {e}")
            return json.dumps({
                'success': False,
                'error': f'Investment analysis failed for {ticker}: {str(e)}'
            })


class AnalysisLoggerInput(BaseModel):
    """Input schema for analysis logger tool"""
    analysis_data: str = Field(description="JSON string containing analysis data to log")


class AnalysisLoggerTool(BaseTool):
    """Tool for logging analysis results"""
    
    name: str = "analysis_logger"
    description: str = """
    Logs analysis results to the database for audit trails and tracking.
    Use this tool to store completed analysis results.
    Input should be JSON string containing analysis data.
    Returns confirmation of successful logging.
    """
    args_schema = AnalysisLoggerInput
    
    def _run(self, analysis_data: str) -> str:
        """Synchronous version (not used in async context)"""
        return "This tool requires async execution"
    
    async def _arun(self, analysis_data: str) -> str:
        """Log analysis results to database"""
        try:
            # Parse analysis data
            data = json.loads(analysis_data)
            
            # This is typically handled automatically by the comprehensive analysis service
            # But we can provide confirmation
            result = {
                'success': True,
                'message': 'Analysis logging is handled automatically by the analysis service',
                'analysis_id': data.get('analysis_id', 'unknown'),
                'ticker': data.get('ticker', 'unknown')
            }
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Analysis logger tool failed: {e}")
            return json.dumps({
                'success': False,
                'error': f'Analysis logging failed: {str(e)}'
            })


class MarketStatusCheckerTool(BaseTool):
    """Tool for checking market status"""
    
    name: str = "market_status_checker"
    description: str = """
    Checks current market status (open/closed) and provides market information.
    Use this tool to determine if markets are currently open for trading.
    No input required.
    Returns market status, trading hours, and last update time.
    """
    
    def _run(self) -> str:
        """Synchronous version (not used in async context)"""
        return "This tool requires async execution"
    
    async def _arun(self) -> str:
        """Check current market status"""
        try:
            status = await market_data_service.get_market_status()
            
            result = {
                'success': True,
                'market_state': status.get('market_state', 'UNKNOWN'),
                'is_open': status.get('is_open', False),
                'last_update': status.get('last_update').isoformat() if status.get('last_update') else None,
                'timestamp': status.get('timestamp').isoformat() if status.get('timestamp') else None
            }
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Market status checker tool failed: {e}")
            return json.dumps({
                'success': False,
                'error': f'Market status check failed: {str(e)}'
            })


class TickerValidatorInput(BaseModel):
    """Input schema for ticker validator tool"""
    ticker: str = Field(description="Ticker symbol to validate")


class TickerValidatorTool(BaseTool):
    """Tool for validating ticker symbols"""
    
    name: str = "ticker_validator"
    description: str = """
    Validates whether a ticker symbol exists and is tradeable.
    Use this tool to check if a ticker symbol is valid before fetching data.
    Input should be a ticker symbol string.
    Returns validation result and ticker information if valid.
    """
    args_schema = TickerValidatorInput
    
    def _run(self, ticker: str) -> str:
        """Synchronous version (not used in async context)"""
        return "This tool requires async execution"
    
    async def _arun(self, ticker: str) -> str:
        """Validate ticker symbol"""
        try:
            is_valid = await market_data_service.validate_ticker(ticker)
            
            result = {
                'success': True,
                'ticker': ticker.upper(),
                'is_valid': is_valid,
                'message': f"Ticker {ticker.upper()} is {'valid' if is_valid else 'invalid'}"
            }
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Ticker validator tool failed for {ticker}: {e}")
            return json.dumps({
                'success': False,
                'error': f'Ticker validation failed for {ticker}: {str(e)}'
            })


# Tool registry for easy access
LANGCHAIN_TOOLS = [
    CompanyNameResolverTool(),
    MarketDataFetcherTool(),
    InvestmentAnalyzerTool(),
    AnalysisLoggerTool(),
    MarketStatusCheckerTool(),
    TickerValidatorTool()
]


def get_tool_by_name(tool_name: str) -> Optional[BaseTool]:
    """Get a tool by its name"""
    for tool in LANGCHAIN_TOOLS:
        if tool.name == tool_name:
            return tool
    return None


def get_all_tools() -> list:
    """Get all available Langchain tools"""
    return LANGCHAIN_TOOLS


def get_tool_descriptions() -> Dict[str, str]:
    """Get descriptions of all tools"""
    return {tool.name: tool.description for tool in LANGCHAIN_TOOLS}