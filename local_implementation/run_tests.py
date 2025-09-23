#!/usr/bin/env python3
"""AIFS Test Runner

Comprehensive test runner for AIFS implementation.
"""

import sys
import os
import subprocess
import time
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end_time = time.time()
    
    duration = end_time - start_time
    
    if result.returncode == 0:
        print(f"✅ SUCCESS ({duration:.2f}s)")
        if result.stdout:
            print("Output:")
            print(result.stdout)
    else:
        print(f"❌ FAILED ({duration:.2f}s)")
        print("Error:")
        print(result.stderr)
        if result.stdout:
            print("Output:")
            print(result.stdout)
    
    return result.returncode == 0, duration


def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'blake3', 'cryptography', 'grpcio', 'grpcio-status', 
        'grpcio-reflection', 'numpy', 'faiss-cpu', 'pytest'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            # Handle special cases for package names
            import_name = package.replace('-', '_')
            if package == 'grpcio':
                import_name = 'grpc'
            elif package == 'grpcio-status':
                import_name = 'grpc_status'
            elif package == 'grpcio-reflection':
                import_name = 'grpc_reflection'
            elif package == 'faiss-cpu':
                import_name = 'faiss'
            
            __import__(import_name)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ All dependencies available")
    return True


def run_tests():
    """Run all AIFS tests."""
    print("🧪 Running AIFS Test Suite")
    print("=" * 60)
    
    # Change to the correct directory
    os.chdir(Path(__file__).parent)
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Test categories
    test_categories = [
        {
            "name": "Core Functionality",
            "tests": [
                "tests/test_basic.py",
                "tests/test_asset_manager.py", 
                "tests/test_storage.py",
                "tests/test_merkle_tree.py",
                "tests/test_crypto.py",
                "tests/test_auth.py"
            ]
        },
        {
            "name": "New Features (BLAKE3 & URI)",
            "tests": [
                "tests/test_blake3_uri.py",
                "tests/test_merkle_blake3.py"
            ]
        },
        {
            "name": "Error Handling",
            "tests": [
                "tests/test_error_handling.py"
            ]
        },
        {
            "name": "Encryption & KMS",
            "tests": [
                "tests/test_encryption_kms.py"
            ]
        },
        {
            "name": "gRPC Server",
            "tests": [
                "tests/test_grpc_server.py"
            ]
        },
        {
            "name": "Built-in Services",
            "tests": [
                "tests/test_builtin_services.py",
                "tests/test_compression.py"
            ]
        }
    ]
    
    total_tests = 0
    passed_tests = 0
    total_duration = 0
    
    # Run each test category
    for category in test_categories:
        print(f"\n📁 {category['name']}")
        print("-" * 40)
        
        category_passed = 0
        category_total = len(category['tests'])
        
        for test_file in category['tests']:
            if os.path.exists(test_file):
                success, duration = run_command(
                    f"python -m pytest {test_file} -v --tb=short",
                    f"Running {test_file}"
                )
                total_duration += duration
                if success:
                    passed_tests += 1
                    category_passed += 1
                total_tests += 1
            else:
                print(f"⚠️  Test file not found: {test_file}")
        
        print(f"\n📊 {category['name']}: {category_passed}/{category_total} passed")
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "No tests run")
    print(f"Total Duration: {total_duration:.2f}s")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"\n❌ {total_tests - passed_tests} TESTS FAILED")
        return False


def run_specific_tests(test_pattern):
    """Run specific tests matching a pattern."""
    print(f"🔍 Running tests matching: {test_pattern}")
    
    success, duration = run_command(
        f"python -m pytest {test_pattern} -v --tb=short",
        f"Running tests matching '{test_pattern}'"
    )
    
    return success


def run_quick_tests():
    """Run quick tests (excluding slow gRPC server tests)."""
    print("⚡ Running Quick Tests")
    
    quick_tests = [
        "tests/test_blake3_uri.py",
        "tests/test_error_handling.py", 
        "tests/test_encryption_kms.py",
        "tests/test_merkle_blake3.py"
    ]
    
    total_passed = 0
    total_tests = len(quick_tests)
    
    for test_file in quick_tests:
        if os.path.exists(test_file):
            success, _ = run_command(
                f"python -m pytest {test_file} -v --tb=short",
                f"Running {test_file}"
            )
            if success:
                total_passed += 1
    
    print(f"\n📊 Quick Tests: {total_passed}/{total_tests} passed")
    return total_passed == total_tests


def main():
    """Main test runner."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "quick":
            success = run_quick_tests()
        elif command == "deps":
            success = check_dependencies()
        elif command.startswith("pattern:"):
            pattern = command.split(":", 1)[1]
            success = run_specific_tests(pattern)
        else:
            print(f"Unknown command: {command}")
            print("Usage: python run_tests.py [quick|deps|pattern:<pattern>]")
            success = False
    else:
        success = run_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()