# main.py
from datetime import datetime
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from sqlmodel import Field, SQLModel, Session, create_engine, select

# ──────────────────────────────────────────────
# Database models & engine  (SQLite file = messages.db)
# ──────────────────────────────────────────────
class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

engine = create_engine("sqlite:///messages.db", echo=False)
SQLModel.metadata.create_all(engine)           # create table if not exists

# ──────────────────────────────────────────────
# FastAPI app & static file mount
# ──────────────────────────────────────────────
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Root returns chat.html
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/chat.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# ──────────────────────────────────────────────
# WebSocket logic
# ──────────────────────────────────────────────
connections: List[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connections.append(ws)

    # 1️⃣  On join: send last 50 messages (oldest → newest)
    with Session(engine) as session:
        stmt = select(Message).order_by(Message.id.desc()).limit(50)
        history = list(reversed(session.exec(stmt).all()))
        for m in history:
            await ws.send_json({"username": m.username, "text": m.text})

    try:
        # 2️⃣  Main receive / broadcast loop
        while True:
            data = await ws.receive_json()          # expects {"username": "...", "text": "..."}
            username = data["username"].strip()
            text     = data["text"].strip()
            if not text:
                continue

            # 2a. Save to DB
            with Session(engine) as session:
                session.add(Message(username=username, text=text))
                session.commit()

            # 2b. Broadcast to everyone
            payload = {"username": username, "text": text}
            for conn in connections:
                await conn.send_json(payload)

    except WebSocketDisconnect:
        connections.remove(ws)
