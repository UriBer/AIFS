#!/usr/bin/env python3
"""Generate HTML documentation from AIFS proto files."""

import os
import subprocess
import sys
from pathlib import Path

def install_protoc_gen_doc():
    """Install protoc-gen-doc if not available."""
    try:
        subprocess.run(["protoc-gen-doc", "--version"], check=True, capture_output=True)
        print("protoc-gen-doc is already installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing protoc-gen-doc...")
        subprocess.run([
            "go", "install", "github.com/pseudomuto/protoc-gen-doc/cmd/protoc-gen-doc@latest"
        ], check=True)

def generate_html_docs():
    """Generate HTML documentation from proto files."""
    proto_file = Path("aifs/proto/aifs.proto")
    
    if not proto_file.exists():
        print(f"Proto file not found: {proto_file}")
        return False
    
    # Generate HTML documentation
    cmd = [
        "protoc",
        f"--proto_path={proto_file.parent}",
        f"--doc_out=docs",
        f"--doc_opt=html,index.html",
        str(proto_file)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"HTML documentation generated in docs/index.html")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error generating docs: {e}")
        return False

def generate_markdown_docs():
    """Generate Markdown documentation from proto files."""
    proto_file = Path("aifs/proto/aifs.proto")
    
    if not proto_file.exists():
        print(f"Proto file not found: {proto_file}")
        return False
    
    # Generate Markdown documentation
    cmd = [
        "protoc",
        f"--proto_path={proto_file.parent}",
        f"--doc_out=docs",
        f"--doc_opt=markdown,api.md",
        str(proto_file)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Markdown documentation generated in docs/api.md")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error generating docs: {e}")
        return False

def main():
    """Main function."""
    print("Generating AIFS API documentation...")
    
    # Create docs directory
    os.makedirs("docs", exist_ok=True)
    
    # Try to generate HTML docs
    if generate_html_docs():
        print("✅ HTML documentation generated successfully!")
        print("📖 Open docs/index.html in your browser to view the API documentation")
    
    # Try to generate Markdown docs
    if generate_markdown_docs():
        print("✅ Markdown documentation generated successfully!")
        print("📝 View docs/api.md for the API documentation")

if __name__ == "__main__":
    main()
