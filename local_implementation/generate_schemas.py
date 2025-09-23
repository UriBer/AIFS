#!/usr/bin/env python3
"""
Generate protobuf and FlatBuffers schema files for AIFS asset kinds.

This script compiles the schema definitions into Python modules.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Command failed: {cmd}")
            print(f"   Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"❌ Exception running command: {cmd}")
        print(f"   Error: {e}")
        return False


def generate_protobuf_schemas():
    """Generate Python protobuf modules from .proto files."""
    print("🔧 Generating protobuf schemas...")
    
    schemas_dir = Path("aifs/schemas")
    proto_files = list(schemas_dir.glob("*.proto"))
    
    if not proto_files:
        print("⚠️  No .proto files found in aifs/schemas/")
        return False
    
    # Create output directory
    output_dir = schemas_dir / "generated"
    output_dir.mkdir(exist_ok=True)
    
    success = True
    for proto_file in proto_files:
        print(f"   📄 Processing {proto_file.name}...")
        
        # Generate Python protobuf files
        cmd = f"python -m grpc_tools.protoc --python_out={output_dir} --proto_path={schemas_dir} {proto_file.name}"
        if not run_command(cmd, cwd=schemas_dir):
            success = False
            continue
        
        # Generate gRPC service files (if any)
        cmd = f"python -m grpc_tools.protoc --grpc_python_out={output_dir} --proto_path={schemas_dir} {proto_file.name}"
        run_command(cmd, cwd=schemas_dir)  # Don't fail on this, not all proto files have services
        
        print(f"   ✅ Generated Python files for {proto_file.name}")
    
    if success:
        print("✅ Protobuf schemas generated successfully")
    else:
        print("❌ Some protobuf schemas failed to generate")
    
    return success


def generate_flatbuffers_schemas():
    """Generate Python FlatBuffers modules from .fbs files."""
    print("🔧 Generating FlatBuffers schemas...")
    
    schemas_dir = Path("aifs/schemas")
    fbs_files = list(schemas_dir.glob("*.fbs"))
    
    if not fbs_files:
        print("⚠️  No .fbs files found in aifs/schemas/")
        return False
    
    # Check if flatc is available
    if not run_command("flatc --version"):
        print("⚠️  FlatBuffers compiler (flatc) not found")
        print("   Install with: pip install flatbuffers")
        print("   Or download from: https://github.com/google/flatbuffers/releases")
        return False
    
    # Create output directory
    output_dir = schemas_dir / "generated"
    output_dir.mkdir(exist_ok=True)
    
    success = True
    for fbs_file in fbs_files:
        print(f"   📄 Processing {fbs_file.name}...")
        
        # Generate Python FlatBuffers files
        cmd = f"flatc --python --gen-mutable --gen-object-api -o {output_dir} {fbs_file}"
        if not run_command(cmd, cwd=schemas_dir):
            success = False
            continue
        
        print(f"   ✅ Generated Python files for {fbs_file.name}")
    
    if success:
        print("✅ FlatBuffers schemas generated successfully")
    else:
        print("❌ Some FlatBuffers schemas failed to generate")
    
    return success


def create_init_files():
    """Create __init__.py files for the generated modules."""
    print("📁 Creating __init__.py files...")
    
    generated_dir = Path("aifs/schemas/generated")
    if not generated_dir.exists():
        print("⚠️  Generated directory not found")
        return False
    
    # Create __init__.py for generated directory
    init_file = generated_dir / "__init__.py"
    with open(init_file, 'w') as f:
        f.write('"""Generated schema files for AIFS asset kinds."""\n')
    
    # Create __init__.py for schemas directory
    schemas_init = Path("aifs/schemas/__init__.py")
    with open(schemas_init, 'w') as f:
        f.write('"""AIFS schema definitions for asset kinds."""\n')
    
    print("✅ __init__.py files created")
    return True


def update_asset_kinds_imports():
    """Update asset_kinds.py to use generated modules."""
    print("🔄 Updating asset_kinds.py imports...")
    
    asset_kinds_file = Path("aifs/asset_kinds.py")
    if not asset_kinds_file.exists():
        print("⚠️  asset_kinds.py not found")
        return False
    
    # Read current file
    with open(asset_kinds_file, 'r') as f:
        content = f.read()
    
    # Update imports to use generated modules
    old_import = "from .schemas import nd_array_pb2, artifact_pb2"
    new_import = "from .schemas.generated import nd_array_pb2, artifact_pb2"
    
    if old_import in content:
        content = content.replace(old_import, new_import)
        
        # Write updated file
        with open(asset_kinds_file, 'w') as f:
            f.write(content)
        
        print("✅ Updated asset_kinds.py imports")
        return True
    else:
        print("⚠️  Import statement not found in asset_kinds.py")
        return False


def main():
    """Main function to generate all schemas."""
    print("🚀 AIFS Schema Generation")
    print("=" * 40)
    print()
    
    # Check if we're in the right directory
    if not Path("aifs/schemas").exists():
        print("❌ Please run this script from the local_implementation directory")
        print("   Expected structure: local_implementation/aifs/schemas/")
        return False
    
    success = True
    
    # Generate protobuf schemas
    if not generate_protobuf_schemas():
        success = False
    
    print()
    
    # Generate FlatBuffers schemas
    if not generate_flatbuffers_schemas():
        success = False
    
    print()
    
    # Create init files
    if not create_init_files():
        success = False
    
    print()
    
    # Update imports
    if not update_asset_kinds_imports():
        success = False
    
    print()
    
    if success:
        print("✅ All schemas generated successfully!")
        print()
        print("📚 Next steps:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Test the asset kinds: python examples/asset_kinds_demo.py")
        print("   3. Run the AIFS server: aifs server --dev")
    else:
        print("❌ Some schemas failed to generate")
        print("   Check the error messages above and install missing dependencies")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
