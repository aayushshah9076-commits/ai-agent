"""Configuration for the Anime AI Agent."""

import os
from pathlib import Path

# Directories
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
FRONTEND_DIR = BASE_DIR / "frontend"

OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
(ASSETS_DIR / "generated").mkdir(exist_ok=True)

# LLM Configuration (Ollama)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# Image Generation (HuggingFace Inference API)
HF_API_URL = "https://api-inference.huggingface.co/models"
HF_ANIME_MODEL = os.getenv("HF_ANIME_MODEL", "cagliostrolab/animagine-xl-3.1")
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")  # Optional - works without for some models

# Video Settings
DEFAULT_FPS = 24
DEFAULT_SCENE_DURATION = 8  # seconds per scene
TRANSITION_DURATION = 1.5  # seconds for transitions
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

# Animation Settings
KEN_BURNS_ZOOM_RANGE = (1.0, 1.15)  # min/max zoom for Ken Burns
PARALLAX_LAYERS = 3
PAN_SPEED = 30  # pixels per second

# Agent Settings
MAX_SCENES_PER_EPISODE = 30
MAX_CHARACTERS = 10
MAX_RETRIES = 3
