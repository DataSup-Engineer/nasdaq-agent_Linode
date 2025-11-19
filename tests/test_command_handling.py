"""
Test command handling functionality in StockAgentBridge.

Tests the implementation of task 4.4:
- _handle_command() method
- Support for /help, /status, /ping commands
- Formatted command responses
"""

import pytest
from unittest.mock import Mock, patch
from python_a2a import Message, TextContent, MessageRole

from src.nest.agent_bridge import StockAgentBridge


class TestCommandHandling:
    """Test command handling functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent_id = "nasdaq-stock-agent"
        self.bridge = StockAgentBridge(
            agent_id=self.agent_id,
            registry_url="http://test-registry.com:6900"
        )
    
    def test_handle_help_command(self):
        """Test /help command returns help information."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="/help"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge.handle_message(msg)
        
        # Verify response
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        assert "Available Commands" in response.content.text or "help" in response.content.text.lower()
        assert response.parent_message_id == msg.message_id
        assert response.conversation_id == "test-conv-123"
    
    def test_handle_info_command(self):
        """Test /info command returns agent information."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="/info"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge.handle_message(msg)
        
        # Verify response
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        # /info should return help information
        assert "Available Commands" in response.content.text or "help" in response.content.text.lower()
    
    def test_handle_ping_command(self):
        """Test /ping command returns pong response."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="/ping"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge.handle_message(msg)
        
        # Verify response
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        assert "pong" in response.content.text.lower() or "online" in response.content.text.lower()
    
    def test_handle_status_command(self):
        """Test /status command returns agent status."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="/status"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge.handle_message(msg)
        
        # Verify response
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        assert "status" in response.content.text.lower() or "online" in response.content.text.lower()
    
    def test_handle_capabilities_command(self):
        """Test /capabilities command returns agent capabilities."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="/capabilities"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge.handle_message(msg)
        
        # Verify response
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        assert "capabilit" in response.content.text.lower()
    
    def test_handle_unknown_command(self):
        """Test unknown command returns error message."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="/unknown"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge.handle_message(msg)
        
        # Verify response
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        assert "unknown" in response.content.text.lower() or "help" in response.content.text.lower()
    
    def test_handle_command_with_arguments(self):
        """Test command with additional arguments."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="/help me please"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge.handle_message(msg)
        
        # Verify response (should still process as /help)
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        # Should return help information
        assert len(response.content.text) > 0
    
    def test_handle_command_case_insensitive(self):
        """Test commands are case-insensitive."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="/HELP"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge.handle_message(msg)
        
        # Verify response
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        assert "Available Commands" in response.content.text or "help" in response.content.text.lower()
    
    def test_handle_command_error_handling(self):
        """Test error handling in command processing."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="/status"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        # Mock agent_logic to raise exception
        with patch.object(self.bridge, 'agent_logic', side_effect=Exception("Test error")):
            response = self.bridge.handle_message(msg)
        
        # Verify error response
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        assert "error" in response.content.text.lower()
    
    def test_command_response_format(self):
        """Test that command responses are properly formatted."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="/ping"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge.handle_message(msg)
        
        # Verify response format
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        assert response.parent_message_id == msg.message_id
        assert response.conversation_id == "test-conv-123"
        # Should have agent prefix
        assert f"[{self.agent_id}]" in response.content.text
    
    def test_command_routing_in_handle_message(self):
        """Test that commands are properly routed in handle_message."""
        # Test that / prefix triggers command handling
        commands = ["/help", "/ping", "/status", "/info", "/capabilities"]
        
        for cmd in commands:
            msg = Message(
                role=MessageRole.USER,
                content=TextContent(text=cmd),
                conversation_id="test-conv-123",
                message_id="msg-456"
            )
            
            response = self.bridge.handle_message(msg)
            
            # All should return valid responses
            assert response.role == MessageRole.AGENT
            assert isinstance(response.content, TextContent)
            assert len(response.content.text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
