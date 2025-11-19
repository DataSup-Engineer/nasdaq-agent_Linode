"""
NASDAQ Stock Agent - Main Application Entry Point
"""
import logging
import uvicorn
from src.api.app import create_app
from src.core.config_manager import config_manager
from src.core.dependencies import service_container

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main application entry point"""
    try:
        # Load configuration
        config = config_manager.load_configuration()
        app_config = config.get("application", {})
        
        # Create FastAPI application
        app = create_app()
        
        logger.info(f"Starting {app_config.get('name', 'NASDAQ Stock Agent')} v{app_config.get('version', '1.0.0')}")
        
        return app
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise


async def startup_check():
    """Perform startup health check"""
    try:
        logger.info("Performing startup health check...")
        
        # Initialize services
        await service_container.initialize()
        
        # Get system status
        status = await service_container.get_system_status()
        
        if status.get('status') in ['healthy', 'degraded']:
            logger.info("Startup health check passed")
            return True
        else:
            logger.error(f"Startup health check failed: {status}")
            return False
            
    except Exception as e:
        logger.error(f"Startup health check error: {e}")
        return False


if __name__ == "__main__":
    try:
        # Load configuration
        config = config_manager.load_configuration()
        app_config = config.get("application", {})
        
        # Get server configuration
        host = app_config.get("host", "0.0.0.0")
        port = app_config.get("port", 8000)
        debug = app_config.get("debug", False)
        
        logger.info(f"Starting server on {host}:{port} (debug={debug})")
        
        # Run server
        uvicorn.run(
            "main:main",
            host=host,
            port=port,
            reload=debug,
            factory=True,
            log_level="info" if not debug else "debug"
        )
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        exit(1)