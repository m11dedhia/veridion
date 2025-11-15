"""
Flask web dashboard for AI QA Engineer.
"""
import os
import json
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
    """API endpoint to run a test."""
    data = request.json
    
    url = data.get('url')
    scenario = data.get('scenario')
    llm_provider = data.get('llm_provider', os.getenv('LLM_PROVIDER', 'openai'))
    
    if not url or not scenario:
        return jsonify({'error': 'URL and scenario are required'}), 400
    
    # Get API key
    if llm_provider == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
    else:
        api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        return jsonify({'error': f'{llm_provider.upper()}_API_KEY not set'}), 500
    
    # Initialize agent
    agent = QAAgent(llm_provider=llm_provider, api_key=api_key)
    
    # Run test
    try:
        result = agent.run_test_sync(scenario, url)
        result['id'] = len(test_results)
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


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

