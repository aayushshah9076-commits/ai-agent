"""Text Analyzer - Parses user input to extract story elements."""

import json
import logging

from backend.models.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class StoryAnalysis:
    """Structured story analysis result."""

    def __init__(self, data: dict):
        self.title = data.get("title", "Untitled Anime")
        self.genre = data.get("genre", "Adventure")
        self.mood = data.get("mood", "Epic")
        self.themes = data.get("themes", [])
        self.setting = data.get("setting", {})
        self.characters = data.get("characters", [])
        self.summary = data.get("summary", "")
        self.estimated_scenes = data.get("estimated_scenes", 8)
        self.raw = data

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "genre": self.genre,
            "mood": self.mood,
            "themes": self.themes,
            "setting": self.setting,
            "characters": self.characters,
            "summary": self.summary,
            "estimated_scenes": self.estimated_scenes,
        }


class TextAnalyzer:
    """Analyzes user text input to extract story structure."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def analyze(self, text: str) -> StoryAnalysis:
        logger.info("Analyzing story text...")

        system_prompt = """You are an expert anime screenwriter and story analyst.
Analyze the provided text and extract a structured story breakdown for anime production.
You must respond with ONLY valid JSON, no other text."""

        prompt = f"""Analyze the following story/concept for anime production and return a JSON object with these fields:
- title: A compelling anime title
- genre: The genre (e.g., Action/Adventure, Romance, Sci-Fi, Fantasy)
- mood: The overall mood/tone
- themes: Array of main themes
- setting: Object with time_period, location, atmosphere
- characters: Array of character objects, each with name, role (main/supporting/antagonist), description, personality, appearance (detailed anime-style visual description)
- summary: Brief story summary
- estimated_scenes: Recommended number of scenes (6-20)

Story text:
{text}

Respond with ONLY the JSON object:"""

        result = await self.llm.generate_json(prompt, system_prompt)

        if not result:
            result = self._extract_from_text(text)

        analysis = StoryAnalysis(result)
        logger.info(f"Story analysis complete: '{analysis.title}' with {len(analysis.characters)} characters")
        return analysis

    def _extract_from_text(self, text: str) -> dict:
        """Basic heuristic extraction when LLM is unavailable."""
        words = text.split()
        title = " ".join(words[:6]).title() if len(words) >= 6 else text[:60].title()

        # Simple keyword detection
        genres = {
            "fight": "Action", "battle": "Action", "sword": "Action",
            "love": "Romance", "heart": "Romance",
            "space": "Sci-Fi", "robot": "Sci-Fi", "future": "Sci-Fi",
            "magic": "Fantasy", "dragon": "Fantasy", "wizard": "Fantasy",
            "school": "Slice of Life", "friend": "Slice of Life",
            "mystery": "Mystery", "detective": "Mystery",
            "demon": "Dark Fantasy", "horror": "Horror",
        }

        detected_genre = "Adventure"
        text_lower = text.lower()
        for keyword, genre in genres.items():
            if keyword in text_lower:
                detected_genre = genre
                break

        return {
            "title": title,
            "genre": detected_genre,
            "mood": "Epic and dramatic",
            "themes": ["courage", "adventure", "growth"],
            "setting": {
                "time_period": "Fantasy era",
                "location": "A vast mystical world",
                "atmosphere": "Grand and mysterious",
            },
            "characters": [
                {
                    "name": "Hero",
                    "role": "main",
                    "description": "The determined protagonist",
                    "personality": "Brave and kind-hearted",
                    "appearance": "anime style, spiky dark hair, bright determined eyes, wearing adventure gear, detailed",
                },
                {
                    "name": "Ally",
                    "role": "supporting",
                    "description": "A loyal companion",
                    "personality": "Wise and supportive",
                    "appearance": "anime style, long flowing hair, gentle eyes, wearing elegant robes, detailed",
                },
            ],
            "summary": text[:300],
            "estimated_scenes": 8,
        }
