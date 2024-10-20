@echo off
setlocal enabledelayedexpansion

set FOLDERS=scraper builder bot

for %%F in (%FOLDERS%) do (
    if exist "%%F" (
        if exist "%%F\requirements.txt" (
            echo Updating requirements for %%F
            call "%%F\.venv\Scripts\activate.bat"
            pip install --upgrade pip
            pip install -r "%%F\requirements.txt"
            deactivate
        ) else (
            echo No requirements.txt found in %%F
        )
    ) else (
        echo Folder %%F not found
    )
)

endlocal
pause