"""
Test response creation functionality in StockAgentBridge.

Tests the implementation of task 4.5:
- _create_response() helper method
- Message formatting with [nasdaq-stock-agent] prefix
- parent_message_id and conversation_id inclusion
"""

import pytest
from python_a2a import Message, TextContent, MessageRole

from src.nest.agent_bridge import StockAgentBridge


class TestResponseCreation:
    """Test response creation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent_id = "nasdaq-stock-agent"
        self.bridge = StockAgentBridge(
            agent_id=self.agent_id,
            registry_url="http://test-registry.com:6900"
        )
    
    def test_create_response_basic(self):
        """Test basic response creation."""
        original_msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="Test message"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge._create_response(
            original_msg,
            "test-conv-123",
            "This is a test response"
        )
        
        # Verify response structure
        assert isinstance(response, Message)
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        assert response.parent_message_id == "msg-456"
        assert response.conversation_id == "test-conv-123"
    
    def test_create_response_adds_agent_prefix(self):
        """Test that response adds [nasdaq-stock-agent] prefix."""
        original_msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="Test message"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge._create_response(
            original_msg,
            "test-conv-123",
            "This is a test response"
        )
        
        # Verify prefix is added
        assert response.content.text.startswith(f"[{self.agent_id}]")
        assert "This is a test response" in response.content.text
    
    def test_create_response_no_duplicate_prefix(self):
        """Test that response doesn't add duplicate prefix if already present."""
        original_msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="Test message"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        # Text already has prefix
        text_with_prefix = f"[{self.agent_id}] This is a test response"
        
        response = self.bridge._create_response(
            original_msg,
            "test-conv-123",
            text_with_prefix
        )
        
        # Verify prefix is not duplicated
        assert response.content.text == text_with_prefix
        # Count occurrences of prefix
        prefix_count = response.content.text.count(f"[{self.agent_id}]")
        assert prefix_count == 1
    
    def test_create_response_preserves_conversation_id(self):
        """Test that response preserves conversation_id."""
        original_msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="Test message"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge._create_response(
            original_msg,
            "test-conv-123",
            "Test response"
        )
        
        # Verify conversation_id is preserved
        assert response.conversation_id == "test-conv-123"
    
    def test_create_response_links_parent_message(self):
        """Test that response links to parent message."""
        original_msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="Test message"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge._create_response(
            original_msg,
            "test-conv-123",
            "Test response"
        )
        
        # Verify parent_message_id links to original
        assert response.parent_message_id == original_msg.message_id
        assert response.parent_message_id == "msg-456"
    
    def test_create_response_uses_agent_role(self):
        """Test that response uses MessageRole.AGENT."""
        original_msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="Test message"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge._create_response(
            original_msg,
            "test-conv-123",
            "Test response"
        )
        
        # Verify role is AGENT
        assert response.role == MessageRole.AGENT
    
    def test_create_response_uses_text_content(self):
        """Test that response uses TextContent type."""
        original_msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="Test message"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge._create_response(
            original_msg,
            "test-conv-123",
            "Test response"
        )
        
        # Verify content is TextContent
        assert isinstance(response.content, TextContent)
        assert hasattr(response.content, 'text')
    
    def test_create_response_with_empty_text(self):
        """Test response creation with empty text."""
        original_msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="Test message"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge._create_response(
            original_msg,
            "test-conv-123",
            ""
        )
        
        # Verify response is created with prefix only
        assert response.content.text == f"[{self.agent_id}] "
    
    def test_create_response_with_multiline_text(self):
        """Test response creation with multiline text."""
        original_msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="Test message"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        multiline_text = """Line 1
Line 2
Line 3"""
        
        response = self.bridge._create_response(
            original_msg,
            "test-conv-123",
            multiline_text
        )
        
        # Verify multiline text is preserved
        assert "Line 1" in response.content.text
        assert "Line 2" in response.content.text
        assert "Line 3" in response.content.text
        assert response.content.text.startswith(f"[{self.agent_id}]")
    
    def test_create_response_with_special_characters(self):
        """Test response creation with special characters."""
        original_msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="Test message"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        special_text = "Test with emojis 📊💰🚀 and symbols $100 @user #tag"
        
        response = self.bridge._create_response(
            original_msg,
            "test-conv-123",
            special_text
        )
        
        # Verify special characters are preserved
        assert "📊💰🚀" in response.content.text
        assert "$100" in response.content.text
        assert "@user" in response.content.text
        assert "#tag" in response.content.text
    
    def test_create_response_integration_with_handle_message(self):
        """Test that _create_response is properly used in handle_message."""
        msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="/ping"),
            conversation_id="test-conv-123",
            message_id="msg-456"
        )
        
        response = self.bridge.handle_message(msg)
        
        # Verify response has all required attributes
        assert response.role == MessageRole.AGENT
        assert isinstance(response.content, TextContent)
        assert response.parent_message_id == msg.message_id
        assert response.conversation_id == "test-conv-123"
        assert response.content.text.startswith(f"[{self.agent_id}]")
    
    def test_create_response_different_conversation_ids(self):
        """Test response creation with different conversation IDs."""
        original_msg = Message(
            role=MessageRole.USER,
            content=TextContent(text="Test message"),
            conversation_id="conv-1",
            message_id="msg-1"
        )
        
        # Create response with different conversation_id
        response = self.bridge._create_response(
            original_msg,
            "conv-2",
            "Test response"
        )
        
        # Verify conversation_id from parameter is used
        assert response.conversation_id == "conv-2"
        # Parent message ID should still link to original
        assert response.parent_message_id == "msg-1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
