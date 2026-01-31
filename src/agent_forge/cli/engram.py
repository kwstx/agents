"""
Engram CLI - Command-line interface for the Black Box Flight Recorder
"""

import click
from agent_forge.ui import run_tui


@click.group()
def cli():
    """Engram - The Black Box Flight Recorder for Autonomous Systems"""
    pass


@cli.command()
def tui():
    """Launch the Terminal UI (default interface)"""
    run_tui()


@cli.command()
@click.option('--logs', type=click.Path(exists=True), required=True, help='Path to simulation logs (JSONL)')
@click.option('--output', type=click.Path(), required=True, help='Output path for PIRD')
def replay(logs, output):
    """Replay historical logs and generate PIRD"""
    click.echo(f"Replaying logs from: {logs}")
    click.echo(f"Generating PIRD to: {output}")
    # TODO: Implement log replay functionality
    click.echo("Log replay - Coming soon")


@cli.command()
@click.option('--output', type=click.Path(), required=True, help='Output path for PIRD')
@click.option('--format', type=click.Choice(['txt', 'json', 'pdf']), default='txt', help='Output format')
def export_pird(output, format):
    """Export Pre-Incident Risk Dossier"""
    click.echo(f"Exporting PIRD to: {output} (format: {format})")
    # TODO: Implement PIRD export
    click.echo("PIRD export - Coming soon")


@cli.command()
@click.argument('pird_file', type=click.Path(exists=True))
@click.option('--public-key', type=click.Path(exists=True), help='Public key for verification')
def verify_pird(pird_file, public_key):
    """Verify integrity of a PIRD file"""
    click.echo(f"Verifying PIRD: {pird_file}")
    if public_key:
        click.echo(f"Using public key: {public_key}")
    # TODO: Implement PIRD verification
    click.echo("PIRD verification - Coming soon")


@cli.command()
def verify_logs():
    """Verify integrity of the Justice Log (hash chain)"""
    from agent_forge.core.justice_log import get_justice_logger
    
    click.echo("Verifying Justice Log integrity...")
    justice_log = get_justice_logger()
    result = justice_log.verify_integrity()
    
    if result['valid']:
        click.echo(click.style(f"✓ VERIFIED", fg='green', bold=True))
        click.echo(f"Total Entries: {result['total_entries']}")
        click.echo(f"Message: {result['message']}")
    else:
        click.echo(click.style(f"✗ COMPROMISED", fg='red', bold=True))
        click.echo(f"Failed at index: {result.get('failed_at_index', 'N/A')}")
        click.echo(f"Message: {result['message']}")
        exit(1)


@cli.command()
@click.option('--output', type=click.Path(), help='Output path for manifest (optional)')
def seal_logs(output):
    """Seal logs and generate tamper-proof manifest"""
    from agent_forge.core.justice_log import get_justice_logger
    
    click.echo("Sealing Justice Log...")
    justice_log = get_justice_logger()
    manifest = justice_log.seal()
    
    click.echo(click.style("✓ Log sealed successfully", fg='green'))
    click.echo(f"Total Entries: {manifest['total_entries']}")
    click.echo(f"Chain Hash: {manifest['chain_hash'][:32]}...")
    click.echo(f"Manifest saved to: {manifest['log_file'].replace('.jsonl', '_manifest.json')}")
    
    if output:
        import json
        with open(output, 'w') as f:
            json.dump(manifest, f, indent=2)
        click.echo(f"Manifest also saved to: {output}")


@cli.command()
def version():
    """Show Engram version"""
    click.echo("Engram v0.1.0")
    click.echo("The Black Box Flight Recorder for Autonomous Systems")
    click.echo("Local-First | Forensic-Grade | The Truth Never Leaves")


if __name__ == '__main__':
    cli()
