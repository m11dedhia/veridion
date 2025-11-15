# Upgrading Python to Latest Version

## Current Status
- **Current Python**: 3.8.5
- **Required for Daytona SDK**: 3.10+
- **Latest Python**: 3.12.x or 3.13.x

## Step-by-Step Upgrade Instructions

### 1. Download Latest Python

1. Visit: https://www.python.org/downloads/
2. Download the latest Python 3.12 or 3.13 for Windows
3. Choose the 64-bit installer

### 2. Install Python

**IMPORTANT**: During installation:
- ✅ Check "Add Python to PATH"
- ✅ Check "Install for all users" (optional)
- Click "Install Now"

### 3. Verify Installation

After installation, open a **NEW** PowerShell window and run:

```powershell
python --version
# Should show: Python 3.12.x or 3.13.x

python -m pip --version
# Should show pip version
```

### 4. Update PATH (if needed)

If `python --version` still shows 3.8, you may need to:

1. Check PATH order:
   ```powershell
   $env:PATH -split ';' | Select-String -Pattern "Python"
   ```

2. The new Python should be earlier in PATH than old versions

### 5. Create New Virtual Environment

```powershell
# Navigate to project
cd "D:\Megh Drive\Projects\daytona-hacks"

# Create new venv with latest Python
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Verify Python version in venv
python --version
```

### 6. Reinstall Dependencies

```powershell
# Upgrade pip first
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

### 7. Test Daytona SDK

```powershell
python -c "from daytona import Daytona, DaytonaConfig; print('✓ Daytona SDK works!')"
```

## Quick Install Command (Alternative)

You can also use winget (Windows Package Manager):

```powershell
winget install Python.Python.3.12
```

Or chocolatey:

```powershell
choco install python
```

## After Upgrade

1. **Restart your terminal/IDE** to pick up the new Python
2. **Recreate virtual environment** if using one
3. **Reinstall dependencies** in the new environment
4. **Set DAYTONA_API_KEY** environment variable
5. **Restart the Flask app**

## Troubleshooting

**If old Python still shows:**
- Close and reopen all terminals
- Check PATH: `$env:PATH`
- Use full path: `C:\Users\Megh\AppData\Local\Programs\Python\Python312\python.exe`

**If pip doesn't work:**
```powershell
python -m ensurepip --upgrade
python -m pip install --upgrade pip
```

