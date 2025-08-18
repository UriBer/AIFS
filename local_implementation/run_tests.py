#!/usr/bin/env python3
"""Test runner for AIFS local implementation."""

import sys
import os
import unittest
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_all_tests():
    """Run all tests for the AIFS implementation."""
    # Get the tests directory
    tests_dir = Path(__file__).parent / "tests"
    
    # Discover and run all tests
    loader = unittest.TestLoader()
    suite = loader.discover(tests_dir, pattern="test_*.py")
    
    # Create test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run tests
    print("Running AIFS implementation tests...")
    print("=" * 50)
    
    result = runner.run(suite)
    
    # Print summary
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
    
    return result.wasSuccessful()

def run_specific_test(test_name):
    """Run a specific test module."""
    # Get the tests directory
    tests_dir = Path(__file__).parent / "tests"
    
    # Import and run specific test
    test_file = tests_dir / f"test_{test_name}.py"
    if not test_file.exists():
        print(f"Test file {test_file} not found!")
        return False
    
    # Import the test module
    test_module_name = f"tests.test_{test_name}"
    test_module = __import__(test_module_name, fromlist=["*"])
    
    # Run the tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(test_module)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def main():
    """Main function."""
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        success = run_specific_test(test_name)
    else:
        # Run all tests
        success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
