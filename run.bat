@echo off
echo =======================================================
echo   Starting Developer Task Time-Tracking System
echo =======================================================
echo.

:: Start FastAPI Backend in background
echo [1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "DevTracker Backend (FastAPI)" cmd /k "python -m uvicorn backend.main:app --port 8000 --reload"

:: Wait 2 seconds for backend initialization
timeout /t 2 /nobreak >nul

:: Start Streamlit Frontend
echo [2/2] Starting Streamlit Frontend on http://localhost:8501 ...
start "DevTracker Frontend (Streamlit)" cmd /k "streamlit run frontend/app.py"

echo.
echo All services started!
echo - Streamlit Dashboard: http://localhost:8501
echo - API Documentation:   http://127.0.0.1:8000/docs
echo - Minimal HTML/JS UI:  http://127.0.0.1:8000/app
echo.
