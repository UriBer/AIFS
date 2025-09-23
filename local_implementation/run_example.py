#!/usr/bin/env python3
"""Convenience script to run the basic usage example.

This script can be run from any directory and will automatically:
1. Start the AIFS server if it's not running
2. Run the basic usage example
3. Clean up when done
"""

import subprocess
import sys
import time
import os
import signal
import psutil

def is_server_running():
    """Check if the AIFS server is already running."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and 'start_server.py' in ' '.join(proc.info['cmdline']):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def start_server():
    """Start the AIFS server."""
    print("🚀 Starting AIFS server...")
    return subprocess.Popen([sys.executable, 'start_server.py'], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)

def run_example():
    """Run the basic usage example."""
    print("📚 Running basic usage example...")
    result = subprocess.run([sys.executable, 'examples/basic_usage.py'], 
                           capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    
    return result.returncode == 0

def main():
    """Main function."""
    # Change to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    server_process = None
    
    try:
        # Check if server is already running
        if not is_server_running():
            server_process = start_server()
            print("⏳ Waiting for server to start...")
            time.sleep(5)  # Give server time to start
        else:
            print("✅ AIFS server is already running")
        
        # Run the example
        success = run_example()
        
        if success:
            print("\n🎉 Example completed successfully!")
        else:
            print("\n❌ Example failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        # Clean up server if we started it
        if server_process:
            print("\n🧹 Cleaning up server...")
            try:
                server_process.terminate()
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("✅ Server stopped")

if __name__ == "__main__":
    main()
