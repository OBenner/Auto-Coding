# Starting Web Backend and Frontend Servers

Quick reference guide for running the Auto Code web interface.

## Prerequisites

- Python 3.10+ with virtual environment
- Node.js 18+ with npm
- Backend dependencies installed
- Frontend dependencies installed

## Backend Server

### Start Backend
```bash
cd apps/web-backend
.venv/Scripts/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Server will be available at:** http://localhost:8000

**Features enabled:**
- Auto-reload on code changes (`--reload`)
- API documentation at http://localhost:8000/docs (if DEBUG=true)
- Health check at http://localhost:8000/health
- WebSocket at ws://localhost:8000/ws/agent-events

### Backend Configuration

Edit `apps/web-backend/.env`:
```bash
DEBUG=true                    # Enable debug mode (auto-reload, API docs)
HOST=0.0.0.0                  # Listen on all interfaces
PORT=8000                     # Backend port
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:5173
SECRET_KEY=dev-secret-key-for-testing-only
```

### Backend Logs

To view logs in real-time:
```bash
tail -f backend.log
```

## Frontend Server

### Start Frontend
```bash
cd apps/web-frontend
npm run dev
```

**Server will be available at:** http://localhost:3000 (or http://localhost:3001 if 3000 is in use)

**Features enabled:**
- Hot module replacement (HMR)
- Fast refresh for React components
- Proxy to backend API (configured in vite.config.ts)
- WebSocket connection to backend

### Frontend Configuration

Edit `apps/web-frontend/.env`:
```bash
VITE_API_URL=http://localhost:8000   # Backend API URL
VITE_WS_URL=ws://localhost:8000      # WebSocket URL
VITE_DEBUG=true                       # Enable debug logging
```

### Frontend Logs

Logs are displayed in the terminal where you ran `npm run dev`.

## Testing the Integration

### 1. Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy","service":"auto-claude-web-api","version":"1.0.0","debug_mode":true}
```

### 2. Tasks API
```bash
curl http://localhost:8000/api/tasks
```

### 3. WebSocket Connection

Using Python:
```python
import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://localhost:8000/ws/agent-events') as ws:
        await ws.send(json.dumps({'action': 'subscribe', 'spec_id': '022'}))
        response = await ws.recv()
        print(response)

asyncio.run(test())
```

### 4. Frontend Access

Open browser to http://localhost:3001 (or check terminal output for actual port).

## Stopping the Servers

### Stop Backend
- Press `Ctrl+C` in the terminal running uvicorn
- Or if running in background: `kill $(cat backend.pid)`

### Stop Frontend
- Press `Ctrl+C` in the terminal running npm

## Troubleshooting

### Backend won't start

**Problem:** Port 8000 already in use
**Solution:**
```bash
# Find process using port 8000
netstat -ano | findstr :8000
# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

**Problem:** Module not found errors
**Solution:**
```bash
cd apps/web-backend
.venv/Scripts/python -m pip install -r requirements.txt
```

### Frontend won't start

**Problem:** Port 3000 already in use
**Solution:** Vite will automatically try port 3001. Update backend CORS if needed:
```bash
# In apps/web-backend/.env
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:5173
```

**Problem:** Module not found errors
**Solution:**
```bash
cd apps/web-frontend
npm install
```

### CORS errors in browser console

**Problem:** Frontend can't access backend API
**Solution:** Ensure backend `.env` includes frontend port in CORS_ORIGINS:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:5173
```

Then restart backend server.

### WebSocket connection fails

**Problem:** WebSocket won't connect
**Solution:**
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify WebSocket URL in frontend `.env`: `VITE_WS_URL=ws://localhost:8000`
3. Check browser console for connection errors
4. Ensure no firewall blocking WebSocket connections

## Development Workflow

### Typical development session:

1. **Start backend** (Terminal 1):
   ```bash
   cd apps/web-backend
   .venv/Scripts/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Start frontend** (Terminal 2):
   ```bash
   cd apps/web-frontend
   npm run dev
   ```

3. **Open browser** to http://localhost:3001

4. **Make changes** - both servers will auto-reload:
   - Backend: Changes to `.py` files trigger uvicorn reload
   - Frontend: Changes to `.tsx`/`.ts` files trigger Vite HMR

5. **Test API** in browser or with curl

6. **View logs** in respective terminals

## Production Deployment

For production deployment, see:
- `apps/web-backend/DEPLOYMENT.md` (to be created in subtask-3-3)
- `apps/web-frontend/DEPLOYMENT.md` (to be created in subtask-3-3)

## Quick Commands Reference

| Task | Command |
|------|---------|
| Start backend | `cd apps/web-backend && .venv/Scripts/python -m uvicorn main:app --reload` |
| Start frontend | `cd apps/web-frontend && npm run dev` |
| Test backend health | `curl http://localhost:8000/health` |
| Test tasks API | `curl http://localhost:8000/api/tasks` |
| View backend logs | `cd apps/web-backend && tail -f backend.log` |
| Install backend deps | `cd apps/web-backend && .venv/Scripts/python -m pip install -r requirements.txt` |
| Install frontend deps | `cd apps/web-frontend && npm install` |
| Build frontend | `cd apps/web-frontend && npm run build` |
| Type check frontend | `cd apps/web-frontend && npx tsc --noEmit` |

---

**Last Updated:** 2026-01-27
**Subtask:** 3-1 (Configure CORS and test API integration)
