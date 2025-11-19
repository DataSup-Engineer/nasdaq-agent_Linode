"""
MCP Tool implementations that integrate with existing Langchain agent services
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from .schemas import MCPResponse
from .response_formatter import MCPResponseFormatter

# Use absolute imports to avoid circular import issues
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.stock_analysis_agent import agent_orchestrator
from services.logging_service import logging_service

logger = logging.getLogger(__name__)


class MCPToolImplementations:
    """Implementation of MCP tools that integrate with existing services"""
    
    def __init__(self):
        self.response_formatter = MCPResponseFormatter()
        self.agent_orchestrator = agent_orchestrator
    
    async def analyze_stock_tool(self, parameters: Dict[str, Any]) -> MCPResponse:
        """
        MCP tool implementation for stock analysis
        Integrates with existing Langchain agent
        """
        try:
            company_name_or_ticker = parameters.get("company_name_or_ticker", "")
            
            if not company_name_or_ticker:
                return self.response_formatter.format_error_response(
                    "Missing required parameter: company_name_or_ticker"
                )
            
            logger.info(f"MCP analyze_stock tool called for: {company_name_or_ticker}")
            
            # Use the existing Langchain agent to perform analysis
            agent_result = await self.agent_orchestrator.stock_agent.analyze_stock_query(
                f"Analyze {company_name_or_ticker} stock and provide investment recommendations"
            )
            
            if agent_result.get('success', False):
                # Format successful analysis response
                analysis_data = {
                    'tool_call': 'analyze_stock',
                    'input': company_name_or_ticker,
                    'ticker': agent_result.get('ticker', 'unknown'),
                    'company_name': agent_result.get('company_name', 'unknown'),
                    'recommendation': agent_result.get('recommendation', 'Hold'),
                    'confidence_score': agent_result.get('confidence_score', 50.0),
                    'current_price': agent_result.get('current_price', 0.0),
                    'price_change_percentage': agent_result.get('price_change_percentage', 0.0),
                    'reasoning': agent_result.get('response', ''),
                    'processing_time_ms': agent_result.get('processing_time_ms', 0),
                    'timestamp': agent_result.get('timestamp', datetime.utcnow().isoformat()),
                    'extracted_data': agent_result.get('extracted_data', {}),
                    'analysis_id': agent_result.get('extracted_data', {}).get('investment_analysis', {}).get('analysis_id', f"mcp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
                }
                
                return self.response_formatter.format_analysis_response(analysis_data)
            
            else:
                # Format error response
                error_msg = agent_result.get('error', 'Analysis failed')
                suggestions = agent_result.get('suggestions', [])
                
                error_details = {
                    'tool_call': 'analyze_stock',
                    'input': company_name_or_ticker,
                    'error': error_msg,
                    'suggestions': suggestions,
                    'processing_time_ms': agent_result.get('processing_time_ms', 0)
                }
                
                return self.response_formatter.format_error_response(error_msg, error_details)
                
        except Exception as e:
            logger.error(f"MCP analyze_stock tool failed: {e}")
            return self.response_formatter.format_error_response(
                f"Stock analysis failed: {str(e)}",
                {'tool_call': 'analyze_stock', 'input': parameters.get('company_name_or_ticker', 'unknown')}
            )
    
    async def get_market_data_tool(self, parameters: Dict[str, Any]) -> MCPResponse:
        """
        MCP tool implementation for market data retrieval
        Integrates with existing market data services via Langchain agent
        """
        try:
            ticker = parameters.get("ticker", "")
            include_historical = parameters.get("include_historical", True)
            
            if not ticker:
                return self.response_formatter.format_error_response(
                    "Missing required parameter: ticker"
                )
            
            logger.info(f"MCP get_market_data tool called for: {ticker}")
            
            # Construct query for the agent
            query = f"Get current market data for {ticker}"
            if include_historical:
                query += " including 6-month historical data"
            else:
                query += " current data only"
            
            # Use the Langchain agent to fetch market data
            agent_result = await self.agent_orchestrator.stock_agent.analyze_stock_query(query)
            
            if agent_result.get('success', False):
                # Extract market data from agent result
                extracted_data = agent_result.get('extracted_data', {})
                market_data = extracted_data.get('market_data', {})
                
                if market_data:
                    # Enhance market data with metadata
                    enhanced_market_data = {
                        'tool_call': 'get_market_data',
                        'ticker': ticker,
                        'include_historical': include_historical,
                        'data': market_data,
                        'timestamp': datetime.utcnow().isoformat(),
                        'processing_time_ms': agent_result.get('processing_time_ms', 0)
                    }
                    
                    return self.response_formatter.format_market_data_response(enhanced_market_data)
                else:
                    # Fallback to general agent response
                    market_data = {
                        'tool_call': 'get_market_data',
                        'ticker': ticker,
                        'current_price': agent_result.get('current_price', 0.0),
                        'price_change_percentage': agent_result.get('price_change_percentage', 0.0),
                        'company_name': agent_result.get('company_name', 'unknown'),
                        'timestamp': datetime.utcnow().isoformat(),
                        'processing_time_ms': agent_result.get('processing_time_ms', 0),
                        'note': 'Data extracted from general analysis response'
                    }
                    
                    return self.response_formatter.format_market_data_response(market_data)
            
            else:
                error_msg = agent_result.get('error', f'Failed to retrieve market data for {ticker}')
                error_details = {
                    'tool_call': 'get_market_data',
                    'ticker': ticker,
                    'include_historical': include_historical,
                    'error': error_msg,
                    'processing_time_ms': agent_result.get('processing_time_ms', 0)
                }
                
                return self.response_formatter.format_error_response(error_msg, error_details)
                
        except Exception as e:
            logger.error(f"MCP get_market_data tool failed: {e}")
            return self.response_formatter.format_error_response(
                f"Market data retrieval failed: {str(e)}",
                {'tool_call': 'get_market_data', 'ticker': parameters.get('ticker', 'unknown')}
            )
    
    async def resolve_company_name_tool(self, parameters: Dict[str, Any]) -> MCPResponse:
        """
        MCP tool implementation for company name resolution
        Integrates with existing NLP services via Langchain agent
        """
        try:
            company_name = parameters.get("company_name", "")
            
            if not company_name:
                return self.response_formatter.format_error_response(
                    "Missing required parameter: company_name"
                )
            
            logger.info(f"MCP resolve_company_name tool called for: {company_name}")
            
            # Use the Langchain agent to resolve company name
            query = f"What is the ticker symbol for {company_name}? Just resolve the company name to ticker."
            agent_result = await self.agent_orchestrator.stock_agent.analyze_stock_query(query)
            
            if agent_result.get('success', False):
                # Extract company resolution data
                extracted_data = agent_result.get('extracted_data', {})
                company_resolution = extracted_data.get('company_resolution', {})
                
                if company_resolution:
                    resolution_data = {
                        'tool_call': 'resolve_company_name',
                        'input_name': company_name,
                        'ticker': company_resolution.get('ticker', 'unknown'),
                        'resolved_company_name': company_resolution.get('company_name', company_name),
                        'confidence': company_resolution.get('confidence', 1.0),
                        'timestamp': datetime.utcnow().isoformat(),
                        'processing_time_ms': agent_result.get('processing_time_ms', 0)
                    }
                else:
                    # Try to extract from general response
                    ticker = agent_result.get('ticker', 'unknown')
                    resolved_name = agent_result.get('company_name', company_name)
                    
                    resolution_data = {
                        'tool_call': 'resolve_company_name',
                        'input_name': company_name,
                        'ticker': ticker,
                        'resolved_company_name': resolved_name,
                        'confidence': 0.8 if ticker != 'unknown' else 0.0,
                        'timestamp': datetime.utcnow().isoformat(),
                        'processing_time_ms': agent_result.get('processing_time_ms', 0),
                        'note': 'Extracted from general analysis response'
                    }
                
                return self.response_formatter.format_company_resolution_response(resolution_data)
            
            else:
                error_msg = agent_result.get('error', f'Failed to resolve company name: {company_name}')
                error_details = {
                    'tool_call': 'resolve_company_name',
                    'input_name': company_name,
                    'error': error_msg,
                    'suggestions': agent_result.get('suggestions', []),
                    'processing_time_ms': agent_result.get('processing_time_ms', 0)
                }
                
                return self.response_formatter.format_error_response(error_msg, error_details)
                
        except Exception as e:
            logger.error(f"MCP resolve_company_name tool failed: {e}")
            return self.response_formatter.format_error_response(
                f"Company name resolution failed: {str(e)}",
                {'tool_call': 'resolve_company_name', 'input_name': parameters.get('company_name', 'unknown')}
            )
    
    def get_tool_implementations(self) -> Dict[str, callable]:
        """Get dictionary of tool name to implementation function"""
        return {
            'analyze_stock': self.analyze_stock_tool,
            'get_market_data': self.get_market_data_tool,
            'resolve_company_name': self.resolve_company_name_tool
        }


# Global MCP tool implementations instance
mcp_tool_implementations = MCPToolImplementations()