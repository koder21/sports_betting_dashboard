#!/bin/bash

# Navigate to project root
cd "$(dirname "$0")"

# Start backend
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000 --loop asyncio &
BACKEND_PID=$!

# Start frontend
cd frontend
npm run dev &
FRONTEND_PID=$!

echo "Backend running on http://localhost:8000"
echo "Frontend running on http://localhost:5173"
echo "Press CTRL+C to stop both."

wait $BACKEND_PID $FRONTEND_PID