"""
AI QA Agent using Browser Use for autonomous browser testing.
"""
import asyncio
import traceback
from typing import Dict, Optional, Any
from browser_use import Agent, Browser, BrowserConfig
from sentry.init_sentry import log_error_to_sentry
from llm_analysis.analyze_failure import analyze_failure


class QAAgent:
    """AI-powered QA agent that runs browser tests using Browser Use."""
    
    def __init__(self, llm_provider: str = "openai", api_key: Optional[str] = None):
        """
        Initialize the QA Agent.
        
        Args:
            llm_provider: Either "openai" or "anthropic"
            api_key: API key for the LLM provider
        """
        self.llm_provider = llm_provider
        self.api_key = api_key
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=True
        )
        
    async def run_test(self, test_scenario: str, url: str) -> Dict[str, Any]:
        """
        Run a test scenario on a given URL.
        
        Args:
            test_scenario: Description of what to test (e.g., "Login and navigate to dashboard")
            url: URL to test
            
        Returns:
            Dictionary with test results, including success status, errors, and analysis
        """
        result = {
            "success": False,
            "url": url,
            "scenario": test_scenario,
            "error": None,
            "traceback": None,
            "analysis": None
        }
        
        try:
            # Initialize browser and agent
            browser = Browser(config=self.browser_config)
            agent = Agent(
                task=test_scenario,
                browser=browser,
                llm_provider=self.llm_provider,
                api_key=self.api_key
            )
            
            # Run the test
            await agent.run(url)
            
            result["success"] = True
            
        except Exception as e:
            # Capture error details
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            
            result["success"] = False
            result["error"] = error_msg
            result["traceback"] = error_traceback
            
            # Log to Sentry
            log_error_to_sentry(
                error=error_msg,
                context={
                    "url": url,
                    "scenario": test_scenario,
                    "traceback": error_traceback
                }
            )
            
            # Analyze failure with LLM
            try:
                analysis = analyze_failure(
                    error=error_msg,
                    scenario=test_scenario,
                    url=url,
                    traceback=error_traceback
                )
                result["analysis"] = analysis
            except Exception as analysis_error:
                result["analysis"] = f"Failed to analyze error: {str(analysis_error)}"
        
        return result
    
    def run_test_sync(self, test_scenario: str, url: str) -> Dict[str, Any]:
        """
        Synchronous wrapper for run_test.
        
        Args:
            test_scenario: Description of what to test
            url: URL to test
            
        Returns:
            Dictionary with test results
        """
        return asyncio.run(self.run_test(test_scenario, url))


# Example test scenarios
DEFAULT_TEST_SCENARIOS = [
    {
        "name": "Login Flow",
        "scenario": "Navigate to the login page, enter credentials, and verify successful login",
        "url": "https://example.com/login"
    },
    {
        "name": "Checkout Flow",
        "scenario": "Add items to cart, proceed to checkout, and complete purchase",
        "url": "https://example.com/shop"
    },
    {
        "name": "Navigation Test",
        "scenario": "Navigate through the main pages of the website and verify all links work",
        "url": "https://example.com"
    }
]

