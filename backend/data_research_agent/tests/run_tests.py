#!/usr/bin/env python3
"""
Test runner script for research agent tests.

This script provides an easy way to run the research agent tests with various options.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type="all", verbose=False, coverage=False, specific_test=None):
    """Run tests with specified options."""
    
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=research_graph", "--cov-report=html", "--cov-report=term"])
    
    if test_type == "unit":
        cmd.append("-m unit")
    elif test_type == "integration":
        cmd.append("-m integration")
    elif test_type == "async":
        cmd.append("-k async")
    elif test_type == "scenario":
        cmd.append("test_research_nodes.py::TestAIAgentBusinessScenario")
    elif specific_test:
        cmd.append(f"test_research_nodes.py::{specific_test}")
    else:
        cmd.append("test_research_nodes.py")
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, cwd=Path(__file__).parent)
        print("\n✅ All tests passed!")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with return code: {e.returncode}")
        return e.returncode


def main():
    """Main function to parse arguments and run tests."""
    
    parser = argparse.ArgumentParser(
        description="Run research agent tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                              # Run all tests
  python run_tests.py --type unit                  # Run unit tests only
  python run_tests.py --type async                 # Run async tests only
  python run_tests.py --type scenario              # Run business scenario tests
  python run_tests.py --coverage                   # Run with coverage report
  python run_tests.py --test TestGenerateReportPlan # Run specific test class
  python run_tests.py --verbose --coverage         # Verbose output with coverage
        """
    )
    
    parser.add_argument(
        "--type",
        choices=["all", "unit", "integration", "async", "scenario"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests in verbose mode"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run tests with coverage report"
    )
    
    parser.add_argument(
        "--test", "-t",
        help="Run a specific test class (e.g., TestGenerateReportPlan)"
    )
    
    args = parser.parse_args()
    
    # Check if pytest is available
    try:
        subprocess.run(
            ["python", "-m", "pytest", "--version"], 
            check=True, capture_output=True
        )
    except subprocess.CalledProcessError:
        print("❌ pytest not found. Please install test dependencies:")
        print("pip install -r requirements.txt")
        return 1
    
    return run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage,
        specific_test=args.test
    )


if __name__ == "__main__":
    sys.exit(main()) 