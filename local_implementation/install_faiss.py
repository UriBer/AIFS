#!/usr/bin/env python3
"""FAISS Installation Helper Script

This script helps install FAISS with various strategies when the main installer fails.
"""

import subprocess
import sys
import platform
import os


def run_command(cmd, description):
    """Run a command and show output."""
    print(f"Running: {cmd}")
    print(f"Description: {description}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ Success: {description}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed: {description}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False


def check_system():
    """Check system information."""
    print("System Information:")
    print(f"  OS: {platform.system()}")
    print(f"  Architecture: {platform.machine()}")
    print(f"  Python: {sys.version}")
    print(f"  Platform: {platform.platform()}")
    print()


def install_via_conda():
    """Try installing FAISS via conda."""
    print("Strategy 1: Installing FAISS via conda...")
    
    # Check if conda is available
    conda_check = subprocess.run("conda --version", shell=True, capture_output=True)
    if conda_check.returncode != 0:
        print("✗ Conda not available. Install Anaconda or Miniconda first.")
        return False
    
    print("✓ Conda found, installing FAISS...")
    
    # Try conda-forge channel
    if run_command("conda install -c conda-forge faiss-cpu -y", "FAISS via conda-forge"):
        return True
    
    # Try main channel
    if run_command("conda install faiss-cpu -y", "FAISS via main conda channel"):
        return True
    
    return False


def install_via_pip_wheels():
    """Try installing FAISS via pip with pre-built wheels."""
    print("Strategy 2: Installing FAISS via pip with pre-built wheels...")
    
    # Try different wheel sources
    wheel_sources = [
        "faiss-cpu",
        "faiss-cpu --only-binary=all",
        "faiss-cpu --index-url https://pypi.org/simple/",
        "faiss-cpu --extra-index-url https://pypi.org/simple/"
    ]
    
    for source in wheel_sources:
        if run_command(f"{sys.executable} -m pip install {source}", f"FAISS via pip: {source}"):
            return True
    
    return False


def install_system_dependencies_macos():
    """Install system dependencies on macOS."""
    print("Strategy 3: Installing system dependencies on macOS...")
    
    # Check if Homebrew is available
    brew_check = subprocess.run("brew --version", shell=True, capture_output=True)
    if brew_check.returncode != 0:
        print("✗ Homebrew not available. Install Homebrew first:")
        print("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        return False
    
    print("✓ Homebrew found, installing system dependencies...")
    
    # Install required system libraries
    system_deps = [
        "swig",
        "libomp", 
        "openblas",
        "cmake"
    ]
    
    for dep in system_deps:
        if not run_command(f"brew install {dep}", f"{dep} via Homebrew"):
            print(f"Warning: Failed to install {dep}")
    
    # Try installing FAISS again
    print("Trying to install FAISS after system dependencies...")
    if run_command(f"{sys.executable} -m pip install faiss-cpu", "FAISS after system deps"):
        return True
    
    return False


def install_system_dependencies_linux():
    """Install system dependencies on Linux."""
    print("Strategy 3: Installing system dependencies on Linux...")
    
    # Detect package manager
    package_managers = [
        ("apt-get", "apt-get update && apt-get install -y"),
        ("yum", "yum install -y"),
        ("dnf", "dnf install -y"),
        ("zypper", "zypper install -y")
    ]
    
    for pkg_mgr, install_cmd in package_managers:
        if subprocess.run(f"{pkg_mgr} --version", shell=True, capture_output=True).returncode == 0:
            print(f"✓ Found package manager: {pkg_mgr}")
            
            # Install required system libraries
            system_deps = [
                "swig",
                "libomp-dev",
                "openblas-dev",
                "cmake",
                "build-essential"
            ]
            
            for dep in system_deps:
                if not run_command(f"{install_cmd} {dep}", f"{dep} via {pkg_mgr}"):
                    print(f"Warning: Failed to install {dep}")
            
            # Try installing FAISS again
            print("Trying to install FAISS after system dependencies...")
            if run_command(f"{sys.executable} -m pip install faiss-cpu", "FAISS after system deps"):
                return True
            
            break
    
    return False


def install_from_source():
    """Install FAISS from source."""
    print("Strategy 4: Installing FAISS from source...")
    
    # Clone FAISS repository
    if not os.path.exists("faiss"):
        if not run_command("git clone https://github.com/facebookresearch/faiss.git", "Clone FAISS repository"):
            return False
    
    # Navigate to faiss directory
    os.chdir("faiss")
    
    # Build and install
    build_steps = [
        "mkdir -p build && cd build",
        "cmake .. -DFAISS_ENABLE_GPU=OFF -DFAISS_ENABLE_PYTHON=ON -DBUILD_TESTING=OFF",
        "make -j$(nproc)",
        "make install"
    ]
    
    for step in build_steps:
        if not run_command(step, f"Build step: {step}"):
            return False
    
    # Install Python bindings
    os.chdir("faiss/python")
    if run_command(f"{sys.executable} setup.py install", "Install Python bindings"):
        return True
    
    return False


def verify_installation():
    """Verify that FAISS is properly installed."""
    print("\nVerifying FAISS installation...")
    
    try:
        import faiss
        print("✓ FAISS imported successfully")
        
        # Test basic functionality
        index = faiss.IndexFlatL2(128)
        print("✓ FAISS index creation successful")
        
        # Test search
        vectors = faiss.randn(10, 128).astype('float32')
        index.add(vectors)
        print("✓ FAISS vector addition successful")
        
        D, I = index.search(vectors[:1], 5)
        print("✓ FAISS search successful")
        
        print(f"✓ FAISS is fully functional!")
        print(f"  Version: {faiss.__version__}")
        print(f"  Build: {faiss.get_compile_options()}")
        
        return True
        
    except ImportError as e:
        print(f"✗ FAISS import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ FAISS functionality test failed: {e}")
        return False


def main():
    """Main installation function."""
    print("FAISS Installation Helper")
    print("=" * 50)
    
    check_system()
    
    print("This script will try multiple strategies to install FAISS.")
    print("FAISS is required for high-performance vector similarity search.")
    print()
    
    # Strategy 1: Conda
    if install_via_conda():
        if verify_installation():
            print("\n🎉 FAISS installed successfully via conda!")
            return
    
    # Strategy 2: Pip wheels
    if install_via_pip_wheels():
        if verify_installation():
            print("\n🎉 FAISS installed successfully via pip!")
            return
    
    # Strategy 3: System dependencies
    if platform.system() == "Darwin":  # macOS
        if install_system_dependencies_macos():
            if verify_installation():
                print("\n🎉 FAISS installed successfully after system dependencies!")
                return
    elif platform.system() == "Linux":
        if install_system_dependencies_linux():
            if verify_installation():
                print("\n🎉 FAISS installed successfully after system dependencies!")
                return
    
    # Strategy 4: Build from source
    print("\nTrying to build FAISS from source...")
    if install_from_source():
        if verify_installation():
            print("\n🎉 FAISS built and installed successfully from source!")
            return
    
    print("\n❌ All FAISS installation strategies failed.")
    print("\nAlternative solutions:")
    print("1. Use the scikit-learn fallback (already installed)")
    print("2. Install Anaconda/Miniconda and try again")
    print("3. Use Docker with pre-built FAISS image")
    print("4. Contact system administrator for help")
    
    print("\nThe AIFS system will work with scikit-learn, but vector search will be slower.")


if __name__ == "__main__":
    main()
