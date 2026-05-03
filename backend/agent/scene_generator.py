"""Scene Generator - Creates background and scene images."""

import asyncio
import logging
from pathlib import Path

from backend.agent.character_designer import CharacterDesign
from backend.agent.storyboard import Scene
from backend.models.image_provider import ImageProvider

logger = logging.getLogger(__name__)


class GeneratedScene:
    """A generated scene with background and composite images."""

    def __init__(self, scene: Scene, background_path: Path):
        self.scene = scene
        self.background_path = background_path
        self.composite_path: Path | None = None
        self.character_overlays: list[Path] = []

    def to_dict(self) -> dict:
        return {
            "scene_number": self.scene.scene_number,
            "title": self.scene.title,
            "background": str(self.background_path),
            "composite": str(self.composite_path) if self.composite_path else None,
            "duration": self.scene.duration,
            "dialogue": self.scene.dialogue,
            "transition": self.scene.transition,
        }


class SceneGenerator:
    """Generates scene backgrounds and composites."""

    def __init__(self, image_provider: ImageProvider):
        self.image_provider = image_provider

    async def generate_scenes(
        self,
        scenes: list[Scene],
        characters: list[CharacterDesign],
        project_dir: Path,
    ) -> list[GeneratedScene]:
        logger.info(f"Generating {len(scenes)} scene images...")
        scene_dir = project_dir / "scenes"
        scene_dir.mkdir(parents=True, exist_ok=True)

        generated = []
        for scene in scenes:
            logger.info(f"Generating scene {scene.scene_number}: {scene.title}")

            # Generate background
            bg_path = scene_dir / f"scene_{scene.scene_number:03d}_bg.png"
            await self.image_provider.generate_image(
                prompt=scene.background_prompt,
                negative_prompt="low quality, worst quality, blurry, deformed, watermark, text, logo, signature",
                width=1920,
                height=1080,
                save_path=str(bg_path),
            )

            gen_scene = GeneratedScene(scene, bg_path)

            # If characters are present, generate character overlay
            present_chars = [c for c in characters if c.name in scene.characters_present]
            if present_chars:
                char_overlay_path = scene_dir / f"scene_{scene.scene_number:03d}_chars.png"
                char_prompt = self._build_scene_character_prompt(scene, present_chars)
                await self.image_provider.generate_image(
                    prompt=char_prompt,
                    negative_prompt="low quality, worst quality, blurry, deformed, bad anatomy, bad hands",
                    width=1920,
                    height=1080,
                    save_path=str(char_overlay_path),
                )
                gen_scene.composite_path = char_overlay_path

            generated.append(gen_scene)
            logger.info(f"Scene {scene.scene_number} generated")
            await asyncio.sleep(0)

        return generated

    def _build_scene_character_prompt(self, scene: Scene, characters: list[CharacterDesign]) -> str:
        """Build prompt for scene with characters."""
        parts = []

        # Number of characters
        char_count = len(characters)
        if char_count == 1:
            parts.append("1character")
        elif char_count == 2:
            parts.append("2characters, duo")
        else:
            parts.append(f"{char_count}characters, group")

        # Character appearances
        for char in characters[:3]:  # Limit to 3 characters per prompt
            parts.append(char.appearance)

        # Scene context
        parts.append(scene.mood)
        parts.append(scene.camera)

        # Extract key elements from background prompt
        bg_keywords = scene.background_prompt.split(",")[:3]
        parts.extend(bg_keywords)

        # Quality tags
        parts.extend(["anime style", "masterpiece", "best quality", "detailed"])

        return ", ".join(parts)
