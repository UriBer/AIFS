#!/usr/bin/env python3
"""Test runner for Ed25519 signature implementation tests.

This script runs the comprehensive test suite for the Ed25519 signature
implementation according to the AIFS architecture specification.
"""

import sys
import os
import argparse
import unittest
from pathlib import Path

# Add the local implementation to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from tests.test_ed25519_signatures import (
    TestCryptoManager,
    TestMetadataStoreEd25519,
    TestAssetManagerEd25519,
    TestEd25519EdgeCases
)


def run_tests(test_classes=None, verbose=False):
    """Run the Ed25519 signature tests.
    
    Args:
        test_classes: List of test classes to run (None for all)
        verbose: Whether to run in verbose mode
        
    Returns:
        TestResult object
    """
    # Create test suite
    suite = unittest.TestSuite()
    
    if test_classes is None:
        test_classes = [
            TestCryptoManager,
            TestMetadataStoreEd25519,
            TestAssetManagerEd25519,
            TestEd25519EdgeCases
        ]
    
    # Add test classes to suite
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
    result = runner.run(suite)
    
    return result


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Run Ed25519 signature implementation tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Categories:
  crypto        - Test CryptoManager class
  metadata      - Test MetadataStore with Ed25519 integration
  asset         - Test AssetManager with Ed25519 integration
  edge_cases    - Test edge cases and error handling

Examples:
  python run_ed25519_tests.py                    # Run all tests
  python run_ed25519_tests.py --tests crypto     # Run only crypto tests
  python run_ed25519_tests.py --verbose          # Run with verbose output
        """
    )
    
    parser.add_argument(
        "--tests",
        nargs="+",
        choices=["crypto", "metadata", "asset", "edge_cases"],
        help="Specific test categories to run"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests in verbose mode"
    )
    
    args = parser.parse_args()
    
    # Map test categories to test classes
    test_class_map = {
        "crypto": [TestCryptoManager],
        "metadata": [TestMetadataStoreEd25519],
        "asset": [TestAssetManagerEd25519],
        "edge_cases": [TestEd25519EdgeCases]
    }
    
    # Determine which test classes to run
    if args.tests:
        test_classes = []
        for category in args.tests:
            test_classes.extend(test_class_map[category])
    else:
        test_classes = None
    
    print("🔐 Ed25519 Signature Implementation Tests")
    print("=" * 50)
    
    if args.tests:
        print(f"Running tests: {', '.join(args.tests)}")
    else:
        print("Running all tests")
    
    print()
    
    # Run tests
    result = run_tests(test_classes, args.verbose)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    passed = total_tests - failures - errors - skipped
    
    print(f"Total tests: {total_tests}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failures}")
    print(f"💥 Errors: {errors}")
    print(f"⏭️  Skipped: {skipped}")
    
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
    
    # Print success message
    if failures == 0 and errors == 0:
        print("\n🎉 All Ed25519 signature tests passed!")
        print("✅ Ed25519 implementation is compliant with AIFS specification")
        return 0
    else:
        print(f"\n❌ {failures + errors} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
