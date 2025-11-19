"""
Stock analysis API router for NASDAQ Stock Agent
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from src.models.analysis import AnalysisRequest, AnalysisResponse, ErrorResponse
from src.agents.stock_analysis_agent import agent_orchestrator
from src.services.logging_service import logging_service
from src.services.logging_middleware import performance_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Stock Analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_stock(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
) -> AnalysisResponse:
    """
    Analyze a stock using natural language query
    
    This endpoint accepts natural language queries about NASDAQ stocks and returns
    comprehensive investment analysis including recommendations, confidence scores,
    and detailed reasoning.
    
    **Example queries:**
    - "What do you think about Apple stock?"
    - "Should I buy Tesla?"
    - "Analyze Microsoft"
    - "AAPL"
    
    **Returns:**
    - Investment recommendation (Buy/Hold/Sell)
    - Confidence score (0-100)
    - Current price and market data
    - Detailed reasoning and key factors
    - Risk assessment
    """
    start_time = datetime.utcnow()
    
    try:
        # Process the analysis request through the agent orchestrator
        response = await agent_orchestrator.process_analysis_request(request)
        
        # Record performance metrics
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        background_tasks.add_task(
            performance_monitor.record_request,
            "/api/v1/analyze",
            "POST", 
            processing_time,
            200
        )
        background_tasks.add_task(performance_monitor.record_analysis)
        
        # Log the analysis
        background_tasks.add_task(
            logging_service.log_analysis_request,
            request,
            response
        )
        
        logger.info(f"Analysis completed for query: '{request.query}' -> {response.ticker}")
        return response
        
    except Exception as e:
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Log error and record metrics
        background_tasks.add_task(
            logging_service.log_error,
            e,
            {
                'context': 'analyze_stock_endpoint',
                'query': request.query,
                'processing_time_ms': processing_time
            }
        )
        background_tasks.add_task(
            performance_monitor.record_request,
            "/api/v1/analyze",
            "POST",
            processing_time,
            500
        )
        
        logger.error(f"Analysis failed for query '{request.query}': {e}")
        
        # Return structured error response
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "ANALYSIS_FAILED",
                "error_message": f"Stock analysis failed: {str(e)}",
                "suggestions": [
                    "Try using a specific company name like 'Apple' or 'Microsoft'",
                    "Make sure the company is listed on NASDAQ",
                    "Check your spelling and try again"
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/analyze/{analysis_id}")
async def get_analysis_by_id(analysis_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific analysis by its ID
    
    **Parameters:**
    - analysis_id: Unique identifier for the analysis
    
    **Returns:**
    - Complete analysis record with all details
    """
    try:
        analysis = await logging_service.get_analysis_by_id(analysis_id)
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "ANALYSIS_NOT_FOUND",
                    "error_message": f"Analysis with ID '{analysis_id}' not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        return {
            "success": True,
            "analysis": analysis,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve analysis {analysis_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "RETRIEVAL_FAILED",
                "error_message": f"Failed to retrieve analysis: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/analyses/recent")
async def get_recent_analyses(
    ticker: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get recent stock analyses
    
    **Parameters:**
    - ticker (optional): Filter by specific ticker symbol
    - limit: Maximum number of results (default: 50, max: 100)
    
    **Returns:**
    - List of recent analyses with summary information
    """
    try:
        # Validate limit
        if limit > 100:
            limit = 100
        elif limit < 1:
            limit = 1
        
        analyses = await logging_service.get_recent_analyses(ticker, limit)
        
        return {
            "success": True,
            "count": len(analyses),
            "ticker_filter": ticker,
            "analyses": analyses,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent analyses: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "RETRIEVAL_FAILED",
                "error_message": f"Failed to retrieve recent analyses: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/analyses/search")
async def search_analyses(
    ticker_symbol: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Search analyses with filtering options
    
    **Parameters:**
    - ticker_symbol (optional): Filter by ticker symbol
    - start_date (optional): Start date for date range filter
    - end_date (optional): End date for date range filter  
    - limit: Maximum number of results (default: 100, max: 1000)
    
    **Returns:**
    - Filtered list of analyses matching the criteria
    """
    try:
        from src.models.logging import LogQueryRequest
        
        # Validate limit
        if limit > 1000:
            limit = 1000
        elif limit < 1:
            limit = 1
        
        # Create query request
        query_request = LogQueryRequest(
            ticker_symbol=ticker_symbol,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # Execute search
        result = await logging_service.get_analysis_logs(query_request)
        
        return {
            "success": True,
            "total_count": result.total_count,
            "returned_count": len(result.entries),
            "filters": {
                "ticker_symbol": ticker_symbol,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "limit": limit
            },
            "analyses": result.entries,
            "query_timestamp": result.query_timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to search analyses: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "SEARCH_FAILED",
                "error_message": f"Analysis search failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )