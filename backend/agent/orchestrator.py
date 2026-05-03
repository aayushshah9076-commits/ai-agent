"""Orchestrator - Main AI agent that coordinates the entire anime creation pipeline."""

import asyncio
import logging
import time
from pathlib import Path

from backend.agent.animator import Animator
from backend.agent.character_designer import CharacterDesigner
from backend.agent.scene_generator import SceneGenerator
from backend.agent.storyboard import StoryboardGenerator
from backend.agent.text_analyzer import TextAnalyzer
from backend.agent.video_assembler import VideoAssembler
from backend.config import OUTPUT_DIR
from backend.models.image_provider import ImageProvider
from backend.models.llm_provider import LLMProvider
from backend.websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)


class ProjectState:
    """Tracks the state of an anime project."""

    def __init__(self, project_id: str, input_text: str):
        self.project_id = project_id
        self.input_text = input_text
        self.status = "initialized"
        self.progress = 0.0
        self.current_stage = ""
        self.analysis = None
        self.storyboard = None
        self.characters = None
        self.scenes = None
        self.animated_scenes = None
        self.output_video = None
        self.project_dir = OUTPUT_DIR / project_id
        self.error = None
        self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "status": self.status,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "storyboard": self.storyboard.to_dict() if self.storyboard else None,
            "characters": [c.to_dict() for c in self.characters] if self.characters else None,
            "scenes": [s.to_dict() for s in self.scenes] if self.scenes else None,
            "animated_scenes": [a.to_dict() for a in self.animated_scenes] if self.animated_scenes else None,
            "output_video": str(self.output_video) if self.output_video else None,
            "error": self.error,
        }


class Orchestrator:
    """Main AI agent orchestrating the anime creation pipeline."""

    def __init__(self, ws_manager: ConnectionManager):
        self.ws = ws_manager
        self.llm = LLMProvider()
        self.image_provider = ImageProvider()
        self.text_analyzer = TextAnalyzer(self.llm)
        self.storyboard_gen = StoryboardGenerator(self.llm)
        self.character_designer = CharacterDesigner(self.llm, self.image_provider)
        self.scene_generator = SceneGenerator(self.image_provider)
        self.animator = Animator()
        self.video_assembler = VideoAssembler()

        self.projects: dict[str, ProjectState] = {}

    async def initialize(self):
        """Check availability of AI providers."""
        logger.info("Initializing Anime AI Agent...")
        llm_ok = await self.llm.check_availability()
        img_ok = await self.image_provider.check_availability()

        status = {
            "llm": "ollama" if llm_ok else "fallback_templates",
            "image": self.image_provider.active_model if img_ok else "placeholder_generator",
        }
        logger.info(f"Agent initialized: {status}")
        return status

    async def create_anime(self, input_text: str, project_id: str | None = None) -> ProjectState:
        """Execute the full anime creation pipeline."""
        if not project_id:
            project_id = f"anime_{int(time.time())}"

        state = ProjectState(project_id, input_text)
        state.project_dir.mkdir(parents=True, exist_ok=True)
        self.projects[project_id] = state

        try:
            # Stage 1: Text Analysis (0-15%)
            state.status = "analyzing"
            state.current_stage = "text_analysis"
            await self.ws.send_progress("text_analysis", "start", 0, "Analyzing your story concept...")

            state.analysis = await self.text_analyzer.analyze(input_text)
            state.progress = 15

            await self.ws.send_progress(
                "text_analysis", "complete", 15,
                f"Story analyzed: '{state.analysis.title}' - {state.analysis.genre}",
                {"analysis": state.analysis.to_dict()},
            )

            # Stage 2: Storyboard Generation (15-25%)
            state.current_stage = "storyboard"
            await self.ws.send_progress("storyboard", "start", 15, "Creating storyboard...")

            state.storyboard = await self.storyboard_gen.generate(state.analysis)
            state.progress = 25

            await self.ws.send_progress(
                "storyboard", "complete", 25,
                f"Storyboard created: {len(state.storyboard.scenes)} scenes, {state.storyboard.total_duration}s",
                {"storyboard": state.storyboard.to_dict()},
            )

            # Stage 3: Character Design (25-40%)
            state.current_stage = "character_design"
            await self.ws.send_progress("character_design", "start", 25, "Designing characters...")

            state.characters = await self.character_designer.design_characters(
                state.analysis, state.project_dir
            )
            state.progress = 40

            await self.ws.send_progress(
                "character_design", "complete", 40,
                f"Designed {len(state.characters)} characters",
                {"characters": [c.to_dict() for c in state.characters]},
            )

            # Stage 4: Scene Generation (40-65%)
            state.current_stage = "scene_generation"
            total_scenes = len(state.storyboard.scenes)
            await self.ws.send_progress("scene_generation", "start", 40, f"Generating {total_scenes} scenes...")

            state.scenes = await self.scene_generator.generate_scenes(
                state.storyboard.scenes, state.characters, state.project_dir
            )
            state.progress = 65

            await self.ws.send_progress(
                "scene_generation", "complete", 65,
                f"Generated {len(state.scenes)} scene images",
                {"scenes": [s.to_dict() for s in state.scenes]},
            )

            # Stage 5: Animation (65-85%)
            state.current_stage = "animation"
            await self.ws.send_progress("animation", "start", 65, "Animating scenes...")

            state.animated_scenes = await self.animator.animate_scenes(
                state.scenes, state.project_dir
            )
            state.progress = 85

            total_frames = sum(a.frame_count for a in state.animated_scenes)
            await self.ws.send_progress(
                "animation", "complete", 85,
                f"Animation complete: {total_frames} frames generated",
            )

            # Stage 6: Video Assembly (85-100%)
            state.current_stage = "video_assembly"
            await self.ws.send_progress("video_assembly", "start", 85, "Assembling final video...")

            state.output_video = await self.video_assembler.assemble(
                state.animated_scenes,
                state.project_dir,
                f"{state.analysis.title.replace(' ', '_').lower()}.mp4",
            )
            state.progress = 100

            state.status = "complete"
            state.current_stage = "done"

            result = {
                "project_id": project_id,
                "title": state.analysis.title,
                "video_path": str(state.output_video),
                "duration": state.storyboard.total_duration,
                "scenes": len(state.storyboard.scenes),
                "characters": len(state.characters),
            }

            await self.ws.send_complete(result)
            logger.info(f"Anime creation complete: {result}")

            return state

        except Exception as e:
            state.status = "error"
            state.error = str(e)
            logger.exception(f"Anime creation failed: {e}")
            await self.ws.send_error(state.current_stage, str(e))
            return state

    def get_project(self, project_id: str) -> ProjectState | None:
        return self.projects.get(project_id)

    def list_projects(self) -> list[dict]:
        return [state.to_dict() for state in self.projects.values()]
