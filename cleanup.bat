@echo off
REM v20260309-1
REM ============================================================
REM  HomeFinder — Project Cleanup Script
REM  Run from the project root: D:\Projects\home_finder\
REM ============================================================

echo.
echo  HomeFinder Cleanup
echo  ==================
echo  Removing Python, editor, and OS artifacts...
echo.

REM --- Python bytecode cache ---
if exist "__pycache__" (
	echo   Removing: __pycache__
	rd /s /q "__pycache__"
)

echo [1/6] Removing __pycache__ directories...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        echo   Removing: %%d
        rd /s /q "%%d"
    )
)

REM --- Compiled Python files ---
echo [2/6] Removing .pyc / .pyo files...
del /s /q "*.pyc" >nul 2>&1
del /s /q "*.pyo" >nul 2>&1

REM --- pytest / coverage artifacts ---
echo [3/6] Removing test and coverage artifacts...
if exist ".pytest_cache"  rd /s /q ".pytest_cache"
if exist "htmlcov"         rd /s /q "htmlcov"
if exist ".coverage"       del /q ".coverage"
if exist "coverage.xml"    del /q "coverage.xml"

REM --- Python egg/build artifacts ---
echo [4/6] Removing build artifacts...
if exist "build"           rd /s /q "build"
if exist "dist"            rd /s /q "dist"
if exist "*.egg-info"      rd /s /q "*.egg-info"
for /d /r . %%d in (*.egg-info) do (
    if exist "%%d" rd /s /q "%%d"
)

REM --- VSCodium / VS Code editor artifacts ---
echo [5/6] Removing editor artifacts...
if exist ".vscode\ipch"    rd /s /q ".vscode\ipch"
del /s /q "*.orig" >nul 2>&1

REM --- Windows / OS artifacts ---
echo [6/6] Removing OS artifacts...
del /s /q "Thumbs.db"    >nul 2>&1
del /s /q "Desktop.ini"  >nul 2>&1
del /s /q "*.tmp"        >nul 2>&1
del /s /q "*.log"        >nul 2>&1

echo.
echo  Done! The following are intentionally preserved:
echo    .venv\          - virtual environment
echo    instance\       - SQLite database
echo    .env            - environment variables
echo    .vscode\        - editor settings (only cache removed)
echo.
pause
