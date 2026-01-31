"""Dashboard Screen - Overview of simulation status and risk"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, DataTable, Label
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.table import Table as RichTable
from agent_forge.ui.data_bridge import data_bridge


class RiskMeter(Static):
    """Widget to display risk score with visual meter"""
    
    risk_score = reactive(0)
    
    def __init__(self, agent_id: str = "SYSTEM", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_id = agent_id
    
    def render(self) -> Text:
        """Render the risk meter"""
        score = self.risk_score
        
        # Determine risk level and color
        if score >= 100:
            level = "CRITICAL"
            color = "magenta"
        elif score >= 50:
            level = "HIGH"
            color = "red"
        elif score >= 20:
            level = "MEDIUM"
            color = "yellow"
        else:
            level = "LOW"
            color = "green"
        
        # Create progress bar
        bar_length = 20
        filled = int((min(score, 100) / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # Build display
        text = Text()
        text.append(f"RISK SCORE: ", style="bold")
        text.append(f"{score:.0f}", style=f"bold {color}")
        text.append(f" [{level}]\n", style=f"bold {color}")
        text.append(f"[{bar}] ", style=color)
        text.append(f"{score:.0f}/100", style=color)
        
        return text


class DashboardScreen(Screen):
    """Main dashboard showing simulation overview"""
    
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("r", "refresh_data", "Refresh"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create dashboard layout"""
        yield Container(
            Vertical(
                Static(self._get_logo(), id="logo"),
                Horizontal(
                    Vertical(
                        Static("📊 SIMULATION STATUS", classes="panel-title"),
                        Static(self._get_status_info(), id="status-info"),
                        classes="panel"
                    ),
                    Vertical(
                        Static("⚠️  RISK OVERVIEW", classes="panel-title"),
                        RiskMeter(id="system-risk-meter"),
                        Static(id="risk-summary"),
                        classes="panel"
                    ),
                    classes="top-panels"
                ),
                Vertical(
                    Static("🤖 ACTIVE AGENTS", classes="panel-title"),
                    DataTable(id="agents-table"),
                    classes="panel agents-panel"
                ),
                Vertical(
                    Static("⚡ QUICK ACTIONS", classes="panel-title"),
                    Static(self._get_quick_actions(), id="quick-actions"),
                    classes="panel"
                ),
                id="dashboard-container"
            )
        )
    
    def on_mount(self) -> None:
        """Initialize dashboard when mounted"""
        # Setup agents table
        table = self.query_one("#agents-table", DataTable)
        table.add_columns("Agent ID", "Type", "Risk", "Battery", "Status")
        
        # Load initial data
        self.refresh_data()
        
        # Set up periodic refresh
        self.set_interval(1.0, self.refresh_data)
    
    def _get_logo(self) -> str:
        """Get ASCII logo"""
        return """
╔═══════════════════════════════════════════════════════════════════════════════╗
║  ███████╗███╗   ██╗ ██████╗ ██████╗  █████╗ ███╗   ███╗                      ║
║  ██╔════╝████╗  ██║██╔════╝ ██╔══██╗██╔══██╗████╗ ████║                      ║
║  █████╗  ██╔██╗ ██║██║  ███╗██████╔╝███████║██╔████╔██║                      ║
║  ██╔══╝  ██║╚██╗██║██║   ██║██╔══██╗██╔══██║██║╚██╔╝██║                      ║
║  ███████╗██║ ╚████║╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║                      ║
║  ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝                      ║
║                                                                               ║
║              THE BLACK BOX FLIGHT RECORDER FOR AUTONOMOUS SYSTEMS             ║
║                    Local-First | Forensic-Grade | The Truth Never Leaves      ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""
    
    def _get_status_info(self) -> str:
        """Get simulation status information"""
        return """
Status: RUNNING ✓
Mode: SEALED (No external connections)
Uptime: 00:15:32
Events Logged: 1,247
"""
    
    def _get_quick_actions(self) -> str:
        """Get quick actions help text"""
        return """
[E] Export PIRD          [I] View Incidents       [P] Pause/Resume
[F2] Incident Log        [F3] Agent Details       [F5] Export Screen
[Q] Quit                 [?] Help
"""
    
    def action_refresh_data(self) -> None:
        """Refresh dashboard data"""
        self.refresh_data()
    
    def refresh_data(self) -> None:
        """Update dashboard with latest data"""
        # Update risk meter with live data
        risk_meter = self.query_one("#system-risk-meter", RiskMeter)
        risk_meter.risk_score = data_bridge.get_system_risk_score()
        
        # Update risk summary with live data
        risk_summary = self.query_one("#risk-summary", Static)
        summary_data = data_bridge.get_risk_summary()
        risk_summary.update(f"""
Total Incidents: {summary_data['total_incidents']}
Highest Risk Agent: {summary_data['highest_risk_agent']}
Latest Event: {summary_data['latest_event']}
""")
        
        # Update agents table with live data
        table = self.query_one("#agents-table", DataTable)
        table.clear()
        
        agents = data_bridge.get_active_agents()
        for agent_data in agents:
            table.add_row(
                agent_data['agent_id'],
                agent_data['type'],
                f"{agent_data['risk_score']} [{agent_data['risk_level']}]",
                str(agent_data['battery']) if agent_data['battery'] != 'N/A' else 'N/A',
                agent_data['status']
            )


# CSS for dashboard
DashboardScreen.DEFAULT_CSS = """
DashboardScreen {
    background: black;
    color: white;
}

#logo {
    height: auto;
    color: cyan;
    text-align: center;
    margin: 1;
}

.panel-title {
    background: darkblue;
    color: white;
    text-style: bold;
    padding: 1;
}

.panel {
    border: solid white;
    margin: 1;
    padding: 1;
}

.top-panels {
    height: auto;
}

.agents-panel {
    height: 1fr;
}

#status-info, #risk-summary, #quick-actions {
    padding: 1;
}

#agents-table {
    height: 100%;
}
"""
