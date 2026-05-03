"""Anime AI Agent - FastAPI Backend."""

import asyncio
import logging
import mimetypes
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.agent.orchestrator import Orchestrator
from backend.config import ASSETS_DIR, FRONTEND_DIR, OUTPUT_DIR
from backend.websocket_manager import ConnectionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Anime AI Agent",
    description="AI-powered anime video creation agent",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket manager and orchestrator
ws_manager = ConnectionManager()
orchestrator = Orchestrator(ws_manager)

# Mount static dirs
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


class CreateAnimeRequest(BaseModel):
    text: str
    project_id: str | None = None


class ProjectResponse(BaseModel):
    project_id: str
    status: str
    message: str


@app.on_event("startup")
async def startup():
    status = await orchestrator.initialize()
    logger.info(f"Anime AI Agent started. Providers: {status}")


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(content="<h1>Anime AI Agent</h1><p>Frontend not found.</p>")


@app.post("/api/create", response_model=ProjectResponse)
async def create_anime(request: CreateAnimeRequest):
    """Start anime creation pipeline."""
    if not request.text.strip():
        return JSONResponse(status_code=400, content={"error": "Text input is required"})

    project_id = request.project_id or f"anime_{int(__import__('time').time())}"

    # Run in background
    asyncio.create_task(orchestrator.create_anime(request.text, project_id))

    return ProjectResponse(
        project_id=project_id,
        status="started",
        message=f"Anime creation started. Project ID: {project_id}",
    )


@app.get("/api/projects")
async def list_projects():
    """List all projects."""
    return {"projects": orchestrator.list_projects()}


@app.get("/api/project/{project_id}")
async def get_project(project_id: str):
    """Get project status and details."""
    state = orchestrator.get_project(project_id)
    if not state:
        return JSONResponse(status_code=404, content={"error": "Project not found"})
    return state.to_dict()


@app.get("/api/project/{project_id}/video")
async def get_video(project_id: str):
    """Download the generated video."""
    state = orchestrator.get_project(project_id)
    if not state or not state.output_video:
        return JSONResponse(status_code=404, content={"error": "Video not found"})

    video_path = Path(state.output_video)
    if not video_path.exists():
        return JSONResponse(status_code=404, content={"error": "Video file not found"})

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=video_path.name,
    )


@app.get("/api/project/{project_id}/assets/{asset_type}/{filename:path}")
async def get_asset(project_id: str, asset_type: str, filename: str):
    """Serve generated assets (images, frames)."""
    state = orchestrator.get_project(project_id)
    if not state:
        return JSONResponse(status_code=404, content={"error": "Project not found"})

    asset_path = state.project_dir / asset_type / filename
    if not asset_path.exists():
        return JSONResponse(status_code=404, content={"error": "Asset not found"})

    mime_type = mimetypes.guess_type(str(asset_path))[0] or "application/octet-stream"
    return FileResponse(path=str(asset_path), media_type=mime_type)


@app.get("/api/status")
async def agent_status():
    """Get agent and provider status."""
    return {
        "status": "running",
        "llm": "ollama" if orchestrator.llm.ollama_available else "fallback",
        "image": orchestrator.image_provider.active_model if orchestrator.image_provider.available else "placeholder",
        "projects_count": len(orchestrator.projects),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time progress updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Client can send pings or commands
            if data == "ping":
                await websocket.send_text('{"type": "pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
