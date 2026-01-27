import asyncio
import random
from typing import List, Tuple, Optional
from agents.base_agent import BaseAgent
from environments.simulation_engine import SimulationEngine
from utils.message_bus import MessageBus

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
        
        # Desynchronize Start (Jitter)
        await asyncio.sleep(random.uniform(0.0, 2.0))
        
        # Initialize
        obs = await self.engine.get_state(self.agent_id)
        
        while self.running:
            await self.step()
            # Step Jitter (0.1 +/- 0.05s)
            await asyncio.sleep(max(0.05, 0.1 + random.uniform(-0.05, 0.05)))
            
    async def step(self):
        # 1. Sense
        state = await self.engine.get_state(self.agent_id)
        if not state:
            self.logger.warning("No state received!")
            return
            
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
        if cx < tx: return "RIGHT"
        if cx > tx: return "LEFT"
        if cy < ty: return "UP"
        if cy > ty: return "DOWN"
        return "STAY"
