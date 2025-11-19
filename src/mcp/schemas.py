"""
MCP (Model Context Protocol) schema definitions and data models
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json


@dataclass
class MCPToolSchema:
    """Schema definition for an MCP tool"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for parameters
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP protocol"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameters
        }


@dataclass
class MCPRequest:
    """MCP request structure"""
    method: str
    params: Dict[str, Any]
    id: Optional[Union[str, int]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPRequest':
        """Create MCPRequest from dictionary"""
        return cls(
            method=data.get('method', ''),
            params=data.get('params', {}),
            id=data.get('id')
        )


@dataclass
class MCPResponse:
    """MCP response structure"""
    content: List[Dict[str, Any]] = field(default_factory=list)
    isError: bool = False
    
    def add_text_content(self, text: str) -> None:
        """Add text content to response"""
        self.content.append({
            "type": "text",
            "text": text
        })
    
    def add_resource_content(self, uri: str, mime_type: str, text: str) -> None:
        """Add resource content to response"""
        self.content.append({
            "type": "resource",
            "resource": {
                "uri": uri,
                "mimeType": mime_type,
                "text": text
            }
        })
    
    def add_json_content(self, data: Dict[str, Any], uri: str = None) -> None:
        """Add JSON data as resource content"""
        json_text = json.dumps(data, indent=2, default=str)
        uri = uri or f"analysis://{data.get('ticker', 'unknown')}/{datetime.utcnow().strftime('%Y-%m-%d')}"
        self.add_resource_content(uri, "application/json", json_text)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP protocol"""
        return {
            "content": self.content,
            "isError": self.isError
        }


# MCP Tool Schema Definitions
ANALYZE_STOCK_TOOL = MCPToolSchema(
    name="analyze_stock",
    description="Analyze a NASDAQ stock and provide investment recommendations with AI-powered insights",
    parameters={
        "type": "object",
        "properties": {
            "company_name_or_ticker": {
                "type": "string",
                "description": "Company name (e.g., 'Apple', 'Microsoft') or ticker symbol (e.g., 'AAPL', 'MSFT')"
            }
        },
        "required": ["company_name_or_ticker"]
    }
)

GET_MARKET_DATA_TOOL = MCPToolSchema(
    name="get_market_data",
    description="Retrieve current and historical market data for a NASDAQ stock",
    parameters={
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker symbol (e.g., 'AAPL', 'MSFT')"
            },
            "include_historical": {
                "type": "boolean",
                "description": "Whether to include 6-month historical data",
                "default": True
            }
        },
        "required": ["ticker"]
    }
)

RESOLVE_COMPANY_NAME_TOOL = MCPToolSchema(
    name="resolve_company_name",
    description="Convert company name to NASDAQ ticker symbol with fuzzy matching",
    parameters={
        "type": "object",
        "properties": {
            "company_name": {
                "type": "string",
                "description": "Company name to resolve (e.g., 'Apple Inc.', 'Microsoft Corporation')"
            }
        },
        "required": ["company_name"]
    }
)

# Default MCP tools available
DEFAULT_MCP_TOOLS = [
    ANALYZE_STOCK_TOOL,
    GET_MARKET_DATA_TOOL,
    RESOLVE_COMPANY_NAME_TOOL
]