"""
QA Agent that runs tests in Daytona sandboxes.
"""
import os
import json
import time
from typing import Dict, Optional, Any
# Try SDK first (requires Python 3.10+), fallback to CLI-based manager
try:
    from daytona_integration.sandbox_manager_sdk import DaytonaSandboxManager
    SDK_AVAILABLE = True
except (ImportError, SyntaxError) as e:
    # Fallback to CLI-based manager if SDK not available (Python < 3.10 or not installed)
    SDK_AVAILABLE = False
    from daytona_integration.sandbox_manager import DaytonaSandboxManager
from sentry.init_sentry import log_error_to_sentry
from llm_analysis.analyze_failure import analyze_failure


class QAAgentDaytona:
    """AI-powered QA agent that runs tests in ephemeral Daytona sandboxes."""
    
    def __init__(self, llm_provider: str = "openai", api_key: Optional[str] = None, browser_use_api_key: Optional[str] = None):
        """
        Initialize the QA Agent with Daytona sandbox support.
        
        Args:
            llm_provider: Either "openai" or "anthropic"
            api_key: API key for the LLM provider
            browser_use_api_key: API key for Browser Use Cloud service (optional, will try env var if not provided)
        """
        self.llm_provider = llm_provider
        self.api_key = api_key
        # Get BROWSER_USE_API_KEY from parameter or environment
        self.browser_use_api_key = browser_use_api_key or os.getenv('BROWSER_USE_API_KEY')
        
        # Initialize Daytona sandbox manager (uses SDK if available)
        try:
            self.sandbox_manager = DaytonaSandboxManager()
        except Exception as e:
            error_msg = str(e)
            if "DAYTONA_API_KEY" in error_msg:
                raise Exception(
                    "Daytona API key not set. "
                    "Please set DAYTONA_API_KEY environment variable. "
                    "Get your API key from https://www.daytona.io/docs"
                )
            raise
        
    def run_test_in_sandbox(self, test_scenario: str, url: str, repo_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a test scenario in a new Daytona sandbox.
        
        Args:
            test_scenario: Description of what to test
            url: URL to test
            repo_url: Optional repo URL for sandbox (uses default if not provided)
            
        Returns:
            Dictionary with test results
        """
        result = {
            "success": False,
            "url": url,
            "scenario": test_scenario,
            "error": None,
            "traceback": None,
            "analysis": None,
            "sandbox_id": None,
            "sandbox_cleaned": False
        }
        
        sandbox_id = None
        sandbox_obj = None
        
        try:
            # Step 1: Create a new Daytona sandbox
            print(f"\n{'='*60}")
            print(f"🏗️  Creating ephemeral Daytona sandbox for QA task...")
            print(f"{'='*60}")
            
            try:
                sandbox_info = self.sandbox_manager.create_sandbox(repo_url=repo_url)
                sandbox_id = sandbox_info['id']
                sandbox_obj = sandbox_info.get('sandbox_object')  # Store sandbox object for SDK (internal use only)
                result['sandbox_id'] = sandbox_id
                result['sandbox_name'] = sandbox_info.get('name', sandbox_id)
                # Store sandbox_obj in a separate variable for cleanup, NOT in result dict
                print(f"✓ Sandbox created: {sandbox_id}")
            except Exception as sandbox_error:
                error_msg = str(sandbox_error)
                import traceback
                result['error'] = f"Failed to create Daytona sandbox: {error_msg}"
                result['traceback'] = traceback.format_exc()
                result['error_details'] = {
                    'message': error_msg,
                    'suggestion': self._get_daytona_suggestion(error_msg)
                }
                # Don't return early - let cleanup happen in finally block
                raise  # Re-raise to trigger cleanup
            
            # Step 2: Install dependencies in sandbox
            print(f"\n📦 Installing dependencies in sandbox...")
            install_cmd = "pip install --no-cache-dir browser-use sentry-sdk openai anthropic python-dotenv requests pydantic"
            # Use sandbox object if available (SDK mode), otherwise use ID (CLI mode)
            sandbox_ref = sandbox_obj if sandbox_obj else sandbox_id
            install_result = self.sandbox_manager.run_command_in_sandbox(
                sandbox_ref,
                install_cmd,
                timeout=300
            )
            
            if not install_result['success']:
                result['error'] = f"Failed to install dependencies: {install_result['stderr']}"
                return result
            
            print(f"✓ Dependencies installed")
            
            # Step 3: Create test script in sandbox
            print(f"\n📝 Creating test script in sandbox...")
            # Escape special characters for shell
            escaped_scenario = test_scenario.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            escaped_url = url.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            escaped_api_key = self.api_key.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            escaped_browser_use_key = (self.browser_use_api_key or '').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            
            test_script = f'''import asyncio
import os
import sys
import json
import traceback

# Set environment variables
os.environ['OPENAI_API_KEY'] = '{escaped_api_key}' if '{self.llm_provider}' == 'openai' else ''
os.environ['ANTHROPIC_API_KEY'] = '{escaped_api_key}' if '{self.llm_provider}' == 'anthropic' else ''
os.environ['BROWSER_USE_API_KEY'] = '{escaped_browser_use_key}' if '{escaped_browser_use_key}' else ''

try:
    # Import browser_use - use correct API per https://docs.cloud.browser-use.com/get-started/llm-quickstart
    from browser_use import Agent
    
    async def run_test():
        # Create agent directly - no need for Browser or BrowserConfig
        # The Agent handles browser initialization internally
        agent = Agent(
            task="{escaped_scenario}",
            llm_provider="{self.llm_provider}",
            api_key="{escaped_api_key}",
            headless=True
        )
        
        # Run the test - agent.run() handles browser automation
        await agent.run("{escaped_url}")
        return {{"success": True, "error": None}}
        
    result = asyncio.run(run_test())
    print(json.dumps(result))
    
except Exception as e:
    error_result = {{
        "success": False,
        "error": str(e),
        "traceback": traceback.format_exc()
    }}
    print(json.dumps(error_result))
    sys.exit(1)
'''
            
            # Write test script to sandbox using SDK's file upload
            # Use sandbox object if available (SDK mode), otherwise use command (CLI mode)
            if sandbox_obj and hasattr(sandbox_obj, 'fs'):
                # SDK mode: upload file directly
                try:
                    sandbox_obj.fs.upload_file(test_script.encode(), "/tmp/qa_test.py")
                    write_result = {'success': True}
                except Exception as e:
                    write_result = {'success': False, 'stderr': str(e)}
            else:
                # CLI mode: use base64 encoding
                import base64
                script_b64 = base64.b64encode(test_script.encode()).decode()
                write_script_cmd = f'echo "{script_b64}" | base64 -d > /tmp/qa_test.py'
                write_result = self.sandbox_manager.run_command_in_sandbox(sandbox_ref, write_script_cmd)
            
            if not write_result['success']:
                result['error'] = f"Failed to create test script: {write_result.get('stderr', '')}"
                return result
            
            # Step 4: Run the test in sandbox
            print(f"\n🧪 Running QA test in sandbox...")
            print(f"   Scenario: {test_scenario}")
            print(f"   URL: {url}")
            
            test_result = self.sandbox_manager.run_command_in_sandbox(
                sandbox_ref,
                "python /tmp/qa_test.py",
                timeout=600  # 10 minute timeout for tests
            )
            
            # Step 5: Parse results
            if test_result['success']:
                try:
                    test_output = test_result['stdout']
                    # Extract JSON from output
                    json_start = test_output.find('{')
                    json_end = test_output.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        test_data = json.loads(test_output[json_start:json_end])
                        result['success'] = test_data.get('success', False)
                        result['error'] = test_data.get('error')
                        result['traceback'] = test_data.get('traceback')
                    else:
                        result['success'] = True
                        result['error'] = None
                except json.JSONDecodeError:
                    # If no JSON, assume success if exit code is 0
                    result['success'] = True
                    result['error'] = None
            else:
                result['success'] = False
                result['error'] = test_result.get('stderr', 'Test execution failed')
                result['traceback'] = test_result.get('stdout', '')
            
            # Step 6: Analyze failure if needed
            if not result['success'] and result['error']:
                print(f"\n🧠 Analyzing failure with LLM...")
                try:
                    analysis = analyze_failure(
                        error=result['error'],
                        scenario=test_scenario,
                        url=url,
                        traceback=result.get('traceback'),
                        provider=self.llm_provider
                    )
                    result['analysis'] = analysis
                except Exception as analysis_error:
                    result['analysis'] = f"Failed to analyze: {str(analysis_error)}"
            
            # Step 7: Log to Sentry if failure
            if not result['success']:
                log_error_to_sentry(
                    error=result['error'],
                    context={
                        'url': url,
                        'scenario': test_scenario,
                        'sandbox_id': sandbox_id,
                        'traceback': result.get('traceback')
                    }
                )
            
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            import traceback
            result['traceback'] = traceback.format_exc()
            
            log_error_to_sentry(
                error=str(e),
                context={
                    'url': url,
                    'scenario': test_scenario,
                    'sandbox_id': sandbox_id
                }
            )
        
        finally:
            # Step 8: Always cleanup sandbox
            if sandbox_id or sandbox_obj:
                print(f"\n🧹 Cleaning up sandbox: {sandbox_id}")
                # Use sandbox object if available (SDK mode), otherwise use ID (CLI mode)
                sandbox_ref = sandbox_obj if sandbox_obj else sandbox_id
                cleaned = self.sandbox_manager.delete_sandbox(sandbox_ref)
                result['sandbox_cleaned'] = cleaned
                if cleaned:
                    print(f"✓ Sandbox cleaned up successfully")
                else:
                    print(f"⚠️  Warning: Sandbox cleanup may have failed")
        
        # Clean up result: remove any non-serializable objects before returning
        # This ensures JSON serialization works properly
        def make_serializable(obj):
            """Recursively convert non-serializable objects to strings."""
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            elif isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            else:
                # Convert non-serializable objects to string representation
                return str(obj)
        
        result = make_serializable(result)
        return result
    
    def _get_daytona_suggestion(self, error_msg: str) -> str:
        """Get helpful suggestion based on error message."""
        error_lower = error_msg.lower()
        if "cli not found" in error_lower or "not recognized" in error_lower or "file not found" in error_lower:
            return (
                "Install Daytona CLI:\n"
                "1. Visit https://www.daytona.io/docs\n"
                "2. Install Daytona CLI for your platform\n"
                "3. Verify: daytona --version"
            )
        elif "connection refused" in error_lower or "not available" in error_lower or "failed to establish" in error_lower:
            return (
                "Daytona server not running:\n"
                "1. Start Daytona server, OR\n"
                "2. Install Daytona CLI and set DAYTONA_USE_CLI=true"
            )
        else:
            return "Check Daytona installation and configuration. See https://www.daytona.io/docs"

