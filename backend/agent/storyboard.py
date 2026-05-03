"""Storyboard Generator - Creates detailed scene-by-scene storyboard."""

import json
import logging

from backend.agent.text_analyzer import StoryAnalysis
from backend.models.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class Scene:
    """Represents a single scene in the storyboard."""

    def __init__(self, data: dict):
        self.scene_number = data.get("scene_number", 0)
        self.title = data.get("title", f"Scene {self.scene_number}")
        self.description = data.get("description", "")
        self.duration = data.get("duration", 8)
        self.camera = data.get("camera", "medium shot")
        self.mood = data.get("mood", "neutral")
        self.dialogue = data.get("dialogue", "")
        self.characters_present = data.get("characters_present", [])
        self.background_prompt = data.get("background_prompt", "anime background, detailed, masterpiece")
        self.transition = data.get("transition", "cross_dissolve")

    def to_dict(self) -> dict:
        return {
            "scene_number": self.scene_number,
            "title": self.title,
            "description": self.description,
            "duration": self.duration,
            "camera": self.camera,
            "mood": self.mood,
            "dialogue": self.dialogue,
            "characters_present": self.characters_present,
            "background_prompt": self.background_prompt,
            "transition": self.transition,
        }


class Storyboard:
    """Complete storyboard with all scenes."""

    def __init__(self, scenes: list[Scene], metadata: dict | None = None):
        self.scenes = scenes
        self.metadata = metadata or {}
        self.total_duration = sum(s.duration for s in scenes)

    def to_dict(self) -> dict:
        return {
            "scenes": [s.to_dict() for s in self.scenes],
            "total_duration": self.total_duration,
            "scene_count": len(self.scenes),
            "metadata": self.metadata,
        }


class StoryboardGenerator:
    """Generates storyboards from story analysis."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate(self, analysis: StoryAnalysis) -> Storyboard:
        logger.info(f"Generating storyboard for '{analysis.title}'...")

        system_prompt = """You are an expert anime storyboard artist and director.
Create detailed storyboards with vivid scene descriptions optimized for AI image generation.
You must respond with ONLY valid JSON."""

        character_list = ", ".join([c.get("name", "Character") for c in analysis.characters])

        prompt = f"""Create a detailed anime storyboard for:
Title: {analysis.title}
Genre: {analysis.genre}
Mood: {analysis.mood}
Setting: {json.dumps(analysis.setting)}
Characters: {character_list}
Story: {analysis.summary}
Target scenes: {analysis.estimated_scenes}

Return a JSON object with:
- scenes: Array of scene objects, each with:
  - scene_number: Sequential number
  - title: Scene title
  - description: What happens in this scene
  - duration: Duration in seconds (6-15)
  - camera: Camera angle/movement description
  - mood: Scene mood
  - dialogue: Character dialogue (if any)
  - characters_present: Array of character names in scene
  - background_prompt: Detailed Stable Diffusion prompt for the background (include "anime style, masterpiece, best quality" and scene-specific details)
  - transition: Transition type (fade, cross_dissolve, wipe, zoom)

Make scenes visually diverse and cinematically interesting.
Include an opening establishing shot and a dramatic conclusion.

Respond with ONLY the JSON object:"""

        result = await self.llm.generate_json(prompt, system_prompt)

        scenes_data = []
        if isinstance(result, dict) and "scenes" in result:
            scenes_data = result["scenes"]
        elif isinstance(result, list):
            scenes_data = result

        if not scenes_data:
            scenes_data = self._generate_default_storyboard(analysis)

        scenes = []
        for i, scene_data in enumerate(scenes_data):
            if isinstance(scene_data, dict):
                scene_data["scene_number"] = i + 1
                # Enhance background prompts with anime quality tags
                bg_prompt = scene_data.get("background_prompt", "")
                if "masterpiece" not in bg_prompt.lower():
                    scene_data["background_prompt"] = f"{bg_prompt}, anime style, masterpiece, best quality, detailed"
                scenes.append(Scene(scene_data))

        storyboard = Storyboard(scenes, {"title": analysis.title, "genre": analysis.genre})
        logger.info(f"Storyboard complete: {len(scenes)} scenes, {storyboard.total_duration}s total")
        return storyboard

    def _generate_default_storyboard(self, analysis: StoryAnalysis) -> list[dict]:
        """Generate a default storyboard structure."""
        character_names = [c.get("name", f"Character_{i}") for i, c in enumerate(analysis.characters)]
        setting = analysis.setting

        location = setting.get("location", "mystical world")
        atmosphere = setting.get("atmosphere", "grand")

        return [
            {
                "title": "Opening - World Establishing",
                "description": f"A sweeping view of {location}, establishing the {atmosphere} atmosphere",
                "duration": 8,
                "camera": "wide panoramic shot, slow pan",
                "mood": "majestic, anticipatory",
                "dialogue": "",
                "characters_present": [],
                "background_prompt": f"anime landscape, {location}, panoramic view, {atmosphere}, sunrise, volumetric lighting, studio ghibli style, masterpiece, best quality, highly detailed",
                "transition": "fade",
            },
            {
                "title": "Introduction - Meet the Hero",
                "description": f"{character_names[0] if character_names else 'The protagonist'} is introduced",
                "duration": 10,
                "camera": "medium shot, character focus",
                "mood": "contemplative",
                "dialogue": "Today feels different... like destiny is calling.",
                "characters_present": character_names[:1],
                "background_prompt": f"anime town, peaceful morning, traditional architecture, warm lighting, {location}, detailed background, masterpiece",
                "transition": "cross_dissolve",
            },
            {
                "title": "The Catalyst",
                "description": "An extraordinary event disrupts the ordinary world",
                "duration": 10,
                "camera": "dramatic angle, quick zoom",
                "mood": "shocking, tense",
                "dialogue": "What... what is happening?!",
                "characters_present": character_names[:1],
                "background_prompt": "anime dramatic scene, explosion of light, dark clouds, magical energy, intense atmosphere, dynamic composition, masterpiece, best quality",
                "transition": "wipe",
            },
            {
                "title": "Alliance Formed",
                "description": "Key characters meet and decide to work together",
                "duration": 10,
                "camera": "two-shot, conversation framing",
                "mood": "hopeful, determined",
                "dialogue": "We share the same goal. Together, we can make it.",
                "characters_present": character_names[:2],
                "background_prompt": "anime forest clearing, ethereal light, ancient trees, mystical atmosphere, soft glow, detailed environment, masterpiece",
                "transition": "cross_dissolve",
            },
            {
                "title": "Journey Montage",
                "description": "The group travels through various landscapes",
                "duration": 12,
                "camera": "tracking shots, varied angles",
                "mood": "adventurous, uplifting",
                "dialogue": "",
                "characters_present": character_names,
                "background_prompt": "anime adventure landscape, epic journey, mountains and valleys, river crossing, dramatic sky, vibrant colors, cinematic, masterpiece",
                "transition": "cross_dissolve",
            },
            {
                "title": "Trial by Fire",
                "description": "The first major battle or challenge tests the group",
                "duration": 12,
                "camera": "dynamic action shots, close-ups",
                "mood": "intense, thrilling",
                "dialogue": "Don't give up! We've come too far!",
                "characters_present": character_names,
                "background_prompt": "anime battle scene, magical combat, energy blasts, dramatic lighting, action scene, dynamic poses, fire and lightning, masterpiece, best quality",
                "transition": "wipe",
            },
            {
                "title": "The Truth Revealed",
                "description": "A crucial discovery changes everything",
                "duration": 10,
                "camera": "slow reveal, dramatic close-up",
                "mood": "awe, revelation",
                "dialogue": "So this is the truth behind everything...",
                "characters_present": character_names[:2],
                "background_prompt": "anime mysterious chamber, ancient artifacts, glowing symbols, sacred knowledge, dramatic revelation, ethereal light, masterpiece",
                "transition": "zoom",
            },
            {
                "title": "Finale - Dawn of a New Era",
                "description": "The climactic resolution and a new beginning",
                "duration": 15,
                "camera": "epic wide shot, triumphant framing",
                "mood": "triumphant, hopeful",
                "dialogue": "This is just the beginning of our story!",
                "characters_present": character_names,
                "background_prompt": "anime epic finale, heroes standing together, golden sunset, dramatic clouds, rays of light, triumphant, emotional, cinematic, masterpiece, best quality",
                "transition": "fade",
            },
        ]
