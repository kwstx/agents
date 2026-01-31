// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use serde::{Deserialize, Serialize};

// Data structures matching Python backend
#[derive(Serialize, Deserialize, Debug)]
struct SimulationStatus {
    status: String,
    mode: String,
    uptime: String,
    events_logged: u32,
}

#[derive(Serialize, Deserialize, Debug)]
struct Agent {
    agent_id: String,
    #[serde(rename = "type")]
    agent_type: String,
    risk_score: i32,
    risk_level: String,
    battery: String,
    status: String,
}

#[derive(Serialize, Deserialize, Debug)]
struct Incident {
    incident_id: String,
    timestamp: String,
    agent_id: String,
    fault_type: String,
    preventability: i32,
    liability: i32,
}

#[derive(Serialize, Deserialize, Debug)]
struct RiskSummary {
    total_incidents: i32,
    highest_risk_agent: String,
    latest_event: String,
}

// Python backend URL (localhost)
const PYTHON_API_URL: &str = "http://127.0.0.1:8765";

// Tauri Commands
#[tauri::command]
async fn get_simulation_status() -> Result<SimulationStatus, String> {
    let url = format!("{}/api/status", PYTHON_API_URL);
    
    match reqwest::get(&url).await {
        Ok(response) => {
            match response.json::<SimulationStatus>().await {
                Ok(status) => Ok(status),
                Err(e) => Err(format!("Failed to parse status: {}", e)),
            }
        }
        Err(e) => {
            // If Python backend is not running, return default
            eprintln!("Python backend not available: {}", e);
            Ok(SimulationStatus {
                status: "NOT_RUNNING".to_string(),
                mode: "SEALED".to_string(),
                uptime: "00:00:00".to_string(),
                events_logged: 0,
            })
        }
    }
}

#[tauri::command]
async fn get_system_risk_score() -> Result<f64, String> {
    let url = format!("{}/api/risk", PYTHON_API_URL);
    
    match reqwest::get(&url).await {
        Ok(response) => {
            match response.json::<serde_json::Value>().await {
                Ok(data) => {
                    if let Some(score) = data.get("risk_score").and_then(|v| v.as_f64()) {
                        Ok(score)
                    } else {
                        Ok(0.0)
                    }
                }
                Err(_) => Ok(0.0),
            }
        }
        Err(_) => Ok(0.0),
    }
}

#[tauri::command]
async fn get_active_agents() -> Result<Vec<Agent>, String> {
    let url = format!("{}/api/agents", PYTHON_API_URL);
    
    match reqwest::get(&url).await {
        Ok(response) => {
            match response.json::<Vec<Agent>>().await {
                Ok(agents) => Ok(agents),
                Err(e) => Err(format!("Failed to parse agents: {}", e)),
            }
        }
        Err(_) => {
            // Return empty list if backend not available
            Ok(Vec::new())
        }
    }
}

#[tauri::command]
async fn get_incidents() -> Result<Vec<Incident>, String> {
    let url = format!("{}/api/incidents", PYTHON_API_URL);
    
    match reqwest::get(&url).await {
        Ok(response) => {
            match response.json::<Vec<Incident>>().await {
                Ok(incidents) => Ok(incidents),
                Err(e) => Err(format!("Failed to parse incidents: {}", e)),
            }
        }
        Err(_) => {
            Ok(Vec::new())
        }
    }
}

#[tauri::command]
async fn get_risk_summary() -> Result<RiskSummary, String> {
    let url = format!("{}/api/risk-summary", PYTHON_API_URL);
    
    match reqwest::get(&url).await {
        Ok(response) => {
            match response.json::<RiskSummary>().await {
                Ok(summary) => Ok(summary),
                Err(e) => Err(format!("Failed to parse summary: {}", e)),
            }
        }
        Err(_) => {
            Ok(RiskSummary {
                total_incidents: 0,
                highest_risk_agent: "None".to_string(),
                latest_event: "No events".to_string(),
            })
        }
    }
}

#[tauri::command]
async fn get_incident_details(incident_id: String) -> Result<String, String> {
    let url = format!("{}/api/incidents/{}", PYTHON_API_URL, incident_id);
    
    match reqwest::get(&url).await {
        Ok(response) => {
            match response.text().await {
                Ok(details) => Ok(details),
                Err(e) => Err(format!("Failed to get details: {}", e)),
            }
        }
        Err(e) => Err(format!("Backend error: {}", e)),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_simulation_status,
            get_system_risk_score,
            get_active_agents,
            get_incidents,
            get_risk_summary,
            get_incident_details,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
