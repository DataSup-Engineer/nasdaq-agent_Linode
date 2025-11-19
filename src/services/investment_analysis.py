"""
Comprehensive investment analysis service for NASDAQ Stock Agent
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import asdict
from src.services.claude_client import InvestmentAnalyzer
from src.services.market_data_service import MarketDataService
from src.models.market_data import MarketData, PricePoint
from src.models.analysis import StockAnalysis, InvestmentRecommendation, RecommendationType

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Technical analysis utilities for stock data"""
    
    @staticmethod
    def calculate_moving_average(prices: List[PricePoint], days: int) -> Optional[float]:
        """Calculate simple moving average"""
        if len(prices) < days:
            return None
        
        recent_prices = prices[-days:]
        return sum(p.close_price for p in recent_prices) / days
    
    @staticmethod
    def calculate_rsi(prices: List[PricePoint], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index (RSI)"""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i].close_price - prices[i-1].close_price
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return None
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_volatility(prices: List[PricePoint], days: int = 30) -> Optional[float]:
        """Calculate price volatility (standard deviation of returns)"""
        if len(prices) < days + 1:
            return None
        
        recent_prices = prices[-days-1:]
        returns = []
        
        for i in range(1, len(recent_prices)):
            prev_price = recent_prices[i-1].close_price
            curr_price = recent_prices[i].close_price
            return_pct = (curr_price - prev_price) / prev_price
            returns.append(return_pct)
        
        if not returns:
            return None
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = variance ** 0.5
        
        return volatility * 100  # Convert to percentage
    
    @staticmethod
    def identify_trend(prices: List[PricePoint], short_period: int = 20, long_period: int = 50) -> str:
        """Identify price trend using moving averages"""
        if len(prices) < long_period:
            return "insufficient_data"
        
        short_ma = TechnicalAnalyzer.calculate_moving_average(prices, short_period)
        long_ma = TechnicalAnalyzer.calculate_moving_average(prices, long_period)
        
        if short_ma is None or long_ma is None:
            return "insufficient_data"
        
        if short_ma > long_ma * 1.02:  # 2% threshold
            return "bullish"
        elif short_ma < long_ma * 0.98:  # 2% threshold
            return "bearish"
        else:
            return "neutral"
    
    @staticmethod
    def calculate_support_resistance(prices: List[PricePoint], window: int = 20) -> Tuple[Optional[float], Optional[float]]:
        """Calculate basic support and resistance levels"""
        if len(prices) < window:
            return None, None
        
        recent_prices = prices[-window:]
        
        # Support: lowest low in the window
        support = min(p.low_price for p in recent_prices)
        
        # Resistance: highest high in the window
        resistance = max(p.high_price for p in recent_prices)
        
        return support, resistance


class FundamentalAnalyzer:
    """Fundamental analysis utilities"""
    
    @staticmethod
    def analyze_valuation(market_data: MarketData) -> Dict[str, Any]:
        """Analyze valuation metrics"""
        analysis = {
            'pe_ratio': market_data.pe_ratio,
            'market_cap': market_data.market_cap,
            'valuation_assessment': 'unknown'
        }
        
        if market_data.pe_ratio:
            if market_data.pe_ratio < 15:
                analysis['valuation_assessment'] = 'undervalued'
            elif market_data.pe_ratio > 30:
                analysis['valuation_assessment'] = 'overvalued'
            else:
                analysis['valuation_assessment'] = 'fairly_valued'
        
        return analysis
    
    @staticmethod
    def analyze_liquidity(market_data: MarketData) -> Dict[str, Any]:
        """Analyze stock liquidity"""
        avg_volume = market_data.get_average_volume(30)
        current_volume = market_data.volume
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        liquidity_score = 'high' if avg_volume > 1000000 else 'medium' if avg_volume > 100000 else 'low'
        
        return {
            'average_volume_30d': avg_volume,
            'current_volume': current_volume,
            'volume_ratio': volume_ratio,
            'liquidity_score': liquidity_score,
            'unusual_volume': volume_ratio > 2.0 or volume_ratio < 0.5
        }


class ComprehensiveAnalysisService:
    """Comprehensive stock analysis combining technical, fundamental, and AI analysis"""
    
    def __init__(self):
        self.market_data_service = MarketDataService()
        self.investment_analyzer = InvestmentAnalyzer()
        self.technical_analyzer = TechnicalAnalyzer()
        self.fundamental_analyzer = FundamentalAnalyzer()
    
    async def perform_complete_analysis(self, ticker: str, query_text: str = "") -> StockAnalysis:
        """Perform comprehensive stock analysis"""
        start_time = datetime.utcnow()
        
        try:
            # 1. Get market data
            market_data = await self.market_data_service.get_stock_data(ticker)
            
            # 2. Perform technical analysis
            technical_analysis = self._perform_technical_analysis(market_data)
            
            # 3. Perform fundamental analysis
            fundamental_analysis = self._perform_fundamental_analysis(market_data)
            
            # 4. Get AI investment recommendation
            ai_recommendation = await self.investment_analyzer.analyze_stock(market_data)
            
            # 5. Generate comprehensive summary
            summary = await self._generate_comprehensive_summary(
                market_data, technical_analysis, fundamental_analysis, ai_recommendation
            )
            
            # 6. Calculate processing time
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # 7. Create stock analysis object
            stock_analysis = StockAnalysis(
                ticker=market_data.ticker,
                company_name=market_data.company_name,
                query_text=query_text,
                market_data=market_data,
                recommendation=ai_recommendation,
                summary=summary,
                processing_time_ms=processing_time
            )
            
            logger.info(f"Completed comprehensive analysis for {ticker} in {processing_time}ms")
            return stock_analysis
            
        except Exception as e:
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"Failed to perform complete analysis for {ticker}: {e}")
            
            # Return error analysis
            return StockAnalysis(
                ticker=ticker,
                company_name="Unknown",
                query_text=query_text,
                summary=f"Analysis failed: {str(e)}",
                processing_time_ms=processing_time
            )
    
    def _perform_technical_analysis(self, market_data: MarketData) -> Dict[str, Any]:
        """Perform technical analysis on market data"""
        try:
            prices = market_data.historical_prices
            
            analysis = {
                'moving_averages': {
                    'ma_20': self.technical_analyzer.calculate_moving_average(prices, 20),
                    'ma_50': self.technical_analyzer.calculate_moving_average(prices, 50),
                    'ma_200': self.technical_analyzer.calculate_moving_average(prices, 200)
                },
                'rsi': self.technical_analyzer.calculate_rsi(prices),
                'volatility': self.technical_analyzer.calculate_volatility(prices),
                'trend': self.technical_analyzer.identify_trend(prices),
                'support_resistance': self.technical_analyzer.calculate_support_resistance(prices)
            }
            
            # Add technical signals
            current_price = market_data.current_price
            ma_20 = analysis['moving_averages']['ma_20']
            ma_50 = analysis['moving_averages']['ma_50']
            
            signals = []
            if ma_20 and current_price > ma_20:
                signals.append("Price above 20-day MA (bullish)")
            elif ma_20 and current_price < ma_20:
                signals.append("Price below 20-day MA (bearish)")
            
            if ma_20 and ma_50:
                if ma_20 > ma_50:
                    signals.append("20-day MA above 50-day MA (bullish)")
                else:
                    signals.append("20-day MA below 50-day MA (bearish)")
            
            rsi = analysis['rsi']
            if rsi:
                if rsi > 70:
                    signals.append("RSI overbought (>70)")
                elif rsi < 30:
                    signals.append("RSI oversold (<30)")
            
            analysis['signals'] = signals
            
            return analysis
            
        except Exception as e:
            logger.error(f"Technical analysis failed: {e}")
            return {'error': str(e)}
    
    def _perform_fundamental_analysis(self, market_data: MarketData) -> Dict[str, Any]:
        """Perform fundamental analysis on market data"""
        try:
            valuation = self.fundamental_analyzer.analyze_valuation(market_data)
            liquidity = self.fundamental_analyzer.analyze_liquidity(market_data)
            
            # Price performance analysis
            price_change_pct = market_data.get_price_change_percentage()
            
            performance_signals = []
            if price_change_pct > 5:
                performance_signals.append("Strong positive momentum (+5%)")
            elif price_change_pct > 2:
                performance_signals.append("Positive momentum (+2%)")
            elif price_change_pct < -5:
                performance_signals.append("Strong negative momentum (-5%)")
            elif price_change_pct < -2:
                performance_signals.append("Negative momentum (-2%)")
            
            return {
                'valuation': valuation,
                'liquidity': liquidity,
                'price_performance': {
                    'change_percentage': price_change_pct,
                    'signals': performance_signals
                }
            }
            
        except Exception as e:
            logger.error(f"Fundamental analysis failed: {e}")
            return {'error': str(e)}
    
    async def _generate_comprehensive_summary(
        self, 
        market_data: MarketData, 
        technical_analysis: Dict[str, Any],
        fundamental_analysis: Dict[str, Any],
        ai_recommendation: InvestmentRecommendation
    ) -> str:
        """Generate comprehensive analysis summary"""
        try:
            # Build summary components
            price_info = f"${market_data.current_price:.2f} ({market_data.get_price_change_percentage():+.2f}%)"
            
            # Technical summary
            tech_signals = technical_analysis.get('signals', [])
            tech_summary = f"Technical: {', '.join(tech_signals[:2])}" if tech_signals else "Technical: Neutral signals"
            
            # Fundamental summary
            fund_analysis = fundamental_analysis.get('valuation', {})
            valuation = fund_analysis.get('valuation_assessment', 'unknown')
            fund_summary = f"Valuation: {valuation.replace('_', ' ').title()}"
            
            # AI recommendation summary
            ai_summary = f"AI Recommendation: {ai_recommendation.recommendation.value} (Confidence: {ai_recommendation.confidence_score:.0f}%)"
            
            # Combine into comprehensive summary
            summary = f"""
{market_data.company_name} ({market_data.ticker}) Analysis:

Current Price: {price_info}
{tech_summary}
{fund_summary}
{ai_summary}

Key Factors: {', '.join(ai_recommendation.key_factors[:3])}

Risk Assessment: {ai_recommendation.risk_assessment[:100]}{'...' if len(ai_recommendation.risk_assessment) > 100 else ''}
""".strip()
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate comprehensive summary: {e}")
            return f"Analysis summary for {market_data.company_name} could not be generated due to an error."
    

    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get health status of the analysis service"""
        try:
            # Test market data service
            market_health = await self.market_data_service.get_service_health()
            
            # Test AI analyzer
            ai_health = await self.investment_analyzer.get_health_status()
            
            # Overall health
            is_healthy = (
                market_health.get('overall_status') == 'healthy' and
                ai_health.get('status') == 'healthy'
            )
            
            return {
                'service': 'ComprehensiveAnalysisService',
                'overall_status': 'healthy' if is_healthy else 'degraded',
                'market_data_service': market_health,
                'ai_analyzer': ai_health,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            return {
                'service': 'ComprehensiveAnalysisService',
                'overall_status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow()
            }


# Global comprehensive analysis service instance
comprehensive_analysis_service = ComprehensiveAnalysisService()