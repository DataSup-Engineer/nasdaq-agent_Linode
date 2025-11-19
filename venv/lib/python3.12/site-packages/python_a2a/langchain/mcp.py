"""
MCP protocol conversions for LangChain integration.

This module provides functions to convert between LangChain tools and MCP servers/tools.
"""

import logging
import asyncio
import inspect
import json
import requests
from typing import Any, Dict, List, Optional, Union, Callable, Type, get_type_hints

logger = logging.getLogger(__name__)

# Import custom exceptions
from .exceptions import (
    LangChainNotInstalledError,
    LangChainToolConversionError,
    MCPToolConversionError
)

# Check for LangChain availability without failing
try:
    # Try to import LangChain components
    try:
        from langchain_core.tools import BaseTool, ToolException
    except ImportError:
        # Fall back to older LangChain structure
        from langchain.tools import BaseTool, ToolException
    
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    # Create stub classes for type hints
    class BaseTool:
        name: str
        description: str
    
    class ToolException(Exception):
        pass


# Utility for mapping between Python types and MCP types
class TypeMapper:
    """Maps between Python types and MCP parameter types."""
    
    # Map Python types to MCP types
    PYTHON_TO_MCP = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        None: "string"  # Default
    }
    
    # Map MCP types to Python types
    MCP_TO_PYTHON = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict
    }
    
    @classmethod
    def to_mcp_type(cls, python_type: Type) -> str:
        """Convert Python type to MCP type string."""
        # Handle generic types like List[str]
        origin = getattr(python_type, "__origin__", None)
        if origin is not None:
            # Map the origin type
            if origin in cls.PYTHON_TO_MCP:
                return cls.PYTHON_TO_MCP[origin]
            # Fall back to string for unknown generics
            return "string"
        
        # Handle direct type mappings
        return cls.PYTHON_TO_MCP.get(python_type, "string")
    
    @classmethod
    def to_python_type(cls, mcp_type: str) -> Type:
        """Convert MCP type string to Python type."""
        return cls.MCP_TO_PYTHON.get(mcp_type, str)


class ParameterExtractor:
    """Extracts parameter information from LangChain tools."""
    
    @classmethod
    def extract_from_tool(cls, tool: Any) -> List[Dict[str, Any]]:
        """Extract parameters from a LangChain tool using multiple strategies."""
        # Use multiple strategies in order of preference
        
        # Strategy 1: Try to get from args_schema
        parameters = cls._extract_from_args_schema(tool)
        if parameters:
            return parameters
        
        # Strategy 2: Try to get from _run method signature
        if hasattr(tool, "_run"):
            parameters = cls._extract_from_method(tool._run)
            if parameters:
                return parameters
        
        # Strategy 3: Try to get from func attribute
        if hasattr(tool, "func") and callable(tool.func):
            parameters = cls._extract_from_method(tool.func)
            if parameters:
                return parameters
        
        # Strategy 4: Fall back to default single parameter
        return cls._default_parameter(tool)
    
    @classmethod
    def _extract_from_args_schema(cls, tool: Any) -> List[Dict[str, Any]]:
        """Extract parameters from tool's args_schema attribute."""
        if not hasattr(tool, "args_schema") or not tool.args_schema:
            return []
        
        parameters = []
        schema_cls = tool.args_schema
        
        if hasattr(schema_cls, "__annotations__"):
            for field_name, field_type in schema_cls.__annotations__.items():
                # Determine required status and description
                required = True
                description = f"Parameter: {field_name}"
                
                # Try to get field info from different Pydantic versions
                if hasattr(schema_cls, "__fields__"):  # Pydantic v1
                    field_info = schema_cls.__fields__.get(field_name)
                    if field_info and hasattr(field_info, "field_info"):
                        required = not field_info.allow_none
                        field_desc = getattr(field_info.field_info, "description", None)
                        if field_desc:
                            description = field_desc
                
                elif hasattr(schema_cls, "model_fields"):  # Pydantic v2
                    field_info = schema_cls.model_fields.get(field_name)
                    if field_info:
                        required = not getattr(field_info, "allow_none", False)
                        field_desc = getattr(field_info, "description", None)
                        if field_desc:
                            description = field_desc
                
                # Create parameter schema
                parameters.append({
                    "name": field_name,
                    "type": TypeMapper.to_mcp_type(field_type),
                    "description": description,
                    "required": required
                })
        
        return parameters
    
    @classmethod
    def _extract_from_method(cls, method: Callable) -> List[Dict[str, Any]]:
        """Extract parameters from a method signature."""
        parameters = []
        
        try:
            sig = inspect.signature(method)
            type_hints = get_type_hints(method)
            
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                if param_name == "config":  # Skip config parameter for LangChain tools
                    continue
                
                param_type = type_hints.get(param_name, str)
                param_required = param.default == inspect.Parameter.empty
                
                parameters.append({
                    "name": param_name,
                    "type": TypeMapper.to_mcp_type(param_type),
                    "description": f"Parameter: {param_name}",
                    "required": param_required
                })
        except Exception as e:
            logger.debug(f"Error extracting parameters from method: {e}")
        
        return parameters
    
    @classmethod
    def _default_parameter(cls, tool: Any) -> List[Dict[str, Any]]:
        """Create a default single parameter for tools."""
        return [{
            "name": "input",
            "type": "string",
            "description": f"Input for {tool.name}",
            "required": True
        }]


class ToolUtil:
    """Utility functions for working with LangChain tools."""
    
    @staticmethod
    def normalize_input(tool: Any, **kwargs) -> Any:
        """Normalize input data for a tool based on its expected format."""
        # Check for single string input pattern
        single_string_input = getattr(tool, "expects_string_input", False)
        if single_string_input:
            if len(kwargs) == 1:
                # If only one parameter, pass its value directly
                return next(iter(kwargs.values()))
            # Otherwise, serialize to JSON
            return json.dumps(kwargs)
        
        # Check signature of _run method
        if hasattr(tool, "_run"):
            sig = inspect.signature(tool._run)
            params = list(sig.parameters.values())
            
            # If only one non-self parameter and it's not **kwargs
            if len(params) == 2 and params[1].name != "kwargs" and params[1].kind != inspect.Parameter.VAR_KEYWORD:
                # If we have just the expected parameter, pass its value
                if len(kwargs) == 1 and next(iter(kwargs.keys())) == params[1].name:
                    return next(iter(kwargs.values()))
                # Otherwise, pass all kwargs as a single param if possible
                if len(kwargs) == 1:
                    return next(iter(kwargs.values()))
        
        # Check signature of func attribute if available
        if hasattr(tool, "func") and callable(tool.func):
            try:
                sig = inspect.signature(tool.func)
                param_names = set()
                for param_name, param in sig.parameters.items():
                    if param_name != "self" and param_name != "config":
                        param_names.add(param_name)
                
                # Filter kwargs to only include parameters that exist in the function signature
                filtered_kwargs = {}
                for key, value in kwargs.items():
                    if key in param_names:
                        filtered_kwargs[key] = value
                
                if filtered_kwargs:
                    return filtered_kwargs
            except Exception as e:
                logger.debug(f"Error analyzing func signature: {e}")
        
        # Default: return kwargs as is
        return kwargs
    
    @staticmethod
    def normalize_output(result: Any) -> Dict[str, Any]:
        """Normalize tool output to MCP response format."""
        # Already in MCP format with text or error key
        if isinstance(result, dict) and ("text" in result or "error" in result):
            return result
        
        # String result
        if isinstance(result, str):
            return {"text": result}
        
        # Error result
        if isinstance(result, Exception):
            return {"error": str(result)}
        
        # None result
        if result is None:
            return {"text": ""}
        
        # Any other type, convert to string
        return {"text": str(result)}


def to_mcp_server(langchain_tools):
    """
    Create an MCP server that exposes LangChain tools.
    
    Args:
        langchain_tools: Single tool or list of LangChain tools
    
    Returns:
        MCP server instance
    
    Example:
        >>> from langchain.tools import Tool
        >>> calculator = Tool(name="calculator", func=lambda x: eval(x))
        >>> server = to_mcp_server([calculator])
        >>> server.run(port=8000)
        
    Raises:
        LangChainNotInstalledError: If LangChain is not installed
        LangChainToolConversionError: If tool conversion fails
    """
    if not HAS_LANGCHAIN:
        raise LangChainNotInstalledError()
    
    try:
        from python_a2a.mcp import FastMCP
        
        # Create server instance with explicit name and description
        server = FastMCP(
            name="LangChain Tools",
            description="MCP server exposing LangChain tools"
        )
        
        # Store tools map in the server for later reference
        server.tools_map = {}
        
        # Handle single tool case
        if not isinstance(langchain_tools, list):
            langchain_tools = [langchain_tools]
        
        # Register each tool with the server
        for tool in langchain_tools:
            # Validate tool
            if not hasattr(tool, "name"):
                raise LangChainToolConversionError("Tool must have a name attribute")
            
            # Check for execution method (one of them must exist)
            executable = (hasattr(tool, "_run") or hasattr(tool, "func") or 
                          (hasattr(tool, "__call__") and callable(tool)))
            if not executable:
                raise LangChainToolConversionError(
                    f"Tool '{tool.name}' has no execution method (_run, func, or __call__)"
                )
            
            # Get tool information
            tool_name = tool.name
            tool_description = getattr(tool, "description", f"Tool: {tool_name}")
            
            # Store the tool for later reference
            server.tools_map[tool_name] = tool
            
            # Extract parameter information
            parameters = ParameterExtractor.extract_from_tool(tool)
            
            # Create a wrapper function for this tool
            def create_tool_wrapper(current_tool_name, current_tool):
                # Create the async wrapper function
                async def wrapper(**kwargs):
                    """Wrapper that calls the LangChain tool."""
                    try:
                        # Extract parameters for the specific tool being called
                        input_data = kwargs
                        
                        # Get parameters specific to this tool's function
                        if hasattr(current_tool, "func") and callable(current_tool.func):
                            try:
                                sig = inspect.signature(current_tool.func)
                                valid_params = {}
                                
                                # Only include parameters that exist in the function signature
                                for param_name, param in sig.parameters.items():
                                    if param_name in kwargs:
                                        valid_params[param_name] = kwargs[param_name]
                                
                                if valid_params:
                                    input_data = valid_params
                            except Exception as e:
                                logger.debug(f"Error analyzing func signature: {e}")
                        
                        # Try using func directly first if available
                        result = None
                        if hasattr(current_tool, "func") and callable(current_tool.func):
                            loop = asyncio.get_event_loop()
                            try:
                                if isinstance(input_data, dict):
                                    result = await loop.run_in_executor(
                                        None, 
                                        lambda: current_tool.func(**input_data)
                                    )
                                else:
                                    result = await loop.run_in_executor(
                                        None, 
                                        lambda: current_tool.func(input_data)
                                    )
                            except Exception as e:
                                logger.debug(f"Error using func directly: {e}")
                                # Continue to other methods
                        
                        # If no result yet, try _run with config parameter
                        if result is None and hasattr(current_tool, "_run"):
                            loop = asyncio.get_event_loop()
                            try:
                                if isinstance(input_data, dict):
                                    result = await loop.run_in_executor(
                                        None, 
                                        lambda: current_tool._run(config={}, **input_data)
                                    )
                                else:
                                    result = await loop.run_in_executor(
                                        None, 
                                        lambda: current_tool._run(input_data, config={})
                                    )
                            except TypeError as e:
                                if "config" in str(e):
                                    # Try without config for older versions
                                    try:
                                        if isinstance(input_data, dict):
                                            result = await loop.run_in_executor(
                                                None, 
                                                lambda: current_tool._run(**input_data)
                                            )
                                        else:
                                            result = await loop.run_in_executor(
                                                None, 
                                                lambda: current_tool._run(input_data)
                                            )
                                    except Exception as inner_e:
                                        logger.debug(f"Error in _run without config: {inner_e}")
                                else:
                                    logger.debug(f"TypeError in _run: {e}")
                            except Exception as e:
                                logger.debug(f"Error in _run: {e}")
                        
                        # If we still have no result, raise an error
                        if result is None:
                            return {"error": f"Failed to execute tool {current_tool_name} with the provided parameters"}
                        
                        # Normalize the output
                        return ToolUtil.normalize_output(result)
                    
                    except ToolException as e:
                        # Handle LangChain tool exceptions
                        logger.warning(f"Tool exception in {current_tool_name}: {e}")
                        return {"error": str(e)}
                    except Exception as e:
                        # Handle any other exceptions
                        logger.exception(f"Error calling tool {current_tool_name}")
                        return {"error": f"Error: {str(e)}"}
                
                return wrapper
            
            # Create and register wrapper for this specific tool
            wrapper_func = create_tool_wrapper(tool_name, tool)
            
            # Use decorator pattern to register the tool with FastMCP
            server.tool(
                name=tool_name,
                description=tool_description
            )(wrapper_func)
            
            logger.debug(f"Registered tool: {tool_name}")
        
        return server
        
    except Exception as e:
        logger.exception("Failed to create MCP server from LangChain tools")
        raise LangChainToolConversionError(f"Failed to convert LangChain tools: {str(e)}")


def to_langchain_tool(mcp_url, tool_name=None):
    """
    Convert MCP server tool(s) to LangChain tool(s).
    
    Args:
        mcp_url: URL of the MCP server
        tool_name: Optional specific tool to convert (if None, converts all tools)
    
    Returns:
        LangChain tool or list of tools
    
    Example:
        >>> # Convert a specific tool
        >>> calculator_tool = to_langchain_tool("http://localhost:8000", "calculator")
        >>> 
        >>> # Convert all tools from a server
        >>> tools = to_langchain_tool("http://localhost:8000")
        
    Raises:
        LangChainNotInstalledError: If LangChain is not installed
        MCPToolConversionError: If tool conversion fails
    """
    if not HAS_LANGCHAIN:
        raise LangChainNotInstalledError()
    
    try:
        # Try to import Tool from various possible locations in LangChain
        try:
            from langchain.tools import Tool
        except ImportError:
            try:
                from langchain.agents import Tool
            except ImportError:
                raise ImportError("Cannot import Tool class from LangChain")
        
        # Get available tools from MCP server - try multiple discovery methods
        available_tools = None
        discovery_errors = []
        
        try:
            # Method 1: Try GET request (python-a2a FastMCP style)
            logger.debug("Trying GET /tools for tool discovery")
            tools_response = requests.get(f"{mcp_url}/tools", timeout=10)
            if tools_response.status_code == 200:
                available_tools = tools_response.json()
                logger.info(f"Found {len(available_tools)} tools using GET /tools")
            else:
                discovery_errors.append(f"GET /tools returned {tools_response.status_code}")
        except requests.exceptions.RequestException as e:
            discovery_errors.append(f"GET /tools failed: {str(e)}")
        
        # Method 2: Try POST request (fastmcp package style) 
        if available_tools is None:
            try:
                logger.debug("Trying POST /tools for tool discovery")
                tools_response = requests.post(f"{mcp_url}/tools", timeout=10)
                if tools_response.status_code == 200:
                    available_tools = tools_response.json()
                    logger.info(f"Found {len(available_tools)} tools using POST /tools")
                else:
                    discovery_errors.append(f"POST /tools returned {tools_response.status_code}")
            except requests.exceptions.RequestException as e:
                discovery_errors.append(f"POST /tools failed: {str(e)}")
        
        # Method 3: Try MCP JSON-RPC protocol for tools/list
        if available_tools is None:
            try:
                logger.debug("Trying MCP JSON-RPC tools/list")
                json_rpc_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                }
                tools_response = requests.post(
                    mcp_url, 
                    json=json_rpc_request,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                if tools_response.status_code == 200:
                    response_data = tools_response.json()
                    if "result" in response_data and "tools" in response_data["result"]:
                        available_tools = response_data["result"]["tools"]
                        logger.info(f"Found {len(available_tools)} tools using MCP JSON-RPC")
                    else:
                        discovery_errors.append("MCP JSON-RPC response missing 'result.tools'")
                else:
                    discovery_errors.append(f"MCP JSON-RPC returned {tools_response.status_code}")
            except requests.exceptions.RequestException as e:
                discovery_errors.append(f"MCP JSON-RPC failed: {str(e)}")
            except (KeyError, ValueError) as e:
                discovery_errors.append(f"MCP JSON-RPC response parsing failed: {str(e)}")
        
        # Method 4: Try using the python-a2a MCP client directly
        if available_tools is None:
            try:
                logger.debug("Trying python-a2a MCP client for tool discovery")
                from ..mcp.client import MCPClient
                
                # Try to create MCP client and get tools
                mcp_client = MCPClient(server_url=mcp_url)
                tools_list = mcp_client.get_tools_sync()
                if tools_list:
                    available_tools = tools_list
                    logger.info(f"Found {len(available_tools)} tools using MCP client")
                else:
                    discovery_errors.append("MCP client returned empty tools list")
            except Exception as e:
                discovery_errors.append(f"MCP client failed: {str(e)}")
        
        # If all methods failed, handle fallback
        if available_tools is None:
            if tool_name:
                # If a specific tool is requested, create it anyway with a warning
                logger.warning(f"Could not discover tools from server, creating tool '{tool_name}' directly")
                logger.debug(f"Discovery attempts failed: {'; '.join(discovery_errors)}")
                available_tools = [{"name": tool_name, "description": f"MCP Tool: {tool_name}"}]
            else:
                # No tool name specified and discovery failed
                error_summary = "; ".join(discovery_errors[:3])  # Limit error message length
                raise MCPToolConversionError(
                    f"Failed to get tools from MCP server: {error_summary}. "
                    f"Tried GET/POST /tools, MCP JSON-RPC, and python-a2a client. "
                    f"Server might not be running or might not follow MCP protocol."
                )
        
        # Filter tools if a specific tool is requested
        if tool_name is not None:
            available_tools = [t for t in available_tools if t.get("name") == tool_name]
            if not available_tools:
                raise MCPToolConversionError(f"Tool '{tool_name}' not found on MCP server at {mcp_url}")
        
        # Create LangChain tools
        langchain_tools = []
        
        for tool_info in available_tools:
            name = tool_info.get("name", "unnamed_tool")
            description = tool_info.get("description", f"MCP Tool: {name}")
            parameters = tool_info.get("parameters", [])
            
            logger.info(f"Creating LangChain tool for MCP tool: {name}")
            
            # Create function to call the MCP tool
            def create_tool_func(tool_name):
                # Need this wrapper to properly capture tool_name in closure
                def tool_func(*args, **kwargs):
                    """Call MCP tool function"""
                    try:
                        # Handle different input patterns
                        if len(args) == 1 and not kwargs:
                            input_value = args[0]
                            
                            # If the input looks like a parameter=value string (for multi-param tools)
                            if '=' in input_value and not input_value.startswith('{'):
                                # Parse simple param=value&param2=value2 format
                                params = {}
                                for pair in input_value.split('&'):
                                    if '=' in pair:
                                        k, v = pair.split('=', 1)
                                        params[k.strip()] = v.strip()
                                if params:
                                    kwargs = params
                            # Try to detect parameter format based on tool parameters
                            elif parameters and len(parameters) == 1:
                                # Single parameter case - use the parameter name from tool info
                                param_name = parameters[0]["name"]
                                kwargs = {param_name: input_value}
                            else:
                                # Default to 'input' parameter
                                kwargs = {"input": input_value}
                        
                        # Call the MCP tool - try multiple execution methods
                        execution_result = None
                        execution_errors = []
                        
                        # Method 1: Try REST API call (FastMCP style)
                        try:
                            response = requests.post(
                                f"{mcp_url}/tools/{tool_name}",
                                json=kwargs,
                                timeout=30
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                
                                # Process error in response
                                if "error" in result:
                                    execution_result = f"Error: {result['error']}"
                                # Process content in response
                                elif "content" in result:
                                    content = result.get("content", [])
                                    if content and isinstance(content, list) and "text" in content[0]:
                                        execution_result = content[0]["text"]
                                    else:
                                        execution_result = str(result)
                                # Handle isError response format
                                elif "isError" in result and result["isError"]:
                                    execution_result = f"Error: {result.get('content', [{}])[0].get('text', 'Unknown error')}"
                                else:
                                    execution_result = str(result)
                            else:
                                execution_errors.append(f"REST API returned {response.status_code}: {response.text[:100]}")
                        except requests.exceptions.RequestException as e:
                            execution_errors.append(f"REST API failed: {str(e)}")
                        
                        # Method 2: Try MCP JSON-RPC protocol
                        if execution_result is None:
                            try:
                                json_rpc_request = {
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "tools/call",
                                    "params": {
                                        "name": tool_name,
                                        "arguments": kwargs
                                    }
                                }
                                response = requests.post(
                                    mcp_url,
                                    json=json_rpc_request,
                                    headers={"Content-Type": "application/json"},
                                    timeout=30
                                )
                                
                                if response.status_code == 200:
                                    rpc_result = response.json()
                                    if "result" in rpc_result:
                                        result_data = rpc_result["result"]
                                        if "content" in result_data:
                                            content = result_data["content"]
                                            if content and isinstance(content, list) and "text" in content[0]:
                                                execution_result = content[0]["text"]
                                            else:
                                                execution_result = str(result_data)
                                        else:
                                            execution_result = str(result_data)
                                    elif "error" in rpc_result:
                                        execution_result = f"Error: {rpc_result['error'].get('message', 'Unknown RPC error')}"
                                    else:
                                        execution_result = str(rpc_result)
                                else:
                                    execution_errors.append(f"JSON-RPC returned {response.status_code}")
                            except requests.exceptions.RequestException as e:
                                execution_errors.append(f"JSON-RPC failed: {str(e)}")
                            except (KeyError, ValueError) as e:
                                execution_errors.append(f"JSON-RPC parsing failed: {str(e)}")
                        
                        # Method 3: Try using the python-a2a MCP client directly
                        if execution_result is None:
                            try:
                                from ..mcp.client import MCPClient
                                mcp_client = MCPClient(server_url=mcp_url)
                                client_result = mcp_client.call_tool_sync(tool_name, kwargs)
                                
                                if hasattr(client_result, 'content') and client_result.content:
                                    if isinstance(client_result.content, list) and client_result.content:
                                        first_content = client_result.content[0]
                                        if isinstance(first_content, dict) and "text" in first_content:
                                            execution_result = first_content["text"]
                                        else:
                                            execution_result = str(first_content)
                                    else:
                                        execution_result = str(client_result.content)
                                elif hasattr(client_result, 'is_error') and client_result.is_error:
                                    execution_result = f"Error: {str(client_result)}"
                                else:
                                    execution_result = str(client_result)
                            except Exception as e:
                                execution_errors.append(f"MCP client failed: {str(e)}")
                        
                        # If all methods failed, return error summary
                        if execution_result is None:
                            error_summary = "; ".join(execution_errors[:2])  # Limit error length
                            return f"Failed to execute tool '{tool_name}': {error_summary}"
                        
                        return execution_result
                    except Exception as e:
                        logger.exception(f"Error calling MCP tool {tool_name}")
                        return f"Error calling tool: {str(e)}"
                
                return tool_func
            
            # Create the tool with a function that properly handles tool name in closure
            tool_func = create_tool_func(name)
            
            # Create the LangChain tool
            lc_tool = Tool(
                name=name,
                description=description,
                func=tool_func
            )
            
            # Add metadata if applicable
            if hasattr(lc_tool, "metadata"):
                lc_tool.metadata = {
                    "source": "mcp",
                    "url": mcp_url,
                    "parameters": parameters
                }
            
            langchain_tools.append(lc_tool)
            logger.info(f"Successfully created LangChain tool: {name}")
        
        # Return single tool if requested, otherwise return list
        if tool_name is not None and len(langchain_tools) == 1:
            return langchain_tools[0]
        
        return langchain_tools
        
    except MCPToolConversionError:
        # Re-raise without wrapping
        raise
    except Exception as e:
        logger.exception("Failed to convert MCP tool to LangChain format")
        raise MCPToolConversionError(f"Failed to convert MCP tool: {str(e)}")