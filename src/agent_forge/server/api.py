import asyncio
import uuid
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent_forge.core.engine import SimulationEngine


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

app = FastAPI(title="Agent Forge Mission Control")




# CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimConfig(BaseModel):
    num_agents: int = Field(4, ge=1, le=1000, description="Number of agents (1-1000)")
    grid_size: int = Field(10, ge=4, le=1000, description="Grid size (4-1000)")
    vertical: str = Field("warehouse", pattern="^(warehouse|logistics)$")

from agent_forge.core.runner import HeadlessRunner

class ConnectionManager:
    def __init__(self):
        # ws -> (queue, task)
        self.connections: Dict[WebSocket, Any] = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        queue = asyncio.Queue(maxsize=100) # Conflation buffer

        
        # Start sender task
        task = asyncio.create_task(self._sender_loop(websocket, queue))
        self.connections[websocket] = (queue, task)
        logger.info(f"Client connected. Active: {len(self.connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            queue, task = self.connections[websocket]
            task.cancel()
            del self.connections[websocket]
            logger.info(f"Client disconnected. Active: {len(self.connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Non-blocking broadcast with conflation."""
        for ws, (queue, task) in list(self.connections.items()):
            try:
                # If full, we drop the NEWEST message (tail drop) 
                # OR we could pop old and push new.
                # For simplicity and speed: Try push. If full, SKIP.
                # Ideally: Queue holds LATEST state. If full, dropping intermediate is fine.
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # Queue is full, client is slow. Drop this frame.
                # Optional: Log warning periodically?
                pass
                
    async def _sender_loop(self, ws: WebSocket, queue: asyncio.Queue):
        try:
            while True:
                msg = await queue.get()
                await ws.send_json(msg)
                queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Sender loop error: {e}")
            self.disconnect(ws)

class SessionManager:
    def __init__(self):
        # session_id -> HeadlessRunner
        self.sessions: Dict[str, HeadlessRunner] = {}
        self.connection_manager = ConnectionManager()
        self._lock = asyncio.Lock()

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        runner = HeadlessRunner()
        self.sessions[session_id] = runner
        logger.info(f"Created session {session_id}")
        return session_id

    async def start_session(self, session_id: str, config: SimConfig):
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        runner = self.sessions[session_id]
        if runner.is_running:
            await runner.stop()
        
        conf_dict = config.dict()
        await runner.setup(
            num_agents=config.num_agents, 
            grid_size=config.grid_size,
            config=conf_dict
        )
        
        # Hook runner engine callback
        if runner.engine:
            runner.engine.on_step_callback = self.on_engine_step
            
        try:
            await runner.start()
            logger.info(f"Started session {session_id}")
        except Exception as e:
            logger.error(f"Failed to start session {session_id}: {e}")
            raise e

    async def stop_session(self, session_id: str):
        if session_id in self.sessions:
            await self.sessions[session_id].stop()
            logger.info(f"Stopped session {session_id}")

    async def connect_ws(self, websocket: WebSocket):
        await self.connection_manager.connect(websocket)
        # Send initial snapshot if session exists
        if "default" in self.sessions:
            runner = self.sessions["default"]
            if runner.is_running:
                 snapshot = await runner.get_snapshot()
                 await websocket.send_json({
                     "type": "snapshot",
                     "data": snapshot,
                     "timestamp": asyncio.get_event_loop().time()
                 })

    def disconnect_ws(self, websocket: WebSocket):
        self.connection_manager.disconnect(websocket)

    async def _get_or_create_runner(self, session_id: str) -> HeadlessRunner:
        if session_id not in self.sessions:
            self.sessions[session_id] = HeadlessRunner()
        return self.sessions[session_id]

    async def control_session(self, session_id: str, action: str, config: Optional[Dict[str, Any]] = None):
        async with self._lock:
            runner = await self._get_or_create_runner(session_id)
            
            if action == "start":
                # If running, stop first (restart behavior)
                if runner.is_running:
                    logger.info(f"Restarting session {session_id}...")
                    await runner.stop()
                
                # Setup
                conf_dict = config or {}
                await runner.setup(
                    num_agents=conf_dict.get("num_agents", 4),
                    grid_size=conf_dict.get("grid_size", 10),
                    config=conf_dict
                )
                
                # Hook callback
                if runner.engine:
                    runner.engine.on_step_callback = self.on_engine_step

                await runner.start()
                logger.info(f"Started session {session_id}")

            elif action == "stop":
                await runner.stop()
                # Optional: Remove from sessions if we want fresh state next time
                # del self.sessions[session_id] 
                logger.info(f"Stopped session {session_id}")
            
            elif action == "pause":
                await runner.pause()
                logger.info(f"Paused session {session_id}")
            
            elif action == "resume":
                await runner.resume()
                logger.info(f"Resumed session {session_id}")
            
            else:
                raise ValueError(f"Unknown action: {action}")
            
            return {"status": runner.status, "is_running": runner.is_running}


    async def on_engine_step(self, update: Dict[str, Any]):
        """Broadcasts updates to all connected clients."""
        await self.connection_manager.broadcast(update)

session_manager = SessionManager()

@app.websocket("/ws/state")
async def websocket_endpoint(websocket: WebSocket):
    await session_manager.connect_ws(websocket)
    try:
        while True:
            # Keep connection alive, listen for client cmds if any (ping/pong)
            await websocket.receive_text()
    except WebSocketDisconnect:
        session_manager.disconnect_ws(websocket)
    except Exception:
        session_manager.disconnect_ws(websocket)

@app.post("/api/sim/start")
async def start_sim(config: SimConfig):
    # Legacy wrapper
    await session_manager.control_session("default", "start", config.dict())
    return {"status": "started", "session_id": "default", "config": config}

@app.post("/api/sim/stop")
async def stop_sim():
    # Legacy wrapper
    await session_manager.control_session("default", "stop")
    return {"status": "stopped"}

class ControlRequest(BaseModel):
    action: str # start, stop, pause, resume
    config: Optional[SimConfig] = None

@app.post("/api/v1/sim/control")
async def control_sim(req: ControlRequest):
    try:
        # If config is provided, convert to dict using model_dump for Pydantic v2
        conf_dict = req.config.model_dump() if req.config else {}
        result = await session_manager.control_session("default", req.action, conf_dict)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/sim/state")
async def get_full_state():
    runner = await session_manager._get_or_create_runner("default")
    return await runner.get_snapshot()

@app.get("/api/sim/status")
async def get_status():
    if "default" not in session_manager.sessions:
        return {"status": "NOT_CREATED"}
    
    runner = session_manager.sessions["default"]
    return {
        "status": runner.status,
        "is_running": runner.is_running,
        "error": runner.error_message
    }

# Serve UI (Mount last to avoid shadowing API routes)
from fastapi.staticfiles import StaticFiles
import os
if os.path.exists("ui"):
    app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
else:
    logger.warning("UI directory not found. Dashboard will not be available.")
