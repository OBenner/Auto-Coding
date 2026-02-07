#!/usr/bin/env python
"""
Minimal WebSocket test - standalone FastAPI app
"""

from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket("/ws/test")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"message": "Connected!"})
    await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
