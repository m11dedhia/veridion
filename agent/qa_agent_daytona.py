"""
QA Agent that runs tests in Daytona sandboxes.
"""
import os
import json
import time
from typing import Dict, Optional, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
        # Universal API key fallback mechanism
        # Checks in order: parameter -> BROWSER_USE_API_KEY -> OPENAI_API_KEY -> ANTHROPIC_API_KEY
        self.api_key = (
            api_key
            or os.getenv('BROWSER_USE_API_KEY')
            or os.getenv('OPENAI_API_KEY')
            or os.getenv('ANTHROPIC_API_KEY')
        )
        # Get BROWSER_USE_API_KEY from parameter or environment (.env)
        # Falls back to the universal API key if not specifically set
        self.browser_use_api_key = (
            browser_use_api_key
            or os.getenv('BROWSER_USE_API_KEY')
            or self.api_key  # Fallback to universal API key
        )
        
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
            
            # Get all environment variables from .env for sandbox
            # These will be passed to the sandbox test script
            sentry_dsn = os.getenv('SENTRY_DSN', '')
            llm_provider_env = os.getenv('LLM_PROVIDER', self.llm_provider)
            
            # Ensure we have the API key using universal fallback
            if not self.api_key:
                self.api_key = (
                    os.getenv('BROWSER_USE_API_KEY')
                    or os.getenv('OPENAI_API_KEY')
                    or os.getenv('ANTHROPIC_API_KEY')
                )
            
            # Ensure browser_use_api_key is set (fallback to universal API key)
            if not self.browser_use_api_key:
                self.browser_use_api_key = (
                    os.getenv('BROWSER_USE_API_KEY')
                    or self.api_key  # Fallback to universal API key
                )
            
            # Step 3: Create test script in sandbox
            print(f"\n📝 Creating test script in sandbox...")
            # Escape special characters for shell
            escaped_scenario = test_scenario.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            escaped_url = url.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            escaped_api_key = self.api_key.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            escaped_browser_use_key = (self.browser_use_api_key or '').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            escaped_sentry_dsn = sentry_dsn.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`') if sentry_dsn else ''
            escaped_llm_provider = llm_provider_env.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            
            test_script = f'''import asyncio
import os
import sys
import json
import traceback
import socket

# Set environment variables from .env (all LLM calls will use these)
os.environ['LLM_PROVIDER'] = '{escaped_llm_provider}'

# Universal API key setup - set all possible API key variables
# This ensures browser-use can find the API key regardless of which one is available
universal_api_key = '{escaped_api_key}'

# Set provider-specific API keys based on LLM provider
if '{escaped_llm_provider}' == 'openai':
    os.environ['OPENAI_API_KEY'] = universal_api_key
elif '{escaped_llm_provider}' == 'anthropic':
    os.environ['ANTHROPIC_API_KEY'] = universal_api_key

# Set BROWSER_USE_API_KEY (universal fallback)
if '{escaped_browser_use_key}':
    os.environ['BROWSER_USE_API_KEY'] = '{escaped_browser_use_key}'
else:
    # Fallback to universal API key if browser-use key not available
    os.environ['BROWSER_USE_API_KEY'] = universal_api_key

# Browser-use requires BROWSER_USE_LLM_API_KEY when using LLM providers
# Set it to the universal API key (works with any provider)
os.environ['BROWSER_USE_LLM_API_KEY'] = universal_api_key

# Also try with dashes (some systems may expect this format)
try:
    os.environ['BROWSER-USE-LLM_API_KEY'] = universal_api_key
except:
    pass  # Some systems don't allow dashes in env var names

# Initialize Sentry in sandbox for error logging
sentry_initialized = False
if '{escaped_sentry_dsn}':
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn='{escaped_sentry_dsn}',
            traces_sample_rate=1.0,
            environment="daytona-sandbox",
        )
        # Set sandbox context
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("sandbox_id", "{sandbox_id}")
            scope.set_tag("test_scenario", "{escaped_scenario[:50]}")
            scope.set_tag("test_url", "{escaped_url}")
            scope.set_context("sandbox", {{
                "sandbox_id": "{sandbox_id}",
                "hostname": socket.gethostname(),
                "python_version": sys.version,
            }})
        sentry_initialized = True
        print(f"[SANDBOX] ✓ Sentry initialized for error logging", file=sys.stderr, flush=True)
    except Exception as sentry_error:
        print(f"[SANDBOX] ⚠️  Failed to initialize Sentry: {{sentry_error}}", file=sys.stderr, flush=True)

try:
    # Import browser_use - use correct API per https://docs.cloud.browser-use.com/get-started/llm-quickstart
    from browser_use import Agent
    print(f"[SANDBOX] ✓ browser_use imported successfully", file=sys.stderr, flush=True)
    
    async def run_test():
        # Create agent directly - no need for Browser or BrowserConfig
        # The Agent handles browser initialization internally
        print(f"[SANDBOX] Creating browser-use Agent...", file=sys.stderr, flush=True)
        # Use LLM_PROVIDER from environment (from .env)
        llm_provider = os.getenv('LLM_PROVIDER', '{escaped_llm_provider}')
        
        # Universal API key fallback mechanism in sandbox
        # Checks in order: BROWSER_USE_API_KEY -> OPENAI_API_KEY -> ANTHROPIC_API_KEY
        api_key = (
            os.getenv('BROWSER_USE_API_KEY')
            or os.getenv('OPENAI_API_KEY')
            or os.getenv('ANTHROPIC_API_KEY')
            or '{escaped_api_key}'  # Fallback to passed key
        )
        
        print(f"[SANDBOX] Using LLM provider: {{llm_provider}}", file=sys.stderr, flush=True)
        print(f"[SANDBOX] API key source: {{'BROWSER_USE_API_KEY' if os.getenv('BROWSER_USE_API_KEY') else ('OPENAI_API_KEY' if os.getenv('OPENAI_API_KEY') else 'ANTHROPIC_API_KEY' if os.getenv('ANTHROPIC_API_KEY') else 'passed parameter')}}", file=sys.stderr, flush=True)
        agent = Agent(
            task="{escaped_scenario}",
            llm_provider=llm_provider,
            api_key=api_key,
            headless=True
        )
        
        print(f"[SANDBOX] Starting browser automation...", file=sys.stderr, flush=True)
        # Run the test - agent.run() handles browser automation
        await agent.run("{escaped_url}")
        print(f"[SANDBOX] ✓ Browser automation completed successfully", file=sys.stderr, flush=True)
        return {{"success": True, "error": None}}
        
    result = asyncio.run(run_test())
    print(json.dumps(result))
    
except Exception as e:
    error_msg = str(e)
    error_traceback = traceback.format_exc()
    
    # Log to Sentry from sandbox if initialized
    if sentry_initialized:
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_context("test", {{
                    "scenario": "{escaped_scenario}",
                    "url": "{escaped_url}",
                    "llm_provider": os.getenv('LLM_PROVIDER', '{escaped_llm_provider}'),
                }})
                scope.set_context("error", {{
                    "message": error_msg,
                    "traceback": error_traceback,
                }})
                sentry_sdk.capture_exception(e)
            print(f"[SANDBOX] ✓ Error logged to Sentry", file=sys.stderr, flush=True)
        except Exception as sentry_log_error:
            print(f"[SANDBOX] ⚠️  Failed to log to Sentry: {{sentry_log_error}}", file=sys.stderr, flush=True)
    
    # Analyze failure with LLM FROM WITHIN SANDBOX (using .env variables)
    analysis = None
    try:
        print(f"[SANDBOX] 🧠 Analyzing failure with LLM (from sandbox)...", file=sys.stderr, flush=True)
        from openai import OpenAI
        from anthropic import Anthropic
        
        llm_provider = os.getenv('LLM_PROVIDER', '{escaped_llm_provider}')
        
        # Build analysis prompt
        prompt = f"""You are a QA engineer analyzing a test failure. Provide a clear, concise analysis.

Test Scenario: {escaped_scenario}
URL: {escaped_url}
Error: {{error_msg}}
Traceback:
{{error_traceback}}

Please provide:
1. A summary of what went wrong
2. Likely root cause
3. Suggested fixes or next steps
4. Severity assessment (Critical, High, Medium, Low)

Format your response in a clear, structured way."""
        
        if llm_provider.lower() == "anthropic":
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                client = Anthropic(api_key=api_key)
                response = client.messages.create(
                    model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                    max_tokens=1000,
                    system="You are an expert QA engineer analyzing test failures.",
                    messages=[{{"role": "user", "content": prompt}}]
                )
                analysis = response.content[0].text
                print(f"[SANDBOX] ✓ LLM analysis completed (Anthropic)", file=sys.stderr, flush=True)
        else:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4"),
                    messages=[
                        {{"role": "system", "content": "You are an expert QA engineer analyzing test failures."}},
                        {{"role": "user", "content": prompt}}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                analysis = response.choices[0].message.content
                print(f"[SANDBOX] ✓ LLM analysis completed (OpenAI)", file=sys.stderr, flush=True)
    except Exception as analysis_error:
        print(f"[SANDBOX] ⚠️  LLM analysis failed: {{analysis_error}}", file=sys.stderr, flush=True)
        analysis = f"Failed to analyze: {{str(analysis_error)}}"
    
    error_result = {{
        "success": False,
        "error": error_msg,
        "traceback": error_traceback,
        "analysis": analysis
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
                        # Get analysis from sandbox if available (LLM analysis done in sandbox)
                        result['analysis'] = test_data.get('analysis')
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
                # Try to extract analysis from stdout if available (from sandbox LLM call)
                try:
                    test_output = test_result.get('stdout', '')
                    json_start = test_output.find('{')
                    json_end = test_output.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        test_data = json.loads(test_output[json_start:json_end])
                        result['analysis'] = test_data.get('analysis')
                except:
                    pass
            
            # Step 6: Log to Sentry from orchestrator (with sandbox context)
            # Note: Errors are also logged from within the sandbox, but we log here too
            # to ensure we capture orchestrator-level issues
            if not result['success']:
                print(f"\n📊 Logging failure to Sentry (orchestrator)...")
                log_error_to_sentry(
                    error=result['error'],
                    context={
                        'url': url,
                        'scenario': test_scenario,
                        'sandbox_id': sandbox_id,
                        'sandbox_name': result.get('sandbox_name'),
                        'traceback': result.get('traceback'),
                        'execution_location': 'daytona_sandbox',
                        'browser_use_executed': True
                    }
                )
            
            # Step 7: LLM analysis is now done within the sandbox
            # If analysis wasn't done in sandbox (e.g., for orchestrator-level errors), do it here
            if not result['success'] and result['error'] and not result.get('analysis'):
                print(f"\n🧠 Analyzing failure with LLM (orchestrator fallback)...")
                try:
                    # Fallback: analyze from orchestrator if not done in sandbox
                    analysis = analyze_failure(
                        error=result['error'],
                        scenario=test_scenario,
                        url=url,
                        traceback=result.get('traceback'),
                        provider=self.llm_provider
                    )
                    result['analysis'] = analysis
                    print(f"✓ LLM analysis completed (orchestrator)")
                except Exception as analysis_error:
                    result['analysis'] = f"Failed to analyze: {str(analysis_error)}"
                    print(f"⚠️  LLM analysis failed: {str(analysis_error)}")
            elif result.get('analysis'):
                print(f"✓ LLM analysis completed (from sandbox)")
            
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

