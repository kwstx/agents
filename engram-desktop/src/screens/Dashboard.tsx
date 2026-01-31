import React, { useState, useEffect } from 'react';
import { tauriAPI, SimulationStatus, Agent, RiskSummary } from '../services/tauri-api';
import './Dashboard.css';

const Dashboard: React.FC = () => {
    const [status, setStatus] = useState<SimulationStatus>({
        status: "Initializing...",
        mode: "SEALED",
        uptime: "00:00:00",
        events_logged: 0,
    });
    const [riskScore, setRiskScore] = useState<number>(0);
    const [agents, setAgents] = useState<Agent[]>([]);
    const [riskSummary, setRiskSummary] = useState<RiskSummary>({
        total_incidents: 0,
        highest_risk_agent: "None",
        latest_event: "No events",
    });

    const loadData = async () => {
        try {
            const [statusData, risk, agentsData, summary] = await Promise.all([
                tauriAPI.getSimulationStatus(),
                tauriAPI.getSystemRiskScore(),
                tauriAPI.getActiveAgents(),
                tauriAPI.getRiskSummary(),
            ]);

            setStatus(statusData);
            setRiskScore(risk);
            setAgents(agentsData);
            setRiskSummary(summary);
        } catch (error) {
            console.error("Failed to load data:", error);
        }
    };

    useEffect(() => {
        loadData();
        const interval = setInterval(loadData, 1000);
        return () => clearInterval(interval);
    }, []);

    const getRiskClass = (score: number): string => {
        if (score >= 100) return "risk-critical";
        if (score >= 50) return "risk-high";
        if (score >= 20) return "risk-medium";
        return "risk-low";
    };

    return (
        <div className="dashboard-screen">
            <div className="screen-header">
                <h1>Dashboard</h1>
                <p className="screen-subtitle">Real-time System Overview</p>
            </div>

            <div className="dashboard-grid">
                {/* Simulation Status Panel */}
                <div className="panel">
                    <div className="panel-header">SIMULATION STATUS</div>
                    <div className="panel-content">
                        <p>
                            Status: <span className="status-badge">{status.status}</span>
                        </p>
                        <p>Mode: {status.mode}</p>
                        <p>Uptime: {status.uptime}</p>
                        <p>Events Logged: {status.events_logged}</p>
                    </div>
                </div>

                {/* Risk Overview Panel */}
                <div className="panel">
                    <div className="panel-header">RISK OVERVIEW</div>
                    <div className="panel-content">
                        <p>
                            System Risk Score:{" "}
                            <span className={getRiskClass(riskScore)}>{riskScore.toFixed(0)}</span>
                        </p>
                        <p>Total Incidents: {riskSummary.total_incidents}</p>
                        <p>Highest Risk Agent: {riskSummary.highest_risk_agent}</p>
                        <p>Latest Event: {riskSummary.latest_event}</p>
                    </div>
                </div>

                {/* Active Agents Table */}
                <div className="panel full-width">
                    <div className="panel-header">ACTIVE AGENTS</div>
                    <div className="panel-content">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Agent ID</th>
                                    <th>Type</th>
                                    <th>Risk</th>
                                    <th>Battery</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {agents.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} style={{ textAlign: "center", color: "#888" }}>
                                            No active agents
                                        </td>
                                    </tr>
                                ) : (
                                    agents.map((agent) => (
                                        <tr key={agent.agent_id}>
                                            <td>{agent.agent_id}</td>
                                            <td>{agent.type}</td>
                                            <td>
                                                <span className={getRiskClass(agent.risk_score)}>
                                                    {agent.risk_score} [{agent.risk_level}]
                                                </span>
                                            </td>
                                            <td>{agent.battery}</td>
                                            <td>{agent.status}</td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
