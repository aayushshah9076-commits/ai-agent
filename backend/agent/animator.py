"""Animator - Applies animation effects to static scene images."""

import logging
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from backend.agent.scene_generator import GeneratedScene
from backend.config import DEFAULT_FPS, KEN_BURNS_ZOOM_RANGE, VIDEO_HEIGHT, VIDEO_WIDTH

logger = logging.getLogger(__name__)


class AnimatedScene:
    """Scene with animation frames ready for video assembly."""

    def __init__(self, scene: GeneratedScene, frames_dir: Path, frame_count: int):
        self.scene = scene
        self.frames_dir = frames_dir
        self.frame_count = frame_count
        self.fps = DEFAULT_FPS

    def to_dict(self) -> dict:
        return {
            "scene_number": self.scene.scene.scene_number,
            "title": self.scene.scene.title,
            "frames_dir": str(self.frames_dir),
            "frame_count": self.frame_count,
            "duration": self.scene.scene.duration,
            "dialogue": self.scene.scene.dialogue,
        }


class Animator:
    """Applies cinematic animation effects to scene images."""

    def __init__(self):
        self.fps = DEFAULT_FPS
        self.width = VIDEO_WIDTH
        self.height = VIDEO_HEIGHT

    async def animate_scenes(
        self,
        generated_scenes: list[GeneratedScene],
        project_dir: Path,
    ) -> list[AnimatedScene]:
        logger.info(f"Animating {len(generated_scenes)} scenes...")
        frames_base = project_dir / "frames"
        frames_base.mkdir(parents=True, exist_ok=True)

        animated = []
        for gen_scene in generated_scenes:
            scene_num = gen_scene.scene.scene_number
            logger.info(f"Animating scene {scene_num}: {gen_scene.scene.title}")

            scene_frames_dir = frames_base / f"scene_{scene_num:03d}"
            scene_frames_dir.mkdir(parents=True, exist_ok=True)

            duration = gen_scene.scene.duration
            total_frames = duration * self.fps

            # Choose animation effect based on scene type
            camera = gen_scene.scene.camera.lower()
            if "zoom" in camera:
                effect = "zoom"
            elif "pan" in camera:
                effect = "pan"
            elif "track" in camera:
                effect = "parallax"
            else:
                effect = "ken_burns"

            # Use composite if available, otherwise background
            source_img_path = gen_scene.composite_path or gen_scene.background_path

            frame_count = await self._generate_frames(
                source_path=source_img_path,
                output_dir=scene_frames_dir,
                total_frames=total_frames,
                effect=effect,
                dialogue=gen_scene.scene.dialogue,
                scene_title=gen_scene.scene.title,
            )

            animated.append(AnimatedScene(gen_scene, scene_frames_dir, frame_count))
            logger.info(f"Scene {scene_num} animated: {frame_count} frames")

        return animated

    async def _generate_frames(
        self,
        source_path: Path,
        output_dir: Path,
        total_frames: int,
        effect: str,
        dialogue: str = "",
        scene_title: str = "",
    ) -> int:
        """Generate animation frames from a source image."""
        try:
            source_img = Image.open(str(source_path)).convert("RGB")
        except Exception as e:
            logger.error(f"Failed to open source image: {e}")
            source_img = Image.new("RGB", (self.width, self.height), (30, 20, 60))

        # Upscale source for smooth animation
        scale_factor = 1.3
        scaled_w = int(self.width * scale_factor)
        scaled_h = int(self.height * scale_factor)
        source_img = source_img.resize((scaled_w, scaled_h), Image.LANCZOS)

        effects = {
            "ken_burns": self._effect_ken_burns,
            "zoom": self._effect_zoom,
            "pan": self._effect_pan,
            "parallax": self._effect_parallax,
        }

        effect_fn = effects.get(effect, self._effect_ken_burns)

        for frame_idx in range(total_frames):
            progress = frame_idx / max(total_frames - 1, 1)
            frame = effect_fn(source_img, progress, scaled_w, scaled_h)

            # Apply dialogue overlay
            if dialogue:
                frame = self._add_dialogue(frame, dialogue, progress)

            # Add scene title (first 2 seconds)
            fade_frames = self.fps * 2
            if frame_idx < fade_frames:
                title_alpha = 1.0 - (frame_idx / fade_frames)
                frame = self._add_scene_title(frame, scene_title, title_alpha)

            # Add subtle vignette
            frame = self._add_vignette(frame)

            frame_path = output_dir / f"frame_{frame_idx:06d}.png"
            frame.save(str(frame_path), "PNG")

        return total_frames

    def _effect_ken_burns(
        self, img: Image.Image, progress: float, src_w: int, src_h: int
    ) -> Image.Image:
        """Ken Burns effect - slow zoom with slight pan."""
        min_zoom, max_zoom = KEN_BURNS_ZOOM_RANGE
        zoom = min_zoom + (max_zoom - min_zoom) * progress

        crop_w = int(self.width / zoom)
        crop_h = int(self.height / zoom)

        # Smooth pan using sine wave
        max_offset_x = src_w - crop_w
        max_offset_y = src_h - crop_h
        offset_x = int(max_offset_x * (0.5 + 0.3 * math.sin(progress * math.pi)))
        offset_y = int(max_offset_y * (0.5 + 0.2 * math.cos(progress * math.pi * 0.7)))

        offset_x = max(0, min(offset_x, src_w - crop_w))
        offset_y = max(0, min(offset_y, src_h - crop_h))

        cropped = img.crop((offset_x, offset_y, offset_x + crop_w, offset_y + crop_h))
        return cropped.resize((self.width, self.height), Image.LANCZOS)

    def _effect_zoom(
        self, img: Image.Image, progress: float, src_w: int, src_h: int
    ) -> Image.Image:
        """Dramatic zoom in/out effect."""
        zoom = 1.0 + 0.25 * progress
        crop_w = int(self.width / zoom)
        crop_h = int(self.height / zoom)

        cx = src_w // 2
        cy = src_h // 2

        x1 = max(0, cx - crop_w // 2)
        y1 = max(0, cy - crop_h // 2)
        x2 = min(src_w, x1 + crop_w)
        y2 = min(src_h, y1 + crop_h)

        cropped = img.crop((x1, y1, x2, y2))
        return cropped.resize((self.width, self.height), Image.LANCZOS)

    def _effect_pan(
        self, img: Image.Image, progress: float, src_w: int, src_h: int
    ) -> Image.Image:
        """Horizontal pan across the image."""
        crop_w = self.width
        crop_h = self.height

        max_offset = src_w - crop_w
        offset_x = int(max_offset * progress)
        offset_y = (src_h - crop_h) // 2

        offset_x = max(0, min(offset_x, src_w - crop_w))
        offset_y = max(0, min(offset_y, src_h - crop_h))

        cropped = img.crop((offset_x, offset_y, offset_x + crop_w, offset_y + crop_h))
        return cropped.resize((self.width, self.height), Image.LANCZOS)

    def _effect_parallax(
        self, img: Image.Image, progress: float, src_w: int, src_h: int
    ) -> Image.Image:
        """Simulated parallax by moving crop position with easing."""
        ease = 0.5 - 0.5 * math.cos(progress * math.pi)

        crop_w = int(self.width * 1.05)
        crop_h = int(self.height * 1.05)

        max_offset_x = src_w - crop_w
        max_offset_y = src_h - crop_h

        offset_x = int(max_offset_x * ease)
        offset_y = int(max_offset_y * (0.5 + 0.15 * math.sin(progress * math.pi * 2)))

        offset_x = max(0, min(offset_x, src_w - crop_w))
        offset_y = max(0, min(offset_y, src_h - crop_h))

        cropped = img.crop((offset_x, offset_y, offset_x + crop_w, offset_y + crop_h))
        return cropped.resize((self.width, self.height), Image.LANCZOS)

    def _add_dialogue(self, frame: Image.Image, dialogue: str, progress: float) -> Image.Image:
        """Add anime-style dialogue subtitle overlay."""
        if not dialogue:
            return frame

        # Show dialogue in the middle portion of the scene
        if progress < 0.15 or progress > 0.90:
            return frame

        frame = frame.copy()
        draw = ImageDraw.Draw(frame)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        except OSError:
            font = ImageFont.load_default()

        # Calculate text position
        max_chars_per_line = 50
        lines = []
        words = dialogue.split()
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars_per_line:
                current_line = f"{current_line} {word}" if current_line else word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        # Draw dialogue box background
        line_height = 40
        box_height = len(lines) * line_height + 30
        box_y = self.height - box_height - 40

        # Semi-transparent black box
        overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle(
            [(60, box_y), (self.width - 60, box_y + box_height)],
            radius=15,
            fill=(0, 0, 0, 180),
        )
        frame = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(frame)

        # Draw text
        y = box_y + 15
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            x = (self.width - tw) // 2
            # Text shadow
            draw.text((x + 2, y + 2), line, fill=(0, 0, 0), font=font)
            draw.text((x, y), line, fill=(255, 255, 255), font=font)
            y += line_height

        return frame

    def _add_scene_title(self, frame: Image.Image, title: str, alpha: float) -> Image.Image:
        """Add scene title overlay with fade effect."""
        if alpha <= 0 or not title:
            return frame

        frame = frame.copy()
        draw = ImageDraw.Draw(frame)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), title, font=font)
        tw = bbox[2] - bbox[0]
        x = (self.width - tw) // 2
        y = self.height // 3

        color_val = int(255 * alpha)
        # Shadow
        draw.text((x + 3, y + 3), title, fill=(0, 0, 0, color_val), font=font)
        draw.text((x, y), title, fill=(255, 255, color_val, color_val), font=font)

        return frame

    def _add_vignette(self, frame: Image.Image) -> Image.Image:
        """Add subtle vignette effect for cinematic look."""
        w, h = frame.size
        vignette = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(vignette)

        # Draw concentric ellipses from dark edges to bright center
        for i in range(20):
            ratio = i / 20
            brightness = int(255 * (ratio ** 0.5))
            margin_x = int(w * 0.15 * (1 - ratio))
            margin_y = int(h * 0.15 * (1 - ratio))
            draw.ellipse(
                [margin_x, margin_y, w - margin_x, h - margin_y],
                fill=brightness,
            )

        # Apply vignette as brightness mask
        frame_array = np.array(frame, dtype=np.float32)
        vignette_array = np.array(vignette, dtype=np.float32) / 255.0
        vignette_array = np.clip(vignette_array * 0.4 + 0.6, 0, 1)  # Subtle effect

        result = frame_array * vignette_array[:, :, np.newaxis]
        return Image.fromarray(result.astype(np.uint8))
