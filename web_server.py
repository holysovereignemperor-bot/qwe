import os
import asyncio
import threading
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from blackboard import Blackboard

app = FastAPI()
_current_blackboard = None

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    global _current_blackboard
    if not _current_blackboard: return "<h1>OmniAgent: Idle</h1>"

    data = _current_blackboard.to_dict()
    # Monologue feed
    monologue = "\n".join([f"> {c['content']}" for c in _current_blackboard.chat_history[-10:]])

    html = f"""
    <html>
        <head>
            <title>OmniAgent Elite Dashboard</title>
            <meta http-equiv="refresh" content="3">
            <style>
                body {{ font-family: 'SF Mono', monospace; background: #0b0c10; color: #00ffa3; padding: 20px; }}
                .card {{ background: #1f2833; padding: 20px; border-radius: 8px; border: 1px solid #00ffa3; margin-bottom: 20px; }}
                .terminal {{ background: #000; padding: 15px; border-radius: 4px; height: 300px; overflow-y: auto; color: #fff; border: 1px solid #333; }}
                h1 {{ color: #00e5ff; }}
            </style>
        </head>
        <body>
            <h1>OmniAgent OS: Elite Monolith</h1>
            <div class="card">
                <p>Goal: {data['goal']}</p>
                <p>Status: {data['status']}</p>
                <p>Cost: ${data['total_cost']:.4f}</p>
            </div>
            <h2>Internal Monologue</h2>
            <div class="terminal"><pre>{monologue}</pre></div>
            <form action="/kill" method="post"><button type="submit" style="background:#ff0055; color:#fff; border:none; padding:10px; cursor:pointer;">KILL SWITCH</button></form>
        </body>
    </html>
    """
    return html

@app.post("/kill")
async def kill_switch():
    global _current_blackboard
    if _current_blackboard: _current_blackboard.is_running = False
    return {"status": "Stopped"}

def run_server(blackboard: Blackboard, port=8080):
    global _current_blackboard
    _current_blackboard = blackboard
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    return server
