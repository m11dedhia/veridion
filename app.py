"""
Flask web dashboard for AI QA Engineer.
"""
import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
from agent.qa_agent import QAAgent, DEFAULT_TEST_SCENARIOS
from agent.qa_agent_daytona import QAAgentDaytona
from sentry.init_sentry import init_sentry

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize Sentry
init_sentry()

# Store test results in memory (in production, use a database)
test_results = []


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html', 
                         test_results=test_results[-10:],  # Show last 10 results
                         default_scenarios=DEFAULT_TEST_SCENARIOS)


@app.route('/api/run-test', methods=['POST'])
def run_test():
    """API endpoint to run a test in a Daytona sandbox."""
    data = request.json
    
    url = data.get('url')
    scenario = data.get('scenario')
    llm_provider = data.get('llm_provider', os.getenv('LLM_PROVIDER', 'openai'))
    use_daytona = data.get('use_daytona', True)  # Default to using Daytona
    repo_url = data.get('repo_url')  # Optional custom repo URL
    
    if not url or not scenario:
        return jsonify({'error': 'URL and scenario are required'}), 400
    
    # Get API key
    if llm_provider == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
    else:
        api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        return jsonify({'error': f'{llm_provider.upper()}_API_KEY not set'}), 500
    
    # Run test in Daytona sandbox (REQUIRED - no fallback)
    try:
        if use_daytona:
            # Use Daytona sandbox for isolation - REQUIRED
            agent = QAAgentDaytona(llm_provider=llm_provider, api_key=api_key)
            result = agent.run_test_in_sandbox(scenario, url, repo_url=repo_url)
        else:
            # Local execution only if explicitly disabled
            return jsonify({
                'error': 'Daytona is required for QA tasks. Set use_daytona=true or install Daytona CLI/server.',
                'success': False
            }), 400
        
        result['id'] = len(test_results)
        result['use_daytona'] = use_daytona
        
        # Ensure result is JSON serializable (remove any Sandbox objects or other non-serializable items)
        # The agent already handles this, but double-check here for safety
        import json
        try:
            # Test if result is JSON serializable
            json.dumps(result)
            cleaned_result = result
        except (TypeError, ValueError):
            # If not, recursively clean it
            def clean_for_json(obj):
                """Recursively remove non-serializable objects."""
                if isinstance(obj, dict):
                    cleaned = {}
                    for k, v in obj.items():
                        try:
                            json.dumps(v)
                            cleaned[k] = clean_for_json(v)
                        except (TypeError, ValueError):
                            # Skip non-serializable values
                            cleaned[k] = str(v) if v is not None else None
                    return cleaned
                elif isinstance(obj, list):
                    return [clean_for_json(item) for item in obj]
                elif isinstance(obj, (str, int, float, bool, type(None))):
                    return obj
                else:
                    return str(obj)
            cleaned_result = clean_for_json(result)
        
        test_results.append(cleaned_result)
        
        return jsonify(cleaned_result)
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': str(e.__traceback__)}), 500


@app.route('/api/results')
def get_results():
    """Get all test results."""
    return jsonify(test_results)


@app.route('/api/results/<int:result_id>')
def get_result(result_id):
    """Get a specific test result."""
    if 0 <= result_id < len(test_results):
        return jsonify(test_results[result_id])
    return jsonify({'error': 'Result not found'}), 404


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


@app.route('/api/sandbox-info')
def sandbox_info():
    """Return information about the sandbox environment."""
    import socket
    import platform
    
    return jsonify({
        'hostname': socket.gethostname(),
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'python_executable': platform.python_implementation(),
        'workspace': os.getenv('WORKSPACE', '/workspace'),
        'is_daytona': os.path.exists('/workspace') or os.getenv('DAYTONA', 'false').lower() == 'true',
        'llm_provider_configured': 'openai' if os.getenv('OPENAI_API_KEY') else ('anthropic' if os.getenv('ANTHROPIC_API_KEY') else 'none'),
        'port': int(os.getenv('PORT', 5000))
    })


if __name__ == '__main__':
    import socket
    import platform
    
    port = int(os.getenv('PORT', 5000))
    
    # Log startup information
    print("=" * 60)
    print("🤖 AI QA Engineer - Daytona Sandbox Orchestrator")
    print("=" * 60)
    print(f"Hostname: {socket.gethostname()}")
    print(f"Platform: {platform.platform()}")
    print(f"Python: {platform.python_version()}")
    print(f"Port: {port}")
    print("")
    print("📋 Architecture:")
    print("   • Flask app runs locally (orchestrator)")
    print("   • Each QA task runs in a NEW ephemeral Daytona sandbox")
    print("   • Sandboxes are automatically cleaned up after tests")
    print("")
    
    # Check LLM configuration
    if os.getenv('OPENAI_API_KEY'):
        print("✓ OpenAI API key configured")
    elif os.getenv('ANTHROPIC_API_KEY'):
        print("✓ Anthropic API key configured")
    else:
        print("⚠️  Warning: No LLM API keys found!")
    
    # Check Daytona availability
    try:
        from daytona_integration.sandbox_manager_sdk import DaytonaSandboxManager
        manager = DaytonaSandboxManager()
        print("✓ Daytona SDK initialized")
    except Exception as e:
        error_msg = str(e)
        if "DAYTONA_API_KEY" in error_msg:
            print("⚠️  Warning: DAYTONA_API_KEY not set")
            print("   Get your API key from https://www.daytona.io/docs")
            print("   Set it: export DAYTONA_API_KEY=your_key")
        else:
            print(f"⚠️  Warning: Daytona integration may not be available: {e}")
            print("   See DAYTONA_API_KEY_SETUP.md for setup instructions")
    
    print(f"🌐 Starting Flask server on http://0.0.0.0:{port}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=True)

