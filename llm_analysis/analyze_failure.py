"""
LLM-based failure analysis using Claude or GPT-4.
"""
import os
from typing import Optional, Dict, Any
from openai import OpenAI
from anthropic import Anthropic


def analyze_failure(
    error: str,
    scenario: str,
    url: str,
    traceback: Optional[str] = None,
    provider: Optional[str] = None
) -> str:
    """
    Analyze a test failure using LLM (Claude or GPT-4).
    
    Args:
        error: Error message
        scenario: Test scenario description
        url: URL being tested
        traceback: Optional traceback string
        provider: LLM provider ("openai" or "anthropic"). If None, uses env var.
        
    Returns:
        Human-readable analysis of the failure
    """
    provider = provider or os.getenv("LLM_PROVIDER", "openai")
    
    # Build prompt
    prompt = f"""You are a QA engineer analyzing a test failure. Provide a clear, concise analysis.

Test Scenario: {scenario}
URL: {url}
Error: {error}
"""
    if traceback:
        prompt += f"\nTraceback:\n{traceback}\n"
    
    prompt += """
Please provide:
1. A summary of what went wrong
2. Likely root cause
3. Suggested fixes or next steps
4. Severity assessment (Critical, High, Medium, Low)

Format your response in a clear, structured way."""

    try:
        # Log that LLM call is being made from sandbox
        import socket
        hostname = socket.gethostname()
        print(f"[Sandbox: {hostname}] Making LLM API call to {provider}...")
        
        if provider.lower() == "anthropic":
            result = _analyze_with_anthropic(prompt)
            print(f"[Sandbox: {hostname}] LLM analysis completed (Anthropic)")
            return result
        else:
            result = _analyze_with_openai(prompt)
            print(f"[Sandbox: {hostname}] LLM analysis completed (OpenAI)")
            return result
    except Exception as e:
        return f"Failed to analyze with LLM: {str(e)}\n\nOriginal error: {error}"


def _analyze_with_openai(prompt: str) -> str:
    """Analyze failure using OpenAI GPT-4."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4"),
        messages=[
            {"role": "system", "content": "You are an expert QA engineer analyzing test failures."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content


def _analyze_with_anthropic(prompt: str) -> str:
    """Analyze failure using Anthropic Claude."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    
    client = Anthropic(api_key=api_key)
    
    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        max_tokens=1000,
        system="You are an expert QA engineer analyzing test failures.",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.content[0].text

