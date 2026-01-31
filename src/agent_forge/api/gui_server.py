"""
FastAPI Server for Engram GUI
Provides REST API endpoints for Tauri to access simulation data
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agent_forge.ui.data_bridge import data_bridge
import uvicorn

app = FastAPI(title="Engram API", version="0.1.0")

# Allow localhost CORS for Tauri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
def get_status():
    """Get simulation status"""
    return data_bridge.get_simulation_status()


@app.get("/api/risk")
def get_risk():
    """Get system risk score"""
    return {"risk_score": data_bridge.get_system_risk_score()}


@app.get("/api/agents")
def get_agents():
    """Get active agents"""
    return data_bridge.get_active_agents()


@app.get("/api/incidents")
def get_incidents():
    """Get all incidents"""
    return data_bridge.get_incidents()


@app.get("/api/risk-summary")
def get_risk_summary():
    """Get risk summary statistics"""
    return data_bridge.get_risk_summary()


@app.get("/api/incidents/{incident_id}")
def get_incident_details(incident_id: str):
    """Get detailed information for a specific incident"""
    return data_bridge.get_incident_details(incident_id)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "engram-api"}


def start_server(host: str = "127.0.0.1", port: int = 8765):
    """Start the FastAPI server"""
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    print("Starting Engram API server on http://127.0.0.1:8765")
    start_server()
