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
    if not _current_blackboard:
        return "<h1>OmniAgent: No active session</h1>"

    data = _current_blackboard.to_dict()
    html = f"""
    <html>
        <head>
            <title>OmniAgent Dashboard</title>
            <meta http-equiv="refresh" content="5">
            <style>
                body {{ font-family: sans-serif; background: #0b0c10; color: #fff; padding: 20px; }}
                .card {{ background: #1f2833; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #00e5ff; }}
                h1 {{ color: #00e5ff; }}
                .status {{ color: #00ffa3; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>OmniAgent Live Dashboard</h1>
            <div class="card">
                <p>Goal: {data['goal']}</p>
                <p>Status: <span class="status">{data['status']}</span></p>
                <p>Cost: ${data['total_cost']:.4f}</p>
                <p>Step: {data['current_step'] + 1}</p>
            </div>
            <form action="/kill" method="post">
                <button type="submit" style="background: #ff0055; color: #fff; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">
                    EMERGENCY KILL SWITCH
                </button>
            </form>
        </body>
    </html>
    """
    return html

@app.post("/kill")
async def kill_switch():
    global _current_blackboard
    if _current_blackboard:
        _current_blackboard.is_running = False
        _current_blackboard.error = "Emergency kill switch activated from web dashboard"
    return {"status": "Agent stopped"}

def run_server(blackboard: Blackboard, port=8080):
    global _current_blackboard
    _current_blackboard = blackboard
    import uvicorn

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)

    # Start server in a background thread
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server
