import React from 'react';
import './Lineage.css';

const Lineage: React.FC = () => {
    return (
        <div className="lineage-screen">
            <div className="screen-header">
                <h1>Lineage</h1>
                <p className="screen-subtitle">Agent → Asset → Goal → Violation Relationships</p>
            </div>

            <div className="lineage-content">
                <div className="panel">
                    <div className="panel-header">LINEAGE GRAPH</div>
                    <div className="panel-content">
                        <div className="lineage-placeholder">
                            <div className="ascii-graph">
                                <pre>{`
┌─────────────────────────────────────────────────────────────┐
│                     LINEAGE VISUALIZATION                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│    [Agent: Bot-01]                                           │
│           │                                                  │
│           ├──▶ [Asset: Warehouse-A]                          │
│           │         │                                        │
│           │         └──▶ [Goal: Maintain Inventory]          │
│           │                   │                              │
│           │                   └──▶ [Violation: Battery < 0]  │
│           │                                                  │
│           └──▶ [Asset: Warehouse-B]                          │
│                     │                                        │
│                     └──▶ [Goal: Optimize Routes]             │
│                                                              │
│    [Agent: Bot-02]                                           │
│           │                                                  │
│           └──▶ [Asset: Warehouse-A]                          │
│                     │                                        │
│                     └──▶ [Goal: Maintain Inventory]          │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  Legend:                                                     │
│    [Agent]     - Autonomous agent                            │
│    [Asset]     - Protected resource                          │
│    [Goal]      - Objective/constraint                        │
│    [Violation] - Detected incident                           │
└─────────────────────────────────────────────────────────────┘
                `}</pre>
                            </div>

                            <div className="lineage-info">
                                <h3>Interactive Graph (Coming Soon)</h3>
                                <p>
                                    This screen will display an interactive visualization of the
                                    relationships between agents, assets, goals, and violations.
                                </p>
                                <p>Features:</p>
                                <ul>
                                    <li>Click nodes to expand/collapse</li>
                                    <li>Filter by agent, asset, or violation type</li>
                                    <li>Export graph as image</li>
                                    <li>Trace incident lineage</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Lineage;
