@echo off
cd /d "%~dp0\05_Web_Application"
where python >nul 2>nul || (echo Python 3 is required. Install it from python.org and try again.& pause & exit /b 1)
python -c "import fastapi,uvicorn,pymupdf" >nul 2>nul || (echo Installing required local libraries...& python -m pip install --upgrade fastapi uvicorn pymupdf)
start "StudyVault API" /min python -m uvicorn server:app --host 127.0.0.1 --port 8765
 timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8765
