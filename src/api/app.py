"""
FastAPI application factory and configuration
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from src.config.settings import settings
from src.api.routers import analysis, health, agent
from src.services.logging_middleware import RequestLoggingMiddleware, monitoring_service
from src.services.cache_service import global_cache
from src.api.middleware.validation import ValidationMiddleware
from src.api.error_handlers import setup_error_handlers

logger = logging.getLogger(__name__)

# Global NEST adapter instance
_nest_adapter: Optional['NESTAdapter'] = None


async def initialize_nest():
    """
    Initialize NEST integration if enabled.
    
    Returns:
        NESTAdapter instance if successful, None otherwise
    """
    global _nest_adapter
    
    try:
        # Import NEST components
        from src.nest import NESTConfig, NESTAdapter
        
        # Load NEST configuration
        nest_config = NESTConfig.from_env()
        
        # Check if NEST should be enabled
        if not nest_config.should_enable_nest():
            logger.info("NEST integration is disabled")
            return None
        
        # Validate configuration
        is_valid, errors = nest_config.validate()
        if not is_valid:
            logger.error(f"NEST configuration invalid: {', '.join(errors)}")
            logger.warning("Continuing in REST-only mode")
            return None
        
        # Create NEST adapter
        _nest_adapter = NESTAdapter(config=nest_config)
        
        # Start NEST adapter
        await _nest_adapter.start_async(register=True)
        
        logger.info(f"✅ NEST adapter started on port {nest_config.nest_port}")
        logger.info(f"🌐 A2A endpoint: {nest_config.nest_public_url}/a2a")
        return _nest_adapter
        
    except ImportError as e:
        logger.warning(f"NEST integration requires python-a2a library: {e}")
        logger.warning("Install with: pip install python-a2a")
        logger.info("Continuing in REST-only mode")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize NEST: {e}", exc_info=True)
        logger.warning("Continuing in REST-only mode")
        return None


async def shutdown_nest():
    """Shutdown NEST integration gracefully."""
    global _nest_adapter
    
    if _nest_adapter and _nest_adapter.is_running():
        try:
            logger.info("Shutting down NEST adapter...")
            await _nest_adapter.stop_async()
            _nest_adapter = None
            logger.info("✅ NEST adapter shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down NEST adapter: {e}", exc_info=True)


def get_nest_adapter():
    """
    Get the global NEST adapter instance.
    
    Returns:
        NESTAdapter instance or None if not initialized
    """
    return _nest_adapter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting NASDAQ Stock Agent...")
    
    try:
        # Ensure logs directory exists
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Logs directory ensured at: {logs_dir.absolute()}")
        
        # Start global in-memory cache background task
        try:
            await global_cache.start()
        except Exception as e:
            logger.warning(f"Failed to start global cache background task: {e}")
        
        # Initialize monitoring
        await monitoring_service.initialize_monitoring()
        
        # Initialize NEST integration
        try:
            await initialize_nest()
        except Exception as e:
            logger.error(f"NEST initialization failed: {e}", exc_info=True)
            logger.warning("Continuing in REST-only mode")
        
        logger.info("NASDAQ Stock Agent started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down NASDAQ Stock Agent...")
    
    try:
        # Shutdown NEST integration
        try:
            await shutdown_nest()
        except Exception as e:
            logger.warning(f"Failed to shutdown NEST cleanly: {e}")
        
        # Shutdown global cache
        try:
            await global_cache.shutdown()
        except Exception as e:
            logger.warning(f"Failed to shutdown global cache cleanly: {e}")
        
        logger.info("NASDAQ Stock Agent shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
        AI-powered NASDAQ stock analysis and investment recommendations using Langchain, 
        Anthropic Claude, and real-time market data.
        
        ## Features
        
        * **Natural Language Processing**: Query stocks using company names or natural language
        * **Real-time Market Data**: Current prices, volume, and 6-month historical data
        * **AI-Powered Analysis**: Investment recommendations with confidence scores
        * **Comprehensive Logging**: Full audit trails and performance monitoring
        * **Agent Registry**: Discoverable agent capabilities and information
        
        ## Example Queries
        
        * "What do you think about Apple stock?"
        * "Should I buy Tesla?"
        * "Analyze Microsoft"
        * "AAPL"
        
        ## Response Format
        
        All analysis responses include:
        * Investment recommendation (Buy/Hold/Sell)
        * Confidence score (0-100)
        * Current price and market data
        * Detailed reasoning and key factors
        * Risk assessment
        """,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add middleware
    app.add_middleware(ValidationMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    
    # Setup error handlers
    setup_error_handlers(app)
    
    # Include routers
    app.include_router(analysis.router)
    app.include_router(health.router)
    app.include_router(agent.router)
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for unhandled errors"""
        logger.error(f"Unhandled exception in {request.method} {request.url}: {exc}")
        
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "An internal server error occurred",
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path)
            }
        )
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information"""
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "description": "AI-powered NASDAQ stock analysis and investment recommendations",
            "documentation": "/docs",
            "health_check": "/health",
            "api_endpoints": {
                "analyze_stock": "/api/v1/analyze",
                "agent_info": "/api/v1/agent/info",
                "system_status": "/status"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return app