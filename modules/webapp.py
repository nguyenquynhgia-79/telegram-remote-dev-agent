"""
modules/webapp.py
=================
FastAPI server to host the Telegram Web App Dashboard.
Runs alongside the Telegram bot in the same event loop.
"""

import os
import psutil
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

WEB_DIR = Path(__file__).parent.parent / "web"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the Web App Dashboard HTML."""
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return "<h1>Web App UI not found</h1>"

@app.get("/api/status")
async def get_status():
    """Return real-time CPU and RAM stats."""
    return {
        "cpu": psutil.cpu_percent(interval=0.1),
        "ram": psutil.virtual_memory().percent
    }

WEBAPP_URL = ""

async def start_webapp():
    """Start the FastAPI server and localtunnel in the background."""
    global WEBAPP_URL
    logger.info("Khởi động Web App Server trên port 8000")
    
    # Khởi chạy Uvicorn trong thread hoặc task riêng
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    asyncio.create_task(server.serve())
    
    # Khởi chạy localtunnel
    try:
        import subprocess
        logger.info("Khởi tạo ngầm localtunnel để lấy Public URL...")
        process = await asyncio.create_subprocess_shell(
            "npx localtunnel --port 8000",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            text = line.decode().strip()
            if "your url is:" in text:
                WEBAPP_URL = text.split("your url is:")[1].strip()
                logger.info(f"🌐 Telegram Web App URL: {WEBAPP_URL}")
                break
    except Exception as e:
        logger.error(f"Lỗi khởi chạy localtunnel: {e}")
