# Anime AI Agent

AI-powered anime video creation agent that analyzes your story, designs characters, generates scenes, animates them, and produces complete anime episodes.

## Features

- **Text Analysis** - AI analyzes your story concept, extracts characters, themes, settings, and mood
- **Storyboard Generation** - Creates detailed scene-by-scene storyboard with camera directions
- **Character Design** - Generates anime-style character sheets with multiple poses
- **Scene Generation** - Creates background art and scene compositions
- **Animation Pipeline** - Applies Ken Burns, parallax, zoom, and pan effects
- **Video Assembly** - Combines scenes with transitions, dialogue overlays, and titles using FFmpeg
- **Real-time Dashboard** - Beautiful web UI with live progress tracking via WebSocket

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│  Web UI     │────>│  FastAPI      │────>│  Orchestrator  │
│  Dashboard  │<────│  Backend      │<────│  Agent         │
└─────────────┘     └──────────────┘     └────────────────┘
     WebSocket            REST API              │
                                                ├── Text Analyzer (Ollama/fallback)
                                                ├── Storyboard Generator
                                                ├── Character Designer (HuggingFace)
                                                ├── Scene Generator (HuggingFace)
                                                ├── Animator (PIL/NumPy)
                                                └── Video Assembler (FFmpeg)
```

## AI Providers

| Component | Primary | Fallback |
|-----------|---------|----------|
| LLM (text analysis, storyboard) | Ollama (Mistral/Llama) | Built-in template engine |
| Image Generation | HuggingFace Inference API (Animagine XL) | Styled placeholder images |
| Animation | PIL + NumPy frame generation | Always available |
| Video | FFmpeg | Always available |

## Quick Start

### Prerequisites

- Python 3.11+
- FFmpeg (`sudo apt install ffmpeg`)

### Installation

```bash
# Clone the repo
git clone <repo-url>
cd anime-ai-agent

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Run the server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000 in your browser.

### Optional: Enable AI Providers

**Ollama (Local LLM):**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull mistral

# The agent auto-detects Ollama
```

**HuggingFace (Anime Image Generation):**
```bash
# Set your HuggingFace token (optional, some models work without it)
export HF_API_TOKEN="your_token_here"
```

## Usage

1. Open the web dashboard at http://localhost:8000
2. Describe your anime story in the text box
3. Click "Create Anime"
4. Watch the real-time progress as the agent:
   - Analyzes your story
   - Creates a storyboard
   - Designs characters
   - Generates scenes
   - Animates everything
   - Assembles the final video
5. Download your anime video!

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/create` | Start anime creation |
| GET | `/api/projects` | List all projects |
| GET | `/api/project/{id}` | Get project details |
| GET | `/api/project/{id}/video` | Download video |
| WS | `/ws` | Real-time progress updates |

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `mistral` | LLM model name |
| `HF_API_TOKEN` | (empty) | HuggingFace API token |
| `HF_ANIME_MODEL` | `cagliostrolab/animagine-xl-3.1` | Image generation model |

## Project Structure

```
anime-ai-agent/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py             # Configuration
│   ├── websocket_manager.py  # Real-time updates
│   ├── agent/
│   │   ├── orchestrator.py   # Main pipeline orchestrator
│   │   ├── text_analyzer.py  # Story text analysis
│   │   ├── storyboard.py     # Storyboard generation
│   │   ├── character_designer.py  # Character design
│   │   ├── scene_generator.py     # Scene image generation
│   │   ├── animator.py       # Animation effects
│   │   └── video_assembler.py     # FFmpeg video assembly
│   ├── models/
│   │   ├── llm_provider.py   # LLM abstraction (Ollama)
│   │   └── image_provider.py # Image generation (HuggingFace)
│   └── utils/
│       └── helpers.py
├── frontend/
│   ├── index.html            # Web dashboard
│   ├── css/styles.css        # Cyberpunk-themed styles
│   └── js/app.js             # Frontend logic
├── output/                   # Generated videos
└── pyproject.toml
```

## License

MIT
