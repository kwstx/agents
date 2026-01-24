import asyncio
import logging
import psutil
import time
import os
import random
from datetime import datetime
from agents.base_agent import BaseAgent
from utils.message_bus import MessageBus

# Setup Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Simulation")

class ManagerAgent(BaseAgent):
    def __init__(self, agent_id, bus, worker_count):
        super().__init__(agent_id, bus)
        self.worker_count = worker_count
        self.tasks_assigned = 0
        self.tasks_completed = 0
        
    async def process_task(self, task):
        if task == "start_simulation":
            logger.info(f"{self.agent_id} starting simulation...")
            for i in range(20): # Generate 20 tasks
                worker_id = f"Worker-{random.randint(1, self.worker_count):02d}"
                payload = {"job_id": i, "complexity": random.random()}
                await self.send_message("task_assignment", {"worker": worker_id, "data": payload})
                self.tasks_assigned += 1
                await asyncio.sleep(0.1) # Stagger slightly
        
        elif task.startswith("report_"):
            # A worker reported back
            self.tasks_completed += 1
            logger.info(f"Manager received completion report. Progress: {self.tasks_completed}/{self.tasks_assigned}")

class WorkerAgent(BaseAgent):
    async def process_task(self, task):
        # Workers primarily react to messages, but handle internal tasks too
        if isinstance(task, dict) and "do_job" in task:
            job = task["do_job"]
            # Simulate work
            await asyncio.sleep(job["complexity"] * 0.5) 
            # Report back
            await self.send_message("task_complete", {"job_id": job["job_id"], "worker": self.agent_id})

async def monitor_resources(stop_event):
    process = psutil.Process()
    logger.info("Starting Resource Monitor...")
    while not stop_event.is_set():
        cpu_percent = process.cpu_percent(interval=1.0)
        mem_info = process.memory_info()
        logger.info(f"[MONITOR] CPU: {cpu_percent}% | RSS Memory: {mem_info.rss / 1024 / 1024:.2f} MB")
        await asyncio.sleep(1)

async def run_simulation():
    bus = MessageBus()
    await bus.start()
    
    worker_count = 9
    manager = ManagerAgent("Manager-01", bus, worker_count)
    workers = []
    
    # Init Workers
    for i in range(1, worker_count + 1):
        w_id = f"Worker-{i:02d}"
        w = WorkerAgent(w_id, bus)
        workers.append(w)
        
    # Start all
    await manager.start()
    for w in workers:
        await w.start()
        
    # Wiring: Manager assignment -> Worker
    async def assignment_handler(msg):
        payload = msg.payload
        target_worker = payload["worker"]
        # In a real system, workers would filter themselves. Here we cheat slightly for simulation simplicity
        # or we subscribe everyone. Let's subscribe everyone to 'task_assignment' and filter inside handler?
        # Actually message bus broadcasts logic is simple.
        # Let's map it:
        for w in workers:
            if w.agent_id == target_worker:
                await w.add_task({"do_job": payload["data"]})
                
    bus.subscribe("task_assignment", assignment_handler)
    
    # Wiring: Worker completion -> Manager
    async def completion_handler(msg):
        await manager.add_task(f"report_{msg.payload['job_id']}")
        
    bus.subscribe("task_complete", completion_handler)

    # Monitor
    stop_monitor = asyncio.Event()
    monitor_task = asyncio.create_task(monitor_resources(stop_monitor))
    
    # Kickoff
    logger.info(">>> KICKOFF <<<")
    await manager.add_task("start_simulation")
    
    # Wait for completion (approx 20 tasks * avg 0.25s / concurrency... wait 10s is safe)
    start_time = time.time()
    while manager.tasks_completed < 20:
        if time.time() - start_time > 15:
            logger.error("Simulation timed out!")
            break
        await asyncio.sleep(1)
        
    logger.info(">>> SIMULATION FINISHED <<<")
    
    stop_monitor.set()
    await monitor_task
    
    # Clean shutdown
    await manager.stop()
    for w in workers:
        await w.stop()
    await bus.stop()

if __name__ == "__main__":
    current_process = psutil.Process()
    # Initialize CPU measurement
    current_process.cpu_percent()
    asyncio.run(run_simulation())
