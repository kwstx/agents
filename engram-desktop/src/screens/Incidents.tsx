import React, { useState, useEffect } from 'react';
import { tauriAPI, Incident } from '../services/tauri-api';
import './Incidents.css';

const Incidents: React.FC = () => {
    const [incidents, setIncidents] = useState<Incident[]>([]);
    const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
    const [incidentDetails, setIncidentDetails] = useState<string>("");
    const [searchTerm, setSearchTerm] = useState<string>("");
    const [filterType, setFilterType] = useState<string>("all");

    const loadIncidents = async () => {
        try {
            const data = await tauriAPI.getIncidents();
            setIncidents(data);
        } catch (error) {
            console.error("Failed to load incidents:", error);
        }
    };

    const loadIncidentDetails = async (incidentId: string) => {
        try {
            const details = await tauriAPI.getIncidentDetails(incidentId);
            setIncidentDetails(details);
        } catch (error) {
            console.error("Failed to load incident details:", error);
            setIncidentDetails("Failed to load details");
        }
    };

    useEffect(() => {
        loadIncidents();
        const interval = setInterval(loadIncidents, 2000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (selectedIncident) {
            loadIncidentDetails(selectedIncident.incident_id);
        }
    }, [selectedIncident]);

    const handleIncidentClick = (incident: Incident) => {
        setSelectedIncident(incident);
    };

    // Filter incidents
    const filteredIncidents = incidents.filter((incident) => {
        const matchesSearch =
            incident.incident_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
            incident.agent_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
            incident.fault_type.toLowerCase().includes(searchTerm.toLowerCase());

        const matchesFilter =
            filterType === "all" || incident.fault_type === filterType;

        return matchesSearch && matchesFilter;
    });

    // Get unique fault types for filter
    const faultTypes = Array.from(new Set(incidents.map((i) => i.fault_type)));

    const getSeverityClass = (preventability: number): string => {
        if (preventability >= 80) return "severity-critical";
        if (preventability >= 50) return "severity-high";
        if (preventability >= 20) return "severity-medium";
        return "severity-low";
    };

    return (
        <div className="incidents-screen">
            <div className="screen-header">
                <h1>Incidents</h1>
                <p className="screen-subtitle">Forensic Incident Log</p>
            </div>

            <div className="incidents-content">
                {/* Incidents Table */}
                <div className="incidents-table-panel">
                    <div className="panel">
                        <div className="panel-header">
                            <span>INCIDENT LOG ({filteredIncidents.length})</span>
                            <div className="panel-controls">
                                <input
                                    type="text"
                                    placeholder="Search incidents..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="search-input"
                                />
                                <select
                                    value={filterType}
                                    onChange={(e) => setFilterType(e.target.value)}
                                    className="filter-select"
                                >
                                    <option value="all">All Types</option>
                                    {faultTypes.map((type) => (
                                        <option key={type} value={type}>
                                            {type}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        <div className="panel-content">
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Incident ID</th>
                                        <th>Timestamp</th>
                                        <th>Agent</th>
                                        <th>Fault Type</th>
                                        <th>Preventability</th>
                                        <th>Liability</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredIncidents.length === 0 ? (
                                        <tr>
                                            <td colSpan={6} style={{ textAlign: "center", color: "#888" }}>
                                                No incidents found
                                            </td>
                                        </tr>
                                    ) : (
                                        filteredIncidents.map((incident) => (
                                            <tr
                                                key={incident.incident_id}
                                                onClick={() => handleIncidentClick(incident)}
                                                className={
                                                    selectedIncident?.incident_id === incident.incident_id
                                                        ? "selected"
                                                        : ""
                                                }
                                            >
                                                <td>{incident.incident_id}</td>
                                                <td>{incident.timestamp}</td>
                                                <td>{incident.agent_id}</td>
                                                <td>{incident.fault_type}</td>
                                                <td>
                                                    <span className={getSeverityClass(incident.preventability)}>
                                                        {incident.preventability}%
                                                    </span>
                                                </td>
                                                <td>
                                                    <span className={getSeverityClass(incident.liability)}>
                                                        {incident.liability}%
                                                    </span>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {/* Incident Details Panel */}
                <div className="incident-details-panel">
                    <div className="panel">
                        <div className="panel-header">INCIDENT DETAILS</div>
                        <div className="panel-content">
                            {selectedIncident ? (
                                <div className="incident-details">
                                    <div className="detail-section">
                                        <h3>Overview</h3>
                                        <p><strong>ID:</strong> {selectedIncident.incident_id}</p>
                                        <p><strong>Timestamp:</strong> {selectedIncident.timestamp}</p>
                                        <p><strong>Agent:</strong> {selectedIncident.agent_id}</p>
                                        <p><strong>Fault Type:</strong> {selectedIncident.fault_type}</p>
                                    </div>

                                    <div className="detail-section">
                                        <h3>Analysis</h3>
                                        <p>
                                            <strong>Preventability:</strong>{" "}
                                            <span className={getSeverityClass(selectedIncident.preventability)}>
                                                {selectedIncident.preventability}%
                                            </span>
                                        </p>
                                        <p>
                                            <strong>Liability:</strong>{" "}
                                            <span className={getSeverityClass(selectedIncident.liability)}>
                                                {selectedIncident.liability}%
                                            </span>
                                        </p>
                                    </div>

                                    <div className="detail-section">
                                        <h3>Forensic Narrative</h3>
                                        <pre className="narrative-text">{incidentDetails}</pre>
                                    </div>
                                </div>
                            ) : (
                                <p style={{ color: "#888", textAlign: "center", marginTop: "40px" }}>
                                    Select an incident to view details
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Incidents;
