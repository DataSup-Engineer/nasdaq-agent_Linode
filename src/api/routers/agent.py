"""
Agent information and registry API router
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["Agent Registry"])


@router.get("/info")
async def get_agent_info() -> Dict[str, Any]:
    """
    Get NASDAQ Stock Agent information
    
    Returns comprehensive information about the agent including capabilities,
    specialization, registry details, and NEST integration status.
    """
    try:
        # Get NEST status
        nest_enabled = False
        a2a_endpoint = None
        nest_agent_id = None
        
        try:
            from src.api.app import get_nest_adapter
            
            nest_adapter = get_nest_adapter()
            if nest_adapter:
                nest_status = await nest_adapter.get_status()
                nest_enabled = nest_status.get("nest_running", False)
                nest_agent_id = nest_status.get("agent_id")
                public_url = nest_status.get("public_url")
                if public_url:
                    a2a_endpoint = f"{public_url}/a2a"
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to get NEST status: {e}")
        
        # Build agent info response
        agent_info = {
            "agent_id": nest_agent_id if nest_agent_id else "nasdaq-stock-agent",
            "agent_name": "NASDAQ Stock Agent",
            "agent_domain": "financial analysis",
            "agent_specialization": "NASDAQ stock analysis and investment recommendations",
            "agent_description": "AI-powered agent that provides comprehensive stock analysis and investment recommendations for NASDAQ-listed securities using real-time market data and advanced AI analysis.",
            "agent_capabilities": [
                "stock analysis",
                "ticker resolution",
                "investment recommendations",
                "market data",
                "technical analysis",
                "fundamental analysis"
            ],
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
            ],
            "rest_endpoint": "http://localhost:8000/api/v1",
            "status": "active",
            "nest_enabled": nest_enabled,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add A2A endpoint if NEST is enabled
        if a2a_endpoint:
            agent_info["a2a_endpoint"] = a2a_endpoint
        
        return agent_info
        
    except Exception as e:
        logger.error(f"Failed to get agent info: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "AGENT_INFO_FAILED",
                "error_message": f"Failed to retrieve agent information: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/capabilities")
async def get_agent_capabilities() -> Dict[str, Any]:
    """
    Get detailed agent capabilities and supported operations
    
    Returns information about what the agent can do, supported query types,
    and operational parameters.
    """
    try:
        capabilities = {
            "natural_language_processing": {
                "supported_queries": [
                    "Company name queries (e.g., 'Apple', 'Microsoft')",
                    "Ticker symbol queries (e.g., 'AAPL', 'MSFT')",
                    "Investment questions (e.g., 'Should I buy Tesla?')",
                    "Analysis requests (e.g., 'Analyze Netflix stock')",
                    "Price inquiries (e.g., 'What's Apple's stock price?')"
                ],
                "supported_companies": "50+ major NASDAQ-listed companies",
                "fuzzy_matching": True,
                "typo_correction": True
            },
            "market_data_analysis": {
                "data_sources": ["Yahoo Finance API"],
                "historical_data_range": "6 months",
                "update_frequency": "Real-time",
                "supported_metrics": [
                    "Current price and daily range",
                    "Trading volume",
                    "Market capitalization",
                    "P/E ratio",
                    "Price change percentage",
                    "Moving averages (20, 50, 200-day)",
                    "RSI (Relative Strength Index)",
                    "Volatility analysis"
                ]
            },
            "ai_analysis": {
                "ai_model": "Anthropic Claude",
                "recommendation_types": ["Buy", "Hold", "Sell"],
                "confidence_scoring": "0-100 scale",
                "analysis_factors": [
                    "Technical indicators",
                    "Price trends and momentum",
                    "Volume analysis",
                    "Fundamental metrics",
                    "Risk assessment"
                ]
            },
            "api_features": {
                "response_format": "JSON",
                "max_concurrent_requests": 50,
                "average_response_time": "< 10 seconds",
                "caching": "Intelligent caching with TTL",
                "rate_limiting": "100 requests per minute",
                "logging": "Comprehensive audit trails"
            },
            "supported_exchanges": ["NASDAQ"],
            "data_retention": "30 days",
            "availability": "24/7"
        }
        
        return {
            "success": True,
            "agent_capabilities": capabilities,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get agent capabilities: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "CAPABILITIES_FAILED",
                "error_message": f"Failed to retrieve capabilities: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/registry")
async def get_registry_info() -> Dict[str, Any]:
    """
    Get agent registry information
    
    Returns information about the agent registry, including storage location
    and registration details.
    """
    try:
        registry_info = {
            "registry_type": "MongoDB",
            "registry_url": "mongodb://localhost:27017/nasdaq_stock_agent/agent_registry",
            "agent_id": "nasdaq-stock-agent-v1",
            "registration_status": "active",
            "last_updated": datetime.utcnow().isoformat(),
            "registry_schema": {
                "agent_id": "Unique identifier for the agent",
                "agent_name": "Human-readable name",
                "agent_domain": "Domain of expertise",
                "agent_specialization": "Specific area of specialization",
                "agent_description": "Detailed description of capabilities",
                "agent_capabilities": "List of specific capabilities",
                "registry_url": "URL of the registry storage",
                "public_url": "Public API endpoint URL"
            }
        }
        
        return {
            "success": True,
            "registry_info": registry_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get registry info: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "REGISTRY_INFO_FAILED",
                "error_message": f"Failed to retrieve registry information: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/examples")
async def get_usage_examples() -> Dict[str, Any]:
    """
    Get usage examples and sample queries
    
    Returns example queries and expected responses to help users understand
    how to interact with the agent.
    """
    try:
        examples = {
            "basic_queries": [
                {
                    "query": "Apple",
                    "description": "Simple company name query",
                    "expected_response": "Investment analysis for Apple Inc. (AAPL)"
                },
                {
                    "query": "MSFT",
                    "description": "Direct ticker symbol query", 
                    "expected_response": "Investment analysis for Microsoft Corporation (MSFT)"
                }
            ],
            "natural_language_queries": [
                {
                    "query": "What do you think about Tesla stock?",
                    "description": "Opinion-based investment question",
                    "expected_response": "Comprehensive analysis with Buy/Hold/Sell recommendation"
                },
                {
                    "query": "Should I buy Netflix?",
                    "description": "Direct investment advice question",
                    "expected_response": "Investment recommendation with confidence score and reasoning"
                },
                {
                    "query": "Analyze Amazon stock performance",
                    "description": "Analysis request",
                    "expected_response": "Detailed technical and fundamental analysis"
                }
            ],
            "response_format": {
                "analysis_id": "Unique identifier for the analysis",
                "ticker": "Stock ticker symbol",
                "company_name": "Full company name",
                "current_price": "Current stock price",
                "recommendation": "Buy/Hold/Sell recommendation",
                "confidence_score": "Confidence level (0-100)",
                "reasoning": "Detailed analysis reasoning",
                "key_factors": "List of key factors influencing the recommendation",
                "risk_assessment": "Risk evaluation",
                "processing_time_ms": "Analysis processing time"
            },
            "error_handling": {
                "invalid_company": {
                    "query": "XYZ Company",
                    "response": "Error with suggestions for valid companies"
                },
                "misspelled_name": {
                    "query": "Aple",
                    "response": "Automatic correction to 'Apple' with analysis"
                }
            }
        }
        
        return {
            "success": True,
            "usage_examples": examples,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get usage examples: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "EXAMPLES_FAILED",
                "error_message": f"Failed to retrieve usage examples: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )