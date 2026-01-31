"""Incidents Screen - Detailed list of all detected incidents"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, DataTable, Input, Label
from textual.reactive import reactive
from rich.text import Text
from agent_forge.ui.data_bridge import data_bridge


class IncidentsScreen(Screen):
    """Incident log with filtering and search"""
    
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("/", "focus_search", "Search"),
        ("f", "toggle_filters", "Filters"),
        ("e", "export_selected", "Export"),
        ("r", "refresh_data", "Refresh"),
    ]
    
    selected_incident = reactive(None)
    
    def compose(self) -> ComposeResult:
        """Create incidents screen layout"""
        yield Container(
            Vertical(
                Static("⚠️  INCIDENT LOG - FORENSIC EVIDENCE TRAIL", id="incidents-title"),
                Horizontal(
                    Input(placeholder="Search incidents... (Press / to focus)", id="search-input"),
                    Static("[F] Filters: ALL", id="filter-status"),
                    classes="search-bar"
                ),
                Horizontal(
                    Vertical(
                        DataTable(id="incidents-table"),
                        classes="incidents-list"
                    ),
                    Vertical(
                        Static("INCIDENT DETAILS", id="detail-title"),
                        Static("Select an incident to view details", id="incident-detail"),
                        classes="detail-panel"
                    ),
                    classes="main-content"
                ),
                Static(self._get_help_text(), id="help-bar"),
                id="incidents-container"
            )
        )
    
    def on_mount(self) -> None:
        """Initialize incidents screen"""
        # Setup incidents table
        table = self.query_one("#incidents-table", DataTable)
        table.add_columns(
            "ID", 
            "Time", 
            "Agent", 
            "Fault Type", 
            "Prevent%", 
            "Liability"
        )
        table.cursor_type = "row"
        
        # Load initial data
        self.refresh_data()
    
    def _get_help_text(self) -> str:
        """Get help text for bottom bar"""
        return "[↑/↓] Navigate  [Enter] Details  [/] Search  [F] Filter  [E] Export  [Esc] Back"
    
    def refresh_data(self) -> None:
        """Load incidents from DossierGenerator"""
        table = self.query_one("#incidents-table", DataTable)
        table.clear()
        
        # Get live incidents from data bridge
        incidents = data_bridge.get_incidents()
        
        for incident in incidents:
            table.add_row(
                incident['incident_id'],
                incident['timestamp'],
                incident['agent_id'],
                incident['fault_type'],
                f"{incident['preventability']}%",
                f"${incident['liability']:,}"
            )
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection"""
        table = self.query_one("#incidents-table", DataTable)
        row_key = event.row_key
        
        # Get row data
        row = table.get_row(row_key)
        incident_id = row[0]
        
        # Update detail panel
        detail = self.query_one("#incident-detail", Static)
        detail.update(self._get_incident_details(incident_id))
    
    def _get_incident_details(self, incident_id: str) -> str:
        """Get detailed information for an incident"""
        return data_bridge.get_incident_details(incident_id)
    
    def action_focus_search(self) -> None:
        """Focus the search input"""
        search = self.query_one("#search-input", Input)
        search.focus()
    
    def action_toggle_filters(self) -> None:
        """Toggle filter options"""
        self.notify("Filter options - Coming soon")
    
    def action_export_selected(self) -> None:
        """Export selected incident to PIRD"""
        if self.selected_incident:
            self.notify(f"Exporting {self.selected_incident} to PIRD...")
        else:
            self.notify("No incident selected")
    
    def action_refresh_data(self) -> None:
        """Refresh incident data"""
        self.refresh_data()
        self.notify("Incident log refreshed")


# CSS for incidents screen
IncidentsScreen.DEFAULT_CSS = """
IncidentsScreen {
    background: black;
    color: white;
}

#incidents-title {
    background: darkblue;
    color: white;
    text-style: bold;
    padding: 1;
    text-align: center;
}

.search-bar {
    height: 3;
    padding: 1;
}

#search-input {
    width: 3fr;
    border: solid white;
}

#filter-status {
    width: 1fr;
    padding: 1;
    text-align: right;
}

.main-content {
    height: 1fr;
}

.incidents-list {
    width: 60%;
    border: solid white;
    margin: 1;
}

.detail-panel {
    width: 40%;
    border: solid white;
    margin: 1;
    padding: 1;
}

#detail-title {
    background: darkgray;
    text-style: bold;
    padding: 1;
}

#incident-detail {
    padding: 1;
    height: 1fr;
}

#help-bar {
    background: darkgray;
    color: white;
    padding: 1;
    text-align: center;
}

#incidents-table {
    height: 100%;
}
"""
