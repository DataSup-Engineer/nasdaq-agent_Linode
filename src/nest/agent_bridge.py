"""
Agent Bridge for NASDAQ Stock Agent A2A Communication

Implements A2AServer interface from python_a2a library for agent-to-agent communication.
"""

import logging
import uuid
import requests
from typing import Optional, Callable
from python_a2a import A2AServer, A2AClient, Message, TextContent, MessageRole

from .agent_logic import process_a2a_message_sync

logger = logging.getLogger(__name__)


class StockAgentBridge(A2AServer):
    """
    Agent Bridge for NASDAQ Stock Agent.
    
    Handles incoming A2A messages and routes them to appropriate handlers:
    - Stock queries: Processed through agent_logic
    - @agent-id messages: Forwarded to other agents
    - /commands: System commands
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_url: str,
        agent_logic: Optional[Callable[[str, str], str]] = None,
        registry_url: Optional[str] = None
    ):
        """
        Initialize the Stock Agent Bridge.
        
        Args:
            agent_id: Unique identifier for this agent
            agent_url: Public URL for this agent's A2A endpoint
            agent_logic: Function to process messages (defaults to process_a2a_message_sync)
            registry_url: URL of NANDA Registry for agent discovery
        """
        super().__init__(url=agent_url)
        self.agent_id = agent_id
        self.agent_logic = agent_logic or process_a2a_message_sync
        self.registry_url = registry_url
        
        logger.info(f"🤖 [StockAgentBridge] Initialized with agent_id: {agent_id}")
        logger.info(f"🌐 [StockAgentBridge] Agent URL: {agent_url}")
        logger.info(f"🌐 [StockAgentBridge] Registry URL: {registry_url}")
    
    def handle_message(self, msg: Message) -> Message:
        """
        Handle incoming A2A messages.
        
        Routes messages based on content:
        - @agent-id: Forward to another agent
        - /command: Execute system command
        - Other: Process as stock query
        
        Args:
            msg: Incoming A2A Message
            
        Returns:
            Message: Response message
        """
        conversation_id = msg.conversation_id or str(uuid.uuid4())
        
        # Only handle text content
        if not isinstance(msg.content, TextContent):
            logger.warning(f"⚠️ [{self.agent_id}] Received non-text message")
            return self._create_response(
                msg, conversation_id,
                "Sorry, I only support text messages."
            )
        
        user_text = msg.content.text.strip()
        
        logger.info(f"📨 [{self.agent_id}] Received message: {user_text[:100]}...")
        
        try:
            # Route based on message prefix
            if user_text.startswith("@"):
                # Agent-to-agent message
                return self._handle_agent_message(user_text, msg, conversation_id)
            elif user_text.startswith("/"):
                # System command
                return self._handle_command(user_text, msg, conversation_id)
            else:
                # Stock query - process through agent logic
                return self._handle_stock_query(user_text, msg, conversation_id)
                
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] Error handling message: {e}", exc_info=True)
            return self._create_response(
                msg, conversation_id,
                f"Sorry, I encountered an error: {str(e)}"
            )


    def _handle_stock_query(self, query: str, msg: Message, conversation_id: str) -> Message:
        """
        Handle stock analysis queries.
        
        Args:
            query: Stock query text
            msg: Original message
            conversation_id: Conversation ID
            
        Returns:
            Message: Response with stock analysis
        """
        try:
            logger.info(f"📊 [{self.agent_id}] Processing stock query: {query[:50]}...")
            
            # Process through agent logic
            response_text = self.agent_logic(query, conversation_id)
            
            logger.info(f"✅ [{self.agent_id}] Stock query processed successfully")
            return self._create_response(msg, conversation_id, response_text)
            
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] Error processing stock query: {e}", exc_info=True)
            return self._create_response(
                msg, conversation_id,
                f"Sorry, I couldn't process that stock query: {str(e)}"
            )
    
    def _handle_agent_message(self, text: str, msg: Message, conversation_id: str) -> Message:
        """
        Handle @agent-id messages for A2A communication.
        
        Format: @agent-id message text
        
        Args:
            text: Message text starting with @agent-id
            msg: Original message
            conversation_id: Conversation ID
            
        Returns:
            Message: Response from target agent or error
        """
        try:
            # Parse @agent-id message
            parts = text.split(" ", 1)
            if len(parts) < 2:
                return self._create_response(
                    msg, conversation_id,
                    "Invalid format. Use: @agent-id your message here"
                )
            
            target_agent_id = parts[0][1:]  # Remove @ prefix
            message_text = parts[1]
            
            logger.info(f"🔄 [{self.agent_id}] Forwarding to {target_agent_id}: {message_text[:50]}...")
            
            # Look up target agent
            agent_url = self._lookup_agent(target_agent_id)
            if not agent_url:
                logger.warning(f"⚠️ [{self.agent_id}] Agent {target_agent_id} not found")
                return self._create_response(
                    msg, conversation_id,
                    f"Agent '{target_agent_id}' not found in registry."
                )
            
            # Send message to target agent
            result = self._send_to_agent(agent_url, target_agent_id, message_text, conversation_id)
            
            return self._create_response(msg, conversation_id, result)
            
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] Error handling agent message: {e}", exc_info=True)
            return self._create_response(
                msg, conversation_id,
                f"Error forwarding message: {str(e)}"
            )
    
    def _handle_command(self, text: str, msg: Message, conversation_id: str) -> Message:
        """
        Handle system commands (/help, /status, etc.).
        
        Args:
            text: Command text starting with /
            msg: Original message
            conversation_id: Conversation ID
            
        Returns:
            Message: Command response
        """
        try:
            # Parse command
            parts = text.split(" ", 1)
            command = parts[0][1:].lower() if parts else ""
            
            logger.info(f"⚙️ [{self.agent_id}] Executing command: /{command}")
            
            # Route to agent logic which handles commands
            response_text = self.agent_logic(text, conversation_id)
            
            return self._create_response(msg, conversation_id, response_text)
            
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] Error handling command: {e}", exc_info=True)
            return self._create_response(
                msg, conversation_id,
                f"Error executing command: {str(e)}"
            )
    
    def _lookup_agent(self, agent_id: str) -> Optional[str]:
        """
        Look up agent URL in NANDA Registry.
        
        Args:
            agent_id: Target agent identifier
            
        Returns:
            Optional[str]: Agent URL or None if not found
        """
        if not self.registry_url:
            logger.warning(f"⚠️ [{self.agent_id}] No registry URL configured")
            return None
        
        try:
            # Query registry for agent
            lookup_url = f"{self.registry_url}/lookup/{agent_id}"
            logger.info(f"🌐 [{self.agent_id}] Looking up {agent_id} at {lookup_url}")
            
            response = requests.get(lookup_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                agent_url = data.get("agent_url")
                logger.info(f"✅ [{self.agent_id}] Found {agent_id}: {agent_url}")
                return agent_url
            else:
                logger.warning(f"⚠️ [{self.agent_id}] Agent {agent_id} not found (status: {response.status_code})")
                return None
                
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] Registry lookup failed: {e}")
            return None
    
    def _send_to_agent(
        self,
        agent_url: str,
        target_agent_id: str,
        message_text: str,
        conversation_id: str
    ) -> str:
        """
        Send message to another agent using A2A protocol.
        
        Args:
            agent_url: Target agent's A2A endpoint URL
            target_agent_id: Target agent identifier
            message_text: Message to send
            conversation_id: Conversation ID
            
        Returns:
            str: Response from target agent
        """
        try:
            # Ensure URL has /a2a endpoint
            if not agent_url.endswith('/a2a'):
                agent_url = f"{agent_url}/a2a"
            
            logger.info(f"📤 [{self.agent_id}] → [{target_agent_id}]: {message_text[:50]}...")
            
            # Create A2A client and send message
            client = A2AClient(agent_url, timeout=30)
            response = client.send_message(
                Message(
                    role=MessageRole.USER,
                    content=TextContent(text=message_text),
                    conversation_id=conversation_id
                )
            )
            
            # Extract response text
            logger.info(f"🔍 [{self.agent_id}] Response type: {type(response)}, has parts: {hasattr(response, 'parts')}")
            
            if response:
                # Try different response formats
                if hasattr(response, 'parts') and response.parts:
                    response_text = response.parts[0].text
                    logger.info(f"✅ [{self.agent_id}] Received response from {target_agent_id}")
                    return f"[{target_agent_id}] {response_text}"
                elif hasattr(response, 'content') and hasattr(response.content, 'text'):
                    response_text = response.content.text
                    logger.info(f"✅ [{self.agent_id}] Received response from {target_agent_id}")
                    return f"[{target_agent_id}] {response_text}"
                elif hasattr(response, 'text'):
                    response_text = response.text
                    logger.info(f"✅ [{self.agent_id}] Received response from {target_agent_id}")
                    return f"[{target_agent_id}] {response_text}"
                else:
                    logger.warning(f"⚠️ [{self.agent_id}] Unknown response format: {response}")
                    return f"Message sent to {target_agent_id} (response format unknown)"
            else:
                logger.info(f"✅ [{self.agent_id}] Message delivered to {target_agent_id}")
                return f"Message sent to {target_agent_id}"
                
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] Error sending to {target_agent_id}: {e}")
            return f"Error communicating with {target_agent_id}: {str(e)}"
    
    def _create_response(self, original_msg: Message, conversation_id: str, text: str) -> Message:
        """
        Create A2A response message.
        
        Args:
            original_msg: Original incoming message
            conversation_id: Conversation ID
            text: Response text
            
        Returns:
            Message: Formatted A2A response
        """
        # Prefix response with agent identifier
        prefixed_text = f"[{self.agent_id}] {text}" if not text.startswith(f"[{self.agent_id}]") else text
        
        return Message(
            role=MessageRole.AGENT,
            content=TextContent(text=prefixed_text),
            parent_message_id=original_msg.message_id,
            conversation_id=conversation_id
        )
