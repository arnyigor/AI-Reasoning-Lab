@echo off
rem Set console to UTF-8 mode to correctly display Python script output
chcp 65001 > nul

rem =================================================
rem  AI Reasoning Lab Benchmark Launcher
rem =================================================

:: --- Configuration ---
set "RequiredPythonVersion=3.10"
set "VenvDir=venv"
set "MainScript=scripts/run_baselogic_benchmark.py"
set "PythonExecutable=%VenvDir%\Scripts\python.exe"

:: --- Script Logic ---

echo.
echo =================================================
echo           AI REASONING LAB BENCHMARK
echo =================================================
echo.

:: 1. Check for venv directory
if not exist "%VenvDir%\" (
    echo [INFO] Virtual environment not found. Creating a new one...
    
    :: Try to create venv using the py.exe launcher
    py -%RequiredPythonVersion% -m venv %VenvDir%
    
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create the virtual environment.
        echo         Please make sure Python %RequiredPythonVersion% is installed and accessible.
        goto:fail
    )
    echo [SUCCESS] Virtual environment created successfully.
) else (
    echo [INFO] Virtual environment found.
)

:: 2. Install/Update dependencies
echo.
echo [INFO] Installing/Updating dependencies from pyproject.toml...

:: Upgrade pip first
call %PythonExecutable% -m pip install --upgrade pip > nul

:: Install all project dependencies
call %PythonExecutable% -m pip install -e .[dev]

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    goto:fail
)
echo [SUCCESS] Dependencies are ready.

:: 3. Run the main benchmark script
echo.
echo =================================================
echo [INFO] Starting the main benchmark script...
echo =================================================
echo.

call %PythonExecutable% %MainScript% %*

echo.
echo =================================================
echo [INFO] Benchmark script has finished.
echo =================================================
echo.

goto:end

:fail
echo.
echo [FAIL] Script stopped due to an error.

:end
pause
exit /b 0