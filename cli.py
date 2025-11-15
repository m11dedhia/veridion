"""
Command-line interface for AI QA Engineer.
"""
import argparse
import json
import os
import sys
from dotenv import load_dotenv
from agent.qa_agent import QAAgent, DEFAULT_TEST_SCENARIOS
from sentry.init_sentry import init_sentry

# Load environment variables
load_dotenv()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI QA Engineer - Autonomous browser testing with AI"
    )
    
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="URL to test"
    )
    
    parser.add_argument(
        "--scenario",
        type=str,
        required=True,
        help="Test scenario description (e.g., 'Login and navigate to dashboard')"
    )
    
    parser.add_argument(
        "--llm-provider",
        type=str,
        choices=["openai", "anthropic"],
        default=os.getenv("LLM_PROVIDER", "openai"),
        help="LLM provider to use (default: openai)"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for LLM provider (or set via env vars)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)"
    )
    
    parser.add_argument(
        "--sentry-dsn",
        type=str,
        default=None,
        help="Sentry DSN for error logging"
    )
    
    args = parser.parse_args()
    
    # Initialize Sentry
    if args.sentry_dsn:
        init_sentry(dsn=args.sentry_dsn)
    else:
        init_sentry()
    
    # Get API key
    api_key = args.api_key
    if not api_key:
        if args.llm_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
        else:
            api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print(f"Error: {args.llm_provider.upper()}_API_KEY not set")
        sys.exit(1)
    
    # Initialize agent
    agent = QAAgent(
        llm_provider=args.llm_provider,
        api_key=api_key
    )
    
    # Run test
    print(f"Running test on {args.url}...")
    print(f"Scenario: {args.scenario}\n")
    
    result = agent.run_test_sync(args.scenario, args.url)
    
    # Output results
    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        print_output_text(result)
    
    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


def print_output_text(result: dict):
    """Print results in human-readable text format."""
    print("=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"URL: {result['url']}")
    print(f"Scenario: {result['scenario']}")
    print(f"Status: {'✓ PASSED' if result['success'] else '✗ FAILED'}")
    print()
    
    if not result["success"]:
        print("ERROR:")
        print(f"  {result['error']}")
        print()
        
        if result.get("traceback"):
            print("TRACEBACK:")
            print(result["traceback"])
            print()
        
        if result.get("analysis"):
            print("LLM ANALYSIS:")
            print(result["analysis"])
            print()
    
    print("=" * 60)


if __name__ == "__main__":
    main()

