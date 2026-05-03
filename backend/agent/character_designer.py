"""Character Designer - Creates consistent anime character designs."""

import logging
from pathlib import Path

from backend.agent.text_analyzer import StoryAnalysis
from backend.config import ASSETS_DIR
from backend.models.image_provider import ImageProvider
from backend.models.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class CharacterDesign:
    """Character design with reference images."""

    def __init__(self, name: str, description: str, appearance: str, images: list[Path]):
        self.name = name
        self.description = description
        self.appearance = appearance
        self.images = images
        self.prompt_base = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "appearance": self.appearance,
            "images": [str(p) for p in self.images],
            "prompt_base": self.prompt_base,
        }


class CharacterDesigner:
    """Designs anime characters from story analysis."""

    def __init__(self, llm: LLMProvider, image_provider: ImageProvider):
        self.llm = llm
        self.image_provider = image_provider

    async def design_characters(self, analysis: StoryAnalysis, project_dir: Path) -> list[CharacterDesign]:
        logger.info(f"Designing {len(analysis.characters)} characters...")
        char_dir = project_dir / "characters"
        char_dir.mkdir(parents=True, exist_ok=True)

        designs = []
        for char_data in analysis.characters:
            name = char_data.get("name", "Character")
            description = char_data.get("description", "An anime character")
            appearance = char_data.get("appearance", "anime style character")
            role = char_data.get("role", "supporting")

            logger.info(f"Designing character: {name} ({role})")

            # Build optimized prompt
            prompt = self._build_character_prompt(name, appearance, role)

            # Generate character sheet images
            images = await self.image_provider.generate_character_sheet(
                character_description=prompt,
                character_name=name,
                save_dir=char_dir / name.lower().replace(" ", "_"),
            )

            design = CharacterDesign(
                name=name,
                description=description,
                appearance=appearance,
                images=images,
            )
            design.prompt_base = prompt
            designs.append(design)

            logger.info(f"Character '{name}' designed with {len(images)} reference images")

        return designs

    def _build_character_prompt(self, name: str, appearance: str, role: str) -> str:
        """Build an optimized SD prompt for character generation."""
        quality_tags = "masterpiece, best quality, highly detailed, sharp focus"
        style_tags = "anime style, anime art, manga style"

        role_enhancements = {
            "main": "heroic aura, protagonist, confident stance",
            "supporting": "warm expression, supportive presence",
            "antagonist": "intimidating, dark aura, menacing",
            "mentor": "wise appearance, dignified, experienced",
        }

        role_extra = role_enhancements.get(role, "")

        parts = [
            "1character",
            style_tags,
            appearance,
            role_extra,
            quality_tags,
            "detailed face, detailed eyes, detailed hair",
            "full body",
        ]

        return ", ".join(p for p in parts if p)
