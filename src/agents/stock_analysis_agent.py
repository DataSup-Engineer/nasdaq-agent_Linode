"""
Main Langchain agent orchestrator for NASDAQ Stock Agent
"""
import asyncio
from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime
from langchain.agents import AgentExecutor, create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from langchain.schema import AgentAction, AgentFinish
from src.config.settings import settings
from src.agents.langchain_tools import LANGCHAIN_TOOLS, get_tool_descriptions
from src.models.analysis import StockAnalysis, AnalysisRequest, AnalysisResponse

logger = logging.getLogger(__name__)


class StockAnalysisAgent:
    """Main Langchain agent for stock analysis orchestration"""
    
    def __init__(self):
        self.llm = self._initialize_llm()
        self.tools = LANGCHAIN_TOOLS
        self.agent_executor = self._create_agent_executor()
        self.conversation_memory = {}  # Simple in-memory conversation tracking
    
    def _initialize_llm(self) -> ChatAnthropic:
        """Initialize the Claude LLM"""
        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")
        
        return ChatAnthropic(
            model=settings.anthropic_model,
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0.1,  # Low temperature for consistent analysis
            max_tokens=4000
        )
    
    def _create_agent_prompt(self) -> PromptTemplate:
        """Create the agent prompt template"""
        
        tool_descriptions = get_tool_descriptions()
        tools_text = "\n".join([f"- {name}: {desc}" for name, desc in tool_descriptions.items()])
        
        template = """
You are a professional NASDAQ stock analysis agent. Your role is to help users analyze stocks and make informed investment decisions.

AVAILABLE TOOLS:
{tools}

Tool Names: {tool_names}

WORKFLOW:
1. If the user provides a company name (not a ticker), use company_name_resolver to get the ticker symbol
2. Validate the ticker using ticker_validator if needed
3. Fetch comprehensive market data using market_data_fetcher
4. Perform investment analysis using investment_analyzer
5. Check market status if relevant using market_status_checker
6. Provide a comprehensive response with clear recommendations

RESPONSE GUIDELINES:
- Always provide clear, actionable investment advice
- Include confidence scores and reasoning for recommendations
- Mention key risk factors and considerations
- Use professional financial language but keep it accessible
- If markets are closed, mention this in your response
- Always cite the specific data points that support your analysis

IMPORTANT RULES:
- Only analyze NASDAQ-listed stocks
- Always use the tools to get current data - never make up numbers
- If a company name cannot be resolved, provide helpful suggestions
- Be transparent about limitations and risks
- Focus on factual analysis based on the 6-month historical data

Current date and time: {current_time}

User Query: {input}

Thought: I need to analyze this stock query step by step.

{agent_scratchpad}
"""
        
        return PromptTemplate(
            template=template,
            input_variables=["input", "agent_scratchpad", "current_time", "tools", "tool_names"],
            partial_variables={}
        )
    
    def _create_agent_executor(self) -> AgentExecutor:
        """Create the agent executor with tools"""
        prompt = self._create_agent_prompt()
        
        # Create the ReAct agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            max_execution_time=120,  # 2 minutes timeout
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        return agent_executor
    
    async def analyze_stock_query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """Analyze a stock query using direct tool execution (bypassing LangChain agent for reliability)"""
        start_time = datetime.utcnow()
        
        try:
            # Use direct tool execution instead of LangChain agent for better reliability
            result = await self._execute_direct_analysis(query)
            
            # Calculate processing time
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Add processing time to result
            result['processing_time_ms'] = processing_time
            result['timestamp'] = datetime.utcnow().isoformat()
            
            # Store in conversation memory if session provided
            if session_id:
                self._update_conversation_memory(session_id, query, result)
            
            logger.info(f"Stock analysis completed in {processing_time}ms for query: {query[:50]}...")
            return result
            
        except Exception as e:
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"Stock analysis failed for query '{query}': {e}", exc_info=True)
            
            return {
                'success': False,
                'error': f'Analysis failed: {str(e)}',
                'query': query,
                'processing_time_ms': processing_time,
                'timestamp': datetime.utcnow().isoformat(),
                'suggestions': [
                    'Try using a ticker symbol like "AAPL" or "MSFT"',
                    'Make sure the company is listed on NASDAQ',
                    'Check your spelling and try again'
                ]
            }
    
    async def _execute_direct_analysis(self, query: str) -> Dict[str, Any]:
        """Execute analysis directly using tools without LangChain agent complexity"""
        try:
            # Step 1: Extract ticker from query
            ticker = await self._extract_ticker_from_query(query)
            
            if not ticker:
                return {
                    'success': False,
                    'error': 'Could not identify a stock ticker in your query',
                    'query': query,
                    'suggestions': [
                        'Try using a ticker symbol like "AAPL" for Apple',
                        'Or use the full company name like "Apple" or "Microsoft"'
                    ]
                }
            
            # Step 2: Get market data
            market_data_tool = next((t for t in self.tools if t.name == 'market_data_fetcher'), None)
            if not market_data_tool:
                raise Exception("market_data_fetcher tool not found")
            
            market_data_result = await market_data_tool._arun(ticker=ticker)
            market_data = json.loads(market_data_result) if isinstance(market_data_result, str) else market_data_result
            
            if not market_data.get('success'):
                return {
                    'success': False,
                    'error': f'Could not fetch market data for {ticker}',
                    'query': query,
                    'ticker': ticker
                }
            
            # Step 3: Perform investment analysis
            investment_tool = next((t for t in self.tools if t.name == 'investment_analyzer'), None)
            if not investment_tool:
                raise Exception("investment_analyzer tool not found")
            
            analysis_result = await investment_tool._arun(ticker=ticker)
            analysis = json.loads(analysis_result) if isinstance(analysis_result, str) else analysis_result
            
            if not analysis.get('success'):
                return {
                    'success': False,
                    'error': f'Could not perform analysis for {ticker}',
                    'query': query,
                    'ticker': ticker
                }
            
            # Step 4: Build response
            return {
                'success': True,
                'query': query,
                'ticker': ticker,
                'company_name': market_data.get('company_name', ticker),
                'current_price': market_data.get('current_price', 0.0),
                'price_change_percentage': market_data.get('price_change_percentage', 0.0),
                'recommendation': analysis.get('recommendation', 'Hold'),
                'confidence_score': analysis.get('confidence_score', 50.0),
                'response': analysis.get('summary', ''),
                'extracted_data': {
                    'market_data': market_data,
                    'investment_analysis': analysis
                }
            }
            
        except Exception as e:
            logger.error(f"Direct analysis failed: {e}", exc_info=True)
            raise
    
    async def _extract_ticker_from_query(self, query: str) -> Optional[str]:
        """Extract ticker symbol from query"""
        try:
            # First try to find a ticker pattern (2-5 uppercase letters)
            import re
            ticker_pattern = r'\b([A-Z]{2,5})\b'
            matches = re.findall(ticker_pattern, query)
            
            if matches:
                # Validate the first match using the tool from self.tools
                ticker_validator_tool = next((t for t in self.tools if t.name == 'ticker_validator'), None)
                if ticker_validator_tool:
                    for potential_ticker in matches:
                        result = await ticker_validator_tool._arun(ticker=potential_ticker)
                        result_data = json.loads(result) if isinstance(result, str) else result
                        if result_data.get('valid'):
                            return potential_ticker
            
            # If no ticker found, try company name resolution
            company_resolver_tool = next((t for t in self.tools if t.name == 'company_name_resolver'), None)
            if company_resolver_tool:
                result = await company_resolver_tool._arun(company_name=query)
                result_data = json.loads(result) if isinstance(result, str) else result
                
                if result_data.get('success'):
                    return result_data.get('ticker')
            
            return None
            
        except Exception as e:
            logger.error(f"Ticker extraction failed: {e}", exc_info=True)
            return None
    
    async def _execute_agent_async(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent asynchronously"""
        try:
            # Run the agent executor
            result = await self.agent_executor.ainvoke(agent_input)
            return result
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise
    
    def _structure_agent_response(self, agent_result: Dict[str, Any], original_query: str, processing_time: int) -> Dict[str, Any]:
        """Structure the agent response into a standardized format"""
        try:
            # Handle None or empty result
            if agent_result is None:
                logger.error("Agent result is None")
                return {
                    'success': False,
                    'error': 'Agent returned no result',
                    'query': original_query,
                    'processing_time_ms': processing_time,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            output = agent_result.get('output', '')
            intermediate_steps = agent_result.get('intermediate_steps', [])
            
            # Check if output is None or empty
            if output is None or (isinstance(output, str) and not output.strip()):
                logger.warning("Agent output is empty - agent may have hit max iterations")
                return {
                    'success': False,
                    'error': 'Agent failed to generate output. Try using a specific ticker symbol like "AAPL".',
                    'query': original_query,
                    'processing_time_ms': processing_time,
                    'timestamp': datetime.utcnow().isoformat(),
                    'agent_steps': len(intermediate_steps)
                }
            
            # Extract structured data from intermediate steps
            extracted_data = self._extract_data_from_steps(intermediate_steps)
            
            # Build structured response
            response = {
                'success': True,
                'query': original_query,
                'response': output,
                'processing_time_ms': processing_time,
                'timestamp': datetime.utcnow().isoformat(),
                'agent_steps': len(intermediate_steps),
                'extracted_data': extracted_data
            }
            
            # Add specific fields if analysis was completed
            if extracted_data.get('investment_analysis'):
                analysis = extracted_data['investment_analysis']
                response.update({
                    'ticker': analysis.get('ticker'),
                    'company_name': analysis.get('company_name'),
                    'recommendation': analysis.get('recommendation'),
                    'confidence_score': analysis.get('confidence_score'),
                    'current_price': extracted_data.get('market_data', {}).get('current_price'),
                    'price_change_percentage': extracted_data.get('market_data', {}).get('price_change_percentage')
                })
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to structure agent response: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Response structuring failed: {str(e)}',
                'query': original_query,
                'processing_time_ms': processing_time,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _extract_data_from_steps(self, intermediate_steps: List) -> Dict[str, Any]:
        """Extract structured data from agent intermediate steps"""
        extracted = {
            'company_resolution': None,
            'market_data': None,
            'investment_analysis': None,
            'market_status': None
        }
        
        try:
            for step in intermediate_steps:
                if isinstance(step, tuple) and len(step) == 2:
                    action, observation = step
                    
                    if hasattr(action, 'tool') and observation:
                        tool_name = action.tool
                        
                        # Try to parse JSON observations
                        try:
                            obs_data = json.loads(observation)
                            
                            if tool_name == 'company_name_resolver':
                                extracted['company_resolution'] = obs_data
                            elif tool_name == 'market_data_fetcher':
                                extracted['market_data'] = obs_data
                            elif tool_name == 'investment_analyzer':
                                extracted['investment_analysis'] = obs_data
                            elif tool_name == 'market_status_checker':
                                extracted['market_status'] = obs_data
                                
                        except json.JSONDecodeError:
                            # If not JSON, store as text
                            pass
            
            return extracted
            
        except Exception as e:
            logger.error(f"Failed to extract data from agent steps: {e}")
            return extracted
    
    def _update_conversation_memory(self, session_id: str, query: str, response: Dict[str, Any]) -> None:
        """Update conversation memory for session tracking"""
        try:
            if session_id not in self.conversation_memory:
                self.conversation_memory[session_id] = {
                    'created_at': datetime.utcnow(),
                    'interactions': []
                }
            
            interaction = {
                'timestamp': datetime.utcnow(),
                'query': query,
                'response_summary': response.get('response', '')[:200],  # First 200 chars
                'success': response.get('success', False),
                'ticker': response.get('ticker'),
                'recommendation': response.get('recommendation')
            }
            
            self.conversation_memory[session_id]['interactions'].append(interaction)
            
            # Keep only last 10 interactions per session
            if len(self.conversation_memory[session_id]['interactions']) > 10:
                self.conversation_memory[session_id]['interactions'] = \
                    self.conversation_memory[session_id]['interactions'][-10:]
                    
        except Exception as e:
            logger.error(f"Failed to update conversation memory: {e}")
    
    def get_conversation_history(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation history for a session"""
        return self.conversation_memory.get(session_id)
    
    def clear_conversation_memory(self, session_id: str = None) -> None:
        """Clear conversation memory for a session or all sessions"""
        if session_id:
            self.conversation_memory.pop(session_id, None)
        else:
            self.conversation_memory.clear()
    
    async def get_agent_health(self) -> Dict[str, Any]:
        """Get health status of the agent"""
        try:
            # Test basic agent functionality
            test_query = "What is the status of Apple stock?"
            
            start_time = datetime.utcnow()
            
            # Quick health check - just test LLM connection
            test_response = await self.llm.ainvoke("Respond with 'OK' if you can read this.")
            
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return {
                'service': 'StockAnalysisAgent',
                'status': 'healthy',
                'llm_model': settings.anthropic_model,
                'available_tools': len(self.tools),
                'response_time_ms': response_time,
                'conversation_sessions': len(self.conversation_memory),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'service': 'StockAnalysisAgent',
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


class AgentOrchestrator:
    """High-level orchestrator for the stock analysis agent"""
    
    def __init__(self):
        self.stock_agent = StockAnalysisAgent()
    
    async def process_analysis_request(self, request: AnalysisRequest) -> AnalysisResponse:
        """Process an analysis request and return structured response"""
        try:
            # Execute agent analysis
            agent_result = await self.stock_agent.analyze_stock_query(request.query)
            
            # Handle None result
            if agent_result is None:
                logger.error("Agent returned None result")
                return AnalysisResponse(
                    analysis_id='error',
                    ticker='unknown',
                    company_name='unknown',
                    current_price=0.0,
                    price_change_percentage=0.0,
                    recommendation='Hold',
                    confidence_score=0.0,
                    reasoning='Agent failed to return a result. Please try with a specific ticker symbol like "AAPL" or "MSFT".',
                    key_factors=[],
                    risk_assessment='Unable to assess',
                    summary='Agent execution failed. Try using a ticker symbol directly.',
                    processing_time_ms=0,
                    timestamp=datetime.utcnow()
                )
            
            if agent_result.get('success'):
                # Safely extract nested data
                extracted_data = agent_result.get('extracted_data', {}) or {}
                investment_analysis = extracted_data.get('investment_analysis', {}) or {}
                
                # Create structured response
                response = AnalysisResponse(
                    analysis_id=investment_analysis.get('analysis_id', 'unknown'),
                    ticker=agent_result.get('ticker', 'unknown'),
                    company_name=agent_result.get('company_name', 'unknown'),
                    current_price=agent_result.get('current_price', 0.0),
                    price_change_percentage=agent_result.get('price_change_percentage', 0.0),
                    recommendation=agent_result.get('recommendation', 'Hold'),
                    confidence_score=agent_result.get('confidence_score', 50.0),
                    reasoning=agent_result.get('response', ''),
                    key_factors=investment_analysis.get('key_factors', []),
                    risk_assessment=investment_analysis.get('risk_assessment', ''),
                    summary=agent_result.get('response', ''),
                    processing_time_ms=agent_result.get('processing_time_ms', 0),
                    timestamp=datetime.fromisoformat(agent_result['timestamp'].replace('Z', '+00:00'))
                )
                
                return response
            
            else:
                # Return error response
                return AnalysisResponse(
                    analysis_id='error',
                    ticker='unknown',
                    company_name='unknown',
                    current_price=0.0,
                    price_change_percentage=0.0,
                    recommendation='Hold',
                    confidence_score=0.0,
                    reasoning=agent_result.get('error', 'Analysis failed'),
                    key_factors=[],
                    risk_assessment='Unable to assess due to error',
                    summary=agent_result.get('error', 'Analysis failed'),
                    processing_time_ms=agent_result.get('processing_time_ms', 0),
                    timestamp=datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Agent orchestrator failed: {e}", exc_info=True)
            return AnalysisResponse(
                analysis_id='error',
                ticker='unknown',
                company_name='unknown',
                current_price=0.0,
                price_change_percentage=0.0,
                recommendation='Hold',
                confidence_score=0.0,
                reasoning=f'Orchestration failed: {str(e)}',
                key_factors=[],
                risk_assessment='Unable to assess due to orchestration error',
                summary=f'Analysis orchestration failed: {str(e)}',
                processing_time_ms=0,
                timestamp=datetime.utcnow()
            )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        agent_health = await self.stock_agent.get_agent_health()
        
        return {
            'service': 'AgentOrchestrator',
            'overall_status': agent_health.get('status', 'unknown'),
            'agent_health': agent_health,
            'timestamp': datetime.utcnow().isoformat()
        }


# Global agent orchestrator instance
agent_orchestrator = AgentOrchestrator()