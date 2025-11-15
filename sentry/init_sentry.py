"""
Sentry integration for error logging and monitoring.
"""
import os
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def init_sentry(dsn: Optional[str] = None):
    """
    Initialize Sentry SDK.
    
    Args:
        dsn: Sentry DSN (Data Source Name). If None, reads from SENTRY_DSN env var.
    """
    dsn = dsn or os.getenv("SENTRY_DSN")
    
    if not dsn:
        print("Warning: SENTRY_DSN not set. Sentry logging will be disabled.")
        return
    
    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            FlaskIntegration(),
        ],
        traces_sample_rate=1.0,
        environment=os.getenv("ENVIRONMENT", "development"),
    )


def log_error_to_sentry(
    error: str,
    context: Optional[Dict[str, Any]] = None,
    level: str = "error"
):
    """
    Log an error to Sentry with context.
    
    Args:
        error: Error message
        context: Additional context dictionary
        level: Log level (error, warning, info)
    """
    try:
        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_context(key, {"value": value})
            
            if level == "error":
                sentry_sdk.capture_message(error, level="error")
            elif level == "warning":
                sentry_sdk.capture_message(error, level="warning")
            else:
                sentry_sdk.capture_message(error, level="info")
    except Exception as e:
        # Fallback if Sentry is not initialized
        print(f"Failed to log to Sentry: {e}")
        print(f"Original error: {error}")
        if context:
            print(f"Context: {context}")

