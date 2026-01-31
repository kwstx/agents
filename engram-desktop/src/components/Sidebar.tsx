import React from 'react';
import './Sidebar.css';

interface SidebarProps {
    activeScreen: string;
    onNavigate: (screen: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeScreen, onNavigate }) => {
    const screens = [
        { id: 'dashboard', label: 'Dashboard', key: 'F1' },
        { id: 'incidents', label: 'Incidents', key: 'F2' },
        { id: 'export', label: 'Export', key: 'F3' },
        { id: 'lineage', label: 'Lineage', key: 'F4' },
    ];

    return (
        <div className="sidebar">
            <div className="sidebar-header">
                <h2>ENGRAM</h2>
                <p className="sidebar-subtitle">Navigation</p>
            </div>

            <nav className="sidebar-nav">
                {screens.map((screen) => (
                    <button
                        key={screen.id}
                        className={`nav-item ${activeScreen === screen.id ? 'active' : ''}`}
                        onClick={() => onNavigate(screen.id)}
                    >
                        <span className="nav-label">{screen.label}</span>
                        <span className="nav-key">{screen.key}</span>
                    </button>
                ))}
            </nav>

            <div className="sidebar-footer">
                <div className="status-indicator">
                    <span className="status-dot"></span>
                    <span>SEALED</span>
                </div>
                <p className="version">v0.1.0</p>
            </div>
        </div>
    );
};

export default Sidebar;
