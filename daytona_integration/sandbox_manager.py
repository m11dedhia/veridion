"""
Daytona Sandbox Manager - Creates and manages ephemeral sandboxes for QA tasks.
"""
import os
import subprocess
import time
import uuid
from typing import Dict, Optional, Any, Tuple
import json


class DaytonaSandboxManager:
    """Manages Daytona sandboxes for QA tasks."""
    
    def __init__(self, daytona_api_url: Optional[str] = None, daytona_token: Optional[str] = None):
        """
        Initialize the Daytona Sandbox Manager.
        
        Args:
            daytona_api_url: Daytona API URL (defaults to env var or local)
            daytona_token: Daytona API token (defaults to env var)
        """
        self.daytona_api_url = daytona_api_url or os.getenv('DAYTONA_API_URL', 'http://localhost:3000')
        self.daytona_token = daytona_token or os.getenv('DAYTONA_TOKEN')
        # Default to CLI mode (more reliable)
        self.use_cli = os.getenv('DAYTONA_USE_CLI', 'true').lower() == 'true'
        
        # Check if Daytona CLI is available
        if self.use_cli:
            try:
                result = subprocess.run(
                    'daytona --version',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    raise FileNotFoundError("Daytona CLI command failed")
                print(f"✓ Daytona CLI detected: {result.stdout.strip()}")
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                # CLI not available - check if we should use API or fail
                if os.getenv('DAYTONA_REQUIRE_CLI', 'false').lower() == 'true':
                    raise Exception(
                        "Daytona CLI is required but not found. "
                        "Please install Daytona CLI from https://www.daytona.io/docs "
                        "or set DAYTONA_USE_CLI=false to use API mode."
                    )
                print("⚠️  Warning: Daytona CLI not found. Install from https://www.daytona.io/docs")
                print("   Falling back to API mode (requires Daytona server)")
                self.use_cli = False
        
    def _run_daytona_cli(self, command: str, check: bool = True) -> Tuple[str, int]:
        """
        Run a Daytona CLI command.
        
        Args:
            command: Daytona CLI command to run
            check: Whether to raise exception on non-zero exit
            
        Returns:
            Tuple of (stdout, return_code)
        """
        try:
            result = subprocess.run(
                f"daytona {command}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            if check and result.returncode != 0:
                raise Exception(f"Daytona CLI error: {result.stderr}")
            return result.stdout.strip(), result.returncode
        except subprocess.TimeoutExpired:
            raise Exception("Daytona CLI command timed out")
        except FileNotFoundError:
            raise Exception("Daytona CLI not found. Please install Daytona CLI or set DAYTONA_USE_CLI=false to use API")
    
    def create_sandbox(self, repo_url: Optional[str] = None, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new Daytona sandbox for a QA task.
        
        Args:
            repo_url: Git repository URL (defaults to current project)
            project_name: Name for the project (auto-generated if not provided)
            
        Returns:
            Dictionary with sandbox information (id, name, status, etc.)
        """
        if not project_name:
            project_name = f"qa-task-{uuid.uuid4().hex[:8]}"
        
        if not repo_url:
            # Use current repository or a default template
            repo_url = os.getenv('DAYTONA_DEFAULT_REPO', 'https://github.com/daytonaio/templates/tree/main/python')
        
        print(f"🏗️  Creating Daytona sandbox: {project_name}")
        
        try:
            # Always try CLI first (more reliable)
            if self.use_cli:
                # Use Daytona CLI to create workspace
                command = f'workspace create --project "{project_name}" --repo "{repo_url}"'
                output, code = self._run_daytona_cli(command, check=False)
                
                if code != 0:
                    # Try alternative command format
                    command = f'create --name "{project_name}" --repo "{repo_url}"'
                    output, code = self._run_daytona_cli(command, check=False)
                
                if code == 0:
                    # Parse workspace ID from output
                    workspace_id = project_name  # Fallback
                    if output:
                        # Try to extract workspace ID from output
                        lines = output.split('\n')
                        for line in lines:
                            if 'workspace' in line.lower() or 'id' in line.lower():
                                parts = line.split()
                                if parts:
                                    workspace_id = parts[-1]
                                    break
                else:
                    # CLI failed, fall back to API if not already using CLI
                    if not self.use_cli:
                        raise Exception("Daytona CLI not available and API mode failed")
                    else:
                        raise Exception(f"Daytona CLI failed: {output}")
            
            # Use API mode only if explicitly requested and CLI is disabled
            if not self.use_cli:
                # Use REST API (if available)
                import requests
                try:
                    headers = {}
                    if self.daytona_token:
                        headers['Authorization'] = f'Bearer {self.daytona_token}'
                    
                    # Test connection first
                    test_response = requests.get(
                        f'{self.daytona_api_url}/health',
                        headers=headers,
                        timeout=5
                    )
                    
                    response = requests.post(
                        f'{self.daytona_api_url}/api/workspaces',
                        json={
                            'name': project_name,
                            'repository': repo_url
                        },
                        headers=headers,
                        timeout=60
                    )
                    response.raise_for_status()
                    workspace_data = response.json()
                    workspace_id = workspace_data.get('id', project_name)
                    output = json.dumps(workspace_data)
                except requests.exceptions.ConnectionError as e:
                    raise Exception(
                        f"Daytona API server not available at {self.daytona_api_url}. "
                        "Please ensure Daytona server is running, or install Daytona CLI and set DAYTONA_USE_CLI=true"
                    )
                except requests.exceptions.RequestException as e:
                    raise Exception(f"Daytona API request failed: {str(e)}")
            
            # Wait for workspace to be ready
            print(f"⏳ Waiting for sandbox to be ready...")
            time.sleep(5)  # Give it a moment to initialize
            
            sandbox_info = {
                'id': workspace_id,
                'name': project_name,
                'repo_url': repo_url,
                'status': 'created',
                'created_at': time.time()
            }
            
            print(f"✓ Sandbox created: {workspace_id}")
            return sandbox_info
            
        except FileNotFoundError:
            error_msg = "Daytona CLI not found. Please install Daytona CLI (https://www.daytona.io/docs) or set DAYTONA_USE_CLI=false to use API mode."
            print(f"✗ {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg or "Failed to establish" in error_msg:
                error_msg = "Daytona server not available. Please ensure Daytona is running, or install Daytona CLI and set DAYTONA_USE_CLI=true"
            print(f"✗ Failed to create sandbox: {error_msg}")
            raise Exception(error_msg)
    
    def run_command_in_sandbox(self, sandbox_id: str, command: str, timeout: int = 600) -> Dict[str, Any]:
        """
        Run a command in a Daytona sandbox.
        
        Args:
            sandbox_id: Sandbox/workspace ID
            command: Command to run
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with command output and status
        """
        print(f"🚀 Running command in sandbox {sandbox_id}: {command}")
        
        try:
            if self.use_cli:
                # Use Daytona CLI to execute command
                escaped_command = command.replace('"', '\\"')
                cli_command = f'workspace exec --workspace "{sandbox_id}" --command "{escaped_command}"'
                output, code = self._run_daytona_cli(cli_command, check=False)
                
                return {
                    'success': code == 0,
                    'exit_code': code,
                    'stdout': output,
                    'stderr': '' if code == 0 else output
                }
            else:
                # Use REST API
                import requests
                headers = {}
                if self.daytona_token:
                    headers['Authorization'] = f'Bearer {self.daytona_token}'
                
                response = requests.post(
                    f'{self.daytona_api_url}/api/workspaces/{sandbox_id}/exec',
                    json={'command': command},
                    headers=headers,
                    timeout=timeout
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    'success': result.get('exit_code', 0) == 0,
                    'exit_code': result.get('exit_code', 0),
                    'stdout': result.get('stdout', ''),
                    'stderr': result.get('stderr', '')
                }
                
        except Exception as e:
            return {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e)
            }
    
    def delete_sandbox(self, sandbox_id: str) -> bool:
        """
        Delete/cleanup a Daytona sandbox.
        
        Args:
            sandbox_id: Sandbox/workspace ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        print(f"🧹 Cleaning up sandbox: {sandbox_id}")
        
        try:
            if self.use_cli:
                # Use Daytona CLI to delete workspace
                command = f'workspace delete --workspace "{sandbox_id}" --yes'
                output, code = self._run_daytona_cli(command, check=False)
                
                if code == 0:
                    print(f"✓ Sandbox {sandbox_id} deleted successfully")
                    return True
                else:
                    # Try alternative command
                    command = f'delete "{sandbox_id}" --yes'
                    output, code = self._run_daytona_cli(command, check=False)
                    return code == 0
            else:
                # Use REST API
                import requests
                headers = {}
                if self.daytona_token:
                    headers['Authorization'] = f'Bearer {self.daytona_token}'
                
                response = requests.delete(
                    f'{self.daytona_api_url}/api/workspaces/{sandbox_id}',
                    headers=headers,
                    timeout=60
                )
                response.raise_for_status()
                print(f"✓ Sandbox {sandbox_id} deleted successfully")
                return True
                
        except Exception as e:
            print(f"⚠️  Warning: Failed to delete sandbox {sandbox_id}: {str(e)}")
            return False
    
    def get_sandbox_status(self, sandbox_id: str) -> Dict[str, Any]:
        """
        Get status of a sandbox.
        
        Args:
            sandbox_id: Sandbox/workspace ID
            
        Returns:
            Dictionary with sandbox status
        """
        try:
            if self.use_cli:
                command = f'workspace info --workspace "{sandbox_id}"'
                output, code = self._run_daytona_cli(command, check=False)
                return {
                    'id': sandbox_id,
                    'status': 'running' if code == 0 else 'unknown',
                    'info': output
                }
            else:
                import requests
                headers = {}
                if self.daytona_token:
                    headers['Authorization'] = f'Bearer {self.daytona_token}'
                
                response = requests.get(
                    f'{self.daytona_api_url}/api/workspaces/{sandbox_id}',
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {
                'id': sandbox_id,
                'status': 'error',
                'error': str(e)
            }

