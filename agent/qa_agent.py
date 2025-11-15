"""
AI QA Agent using Browser Use Cloud API for autonomous browser testing.
"""
import json
import os
import time
import asyncio
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv
from textwrap import dedent

from sentry.init_sentry import log_error_to_sentry
from llm_analysis.analyze_failure import analyze_failure

# Daytona SDK (optional).
DAYTONA_AVAILABLE = True
try:
    from daytona import Daytona, DaytonaConfig
except ImportError:
    DAYTONA_AVAILABLE = False
    Daytona = None
    DaytonaConfig = None


# Load environment variables so BROWSER_USE_API_KEY is available when the module is imported
load_dotenv()


class QAAgent:
    """AI-powered QA agent that runs browser tests using Browser Use Cloud API."""

    def __init__(
        self,
        llm_provider: str = "browser-use-llm",
        api_key: Optional[str] = None,
        use_daytona: bool = False,
        daytona_api_key: Optional[str] = None,
        daytona_target: Optional[str] = None,
    ):
        """Initialize the QA Agent."""
        self.llm_provider = llm_provider
        self.api_key = api_key or os.getenv("BROWSER_USE_API_KEY")

        self.use_daytona = use_daytona
        self.daytona_api_key = daytona_api_key or os.getenv("DAYTONA_API_KEY")
        self.daytona_target = daytona_target or os.getenv("DAYTONA_TARGET")

        if not self.api_key:
            raise ValueError(
                "Browser-Use API key not found. Please set BROWSER_USE_API_KEY in your .env file or pass it directly.\n"
                "You can create a key at https://cloud.browser-use.com/api-keys"
            )

        if self.use_daytona:
            if not DAYTONA_AVAILABLE:
                raise RuntimeError(
                    "Daytona SDK is not installed. Please run 'pip install daytona>=0.22.0' to enable sandbox execution."
                )
            if not self.daytona_api_key:
                raise ValueError(
                    "DAYTONA_API_KEY not set. Provide it via argument or environment variable to use Daytona sandboxes."
                )

        self.base_url = "https://api.browser-use.com/api/v2"
        self.headers = {
            "X-Browser-Use-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

        # Fail fast if the API key is invalid to avoid running a task that will 401 later
        self._validate_api_key()

        # Reusable Daytona client (lazy-initialized)
        self._daytona_client: Daytona | None = None

    def _validate_api_key(self) -> None:
        """Ensure the API key can authenticate with Browser-Use Cloud."""
        try:
            response = requests.get(
                f"{self.base_url}/billing/account",
                headers=self.headers,
                timeout=10,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Unable to reach Browser-Use Cloud API: {exc}") from exc

        if response.status_code == 401:
            raise ValueError(
                "Browser-Use API key was rejected (HTTP 401). Please generate a new key at "
                "https://cloud.browser-use.com/api-keys and export it as BROWSER_USE_API_KEY."
            )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Browser-Use API key validation failed: {response.status_code} - {response.text}"
            )

    async def run_test(self, test_scenario: str, url: str) -> Dict[str, Any]:
        """Run a test scenario on a given URL via Browser Use Cloud API."""
        result: Dict[str, Any] = {
            "success": False,
            "error": None,
            "details": None,
            "session_url": None,
            "url": url,
            "scenario": test_scenario,
        }

        try:
            if self.use_daytona:
                return await self._run_test_in_daytona(test_scenario, url)

            payload = {
                "task": (
                    "You are a QA engineer testing a web application.\n"
                    f"Test Scenario: {test_scenario}\n\n"
                    "Instructions:\n"
                    f"1. Navigate to: {url}\n"
                    "2. Execute the test scenario\n"
                    "3. If a navigation seems to load a blank or empty page, wait a few seconds, then refresh once and follow any redirect or new tab to its final destination before deciding it failed.\n"
                    "4. Confirm the page finished loading by checking the title or presence of expected content.\n"
                    "5. Report any issues or errors\n"
                    "6. End with a summary of your findings\n\n"
                    "IMPORTANT: End your response with a line beginning with 'RESULT: ' followed by 'PASS' or 'FAIL' "
                    "and a brief reason."
                ),
                "llm": self.llm_provider,
                "startUrl": url,
                "metadata": {
                    "test_scenario": test_scenario,
                    "source": "ai-qa-engineer",
                },
            }

            response = requests.post(
                f"{self.base_url}/tasks",
                headers=self.headers,
                json=payload,
                timeout=30,
            )

            if response.status_code != 202:
                raise RuntimeError(f"Failed to create task: {response.status_code} - {response.text}")

            task_info = response.json()
            task_id = task_info["id"]
            session_id = task_info.get("sessionId")
            if session_id:
                result["session_url"] = f"https://cloud.browser-use.com/sessions/{session_id}"

            task_data = await self._wait_for_task_completion(task_id)

            if not task_data:
                result["error"] = "Task timed out waiting for completion"
                return result

            self._interpret_task_outcome(result, task_data, test_scenario, url)

        except Exception as exc:
            result["error"] = str(exc)
            log_error_to_sentry(
                error=exc,
                context={
                    "test_scenario": test_scenario,
                    "url": url,
                    "llm_provider": self.llm_provider,
                },
            )

        return result

    async def _wait_for_task_completion(self, task_id: str, timeout_seconds: int = 300) -> Optional[Dict[str, Any]]:
        """Poll the Browser Use Cloud API until the task completes or times out."""
        start = time.time()

        while time.time() - start < timeout_seconds:
            try:
                response = requests.get(
                    f"{self.base_url}/tasks/{task_id}",
                    headers=self.headers,
                    timeout=15,
                )
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    if status in {"finished", "stopped", "error"}:
                        return data
                else:
                    # Non-200 responses still warrant a backoff before retrying
                    await asyncio.sleep(3)
            except requests.RequestException:
                await asyncio.sleep(3)

            await asyncio.sleep(2)

        return None

    def run_test_sync(self, test_scenario: str, url: str) -> Dict[str, Any]:
        """Synchronous wrapper for run_test."""
        return asyncio.run(self.run_test(test_scenario, url))

    async def _run_test_in_daytona(self, test_scenario: str, url: str) -> Dict[str, Any]:
        """Run the Browser-Use Cloud workflow from within a Daytona sandbox."""
        result: Dict[str, Any] = {
            "success": False,
            "error": None,
            "details": None,
            "session_url": None,
            "url": url,
            "scenario": test_scenario,
            "sandbox_id": None,
            "daytona_logs": [],
        }

        def _log(message: str) -> None:
            formatted = f"[Daytona] {message}"
            print(formatted)
            result["daytona_logs"].append(message)

        if not self._daytona_client:
            config = DaytonaConfig(api_key=self.daytona_api_key)
            if self.daytona_target:
                config.target = self.daytona_target
            self._daytona_client = Daytona(config)
            _log("Initialized Daytona client")

        sandbox = None
        try:
            _log("Initializing sandbox-backed Browser-Use task...")
            sandbox = self._daytona_client.create()
            result["sandbox_id"] = sandbox.id
            target_display = self.daytona_target or "default"
            _log(f"Sandbox created (target={target_display}, id={sandbox.id})")

            # Upload helper script to sandbox
            _log("Uploading runner script to sandbox...")
            helper = self._build_daytona_runner_script(test_scenario, url)
            sandbox.fs.upload_file(helper.encode("utf-8"), "run_browser_use.py")
            _log("Runner script uploaded as run_browser_use.py")

            # Execute script inside sandbox
            _log("Executing Browser-Use workflow inside sandbox...")
            exec_resp = sandbox.process.code_run("python run_browser_use.py")
            if exec_resp.exit_code != 0:
                _log(
                    f"Sandbox execution failed (exit={exec_resp.exit_code}). Output: {exec_resp.result}"
                )
                result["error"] = f"Sandbox execution failed: {exec_resp.exit_code} {exec_resp.result}"
                return result

            _log(f"Sandbox execution completed (exit={exec_resp.exit_code}). Parsing output...")

            # Parse JSON response from helper
            try:
                returned = json.loads(exec_resp.result)
            except (TypeError, json.JSONDecodeError):
                _log("Failed to decode sandbox response as JSON")
                result["error"] = f"Unexpected sandbox response: {exec_resp.result}"
                return result

            if not isinstance(returned, dict):
                _log("Sandbox response was not a dictionary payload")
                result["error"] = "Daytona sandbox returned invalid data"
                return result

            if "sessionId" in returned and returned["sessionId"] and not result.get("session_url"):
                result["session_url"] = f"https://cloud.browser-use.com/sessions/{returned['sessionId']}"

            _log("Browser-Use task payload received from sandbox")
            self._interpret_task_outcome(result, returned, test_scenario, url)

        except Exception as exc:
            _log(f"Exception during sandbox run: {exc}")
            result["error"] = str(exc)
            log_error_to_sentry(
                error=exc,
                context={
                    "test_scenario": test_scenario,
                    "url": url,
                    "llm_provider": self.llm_provider,
                    "sandbox_id": result.get("sandbox_id"),
                },
            )
        finally:
            if sandbox is not None:
                try:
                    sandbox.delete()
                    _log(f"Sandbox {sandbox.id} deleted successfully")
                    result["sandbox_cleaned"] = True
                except Exception:
                    _log(f"Sandbox {sandbox.id} cleanup failed")
                    result["sandbox_cleaned"] = False

        return result

    def _build_daytona_runner_script(self, test_scenario: str, url: str) -> str:
        """Create the Python script executed inside the Daytona sandbox."""
        payload = {
            "task": (
                "You are a QA engineer testing a web application.\n"
                f"Test Scenario: {test_scenario}\n\n"
                "Instructions:\n"
                f"1. Navigate to: {url}\n"
                "2. Execute the test scenario\n"
                "3. If a navigation seems to load a blank or empty page, wait a few seconds, then refresh once and follow any redirect or new tab to its final destination before deciding it failed.\n"
                "4. Confirm the page finished loading by checking the title or presence of expected content.\n"
                "5. Report any issues or errors\n"
                "6. End with a summary of your findings\n\n"
                "IMPORTANT: End your response with a line beginning with 'RESULT: ' followed by 'PASS' or 'FAIL' and a brief reason."
            ),
            "llm": self.llm_provider,
            "startUrl": url,
            "metadata": {
                "test_scenario": test_scenario,
                "source": "ai-qa-engineer",
            },
        }

        script = dedent(
            f"""import asyncio
import json
import os
import time
import requests

BASE_URL = "https://api.browser-use.com/api/v2"

PAYLOAD = json.loads({json.dumps(json.dumps(payload))})
HEADERS = {{
    "X-Browser-Use-API-Key": {json.dumps(self.api_key)},
    "Content-Type": "application/json",
}}


async def main():
    response = requests.post(f"{{BASE_URL}}/tasks", headers=HEADERS, json=PAYLOAD, timeout=30)
    response.raise_for_status()
    task_info = response.json()
    task_id = task_info['id']
    session_id = task_info.get('sessionId')

    start = time.time()
    while time.time() - start < 300:
        poll = requests.get(f"{{BASE_URL}}/tasks/{{task_id}}", headers=HEADERS, timeout=15)
        if poll.status_code == 200:
            data = poll.json()
            status = data.get("status")
            if status in {{"finished", "stopped", "error"}}:
                if session_id and "sessionId" not in data:
                    data["sessionId"] = session_id
                print(json.dumps(data))
                return
        time.sleep(2)

    print(json.dumps({{"error": "Task timed out waiting for completion"}}))


if __name__ == "__main__":
    asyncio.run(main())
"""
        )

        return script

    def _interpret_task_outcome(
        self,
        result: Dict[str, Any],
        task_data: Dict[str, Any],
        test_scenario: str,
        url: str,
    ) -> None:
        """Update result dict based on Browser-Use task payload."""

        status = task_data.get("status")
        output = task_data.get("output") or task_data.get("result")
        result["details"] = output or "No output returned by Browser Use"
        result["status"] = status

        session_id = task_data.get("sessionId")
        if session_id:
            result["session_url"] = f"https://cloud.browser-use.com/sessions/{session_id}"

        if status == "finished" and output:
            if "RESULT: PASS" in output:
                result["success"] = True
                result["error"] = None
            elif "RESULT: FAIL" in output:
                result["success"] = False
                result["error"] = (
                    output.split("RESULT: FAIL", 1)[-1].strip(" -:\n") or "Agent reported failure"
                )
            else:
                result["success"] = False
                result["error"] = "No RESULT line found in agent output"
        else:
            result["success"] = False
            result["error"] = task_data.get("error") or (
                f"Task ended with status '{status}'" if status else "Task did not return a status"
            )

        if not result["success"]:
            try:
                result["analysis"] = analyze_failure(
                    error=result.get("error") or (output or ""),
                    scenario=test_scenario,
                    url=url,
                    provider=self.llm_provider,
                )
            except Exception as analysis_exc:
                result["analysis"] = f"Failed to analyze with LLM: {analysis_exc}"
        else:
            result["analysis"] = None


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

