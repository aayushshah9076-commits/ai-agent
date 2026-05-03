"""Image generation provider using HuggingFace Inference API."""

import io
import logging
import time
from pathlib import Path

import httpx
from PIL import Image

from backend.config import ASSETS_DIR, HF_ANIME_MODEL, HF_API_TOKEN, HF_API_URL

logger = logging.getLogger(__name__)

# Fallback models to try if primary is unavailable
FALLBACK_MODELS = [
    "cagliostrolab/animagine-xl-3.1",
    "Linaqruf/animagine-xl-2.0",
    "stablediffusionapi/anything-v5",
    "gsdf/Counterfeit-V2.5",
    "stabilityai/stable-diffusion-xl-base-1.0",
]


class ImageProvider:
    """Generates anime-style images via HuggingFace Inference API."""

    def __init__(self):
        self.api_url = HF_API_URL
        self.model = HF_ANIME_MODEL
        self.token = HF_API_TOKEN
        self.available = False
        self.active_model = self.model

    async def check_availability(self) -> bool:
        models_to_try = [self.model] + [m for m in FALLBACK_MODELS if m != self.model]

        for model in models_to_try:
            try:
                headers = self._get_headers()
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(f"{self.api_url}/{model}", headers=headers)
                    if resp.status_code == 200:
                        self.active_model = model
                        self.available = True
                        logger.info(f"Image provider available: {model}")
                        return True
            except Exception:
                continue

        logger.warning("No HuggingFace image models available - will generate placeholder images")
        self.available = False
        return False

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "low quality, worst quality, blurry, deformed",
        width: int = 1024,
        height: int = 576,
        save_path: str | None = None,
    ) -> Path:
        if save_path is None:
            filename = f"img_{int(time.time())}_{hash(prompt) % 10000}.png"
            save_path = str(ASSETS_DIR / "generated" / filename)

        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        if self.available:
            try:
                return await self._generate_hf(prompt, negative_prompt, width, height, save_path)
            except Exception as e:
                logger.error(f"HF generation failed: {e}")

        return self._generate_placeholder(prompt, width, height, save_path)

    async def _generate_hf(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        save_path: Path,
    ) -> Path:
        headers = self._get_headers()
        payload = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": negative_prompt,
                "width": min(width, 1024),
                "height": min(height, 1024),
                "num_inference_steps": 25,
                "guidance_scale": 7.5,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            for attempt in range(3):
                resp = await client.post(
                    f"{self.api_url}/{self.active_model}",
                    headers=headers,
                    json=payload,
                )

                if resp.status_code == 200:
                    img = Image.open(io.BytesIO(resp.content))
                    if img.size != (width, height):
                        img = img.resize((width, height), Image.LANCZOS)
                    img.save(str(save_path), "PNG")
                    logger.info(f"Generated image: {save_path}")
                    return save_path

                if resp.status_code == 503:
                    wait_time = resp.json().get("estimated_time", 30)
                    logger.info(f"Model loading, waiting {wait_time}s...")
                    import asyncio
                    await asyncio.sleep(min(wait_time, 60))
                    continue

                if resp.status_code == 429:
                    logger.warning("Rate limited, waiting 10s...")
                    import asyncio
                    await asyncio.sleep(10)
                    continue

                logger.error(f"HF API error {resp.status_code}: {resp.text[:200]}")
                break

        return self._generate_placeholder(prompt, width, height, save_path)

    def _generate_placeholder(self, prompt: str, width: int, height: int, save_path: Path) -> Path:
        """Generate a styled placeholder image with gradient and text."""
        import numpy as np

        img_array = np.zeros((height, width, 3), dtype=np.uint8)

        # Anime-style gradient background
        for y in range(height):
            ratio = y / height
            r = int(40 + 80 * ratio)
            g = int(20 + 40 * (1 - ratio))
            b = int(100 + 120 * (1 - ratio))
            img_array[y, :] = [r, g, b]

        # Add some visual interest with rectangles
        cx, cy = width // 2, height // 2
        for i in range(5):
            offset = i * 40
            y1 = max(0, cy - 100 + offset)
            y2 = min(height, cy - 60 + offset)
            x1 = max(0, cx - 200 + offset * 2)
            x2 = min(width, cx + 200 - offset * 2)
            color_shift = i * 20
            img_array[y1:y2, x1:x2] = [
                min(255, 80 + color_shift),
                min(255, 40 + color_shift),
                min(255, 160 + color_shift),
            ]

        img = Image.fromarray(img_array)

        # Add text overlay
        try:
            from PIL import ImageDraw, ImageFont

            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            except OSError:
                font = ImageFont.load_default()
                small_font = font

            # Title
            title = "ANIME AI AGENT"
            bbox = draw.textbbox((0, 0), title, font=font)
            tw = bbox[2] - bbox[0]
            draw.text(((width - tw) // 2, 30), title, fill=(255, 255, 255), font=font)

            # Scene description
            short_prompt = prompt[:80] + "..." if len(prompt) > 80 else prompt
            bbox2 = draw.textbbox((0, 0), short_prompt, font=small_font)
            tw2 = bbox2[2] - bbox2[0]
            draw.text(((width - tw2) // 2, height - 60), short_prompt, fill=(200, 200, 255), font=small_font)

            # "Placeholder" notice
            notice = "[Placeholder - Connect HuggingFace or Ollama for AI generation]"
            bbox3 = draw.textbbox((0, 0), notice, font=small_font)
            tw3 = bbox3[2] - bbox3[0]
            draw.text(((width - tw3) // 2, height - 30), notice, fill=(150, 150, 180), font=small_font)
        except ImportError:
            pass

        img.save(str(save_path), "PNG")
        logger.info(f"Generated placeholder image: {save_path}")
        return save_path

    async def generate_character_sheet(
        self,
        character_description: str,
        character_name: str,
        save_dir: Path | None = None,
    ) -> list[Path]:
        if save_dir is None:
            save_dir = ASSETS_DIR / "generated" / "characters"
        save_dir.mkdir(parents=True, exist_ok=True)

        poses = [
            ("front view, standing pose", "front"),
            ("side view, profile", "side"),
            ("action pose, dynamic", "action"),
            ("close-up face, emotional expression", "closeup"),
        ]

        paths = []
        base_prompt = f"1character, anime style, {character_description}, masterpiece, best quality, detailed"

        for pose_desc, pose_name in poses:
            prompt = f"{base_prompt}, {pose_desc}"
            filename = f"{character_name.lower().replace(' ', '_')}_{pose_name}.png"
            path = await self.generate_image(
                prompt=prompt,
                save_path=str(save_dir / filename),
                width=768,
                height=1024,
            )
            paths.append(path)

        return paths
