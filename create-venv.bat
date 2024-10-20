@echo off
setlocal enabledelayedexpansion

set PYTHON_BIN=python

REM Check if Python is available
where %PYTHON_BIN% >nul 2>&1
if %errorlevel% neq 0 (
    echo %PYTHON_BIN% could not be found
    exit /b 1
)

set FOLDERS=scraper builder bot

for %%F in (%FOLDERS%) do (
    if exist "%%F" (
        echo Creating virtual environment for %%F
        if exist "%%F\.venv" (
            echo Removing existing virtual environment in %%F
            rmdir /s /q "%%F\.venv"
        )
        %PYTHON_BIN% -m venv "%%F\.venv"
    ) else (
        echo Folder %%F not found
    )
)

REM Run update-venv.bat
if exist "update-venv.bat" (
    echo Running update-venv.bat
    call update-venv.bat
) else (
    echo update-venv.bat not found
)

endlocal