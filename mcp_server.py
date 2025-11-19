#!/usr/bin/env python3
"""
Standalone MCP (Model Context Protocol) server entry point for NASDAQ Stock Agent
"""

import asyncio
import logging
import sys
import signal
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.mcp.mcp_server import mcp_server
from src.core.config_manager import config_manager
from src.core.dependencies import service_container

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class MCPServerRunner:
    """Standalone MCP server runner"""
    
    def __init__(self):
        self.server = mcp_server
        self.running = False
        self.shutdown_event = asyncio.Event()
    
    async def start(self):
        """Start the MCP server"""
        try:
            logger.info("Starting NASDAQ Stock Agent MCP Server...")
            
            # Load configuration
            config = config_manager.load_configuration()
            mcp_config = config_manager.get_mcp_config()
            
            if not mcp_config.enabled:
                logger.error("MCP server is disabled in configuration")
                return False
            
            # Initialize core services (without full web app)
            logger.info("Initializing core services...")
            await self._initialize_core_services()
            
            # Start MCP server
            logger.info(f"Starting MCP server on {mcp_config.host}:{mcp_config.port}")
            
            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Run MCP server with stdio transport
            self.running = True
            await self.server.run_stdio()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"MCP server failed: {e}")
            return False
        finally:
            await self.shutdown()
        
        return True
    
    async def _initialize_core_services(self):
        """Initialize only the core services needed for MCP"""
        try:
            # Initialize agent orchestrator
            from src.agents.stock_analysis_agent import agent_orchestrator
            health = await agent_orchestrator.get_health_status()
            logger.info(f"Agent orchestrator initialized: {health.get('overall_status')}")
            
            logger.info("Core services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize core services: {e}")
            raise
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def shutdown(self):
        """Shutdown the MCP server and cleanup"""
        if not self.running:
            return
        
        logger.info("Shutting down MCP server...")
        
        try:
            # Stop MCP server
            await self.server.stop_server()
            
            self.running = False
            logger.info("MCP server shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during MCP server shutdown: {e}")


async def main():
    """Main entry point for standalone MCP server"""
    runner = MCPServerRunner()
    
    try:
        success = await runner.start()
        if not success:
            sys.exit(1)
    except Exception as e:
        logger.error(f"MCP server startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
    except Exception as e:
        logger.error(f"MCP server failed: {e}")
        sys.exit(1)