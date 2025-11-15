# Starting Daytona for QA Tasks

## Important: Daytona is a Cloud Service

**Daytona is a cloud-based development platform** - you don't need to run a local server. The SDK connects to Daytona's cloud infrastructure.

## Quick Setup (Recommended)

### 1. Get Your Daytona API Key

1. **Sign up** at https://www.daytona.io (if you don't have an account)
2. **Log in** to your dashboard
3. **Go to Settings** → **API Keys**
4. **Generate a new API key**
5. **Copy the key**

### 2. Set Environment Variable

**PowerShell:**
```powershell
$env:DAYTONA_API_KEY="your-api-key-here"
```

**Permanent (User-level):**
```powershell
[System.Environment]::SetEnvironmentVariable("DAYTONA_API_KEY", "your-api-key-here", "User")
```

**Or add to `.env` file:**
```bash
DAYTONA_API_KEY=your-api-key-here
DAYTONA_TARGET=us  # Optional: us, eu, etc.
```

### 3. Activate Python 3.12 Environment

```powershell
.\venv312\Scripts\Activate.ps1
```

### 4. Test Daytona Connection

```powershell
python -c "from daytona import Daytona, DaytonaConfig; import os; d = Daytona(DaytonaConfig(api_key=os.getenv('DAYTONA_API_KEY'))); print('✓ Connected to Daytona!')"
```

### 5. Run Your Flask App

```powershell
python app.py
```

## How It Works

- **No local server needed** - Daytona runs in the cloud
- **SDK connects to** `https://api.daytona.io` (or your target region)
- **Each QA task** creates a new sandbox in Daytona's cloud
- **Sandboxes are ephemeral** - automatically deleted after tests

## Alternative: Self-Hosted Daytona (Advanced)

If you specifically need a local Daytona server:

1. **Install Daytona CLI** (Linux/Mac):
   ```bash
   curl -sf -L https://download.daytona.io/daytona/install.sh | sudo bash
   ```

2. **Start server**:
   ```bash
   daytona server -y
   ```

3. **Get API key from local server**:
   ```bash
   daytona server api-key generate
   ```

4. **Set environment variables**:
   ```bash
   export DAYTONA_API_URL=http://localhost:3000
   export DAYTONA_API_KEY=your-local-key
   ```

**Note**: Self-hosted Daytona requires Docker and is more complex. The cloud service is recommended for the hackathon.

## Current Status

✅ Python 3.12.10 installed  
✅ Daytona SDK installed  
✅ Virtual environment ready  
⏳ Need: DAYTONA_API_KEY

## Next Steps

1. Get your API key from https://www.daytona.io
2. Set `DAYTONA_API_KEY` environment variable
3. Run `python app.py` with the venv312 environment
4. Test a QA task - it will create sandboxes in Daytona cloud!

