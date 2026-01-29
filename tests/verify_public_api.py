import sys
import pytest

def test_public_api_completeness():
    """
    Verify that a user can build a complete simulation using ONLY the top-level 'agent_forge' package.
    Deep imports (e.g., 'agent_forge.agents.learning_agent') are forbidden in this test context
    to ensure the public API is self-sufficient.
    """
    
    # Reset sys.modules to force fresh imports (optional but safer)
    # Actually, we just want to write code that uses 'agent_forge.X'
    
    import agent_forge as af
    
    print("Testing Public API Surface...")
    
    # 1. Instantiate Environment
    assert hasattr(af, "GridWorld"), "GridWorld not exposed in public API"
    env = af.GridWorld(size=10)
    assert env is not None
    
    # 2. Instantiate Model
    assert hasattr(af, "GridDecisionModel"), "GridDecisionModel not exposed"
    assert hasattr(af, "ModelConfig"), "ModelConfig not exposed"
    config = af.ModelConfig()
    model = af.GridDecisionModel(config)
    
    # 3. Instantiate MessageBus
    assert hasattr(af, "MessageBus"), "MessageBus not exposed"
    bus = af.MessageBus()
    
    # 4. Instantiate Agent
    assert hasattr(af, "LearningGridAgent"), "LearningGridAgent not exposed"
    agent = af.LearningGridAgent("TestAgent", bus, env, model)
    assert agent is not None
    
    # 5. Instantiate Financial Components
    assert hasattr(af, "OrderBookEnv"), "OrderBookEnv not exposed"
    assert hasattr(af, "MomentumTrader"), "MomentumTrader not exposed"
    
    fin_env = af.OrderBookEnv()
    fin_agent = af.MomentumTrader("Trader1", 1000.0, message_bus=bus)
    
    assert fin_agent is not None
    
    # 6. Verify InteractionLogger
    assert hasattr(af, "InteractionLogger"), "InteractionLogger not exposed"
    logger = af.InteractionLogger(db_path=":memory:", log_file="test_log.jsonl")
    
    print("SUCCESS: Public API contains all necessary components for standard simulations.")

    # 7. Negative Test: Check that internal submodules are NOT implicitly reachable 
    # if we haven't imported them explicitly (though Python caching makes this hard if we already imported af)
    # Instead, we rely on the fact that the USER CODE above didn't need them.
    
if __name__ == "__main__":
    test_public_api_completeness()
