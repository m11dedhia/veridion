# Running AI QA Engineer in Daytona Sandbox

This project is configured to run entirely within Daytona sandboxes. All LLM calls, browser automation, and processing happens inside the sandbox environment.

## 🚀 Quick Start in Daytona

1. **Open in Daytona**: Create a new workspace from this repository in Daytona
2. **Environment Variables**: Set your API keys in the Daytona environment or create a `.env` file:
   ```bash
   OPENAI_API_KEY=your_key_here
   # OR
   ANTHROPIC_API_KEY=your_key_here
   
   SENTRY_DSN=your_sentry_dsn_here  # Optional
   PORT=5000
   ```

3. **Auto-start**: The sandbox will automatically:
   - Install dependencies
   - Start the Flask web server
   - Make port 5000 available

4. **Access Dashboard**: Open the forwarded port (usually `https://your-workspace.daytona.io` or check Daytona's port forwarding)

## 📋 Manual Start (if needed)

If the app doesn't start automatically:

```bash
# Install dependencies
pip install -r requirements.txt

# Start the Flask app
python app.py
```

Or use the startup script:
```bash
chmod +x start.sh
./start.sh
```

## 🔧 Configuration

### Environment Variables

All LLM calls run from within the sandbox. Set these in Daytona's environment settings or `.env` file:

- `OPENAI_API_KEY` - For GPT-4 tests
- `ANTHROPIC_API_KEY` - For Claude tests  
- `LLM_PROVIDER` - Default provider (openai or anthropic)
- `SENTRY_DSN` - Error monitoring (optional)
- `PORT` - Flask port (default: 5000)

### Port Forwarding

The devcontainer is configured to forward port 5000. Daytona will automatically expose this port.

## 🧪 Running Tests

All test execution happens in the sandbox:

1. **Via Web UI**: Open the dashboard and run tests through the interface
2. **Via CLI**: 
   ```bash
   python cli.py --url https://example.com --scenario "Test login flow"
   ```

## 🔍 Verifying Sandbox Execution

To confirm everything runs in the sandbox:

```bash
# Check Python location
which python
# Should show: /usr/local/bin/python

# Check if running in container
cat /etc/os-release

# Check network connectivity (LLM API calls)
curl -I https://api.openai.com
```

## 📝 Notes

- All LLM API calls originate from the Daytona sandbox IP
- Browser automation (Browser Use) runs inside the container
- Test results are stored in memory (use a database for persistence)
- The sandbox is ephemeral - results are lost on restart

## 🐛 Troubleshooting

**App won't start:**
- Check if port 5000 is available
- Verify dependencies are installed: `pip list`
- Check logs: `python app.py` (run in foreground)

**LLM calls failing:**
- Verify API keys are set: `echo $OPENAI_API_KEY`
- Check network connectivity from sandbox
- Review error logs in the dashboard

**Port not accessible:**
- Check Daytona port forwarding settings
- Verify devcontainer.json has `forwardPorts: [5000]`
- Try accessing via Daytona's workspace URL

