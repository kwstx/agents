__version__ = "0.2.0"

# Explicitly export the public API
from agent_forge.environments.grid_world import GridWorld
from agent_forge.environments.order_book_env import OrderBookEnv, OrderBook
from agent_forge.agents.learning_agent import LearningGridAgent
from agent_forge.agents.strategy_agents import MomentumTrader, MeanReversionTrader
from agent_forge.models.decision_model import GridDecisionModel, ModelConfig
from agent_forge.utils.interaction_logger import InteractionLogger
from agent_forge.utils.message_bus import MessageBus

__all__ = [
    "GridWorld",
    "OrderBookEnv",
    "OrderBook",
    "LearningGridAgent",
    "MomentumTrader",
    "MeanReversionTrader",
    "GridDecisionModel",
    "ModelConfig",
    "InteractionLogger",
    "MessageBus"
]
