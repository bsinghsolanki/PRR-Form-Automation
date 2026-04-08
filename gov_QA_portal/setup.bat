@echo off
:: ═══════════════════════════════════════════════════
:: setup.bat — Windows setup for Form Automation
:: ═══════════════════════════════════════════════════

echo ═══════════════════════════════════════════════════
echo    FORM AUTOMATION — WINDOWS SETUP
echo ═══════════════════════════════════════════════════

:: ── Check Python ───────────────────────────────────
echo [1/6] Checking Python...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Python not found!
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH"
    pause
    exit /b 1
)
python --version
echo ✅ Python found

:: ── Create virtual environment ─────────────────────
echo [2/6] Creating virtual environment...
IF NOT EXIST "venv" (
    python -m venv venv
    echo ✅ Virtual environment created
) ELSE (
    echo ⚠️  Virtual environment already exists
)

:: ── Activate venv ──────────────────────────────────
call venv\Scripts\activate.bat
echo ✅ Virtual environment activated

:: ── Upgrade pip ────────────────────────────────────
echo [3/6] Upgrading pip...
python -m pip install --upgrade pip setuptools wheel

:: ── Install PyTorch CPU ────────────────────────────
echo [4/6] Installing PyTorch CPU...
echo This may take a few minutes...
pip install torch --index-url https://download.pytorch.org/whl/cpu

:: ── Install requirements ───────────────────────────
echo [5/6] Installing requirements...
pip install -r requirements.txt

:: ── Create folders ─────────────────────────────────
echo [6/6] Creating project folders...
IF NOT EXIST "screenshots\errors"   mkdir screenshots\errors
IF NOT EXIST "screenshots\success"  mkdir screenshots\success
IF NOT EXIST "reports"              mkdir reports
IF NOT EXIST "logs"                 mkdir logs
IF NOT EXIST "temp_audio"           mkdir temp_audio

:: ── Create .env ────────────────────────────────────
IF NOT EXIST ".env" (
    copy .env.example .env
    echo ✅ .env created
)

echo.
echo ═══════════════════════════════════════════════════
echo ✅ SETUP COMPLETE!
echo ═══════════════════════════════════════════════════
echo.
echo Next steps:
echo   1. Edit .env — add your GOOGLE_SHEET_ID
echo   2. Add credentials.json to project root
echo   3. Run: python main.py --dry-run
echo   4. Run: python main.py
echo.
pause
```

---

**How someone uses this on a new system:**
```
# Linux/Mac
git clone your_repo
cd gov_QA_portal
./setup.sh

# Windows
git clone your_repo
cd gov_QA_portal
setup.bat