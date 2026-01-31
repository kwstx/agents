import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./screens/Dashboard";
import Incidents from "./screens/Incidents";
import Export from "./screens/Export";
import Lineage from "./screens/Lineage";
import "./App.css";

function App() {
    const [activeScreen, setActiveScreen] = useState<string>("dashboard");

    // Keyboard shortcuts
    useEffect(() => {
        const handleKeyPress = (e: KeyboardEvent) => {
            if (e.key === "F1") {
                e.preventDefault();
                setActiveScreen("dashboard");
            } else if (e.key === "F2") {
                e.preventDefault();
                setActiveScreen("incidents");
            } else if (e.key === "F3") {
                e.preventDefault();
                setActiveScreen("export");
            } else if (e.key === "F4") {
                e.preventDefault();
                setActiveScreen("lineage");
            }
        };

        window.addEventListener("keydown", handleKeyPress);
        return () => window.removeEventListener("keydown", handleKeyPress);
    }, []);

    const renderScreen = () => {
        switch (activeScreen) {
            case "dashboard":
                return <Dashboard />;
            case "incidents":
                return <Incidents />;
            case "export":
                return <Export />;
            case "lineage":
                return <Lineage />;
            default:
                return <Dashboard />;
        }
    };

    return (
        <div className="app">
            <Sidebar activeScreen={activeScreen} onNavigate={setActiveScreen} />
            <div className="main-container">
                <header className="header">
                    <h1>ENGRAM - The Black Box Flight Recorder</h1>
                    <p className="subtitle">Local-First | Forensic-Grade | The Truth Never Leaves</p>
                </header>

                <main className="main-content">{renderScreen()}</main>

                <footer className="footer">
                    <p>ENGRAM v0.1.0 | {activeScreen.toUpperCase()} | Press F1-F4 to navigate</p>
                </footer>
            </div>
        </div>
    );
}

export default App;
