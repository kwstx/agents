"""
Data bridge between SimulationEngine/RiskMonitor and TUI
Provides a singleton interface for TUI to access live simulation data
"""

from typing import Dict, List, Any, Optional
from agent_forge.core.engine import SimulationEngine
from agent_forge.core.risk import RiskMonitor
from agent_forge.forensics.dossier import DossierGenerator
from agent_forge.core.ontology import Agent, Asset, Goal, GovernanceStandard
import time


class SimulationDataBridge:
    """Singleton bridge for TUI to access simulation data"""
    
    _instance = None
    _engine: Optional[SimulationEngine] = None
    _dossier: Optional[DossierGenerator] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def set_engine(cls, engine: SimulationEngine):
        """Set the simulation engine instance"""
        cls._engine = engine
    
    @classmethod
    def set_dossier(cls, dossier: DossierGenerator):
        """Set the dossier generator instance"""
        cls._dossier = dossier
    
    @classmethod
    def get_simulation_status(cls) -> Dict[str, Any]:
        """Get current simulation status"""
        if not cls._engine:
            return {
                "status": "NOT_RUNNING",
                "mode": "SEALED",
                "uptime": "00:00:00",
                "events_logged": 0
            }
        
        # TODO: Track actual uptime
        return {
            "status": "RUNNING",
            "mode": "SEALED (No external connections)",
            "uptime": "00:15:32",  # TODO: Calculate from start time
            "events_logged": len(cls._engine.risk_monitor.history) if cls._engine.risk_monitor else 0
        }
    
    @classmethod
    def get_system_risk_score(cls) -> float:
        """Get overall system risk score"""
        if not cls._engine or not cls._engine.risk_monitor:
            return 0.0
        
        # Return highest agent risk
        if cls._engine.risk_monitor.agent_risk:
            return max(cls._engine.risk_monitor.agent_risk.values())
        return 0.0
    
    @classmethod
    def get_active_agents(cls) -> List[Dict[str, Any]]:
        """Get list of active agents with their current state"""
        if not cls._engine or not cls._engine.risk_monitor:
            # Return sample data if no engine
            return [
                {
                    "agent_id": "Logistics-Bot-01",
                    "type": "Warehouse",
                    "risk_score": 65,
                    "risk_level": "HIGH",
                    "battery": 42,
                    "status": "RUNNING"
                },
                {
                    "agent_id": "Logistics-Bot-02",
                    "type": "Warehouse",
                    "risk_score": 15,
                    "risk_level": "LOW",
                    "battery": 87,
                    "status": "RUNNING"
                }
            ]
        
        agents = []
        for agent_id, risk_score in cls._engine.risk_monitor.agent_risk.items():
            # Determine risk level
            if risk_score >= 100:
                risk_level = "CRITICAL"
            elif risk_score >= 50:
                risk_level = "HIGH"
            elif risk_score >= 20:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            # Try to get agent state
            battery = "N/A"
            status = "RUNNING"
            agent_type = "Unknown"
            
            if hasattr(cls._engine.env, 'get_agent_state'):
                try:
                    state = cls._engine.env.get_agent_state(agent_id)
                    if isinstance(state, dict):
                        battery = state.get('battery', 'N/A')
                        agent_type = state.get('type', 'Unknown')
                except:
                    pass
            
            agents.append({
                "agent_id": agent_id,
                "type": agent_type,
                "risk_score": int(risk_score),
                "risk_level": risk_level,
                "battery": battery,
                "status": status
            })
        
        return agents if agents else [
            {
                "agent_id": "No active agents",
                "type": "-",
                "risk_score": 0,
                "risk_level": "LOW",
                "battery": "-",
                "status": "IDLE"
            }
        ]
    
    @classmethod
    def get_risk_summary(cls) -> Dict[str, Any]:
        """Get risk summary statistics"""
        if not cls._engine or not cls._engine.risk_monitor:
            return {
                "total_incidents": 0,
                "highest_risk_agent": "None",
                "latest_event": "No events"
            }
        
        history = cls._engine.risk_monitor.history
        total_incidents = len(history)
        
        # Find highest risk agent
        highest_risk_agent = "None"
        highest_risk = 0
        if cls._engine.risk_monitor.agent_risk:
            for agent_id, score in cls._engine.risk_monitor.agent_risk.items():
                if score > highest_risk:
                    highest_risk = score
                    highest_risk_agent = f"{agent_id} ({int(score)})"
        
        # Get latest event
        latest_event = "No events"
        if history:
            last = history[-1]
            violation = last.get('violation', {})
            rule = violation.get('rule', 'Unknown')
            duration = last.get('step_duration', 0)
            latest_event = f"{rule} detected (t={duration:.1f}s)"
        
        return {
            "total_incidents": total_incidents,
            "highest_risk_agent": highest_risk_agent,
            "latest_event": latest_event
        }
    
    @classmethod
    def get_incidents(cls) -> List[Dict[str, Any]]:
        """Get all incidents from risk monitor"""
        if not cls._engine or not cls._engine.risk_monitor:
            # Return sample data
            return [
                {
                    "incident_id": "INC-001",
                    "timestamp": "15:23:12",
                    "agent_id": "Bot-01",
                    "fault_type": "ENV_STRESS",
                    "preventability": 95,
                    "liability": 2450
                }
            ]
        
        incidents = []
        for idx, event in enumerate(cls._engine.risk_monitor.history):
            # Determine fault type
            is_latency = event.get('is_latency_correlated', False)
            violation = event.get('violation', {})
            rule = violation.get('rule', 'UNKNOWN')
            
            if is_latency:
                fault_type = "ENV_STRESS"
                preventability = 95
            elif "NEGATIVE" in rule or "CRITICAL" in rule:
                fault_type = "LOGIC_DEFECT"
                preventability = 40
            else:
                fault_type = "UNDETERMINED"
                preventability = 50
            
            # Calculate liability (simple heuristic)
            impact = event.get('impact', 0)
            liability = int((impact / 100.0) * 10000)  # Scale to dollars
            
            timestamp = time.strftime('%H:%M:%S', time.localtime(event.get('timestamp', time.time())))
            
            incidents.append({
                "incident_id": f"INC-{idx+1:03d}",
                "timestamp": timestamp,
                "agent_id": event.get('agent_id', 'Unknown'),
                "fault_type": fault_type,
                "preventability": preventability,
                "liability": liability,
                "raw_event": event  # Keep for detail view
            })
        
        return incidents if incidents else []
    
    @classmethod
    def get_incident_details(cls, incident_id: str) -> str:
        """Get detailed forensic narrative for an incident"""
        # Extract incident index from ID
        try:
            idx = int(incident_id.split('-')[1]) - 1
            if cls._engine and cls._engine.risk_monitor:
                if idx < len(cls._engine.risk_monitor.history):
                    event = cls._engine.risk_monitor.history[idx]
                    return cls._format_incident_details(incident_id, event)
        except:
            pass
        
        # Fallback to sample
        return f"""
INCIDENT ID: {incident_id}
Timestamp: 2026-01-31T15:23:12Z
Agent: Logistics-Bot-01 (v2.1.0)

FAULT ATTRIBUTION: ENVIRONMENTAL_STRESS

PREVENTABILITY ANALYSIS:
Score: 95%
Narrative: DEMONSTRABLY PREVENTABLE. The failure was a direct 
result of environmental stress (1.512s latency) which exceeded 
the Operational Design Domain (ODD).

ESTIMATED LIABILITY EXPOSURE: $2,450.00
Affected Assets: Inventory-Item-42, Warehouse-Zone-A

TECHNICAL EVIDENCE ANCHORS:
- STEP_DURATION: 1.512 seconds
- BATTERY_DELTA: -8.3%
- NETWORK_JITTER: 450ms

GOVERNANCE STANDARD: Safety-Policy-v1.2
Rule Violated: PHYSICS_BATTERY_NEGATIVE

RECOMMENDED ACTION:
Adjust agent timeout threshold to 2.0s or reduce operational 
load during high-latency periods.
"""
    
    @classmethod
    def _format_incident_details(cls, incident_id: str, event: Dict[str, Any]) -> str:
        """Format event into detailed incident report"""
        violation = event.get('violation', {})
        rule = violation.get('rule', 'UNKNOWN')
        duration = event.get('step_duration', 0)
        is_latency = event.get('is_latency_correlated', False)
        impact = event.get('impact', 0)
        agent_id = event.get('agent_id', 'Unknown')
        timestamp_val = event.get('timestamp', time.time())
        timestamp_str = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(timestamp_val))
        
        fault_type = "ENVIRONMENTAL_STRESS" if is_latency else "LOGIC_DEFECT"
        preventability = 95 if is_latency else 40
        
        narrative = ""
        if is_latency:
            narrative = f"DEMONSTRABLY PREVENTABLE. The failure was a direct result of environmental stress ({duration:.3f}s latency) which exceeded the Operational Design Domain (ODD)."
        else:
            narrative = "POTENTIALLY PREVENTABLE. The agent entered a critical failure state without evidence of external stress, suggesting a logic defect or unhandled edge case."
        
        liability = int((impact / 100.0) * 10000)
        
        evidence_anchors = event.get('evidence_anchors', [])
        evidence_str = "\n".join([f"- {a['signal_type']}: {a['measured_value']} {a['unit']}" for a in evidence_anchors])
        if not evidence_str:
            evidence_str = f"- STEP_DURATION: {duration:.3f} seconds"
        
        return f"""
INCIDENT ID: {incident_id}
Timestamp: {timestamp_str}
Agent: {agent_id}

FAULT ATTRIBUTION: {fault_type}

PREVENTABILITY ANALYSIS:
Score: {preventability}%
Narrative: {narrative}

ESTIMATED LIABILITY EXPOSURE: ${liability:,.2f}

TECHNICAL EVIDENCE ANCHORS:
{evidence_str}

GOVERNANCE STANDARD: Safety-Policy-v1.2
Rule Violated: {rule}

CAUSAL CHAIN:
{chr(10).join(event.get('causal_chain', ['No causal chain available']))}
"""


# Global singleton instance
data_bridge = SimulationDataBridge()
