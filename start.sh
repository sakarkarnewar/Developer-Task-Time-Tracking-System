#!/usr/bin/env bash
set -e

# Initialize and seed database if tracker.db doesn't exist
if [ ! -f "tracker.db" ]; then
    echo "[INFO] Database not found. Initializing with sample data..."
    python seed.py
fi

# Launch FastAPI backend in the background
echo "[INFO] Starting FastAPI backend on http://127.0.0.1:8000 ..."
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &

# Wait for FastAPI backend to be ready
echo "[INFO] Waiting for backend to start..."
for i in {1..30}; do
    if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" >/dev/null 2>&1; then
        echo "[INFO] Backend is ready!"
        break
    fi
    sleep 1
done

# Launch Streamlit dashboard on $PORT assigned by Render
PORT="${PORT:-8501}"
echo "[INFO] Starting Streamlit dashboard on port ${PORT}..."
exec streamlit run frontend/app.py --server.port "${PORT}" --server.address 0.0.0.0
