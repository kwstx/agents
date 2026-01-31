import asyncio
import logging
from typing import Dict, Any, List, Optional
from agent_forge.core.engine import SimulationEngine
from agent_forge.envs.warehouse import WarehouseEnv
from agent_forge.envs.warehouse_agent import WarehouseAgent
from agent_forge.utils.message_bus import MessageBus
from agent_forge.utils.interaction_logger import InteractionLogger
import os

class HeadlessRunner:
    """
    Pure SDK harness for running simulations without file I/O or UI.
    """
    def __init__(self):
        self.bus: Optional[MessageBus] = None
        self.engine: SimulationEngine = SimulationEngine(env=None)
        self.agents: List[WarehouseAgent] = []
        self._loop_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.status = "IDLE" # IDLE, RUNNING, STOPPED, FAILED
        self.error_message: Optional[str] = None

    async def setup(self, num_agents: int = 2, grid_size: int = 10, 
                   config: Dict[str, Any] = None):
        """Initializes the simulation components with Zero IO."""
        # 1. Zero IO Bus
        self.bus = MessageBus(log_path=None) 
        await self.bus.start()

        # 2. Env & Engine & Logger
        log_db_path = os.path.abspath("simulation_logs.db")
        self.logger = InteractionLogger(db_path=log_db_path)
        
        env = WarehouseEnv(size=grid_size, num_agents=num_agents, config=config)
        env = WarehouseEnv(size=grid_size, num_agents=num_agents, config=config)
        
        # Update existing engine instead of creating new one
        self.engine.set_env(env)
        self.engine.logger = self.logger
        self.engine.stress_config = config or {}
        
        # Reinitialize adversarial middleware with new config
        # Note: failure_rate is for _apply_stress() exceptions, drop_rate is for silent drops
        from agent_forge.core.adversarial import AdversarialMiddleware, AdversarialConfig
        adv_conf = AdversarialConfig(
            enabled=True if config else False,
            jitter_rate=config.get("latency_rate", 0.0) if config else 0.0,
            latency_range=tuple(config.get("latency_range", (0.0, 0.0))) if config else (0.0, 0.0),
            drop_rate=config.get("drop_rate", 0.0) if config else 0.0,  # Separate from failure_rate
        )
        self.engine.adversary = AdversarialMiddleware(adv_conf)
        
        # 3. Agents with Zero Checkpoints
        self.agents = []
        for i in range(num_agents):
            a_id = f"Agent-{i}"
            env.get_agent_state(a_id)
            agent = WarehouseAgent(a_id, self.bus, self.engine, behavior_config=config)
            agent.enable_checkpoints = False # Disable disk I/O
            # Redirect agent logger to Null or Memory if needed, 
            # currently it logs to std logging which is fine (controlled by root logger)
            self.agents.append(agent)
            
    async def start(self):
        """Starts all agents."""
        if not self.agents:
            raise RuntimeError("Call setup() before start()")
            
        self.is_running = True
        self.status = "RUNNING"
        for agent in self.agents:
            await agent.start()
            # In headless mode, we might want to trigger them explicitly or let them run async
            # For "SDK Loop" purity, we let them run their async loops
            await agent.add_task("start_logistics")
            
    async def pause(self):
        if self.engine:
            self.engine.pause()

    async def resume(self):
        if self.engine:
            self.engine.resume()

    async def fail(self, reason: str):
        """Manually mark the session as failed (e.g. from an external monitor)."""
        self.status = "FAILED"
        self.is_running = False
        self.error_message = reason
        logging.error(f"Session FAILED: {reason}")
        await self.stop()

    async def stop(self):
        if self.status != "FAILED":
            self.status = "STOPPED"
        self.is_running = False
        if self.agents:
            for agent in self.agents:
                await agent.stop()
        if self.bus:
            await self.bus.stop()
            
    async def get_snapshot(self) -> Dict[str, Any]:
        """Returns a deep copy of the current simulation state."""
        snapshot = {}
        for agent in self.agents:
            state = await self.engine.get_state(agent.agent_id, include_stress=False)
            snapshot[agent.agent_id] = state.copy()
        return snapshot
