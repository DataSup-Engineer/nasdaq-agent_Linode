"""
MCP Response Formatter for converting responses to MCP-compliant format
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from .schemas import MCPResponse

logger = logging.getLogger(__name__)


class MCPResponseFormatter:
    """Formats responses to MCP-compliant format"""
    
    def __init__(self):
        self.default_mime_types = {
            'json': 'application/json',
            'text': 'text/plain',
            'html': 'text/html',
            'markdown': 'text/markdown'
        }
    
    def format_analysis_response(self, analysis_data: Dict[str, Any]) -> MCPResponse:
        """Format stock analysis data into MCP response"""
        try:
            response = MCPResponse()
            
            # Add summary text
            ticker = analysis_data.get('ticker', 'unknown')
            recommendation = analysis_data.get('recommendation', 'Hold')
            confidence = analysis_data.get('confidence_score', 50.0)
            current_price = analysis_data.get('current_price', 0.0)
            
            summary_text = (
                f"Stock Analysis for {ticker}\n"
                f"Recommendation: {recommendation} (Confidence: {confidence}%)\n"
                f"Current Price: ${current_price:.2f}"
            )
            
            if analysis_data.get('price_change_percentage'):
                change_pct = analysis_data['price_change_percentage']
                change_indicator = "↑" if change_pct > 0 else "↓" if change_pct < 0 else "→"
                summary_text += f"\nPrice Change: {change_indicator} {change_pct:.2f}%"
            
            response.add_text_content(summary_text)
            
            # Add detailed analysis as JSON resource
            uri = f"analysis://{ticker.lower()}/{datetime.utcnow().strftime('%Y-%m-%d')}"
            response.add_json_content(analysis_data, uri)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to format analysis response: {e}")
            error_response = MCPResponse(isError=True)
            error_response.add_text_content(f"Response formatting failed: {str(e)}")
            return error_response
    
    def format_market_data_response(self, market_data: Dict[str, Any]) -> MCPResponse:
        """Format market data into MCP response"""
        try:
            response = MCPResponse()
            
            # Add summary text
            ticker = market_data.get('ticker', 'unknown')
            current_price = market_data.get('current_price', 0.0)
            volume = market_data.get('volume', 0)
            
            summary_text = (
                f"Market Data for {ticker}\n"
                f"Current Price: ${current_price:.2f}\n"
                f"Volume: {volume:,}"
            )
            
            if market_data.get('daily_high') and market_data.get('daily_low'):
                summary_text += f"\nDaily Range: ${market_data['daily_low']:.2f} - ${market_data['daily_high']:.2f}"
            
            response.add_text_content(summary_text)
            
            # Add detailed market data as JSON resource
            uri = f"market-data://{ticker.lower()}/{datetime.utcnow().strftime('%Y-%m-%d')}"
            response.add_json_content(market_data, uri)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to format market data response: {e}")
            error_response = MCPResponse(isError=True)
            error_response.add_text_content(f"Market data formatting failed: {str(e)}")
            return error_response
    
    def format_company_resolution_response(self, resolution_data: Dict[str, Any]) -> MCPResponse:
        """Format company name resolution into MCP response"""
        try:
            response = MCPResponse()
            
            input_name = resolution_data.get('input_name', 'unknown')
            ticker = resolution_data.get('ticker', 'unknown')
            resolved_name = resolution_data.get('resolved_company_name', input_name)
            
            if ticker != 'unknown':
                summary_text = f"Company Resolution: '{input_name}' → {ticker} ({resolved_name})"
                
                if resolution_data.get('confidence'):
                    confidence = resolution_data['confidence']
                    summary_text += f"\nConfidence: {confidence:.1%}"
            else:
                summary_text = f"Could not resolve company name: '{input_name}'"
                response.isError = True
            
            response.add_text_content(summary_text)
            
            # Add resolution data as JSON resource
            uri = f"resolution://{input_name.lower().replace(' ', '-')}"
            response.add_json_content(resolution_data, uri)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to format company resolution response: {e}")
            error_response = MCPResponse(isError=True)
            error_response.add_text_content(f"Company resolution formatting failed: {str(e)}")
            return error_response
    
    def format_error_response(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> MCPResponse:
        """Format error into MCP response"""
        try:
            response = MCPResponse(isError=True)
            response.add_text_content(f"Error: {error_message}")
            
            if error_details:
                # Add error details as JSON resource
                uri = f"error://{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
                response.add_json_content(error_details, uri)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to format error response: {e}")
            # Fallback error response
            fallback_response = MCPResponse(isError=True)
            fallback_response.add_text_content(f"Error formatting failed: {str(e)}")
            return fallback_response
    
    def format_generic_response(self, data: Union[Dict[str, Any], str, List], content_type: str = 'json') -> MCPResponse:
        """Format generic data into MCP response"""
        try:
            response = MCPResponse()
            
            if isinstance(data, str):
                response.add_text_content(data)
            elif isinstance(data, (dict, list)):
                if content_type == 'json':
                    # Add as JSON resource
                    uri = f"data://{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
                    response.add_json_content(data if isinstance(data, dict) else {'data': data}, uri)
                else:
                    # Convert to text
                    response.add_text_content(str(data))
            else:
                response.add_text_content(str(data))
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to format generic response: {e}")
            error_response = MCPResponse(isError=True)
            error_response.add_text_content(f"Generic response formatting failed: {str(e)}")
            return error_response
    
    def format_tool_list_response(self, tools: List[Dict[str, Any]]) -> MCPResponse:
        """Format tool list into MCP response"""
        try:
            response = MCPResponse()
            
            # Add summary text
            tool_count = len(tools)
            tool_names = [tool.get('name', 'unknown') for tool in tools]
            
            summary_text = f"Available MCP Tools ({tool_count}):\n"
            for i, tool in enumerate(tools, 1):
                name = tool.get('name', 'unknown')
                description = tool.get('description', 'No description')
                summary_text += f"{i}. {name}: {description}\n"
            
            response.add_text_content(summary_text.strip())
            
            # Add detailed tool information as JSON resource
            uri = f"tools://{datetime.utcnow().strftime('%Y-%m-%d')}"
            tools_data = {
                'tool_count': tool_count,
                'tools': tools,
                'timestamp': datetime.utcnow().isoformat()
            }
            response.add_json_content(tools_data, uri)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to format tool list response: {e}")
            error_response = MCPResponse(isError=True)
            error_response.add_text_content(f"Tool list formatting failed: {str(e)}")
            return error_response
    
    def add_metadata_to_response(self, response: MCPResponse, metadata: Dict[str, Any]) -> MCPResponse:
        """Add metadata to an existing MCP response"""
        try:
            # Add metadata as a separate resource
            uri = f"metadata://{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            response.add_json_content(metadata, uri)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to add metadata to response: {e}")
            return response
    
    def validate_response_format(self, response: MCPResponse) -> bool:
        """Validate that response conforms to MCP format"""
        try:
            # Check basic structure
            if not isinstance(response, MCPResponse):
                return False
            
            # Check content structure
            if not isinstance(response.content, list):
                return False
            
            # Validate each content item
            for item in response.content:
                if not isinstance(item, dict):
                    return False
                
                item_type = item.get('type')
                if item_type not in ['text', 'resource']:
                    return False
                
                if item_type == 'text' and 'text' not in item:
                    return False
                
                if item_type == 'resource' and 'resource' not in item:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Response validation failed: {e}")
            return False
    
    def get_formatter_info(self) -> Dict[str, Any]:
        """Get information about the response formatter"""
        return {
            'service': 'MCPResponseFormatter',
            'supported_content_types': list(self.default_mime_types.keys()),
            'mime_types': self.default_mime_types,
            'timestamp': datetime.utcnow().isoformat()
        }