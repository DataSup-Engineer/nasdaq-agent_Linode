"""
NEST Configuration Management

Handles loading and validation of NEST-specific configuration from environment variables.
"""
import os
import logging
from typing import Tuple, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NESTConfig:
    """Configuration for NEST integration"""
    
    # Core settings
    nest_enabled: bool
    nest_port: int
    nest_registry_url: Optional[str]
    nest_public_url: Optional[str]
    
    # Agent identity
    agent_id: str
    agent_name: str
    domain: str
    specialization: str
    description: str
    capabilities: List[str]
    
    # Optional settings
    host: str = "0.0.0.0"
    enable_telemetry: bool = False
    
    @classmethod
    def from_env(cls) -> "NESTConfig":
        """
        Load NEST configuration from environment variables.
        
        Returns:
            NESTConfig: Configuration object
        """
        # Parse capabilities from comma-separated string
        capabilities_str = os.getenv(
            "NEST_CAPABILITIES",
            "stock analysis,ticker resolution,investment recommendations,market data,technical analysis,fundamental analysis"
        )
        capabilities = [cap.strip() for cap in capabilities_str.split(",")]
        
        config = cls(
            # Core settings
            nest_enabled=os.getenv("NEST_ENABLED", "false").lower() == "true",
            nest_port=int(os.getenv("NEST_PORT", "6000")),
            nest_registry_url=os.getenv("NEST_REGISTRY_URL"),
            nest_public_url=os.getenv("NEST_PUBLIC_URL"),
            
            # Agent identity
            agent_id=os.getenv("NEST_AGENT_ID", "nasdaq-stock-agent"),
            agent_name=os.getenv("NEST_AGENT_NAME", "NASDAQ Stock Agent"),
            domain=os.getenv("NEST_DOMAIN", "financial analysis"),
            specialization=os.getenv(
                "NEST_SPECIALIZATION",
                "NASDAQ stock analysis and investment recommendations"
            ),
            description=os.getenv(
                "NEST_DESCRIPTION",
                "AI-powered agent that provides comprehensive stock analysis and investment "
                "recommendations for NASDAQ-listed securities using real-time market data and "
                "advanced AI analysis."
            ),
            capabilities=capabilities,
            
            # Optional settings
            host=os.getenv("NEST_HOST", "0.0.0.0"),
            enable_telemetry=os.getenv("NEST_TELEMETRY", "false").lower() == "true"
        )
        
        logger.info(f"NEST configuration loaded: enabled={config.nest_enabled}, port={config.nest_port}")
        return config
    
    def should_enable_nest(self) -> bool:
        """
        Determine if NEST should be enabled based on configuration.
        
        Returns:
            bool: True if NEST should be enabled
        """
        if not self.nest_enabled:
            logger.info("NEST is disabled via NEST_ENABLED=false")
            return False
        
        # Check for required dependencies
        try:
            import python_a2a
        except ImportError:
            logger.warning("python-a2a library not installed. NEST will be disabled.")
            logger.warning("Install with: pip install python-a2a")
            return False
        
        return True
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the configuration.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, list of error messages)
        """
        errors = []
        
        # Check required fields when NEST is enabled
        if self.nest_enabled:
            if not self.nest_registry_url:
                errors.append("NEST_REGISTRY_URL is required when NEST is enabled")
            
            if not self.nest_public_url:
                errors.append("NEST_PUBLIC_URL is required when NEST is enabled")
            
            if not self.agent_id:
                errors.append("NEST_AGENT_ID is required")
            
            if self.nest_port < 1 or self.nest_port > 65535:
                errors.append(f"NEST_PORT must be between 1 and 65535, got {self.nest_port}")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.error(f"NEST configuration validation failed: {', '.join(errors)}")
        else:
            logger.info("NEST configuration validation passed")
        
        return is_valid, errors
    
    def get_agent_facts(self) -> dict:
        """
        Get agent facts/metadata for registration and discovery.
        
        Returns:
            dict: Agent metadata
        """
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_domain": self.domain,
            "agent_specialization": self.specialization,
            "agent_description": self.description,
            "agent_capabilities": self.capabilities,
            "supported_operations": [
                {
                    "operation": "stock_analysis",
                    "description": "Analyze a stock and provide investment recommendation",
                    "examples": ["AAPL", "What about Tesla stock?", "Should I buy Microsoft?"]
                },
                {
                    "operation": "ticker_resolution",
                    "description": "Resolve company name to ticker symbol",
                    "examples": ["Apple", "Microsoft Corporation", "Tesla Inc"]
                },
                {
                    "operation": "investment_recommendation",
                    "description": "Get Buy/Hold/Sell recommendation with confidence score",
                    "examples": ["Recommend AAPL", "Investment advice for TSLA"]
                }
            ]
        }
