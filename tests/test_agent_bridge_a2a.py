"""
Test A2A forwarding functionality in StockAgentBridge.

Tests the implementation of task 4.3:
- _handle_agent_message() method for @agent-id syntax
- _lookup_agent() for registry queries
- A2AClient integration for forwarding messages
- Agent not found error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from python_a2a import Message, TextContent, MessageRole

from src.nest.agent_bridge import StockAgentBridge


class TestA2AForwarding:
    """Test A2A message forwarding functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent_id = "nasdaq-stock-agent"
        self.registry_url = "http://test-registry.com:6900"
        self.bridge = StockAgentBridge(
            agent_id=self.agent_id,
            registry_url=self.registry_url
        )
    
    def test_handle_agent_message_valid_format(self):
        """Test handling @agent-id message with valid format."""
        # Create test message
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="@test-agent What is the weather?"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        # Mock registry lookup and agent communication
        with patch.object(self.bridge, '_lookup_agent', return_value="http://test-agent.com:6000"):
            with patch.object(self.bridge, '_send_to_agent', return_value="[test-agent] It's sunny!"):
                response = self.bridge.handle_message(msg)
        
        # Verify response
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        assert "[test-agent]" in response.content.text
        assert response.parent_message_id == msg.message_id
        assert response.conversation_id == "test-conv-123"
    
    def test_handle_agent_message_invalid_format(self):
        """Test handling @agent-id message with invalid format (no message text)."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="@test-agent"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge.handle_message(msg)
        
        # Verify error response
        assert response.role == MessageRole.AGENT
        assert "Invalid format" in response.content.text
        assert "Use: @agent-id your message here" in response.content.text
    
    def test_lookup_agent_success(self):
        """Test successful agent lookup in registry."""
        with patch('requests.get') as mock_get:
            # Mock successful registry response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"agent_url": "http://test-agent.com:6000"}
            mock_get.return_value = mock_response
            
            result = self.bridge._lookup_agent("test-agent")
            
            # Verify lookup
            assert result == "http://test-agent.com:6000"
            mock_get.assert_called_once_with(
                f"{self.registry_url}/lookup/test-agent",
                timeout=10
            )
    
    def test_lookup_agent_not_found(self):
        """Test agent lookup when agent is not in registry."""
        with patch('requests.get') as mock_get:
            # Mock 404 response
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            result = self.bridge._lookup_agent("nonexistent-agent")
            
            # Verify None returned
            assert result is None
    
    def test_lookup_agent_no_registry_url(self):
        """Test agent lookup when no registry URL is configured."""
        bridge = StockAgentBridge(agent_id="test", registry_url=None)
        
        result = bridge._lookup_agent("test-agent")
        
        # Verify None returned
        assert result is None
    
    def test_lookup_agent_registry_error(self):
        """Test agent lookup when registry request fails."""
        with patch('requests.get', side_effect=Exception("Connection error")):
            result = self.bridge._lookup_agent("test-agent")
            
            # Verify None returned on error
            assert result is None
    
    def test_send_to_agent_success(self):
        """Test successful message sending to another agent."""
        with patch('src.nest.agent_bridge.A2AClient') as mock_client_class:
            # Mock A2AClient
            mock_client = Mock()
            mock_response = Mock()
            mock_response.parts = [Mock(text="Response from target agent")]
            mock_client.send_message.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = self.bridge._send_to_agent(
                agent_url="http://test-agent.com:6000",
                target_agent_id="test-agent",
                message_text="Hello!",
                conversation_id="conv-123"
            )
            
            # Verify result
            assert "[test-agent]" in result
            assert "Response from target agent" in result
            mock_client.send_message.assert_called_once()
    
    def test_send_to_agent_adds_a2a_endpoint(self):
        """Test that /a2a endpoint is added if not present."""
        with patch('src.nest.agent_bridge.A2AClient') as mock_client_class:
            mock_client = Mock()
            mock_client.send_message.return_value = Mock(parts=[Mock(text="OK")])
            mock_client_class.return_value = mock_client
            
            self.bridge._send_to_agent(
                agent_url="http://test-agent.com:6000",
                target_agent_id="test-agent",
                message_text="Hello!",
                conversation_id="conv-123"
            )
            
            # Verify A2AClient was created with /a2a endpoint
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args
            assert call_args[0][0] == "http://test-agent.com:6000/a2a"
    
    def test_send_to_agent_error_handling(self):
        """Test error handling when sending to agent fails."""
        with patch('src.nest.agent_bridge.A2AClient', side_effect=Exception("Connection failed")):
            result = self.bridge._send_to_agent(
                agent_url="http://test-agent.com:6000",
                target_agent_id="test-agent",
                message_text="Hello!",
                conversation_id="conv-123"
            )
            
            # Verify error message returned
            assert "Error communicating with test-agent" in result
            assert "Connection failed" in result
    
    def test_handle_agent_message_agent_not_found(self):
        """Test handling when target agent is not found in registry."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="@nonexistent-agent Hello!"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        # Mock registry lookup returning None
        with patch.object(self.bridge, '_lookup_agent', return_value=None):
            response = self.bridge.handle_message(msg)
        
        # Verify error response
        assert response.role == MessageRole.AGENT
        assert "not found in registry" in response.content.text
        assert "nonexistent-agent" in response.content.text
    
    def test_handle_agent_message_exception_handling(self):
        """Test exception handling in agent message forwarding."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="@test-agent Hello!"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        # Mock lookup to raise exception
        with patch.object(self.bridge, '_lookup_agent', side_effect=Exception("Unexpected error")):
            response = self.bridge.handle_message(msg)
        
        # Verify error response
        assert response.role == MessageRole.AGENT
        assert "Error forwarding message" in response.content.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
