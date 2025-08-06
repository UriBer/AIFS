#!/usr/bin/env python3
"""Command-line interface for AIFS.

This script provides a command-line interface for interacting with the AIFS system.
"""

import os
import sys
import time
import json
import base64
import numpy as np
from typing import Optional, List, Dict, Any
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from aifs.client import AIFSClient

# Create Typer app
app = typer.Typer(help="AI-Native File System (AIFS) CLI")
console = Console()

# Global client
client = None


@app.callback()
def callback(ctx: typer.Context, server: str = "localhost:50051"):
    """Initialize AIFS client."""
    global client
    if ctx.invoked_subcommand != "server":
        client = AIFSClient(server)


@app.command("put")
def put_asset(
    file_path: Path = typer.Argument(..., help="Path to file to store"),
    kind: str = typer.Option("blob", help="Asset kind (blob, model, etc.)"),
    content_type: Optional[str] = typer.Option(None, help="Content type"),
    description: Optional[str] = typer.Option(None, help="Asset description"),
    metadata_file: Optional[Path] = typer.Option(None, help="Path to JSON metadata file"),
    parent_ids: List[str] = typer.Option([], help="Parent asset IDs"),
    transform_name: Optional[str] = typer.Option(None, help="Transform name for lineage"),
    transform_digest: Optional[str] = typer.Option(None, help="Transform digest for lineage"),
):
    """Store an asset in AIFS."""
    # Check if file exists
    if not file_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        sys.exit(1)
    
    # Read file
    with open(file_path, "rb") as f:
        data = f.read()
    
    # Prepare metadata
    metadata = {}
    if metadata_file:
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
    
    # Add content type and description if provided
    if content_type:
        metadata["content_type"] = content_type
    elif "content_type" not in metadata:
        # Try to guess content type from file extension
        ext = file_path.suffix.lower()
        content_type_map = {
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".json": "application/json",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".pdf": "application/pdf",
            ".py": "text/x-python",
        }
        if ext in content_type_map:
            metadata["content_type"] = content_type_map[ext]
    
    if description:
        metadata["description"] = description
    
    # Prepare parents
    parents = []
    if parent_ids:
        if not transform_name:
            transform_name = "unknown"
        if not transform_digest:
            transform_digest = "unknown"
        
        for parent_id in parent_ids:
            parents.append({
                "asset_id": parent_id,
                "transform_name": transform_name,
                "transform_digest": transform_digest
            })
    
    # Store asset
    with Progress() as progress:
        task = progress.add_task("Storing asset...", total=1)
        asset_id = client.put_asset(data, kind=kind, metadata=metadata, parents=parents)
        progress.update(task, completed=1)
    
    console.print(f"[green]Asset stored successfully[/green]")
    console.print(f"Asset ID: [bold]{asset_id}[/bold]")


@app.command("get")
def get_asset(
    asset_id: str = typer.Argument(..., help="Asset ID"),
    output_file: Optional[Path] = typer.Option(None, help="Output file path"),
    metadata_only: bool = typer.Option(False, help="Only show metadata, not content"),
):
    """Retrieve an asset from AIFS."""
    # Get asset
    with Progress() as progress:
        task = progress.add_task("Retrieving asset...", total=1)
        asset = client.get_asset(asset_id)
        progress.update(task, completed=1)
    
    # Display asset info
    console.print(f"Asset ID: [bold]{asset_id}[/bold]")
    console.print(f"Kind: {asset['kind']}")
    console.print(f"Size: {asset['size']} bytes")
    console.print(f"Created at: {asset['created_at']}")
    
    # Display metadata
    console.print("\n[bold]Metadata:[/bold]")
    for key, value in asset['metadata'].items():
        console.print(f"  {key}: {value}")
    
    # Display lineage if present
    if asset.get('parents'):
        console.print("\n[bold]Lineage:[/bold]")
        for parent in asset['parents']:
            console.print(f"  Parent: {parent['asset_id']}")
            console.print(f"    Transform: {parent['transform_name']}")
            console.print(f"    Digest: {parent['transform_digest']}")
    
    # Write to file or display content if not metadata_only
    if not metadata_only:
        if output_file:
            with open(output_file, "wb") as f:
                f.write(asset['data'])
            console.print(f"\nContent written to [bold]{output_file}[/bold]")
        else:
            # Try to display content based on content type
            content_type = asset['metadata'].get('content_type', '')
            if content_type.startswith('text/') or content_type in [
                'application/json', 'application/xml'
            ]:
                try:
                    console.print("\n[bold]Content:[/bold]")
                    console.print(asset['data'].decode('utf-8'))
                except UnicodeDecodeError:
                    console.print("\n[yellow]Content is binary and cannot be displayed[/yellow]")
            else:
                console.print("\n[yellow]Content is binary and cannot be displayed[/yellow]")
                console.print(f"Use --output-file to save the content")


@app.command("search")
def vector_search(
    query_file: Path = typer.Argument(..., help="Path to file to use as query"),
    k: int = typer.Option(5, help="Number of results to return"),
    threshold: float = typer.Option(0.0, help="Similarity threshold (0-1)"),
):
    """Perform vector search in AIFS.
    
    Note: This is a simplified version that assumes embeddings are computed server-side.
    In a real implementation, you would compute embeddings client-side or have a separate
    embedding service.
    """
    # Check if file exists
    if not query_file.exists():
        console.print(f"[red]Error: File not found: {query_file}[/red]")
        sys.exit(1)
    
    # Read file
    with open(query_file, "rb") as f:
        data = f.read()
    
    # For demonstration purposes, create a random embedding
    # In a real implementation, you would compute a proper embedding
    console.print("[yellow]Note: Using random embedding for demonstration[/yellow]")
    query_embedding = np.random.rand(1536).astype(np.float32)
    
    # Perform search
    with Progress() as progress:
        task = progress.add_task("Searching...", total=1)
        results = client.vector_search(query_embedding, k=k)
        progress.update(task, completed=1)
    
    # Display results
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return
    
    table = Table(title="Search Results")
    table.add_column("#", style="dim")
    table.add_column("Asset ID", style="bold")
    table.add_column("Score")
    table.add_column("Description")
    
    for i, result in enumerate(results):
        score = result['score']
        if score < threshold:
            continue
        
        # Get asset metadata for description
        asset = client.get_asset(result['asset_id'], metadata_only=True)
        description = asset['metadata'].get('description', 'N/A')
        
        table.add_row(
            str(i + 1),
            result['asset_id'],
            f"{score:.4f}",
            description
        )
    
    console.print(table)


@app.command("snapshot")
def create_snapshot(
    namespace: str = typer.Option("default", help="Snapshot namespace"),
    asset_ids: List[str] = typer.Argument(..., help="Asset IDs to include in snapshot"),
    description: Optional[str] = typer.Option(None, help="Snapshot description"),
    metadata_file: Optional[Path] = typer.Option(None, help="Path to JSON metadata file"),
):
    """Create a snapshot in AIFS."""
    # Prepare metadata
    metadata = {}
    if metadata_file:
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
    
    if description:
        metadata["description"] = description
    
    # Create snapshot
    with Progress() as progress:
        task = progress.add_task("Creating snapshot...", total=1)
        snapshot = client.create_snapshot(namespace, asset_ids, metadata)
        progress.update(task, completed=1)
    
    console.print(f"[green]Snapshot created successfully[/green]")
    console.print(f"Snapshot ID: [bold]{snapshot['snapshot_id']}[/bold]")
    console.print(f"Merkle root: {snapshot['merkle_root']}")
    console.print(f"Assets: {len(asset_ids)}")


@app.command("get-snapshot")
def get_snapshot(
    snapshot_id: str = typer.Argument(..., help="Snapshot ID"),
):
    """Retrieve a snapshot from AIFS."""
    # Get snapshot
    with Progress() as progress:
        task = progress.add_task("Retrieving snapshot...", total=1)
        snapshot = client.get_snapshot(snapshot_id)
        progress.update(task, completed=1)
    
    # Display snapshot info
    console.print(f"Snapshot ID: [bold]{snapshot['snapshot_id']}[/bold]")
    console.print(f"Namespace: {snapshot['namespace']}")
    console.print(f"Created at: {snapshot['created_at']}")
    console.print(f"Merkle root: {snapshot['merkle_root']}")
    
    # Display metadata
    console.print("\n[bold]Metadata:[/bold]")
    for key, value in snapshot['metadata'].items():
        console.print(f"  {key}: {value}")
    
    # Display assets
    console.print(f"\n[bold]Assets ({len(snapshot['asset_ids'])}):[/bold]")
    for i, asset_id in enumerate(snapshot['asset_ids']):
        console.print(f"  {i+1}. {asset_id}")


@app.command("server")
def start_server(
    host: str = typer.Option("localhost", help="Server host"),
    port: int = typer.Option(50051, help="Server port"),
    storage_dir: Path = typer.Option("./aifs_data", help="Storage directory"),
):
    """Start AIFS server."""
    from aifs.server import serve
    
    # Create storage directory if it doesn't exist
    storage_dir = Path(storage_dir).absolute()
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"Starting AIFS server on {host}:{port}")
    console.print(f"Storage directory: {storage_dir}")
    console.print("Press Ctrl+C to stop")
    
    # Start server
    serve(host, port, storage_dir)


@app.command("mount")
def mount_fuse(
    mount_point: Path = typer.Argument(..., help="Mount point directory"),
    server: str = typer.Option("localhost:50051", help="AIFS server address"),
    namespace: str = typer.Option("default", help="Snapshot namespace"),
    foreground: bool = typer.Option(False, help="Run in foreground"),
):
    """Mount AIFS as a FUSE filesystem."""
    try:
        from aifs.fuse import mount
    except ImportError:
        console.print("[red]Error: FUSE support not available[/red]")
        console.print("Install fusepy package: pip install fusepy")
        sys.exit(1)
    
    # Create mount point if it doesn't exist
    mount_point = Path(mount_point).absolute()
    mount_point.mkdir(parents=True, exist_ok=True)
    
    console.print(f"Mounting AIFS at {mount_point}")
    console.print(f"Server: {server}")
    console.print(f"Namespace: {namespace}")
    console.print("Press Ctrl+C to unmount")
    
    # Mount filesystem
    mount(server, str(mount_point), namespace, foreground)


if __name__ == "__main__":
    try:
        app()
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)
    finally:
        if client:
            client.close()