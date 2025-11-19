"""
Enhanced configuration management for NASDAQ Stock Agent
"""
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
from src.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """API configuration"""
    anthropic_api_key: str
    anthropic_model: str
    yfinance_timeout: int = 30


@dataclass
class CacheConfig:
    """Cache configuration"""
    ttl_seconds: int = 300
    cleanup_interval_minutes: int = 60
    max_entries: int = 10000


@dataclass
class LoggingConfig:
    """Logging configuration"""
    retention_days: int = 30
    cleanup_interval_hours: int = 24
    log_level: str = "INFO"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 100
    max_concurrent_requests: int = 50
    burst_limit: int = 20


@dataclass
class SecurityConfig:
    """Security configuration"""
    max_request_size_mb: int = 10
    enable_cors: bool = True
    allowed_origins: List[str] = None
    enable_rate_limiting: bool = True


@dataclass
class MCPConfig:
    """MCP (Model Context Protocol) server configuration"""
    enabled: bool = True
    host: str = "localhost"
    port: int = 8001
    max_connections: int = 100
    connection_timeout: int = 300  # 5 minutes
    tool_execution_timeout: int = 60  # 1 minute per tool call
    enable_logging: bool = True
    log_mcp_requests: bool = True


class ConfigurationManager:
    """Enhanced configuration management with validation and environment support"""
    
    def __init__(self):
        self.config_dir = Path(".kiro/config")
        self.config_file = self.config_dir / "app_config.json"
        self._config_cache = {}
        self._ensure_config_directory()
    
    def _ensure_config_directory(self):
        """Ensure configuration directory exists"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_configuration(self) -> Dict[str, Any]:
        """Load complete application configuration"""
        try:
            # Start with default configuration
            config = self._get_default_configuration()
            
            # Override with file configuration if exists
            if self.config_file.exists():
                file_config = self._load_config_file()
                config = self._merge_configurations(config, file_config)
            
            # Override with environment variables
            env_config = self._load_environment_configuration()
            config = self._merge_configurations(config, env_config)
            
            # Validate configuration
            self._validate_configuration(config)
            
            # Cache configuration
            self._config_cache = config
            
            logger.info("Configuration loaded successfully")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _get_default_configuration(self) -> Dict[str, Any]:
        """Get default configuration values"""
        return {
            "api": asdict(APIConfig(
                anthropic_api_key="",
                anthropic_model="claude-3-sonnet-20240229"
            )),
            "cache": asdict(CacheConfig()),
            "logging": asdict(LoggingConfig()),
            "rate_limiting": asdict(RateLimitConfig()),
            "security": asdict(SecurityConfig(
                allowed_origins=["*"]
            )),
            "mcp": asdict(MCPConfig()),
            "application": {
                "name": "NASDAQ Stock Agent",
                "version": "1.0.0",
                "debug": False,
                "host": "0.0.0.0",
                "port": 8000
            }
        }
    
    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            logger.info(f"Loaded configuration from {self.config_file}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config file {self.config_file}: {e}")
            return {}
    
    def _load_environment_configuration(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_config = {
            "database": {},
            "api": {},
            "cache": {},
            "logging": {},
            "rate_limiting": {},
            "security": {},
            "mcp": {},
            "application": {}
        }
        
        # API configuration
        if settings.anthropic_api_key:
            env_config["api"]["anthropic_api_key"] = settings.anthropic_api_key
        if settings.anthropic_model:
            env_config["api"]["anthropic_model"] = settings.anthropic_model
        if settings.yfinance_timeout:
            env_config["api"]["yfinance_timeout"] = settings.yfinance_timeout
        
        # Cache configuration
        if settings.cache_ttl_seconds:
            env_config["cache"]["ttl_seconds"] = settings.cache_ttl_seconds
        
        # Logging configuration
        if settings.log_retention_days:
            env_config["logging"]["retention_days"] = settings.log_retention_days
        
        # Rate limiting configuration
        if settings.rate_limit_requests:
            env_config["rate_limiting"]["requests_per_minute"] = settings.rate_limit_requests
        if settings.max_concurrent_requests:
            env_config["rate_limiting"]["max_concurrent_requests"] = settings.max_concurrent_requests
        
        # MCP configuration
        mcp_enabled = os.getenv("MCP_ENABLED", "true").lower() == "true"
        env_config["mcp"]["enabled"] = mcp_enabled
        
        mcp_host = os.getenv("MCP_HOST")
        if mcp_host:
            env_config["mcp"]["host"] = mcp_host
        
        mcp_port = os.getenv("MCP_PORT")
        if mcp_port:
            try:
                env_config["mcp"]["port"] = int(mcp_port)
            except ValueError:
                logger.warning(f"Invalid MCP_PORT value: {mcp_port}")
        
        # Application configuration
        if settings.app_name:
            env_config["application"]["name"] = settings.app_name
        if settings.app_version:
            env_config["application"]["version"] = settings.app_version
        if settings.debug is not None:
            env_config["application"]["debug"] = settings.debug
        if settings.host:
            env_config["application"]["host"] = settings.host
        if settings.port:
            env_config["application"]["port"] = settings.port
        
        return env_config
    
    def _merge_configurations(self, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configuration dictionaries"""
        merged = base_config.copy()
        
        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configurations(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _validate_configuration(self, config: Dict[str, Any]):
        """Validate configuration values"""
        errors = []
        
        # Validate required API keys
        api_config = config.get("api", {})
        if not api_config.get("anthropic_api_key"):
            errors.append("Anthropic API key is required")
        
        # Validate numeric values
        cache_config = config.get("cache", {})
        if cache_config.get("ttl_seconds", 0) <= 0:
            errors.append("Cache TTL must be positive")
        
        rate_limit_config = config.get("rate_limiting", {})
        if rate_limit_config.get("requests_per_minute", 0) <= 0:
            errors.append("Rate limit requests per minute must be positive")
        
        # Validate application configuration
        app_config = config.get("application", {})
        port = app_config.get("port", 8000)
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append("Port must be a valid integer between 1 and 65535")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def save_configuration(self, config: Dict[str, Any]):
        """Save configuration to file"""
        try:
            self._validate_configuration(config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self._config_cache = config
            logger.info(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def get_config_section(self, section: str) -> Dict[str, Any]:
        """Get a specific configuration section"""
        if not self._config_cache:
            self.load_configuration()
        
        return self._config_cache.get(section, {})
    
    def get_config_value(self, section: str, key: str, default: Any = None) -> Any:
        """Get a specific configuration value"""
        section_config = self.get_config_section(section)
        return section_config.get(key, default)
    
    def update_config_value(self, section: str, key: str, value: Any):
        """Update a specific configuration value"""
        if not self._config_cache:
            self.load_configuration()
        
        if section not in self._config_cache:
            self._config_cache[section] = {}
        
        self._config_cache[section][key] = value
        
        # Save updated configuration
        self.save_configuration(self._config_cache)
    
    def get_api_config(self) -> APIConfig:
        """Get API configuration as dataclass"""
        api_config = self.get_config_section("api")
        return APIConfig(**api_config)
    
    def get_cache_config(self) -> CacheConfig:
        """Get cache configuration as dataclass"""
        cache_config = self.get_config_section("cache")
        return CacheConfig(**cache_config)
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration as dataclass"""
        logging_config = self.get_config_section("logging")
        return LoggingConfig(**logging_config)
    
    def get_rate_limit_config(self) -> RateLimitConfig:
        """Get rate limiting configuration as dataclass"""
        rate_limit_config = self.get_config_section("rate_limiting")
        return RateLimitConfig(**rate_limit_config)
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration as dataclass"""
        security_config = self.get_config_section("security")
        return SecurityConfig(**security_config)
    
    def get_mcp_config(self) -> MCPConfig:
        """Get MCP configuration as dataclass"""
        mcp_config = self.get_config_section("mcp")
        return MCPConfig(**mcp_config)
    
    def export_configuration(self, file_path: Optional[str] = None) -> str:
        """Export current configuration to file"""
        if not self._config_cache:
            self.load_configuration()
        
        if not file_path:
            file_path = f"nasdaq_agent_config_{int(os.time())}.json"
        
        try:
            with open(file_path, 'w') as f:
                json.dump(self._config_cache, f, indent=2)
            
            logger.info(f"Configuration exported to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            raise
    
    def import_configuration(self, file_path: str):
        """Import configuration from file"""
        try:
            with open(file_path, 'r') as f:
                imported_config = json.load(f)
            
            # Validate imported configuration
            self._validate_configuration(imported_config)
            
            # Save imported configuration
            self.save_configuration(imported_config)
            
            logger.info(f"Configuration imported from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to import configuration from {file_path}: {e}")
            raise
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get configuration summary for monitoring"""
        if not self._config_cache:
            self.load_configuration()
        
        summary = {
            "config_file_exists": self.config_file.exists(),
            "config_file_path": str(self.config_file),
            "sections": list(self._config_cache.keys()),
            "api_keys_configured": bool(self.get_config_value("api", "anthropic_api_key")),
            "cache_enabled": self.get_config_value("cache", "ttl_seconds", 0) > 0,
            "rate_limiting_enabled": self.get_config_value("rate_limiting", "requests_per_minute", 0) > 0,
            "debug_mode": self.get_config_value("application", "debug", False)
        }
        
        return summary


# Global configuration manager instance
config_manager = ConfigurationManager()