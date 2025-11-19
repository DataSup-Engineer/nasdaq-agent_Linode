"""
MCP Request Handler for routing tool calls to appropriate services
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .tool_registry import MCPToolRegistry
from .schemas import MCPResponse
from .tools import mcp_tool_implementations

# Use absolute imports to avoid circular import issues
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.stock_analysis_agent import agent_orchestrator
from services.logging_service import logging_service

logger = logging.getLogger(__name__)


class MCPRequestHandler:
    """Handles MCP requests and routes them to appropriate services"""
    
    def __init__(self, tool_registry: MCPToolRegistry):
        self.tool_registry = tool_registry
        self.agent_orchestrator = None
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the request handler with service dependencies"""
        try:
            # Get the global agent orchestrator
            self.agent_orchestrator = agent_orchestrator
            
            # Register tool handlers
            self._register_tool_handlers()
            
            self.is_initialized = True
            logger.info("MCP request handler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP request handler: {e}")
            raise
    
    def _register_tool_handlers(self) -> None:
        """Register handlers for each MCP tool"""
        try:
            # Get tool implementations from the dedicated tools module
            tool_implementations = mcp_tool_implementations.get_tool_implementations()
            
            # Register each tool handler
            for tool_name, handler_func in tool_implementations.items():
                self.tool_registry.register_tool_handler(tool_name, handler_func)
                logger.info(f"Registered MCP tool handler: {tool_name}")
            
            logger.info(f"Registered {len(tool_implementations)} MCP tool handlers")
            
        except Exception as e:
            logger.error(f"Failed to register MCP tool handlers: {e}")
            raise
    
    async def handle_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> MCPResponse:
        """Handle an MCP tool call request"""
        start_time = datetime.utcnow()
        
        try:
            if not self.is_initialized:
                response = MCPResponse(isError=True)
                response.add_text_content("MCP request handler not initialized")
                return response
            
            # Log the request
            logger.info(f"Handling MCP tool call: {tool_name} with parameters: {parameters}")
            
            # Execute through tool registry
            result = await self.tool_registry.execute_tool(tool_name, parameters)
            
            # Calculate processing time
            processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Log MCP request to the same audit trail as REST API
            await self._log_mcp_request(tool_name, parameters, result, processing_time_ms)
            
            return result
            
        except Exception as e:
            processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"MCP tool call handling failed: {e}")
            
            # Log the error
            await logging_service.log_error(e, {
                'context': 'mcp_tool_call',
                'tool_name': tool_name,
                'parameters': parameters,
                'processing_time_ms': processing_time_ms
            })
            
            response = MCPResponse(isError=True)
            response.add_text_content(f"Tool call handling failed: {str(e)}")
            return response
    

    
    async def _log_mcp_request(self, tool_name: str, parameters: Dict[str, Any], 
                              response: MCPResponse, processing_time_ms: int) -> None:
        """Log MCP request to the same audit trail as REST API"""
        try:
            # Create MCP request log entry
            mcp_log_context = {
                'log_type': 'mcp_request',
                'tool_name': tool_name,
                'parameters': parameters,
                'response_content_count': len(response.content),
                'is_error': response.isError,
                'processing_time_ms': processing_time_ms,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Extract relevant data for analysis logging if it's an analyze_stock call
            if tool_name == 'analyze_stock' and not response.isError:
                # Try to extract analysis data from response content
                analysis_data = None
                for content_item in response.content:
                    if content_item.get('type') == 'resource':
                        resource = content_item.get('resource', {})
                        if resource.get('mimeType') == 'application/json':
                            try:
                                import json
                                analysis_data = json.loads(resource.get('text', '{}'))
                                break
                            except json.JSONDecodeError:
                                pass
                
                # Analysis data is logged via log_api_request below
            
            # Always log the MCP request itself
            await logging_service.log_api_request(
                endpoint=f"mcp://{tool_name}",
                method="MCP_TOOL_CALL",
                request_data=parameters,
                response_data={'content_items': len(response.content), 'is_error': response.isError},
                status_code=500 if response.isError else 200,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            logger.error(f"Failed to log MCP request: {e}")
            # Don't raise - logging failure shouldn't break the tool call
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            self.is_initialized = False
            logger.info("MCP request handler cleaned up")
        except Exception as e:
            logger.error(f"MCP request handler cleanup failed: {e}")
    
    def get_handler_status(self) -> Dict[str, Any]:
        """Get status information about the request handler"""
        return {
            'service': 'MCPRequestHandler',
            'is_initialized': self.is_initialized,
            'has_agent_orchestrator': self.agent_orchestrator is not None,
            'registered_handlers': len(self.tool_registry._tool_handlers),
            'timestamp': datetime.utcnow().isoformat()
        }