"""
Agent Logic Adapter for A2A Communication

Translates A2A messages to stock analysis requests and formats responses.
"""
import logging
import asyncio
from datetime import datetime
from typing import Optional
from src.services import enhanced_nlp_service
from src.services.investment_analysis import comprehensive_analysis_service

logger = logging.getLogger(__name__)


async def process_a2a_message(message: str, conversation_id: str) -> str:
    """
    Process incoming A2A message and return response.
    
    Handles:
    - Stock queries: "AAPL", "Apple", "What about Tesla?"
    - Help commands: "/help", "/info"
    - Status commands: "/status", "/ping"
    
    Args:
        message: The message text from A2A
        conversation_id: Conversation identifier
        
    Returns:
        str: Response text
    """
    try:
        message_lower = message.lower().strip()
        
        # Handle commands
        if message_lower.startswith("/"):
            return await _handle_command(message_lower, conversation_id)
        
        # Handle stock queries
        return await _handle_stock_query(message, conversation_id)
        
    except Exception as e:
        logger.error(f"Error processing A2A message: {e}", exc_info=True)
        return f"Sorry, I encountered an error processing your request: {str(e)}"


async def _handle_command(command: str, conversation_id: str) -> str:
    """Handle system commands"""
    cmd = command.split()[0] if command else ""
    
    if cmd == "/help" or cmd == "/info":
        return """NASDAQ Stock Agent - Available Commands:

📊 Stock Analysis:
   Just send a ticker symbol or company name:
   - "AAPL" or "Apple"
   - "What about Tesla?"
   - "Should I buy Microsoft?"

🔧 Commands:
   /help or /info - Show this help message
   /ping - Test agent responsiveness
   /status - Show agent status
   /capabilities - List agent capabilities

💡 Examples:
   "AAPL" → Get analysis for Apple Inc.
   "What do you think about Tesla stock?" → Get Tesla analysis
   "Microsoft" → Get analysis for Microsoft Corporation

I provide:
✓ Current price and market data
✓ Technical analysis (RSI, MACD, Moving Averages)
✓ Investment recommendations (Buy/Hold/Sell)
✓ Confidence scores and risk assessment
✓ Detailed reasoning for recommendations"""
    
    elif cmd == "/ping":
        return "Pong! NASDAQ Stock Agent is online and ready to analyze stocks."
    
    elif cmd == "/status":
        return f"""NASDAQ Stock Agent Status:
🟢 Status: Online and operational
🤖 Agent ID: nasdaq-stock-agent
📊 Domain: Financial Analysis
🎯 Specialization: NASDAQ Stock Analysis
⏰ Timestamp: {datetime.utcnow().isoformat()}

Services:
✓ Market Data Service: Active
✓ Analysis Service: Active
✓ NLP Service: Active
✓ Claude AI: Active

Ready to analyze NASDAQ stocks!"""
    
    elif cmd == "/capabilities":
        return """NASDAQ Stock Agent Capabilities:

📈 Stock Analysis:
   - Real-time NASDAQ market data retrieval
   - 6-month historical trend analysis
   - Technical indicators (RSI, MACD, Moving Averages)
   - Fundamental analysis (P/E ratio, EPS, Revenue)

🤖 AI-Powered Recommendations:
   - Buy/Hold/Sell recommendations
   - Confidence scoring (0-100 scale)
   - Detailed reasoning and key factors
   - Risk assessment

🔍 Natural Language Processing:
   - Company name to ticker resolution
   - Fuzzy matching and typo correction
   - Support for 50+ major NASDAQ companies

💬 Communication:
   - A2A protocol support
   - REST API interface
   - Agent-to-agent forwarding"""
    
    else:
        return f"Unknown command: {cmd}\nUse /help to see available commands."


async def _handle_stock_query(query: str, conversation_id: str) -> str:
    """
    Handle stock analysis queries.
    
    Args:
        query: Stock query (ticker or company name)
        conversation_id: Conversation ID
        
    Returns:
        str: Formatted analysis response
    """
    try:
        logger.info(f"Processing stock query: {query} (conversation: {conversation_id})")
        
        # Use enhanced NLP service to resolve company name to ticker
        result = await enhanced_nlp_service.process_query_with_suggestions(query)
        
        if not result.get('success'):
            # No match found, provide helpful suggestions
            suggestions = result.get('suggestions', {})
            error_msg = f"""I couldn't find a NASDAQ stock matching "{query}".

Please try:
- Using the ticker symbol (e.g., "AAPL" for Apple)
- Using the full company name (e.g., "Apple Inc.")
- Checking the spelling

Popular NASDAQ stocks: AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA, NFLX"""
            
            # Add suggestions if available
            if suggestions.get('similar_companies'):
                similar = suggestions['similar_companies'][:3]
                if similar:
                    error_msg += "\n\nDid you mean:\n"
                    for comp in similar:
                        error_msg += f"- {comp['company_name']} ({comp['ticker']})\n"
            
            return error_msg
        
        # Get the resolved ticker and company name
        ticker = result['ticker']
        company_name = result['company_name']
        
        logger.info(f"Resolved '{query}' to {ticker} ({company_name})")
        
        # Get comprehensive analysis using the existing service
        analysis = await comprehensive_analysis_service.perform_complete_analysis(ticker, query_text=query)
        
        if not analysis:
            return f"Sorry, I couldn't analyze {ticker} ({company_name}) at this time. Please try again later."
        
        # Format the response
        response = _format_analysis_response(analysis, ticker, company_name)
        
        logger.info(f"Analysis completed for {ticker}")
        return response
        
    except Exception as e:
        logger.error(f"Error handling stock query '{query}': {e}", exc_info=True)
        return f"Sorry, I encountered an error analyzing that stock: {str(e)}"


def _format_analysis_response(analysis, ticker: str, company_name: str) -> str:
    """
    Format stock analysis as readable text for A2A response.
    
    Args:
        analysis: StockAnalysis object
        ticker: Stock ticker symbol
        company_name: Company name
        
    Returns:
        str: Formatted response text
    """
    try:
        # Extract key information
        current_price = analysis.market_data.current_price if analysis.market_data else 0.0
        price_change_pct = analysis.market_data.get_price_change_percentage() if analysis.market_data else 0.0
        recommendation = analysis.recommendation.recommendation.value if analysis.recommendation else "N/A"
        confidence = analysis.recommendation.confidence_score if analysis.recommendation else 0
        
        # Format price change with emoji
        price_emoji = "📈" if price_change_pct > 0 else "📉" if price_change_pct < 0 else "➡️"
        price_change_str = f"+{price_change_pct:.2f}%" if price_change_pct > 0 else f"{price_change_pct:.2f}%"
        
        # Format recommendation with emoji
        rec_emoji = "🟢" if recommendation == "Buy" else "🔴" if recommendation == "Sell" else "🟡"
        
        # Build response
        response = f"""📊 {company_name} ({ticker}) Analysis

💰 Current Price: ${current_price:.2f} {price_emoji} {price_change_str}

{rec_emoji} Recommendation: {recommendation}
🎯 Confidence: {confidence:.0f}%

"""
        
        # Add reasoning if available
        if analysis.recommendation and analysis.recommendation.reasoning:
            reasoning = analysis.recommendation.reasoning
            # Truncate if too long
            if len(reasoning) > 500:
                reasoning = reasoning[:500] + "..."
            response += f"📝 Analysis:\n{reasoning}\n\n"
        
        # Add key factors if available
        if analysis.recommendation and analysis.recommendation.key_factors:
            response += "🔑 Key Factors:\n"
            for i, factor in enumerate(analysis.recommendation.key_factors[:5], 1):
                # Clean up factor text
                factor_text = factor.strip()
                if not factor_text.startswith(str(i)):
                    response += f"{i}. {factor_text}\n"
                else:
                    response += f"{factor_text}\n"
            response += "\n"
        
        # Add risk assessment if available
        if analysis.recommendation and analysis.recommendation.risk_assessment:
            risk = analysis.recommendation.risk_assessment
            if len(risk) > 300:
                risk = risk[:300] + "..."
            response += f"⚠️ Risk Assessment:\n{risk}\n\n"
        
        # Add processing time
        response += f"⏱️ Analysis completed in {analysis.processing_time_ms}ms"
        
        return response
        
    except Exception as e:
        logger.error(f"Error formatting analysis response: {e}", exc_info=True)
        # Fallback to simple format
        current_price = analysis.market_data.current_price if analysis.market_data else 0.0
        recommendation = analysis.recommendation.recommendation.value if analysis.recommendation else "N/A"
        confidence = analysis.recommendation.confidence_score if analysis.recommendation else 0
        return f"""Analysis for {company_name} ({ticker}):
Price: ${current_price:.2f}
Recommendation: {recommendation}
Confidence: {confidence:.0f}%

(Error formatting detailed response)"""


def process_a2a_message_sync(message: str, conversation_id: str) -> str:
    """
    Synchronous wrapper for process_a2a_message.
    
    This is needed for the NEST adapter which expects a synchronous function.
    
    Args:
        message: The message text from A2A
        conversation_id: Conversation identifier
        
    Returns:
        str: Response text
    """
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(process_a2a_message(message, conversation_id))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Error in sync wrapper: {e}", exc_info=True)
        return f"Error processing message: {str(e)}"
