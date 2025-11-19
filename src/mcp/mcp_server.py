"""
MCP (Model Context Protocol) Server implementation
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        ListToolsResult,
    )
except ImportError as e:
    # Fallback for development/testing
    logging.warning(f"MCP package not available: {e}")
    Server = None
    stdio_server = None

from .tool_registry import MCPToolRegistry, mcp_tool_registry
from .request_handler import MCPRequestHandler
from .response_formatter import MCPResponseFormatter
from .schemas import MCPResponse

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server implementation for NASDAQ Stock Agent"""
    
    def __init__(self, tool_registry: Optional[MCPToolRegistry] = None):
        self.tool_registry = tool_registry or mcp_tool_registry
        self.request_handler = MCPRequestHandler(self.tool_registry)
        self.response_formatter = MCPResponseFormatter()
        self.server = None
        self.is_running = False
        self.connection_count = 0
        self.start_time = None
        
        # Server configuration
        self.config = {
            "name": "nasdaq-stock-agent",
            "version": "1.0.0",
            "description": "AI-powered NASDAQ stock analysis and investment recommendations",
            "max_connections": 100,
            "connection_timeout": 300,  # 5 minutes
            "tool_execution_timeout": 60,  # 1 minute per tool call
            "enable_logging": True,
            "log_mcp_requests": True
        }
    
    def _create_mcp_server(self) -> Optional[Server]:
        """Create the MCP server instance"""
        if Server is None:
            logger.error("MCP package not available - cannot create server")
            return None
        
        try:
            server = Server(self.config["name"])
            
            # Register tool list handler
            @server.list_tools()
            async def handle_list_tools() -> ListToolsResult:
                """Handle MCP list tools request"""
                try:
                    tools = []
                    for tool_schema in self.tool_registry.get_all_tool_schemas():
                        tool = Tool(
                            name=tool_schema.name,
                            description=tool_schema.description,
                            inputSchema=tool_schema.parameters
                        )
                        tools.append(tool)
                    
                    logger.info(f"Listed {len(tools)} MCP tools")
                    return ListToolsResult(tools=tools)
                    
                except Exception as e:
                    logger.error(f"Failed to list MCP tools: {e}")
                    return ListToolsResult(tools=[])
            
            # Register tool call handler
            @server.call_tool()
            async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
                """Handle MCP tool call request"""
                try:
                    logger.info(f"MCP tool call: {name} with arguments: {arguments}")
                    
                    # Execute tool through request handler
                    mcp_response = await self.request_handler.handle_tool_call(name, arguments)
                    
                    # Convert MCPResponse to CallToolResult
                    content = []
                    for item in mcp_response.content:
                        if item.get("type") == "text":
                            content.append(TextContent(type="text", text=item["text"]))
                        # Add other content types as needed
                    
                    result = CallToolResult(content=content, isError=mcp_response.isError)
                    
                    if not mcp_response.isError:
                        logger.info(f"MCP tool call completed successfully: {name}")
                    else:
                        logger.warning(f"MCP tool call failed: {name}")
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"MCP tool call handler failed for '{name}': {e}")
                    error_content = [TextContent(type="text", text=f"Tool execution failed: {str(e)}")]
                    return CallToolResult(content=error_content, isError=True)
            
            logger.info("MCP server created successfully")
            return server
            
        except Exception as e:
            logger.error(f"Failed to create MCP server: {e}")
            return None
    
    async def start_server(self, host: str = "localhost", port: int = 8001) -> bool:
        """Start the MCP server"""
        try:
            if self.is_running:
                logger.warning("MCP server is already running")
                return True
            
            # Create server instance
            self.server = self._create_mcp_server()
            if not self.server:
                logger.error("Failed to create MCP server instance")
                return False
            
            # Initialize request handler with agent integration
            await self.request_handler.initialize()
            
            self.start_time = datetime.utcnow()
            self.is_running = True
            
            logger.info(f"MCP server started successfully on {host}:{port}")
            logger.info(f"Available tools: {', '.join(self.tool_registry.get_tool_names())}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            self.is_running = False
            return False
    
    async def run_stdio(self) -> None:
        """Run MCP server with stdio transport"""
        try:
            if not self.server:
                self.server = self._create_mcp_server()
                if not self.server:
                    raise RuntimeError("Failed to create MCP server")
            
            # Initialize request handler
            await self.request_handler.initialize()
            
            self.start_time = datetime.utcnow()
            self.is_running = True
            
            logger.info("Starting MCP server with stdio transport")
            
            if stdio_server:
                async with stdio_server() as (read_stream, write_stream):
                    await self.server.run(
                        read_stream,
                        write_stream,
                        InitializationOptions(
                            server_name=self.config["name"],
                            server_version=self.config["version"]
                        )
                    )
            else:
                logger.error("stdio_server not available")
                
        except Exception as e:
            logger.error(f"MCP stdio server failed: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.is_running = False
    
    async def stop_server(self) -> None:
        """Stop the MCP server"""
        try:
            if not self.is_running:
                logger.warning("MCP server is not running")
                return
            
            self.is_running = False
            
            # Cleanup request handler
            await self.request_handler.cleanup()
            
            logger.info("MCP server stopped successfully")
            
        except Exception as e:
            logger.error(f"Failed to stop MCP server: {e}")
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get MCP server status information"""
        uptime_seconds = 0
        if self.start_time:
            uptime_seconds = int((datetime.utcnow() - self.start_time).total_seconds())
        
        return {
            'service': 'MCPServer',
            'status': 'running' if self.is_running else 'stopped',
            'config': self.config,
            'uptime_seconds': uptime_seconds,
            'connection_count': self.connection_count,
            'available_tools': len(self.tool_registry.get_tool_names()),
            'tool_registry_info': self.tool_registry.get_registry_info(),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for monitoring"""
        status = self.get_server_status()
        
        # Determine health based on server state
        if self.is_running and self.server:
            health_status = 'healthy'
        elif self.is_running and not self.server:
            health_status = 'degraded'
        else:
            health_status = 'unhealthy'
        
        return {
            'service': 'MCPServer',
            'status': health_status,
            'is_running': self.is_running,
            'has_server_instance': self.server is not None,
            'available_tools': len(self.tool_registry.get_tool_names()),
            'uptime_seconds': status['uptime_seconds'],
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def validate_tool_schemas(self) -> Dict[str, Any]:
        """Validate all registered tool schemas"""
        validation_results = {
            'valid_tools': [],
            'invalid_tools': [],
            'total_tools': 0
        }
        
        try:
            for tool_schema in self.tool_registry.get_all_tool_schemas():
                validation_results['total_tools'] += 1
                
                # Basic schema validation
                if (tool_schema.name and 
                    tool_schema.description and 
                    isinstance(tool_schema.parameters, dict)):
                    validation_results['valid_tools'].append(tool_schema.name)
                else:
                    validation_results['invalid_tools'].append({
                        'name': tool_schema.name,
                        'error': 'Missing required fields or invalid parameters'
                    })
            
            logger.info(f"Tool schema validation: {len(validation_results['valid_tools'])} valid, "
                       f"{len(validation_results['invalid_tools'])} invalid")
            
        except Exception as e:
            logger.error(f"Tool schema validation failed: {e}")
            validation_results['error'] = str(e)
        
        return validation_results


# Global MCP server instance
mcp_server = MCPServer()