"""
Engram Terminal UI (TUI)
The Black Box Flight Recorder for Autonomous Systems
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, Button
from textual.binding import Binding
from textual.screen import Screen
from textual import events

class EngramTUI(App):
    """Main TUI Application for Engram"""
    
    CSS = """
    Screen {
        background: black;
        color: white;
    }
    
    Header {
        background: darkblue;
        color: white;
    }
    
    Footer {
        background: darkgray;
        color: white;
    }
    
    .risk-low {
        color: green;
    }
    
    .risk-medium {
        color: yellow;
    }
    
    .risk-high {
        color: red;
    }
    
    .risk-critical {
        color: magenta;
    }
    
    DataTable {
        border: solid white;
    }
    
    Button {
        border: solid white;
        background: darkblue;
    }
    
    Button:hover {
        background: blue;
    }
    """
    
    TITLE = "Engram - The Black Box Flight Recorder"
    SUB_TITLE = "Local-First Forensic System | The Truth Never Leaves"
    
    BINDINGS = [
        Binding("f1", "show_dashboard", "Dashboard", show=True),
        Binding("f2", "show_incidents", "Incidents", show=True),
        Binding("f3", "show_agents", "Agents", show=True),
        Binding("f4", "show_lineage", "Lineage", show=True),
        Binding("f5", "show_export", "Export", show=True),
        Binding("q", "quit_app", "Quit", show=True),
        Binding("?", "show_help", "Help", show=False),
    ]
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Container(
            Static("Engram TUI is starting...", id="main-content")
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.action_show_dashboard()
    
    def action_show_dashboard(self) -> None:
        """Show the dashboard screen."""
        from .screens.dashboard import DashboardScreen
        self.push_screen(DashboardScreen())
    
    def action_show_incidents(self) -> None:
        """Show the incidents screen."""
        from .screens.incidents import IncidentsScreen
        self.push_screen(IncidentsScreen())
    
    def action_show_agents(self) -> None:
        """Show the agents screen."""
        self.notify("Agent details screen - Coming soon")
    
    def action_show_lineage(self) -> None:
        """Show the lineage graph screen."""
        self.notify("Lineage graph screen - Coming soon")
    
    def action_show_export(self) -> None:
        """Show the export screen."""
        from .screens.export import ExportScreen
        self.push_screen(ExportScreen())
    
    def action_show_help(self) -> None:
        """Show help screen."""
        self.notify("Help: F1=Dashboard F2=Incidents F3=Agents F4=Lineage F5=Export Q=Quit")
    
    def action_quit_app(self) -> None:
        """Quit the application."""
        self.exit()


def run_tui():
    """Entry point for the TUI."""
    app = EngramTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
