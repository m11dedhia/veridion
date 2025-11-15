"""
Daytona Sandbox Manager using the official Daytona Python SDK.
"""
import os
from typing import Dict, Optional, Any
from daytona import Daytona, DaytonaConfig


class DaytonaSandboxManager:
    """Manages Daytona sandboxes for QA tasks using the official SDK."""
    
    def __init__(self, api_key: Optional[str] = None, target: Optional[str] = None):
        """
        Initialize the Daytona Sandbox Manager using the official SDK.
        
        Args:
            api_key: Daytona API key (defaults to DAYTONA_API_KEY env var)
            target: Daytona target region (defaults to DAYTONA_TARGET env var or 'us')
        """
        self.api_key = api_key or os.getenv('DAYTONA_API_KEY')
        self.target = target or os.getenv('DAYTONA_TARGET', 'us')
        
        if not self.api_key:
            raise Exception(
                "DAYTONA_API_KEY not set. "
                "Get your API key from https://www.daytona.io/docs "
                "or set DAYTONA_API_KEY environment variable."
            )
        
        # Initialize Daytona client
        config = DaytonaConfig(
            api_key=self.api_key,
            target=self.target
        )
        self.daytona = Daytona(config)
        print(f"✓ Daytona SDK initialized (target: {self.target})")
        
    def create_sandbox(self, repo_url: Optional[str] = None, project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new Daytona sandbox for a QA task.
        
        Args:
            repo_url: Git repository URL (optional - uses default Python template if not provided)
            project_name: Name for the project (auto-generated if not provided)
            
        Returns:
            Dictionary with sandbox information (id, name, status, etc.)
        """
        import uuid
        
        if not project_name:
            project_name = f"qa-task-{uuid.uuid4().hex[:8]}"
        
        print(f"🏗️  Creating Daytona sandbox: {project_name}")
        
        try:
            # Create sandbox using SDK
            # The SDK create() method creates a sandbox with default Python template
            # Repository can be specified if needed, but for QA tasks we use default
            sandbox = self.daytona.create(language="python")
            
            # Get sandbox ID - the SDK returns a sandbox object
            sandbox_id = getattr(sandbox, 'id', None) or str(id(sandbox)) or project_name
            
            sandbox_info = {
                'id': sandbox_id,
                'name': project_name,
                'repo_url': repo_url or 'default-python-template',
                'status': 'created',
                'sandbox_object': sandbox  # Store the sandbox object for later use
            }
            
            print(f"✓ Sandbox created: {sandbox_info['id']}")
            return sandbox_info
            
        except Exception as e:
            error_msg = str(e)
            print(f"✗ Failed to create sandbox: {error_msg}")
            raise Exception(f"Failed to create Daytona sandbox: {error_msg}")
    
    def run_command_in_sandbox(self, sandbox_id: str, command: str, timeout: int = 600) -> Dict[str, Any]:
        """
        Run a command in a Daytona sandbox.
        
        Args:
            sandbox_id: Sandbox ID (or sandbox object)
            command: Command to run
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with command output and status
        """
        print(f"🚀 Running command in sandbox: {command}")
        
        try:
            # If sandbox_id is actually a sandbox object, use it directly
            if hasattr(sandbox_id, 'process'):
                sandbox = sandbox_id
            else:
                # Otherwise, we'd need to retrieve the sandbox by ID
                # For now, assume sandbox_id is the object stored in create_sandbox
                raise Exception("Sandbox object required - use the sandbox from create_sandbox")
            
            # Run command using SDK
            response = sandbox.process.code_run(command)
            
            return {
                'success': response.exit_code == 0,
                'exit_code': response.exit_code,
                'stdout': response.result,
                'stderr': '' if response.exit_code == 0 else response.result
            }
                
        except Exception as e:
            return {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e)
            }
    
    def delete_sandbox(self, sandbox_id: Any) -> bool:
        """
        Delete/cleanup a Daytona sandbox.
        
        Args:
            sandbox_id: Sandbox object or ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        print(f"🧹 Cleaning up sandbox")
        
        try:
            # If sandbox_id is a sandbox object, use it directly
            if hasattr(sandbox_id, 'delete'):
                sandbox_id.delete()
                print(f"✓ Sandbox deleted successfully")
                return True
            else:
                # Otherwise, we'd need to retrieve and delete by ID
                print(f"⚠️  Warning: Cannot delete sandbox - object required")
                return False
                
        except Exception as e:
            print(f"⚠️  Warning: Failed to delete sandbox: {str(e)}")
            return False
    
    def get_sandbox_status(self, sandbox_id: Any) -> Dict[str, Any]:
        """
        Get status of a sandbox.
        
        Args:
            sandbox_id: Sandbox object or ID
            
        Returns:
            Dictionary with sandbox status
        """
        try:
            if hasattr(sandbox_id, 'id'):
                return {
                    'id': sandbox_id.id,
                    'status': 'running',
                    'info': 'Sandbox is active'
                }
            else:
                return {
                    'id': str(sandbox_id),
                    'status': 'unknown',
                    'error': 'Sandbox object required'
                }
        except Exception as e:
            return {
                'id': str(sandbox_id),
                'status': 'error',
                'error': str(e)
            }

