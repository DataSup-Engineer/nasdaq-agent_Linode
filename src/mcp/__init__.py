"""
MCP (Model Context Protocol) server integration for NASDAQ Stock Agent
"""

# Always available - no external dependencies
from .schemas import MCPToolSchema, MCPResponse, MCPRequest

# Conditionally import modules that have dependencies
try:
    from .mcp_server import MCPServer, mcp_server
    from .tool_registry import MCPToolRegistry, mcp_tool_registry
    from .request_handler import MCPRequestHandler
    from .response_formatter import MCPResponseFormatter
    from .tools import MCPToolImplementations, mcp_tool_implementations
    
    __all__ = [
        'MCPServer',
        'mcp_server',
        'MCPToolRegistry',
        'mcp_tool_registry',
        'MCPRequestHandler',
        'MCPResponseFormatter',
        'MCPToolImplementations',
        'mcp_tool_implementations',
        'MCPToolSchema',
        'MCPResponse',
        'MCPRequest'
    ]
except ImportError as e:
    # If dependencies are not available, only export basic schemas
    __all__ = [
        'MCPToolSchema',
        'MCPResponse',
        'MCPRequest'
    ]