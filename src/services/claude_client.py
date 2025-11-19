"""
Anthropic Claude client wrapper for NASDAQ Stock Agent
"""
import asyncio
from typing import Dict, List, Optional, Any
import json
import re
from datetime import datetime
import logging
from anthropic import AsyncAnthropic
from src.config.settings import settings
from src.models.market_data import MarketData, PricePoint
from src.models.analysis import InvestmentRecommendation, RecommendationType

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper for Anthropic Claude API with investment analysis capabilities"""
    
    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")
        
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.max_tokens = 4000
        self.temperature = 0.3  # Lower temperature for more consistent analysis
    
    async def analyze_investment(self, market_data: MarketData) -> Dict[str, Any]:
        """Analyze market data and generate investment recommendation"""
        try:
            # Build analysis prompt
            prompt = self._build_investment_analysis_prompt(market_data)
            
            # Call Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse response
            analysis_text = response.content[0].text
            parsed_analysis = self._parse_investment_analysis(analysis_text)
            
            logger.info(f"Generated investment analysis for {market_data.ticker}")
            return parsed_analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze investment for {market_data.ticker}: {e}")
            raise
    
    def _build_investment_analysis_prompt(self, market_data: MarketData) -> str:
        """Build comprehensive prompt for investment analysis"""
        
        # Calculate key metrics
        price_change_pct = market_data.get_price_change_percentage()
        avg_volume = market_data.get_average_volume(30)
        
        # Get historical price trends
        historical_summary = self._summarize_historical_data(market_data.historical_prices)
        
        prompt = f"""
You are a professional financial analyst specializing in NASDAQ stock analysis. Analyze the following stock data and provide a comprehensive investment recommendation.

STOCK INFORMATION:
- Company: {market_data.company_name}
- Ticker: {market_data.ticker}
- Current Price: ${market_data.current_price:.2f}
- Daily High: ${market_data.daily_high:.2f}
- Daily Low: ${market_data.daily_low:.2f}
- Volume: {market_data.volume:,}
- Price Change: {price_change_pct:+.2f}%
- 30-Day Avg Volume: {avg_volume:,.0f}
- Market Cap: ${market_data.market_cap:,}" if market_data.market_cap else "N/A"
- P/E Ratio: {market_data.pe_ratio:.2f}" if market_data.pe_ratio else "N/A"

6-MONTH HISTORICAL ANALYSIS:
{historical_summary}

ANALYSIS REQUIREMENTS:
Please provide a structured analysis with the following components:

1. RECOMMENDATION: Choose exactly one of: "Buy", "Hold", or "Sell"

2. CONFIDENCE_SCORE: Provide a numerical confidence score between 0 and 100

3. REASONING: Provide detailed reasoning for your recommendation based on:
   - Price trends and momentum
   - Volume analysis
   - Technical indicators
   - Market position and fundamentals
   - Risk factors

4. KEY_FACTORS: List 3-5 specific factors that most influenced your decision

5. RISK_ASSESSMENT: Evaluate the risk level and potential concerns

6. SUMMARY: Provide a concise 2-3 sentence summary of your analysis

FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:
RECOMMENDATION: [Buy/Hold/Sell]
CONFIDENCE_SCORE: [0-100]
REASONING: [Your detailed analysis]
KEY_FACTORS: [Factor 1], [Factor 2], [Factor 3], [Factor 4], [Factor 5]
RISK_ASSESSMENT: [Risk evaluation]
SUMMARY: [Concise summary]

Focus on actionable insights based on the 6-month historical data provided. Consider both technical and fundamental factors in your analysis.
"""
        
        return prompt
    
    def _summarize_historical_data(self, historical_prices: List[PricePoint]) -> str:
        """Summarize historical price data for the prompt"""
        if not historical_prices:
            return "No historical data available"
        
        # Sort by date
        sorted_prices = sorted(historical_prices, key=lambda x: x.date)
        
        # Calculate key metrics
        oldest_price = sorted_prices[0].close_price
        newest_price = sorted_prices[-1].close_price
        total_return = ((newest_price - oldest_price) / oldest_price) * 100
        
        # Find highest and lowest prices
        high_price = max(price.high_price for price in sorted_prices)
        low_price = min(price.low_price for price in sorted_prices)
        
        # Calculate volatility (simplified)
        daily_returns = []
        for i in range(1, len(sorted_prices)):
            prev_close = sorted_prices[i-1].close_price
            curr_close = sorted_prices[i].close_price
            daily_return = (curr_close - prev_close) / prev_close
            daily_returns.append(daily_return)
        
        volatility = (sum(r**2 for r in daily_returns) / len(daily_returns))**0.5 * 100 if daily_returns else 0
        
        # Recent trend (last 30 days vs previous 30 days)
        recent_30 = sorted_prices[-30:] if len(sorted_prices) >= 30 else sorted_prices
        prev_30 = sorted_prices[-60:-30] if len(sorted_prices) >= 60 else sorted_prices[:-30] if len(sorted_prices) > 30 else []
        
        recent_avg = sum(p.close_price for p in recent_30) / len(recent_30)
        prev_avg = sum(p.close_price for p in prev_30) / len(prev_30) if prev_30 else recent_avg
        
        trend_direction = "upward" if recent_avg > prev_avg else "downward" if recent_avg < prev_avg else "sideways"
        
        summary = f"""
- 6-Month Total Return: {total_return:+.2f}%
- Price Range: ${low_price:.2f} - ${high_price:.2f}
- Volatility: {volatility:.2f}%
- Recent Trend: {trend_direction}
- Data Points: {len(sorted_prices)} trading days
- Average Daily Volume: {sum(p.volume for p in sorted_prices) / len(sorted_prices):,.0f}
"""
        
        return summary.strip()
    
    def _parse_investment_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse Claude's response into structured data"""
        try:
            parsed = {
                'recommendation': None,
                'confidence_score': 0,
                'reasoning': '',
                'key_factors': [],
                'risk_assessment': '',
                'summary': '',
                'raw_analysis': analysis_text
            }
            
            # Extract recommendation
            rec_match = re.search(r'RECOMMENDATION:\s*(Buy|Hold|Sell)', analysis_text, re.IGNORECASE)
            if rec_match:
                parsed['recommendation'] = rec_match.group(1).title()
            
            # Extract confidence score
            conf_match = re.search(r'CONFIDENCE_SCORE:\s*(\d+)', analysis_text)
            if conf_match:
                parsed['confidence_score'] = int(conf_match.group(1))
            
            # Extract reasoning
            reasoning_match = re.search(r'REASONING:\s*(.*?)(?=KEY_FACTORS:|$)', analysis_text, re.DOTALL | re.IGNORECASE)
            if reasoning_match:
                parsed['reasoning'] = reasoning_match.group(1).strip()
            
            # Extract key factors
            factors_match = re.search(r'KEY_FACTORS:\s*(.*?)(?=RISK_ASSESSMENT:|$)', analysis_text, re.DOTALL | re.IGNORECASE)
            if factors_match:
                factors_text = factors_match.group(1).strip()
                # Split by commas and clean up
                factors = [f.strip() for f in factors_text.split(',') if f.strip()]
                parsed['key_factors'] = factors[:5]  # Limit to 5 factors
            
            # Extract risk assessment
            risk_match = re.search(r'RISK_ASSESSMENT:\s*(.*?)(?=SUMMARY:|$)', analysis_text, re.DOTALL | re.IGNORECASE)
            if risk_match:
                parsed['risk_assessment'] = risk_match.group(1).strip()
            
            # Extract summary
            summary_match = re.search(r'SUMMARY:\s*(.*?)$', analysis_text, re.DOTALL | re.IGNORECASE)
            if summary_match:
                parsed['summary'] = summary_match.group(1).strip()
            
            # Validate required fields
            if not parsed['recommendation']:
                parsed['recommendation'] = 'Hold'  # Default fallback
                logger.warning("Could not parse recommendation, defaulting to Hold")
            
            if parsed['confidence_score'] == 0:
                parsed['confidence_score'] = 50  # Default fallback
                logger.warning("Could not parse confidence score, defaulting to 50")
            
            return parsed
            
        except Exception as e:
            logger.error(f"Failed to parse investment analysis: {e}")
            # Return default structure
            return {
                'recommendation': 'Hold',
                'confidence_score': 50,
                'reasoning': 'Analysis parsing failed, defaulting to Hold recommendation',
                'key_factors': ['Analysis parsing error'],
                'risk_assessment': 'Unable to assess risk due to parsing error',
                'summary': 'Analysis could not be properly parsed',
                'raw_analysis': analysis_text
            }
    
    async def generate_market_summary(self, market_data: MarketData) -> str:
        """Generate a concise market summary for a stock"""
        try:
            prompt = f"""
Provide a brief, professional summary of {market_data.company_name} ({market_data.ticker}) based on the current market data:

Current Price: ${market_data.current_price:.2f}
Daily Range: ${market_data.daily_low:.2f} - ${market_data.daily_high:.2f}
Volume: {market_data.volume:,}
6-Month Price Change: {market_data.get_price_change_percentage():+.2f}%

Write a 2-3 sentence professional summary suitable for an investment report.
"""
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate market summary for {market_data.ticker}: {e}")
            return f"Market summary for {market_data.company_name} could not be generated due to an error."
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the connection to Anthropic API"""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=50,
                temperature=0.1,
                messages=[
                    {
                        "role": "user", 
                        "content": "Respond with 'Connection successful' if you can read this message."
                    }
                ]
            )
            
            return {
                'status': 'success',
                'model': self.model,
                'response': response.content[0].text,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow()
            }


class InvestmentAnalyzer:
    """High-level investment analyzer using Claude"""
    
    def __init__(self):
        self.claude_client = ClaudeClient()
    
    async def analyze_stock(self, market_data: MarketData) -> InvestmentRecommendation:
        """Analyze stock and return structured investment recommendation"""
        try:
            # Get analysis from Claude
            analysis = await self.claude_client.analyze_investment(market_data)
            
            # Convert to InvestmentRecommendation object
            recommendation_type = RecommendationType(analysis['recommendation'])
            
            investment_rec = InvestmentRecommendation(
                recommendation=recommendation_type,
                confidence_score=float(analysis['confidence_score']),
                reasoning=analysis['reasoning'],
                key_factors=analysis['key_factors'],
                risk_assessment=analysis['risk_assessment']
            )
            
            logger.info(f"Generated investment recommendation for {market_data.ticker}: {recommendation_type}")
            return investment_rec
            
        except Exception as e:
            logger.error(f"Failed to analyze stock {market_data.ticker}: {e}")
            # Return default recommendation on error
            return InvestmentRecommendation(
                recommendation=RecommendationType.HOLD,
                confidence_score=50.0,
                reasoning=f"Analysis failed due to error: {str(e)}",
                key_factors=["Analysis error"],
                risk_assessment="Unable to assess risk due to analysis failure"
            )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the investment analyzer"""
        try:
            connection_test = await self.claude_client.test_connection()
            
            return {
                'service': 'InvestmentAnalyzer',
                'claude_connection': connection_test,
                'model': self.claude_client.model,
                'status': 'healthy' if connection_test['status'] == 'success' else 'unhealthy',
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            return {
                'service': 'InvestmentAnalyzer',
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow()
            }


# Global investment analyzer instance
investment_analyzer = InvestmentAnalyzer()