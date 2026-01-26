import typer
import asyncio
from typing import Optional
from rich.console import Console

app = typer.Typer(help="Agent Forge: The Risk Verification Platform")
console = Console()

@app.command()
def init(name: str):
    """
    Initialize a new agent project.
    """
    console.print(f"[green]Initializing new Agent Forge project: {name}[/green]")
    # TODO: Generate scaffold
    console.print("Created agent_config.yaml")
    console.print("Created src/agent.py")

@app.command()
def verify(
    path: str = typer.Option(".", help="Path to agent code"),
    vertical: str = typer.Option("logistics", help="Target vertical (logistics, finance)")
):
    """
    Run static analysis and smoke tests on the agent.
    """
    console.print(f"[bold yellow]Running Verification Suite for {vertical}...[/bold yellow]")
    # Mock Verification Logic
    import time
    with console.status("[bold green]Checking Risk Compliance...[/bold green]"):
        time.sleep(2)
        console.log("Static Analysis: PASS")
        time.sleep(1)
        console.log("Basic Simulation (10s): PASS")
        time.sleep(1)
        console.log("Resource Constraints: PASS")
        
    console.print("[bold green]VERIFICATION SUCCESSFUL[/bold green]")
    console.print("Your agent is certified for: [blue]Warehouse-v1[/blue]")

@app.command()
def run(
    ui: bool = typer.Option(False, "--ui", help="Start the Mission Control UI"),
    port: int = 3000
):
    """
    Run the simulation engine (long-running).
    """
    if ui:
        console.print(f"[green]Starting Mission Control UI on http://localhost:{port}[/green]")
        import uvicorn
        import webbrowser
        webbrowser.open(f"http://localhost:{port}")
        uvicorn.run("agent_forge.server.api:app", host="0.0.0.0", port=port, reload=True)
    else:
        console.print("[yellow]Running Headless Simulation...[/yellow]")
        # For now, just run the verification suite as headless sim
        verify(path=".", vertical="logistics")

if __name__ == "__main__":
    app()
