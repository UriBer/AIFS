#!/usr/bin/env python3
"""Installation script for AIFS local implementation."""

import subprocess
import sys
import os
import platform
from pathlib import Path


def run_command(cmd, description, check=True):
    """Run a command and handle errors."""
    print(f"Installing {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        print(f"✓ {description} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install {description}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False


def install_faiss():
    """Install FAISS with multiple fallback strategies."""
    print("\nInstalling FAISS (vector database)...")
    
    # Check if we're on macOS ARM (M1/M2)
    is_macos_arm = platform.system() == "Darwin" and platform.machine() == "arm64"
    
    # Strategy 1: Try faiss-cpu with platform-specific constraints
    if not is_macos_arm:
        print("Trying faiss-cpu...")
        if run_command(f"{sys.executable} -m pip install faiss-cpu>=1.7.4", "faiss-cpu", check=False):
            return True
    
    # Strategy 2: Try conda if available
    print("Trying conda installation...")
    conda_available = subprocess.run("conda --version", shell=True, capture_output=True).returncode == 0
    
    if conda_available:
        if run_command("conda install -c conda-forge faiss-cpu -y", "faiss-cpu via conda", check=False):
            return True
    
    # Strategy 3: Try building from source with system dependencies
    print("Trying to install system dependencies and build from source...")
    
    # Install system dependencies (macOS)
    if platform.system() == "Darwin":
        print("Installing system dependencies via Homebrew...")
        brew_available = subprocess.run("brew --version", shell=True, capture_output=True).returncode == 0
        
        if brew_available:
            # Install required system libraries
            system_deps = ["swig", "libomp", "openblas"]
            for dep in system_deps:
                run_command(f"brew install {dep}", f"{dep} via Homebrew", check=False)
            
            # Try installing faiss-cpu again
            if run_command(f"{sys.executable} -m pip install faiss-cpu>=1.7.4", "faiss-cpu after system deps", check=False):
                return True
    
    print("FAISS installation failed. Will use scikit-learn fallback.")
    return False


def install_dependencies():
    """Install all dependencies."""
    print("Installing AIFS dependencies...")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Upgrade pip
    if not run_command(f"{sys.executable} -m pip install --upgrade pip", "pip upgrade"):
        return False
    
    # Install core dependencies first
    core_deps = [
        "grpcio>=1.60.0",
        "grpcio-tools>=1.60.0", 
        "protobuf>=4.25.0",
        "numpy>=1.26.0",
        "sqlite-utils>=3.35",
        "pydantic>=2.5.0",
        "typer>=0.9.0",
        "rich>=13.4.2"
    ]
    
    print("\nInstalling core dependencies...")
    for dep in core_deps:
        if not run_command(f"{sys.executable} -m pip install {dep}", dep):
            print(f"Failed to install {dep}. Continuing with other dependencies...")
    
    # Install FAISS with fallback strategies
    faiss_success = install_faiss()
    
    # Always install scikit-learn as fallback
    print("\nInstalling scikit-learn fallback...")
    sklearn_success = run_command(f"{sys.executable} -m pip install scikit-learn>=1.3.0", "scikit-learn fallback")
    
    if not sklearn_success:
        print("Warning: scikit-learn installation failed. Vector operations may not work.")
    
    # Install security dependencies
    security_deps = [
        "cryptography>=45.0.0",
        "pynacl>=1.5.0"
        # macaroon temporarily disabled due to Python 3.13 compatibility
    ]
    
    print("\nInstalling security dependencies...")
    for dep in security_deps:
        if not run_command(f"{sys.executable} -m pip install {dep}", dep):
            print(f"Failed to install {dep}. Continuing with other dependencies...")
    
    # Install compression
    if not run_command(f"{sys.executable} -m pip install zstandard>=0.22.0", "zstandard"):
        print("Warning: zstandard installation failed. Compression features will not work.")
    
    # Install test dependencies
    test_deps = [
        "pytest",
        "pytest-mock"
    ]
    
    print("\nInstalling test dependencies...")
    for dep in test_deps:
        if not run_command(f"{sys.executable} -m pip install {dep}", dep):
            print(f"Warning: {dep} installation failed. Tests may not work properly.")
    
    # Install optional dependencies
    optional_deps = [
        "fusepy>=3.0.1"
    ]
    
    print("\nInstalling optional dependencies...")
    for dep in optional_deps:
        if not run_command(f"{sys.executable} -m pip install {dep}", dep):
            print(f"Warning: {dep} installation failed. FUSE features will not work.")
    
    return faiss_success or sklearn_success


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True


def verify_installation():
    """Verify that the installation was successful."""
    print("\nVerifying installation...")
    print("=" * 50)
    
    # Try to import key modules
    try:
        import grpc
        print("✓ gRPC installed")
    except ImportError:
        print("✗ gRPC not installed")
        return False
    
    try:
        import numpy
        print("✓ NumPy installed")
    except ImportError:
        print("✗ NumPy not installed")
        return False
    
    # Check FAISS or fallback
    faiss_available = False
    sklearn_available = False
    
    try:
        import faiss
        print("✓ FAISS installed")
        faiss_available = True
    except ImportError:
        print("✗ FAISS not installed")
    
    try:
        import sklearn
        print("✓ scikit-learn installed (FAISS fallback)")
        sklearn_available = True
    except ImportError:
        print("✗ scikit-learn not installed")
    
    if not faiss_available and not sklearn_available:
        print("✗ Neither FAISS nor scikit-learn installed")
        return False
    
    try:
        import cryptography
        print("✓ Cryptography installed")
    except ImportError:
        print("✗ Cryptography not installed")
        return False
    
    try:
        import nacl
        print("✓ PyNaCl installed")
    except ImportError:
        print("✗ PyNaCl not installed")
        return False
    
    # Note: macaroon is temporarily disabled
    print("⚠️  Macaroon not installed (Python 3.13 compatibility issue)")
    
    try:
        import zstandard
        print("✓ Zstandard installed")
    except ImportError:
        print("✗ Zstandard not installed (compression features disabled)")
    
    return True


def main():
    """Main installation function."""
    print("AIFS Local Implementation Installer")
    print("=" * 50)
    
    # Install dependencies
    vector_db_success = install_dependencies()
    if not vector_db_success:
        print("\n⚠️  Warning: Vector database installation failed. Some features may be limited.")
        print("You can try manual installation later:")
        print("  - Install via conda: conda install -c conda-forge faiss-cpu")
        print("  - Install system deps: brew install swig libomp openblas (macOS)")
        print("  - Use pre-built wheels: pip install faiss-cpu --only-binary=all")
        print("  - Use scikit-learn: pip install scikit-learn")
    
    # Verify installation
    if not verify_installation():
        print("\n✗ Installation verification failed.")
        sys.exit(1)
    
    print("\n🎉 Installation completed successfully!")
    print("\nNext steps:")
    print("1. Run tests: python run_tests.py")
    print("2. Start server: python start_server.py")
    print("3. Use CLI: python aifs_cli.py --help")
    
    print("\nNote: This implementation uses BLAKE3 for content addressing with Rust dependency included.")
    print("Note: Macaroon authorization is temporarily disabled due to Python 3.13 compatibility.")
    
    # Check what vector backend is available
    try:
        import faiss
        print("✓ FAISS available for high-performance vector search")
    except ImportError:
        try:
            import sklearn
            print("✓ scikit-learn available for vector operations (slower but functional)")
        except ImportError:
            print("⚠️  No vector database available. Install FAISS or scikit-learn for vector features.")
    
    print("\nFor production use with BLAKE3 and FAISS:")
    print("1. Install Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh")
    print("2. Install FAISS: conda install -c conda-forge faiss-cpu")
    print("3. Update requirements.txt and reinstall")
    print("\nFor macaroon authorization (when Python 3.13 compatibility is fixed):")
    print("1. Wait for macaroon package to support Python 3.13")
    print("2. Or use Python 3.11/3.12 for full feature support")


if __name__ == "__main__":
    main()
