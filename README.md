# AI QA Engineer

🤖 **Autonomous browser testing powered by Browser Use, Sentry, and LLMs**

AI QA Engineer is a browser- and CLI-based QA automation tool that uses AI agents to run autonomous browser tests, log failures to Sentry, and provide intelligent analysis using LLMs (Claude or GPT-4).

## 🎯 Features

- **AI-Powered Testing**: Uses Browser Use to simulate human-like browser interactions
- **Error Monitoring**: Automatic error logging to Sentry
- **LLM Analysis**: Intelligent failure analysis using Claude or GPT-4
- **Daytona Integration**: Runs entirely in Daytona environments for instant, reproducible sandboxes
- **Dual Interface**: CLI for automation and Flask web dashboard for demos
- **Optional Observability**: Galileo integration for LLM trace debugging

### Browser-Use Integration (Agent Mode)

In addition to scripted Playwright tests, the AI QA Engineer supports an “agent mode” powered by Browser-Use. When this mode is enabled (for example, via `--agent-mode --url https://example.com`), the tool spins up a real browser and lets an AI agent drive it end-to-end. You provide a high-level task such as “open the app, log in with test credentials, and verify the dashboard loads,” and Browser-Use translates that into concrete browser actions: navigating, clicking, filling forms, and checking for expected UI elements.

At the end of the run, the agent returns a structured result with a PASS/FAIL status and a concise natural-language summary of what it did and what went wrong if it failed. The CLI surfaces this as a smoke-test outcome, and any failures flow through the same pipeline as the regular tests: they’re logged to Sentry as errors, analyzed by Claude for deeper explanations, and the prompt/response pair is recorded in Galileo for observability. This makes Browser-Use a drop-in, AI-driven alternative to hand-written test scripts while still fitting seamlessly into the overall QA and monitoring flow.

## 🏗️ Architecture

- **Core QA Engine**: Browser Use Python SDK (`Agent`, `Browser`, `ChatBrowserUse`)
- **Cloud Dev Env**: Daytona workspace defined via `.devcontainer.json` + `docker-compose.yml`
- **Error Monitoring**: Sentry (`sentry_sdk`)
- **LLM Summarizer**: Claude or GPT-4 API
- **Optional Observability**: Galileo SDK for LLM traces
- **Interfaces**: CLI (automation) + Flask web UI (demo dashboard)

## 📋 Prerequisites

- Python 3.11+
- Docker and Docker Compose (for Daytona)
- API keys for:
  - OpenAI (for GPT-4) OR Anthropic (for Claude)
  - Sentry (optional, for error monitoring)

## 🚀 Quick Start

### Option 1: Run in Daytona Sandbox (Recommended)

**All workload runs in Daytona sandboxes - LLM calls, browser automation, and processing all happen inside the sandbox.**

1. **Open in Daytona**: Create a new workspace from this repository
2. **Set Environment Variables** in Daytona:
   - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
   - `SENTRY_DSN` (optional)
3. **Auto-start**: The sandbox automatically installs dependencies and starts the Flask app
4. **Access Dashboard**: Use Daytona's port forwarding (usually port 5000)

See [README_DAYTONA.md](README_DAYTONA.md) for detailed Daytona setup instructions.

### Option 2: Local Development

### 1. Clone and Setup

```bash
git clone <repository-url>
cd daytona-hacks
```

### 2. Environment Variables

Create a `.env` file:

```bash
# LLM Provider (openai or anthropic)
LLM_PROVIDER=openai

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# OR Anthropic Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Sentry Configuration (optional)
SENTRY_DSN=your_sentry_dsn_here
ENVIRONMENT=development

# Flask Configuration
SECRET_KEY=your_secret_key_here
PORT=5000
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run in Daytona

**Recommended**: The project is fully configured for Daytona. Open it in a Daytona workspace and all workload (including LLM calls) will run in the sandbox. 
### 5. Run Tests

#### Using CLI

```bash
python cli.py --url https://example.com --scenario "Login and navigate to dashboard"
```

#### Using Web Dashboard

```bash
python app.py
```

Then open `http://localhost:5000` in your browser.

## 📖 Usage Examples

### CLI Examples

```bash
# Basic test
python cli.py --url https://example.com --scenario "Test login flow"

# With specific LLM provider
python cli.py --url https://example.com --scenario "Test checkout" --llm-provider anthropic

# JSON output
python cli.py --url https://example.com --scenario "Test navigation" --output json

# With Sentry DSN
python cli.py --url https://example.com --scenario "Test search" --sentry-dsn your_dsn
```

### Programmatic Usage

```python
from agent.qa_agent import QAAgent

agent = QAAgent(llm_provider="openai", api_key="your_key")
result = agent.run_test_sync(
    test_scenario="Login and navigate to dashboard",
    url="https://example.com"
)

print(f"Test passed: {result['success']}")
if not result['success']:
    print(f"Error: {result['error']}")
    print(f"Analysis: {result['analysis']}")
```

## 🧪 Test Scenarios

The tool comes with default test scenarios:

1. **Login Flow**: Navigate to login, enter credentials, verify login
2. **Checkout Flow**: Add items to cart, proceed to checkout, complete purchase
3. **Navigation Test**: Navigate through main pages, verify links work

## 📁 Project Structure

```
ai-qa-engineer/
├── .devcontainer/
│   └── devcontainer.json      # Daytona devcontainer config
├── agent/
│   └── qa_agent.py            # Core QA agent with Browser Use
├── sentry/
│   └── init_sentry.py         # Sentry integration
├── llm_analysis/
│   └── analyze_failure.py     # LLM failure analysis
├── templates/
│   └── index.html             # Web dashboard UI
├── cli.py                     # Command-line interface
├── app.py                     # Flask web application
├── docker-compose.yml         # Docker services
├── Dockerfile                 # Docker image definition
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🔧 Configuration

### LLM Providers

The tool supports two LLM providers:

- **OpenAI**: Uses GPT-4 by default
- **Anthropic**: Uses Claude 3.5 Sonnet by default

Set `LLM_PROVIDER` environment variable or use `--llm-provider` CLI flag.

### Sentry Integration

Sentry is optional but recommended for production. Set `SENTRY_DSN` environment variable to enable error logging.

### Galileo Integration

Galileo can be integrated for LLM observability. Add the Galileo SDK to your code for trace logging.

## 🎯 Demo Flow

For the Daytona HackSprint demo:

1. **Start Daytona workspace** → Environment ready (all code runs in sandbox)
2. **Run AI browser agent** → Test executes autonomously from sandbox
3. **LLM calls made** → All API calls originate from Daytona sandbox IP
4. **Failure occurs** → Error captured in sandbox
5. **Sentry logs error** → Error visible in Sentry dashboard
6. **LLM analyzes failure** → Human-readable summary generated (from sandbox)
7. **View in dashboard** → Results displayed in web UI

**Verify sandbox execution**: Visit `/api/sandbox-info` endpoint to see sandbox details.

## 🐛 Troubleshooting

### Browser Use Issues

- Ensure Chrome/Chromium is installed
- Check that headless mode is working
- Verify network connectivity

### LLM API Issues

- Verify API keys are set correctly
- Check API rate limits
- Ensure model names are correct

### Sentry Issues

- Verify DSN is correct
- Check Sentry project settings
- Ensure network access to Sentry

## 📝 License

MIT License

## 🤝 Contributing

This is a hackathon project for Daytona HackSprint SF 2025. Contributions welcome!

## 🏆 Hackathon Goals

- 🥇 **Main prize**
- 🏅 **Best Use of Daytona**
- 🎖️ **Best Use of Sentry**
- 🧠 **Best Use of Browser Use**

---

Built with ❤️ for Daytona HackSprint SF 2025

