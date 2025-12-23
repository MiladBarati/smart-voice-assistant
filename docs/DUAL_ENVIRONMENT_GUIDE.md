# Working with Both Windows and WSL Environments

## The Situation

You now have **two different Python environments**:

1. **WSL Environment** (Linux) - Has omnilingual-asr ✅
2. **Windows Environment** - No omnilingual-asr ❌

These are **completely separate** and cannot be mixed.

## Visual Overview

```
Your Project Directory
├── .venv/                    ← Currently: WSL/Linux environment
│   ├── bin/                  ← Linux (activate with: source .venv/bin/activate)
│   └── lib/                  ← Linux Python packages
│
├── pyproject.toml            ← Currently configured for: Linux
├── scripts/maintenance/setup_wsl.sh             ← For WSL setup
└── setup_windows.ps1        ← For Windows setup
```

## How to Use Each Environment

### 🐧 WSL Environment (For omnilingual-asr)

**When to use:**
- When you need omnilingual-asr
- When testing multilingual features
- For production deployment on Linux

**How to activate:**

```bash
# Step 1: Open WSL
wsl

# Step 2: Navigate to project
cd "/mnt/d/Amin Raay/pjsua installation"

# Step 3: Activate virtual environment
source .venv/bin/activate

# Step 4: Run your code
python examples/omnilingual_asr_example.py
```

### 🪟 Windows Environment (For development)

**When to use:**
- When doing general development in Windows
- When you don't need omnilingual-asr
- When using Windows-specific tools

**How to set up:**

```powershell
# In PowerShell (not WSL!)
cd "D:\Amin Raay\pjsua installation"

# Run Windows setup script
.\setup_windows.ps1
```

**How to activate:**

```powershell
# PowerShell
.venv\Scripts\Activate.ps1

# Or in CMD
.venv\Scripts\activate.bat
```

## Quick Reference Commands

### Check Which Environment You're In

**In PowerShell:**
```powershell
# Check if you're in Windows
echo $env:OS
# Output: Windows_NT  ← You're in Windows

# Check Python
python --version
where python
```

**In WSL:**
```bash
# Check if you're in WSL
uname -a
# Output: Linux ... Microsoft  ← You're in WSL

# Check Python
python --version
which python
```

### Switching Between Environments

**From Windows to WSL:**
```powershell
# In PowerShell
wsl
# Now you're in WSL
```

**From WSL to Windows:**
```bash
# In WSL
exit
# Now you're back in PowerShell
```

## The `.venv` Conflict Problem

Since both environments use the same `.venv` directory name, you need to choose:

### Option A: Manual Switching (Simple but manual)

**Current setup** - Switch by recreating `.venv`:

1. **To use WSL:**
   ```bash
   wsl
   cd "/mnt/d/Amin Raay/pjsua installation"
   ./scripts/maintenance/setup_wsl.sh  # Recreates Linux .venv
   ```

2. **To use Windows:**
   ```powershell
   cd "D:\Amin Raay\pjsua installation"
   .\setup_windows.ps1  # Recreates Windows .venv
   ```

### Option B: Rename Virtual Environments (Better)

Use different names for each environment:

**In WSL:**
```bash
uv venv .venv-wsl --python 3.12
source .venv-wsl/bin/activate
```

**In Windows:**
```powershell
uv venv .venv-windows --python 3.11
.venv-windows\Scripts\Activate.ps1
```

**Update `.gitignore`:**
```
.venv-wsl/
.venv-windows/
```

### Option C: Separate Directories (Best for serious work)

Keep two completely separate copies:

**Windows version:**
```
D:\Amin Raay\pjsua installation\
  ├── .venv\              ← Windows environment
  └── pyproject.toml      ← Configured for Windows
```

**WSL version:**
```
~/pjsua-installation/     ← In WSL native filesystem
  ├── .venv\              ← Linux environment
  └── pyproject.toml      ← Configured for Linux
```

**Setup:**
```bash
# In WSL
cp -r "/mnt/d/Amin Raay/pjsua installation" ~/pjsua-installation
cd ~/pjsua-installation
./scripts/maintenance/setup_wsl.sh
```

## Current Status: What You Have Now

Based on your setup:

✅ **WSL environment exists** at `.venv`
- Python 3.12 (Linux)
- Will have omnilingual-asr after running `./scripts/maintenance/setup_wsl.sh`
- Activate with: `source .venv/bin/activate` (in WSL only)

❌ **No Windows environment**
- Was removed when WSL environment was created
- Can be recreated with `.\setup_windows.ps1`
- Would activate with: `.venv\Scripts\Activate.ps1` (in PowerShell only)

## My Recommendation

**For your immediate goal (omnilingual-asr):**

1. **Continue in WSL** where you are now:
   ```bash
   # You should already be here:
   cd "/mnt/d/Amin Raay/pjsua installation"
   ./scripts/maintenance/setup_wsl.sh
   ```

2. **Later, if you need Windows development:**
   - Run `.\setup_windows.ps1` in PowerShell
   - Or use Option C (separate directories)

## Summary Table

| Action | Windows PowerShell | WSL Bash |
|--------|-------------------|----------|
| **Open environment** | Already there | `wsl` |
| **Navigate to project** | `cd "D:\Amin Raay\pjsua installation"` | `cd "/mnt/d/Amin Raay/pjsua installation"` |
| **Setup** | `.\setup_windows.ps1` | `./scripts/maintenance/setup_wsl.sh` |
| **Activate venv** | `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| **Check activation** | `($env:VIRTUAL_ENV -ne $null)` | `echo $VIRTUAL_ENV` |
| **Run Python** | `python` | `python` or `python3` |
| **Deactivate** | `deactivate` | `deactivate` |
| **Has omnilingual-asr** | ❌ No | ✅ Yes |

## Questions?

- **"Can I use the WSL .venv in Windows?"** - No, incompatible
- **"Can I use the Windows .venv in WSL?"** - No, incompatible
- **"Do I need both?"** - Only if you want to develop in both environments
- **"Which should I use?"** - WSL for omnilingual-asr, Windows for everything else

## Next Steps

**Right now**, you should:
1. Stay in WSL (where you currently are)
2. Run: `./scripts/maintenance/setup_wsl.sh`
3. Test omnilingual-asr

**Later**, if you want Windows development:
1. Open PowerShell
2. Run: `.\setup_windows.ps1`
3. Develop without omnilingual-asr


