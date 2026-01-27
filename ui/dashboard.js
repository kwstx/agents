function Dashboard() {
    const [status, setStatus] = useState("DISCONNECTED");
    const [agents, setAgents] = useState({});
    const [logs, setLogs] = useState([]);
    const [gridSize, setGridSize] = useState(10);
    const [riskScore, setRiskScore] = useState(0);
    const [perfMetrics, setPerfMetrics] = useState({ fps: 0, linkLag: 0 });
    const lastRenderTime = React.useRef(performance.now());
    const frameCount = React.useRef(0);


    useEffect(() => {
        // Portable connection
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/state`);

        ws.onopen = () => setStatus("CONNECTED");
        ws.onclose = () => setStatus("DISCONNECTED");

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);

            if (msg.type === "step") {
                // Update specific agent
                setAgents(prev => ({
                    ...prev,
                    [msg.agent_id]: msg.observation
                }));

                // Risk Logic (Simulated for MVP: Low battery = Risk)
                if (msg.observation.battery < 20) {
                    setRiskScore(prev => Math.min(100, prev + 5));
                    addLog(`CRITICAL: ${msg.agent_id} Low Battery!`, "critical");
                } else if (msg.info && msg.info.event === "collision") {
                    setRiskScore(prev => Math.min(100, prev + 20));
                    addLog(`COLLISION: ${msg.agent_id} at ${msg.observation.position}`, "critical");
                } else if (msg.info && msg.info.event === "blocked") {
                    // Blocked is normal congestion, don't increase risk.
                    // setRiskScore(prev => Math.min(100, prev + 1)); 
                    addLog(`BLOCKED: ${msg.agent_id} waiting at ${msg.observation.position}`, "warning");
                }
            } else if (msg.type === "snapshot") {
                // Full state replace
                setAgents(msg.data);
                addLog("State synced from snapshot", "info");
            }
        }
        // FPS Loop
        let fpsId;
        const measureFPS = () => {
            const now = performance.now();
            frameCount.current++;
            if (now - lastRenderTime.current >= 1000) {
                setPerfMetrics(prev => ({ ...prev, fps: frameCount.current }));
                frameCount.current = 0;
                lastRenderTime.current = now;
            }
            fpsId = requestAnimationFrame(measureFPS);
        };
        fpsId = requestAnimationFrame(measureFPS);

        return () => {
            ws.close();
            cancelAnimationFrame(fpsId);
        };
    }, []);

    const addLog = (text, type = "info") => {
        setLogs(prev => [{ text, type, time: new Date().toLocaleTimeString() }, ...prev.slice(0, 19)]);
    };

    const renderGrid = () => {
        const cells = [];
        for (let y = gridSize - 1; y >= 0; y--) {
            for (let x = 0; x < gridSize; x++) {
                let cellContent = null;
                let cellClass = "w-10 h-10 border border-slate-700 bg-slate-800 relative";

                // Draw Zones
                if (x === 0) cellClass += " bg-blue-900/30"; // Pickup
                if (x === gridSize - 1) cellClass += " bg-green-900/30"; // Dropoff
                if (y === gridSize - 1) cellClass += " bg-yellow-900/30"; // Charge

                // Draw Agents
                Object.entries(agents).forEach(([id, state]) => {
                    const [ax, ay] = state.position || [-1, -1];
                    if (ax === x && ay === y) {
                        const color = state.battery < 20 ? "bg-red-500" : "bg-blue-400";
                        cellContent = (
                            <div className={`absolute inset-1 rounded-full ${color} flex items-center justify-center text-xs font-bold text-black`}>
                                {id.split("-")[1]}
                            </div>
                        );
                    }
                });

                cells.push(<div key={`${x}-${y}`} className={cellClass}>{cellContent}</div>);
            }
        }
        return cells;
    };

    return (
        <div className={`min-h-screen p-6 ${riskScore > 80 ? 'border-4 border-red-600 critical-alert' : ''}`}>
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-3xl font-bold text-blue-500">AGENT FORGE <span className="text-white text-lg">MISSION CONTROL</span></h1>
                    <div className="text-xs text-slate-500 font-mono mt-1">v0.9.0-BETA</div>
                </div>
                <div className="flex gap-4">
                    <div id="perf-metrics" className="px-4 py-2 bg-slate-800 rounded font-mono text-cyan-400 border border-slate-700">
                        FPS: {perfMetrics.fps}
                    </div>
                    <div className={`px-4 py-2 rounded font-mono border ${status === "CONNECTED" ? "bg-green-900/50 border-green-700 text-green-400" : "bg-red-900/50 border-red-700 text-red-400 animate-pulse"}`}>
                        {status}
                    </div>
                </div>
            </div>

            {/* System Status Banner */}
            <div className={`mb-6 p-4 rounded-lg font-bold text-center text-xl tracking-widest transition-all duration-300 ${riskScore > 80 ? 'bg-red-600 text-white animate-pulse shadow-[0_0_20px_rgba(220,38,38,0.7)]' :
                riskScore > 50 ? 'bg-yellow-600 text-black' :
                    'bg-emerald-900/50 text-emerald-400 border border-emerald-800'
                }`}>
                SYSTEM STATUS: {riskScore > 80 ? "CRITICAL FAILURE IMMINENT" : riskScore > 50 ? "DEGRADED PERFORMANCE" : "OPERATIONAL"}
            </div>

            <div className="grid grid-cols-12 gap-6">
                {/* Main View: Grid */}
                <div className="col-span-8 bg-slate-900 p-4 rounded-lg border border-slate-700 flex justify-center">
                    <div className="grid grid-cols-10 gap-1">
                        {renderGrid()}
                    </div>
                </div>

                {/* Sidebar: Logs & Controls */}
                <div className="col-span-4 space-y-4">
                    <div className="bg-slate-900 p-4 rounded-lg border border-slate-700 h-96 overflow-y-auto font-mono text-sm">
                        <h3 className="text-slate-400 mb-2 border-b border-slate-700 pb-1">LIVE EVENT STREAM</h3>
                        {logs.map((log, i) => (
                            <div key={i} className={`mb-2 p-1 rounded font-mono text-xs ${log.type === "critical" ? "bg-red-900/30 text-red-300 border-l-2 border-red-500 pl-2" :
                                log.type === "warning" ? "bg-yellow-900/30 text-yellow-300 border-l-2 border-yellow-500 pl-2" :
                                    "text-slate-400 pl-2"
                                }`}>
                                <span className="opacity-50 mr-2">[{log.time}]</span>
                                {log.type === "critical" && "🚨 "}
                                {log.type === "warning" && "⚠️ "}
                                {log.text}
                            </div>
                        ))}
                    </div>

                    <div className="bg-slate-900 p-4 rounded-lg border border-slate-700">
                        <h3 className="text-slate-400 mb-2">CONTROLS</h3>
                        <div className="flex gap-2">
                            <button onClick={() => fetch('/api/sim/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ vertical: 'logistics' }) })}
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-white font-bold w-full">
                                START FLEET
                            </button>
                            <button onClick={() => fetch('/api/sim/stop', { method: 'POST' })}
                                className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded text-white font-bold w-full">
                                EMERGENCY STOP
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

const { useState, useEffect } = React;
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<Dashboard />);
