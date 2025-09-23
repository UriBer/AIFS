#!/usr/bin/env python3
"""
Test runner for AIFS Strong Causality tests.

Runs comprehensive tests for the strong causality implementation and provides detailed reporting.
"""

import unittest
import sys
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from tests.test_strong_causality import (
    TestTransactionManager, TestStrongCausalityManager, 
    TestAssetManagerStrongCausality, TestStrongCausalityEdgeCases
)


def run_strong_causality_tests():
    """Run all strong causality tests with detailed reporting."""
    print("🔒 AIFS Strong Causality Test Suite")
    print("=" * 50)
    print()
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestTransactionManager,
        TestStrongCausalityManager,
        TestAssetManagerStrongCausality,
        TestStrongCausalityEdgeCases
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    end_time = time.time()
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    print(f"Total Tests: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Duration: {end_time - start_time:.2f} seconds")
    
    if result.failures:
        print("\n❌ Failed Tests:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print("\n💥 Error Tests:")
        for test, traceback in result.errors:
            error_lines = traceback.split('\\n')
            error_msg = error_lines[-2] if len(error_lines) > 1 else "Unknown error"
            print(f"  - {test}: {error_msg}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return True
    else:
        print(f"\n❌ {len(result.failures) + len(result.errors)} test(s) failed")
        return False


def run_specific_tests(test_names):
    """Run specific test classes or methods."""
    print(f"🔒 Running specific tests: {', '.join(test_names)}")
    print("=" * 50)
    print()
    
    test_suite = unittest.TestSuite()
    
    # Map test names to classes
    test_class_map = {
        'transaction': TestTransactionManager,
        'causality': TestStrongCausalityManager,
        'integration': TestAssetManagerStrongCausality,
        'edge_cases': TestStrongCausalityEdgeCases
    }
    
    for test_name in test_names:
        if test_name in test_class_map:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class_map[test_name])
            test_suite.addTests(tests)
        else:
            print(f"⚠️  Unknown test: {test_name}")
            print(f"   Available tests: {', '.join(test_class_map.keys())}")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run AIFS Strong Causality tests")
    parser.add_argument('--tests', nargs='+', 
                       choices=['transaction', 'causality', 'integration', 'edge_cases'],
                       help='Specific tests to run')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.tests:
        success = run_specific_tests(args.tests)
    else:
        success = run_strong_causality_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
