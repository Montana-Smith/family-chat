# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List

app = FastAPI()

# ──────────────────────────────────────────────────────────────
# 1. Serve static files (HTML, CSS, JS, images)
#    Requests like /static/chat.html will fetch files in ./static
# ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ──────────────────────────────────────────────────────────────
# 2. Root route (/) returns the chat UI
#    We simply read chat.html and return it as an HTMLResponse.
#    Browsers then load /static/chat.html and the JS inside
#    opens a WebSocket connection to /ws.
# ──────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def get_root() -> HTMLResponse:
    with open("static/chat.html", "r", encoding="utf-8") as file:
        return HTMLResponse(file.read())

# ──────────────────────────────────────────────────────────────
# 3. In-memory list of active WebSocket connections
# ──────────────────────────────────────────────────────────────
connections: List[WebSocket] = []

# ──────────────────────────────────────────────────────────────
# 4. WebSocket endpoint
#    • Accepts the connection
#    • Listens for incoming text messages
#    • Broadcasts each message to all connected clients
# ──────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connections.append(ws)
    try:
        while True:
            msg = await ws.receive_text()           # receive from one client
            for conn in connections:                # broadcast to everyone
                await conn.send_text(msg)
    except WebSocketDisconnect:
        connections.remove(ws)
