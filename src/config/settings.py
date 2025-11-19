"""
Configuration settings for the NASDAQ Stock Agent
"""
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Configuration
    app_name: str = Field(default="NASDAQ Stock Agent", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # Anthropic API Configuration
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", description="Anthropic model to use")
    
    # Yahoo Finance Configuration
    yfinance_timeout: int = Field(default=30, description="Yahoo Finance API timeout in seconds")
    
    # Caching Configuration
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL in seconds (5 minutes)")
    
    # Logging Configuration
    log_retention_days: int = Field(default=30, description="Log retention period in days")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per minute")
    max_concurrent_requests: int = Field(default=50, description="Maximum concurrent requests")
    
    # MCP Server Configuration
    mcp_enabled: bool = Field(default=True, description="Enable MCP server")
    mcp_host: str = Field(default="localhost", description="MCP server host")
    mcp_port: int = Field(default=8001, description="MCP server port")
    
    # NEST Framework Configuration (Agent-to-Agent Communication)
    nest_enabled: bool = Field(default=True, description="Enable NEST A2A communication")
    nest_port: int = Field(default=6000, description="NEST A2A server port")
    nest_public_url: Optional[str] = Field(default=None, description="Public URL for A2A endpoint")
    nest_registry_url: str = Field(default="http://registry.chat39.com:6900", description="NANDA Registry URL")
    nest_agent_id: str = Field(default="nasdaq-stock-agent", description="Unique agent identifier")
    nest_agent_name: str = Field(default="NASDAQ Stock Agent", description="Agent display name")
    nest_domain: str = Field(default="financial analysis", description="Agent domain of expertise")
    nest_specialization: str = Field(default="NASDAQ stock analysis and investment recommendations", description="Agent specialization")
    nest_description: str = Field(default="AI-powered agent that provides comprehensive stock analysis, technical and fundamental analysis, investment recommendations, and risk assessment for NASDAQ-listed stocks", description="Agent description")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()