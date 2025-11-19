"""
MCP Tool Registry for managing available tools and their schemas
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from .schemas import MCPToolSchema, DEFAULT_MCP_TOOLS, MCPResponse

logger = logging.getLogger(__name__)


class MCPToolRegistry:
    """Registry for managing MCP tools and their execution"""
    
    def __init__(self):
        self._tools: Dict[str, MCPToolSchema] = {}
        self._tool_handlers: Dict[str, Callable] = {}
        self._initialize_default_tools()
    
    def _initialize_default_tools(self) -> None:
        """Initialize with default MCP tools"""
        for tool in DEFAULT_MCP_TOOLS:
            self.register_tool(tool)
        
        logger.info(f"Initialized MCP tool registry with {len(self._tools)} default tools")
    
    def register_tool(self, tool_schema: MCPToolSchema, handler: Optional[Callable] = None) -> None:
        """Register a new MCP tool"""
        self._tools[tool_schema.name] = tool_schema
        
        if handler:
            self._tool_handlers[tool_schema.name] = handler
        
        logger.info(f"Registered MCP tool: {tool_schema.name}")
    
    def register_tool_handler(self, tool_name: str, handler: Callable) -> None:
        """Register a handler for a specific tool"""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        
        self._tool_handlers[tool_name] = handler
        logger.info(f"Registered handler for MCP tool: {tool_name}")
    
    def get_tool_schema(self, tool_name: str) -> Optional[MCPToolSchema]:
        """Get schema for a specific tool"""
        return self._tools.get(tool_name)
    
    def get_all_tool_schemas(self) -> List[MCPToolSchema]:
        """Get all registered tool schemas"""
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """Get list of all registered tool names"""
        return list(self._tools.keys())
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered"""
        return tool_name in self._tools
    
    def has_handler(self, tool_name: str) -> bool:
        """Check if a tool has a registered handler"""
        return tool_name in self._tool_handlers
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> MCPResponse:
        """Execute a tool with given parameters"""
        try:
            # Validate tool exists
            if not self.has_tool(tool_name):
                response = MCPResponse(isError=True)
                response.add_text_content(f"Tool '{tool_name}' not found in registry")
                return response
            
            # Validate handler exists
            if not self.has_handler(tool_name):
                response = MCPResponse(isError=True)
                response.add_text_content(f"No handler registered for tool '{tool_name}'")
                return response
            
            # Get tool schema and handler
            tool_schema = self._tools[tool_name]
            handler = self._tool_handlers[tool_name]
            
            # Validate parameters against schema
            validation_error = self._validate_parameters(tool_schema, parameters)
            if validation_error:
                response = MCPResponse(isError=True)
                response.add_text_content(f"Parameter validation failed: {validation_error}")
                return response
            
            # Execute the tool handler
            logger.info(f"Executing MCP tool: {tool_name} with parameters: {parameters}")
            result = await handler(parameters)
            
            # Ensure result is an MCPResponse
            if not isinstance(result, MCPResponse):
                # Convert to MCPResponse if needed
                response = MCPResponse()
                if isinstance(result, dict):
                    response.add_json_content(result)
                else:
                    response.add_text_content(str(result))
                return response
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution failed for '{tool_name}': {e}")
            response = MCPResponse(isError=True)
            response.add_text_content(f"Tool execution failed: {str(e)}")
            return response
    
    def _validate_parameters(self, tool_schema: MCPToolSchema, parameters: Dict[str, Any]) -> Optional[str]:
        """Validate parameters against tool schema"""
        try:
            schema = tool_schema.parameters
            
            # Check required parameters
            required = schema.get('required', [])
            for param in required:
                if param not in parameters:
                    return f"Missing required parameter: {param}"
            
            # Basic type validation for properties
            properties = schema.get('properties', {})
            for param_name, param_value in parameters.items():
                if param_name in properties:
                    expected_type = properties[param_name].get('type')
                    
                    if expected_type == 'string' and not isinstance(param_value, str):
                        return f"Parameter '{param_name}' must be a string"
                    elif expected_type == 'boolean' and not isinstance(param_value, bool):
                        return f"Parameter '{param_name}' must be a boolean"
                    elif expected_type == 'number' and not isinstance(param_value, (int, float)):
                        return f"Parameter '{param_name}' must be a number"
            
            return None  # No validation errors
            
        except Exception as e:
            return f"Parameter validation error: {str(e)}"
    
    def get_registry_info(self) -> Dict[str, Any]:
        """Get information about the tool registry"""
        return {
            'total_tools': len(self._tools),
            'tools_with_handlers': len(self._tool_handlers),
            'available_tools': [
                {
                    'name': tool.name,
                    'description': tool.description,
                    'has_handler': tool.name in self._tool_handlers
                }
                for tool in self._tools.values()
            ]
        }
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool from the registry"""
        if tool_name in self._tools:
            del self._tools[tool_name]
            if tool_name in self._tool_handlers:
                del self._tool_handlers[tool_name]
            logger.info(f"Unregistered MCP tool: {tool_name}")
            return True
        return False
    
    def clear_registry(self) -> None:
        """Clear all tools from the registry"""
        self._tools.clear()
        self._tool_handlers.clear()
        logger.info("Cleared MCP tool registry")
    
    def list_tools_for_mcp(self) -> List[Dict[str, Any]]:
        """Get tool list in MCP protocol format"""
        return [tool.to_dict() for tool in self._tools.values()]


# Global tool registry instance
mcp_tool_registry = MCPToolRegistry()