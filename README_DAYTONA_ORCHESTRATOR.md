# Daytona Sandbox Orchestrator Architecture

## 🏗️ Architecture Overview

The AI QA Engineer now uses a **sandbox orchestrator pattern**:

1. **Flask App (Orchestrator)**: Runs locally or on any server
2. **Ephemeral Sandboxes**: Each QA task gets a **new Daytona sandbox**
3. **Automatic Cleanup**: Sandboxes are deleted after tests complete

## 🔄 Workflow

```
User Request → Flask App → Create Daytona Sandbox → Run QA Test → Cleanup Sandbox → Return Results
```

### Detailed Flow:

1. **User triggers QA test** via web UI or CLI
2. **Flask app creates** a new Daytona sandbox (ephemeral workspace)
3. **Dependencies installed** in the sandbox (browser-use, LLM SDKs, etc.)
4. **QA test runs** in the isolated sandbox environment
5. **LLM calls** originate from the sandbox IP
6. **Results collected** and returned to the orchestrator
7. **Sandbox deleted** automatically (cleanup)

## 🚀 Setup

### Prerequisites

1. **Daytona CLI** installed and configured
   ```bash
   # Install Daytona CLI
   # See: https://www.daytona.io/docs
   
   # Verify installation
   daytona --version
   ```

2. **Environment Variables**:
   ```bash
   OPENAI_API_KEY=your_key  # or ANTHROPIC_API_KEY
   DAYTONA_USE_CLI=true     # Use CLI (default) or set to false for API
   DAYTONA_API_URL=http://localhost:3000  # If using API
   DAYTONA_TOKEN=your_token  # If using API
   ```

### Running the Orchestrator

```bash
# Install dependencies
pip install -r requirements.txt

# Start Flask app (orchestrator)
python app.py
```

The Flask app will:
- Run on `http://localhost:5000`
- Create new Daytona sandboxes for each QA task
- Automatically clean up sandboxes after tests

## 📝 Usage

### Via Web UI

1. Open `http://localhost:5000`
2. Enter URL and test scenario
3. Click "Run Test"
4. Watch as a new sandbox is created, test runs, and sandbox is cleaned up

### Via API

```bash
curl -X POST http://localhost:5000/api/run-test \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "scenario": "Test login flow",
    "llm_provider": "openai",
    "use_daytona": true
  }'
```

### Via CLI

```bash
python cli.py --url https://example.com --scenario "Test login"
```

## 🔧 Configuration

### Daytona CLI vs API

The orchestrator supports two modes:

1. **CLI Mode (Default)**: Uses `daytona` CLI commands
   ```bash
   export DAYTONA_USE_CLI=true
   ```

2. **API Mode**: Uses Daytona REST API
   ```bash
   export DAYTONA_USE_CLI=false
   export DAYTONA_API_URL=http://your-daytona-server:3000
   export DAYTONA_TOKEN=your_api_token
   ```

### Custom Repository

You can specify a custom repository for sandboxes:

```json
{
  "url": "https://example.com",
  "scenario": "Test login",
  "repo_url": "https://github.com/your-org/qa-template"
}
```

If not specified, uses the default Python template.

## 🧹 Cleanup

Sandboxes are **automatically deleted** after tests complete, even if:
- Test fails
- Error occurs
- Timeout happens

The cleanup happens in a `finally` block to ensure it always runs.

## 🔍 Monitoring

### Check Sandbox Status

Each test result includes:
- `sandbox_id`: ID of the sandbox used
- `sandbox_cleaned`: Whether cleanup was successful
- `use_daytona`: Whether Daytona was used

### View Logs

The orchestrator logs:
- Sandbox creation
- Dependency installation
- Test execution
- Cleanup status

## 🐛 Troubleshooting

### Daytona CLI Not Found

```bash
# Install Daytona CLI
# See: https://www.daytona.io/docs

# Verify in PATH
which daytona
```

### Sandbox Creation Fails

- Check Daytona CLI is authenticated: `daytona auth status`
- Verify network connectivity
- Check Daytona server is running (if using API mode)

### Cleanup Fails

- Sandboxes may remain if cleanup fails
- Check Daytona logs for details
- Manually cleanup: `daytona workspace delete <sandbox_id>`

### Test Timeout

- Default timeout: 10 minutes
- Adjust in `agent/qa_agent_daytona.py`:
  ```python
  timeout=600  # seconds
  ```

## 🎯 Benefits

1. **Isolation**: Each test runs in a fresh environment
2. **Security**: Tests can't affect each other
3. **Scalability**: Run multiple tests in parallel
4. **Clean State**: No leftover files or processes
5. **Resource Management**: Automatic cleanup prevents resource leaks

## 📊 Example Output

```
🏗️  Creating ephemeral Daytona sandbox for QA task...
✓ Sandbox created: qa-task-a1b2c3d4

📦 Installing dependencies in sandbox...
✓ Dependencies installed

🧪 Running QA test in sandbox...
   Scenario: Test login flow
   URL: https://example.com
✓ Test completed

🧠 Analyzing failure with LLM...
✓ Analysis complete

🧹 Cleaning up sandbox: qa-task-a1b2c3d4
✓ Sandbox cleaned up successfully
```

