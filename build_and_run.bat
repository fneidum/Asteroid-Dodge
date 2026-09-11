@echo off
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [Error] Tick "Add to PATH" while installing Python to help fix this issue
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install pygame pyinstaller >nul
if errorlevel 1 (
    echo [Error] Failed to install dependencies
    pause
    exit /b 1
)

echo Building game...
python -m PyInstaller "Asteroid Dodge.spec" --noconfirm
if errorlevel 1 (
    echo [Error] Build failed
    pause
    exit /b 1
)

