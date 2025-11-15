# Daytona API Key Setup

## Important: Daytona is a Cloud Service

Daytona is **not a local server** - it's a cloud-based development environment platform. You need to:

1. **Get a Daytona API Key** from https://www.daytona.io
2. **Set the API key** as an environment variable
3. **The SDK connects to Daytona's cloud API** (not localhost:3000)

## Setup Steps

### 1. Get Your Daytona API Key

1. Sign up or log in at https://www.daytona.io
2. Go to your account settings
3. Generate an API key
4. Copy the API key

### 2. Set Environment Variable

**Windows (PowerShell):**
```powershell
$env:DAYTONA_API_KEY="your-api-key-here"
```

**Windows (Command Prompt):**
```cmd
set DAYTONA_API_KEY=your-api-key-here
```

**Linux/Mac:**
```bash
export DAYTONA_API_KEY="your-api-key-here"
```

**Or create a `.env` file:**
```bash
DAYTONA_API_KEY=your-api-key-here
DAYTONA_TARGET=us  # Optional: us, eu, etc.
```

### 3. Verify Setup

```python
from daytona import Daytona, DaytonaConfig

# This should work without errors
daytona = Daytona(DaytonaConfig())
sandbox = daytona.create(language="python")
print(f"Sandbox created: {sandbox.id}")
sandbox.delete()
```

## How It Works

- **No local server needed** - Daytona runs in the cloud
- **SDK connects to** `https://api.daytona.io` (or your target region)
- **Each sandbox** is created in Daytona's cloud infrastructure
- **All code execution** happens in Daytona's secure cloud sandboxes

## Troubleshooting

**Error: "DAYTONA_API_KEY not set"**
- Set the environment variable as shown above
- Or add it to your `.env` file

**Error: "Authentication failed"**
- Verify your API key is correct
- Check that your account is active

**Error: "Connection timeout"**
- Check your internet connection
- Verify firewall isn't blocking outbound connections

## Reference

- [Daytona Getting Started](https://www.daytona.io/docs/en/getting-started/)
- [Daytona Python SDK](https://pypi.org/project/daytona/)

