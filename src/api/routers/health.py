"""
Health check and system status API router
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from datetime import datetime
from src.services.logging_middleware import monitoring_service, performance_monitor
from src.agents.stock_analysis_agent import agent_orchestrator
from src.services.market_data_service import market_data_service
from src.services.investment_analysis import comprehensive_analysis_service
from src.core.dependencies import get_mcp_server

logger = logging.getLogger(__name__)


async def get_nest_status() -> Dict[str, Any]:
    """
    Get NEST adapter status.
    
    Returns:
        Dict with NEST status information
    """
    try:
        from src.api.app import get_nest_adapter
        
        nest_adapter = get_nest_adapter()
        
        if nest_adapter is None:
            return {
                "nest_enabled": False,
                "nest_status": "disabled",
                "message": "NEST integration is not enabled"
            }
        
        # Get adapter status
        adapter_status = await nest_adapter.get_status()
        
        # Determine nest_status based on running state
        if adapter_status.get("nest_running"):
            nest_status = "healthy"
        else:
            nest_status = "unhealthy"
        
        # Determine registry_status
        if adapter_status.get("registered"):
            registry_status = "registered"
        elif adapter_status.get("registry_url"):
            registry_status = "unreachable"
        else:
            registry_status = "not_configured"
        
        return {
            "nest_enabled": True,
            "nest_status": nest_status,
            "nest_running": adapter_status.get("nest_running"),
            "nest_port": adapter_status.get("nest_port"),
            "agent_id": adapter_status.get("agent_id"),
            "registry_status": registry_status,
            "registered": adapter_status.get("registered"),
            "registry_url": adapter_status.get("registry_url"),
            "public_url": adapter_status.get("public_url"),
            "a2a_endpoint": f"{adapter_status.get('public_url')}/a2a" if adapter_status.get("public_url") else None
        }
        
    except ImportError:
        return {
            "nest_enabled": False,
            "nest_status": "disabled",
            "message": "NEST integration not available (python-a2a not installed)"
        }
    except Exception as e:
        logger.error(f"Error getting NEST status: {e}")
        return {
            "nest_enabled": False,
            "nest_status": "error",
            "error": str(e)
        }

router = APIRouter(tags=["Health & Status"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint
    
    Returns simple health status for load balancers and monitoring systems.
    Includes NEST integration status.
    """
    try:
        # Get NEST status
        nest_status = await get_nest_status()
        
        return {
            "status": "healthy",
            "service": "NASDAQ Stock Agent",
            "version": "1.0.0",
            "nest": nest_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with service status
    
    Returns comprehensive health information for all system components including NEST.
    """
    try:
        # Get comprehensive system status
        system_status = await monitoring_service.get_comprehensive_status()
        
        # Get NEST status
        nest_status = await get_nest_status()
        
        return {
            "overall_status": system_status.get("status", "unknown"),
            "system_health": system_status,
            "nest": nest_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/status")
async def system_status() -> Dict[str, Any]:
    """
    Get comprehensive system status and metrics
    
    Returns detailed information about system performance, health, and metrics including NEST.
    """
    try:
        # Get performance metrics
        performance_metrics = await performance_monitor.get_metrics()
        
        # Get agent health
        agent_health = await agent_orchestrator.get_health_status()
        
        # Get market data service health
        market_health = await market_data_service.get_service_health()
        
        # Get analysis service health
        analysis_health = await comprehensive_analysis_service.get_service_health()
        
        # Get MCP server health
        try:
            mcp_server = await get_mcp_server()
            mcp_health = mcp_server.get_health_status() if mcp_server else {"status": "not_available"}
        except Exception:
            mcp_health = {"status": "error", "message": "Failed to get MCP server status"}
        
        # Get NEST status
        nest_status = await get_nest_status()
        
        return {
            "service": "NASDAQ Stock Agent",
            "version": "1.0.0",
            "status": "operational",
            "performance_metrics": performance_metrics,
            "service_health": {
                "agent_orchestrator": agent_health,
                "market_data_service": market_health,
                "analysis_service": analysis_health,
                "mcp_server": mcp_health,
                "nest_adapter": nest_status
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Status check failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Get system performance metrics
    
    Returns real-time performance metrics including request counts, response times,
    error rates, and cache statistics.
    """
    try:
        metrics = await performance_monitor.get_metrics()
        
        return {
            "success": True,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Metrics retrieval failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/metrics/reset")
async def reset_metrics() -> Dict[str, Any]:
    """
    Reset performance metrics
    
    Resets all performance counters and metrics to zero. Useful for testing
    or starting fresh metric collection periods.
    """
    try:
        await performance_monitor.reset_metrics()
        
        return {
            "success": True,
            "message": "Performance metrics have been reset",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Metrics reset failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/mcp")
async def mcp_server_status() -> Dict[str, Any]:
    """
    Get MCP (Model Context Protocol) server status
    
    Returns detailed information about the MCP server including available tools,
    connection status, and performance metrics.
    """
    try:
        mcp_server = await get_mcp_server()
        
        if not mcp_server:
            return {
                "status": "not_available",
                "message": "MCP server not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Get comprehensive MCP server status
        server_status = mcp_server.get_server_status()
        health_status = mcp_server.get_health_status()
        
        # Validate tool schemas
        tool_validation = await mcp_server.validate_tool_schemas()
        
        return {
            "success": True,
            "server_status": server_status,
            "health_status": health_status,
            "tool_validation": tool_validation,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get MCP server status: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"MCP server status check failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
