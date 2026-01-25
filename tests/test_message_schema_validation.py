import pytest
import uuid
from utils.message_bus import Message

def test_valid_message():
    """Test that a valid message is created successfully."""
    msg = Message(
        topic="test", 
        sender="agent_1", 
        payload={"key": "value"}, 
        message_type="command"
    )
    assert msg.topic == "test"
    assert msg.message_type == "command"
    assert msg.trace_id is not None

def test_invalid_message_type():
    """Test that an invalid message_type raises ValueError."""
    with pytest.raises(ValueError) as excinfo:
        Message(
            topic="test", 
            sender="agent_1", 
            payload={}, 
            message_type="gossip" # Invalid
        )
    assert "Invalid message_type" in str(excinfo.value)

def test_invalid_field_types():
    """Test that non-string sender/topic raise TypeError."""
    with pytest.raises(TypeError):
        Message(topic=123, sender="agent_1", payload={})
        
    with pytest.raises(TypeError):
        Message(topic="test", sender=123, payload={})

def test_malformed_trace_id():
    """Test that a manually provided invalid trace_id raises ValueError."""
    with pytest.raises(ValueError) as excinfo:
        Message(
            topic="test", 
            sender="agent_1", 
            payload={}, 
            trace_id="not-a-uuid"
        )
    assert "Invalid trace_id" in str(excinfo.value)
    
def test_valid_trace_id_propagation():
    """Test that a valid trace_id is accepted."""
    valid_uuid = str(uuid.uuid4())
    msg = Message(
        topic="test", 
        sender="agent_1", 
        payload={}, 
        trace_id=valid_uuid
    )
    assert msg.trace_id == valid_uuid
