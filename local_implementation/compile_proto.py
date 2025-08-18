#!/usr/bin/env python3
"""Compile protobuf definitions for AIFS.

This script compiles the protobuf definitions in aifs/proto/aifs.proto
and generates the Python code needed for the gRPC implementation.
"""

import os
import subprocess
import sys


def main():
    """Compile protobuf definitions."""
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set proto file path
    proto_file = os.path.join(script_dir, "aifs", "proto", "aifs.proto")
    
    # Check if proto file exists
    if not os.path.exists(proto_file):
        print(f"Error: Proto file not found: {proto_file}")
        sys.exit(1)
    
    # Create __init__.py in proto directory if it doesn't exist
    proto_dir = os.path.dirname(proto_file)
    init_file = os.path.join(proto_dir, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("""Proto package for AIFS.""")

    
    # Compile proto file
    try:
        cmd = [
            sys.executable, "-m", "grpc_tools.protoc",
            f"--proto_path={script_dir}",
            f"--python_out={script_dir}",
            f"--grpc_python_out={script_dir}",
            proto_file
        ]
        subprocess.check_call(cmd)
        print(f"Successfully compiled {proto_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error compiling proto file: {e}")
        sys.exit(1)
    
    # Fix imports in generated files
    pb2_file = proto_file.replace(".proto", "_pb2.py")
    pb2_grpc_file = proto_file.replace(".proto", "_pb2_grpc.py")
    
    # Fix imports in *_pb2_grpc.py
    if os.path.exists(pb2_grpc_file):
        with open(pb2_grpc_file, "r") as f:
            content = f.read()
        
        # Replace import statement
        content = content.replace(
            "import aifs.proto.aifs_pb2 as aifs_dot_proto_dot_aifs__pb2",
            "from . import aifs_pb2 as aifs_dot_proto_dot_aifs__pb2"
        )
        
        with open(pb2_grpc_file, "w") as f:
            f.write(content)
    
    print("Done!")


if __name__ == "__main__":
    main()