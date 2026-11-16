APP_TITLE = 'PulseChat'
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
import sqlite3, os
from contextlib import contextmanager
from pathlib import Path

DB = Path(os.environ.get("APP_DB", str(Path(__file__).parent / "app.db")))
app = FastAPI(title=APP_TITLE, version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_methods=["*"], allow_headers=["*"])

@contextmanager
def db():
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def rows(cursor):
    return [dict(r) for r in cursor.fetchall()]

def setup(sql):
    with db() as con:
        con.executescript(sql)

@app.get("/api/health")
def health():
    return {"ok": True, "service": APP_TITLE}


from fastapi import WebSocket, WebSocketDisconnect
setup("""CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,room TEXT NOT NULL,author TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);""")
class Message(BaseModel):
    room:str="general"
    author:str
    body:str
clients:dict[str,list[WebSocket]]={}
@app.get('/api/items')
def items(room:str='general'):
    with db() as c:return rows(c.execute('SELECT * FROM messages WHERE room=? ORDER BY id DESC LIMIT 100',(room,)))[::-1]
@app.post('/api/items',status_code=201)
async def create_item(d:Message):
    if not d.body.strip() or not d.author.strip():raise HTTPException(422,'Message and author required')
    with db() as c:
        cur=c.execute('INSERT INTO messages(room,author,body) VALUES(?,?,?)',(d.room,d.author,d.body))
        message=dict(c.execute('SELECT * FROM messages WHERE id=?',(cur.lastrowid,)).fetchone())
    for ws in list(clients.get(d.room,[])):
        try:await ws.send_json(message)
        except Exception:clients[d.room].remove(ws)
    return message
@app.websocket('/ws/{room}')
async def socket(ws:WebSocket,room:str):
    await ws.accept();clients.setdefault(room,[]).append(ws)
    try:
        while True:await ws.receive_text()
    except WebSocketDisconnect:pass
    finally:
        if ws in clients.get(room,[]):clients[room].remove(ws)
@app.get('/api/summary')
def summary():
    with db() as c:return rows(c.execute('SELECT room AS label,COUNT(*) AS value FROM messages GROUP BY room'))


# v0.3: room directory and scoped chat search
@app.get('/api/rooms')
def rooms():
    with db() as con:
        return rows(con.execute("""SELECT room,COUNT(*) AS messages,MAX(created_at) AS last_message
            FROM messages GROUP BY room ORDER BY messages DESC,room ASC"""))

@app.get('/api/messages/search')
def search_messages(room: str = 'general', q: str = '', limit: int = 30):
    if limit < 1 or limit > 100:
        raise HTTPException(422,'Limit must be between 1 and 100')
    if not q.strip():
        return []
    pattern = '%' + q.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
    with db() as con:
        return rows(con.execute("""SELECT * FROM messages WHERE room=? AND body LIKE ? ESCAPE '!'
            ORDER BY id DESC LIMIT ?""",(room,pattern,limit)))

