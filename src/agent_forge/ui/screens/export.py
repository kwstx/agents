"""Export Screen - PIRD generation and export interface"""

import time
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, Button, Checkbox, Input, Label, TextArea
from textual.reactive import reactive


class ExportScreen(Screen):
    """PIRD export interface with configuration and preview"""
    
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("p", "generate_preview", "Preview"),
        ("e", "export_pird", "Export"),
        ("v", "verify_pird", "Verify"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create export screen layout"""
        yield Container(
            Vertical(
                Static("📄 PRE-INCIDENT RISK DOSSIER (PIRD) - EXPORT", id="export-title"),
                Horizontal(
                    Vertical(
                        Static("EXPORT CONFIGURATION", id="config-title"),
                        Vertical(
                            Label("Output Format:"),
                            Horizontal(
                                Checkbox("Text (.txt)", value=True, id="format-txt"),
                                Checkbox("JSON (.json)", id="format-json"),
                                Checkbox("PDF (.pdf)", id="format-pdf"),
                                classes="format-options"
                            ),
                            Label("Output Path:"),
                            Input(
                                placeholder="/path/to/output/pird_report.txt",
                                id="output-path"
                            ),
                            Label("Include Options:"),
                            Checkbox("Agent Metadata", value=True, id="include-metadata"),
                            Checkbox("Evidence Anchors", value=True, id="include-evidence"),
                            Checkbox("Technical Details", value=True, id="include-technical"),
                            Label("Security:"),
                            Checkbox("Sign with Private Key", id="sign-pird"),
                            Input(
                                placeholder="/path/to/private_key.pem",
                                id="key-path",
                                disabled=True
                            ),
                            classes="config-form"
                        ),
                        Horizontal(
                            Button("Generate Preview", variant="primary", id="btn-preview"),
                            Button("Export to File", variant="success", id="btn-export"),
                            Button("Verify PIRD", variant="default", id="btn-verify"),
                            classes="action-buttons"
                        ),
                        classes="config-panel"
                    ),
                    Vertical(
                        Static("PIRD PREVIEW", id="preview-title"),
                        ScrollableContainer(
                            Static(self._get_sample_pird(), id="pird-preview"),
                            classes="preview-container"
                        ),
                        classes="preview-panel"
                    ),
                    classes="main-panels"
                ),
                Vertical(
                    Static("EXPORT AUDIT LOG", id="audit-title"),
                    Static(self._get_audit_log(), id="audit-log"),
                    classes="audit-panel"
                ),
                Static(self._get_help_text(), id="help-bar"),
                id="export-container"
            )
        )
    
    def on_mount(self) -> None:
        """Initialize export screen"""
        # Setup checkbox listeners
        sign_checkbox = self.query_one("#sign-pird", Checkbox)
        sign_checkbox.watch(self, "on_sign_checkbox_changed")
    
    def _get_sample_pird(self) -> str:
        """Get sample PIRD for preview"""
        return """
================================================================================
 ENGRAM: PRE-INCIDENT RISK DOSSIER (PIRD)
 Generated: 2026-01-31 16:15:00
 Security Rank: OFFICIAL / AUDIT-READY
================================================================================

[1.0] EXECUTIVE SUMMARY: Post-Incident Survival
Status: CRITICAL_VIOLATION
Primary Agent: Logistics-Bot-01 (v2.1.0)
Total Preventable Incidents: 3

[2.0] ASSET EXPOSURE & OBJECTIVES
|-- Asset: Inventory-Item-42 (Valuation: $25,000.00)
|-- Asset: Warehouse-Zone-A (Valuation: $150,000.00)
|-- Objective: Deliver Package (Criticality: 8/10)
|-- Objective: Maintain Safety Protocols (Criticality: 10/10)

[3.0] ANALYTICAL FINDINGS (EVIDENCE OF PREVENTABILITY)

INCIDENT ID: INC-1738339512-0
|-- Fault Attribution: ENVIRONMENTAL_STRESS
|-- Estimated Liability Exposure: $2,450.00
|-- Preventability Score: 95%
|-- Forensic Narrative: DEMONSTRABLY PREVENTABLE. The failure was a direct 
    result of environmental stress (1.512s latency) which exceeded the 
    Operational Design Domain (ODD).
|-- Technical Evidence Anchors:
    - STEP_DURATION: 1.512 seconds
    - Confidence: 100%

================================================================================
 END OF DOSSIER | PROOF OF PREVENTABILITY
 ENGRAM | THE SYSTEM OF RECORD FOR AUTONOMY
================================================================================
"""
    
    def _get_audit_log(self) -> str:
        """Get recent export audit log"""
        return """
Recent Exports:
2026-01-31 15:45:23 | pird_report_001.txt | User: admin | Hash: a3f2...
2026-01-31 14:12:10 | incident_analysis.json | User: admin | Hash: b8e1...
2026-01-31 13:05:47 | compliance_report.pdf | User: admin | Hash: c9d3...
"""
    
    def _get_help_text(self) -> str:
        """Get help text for bottom bar"""
        return "[P] Preview  [E] Export  [V] Verify  [Tab] Navigate  [Esc] Back"
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-preview":
            self.action_generate_preview()
        elif event.button.id == "btn-export":
            self.action_export_pird()
        elif event.button.id == "btn-verify":
            self.action_verify_pird()
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes"""
        if event.checkbox.id == "sign-pird":
            key_input = self.query_one("#key-path", Input)
            key_input.disabled = not event.value
    
    def action_generate_preview(self) -> None:
        """Generate PIRD preview"""
        self.notify("Generating PIRD preview...")
        
        # Get live data from data bridge
        from agent_forge.ui.data_bridge import data_bridge
        
        # Generate PIRD content
        pird_content = self._generate_pird_content()
        
        # Update preview
        preview = self.query_one("#pird-preview", Static)
        preview.update(pird_content)
        self.notify("Preview generated successfully")
    
    def _generate_pird_content(self) -> str:
        """Generate actual PIRD content from live data"""
        from agent_forge.ui.data_bridge import data_bridge
        import time
        
        # Get data
        incidents = data_bridge.get_incidents()
        agents = data_bridge.get_active_agents()
        summary = data_bridge.get_risk_summary()
        
        # Build PIRD
        lines = []
        lines.append("=" * 80)
        lines.append(" ENGRAM: PRE-INCIDENT RISK DOSSIER (PIRD)")
        lines.append(f" Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(" Security Rank: OFFICIAL / AUDIT-READY")
        lines.append("=" * 80)
        
        lines.append("\n[1.0] EXECUTIVE SUMMARY: Post-Incident Survival")
        status = "CRITICAL_VIOLATION" if incidents else "COMPLIANT"
        lines.append(f"Status: {status}")
        lines.append(f"Primary Agent: {agents[0]['agent_id'] if agents else 'None'}")
        lines.append(f"Total Preventable Incidents: {len(incidents)}")
        
        lines.append("\n[2.0] ASSET EXPOSURE & OBJECTIVES")
        lines.append("|-- Asset: System Assets (Valuation: $175,000.00)")
        lines.append("|-- Objective: Maintain Safety Protocols (Criticality: 10/10)")
        
        lines.append("\n[3.0] ANALYTICAL FINDINGS (EVIDENCE OF PREVENTABILITY)")
        
        if not incidents:
            lines.append("|-- No preventable failures detected under current ODD parameters.")
        else:
            for inc in incidents[:10]:  # Limit to 10 for preview
                lines.append(f"\nINCIDENT ID: {inc['incident_id']}")
                lines.append(f"|-- Fault Attribution: {inc['fault_type']}")
                lines.append(f"|-- Estimated Liability Exposure: ${inc['liability']:,.2f}")
                lines.append(f"|-- Preventability Score: {inc['preventability']}%")
                
                # Get narrative
                if inc['fault_type'] == 'ENV_STRESS':
                    narrative = "DEMONSTRABLY PREVENTABLE. The failure was a direct result of environmental stress which exceeded the Operational Design Domain (ODD)."
                elif inc['fault_type'] == 'LOGIC_DEFECT':
                    narrative = "POTENTIALLY PREVENTABLE. The agent entered a critical failure state without evidence of external stress, suggesting a logic defect."
                else:
                    narrative = "Analysis inconclusive. Further investigation required."
                
                lines.append(f"|-- Forensic Narrative: {narrative}")
        
        lines.append("\n" + "=" * 80)
        lines.append(" END OF DOSSIER | PROOF OF PREVENTABILITY")
        lines.append(" ENGRAM | THE SYSTEM OF RECORD FOR AUTONOMY")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def action_export_pird(self) -> None:
        """Export PIRD to file"""
        output_path = self.query_one("#output-path", Input).value
        if not output_path:
            self.notify("Please specify output path", severity="error")
            return
        
        try:
            # Generate PIRD content
            pird_content = self._generate_pird_content()
            
            # Write to file
            with open(output_path, 'w') as f:
                f.write(pird_content)
            
            # Log to audit trail (using Justice Log)
            from agent_forge.core.justice_log import get_justice_logger
            justice_log = get_justice_logger()
            justice_log.log("PIRD_EXPORT", "system", {
                "output_path": output_path,
                "timestamp": time.time(),
                "format": "txt"
            })
            
            self.notify(f"PIRD exported to: {output_path}", severity="information")
            
            # Update audit log display
            audit = self.query_one("#audit-log", Static)
            new_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {output_path} | User: admin | Format: TXT\n"
            current_text = str(audit.renderable)
            audit.update(new_entry + current_text)
            
        except Exception as e:
            self.notify(f"Export failed: {str(e)}", severity="error")
    
    def action_verify_pird(self) -> None:
        """Verify existing PIRD"""
        from agent_forge.core.justice_log import get_justice_logger
        justice_log = get_justice_logger()
        
        # Verify Justice Log integrity
        result = justice_log.verify_integrity()
        
        if result['valid']:
            self.notify(f"✓ Justice Log verified: {result['total_entries']} entries intact", severity="information")
        else:
            self.notify(f"✗ Justice Log compromised: {result['message']}", severity="error")


# CSS for export screen
ExportScreen.DEFAULT_CSS = """
ExportScreen {
    background: black;
    color: white;
}

#export-title {
    background: darkblue;
    color: white;
    text-style: bold;
    padding: 1;
    text-align: center;
}

.main-panels {
    height: 3fr;
}

.config-panel {
    width: 40%;
    border: solid white;
    margin: 1;
    padding: 1;
}

.preview-panel {
    width: 60%;
    border: solid white;
    margin: 1;
}

#config-title, #preview-title, #audit-title {
    background: darkgray;
    text-style: bold;
    padding: 1;
}

.config-form {
    padding: 1;
}

.config-form Label {
    margin-top: 1;
    text-style: bold;
}

.config-form Input {
    margin-bottom: 1;
    border: solid white;
}

.format-options {
    height: auto;
}

.action-buttons {
    height: auto;
    margin-top: 1;
}

.action-buttons Button {
    margin: 1;
}

.preview-container {
    height: 100%;
    border-top: solid white;
}

#pird-preview {
    padding: 1;
}

.audit-panel {
    height: 1fr;
    border: solid white;
    margin: 1;
    padding: 1;
}

#audit-log {
    padding: 1;
}

#help-bar {
    background: darkgray;
    color: white;
    padding: 1;
    text-align: center;
}
"""
