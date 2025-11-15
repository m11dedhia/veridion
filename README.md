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

The project is configured for Daytona. Simply open it in a Daytona workspace and it will automatically set up the environment.

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

1. **Start Daytona workspace** → Environment ready
2. **Run AI browser agent** → Test executes autonomously
3. **Failure occurs** → Error captured
4. **Sentry logs error** → Error visible in Sentry dashboard
5. **LLM analyzes failure** → Human-readable summary generated
6. **View in dashboard** → Results displayed in web UI

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

