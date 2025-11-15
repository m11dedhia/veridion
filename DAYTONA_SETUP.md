# Daytona Setup Guide

## Root Cause Analysis (RCA)

The Daytona sandbox creation is failing because:

1. **Daytona CLI is not installed** - The `daytona` command is not found in PATH
2. **System falls back to API mode** - When CLI check fails, it tries API mode
3. **Daytona API server is not running** - No server listening on `localhost:3000`
4. **Connection refused** - API endpoint doesn't exist

## Solution: Install Daytona

You have two options:

### Option 1: Install Daytona CLI (Recommended)

1. **Install Daytona CLI**:
   ```bash
   # Visit https://www.daytona.io/docs for installation instructions
   # For Windows, you may need to use WSL or install via package manager
   ```

2. **Verify installation**:
   ```bash
   daytona --version
   ```

3. **Set environment variable** (optional):
   ```bash
   export DAYTONA_USE_CLI=true
   ```

### Option 2: Run Daytona Server

1. **Start Daytona server** on `localhost:3000`
2. **Set environment variables**:
   ```bash
   export DAYTONA_USE_CLI=false
   export DAYTONA_API_URL=http://localhost:3000
   export DAYTONA_TOKEN=your_token_here  # If required
   ```

## Current Status

- ✅ Code is configured to use Daytona (no local fallback)
- ❌ Daytona CLI not installed
- ❌ Daytona API server not running

## Next Steps

1. Install Daytona CLI or start Daytona server
2. Restart the Flask app
3. Run a test - it will now use Daytona sandboxes

## Error Messages

The system will now provide clear error messages:
- If CLI not found: Instructions to install CLI
- If API not available: Instructions to start server or install CLI
- No automatic fallback to local execution (as requested)

