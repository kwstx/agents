import asyncio
import random
import time
from typing import List, Tuple, Optional
from agent_forge.core.base_agent import BaseAgent
from agent_forge.core.engine import SimulationEngine
from agent_forge.utils.message_bus import MessageBus

class WarehouseAgent(BaseAgent):
    """
    Agent for Warehouse Logistics.
    States: IDLE, TO_PICKUP, TO_DROPOFF, TO_CHARGE
    """
    def __init__(self, agent_id: str, message_bus: MessageBus, engine: SimulationEngine, behavior_config=None):
        super().__init__(agent_id, message_bus)
        self.engine = engine
        self.state["battery"] = 100.0
        self.state["carrying"] = None
        self.current_goal = None # (x, y) or None
        self.goal_type = None # "pickup", "dropoff", "charge"
        
        # Behavior Archetypes
        self.behavior = behavior_config or {}
        self.charge_threshold = self.behavior.get("charge_threshold", 20.0) # Default 20%

    async def process_task(self, task):
        if task == "start_logistics":
            # Run as background task to avoid blocking/timeout
            asyncio.create_task(self.run_logistics_loop())
            return "Logistics Loop Started"
        return f"Unknown task: {task}"

    async def run_logistics_loop(self):
        self.logger.info("Starting logistics loop")
        # Initialize
        obs = await self.engine.get_state(self.agent_id)
        
        # Desynchronize Start
        start_delay_max = self.behavior.get("start_delay_max", 2.0)
        if start_delay_max > 0:
            await asyncio.sleep(random.uniform(0.0, start_delay_max))
        
        while self.running:
            await self.step()
            # Jitter step
            step_interval = self.behavior.get("step_interval", 0.1)
            step_jitter = self.behavior.get("step_jitter", 0.05)
            
            delay = step_interval
            if step_jitter > 0:
                delay += random.uniform(0.0, step_jitter)
            
            await asyncio.sleep(delay)

            
    async def step(self):
        # 1. Sense
        state = await self.engine.get_state(self.agent_id)
        if not state:
            self.logger.warning("No state received!")
            return
            
        read_time = time.time()
        server_time = state.get("server_time", read_time) 
        drift = read_time - server_time
        
        # Log Drift stats
        self.logger.info(f"Drift Analysis - Read: {read_time:.4f}, Server: {server_time:.4f}, Drift: {drift:.4f}s")
        
        pos = state["position"]
        battery = state["battery"]
        carrying = state["carrying"]
        self.state.update(state)

        # 2. Think / Plan
        action = "STAY"
        
        # Priority 1: Battery Critical
        if battery < self.charge_threshold and self.goal_type != "charge":
            self.set_goal(self.find_nearest_zone("charger"), "charge")
            self.logger.warning(f"Battery low ({battery}%), heading to charger")
        
        # Priority 2: Charge until full
        if self.goal_type == "charge":
             if battery >= 95.0:
                 self.goal_type = None # Done charging
                 self.current_goal = None
             else:
                 # Navigate to charger
                 pass
        
        # Priority 3: Deliver if carrying
        if carrying and self.goal_type != "dropoff":
            self.set_goal(self.find_nearest_zone("dropoff"), "dropoff")
        
        # Priority 4: Pickup if idle
        if not carrying and battery > self.charge_threshold and self.goal_type != "pickup":
             self.set_goal(self.find_nearest_zone("pickup"), "pickup")

        # Execute Navigation or Action
        if self.current_goal:
            if pos == self.current_goal:
                # Arrived, perform interaction
                if self.goal_type == "pickup":
                    action = "PICKUP"
                elif self.goal_type == "dropoff":
                    action = "DROPOFF"
                elif self.goal_type == "charge":
                    action = "CHARGE"
                
                # After action, clear goal to rethink
                if action in ["PICKUP", "DROPOFF"]:
                     self.current_goal = None
                     self.goal_type = None
            else:
                # Move towards goal
                action = self.get_next_move(pos, self.current_goal)
        
        # 3. Act
        success = await self.engine.perform_action(self.agent_id, action)
        
        # 4. Feedback
        # In stepped mode, we might wait for feedback or just proceed. 
        # For now, fire and forget or check done status
        feedback = await self.engine.get_feedback(self.agent_id)
        if feedback["done"]:
             self.logger.info("Agent finished (e.g. died or done)")
             self.running = False 
            
    def set_goal(self, pos, type):
        self.current_goal = pos
        self.goal_type = type
        self.logger.info(f"New Goal: {type} at {pos}")

    def find_nearest_zone(self, zone_type: str) -> Tuple[int, int]:
        # Hack: Access env directly via engine to know zones. 
        # Ideally, agent receives map on init.
        zones = self.engine.env.zones[zone_type]
        # Random choice for load balancing for now
        return random.choice(zones)

    def get_next_move(self, current: Tuple[int, int], target: Tuple[int, int]) -> str:
        cx, cy = current
        tx, ty = target
        
        # Simple Manhattan Logic
        next_pos = current
        action = "STAY"
        
        if cx < tx: 
            action = "RIGHT"
            next_pos = (cx + 1, cy)
        elif cx > tx: 
            action = "LEFT"
            next_pos = (cx - 1, cy)
        elif cy < ty: 
            action = "UP"
            next_pos = (cx, cy + 1)
        elif cy > ty: 
            action = "DOWN"
            next_pos = (cx, cy - 1)
            
        # Collision Avoidance (Sensor)
        if self._is_occupied(next_pos):
            self.logger.warning(f"Path blocked at {next_pos}, waiting...")
            return "STAY"
            
        return action

    def _is_occupied(self, pos: Tuple[int, int]) -> bool:
        """Checks if a position is occupied by another agent."""
        # Cheating: accessing env state directly for MVP
        if hasattr(self.engine, "env") and hasattr(self.engine.env, "agents"):
             for aid, state in self.engine.env.agents.items():
                 if aid != self.agent_id and state["position"] == pos:
                     return True
        return False
