"""Flask web dashboard for AI QA Engineer."""
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
from agent.qa_agent import QAAgent, DEFAULT_TEST_SCENARIOS
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
    """API endpoint to run a Browser-Use Cloud test."""
    data = request.json or {}

    url = data.get('url')
    scenario = data.get('scenario')
    llm_provider = data.get('llm_provider', os.getenv('BROWSER_USE_LLM', 'browser-use-llm'))

    use_daytona_raw = data.get('use_daytona')
    if use_daytona_raw is None:
        env_val = os.getenv('USE_DAYTONA', 'false').strip().lower()
        use_daytona = env_val in {'1', 'true', 'yes', 'on'}
    elif isinstance(use_daytona_raw, bool):
        use_daytona = use_daytona_raw
    else:
        use_daytona = str(use_daytona_raw).strip().lower() in {'1', 'true', 'yes', 'on'}

    if not url or not scenario:
        return jsonify({'error': 'URL and scenario are required'}), 400

    # Browser-Use Cloud API key (required for task execution)
    api_key = (
        data.get('browser_use_api_key')
        or os.getenv('BROWSER_USE_API_KEY')
        or data.get('openai_api_key')
        or os.getenv('OPENAI_API_KEY')
        or data.get('anthropic_api_key')
        or os.getenv('ANTHROPIC_API_KEY')
    )

    if not api_key:
        return jsonify({
            'error': (
                'No API key available. Please set BROWSER_USE_API_KEY (preferred) or '
                'OPENAI_API_KEY / ANTHROPIC_API_KEY in your environment.'
            )
        }), 500

    # Initialize agent
    agent = QAAgent(
        llm_provider=llm_provider,
        api_key=api_key,
        use_daytona=use_daytona,
        daytona_api_key=data.get('daytona_api_key') or os.getenv('DAYTONA_API_KEY'),
        daytona_target=data.get('daytona_target') or os.getenv('DAYTONA_TARGET'),
    )

    # Run test (Daytona optional)
    try:
        result = agent.run_test_sync(scenario, url)
        result['id'] = len(test_results)
        result['use_daytona'] = use_daytona
        test_results.append(result)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
    print("🤖 AI QA Engineer")
    print("=" * 60)
    print(f"Hostname: {socket.gethostname()}")
    print(f"Platform: {platform.platform()}")
    print(f"Python: {platform.python_version()}")
    print(f"Port: {port}")
    print("")

    # Check LLM configuration
    if os.getenv('BROWSER_USE_API_KEY'):
        print("✓ Browser-Use API key configured")
    else:
        print("⚠️  Warning: BROWSER_USE_API_KEY not set")

    print(f"🌐 Starting Flask server on http://0.0.0.0:{port}")
    print("=" * 60)

    app.run(host='0.0.0.0', port=port, debug=True)

