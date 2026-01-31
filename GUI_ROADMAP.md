# ENGRAM NATIVE GUI - IMPLEMENTATION ROADMAP

## STRATEGIC OVERVIEW

**Objective**: Build a professional, Bloomberg Terminal-inspired native desktop application using Tauri that maintains the "local-first, sealed system" positioning while providing superior visual clarity and information density.

**Technology Stack**: Tauri + React + Python Backend
**Timeline**: 2-3 weeks for full implementation
**Philosophy**: "Professional = Information Density + Visual Clarity + Local Control"

---

## WHY TAURI (NOT ELECTRON)

### **Tauri Advantages**:
1. **Smaller Binary**: 10-40MB vs Electron's 100-200MB
2. **Native WebView**: Uses system browser (Edge on Windows) instead of bundling Chromium
3. **Better Performance**: Lower memory footprint, faster startup
4. **Rust Backend**: More secure, better for local-first positioning
5. **True Native Feel**: Integrates better with OS

### **Tauri Architecture**:
```
Engram Desktop App
├── Tauri (Rust) - Window management, IPC, system integration
├── React UI - Frontend (reuse existing dashboard)
├── Python Backend - SimulationEngine, RiskMonitor, Justice Log
└── Local SQLite + JSONL - Data storage
```

---

## PHASE 1: TAURI SETUP & PROJECT STRUCTURE (Days 1-2)

### 1.1 Install Tauri Prerequisites

**Windows Requirements**:
- Node.js (already installed)
- Rust (install via rustup)
- Visual Studio Build Tools (for Rust compilation)

**Installation Steps**:
```bash
# Install Rust
winget install --id Rustlang.Rustup

# Verify installation
rustc --version
cargo --version

# Install Tauri CLI
cargo install tauri-cli
```

### 1.2 Create Tauri Project

**Initialize Tauri App**:
```bash
cd c:\Users\galan\potion\agent_forge_mvp
npm create tauri-app@latest
```

**Configuration Choices**:
- Project name: `engram-desktop`
- Frontend framework: `React + TypeScript`
- Package manager: `npm`
- UI template: `React with Vite`

**Expected Structure**:
```
engram-desktop/
├── src-tauri/          # Rust backend
│   ├── src/
│   │   └── main.rs     # Tauri entry point
│   ├── Cargo.toml      # Rust dependencies
│   └── tauri.conf.json # Tauri configuration
├── src/                # React frontend
│   ├── App.tsx
│   ├── main.tsx
│   └── components/
├── package.json
└── vite.config.ts
```

### 1.3 Configure Tauri for Local-First

**Edit `src-tauri/tauri.conf.json`**:
```json
{
  "build": {
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build",
    "devPath": "http://localhost:5173",
    "distDir": "../dist"
  },
  "package": {
    "productName": "Engram",
    "version": "0.1.0"
  },
  "tauri": {
    "allowlist": {
      "all": false,  // Deny all by default (security)
      "fs": {
        "all": false,
        "readFile": true,
        "writeFile": true,
        "scope": ["$APPDATA/engram/*"]  // Restrict file access
      },
      "shell": {
        "all": false,
        "execute": false  // No shell commands
      },
      "http": {
        "all": false,
        "request": false  // No HTTP requests (local-first)
      }
    },
    "windows": [
      {
        "title": "Engram - The Black Box Flight Recorder",
        "width": 1600,
        "height": 1000,
        "resizable": true,
        "fullscreen": false,
        "decorations": true,
        "center": true
      }
    ],
    "security": {
      "csp": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    }
  }
}
```

**Key Security Settings**:
- ❌ No HTTP requests allowed
- ❌ No shell execution
- ✅ File access restricted to app data folder
- ✅ Content Security Policy enforced

### 1.4 Integrate Python Backend

**Challenge**: Tauri is Rust-based, but our backend is Python.

**Solution**: Bundle Python as a subprocess or use Rust-Python bridge.

**Option A: Python Subprocess (Simpler)**:
1. Bundle Python interpreter with app
2. Start Python backend on app launch
3. Communicate via IPC (stdin/stdout or local socket)

**Option B: PyO3 (More Complex, Better Performance)**:
1. Use PyO3 to embed Python in Rust
2. Call Python functions directly from Rust
3. No separate process needed

**Recommendation**: Start with **Option A** (subprocess) for speed, migrate to PyO3 if needed.

**Implementation (Option A)**:
```rust
// src-tauri/src/main.rs
use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader};

fn start_python_backend() -> std::process::Child {
    Command::new("python")
        .arg("src/agent_forge/api/server.py")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to start Python backend")
}

fn main() {
    // Start Python backend
    let mut backend = start_python_backend();
    
    // Start Tauri app
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
    
    // Cleanup: kill backend on exit
    backend.kill().expect("Failed to kill backend");
}
```

---

## PHASE 2: REACT UI MIGRATION (Days 3-5)

### 2.1 Migrate Existing React Dashboard

**Current React UI**: `ui/` directory (from FastAPI web app)

**Migration Steps**:
1. Copy React components to `engram-desktop/src/components/`
2. Update imports and paths
3. Remove FastAPI/WebSocket dependencies
4. Replace with Tauri IPC

**Component Structure**:
```
src/
├── components/
│   ├── Dashboard/
│   │   ├── Dashboard.tsx
│   │   ├── RiskMeter.tsx
│   │   ├── AgentTable.tsx
│   │   └── StatusPanel.tsx
│   ├── Incidents/
│   │   ├── IncidentLog.tsx
│   │   ├── IncidentDetail.tsx
│   │   └── IncidentFilters.tsx
│   ├── Export/
│   │   ├── ExportPanel.tsx
│   │   ├── PIRDPreview.tsx
│   │   └── AuditLog.tsx
│   ├── Lineage/
│   │   └── LineageGraph.tsx
│   └── Layout/
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       └── Footer.tsx
├── services/
│   └── tauri-api.ts  // Tauri IPC wrapper
├── types/
│   └── index.ts      // TypeScript types
├── App.tsx
└── main.tsx
```

### 2.2 Create Tauri IPC Service

**File**: `src/services/tauri-api.ts`

```typescript
import { invoke } from '@tauri-apps/api/tauri';

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
  battery: number | string;
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

// Tauri IPC calls
export const tauriAPI = {
  // Simulation
  getSimulationStatus: (): Promise<SimulationStatus> => 
    invoke('get_simulation_status'),
  
  getSystemRiskScore: (): Promise<number> => 
    invoke('get_system_risk_score'),
  
  // Agents
  getActiveAgents: (): Promise<Agent[]> => 
    invoke('get_active_agents'),
  
  // Incidents
  getIncidents: (): Promise<Incident[]> => 
    invoke('get_incidents'),
  
  getIncidentDetails: (incidentId: string): Promise<string> => 
    invoke('get_incident_details', { incidentId }),
  
  // PIRD Export
  generatePIRD: (): Promise<string> => 
    invoke('generate_pird'),
  
  exportPIRD: (path: string, content: string): Promise<void> => 
    invoke('export_pird', { path, content }),
  
  // Justice Log
  verifyLogs: (): Promise<{ valid: boolean; message: string }> => 
    invoke('verify_logs'),
  
  sealLogs: (): Promise<any> => 
    invoke('seal_logs'),
};
```

### 2.3 Implement Tauri Commands (Rust Side)

**File**: `src-tauri/src/main.rs`

```rust
use tauri::command;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct SimulationStatus {
    status: String,
    mode: String,
    uptime: String,
    events_logged: u32,
}

#[command]
fn get_simulation_status() -> SimulationStatus {
    // Call Python backend via IPC or PyO3
    // For now, return mock data
    SimulationStatus {
        status: "RUNNING".to_string(),
        mode: "SEALED".to_string(),
        uptime: "00:15:32".to_string(),
        events_logged: 42,
    }
}

#[command]
fn get_system_risk_score() -> f64 {
    // Call Python backend
    45.0
}

// ... more commands for agents, incidents, PIRD, etc.

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_simulation_status,
            get_system_risk_score,
            // ... register all commands
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### 2.4 Connect React to Tauri IPC

**Example: Dashboard Component**

```typescript
// src/components/Dashboard/Dashboard.tsx
import { useEffect, useState } from 'react';
import { tauriAPI, SimulationStatus, Agent } from '../../services/tauri-api';
import RiskMeter from './RiskMeter';
import AgentTable from './AgentTable';

export default function Dashboard() {
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [riskScore, setRiskScore] = useState<number>(0);
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    // Initial load
    loadData();
    
    // Auto-refresh every second
    const interval = setInterval(loadData, 1000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    const [statusData, risk, agentsData] = await Promise.all([
      tauriAPI.getSimulationStatus(),
      tauriAPI.getSystemRiskScore(),
      tauriAPI.getActiveAgents(),
    ]);
    
    setStatus(statusData);
    setRiskScore(risk);
    setAgents(agentsData);
  };

  return (
    <div className="dashboard">
      <div className="status-panel">
        <h2>Simulation Status</h2>
        <p>Status: {status?.status}</p>
        <p>Mode: {status?.mode}</p>
        <p>Events: {status?.events_logged}</p>
      </div>
      
      <RiskMeter score={riskScore} />
      
      <AgentTable agents={agents} />
    </div>
  );
}
```

---

## PHASE 3: BLOOMBERG-STYLE UI DESIGN (Days 6-8)

### 3.1 Design System

**Color Palette** (Bloomberg-inspired):
```css
:root {
  /* Background */
  --bg-primary: #000000;
  --bg-secondary: #0a0a0a;
  --bg-panel: #1a1a1a;
  
  /* Text */
  --text-primary: #ffffff;
  --text-secondary: #cccccc;
  --text-muted: #888888;
  
  /* Accent */
  --accent-blue: #0066cc;
  --accent-orange: #ff6600;
  
  /* Risk Colors */
  --risk-low: #00cc66;
  --risk-medium: #ffcc00;
  --risk-high: #ff6600;
  --risk-critical: #ff00ff;
  
  /* Borders */
  --border-color: #333333;
}
```

**Typography**:
- Primary Font: `'Roboto Mono', monospace` (data-dense, professional)
- Fallback: `'Courier New', monospace`
- Sizes: 12px (body), 14px (headers), 10px (labels)

**Layout Principles**:
1. **Multi-Panel Layout**: Show 4-6 panels simultaneously
2. **Fixed Headers**: Panel titles always visible
3. **Scrollable Content**: Each panel scrolls independently
4. **Resizable Panels**: Users can adjust panel sizes
5. **No Wasted Space**: Every pixel serves a purpose

### 3.2 Dashboard Layout

**Grid Structure** (CSS Grid):
```css
.dashboard {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: auto 1fr 1fr;
  gap: 8px;
  height: 100vh;
  padding: 8px;
  background: var(--bg-primary);
}

.header {
  grid-column: 1 / -1;
  height: 60px;
}

.risk-panel {
  grid-column: 1 / 2;
  grid-row: 2 / 3;
}

.status-panel {
  grid-column: 2 / 3;
  grid-row: 2 / 3;
}

.alerts-panel {
  grid-column: 3 / 3;
  grid-row: 2 / 3;
}

.agents-table {
  grid-column: 1 / -1;
  grid-row: 3 / 4;
}
```

**Visual Mockup**:
```
┌─────────────────────────────────────────────────────────────┐
│ ENGRAM - The Black Box Flight Recorder    [SEALED] 15:32:45 │
├──────────────────┬──────────────────┬───────────────────────┤
│ RISK OVERVIEW    │ SIMULATION       │ CRITICAL ALERTS       │
│                  │ STATUS           │                       │
│ System: 65 [HIGH]│ Running ✓        │ • Battery -5% (t=1.5s)│
│ ████████░░░░ 65% │ Uptime: 00:15:32 │ • Latency spike       │
│                  │ Events: 1,247    │ • Agent halted        │
│ Highest Risk:    │ Mode: SEALED     │                       │
│ Bot-01 (65)      │                  │                       │
├──────────────────┴──────────────────┴───────────────────────┤
│ ACTIVE AGENTS                                                │
│ ┌────────────┬─────────┬──────┬─────────┬────────┐          │
│ │ Agent ID   │ Type    │ Risk │ Battery │ Status │          │
│ ├────────────┼─────────┼──────┼─────────┼────────┤          │
│ │ Bot-01     │ Warehouse│ 65  │ 42%     │ RUNNING│          │
│ │ Bot-02     │ Warehouse│ 15  │ 87%     │ RUNNING│          │
│ └────────────┴─────────┴──────┴─────────┴────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Component Library

**Build Reusable Components**:

1. **Panel** - Container with header and content
2. **DataTable** - Sortable, filterable table
3. **RiskMeter** - Visual risk gauge
4. **StatusBadge** - Color-coded status indicator
5. **Chart** - Time-series line chart (using Chart.js or Recharts)
6. **Modal** - For detailed views
7. **Button** - Consistent button styling
8. **Input** - Form inputs

**Example: Panel Component**:
```typescript
// src/components/Layout/Panel.tsx
interface PanelProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

export default function Panel({ title, children, className }: PanelProps) {
  return (
    <div className={`panel ${className}`}>
      <div className="panel-header">{title}</div>
      <div className="panel-content">{children}</div>
    </div>
  );
}
```

```css
/* Panel styles */
.panel {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  background: var(--accent-blue);
  color: var(--text-primary);
  padding: 8px 12px;
  font-weight: bold;
  font-size: 12px;
  text-transform: uppercase;
  border-bottom: 1px solid var(--border-color);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}
```

---

## PHASE 4: PYTHON-RUST BRIDGE (Days 9-11)

### 4.1 IPC Architecture

**Challenge**: Rust (Tauri) needs to call Python (SimulationEngine, Justice Log, etc.)

**Solution Options**:

#### **Option A: HTTP/WebSocket (Simplest)**
- Start Python FastAPI server on localhost
- Tauri makes HTTP requests to `http://127.0.0.1:8000`
- ❌ **Problem**: Violates "no network" policy in `tauri.conf.json`
- ✅ **Fix**: Allow localhost-only HTTP in config

#### **Option B: Named Pipes / Unix Sockets (Better)**
- Python writes to named pipe
- Rust reads from named pipe
- ✅ True local IPC, no network
- ❌ More complex to implement

#### **Option C: Embedded Python (PyO3) (Best, Most Complex)**
- Embed Python interpreter in Rust
- Call Python functions directly
- ✅ No separate process, fastest
- ❌ Requires PyO3 setup, more complex build

**Recommendation**: Start with **Option A** (localhost HTTP), migrate to **Option C** (PyO3) later.

### 4.2 Implement Localhost HTTP Bridge

**Step 1: Allow Localhost in Tauri**

Edit `src-tauri/tauri.conf.json`:
```json
{
  "tauri": {
    "allowlist": {
      "http": {
        "all": false,
        "request": true,
        "scope": ["http://localhost:*", "http://127.0.0.1:*"]
      }
    }
  }
}
```

**Step 2: Start Python Backend on App Launch**

```rust
// src-tauri/src/main.rs
use std::process::{Command, Stdio};

fn start_python_backend() -> std::process::Child {
    Command::new("python")
        .arg("-m")
        .arg("uvicorn")
        .arg("agent_forge.api.server:app")
        .arg("--host")
        .arg("127.0.0.1")
        .arg("--port")
        .arg("8765")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .expect("Failed to start Python backend")
}

fn main() {
    let mut backend = start_python_backend();
    
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![/* commands */])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
    
    backend.kill().expect("Failed to kill backend");
}
```

**Step 3: Tauri Commands Call Python API**

```rust
use reqwest;

#[command]
async fn get_simulation_status() -> Result<SimulationStatus, String> {
    let response = reqwest::get("http://127.0.0.1:8765/api/status")
        .await
        .map_err(|e| e.to_string())?
        .json::<SimulationStatus>()
        .await
        .map_err(|e| e.to_string())?;
    
    Ok(response)
}
```

**Step 4: Update Python API**

Ensure `src/agent_forge/api/server.py` has all necessary endpoints:
```python
from fastapi import FastAPI
from agent_forge.ui.data_bridge import data_bridge

app = FastAPI()

@app.get("/api/status")
def get_status():
    return data_bridge.get_simulation_status()

@app.get("/api/risk")
def get_risk():
    return {"risk_score": data_bridge.get_system_risk_score()}

@app.get("/api/agents")
def get_agents():
    return data_bridge.get_active_agents()

@app.get("/api/incidents")
def get_incidents():
    return data_bridge.get_incidents()

# ... more endpoints
```

### 4.3 Bundle Python with Tauri

**Challenge**: Users won't have Python installed.

**Solution**: Bundle Python interpreter with the app.

**Tools**:
- **PyInstaller**: Freeze Python app into executable
- **PyOxidizer**: Embed Python in Rust binary (advanced)

**Approach**:
1. Use PyInstaller to create standalone Python executable
2. Include in Tauri bundle
3. Launch bundled Python instead of system Python

**Build Script**:
```bash
# Build Python backend
pyinstaller --onefile src/agent_forge/api/server.py

# Copy to Tauri resources
cp dist/server.exe src-tauri/resources/
```

**Update Tauri to use bundled Python**:
```rust
use tauri::api::path::resource_dir;

fn start_python_backend() -> std::process::Child {
    let resource_path = resource_dir(&tauri::generate_context!().config())
        .expect("Failed to get resource dir");
    
    let python_exe = resource_path.join("server.exe");
    
    Command::new(python_exe)
        .spawn()
        .expect("Failed to start Python backend")
}
```

---

## PHASE 5: ADVANCED FEATURES (Days 12-14)

### 5.1 Multi-Panel Layouts with Resizing

**Use React Grid Layout**:
```bash
npm install react-grid-layout
```

**Implementation**:
```typescript
import GridLayout from 'react-grid-layout';

const layout = [
  { i: 'risk', x: 0, y: 0, w: 4, h: 2 },
  { i: 'status', x: 4, y: 0, w: 4, h: 2 },
  { i: 'agents', x: 0, y: 2, w: 12, h: 4 },
];

<GridLayout layout={layout} cols={12} rowHeight={30}>
  <div key="risk"><RiskPanel /></div>
  <div key="status"><StatusPanel /></div>
  <div key="agents"><AgentTable /></div>
</GridLayout>
```

### 5.2 Real-Time Charts

**Use Recharts for Time-Series**:
```bash
npm install recharts
```

**Risk Timeline Chart**:
```typescript
import { LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts';

export default function RiskTimeline({ data }) {
  return (
    <LineChart width={600} height={300} data={data}>
      <CartesianGrid strokeDasharray="3 3" stroke="#333" />
      <XAxis dataKey="time" stroke="#ccc" />
      <YAxis stroke="#ccc" />
      <Line type="monotone" dataKey="risk" stroke="#ff6600" strokeWidth={2} />
    </LineChart>
  );
}
```

### 5.3 Keyboard Shortcuts

**Use React Hotkeys**:
```bash
npm install react-hotkeys-hook
```

**Implementation**:
```typescript
import { useHotkeys } from 'react-hotkeys-hook';

export default function App() {
  useHotkeys('ctrl+d', () => navigate('/dashboard'));
  useHotkeys('ctrl+i', () => navigate('/incidents'));
  useHotkeys('ctrl+e', () => navigate('/export'));
  useHotkeys('ctrl+q', () => window.close());
  
  return <Router>...</Router>;
}
```

### 5.4 Export to PDF

**Use jsPDF**:
```bash
npm install jspdf
```

**Implementation**:
```typescript
import jsPDF from 'jspdf';

export function exportPIRDtoPDF(content: string, filename: string) {
  const doc = new jsPDF();
  doc.setFont('courier');
  doc.setFontSize(10);
  
  const lines = doc.splitTextToSize(content, 180);
  doc.text(lines, 10, 10);
  
  doc.save(filename);
}
```

---

## PHASE 6: PACKAGING & DISTRIBUTION (Days 15-16)

### 6.1 Build for Production

**Build Command**:
```bash
npm run tauri build
```

**Output**:
- Windows: `.exe` installer + `.msi` installer
- macOS: `.dmg` + `.app`
- Linux: `.deb` + `.AppImage`

**Build Configuration** (`src-tauri/tauri.conf.json`):
```json
{
  "tauri": {
    "bundle": {
      "identifier": "com.engram.desktop",
      "icon": [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/icon.ico"
      ],
      "resources": ["resources/*"],
      "externalBin": [],
      "copyright": "© 2026 Engram",
      "category": "Utility",
      "shortDescription": "The Black Box Flight Recorder for Autonomous Systems",
      "longDescription": "Engram is a local-first, forensic-grade system for proving preventability of autonomous agent failures.",
      "windows": {
        "certificateThumbprint": null,
        "digestAlgorithm": "sha256",
        "timestampUrl": ""
      }
    }
  }
}
```

### 6.2 Code Signing (Optional but Recommended)

**Windows**:
- Get code signing certificate
- Sign `.exe` with `signtool`

**macOS**:
- Get Apple Developer certificate
- Sign `.app` with `codesign`
- Notarize with Apple

### 6.3 Auto-Updates (Optional)

**Use Tauri Updater**:
```json
{
  "tauri": {
    "updater": {
      "active": true,
      "endpoints": [
        "https://releases.engram.com/{{target}}/{{current_version}}"
      ],
      "dialog": true,
      "pubkey": "YOUR_PUBLIC_KEY"
    }
  }
}
```

---

## PHASE 7: TESTING & POLISH (Days 17-18)

### 7.1 Testing Checklist

**Functional Tests**:
- [ ] Dashboard loads with live data
- [ ] Incidents screen displays correctly
- [ ] Export generates valid PIRD
- [ ] Justice Log verification works
- [ ] All keyboard shortcuts work
- [ ] Panels resize correctly
- [ ] Charts update in real-time

**Performance Tests**:
- [ ] App starts in < 3 seconds
- [ ] UI remains responsive with 1000+ incidents
- [ ] Memory usage < 200MB
- [ ] CPU usage < 10% when idle

**Security Tests**:
- [ ] No external network calls (except localhost)
- [ ] File access restricted to app data folder
- [ ] Justice Log integrity verified
- [ ] PIRD exports logged to audit trail

### 7.2 UI Polish

**Final Touches**:
- Add loading states for async operations
- Add error boundaries for crash recovery
- Add tooltips for complex UI elements
- Add confirmation dialogs for destructive actions
- Add keyboard shortcut help screen
- Add "About" screen with version info

---

## ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────┐
│                    ENGRAM DESKTOP APP                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │          TAURI (Rust)                            │   │
│  │  - Window Management                             │   │
│  │  - IPC Handler                                   │   │
│  │  - File System Access                            │   │
│  │  - Python Backend Launcher                       │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↕ IPC                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │          REACT UI                                │   │
│  │  - Dashboard (Risk, Status, Agents)              │   │
│  │  - Incidents (Forensic Log)                      │   │
│  │  - Export (PIRD Generation)                      │   │
│  │  - Lineage (Graph Visualization)                 │   │
│  └──────────────────────────────────────────────────┘   │
│                    ↕ HTTP (localhost)                   │
│  ┌──────────────────────────────────────────────────┐   │
│  │          PYTHON BACKEND (FastAPI)                │   │
│  │  - SimulationEngine                              │   │
│  │  - RiskMonitor                                   │   │
│  │  - Justice Logger                                │   │
│  │  - Data Bridge                                   │   │
│  │  - PIRD Generator                                │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↕                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │          LOCAL STORAGE                           │   │
│  │  - SQLite Database                               │   │
│  │  - Justice Log (JSONL)                           │   │
│  │  - PIRD Exports                                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## TIMELINE SUMMARY

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1. Tauri Setup | 2 days | Working Tauri app with Python backend |
| 2. React Migration | 3 days | All UI components ported to Tauri |
| 3. Bloomberg UI | 3 days | Professional multi-panel layout |
| 4. Python Bridge | 3 days | Rust-Python IPC working |
| 5. Advanced Features | 3 days | Charts, resizing, shortcuts |
| 6. Packaging | 2 days | Installable `.exe` / `.dmg` |
| 7. Testing & Polish | 2 days | Production-ready app |
| **Total** | **18 days** | **Engram Desktop v1.0** |

---

## SUCCESS CRITERIA

The GUI is successful if:
- ✅ Looks as professional as Bloomberg Terminal
- ✅ Shows 4-6 data panels simultaneously
- ✅ Updates in real-time (< 1s latency)
- ✅ Runs entirely offline (no network calls except localhost)
- ✅ Installs as a single `.exe` (no dependencies)
- ✅ Starts in < 3 seconds
- ✅ Uses < 200MB RAM
- ✅ Generates valid PIRDs
- ✅ Verifies Justice Log integrity
- ✅ Feels like a "serious tool," not a consumer app

---

## ANTI-PATTERNS TO AVOID

❌ **Don't**:
- Use flashy animations or transitions
- Add "friendly" onboarding flows
- Include telemetry or analytics
- Make it look like a SaaS product
- Simplify the UI (data density is a feature)
- Add social features or sharing
- Use cloud storage or sync

✅ **Do**:
- Maximize information density
- Use monospace fonts and minimal color
- Make keyboard shortcuts primary
- Show raw data alongside visualizations
- Emphasize local control and security
- Make it feel like a professional tool
- Prioritize speed and reliability

---

## FINAL RECOMMENDATION

**Build the GUI using Tauri + React + Python (localhost HTTP bridge).**

This gives you:
1. ✅ Professional native app (not a web app)
2. ✅ Reuse existing React UI code
3. ✅ Keep Python backend intact
4. ✅ Local-first architecture
5. ✅ Small binary size (< 50MB)
6. ✅ Cross-platform (Windows, macOS, Linux)
7. ✅ Bloomberg-level visual quality

**Start with Phase 1 (Tauri Setup) and iterate from there.**
