import json
import time
from typing import List, Dict, Any
from ..core.ontology import Agent, Asset, Goal, GovernanceStandard, FaultType

class DossierGenerator:
    """
    The Legal Translation Layer.
    Translates technical simulation traces into the Pre-Incident Risk Dossier (PIRD).
    Primary Purpose: Proving Foreseeability and Preventability for stakeholders.
    """
    
    def __init__(self, agent: Agent, assets: List[Asset], goals: List[Goal], standard: GovernanceStandard):
        self.agent = agent
        self.assets = assets
        self.goals = goals
        self.standard = standard
        self.incidents = []

    def process_technical_event(self, event: Dict[str, Any]):
        """
        Maps a technical RiskEvent to a human-readable Incident with Fault Attribution.
        """
        violation = event.get("violation", {})
        rule = violation.get("rule", "UNKNOWN_PROTOCOL_DEVIATION")
        is_latency_correlated = event.get("is_latency_correlated", False)
        duration = event.get("step_duration", 0.0)
        
        # Conservative Fault Attribution Logic
        fault_type = FaultType.UNDETERMINED
        preventability_narrative = "Analysis inconclusive."
        preventability_score = 0.0
        
        if is_latency_correlated:
            # PROVEN PREVENTABILITY: Stress exceeded ODD
            fault_type = FaultType.ENVIRONMENTAL_STRESS
            preventability_narrative = (
                f"DEMONSTRABLY PREVENTABLE. The failure was a direct result of environmental stress "
                f"({duration:.3f}s latency) which exceeded the Operational Design Domain (ODD)."
            )
            preventability_score = 0.95 # Conservative confidence
        elif "NEGATIVE" in rule or "CRITICAL" in rule:
            # LIKELY LOGIC DEFECT: Failed under normal conditions
            fault_type = FaultType.LOGIC_DEFECT
            preventability_narrative = (
                "POTENTIALLY PREVENTABLE. The agent entered a critical failure state without evidence "
                "of external stress, suggesting a logic defect or unhandled edge case."
            )
            preventability_score = 0.40
            
        incident = {
            "incident_id": f"INC-{int(time.time())}-{len(self.incidents)}",
            "timestamp_iso": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(event['timestamp'])),
            "fault_attribution": fault_type.value,
            "liability_exposure": self._estimate_liability(event),
            "preventability_analysis": {
                "score": preventability_score,
                "narrative": preventability_narrative
            },
            "evidence_anchors": event.get("evidence_anchors", [])
        }
        self.incidents.append(incident)

    def _estimate_liability(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Maps technical 'impact' to estimated USD exposure."""
        impact_score = event.get("impact", 0.0)
        total_valuation = sum(a.valuation_usd for a in self.assets)
        
        # Heuristic: Impact (0-100) maps to a % of total asset valuation
        # This is a 'conservative' estimate for insurance/risk discussions
        exposure_usd = (impact_score / 100.0) * (total_valuation * 0.15) 
        
        return {
            "estimated_loss_usd": round(exposure_usd, 2),
            "affected_assets": [a.id for a in self.assets]
        }

    def generate_pird(self) -> str:
        """Generates the final PIRD artifact in human-readable Markdown-style format."""
        report = []
        report.append("=" * 80)
        report.append(" AGENT FORGE: PRE-INCIDENT RISK DOSSIER (PIRD)")
        report.append(f" Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f" Security Rank: OFFICIAL / AUDIT-READY")
        report.append("=" * 80)
        
        report.append("\n[1.0] EXECUTIVE SUMMARY: Post-Incident Survival")
        report.append(f"Status: {'CRITICAL_VIOLATION' if self.incidents else 'COMPLIANT'}")
        report.append(f"Primary Agent: {self.agent.id} (v{self.agent.version})")
        report.append(f"Total Preventable Incidents: {len(self.incidents)}")
        
        report.append("\n[2.0] ASSET EXPOSURE & OBJECTIVES")
        for asset in self.assets:
            report.append(f"|-- Asset: {asset.id} (Valuation: ${asset.valuation_usd:,.2f})")
        for goal in self.goals:
            report.append(f"|-- Objective: {goal.description} (Criticality: {goal.criticality}/10)")

        report.append("\n[3.0] ANALYTICAL FINDINGS (EVIDENCE OF PREVENTABILITY)")
        if not self.incidents:
            report.append("|-- No preventable failures detected under current ODD parameters.")
        else:
            for inc in self.incidents:
                report.append(f"\nINCIDENT ID: {inc['incident_id']}")
                report.append(f"|-- Fault Attribution: {inc['fault_attribution']}")
                report.append(f"|-- Estimated Liability Exposure: ${inc['liability_exposure']['estimated_loss_usd']:,.2f}")
                report.append(f"|-- Preventability Score: {inc['preventability_analysis']['score']*100:.0f}%")
                report.append(f"|-- Forensic Narrative: {inc['preventability_analysis']['narrative']}")
                report.append("|-- Technical Evidence Anchors:")
                for anchor in inc['evidence_anchors']:
                    report.append(f"    - {anchor['signal_type']}: {anchor['measured_value']} {anchor['unit']}")

        report.append("\n" + "=" * 80)
        report.append(" END OF DOSSIER | PROOF OF PREVENTABILITY")
        report.append(" AGENT FORGE | THE SYSTEM OF RECORD FOR AUTONOMY")
        report.append("=" * 80)
        
        return "\n".join(report)
