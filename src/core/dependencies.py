"""
Dependency injection and service wiring for NASDAQ Stock Agent
"""
import asyncio
from typing import Dict, Any, Optional
import logging
from contextlib import asynccontextmanager
from src.config.settings import settings
from src.services.market_data_service import market_data_service
from src.services import enhanced_nlp_service
from src.services.investment_analysis import comprehensive_analysis_service
from src.agents.stock_analysis_agent import agent_orchestrator
from src.services.logging_service import logging_service
from src.services.logging_middleware import monitoring_service
from src.services.cache_service import global_cache
from src.mcp.mcp_server import mcp_server
from src.core.config_manager import config_manager

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Dependency injection container for all services"""
    
    def __init__(self):
        self._services = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize all services and their dependencies"""
        if self._initialized:
            logger.warning("Services already initialized")
            return
        
        try:
            logger.info("Initializing NASDAQ Stock Agent services...")
            
            # Initialize database connection
            await self._initialize_database()
            
            # Initialize monitoring
            await self._initialize_monitoring()
            
            # Initialize cache
            await self._initialize_cache()
            
            # Initialize market data service
            await self._initialize_market_data_service()
            
            # Initialize NLP service
            await self._initialize_nlp_service()
            
            # Initialize analysis service
            await self._initialize_analysis_service()
            
            # Initialize agent orchestrator
            await self._initialize_agent_orchestrator()
            
            # Initialize logging service
            await self._initialize_logging_service()
            
            # Initialize MCP server
            await self._initialize_mcp_server()
            
            # Register services
            self._register_services()
            
            # Verify all services are healthy
            await self._verify_service_health()
            
            self._initialized = True
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            await self.shutdown()
            raise
    
    async def _initialize_database(self):
        """Initialize database connection and schema"""
        logger.info("Initializing database connection...")
        
        try:
            # Connect to MongoDB
            await mongodb_client.connect()
            
            # Verify database health
            health = await mongodb_client.health_check()
            if health.get('status') != 'healthy':
                raise Exception(f"Database health check failed: {health}")
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def _initialize_monitoring(self):
        """Initialize monitoring and metrics collection"""
        logger.info("Initializing monitoring service...")
        
        try:
            await monitoring_service.initialize_monitoring()
            logger.info("Monitoring service initialized successfully")
            
        except Exception as e:
            logger.error(f"Monitoring initialization failed: {e}")
            raise
    
    async def _initialize_cache(self):
        """Initialize caching service"""
        logger.info("Initializing cache service...")
        
        try:
            # Cache is already initialized as a global instance
            # Just verify it's working
            await global_cache.set("test_key", "test_value", 1)
            test_value = await global_cache.get("test_key")
            
            if test_value != "test_value":
                raise Exception("Cache test failed")
            
            await global_cache.delete("test_key")
            logger.info("Cache service initialized successfully")
            
        except Exception as e:
            logger.error(f"Cache initialization failed: {e}")
            raise
    
    async def _initialize_market_data_service(self):
        """Initialize market data service"""
        logger.info("Initializing market data service...")
        
        try:
            # Test market data service health
            health = await market_data_service.get_service_health()
            
            if health.get('overall_status') not in ['healthy', 'degraded']:
                logger.warning(f"Market data service health: {health.get('overall_status')}")
            
            logger.info("Market data service initialized successfully")
            
        except Exception as e:
            logger.error(f"Market data service initialization failed: {e}")
            raise
    
    async def _initialize_nlp_service(self):
        """Initialize NLP service"""
        logger.info("Initializing NLP service...")
        
        try:
            # Test NLP service with a simple query
            test_result = await enhanced_nlp_service.process_query_with_suggestions("Apple")
            
            if not test_result.get('success'):
                logger.warning(f"NLP service test query failed: {test_result}")
            
            logger.info("NLP service initialized successfully")
            
        except Exception as e:
            logger.error(f"NLP service initialization failed: {e}")
            raise
    
    async def _initialize_analysis_service(self):
        """Initialize comprehensive analysis service"""
        logger.info("Initializing analysis service...")
        
        try:
            # Test analysis service health
            health = await comprehensive_analysis_service.get_service_health()
            
            if health.get('overall_status') not in ['healthy', 'degraded']:
                logger.warning(f"Analysis service health: {health.get('overall_status')}")
            
            logger.info("Analysis service initialized successfully")
            
        except Exception as e:
            logger.error(f"Analysis service initialization failed: {e}")
            raise
    
    async def _initialize_agent_orchestrator(self):
        """Initialize Langchain agent orchestrator"""
        logger.info("Initializing agent orchestrator...")
        
        try:
            # Test agent health
            health = await agent_orchestrator.get_health_status()
            
            if health.get('overall_status') not in ['healthy', 'degraded']:
                logger.warning(f"Agent orchestrator health: {health.get('overall_status')}")
            
            logger.info("Agent orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Agent orchestrator initialization failed: {e}")
            raise
    
    async def _initialize_logging_service(self):
        """Initialize logging service"""
        logger.info("Initializing logging service...")
        
        try:
            # Initialize logging service (starts background tasks)
            await logging_service.initialize()
            
            # Test logging service
            stats = await logging_service.get_logging_statistics()
            
            if stats.get('database_health', {}).get('status') != 'healthy':
                logger.warning(f"Logging service database health issue: {stats}")
            
            logger.info("Logging service initialized successfully")
            
        except Exception as e:
            logger.error(f"Logging service initialization failed: {e}")
            raise
    
    async def _initialize_mcp_server(self):
        """Initialize MCP server"""
        logger.info("Initializing MCP server...")
        
        try:
            # Get MCP configuration
            mcp_config = config_manager.get_mcp_config()
            
            if not mcp_config.enabled:
                logger.info("MCP server disabled in configuration")
                return
            
            # Start MCP server
            success = await mcp_server.start_server(mcp_config.host, mcp_config.port)
            
            if success:
                logger.info(f"MCP server initialized successfully on {mcp_config.host}:{mcp_config.port}")
            else:
                logger.warning("MCP server failed to start, but continuing without it")
            
        except Exception as e:
            logger.error(f"MCP server initialization failed: {e}")
            # Don't raise - MCP server failure shouldn't prevent app startup
            logger.warning("Continuing without MCP server")
    
    def _register_services(self):
        """Register all services in the container"""
        self._services = {
            'market_data': market_data_service,
            'nlp': enhanced_nlp_service,
            'analysis': comprehensive_analysis_service,
            'agent': agent_orchestrator,
            'logging': logging_service,
            'monitoring': monitoring_service,
            'cache': global_cache,
            'mcp_server': mcp_server
        }
        
        logger.info(f"Registered {len(self._services)} services")
    
    async def _verify_service_health(self):
        """Verify all services are healthy"""
        logger.info("Verifying service health...")
        
        health_checks = []
        
        try:
            # Check database health
            db_health = await mongodb_client.health_check()
            health_checks.append(('database', db_health.get('status')))
            
            # Check market data service health
            market_health = await market_data_service.get_service_health()
            health_checks.append(('market_data', market_health.get('overall_status')))
            
            # Check analysis service health
            analysis_health = await comprehensive_analysis_service.get_service_health()
            health_checks.append(('analysis', analysis_health.get('overall_status')))
            
            # Check agent health
            agent_health = await agent_orchestrator.get_health_status()
            health_checks.append(('agent', agent_health.get('overall_status')))
            
            # Check logging service health
            logging_stats = await logging_service.get_logging_statistics()
            logging_health = logging_stats.get('database_health', {}).get('status')
            health_checks.append(('logging', logging_health))
            
            # Check MCP server health
            mcp_health = mcp_server.get_health_status()
            health_checks.append(('mcp_server', mcp_health.get('status')))
            
            # Report health status
            healthy_services = sum(1 for _, status in health_checks if status == 'healthy')
            total_services = len(health_checks)
            
            logger.info(f"Service health check: {healthy_services}/{total_services} services healthy")
            
            for service_name, status in health_checks:
                if status != 'healthy':
                    logger.warning(f"Service '{service_name}' status: {status}")
            
            if healthy_services < total_services:
                logger.warning("Some services are not fully healthy, but continuing startup")
            
        except Exception as e:
            logger.error(f"Service health verification failed: {e}")
            raise
    
    def get_service(self, service_name: str):
        """Get a service by name"""
        if not self._initialized:
            raise RuntimeError("Services not initialized")
        
        return self._services.get(service_name)
    
    def get_all_services(self) -> Dict[str, Any]:
        """Get all registered services"""
        if not self._initialized:
            raise RuntimeError("Services not initialized")
        
        return self._services.copy()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        if not self._initialized:
            return {
                'status': 'not_initialized',
                'message': 'Services not initialized'
            }
        
        try:
            # Get comprehensive status from monitoring service
            system_status = await monitoring_service.get_comprehensive_status()
            
            # Add service container information
            system_status['service_container'] = {
                'initialized': self._initialized,
                'registered_services': list(self._services.keys()),
                'service_count': len(self._services)
            }
            
            return system_status
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'service_container': {
                    'initialized': self._initialized,
                    'registered_services': list(self._services.keys()) if self._services else [],
                    'service_count': len(self._services) if self._services else 0
                }
            }
    
    async def shutdown(self):
        """Shutdown all services gracefully"""
        logger.info("Shutting down services...")
        
        try:
            # Shutdown MCP server
            if mcp_server:
                await mcp_server.stop_server()
            
            # Shutdown logging service
            if logging_service:
                logging_service.shutdown()
            
            # Shutdown cache
            if global_cache:
                global_cache.shutdown()
            
            # Disconnect from database
            if mongodb_client:
                await mongodb_client.disconnect()
            
            self._initialized = False
            self._services.clear()
            
            logger.info("All services shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during service shutdown: {e}")


# Global service container instance
service_container = ServiceContainer()


# Dependency injection functions for FastAPI
async def get_service_container() -> ServiceContainer:
    """FastAPI dependency for service container"""
    return service_container


async def get_market_data_service():
    """FastAPI dependency for market data service"""
    return service_container.get_service('market_data')


async def get_nlp_service():
    """FastAPI dependency for NLP service"""
    return service_container.get_service('nlp')


async def get_analysis_service():
    """FastAPI dependency for analysis service"""
    return service_container.get_service('analysis')


async def get_agent_orchestrator():
    """FastAPI dependency for agent orchestrator"""
    return service_container.get_service('agent')


async def get_logging_service():
    """FastAPI dependency for logging service"""
    return service_container.get_service('logging')


async def get_monitoring_service():
    """FastAPI dependency for monitoring service"""
    return service_container.get_service('monitoring')


async def get_mcp_server():
    """FastAPI dependency for MCP server"""
    return service_container.get_service('mcp_server')


# Application lifecycle management
@asynccontextmanager
async def application_lifespan():
    """Application lifespan context manager"""
    try:
        # Startup
        logger.info("Starting NASDAQ Stock Agent application...")
        await service_container.initialize()
        
        yield service_container
        
    finally:
        # Shutdown
        logger.info("Shutting down NASDAQ Stock Agent application...")
        await service_container.shutdown()