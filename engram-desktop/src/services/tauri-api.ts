/**
 * Tauri API Service
 * Wrapper for calling Rust commands from React
 */

import { invoke } from '@tauri-apps/api/core';

// Type definitions matching Rust structs
export interface SimulationStatus {
    status: string;
    mode: string;
    uptime: string;
    events_logged: number;
}

export interface Agent {
    agent_id: string;
    type: string;
    risk_score: number;
    risk_level: string;
    battery: string;
    status: string;
}

export interface Incident {
    incident_id: string;
    timestamp: string;
    agent_id: string;
    fault_type: string;
    preventability: number;
    liability: number;
}

export interface RiskSummary {
    total_incidents: number;
    highest_risk_agent: string;
    latest_event: string;
}

/**
 * Tauri API - Calls Rust commands which call Python backend
 */
export const tauriAPI = {
    /**
     * Get current simulation status
     */
    getSimulationStatus: async (): Promise<SimulationStatus> => {
        try {
            return await invoke<SimulationStatus>('get_simulation_status');
        } catch (error) {
            console.error('Failed to get simulation status:', error);
            return {
                status: 'ERROR',
                mode: 'SEALED',
                uptime: '00:00:00',
                events_logged: 0,
            };
        }
    },

    /**
     * Get system-wide risk score
     */
    getSystemRiskScore: async (): Promise<number> => {
        try {
            return await invoke<number>('get_system_risk_score');
        } catch (error) {
            console.error('Failed to get risk score:', error);
            return 0;
        }
    },

    /**
     * Get list of active agents
     */
    getActiveAgents: async (): Promise<Agent[]> => {
        try {
            return await invoke<Agent[]>('get_active_agents');
        } catch (error) {
            console.error('Failed to get agents:', error);
            return [];
        }
    },

    /**
     * Get list of incidents
     */
    getIncidents: async (): Promise<Incident[]> => {
        try {
            return await invoke<Incident[]>('get_incidents');
        } catch (error) {
            console.error('Failed to get incidents:', error);
            return [];
        }
    },

    /**
     * Get risk summary statistics
     */
    getRiskSummary: async (): Promise<RiskSummary> => {
        try {
            return await invoke<RiskSummary>('get_risk_summary');
        } catch (error) {
            console.error('Failed to get risk summary:', error);
            return {
                total_incidents: 0,
                highest_risk_agent: 'None',
                latest_event: 'No events',
            };
        }
    },

    /**
     * Get detailed information for a specific incident
     */
    getIncidentDetails: async (incidentId: string): Promise<string> => {
        try {
            return await invoke<string>('get_incident_details', { incidentId });
        } catch (error) {
            console.error('Failed to get incident details:', error);
            return 'Failed to load incident details';
        }
    },
};
