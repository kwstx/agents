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
    import os
    from pathlib import Path
    
    project_dir = Path(name)
    if project_dir.exists():
        console.print(f"[bold red]Error: Directory '{name}' already exists.[/bold red]")
        raise typer.Exit(code=1)
        
    try:
        project_dir.mkdir(parents=True)
        console.print(f"[green]Initializing new Agent Forge project: {name}[/green]")
        
        # Create agent_config.yaml
        config_content = """
agent:
  name: ${name}
  version: 0.1.0
  vertical: logistics
  
capabilities:
  - planning
  - reasoning
  """
        with open(project_dir / "agent_config.yaml", "w") as f:
             f.write(config_content.strip().replace("${name}", name))
        console.print("Created agent_config.yaml")

        # Create my_agent.py
        agent_code = """
class MyAgent:
    def __init__(self):
        self.name = "MyAgent"

    def think(self, observation):
        # Implement your agent's logic here
        return "wait"
"""
        with open(project_dir / "my_agent.py", "w") as f:
            f.write(agent_code.strip())
        console.print("Created my_agent.py")
        
        console.print(f"[bold green]Success! Project '{name}' created.[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Failed to initialize project: {e}[/bold red]")
        raise typer.Exit(code=1)

@app.command()
def verify(
    path: str = typer.Option(".", help="Path to agent code"),
    vertical: str = typer.Option("logistics", help="Target vertical (logistics, finance)")
):
    """
    Run static analysis and smoke tests on the agent.
    """
    from agent_forge.core.verifier import Verifier
    
    console.print(f"[bold yellow]Running Verification Suite for {vertical}...[/bold yellow]")
    
    verifier = Verifier(path)
    if verifier.verify():
        console.print("[bold green]VERIFICATION SUCCESSFUL[/bold green]")
        console.print(f"Your agent is organic and certified for: [blue]{vertical}[/blue]")
    else:
        console.print(verifier.get_report().replace("[BOLD RED]", "[bold red]").replace("[/BOLD RED]", "[/bold red]"))
        raise typer.Exit(code=1)

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
