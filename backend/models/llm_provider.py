"""LLM Provider - abstracts Ollama and fallback for text generation."""

import json
import logging
import re

import httpx

from backend.config import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)


class LLMProvider:
    """Provides LLM text generation via Ollama or built-in fallback."""

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL
        self.ollama_available = False

    async def check_availability(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    self.ollama_available = True
                    models = resp.json().get("models", [])
                    model_names = [m["name"] for m in models]
                    logger.info(f"Ollama available with models: {model_names}")
                    return True
        except Exception:
            pass
        logger.warning("Ollama not available - using built-in template engine")
        self.ollama_available = False
        return False

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        if self.ollama_available:
            return await self._generate_ollama(prompt, system_prompt)
        return self._generate_fallback(prompt, system_prompt)

    async def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        raw = await self.generate(prompt, system_prompt)
        try:
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                return json.loads(match.group())
            match = re.search(r"\[[\s\S]*\]", raw)
            if match:
                return json.loads(match.group())
        except json.JSONDecodeError:
            pass
        return {}

    async def _generate_ollama(self, prompt: str, system_prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                }
                if system_prompt:
                    payload["system"] = system_prompt

                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                if resp.status_code == 200:
                    return resp.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
        return self._generate_fallback(prompt, system_prompt)

    def _generate_fallback(self, prompt: str, system_prompt: str) -> str:
        """Template-based fallback when no LLM is available.

        Analyzes the prompt to determine what kind of output is needed
        and generates structured responses using heuristics.
        """
        prompt_lower = prompt.lower()

        if "analyze" in prompt_lower and ("story" in prompt_lower or "text" in prompt_lower):
            return self._fallback_analyze_story(prompt)
        elif "storyboard" in prompt_lower or "scene" in prompt_lower:
            return self._fallback_storyboard(prompt)
        elif "character" in prompt_lower:
            return self._fallback_character(prompt)
        elif "prompt" in prompt_lower and "image" in prompt_lower:
            return self._fallback_image_prompt(prompt)
        else:
            return self._fallback_generic(prompt)

    def _fallback_analyze_story(self, prompt: str) -> str:
        # Extract the actual story text from the prompt (after "Story text:" marker)
        story_text = prompt
        markers = ["Story text:", "Story:", "story text:", "Text:"]
        for marker in markers:
            if marker in prompt:
                story_text = prompt.split(marker, 1)[1].strip()
                break

        # Remove instruction lines
        clean_lines = []
        for line in story_text.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("-") and not stripped.startswith("Respond") and "JSON" not in stripped:
                clean_lines.append(stripped)
        story_text = " ".join(clean_lines).strip() or "An epic anime adventure"

        # Generate a proper title from the story
        words = story_text.split()
        if len(words) >= 8:
            title = " ".join(words[:6]).rstrip(".,!?;:").title()
        elif len(words) >= 3:
            title = " ".join(words[:4]).rstrip(".,!?;:").title()
        else:
            title = story_text[:50].title()

        return json.dumps({
            "title": title,
            "genre": "Action/Adventure",
            "mood": "Epic and dramatic",
            "themes": ["courage", "friendship", "destiny"],
            "setting": {
                "time_period": "Fantasy era",
                "location": "A mystical world",
                "atmosphere": "Mysterious and grand"
            },
            "characters": [
                {
                    "name": "Protagonist",
                    "role": "main",
                    "description": "A determined young warrior with spiky dark hair and piercing eyes",
                    "personality": "Brave, determined, kind-hearted",
                    "appearance": "anime style, spiky black hair, blue eyes, wearing a dark cloak with silver armor"
                },
                {
                    "name": "Companion",
                    "role": "supporting",
                    "description": "A wise and loyal friend with magical abilities",
                    "personality": "Calm, intelligent, supportive",
                    "appearance": "anime style, long silver hair, green eyes, wearing mage robes with golden trim"
                }
            ],
            "summary": story_text[:200],
            "estimated_scenes": 8
        }, indent=2)

    def _fallback_storyboard(self, prompt: str) -> str:
        return json.dumps({
            "scenes": [
                {
                    "scene_number": 1,
                    "title": "Opening - The World Awakens",
                    "description": "A sweeping panoramic view of the fantasy world at dawn, establishing the setting",
                    "duration": 8,
                    "camera": "wide establishing shot, slow pan right",
                    "mood": "peaceful, anticipatory",
                    "dialogue": "",
                    "characters_present": [],
                    "background_prompt": "anime landscape, fantasy world, sunrise, mountains, ancient city in distance, clouds, golden light, studio ghibli style, masterpiece, best quality"
                },
                {
                    "scene_number": 2,
                    "title": "Introduction - The Protagonist",
                    "description": "The main character is introduced in their daily life",
                    "duration": 10,
                    "camera": "medium shot, slight zoom in",
                    "mood": "calm, contemplative",
                    "dialogue": "Another day begins... but something feels different today.",
                    "characters_present": ["Protagonist"],
                    "background_prompt": "anime village, morning, traditional japanese houses, cherry blossom trees, peaceful, warm lighting, detailed, masterpiece"
                },
                {
                    "scene_number": 3,
                    "title": "The Call to Adventure",
                    "description": "An event disrupts the peaceful world and sets the protagonist on their journey",
                    "duration": 12,
                    "camera": "dynamic angle, dramatic zoom",
                    "mood": "tense, exciting",
                    "dialogue": "What is that light in the sky? I must find out!",
                    "characters_present": ["Protagonist"],
                    "background_prompt": "anime dramatic sky, beam of light, mysterious portal, dark clouds gathering, epic, detailed, cinematic lighting, masterpiece"
                },
                {
                    "scene_number": 4,
                    "title": "Meeting the Companion",
                    "description": "The protagonist meets their companion who will join the journey",
                    "duration": 10,
                    "camera": "over-the-shoulder shot, conversation framing",
                    "mood": "curious, hopeful",
                    "dialogue": "You seek the source of the light too? Then let us travel together.",
                    "characters_present": ["Protagonist", "Companion"],
                    "background_prompt": "anime forest clearing, mystical atmosphere, fireflies, ancient trees, soft magical glow, detailed background, masterpiece"
                },
                {
                    "scene_number": 5,
                    "title": "The Journey Begins",
                    "description": "The duo sets out on their adventure through varied landscapes",
                    "duration": 10,
                    "camera": "tracking shot, moving alongside characters",
                    "mood": "adventurous, determined",
                    "dialogue": "",
                    "characters_present": ["Protagonist", "Companion"],
                    "background_prompt": "anime epic landscape, winding path through mountains, vast valley, dramatic clouds, adventure, journey, masterpiece, best quality"
                },
                {
                    "scene_number": 6,
                    "title": "First Challenge",
                    "description": "They face their first obstacle or enemy",
                    "duration": 12,
                    "camera": "action shots, fast cuts",
                    "mood": "intense, action-packed",
                    "dialogue": "Stay behind me! I will protect us!",
                    "characters_present": ["Protagonist", "Companion"],
                    "background_prompt": "anime battle scene, dark forest, magical energy, dramatic lighting, action pose, dynamic composition, epic, masterpiece"
                },
                {
                    "scene_number": 7,
                    "title": "Revelation",
                    "description": "A key discovery or revelation changes the course of the journey",
                    "duration": 10,
                    "camera": "close-up to wide shot reveal",
                    "mood": "awe, mystery",
                    "dialogue": "So this is what the prophecy spoke of... We are chosen.",
                    "characters_present": ["Protagonist", "Companion"],
                    "background_prompt": "anime ancient temple interior, glowing runes, magical artifacts, mysterious light, sacred place, detailed architecture, masterpiece"
                },
                {
                    "scene_number": 8,
                    "title": "Climax and Resolution",
                    "description": "The final confrontation and resolution of the story",
                    "duration": 15,
                    "camera": "epic wide shots with dramatic close-ups",
                    "mood": "epic, triumphant",
                    "dialogue": "Together, we can overcome anything!",
                    "characters_present": ["Protagonist", "Companion"],
                    "background_prompt": "anime epic finale, dramatic sky, beams of light, hero standing triumphant, magical energy, cinematic, sunset, masterpiece, best quality"
                }
            ],
            "total_duration": 87,
            "transitions": ["fade", "cross_dissolve", "wipe", "zoom"]
        }, indent=2)

    def _fallback_character(self, prompt: str) -> str:
        return json.dumps({
            "character_prompt": "1girl, anime style, detailed face, beautiful eyes, high quality, masterpiece, best quality, detailed hair, full body",
            "negative_prompt": "low quality, worst quality, blurry, deformed, ugly, bad anatomy, bad hands",
            "style_tags": ["anime", "detailed", "masterpiece"]
        }, indent=2)

    def _fallback_image_prompt(self, prompt: str) -> str:
        return json.dumps({
            "positive_prompt": "anime style, masterpiece, best quality, highly detailed, cinematic lighting, vibrant colors",
            "negative_prompt": "low quality, worst quality, blurry, deformed, ugly, bad anatomy, watermark, text",
        }, indent=2)

    def _fallback_generic(self, prompt: str) -> str:
        return "I understand your request. Processing with the anime AI agent pipeline."
