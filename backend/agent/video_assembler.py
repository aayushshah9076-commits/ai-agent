"""Video Assembler - Combines animated scenes into final video using FFmpeg."""

import asyncio
import logging
import shutil
from pathlib import Path

from backend.agent.animator import AnimatedScene
from backend.config import DEFAULT_FPS, TRANSITION_DURATION, VIDEO_HEIGHT, VIDEO_WIDTH

logger = logging.getLogger(__name__)


class VideoAssembler:
    """Assembles animated scenes into a final video with transitions."""

    def __init__(self):
        self.fps = DEFAULT_FPS
        self.width = VIDEO_WIDTH
        self.height = VIDEO_HEIGHT
        self.ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"

    async def assemble(
        self,
        animated_scenes: list[AnimatedScene],
        project_dir: Path,
        output_filename: str = "anime_episode.mp4",
    ) -> Path:
        logger.info(f"Assembling {len(animated_scenes)} scenes into video...")

        output_path = project_dir / output_filename

        # Step 1: Create individual scene videos
        scene_videos = []
        for scene in animated_scenes:
            video_path = await self._create_scene_video(scene, project_dir)
            if video_path:
                scene_videos.append(video_path)

        if not scene_videos:
            logger.error("No scene videos were created")
            return await self._create_fallback_video(output_path)

        # Step 2: Create transitions and concat
        if len(scene_videos) == 1:
            shutil.copy2(str(scene_videos[0]), str(output_path))
        else:
            await self._concat_with_transitions(scene_videos, output_path)

        # Cleanup intermediate files
        for v in scene_videos:
            try:
                v.unlink()
            except Exception:
                pass

        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"Video assembled: {output_path} ({size_mb:.1f} MB)")
        else:
            logger.error("Video assembly failed")
            return await self._create_fallback_video(output_path)

        return output_path

    async def _create_scene_video(self, scene: AnimatedScene, project_dir: Path) -> Path | None:
        """Create video from scene frames."""
        scene_num = scene.scene.scene.scene_number
        output = project_dir / f"scene_{scene_num:03d}.mp4"

        frame_pattern = str(scene.frames_dir / "frame_%06d.png")

        # Check if frames exist
        frames = list(scene.frames_dir.glob("frame_*.png"))
        if not frames:
            logger.warning(f"No frames found for scene {scene_num}")
            return None

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-framerate", str(self.fps),
            "-i", frame_pattern,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2",
            str(output),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            if proc.returncode != 0:
                logger.error(f"FFmpeg scene {scene_num} error: {stderr.decode()[:300]}")
                return None

            logger.info(f"Scene {scene_num} video created: {output}")
            return output

        except asyncio.TimeoutError:
            logger.error(f"FFmpeg timeout for scene {scene_num}")
            return None
        except Exception as e:
            logger.error(f"Scene video creation failed: {e}")
            return None

    async def _concat_with_transitions(self, scene_videos: list[Path], output_path: Path) -> None:
        """Concatenate scene videos with cross-fade transitions."""
        # Create concat file list
        concat_file = output_path.parent / "concat_list.txt"
        with open(str(concat_file), "w") as f:
            for video in scene_videos:
                f.write(f"file '{video}'\n")

        # Build complex filter for crossfade transitions
        n = len(scene_videos)
        if n <= 1:
            return

        transition_dur = TRANSITION_DURATION

        # For many scenes, use simple concat to avoid filter complexity
        if n > 8:
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                str(output_path),
            ]
        else:
            # Build xfade filter chain
            inputs = []
            for v in scene_videos:
                inputs.extend(["-i", str(v)])

            filter_parts = []
            # Get durations for offset calculation
            offsets = []
            accumulated = 0
            for i, v in enumerate(scene_videos[:-1]):
                # Estimate duration from file (fallback 8 seconds)
                dur = await self._get_video_duration(v)
                if i == 0:
                    offset = dur - transition_dur
                else:
                    offset = accumulated + dur - transition_dur
                offsets.append(max(0, offset))
                accumulated = offset

            # Build xfade filter
            current_stream = "[0:v]"
            for i in range(1, n):
                next_stream = f"[{i}:v]"
                out_label = f"[v{i}]" if i < n - 1 else "[outv]"
                offset = offsets[i - 1] if i - 1 < len(offsets) else i * 6

                transition_type = ["fade", "wipeleft", "wiperight", "slidedown", "circlecrop"][i % 5]

                filter_parts.append(
                    f"{current_stream}{next_stream}xfade=transition={transition_type}:duration={transition_dur}:offset={offset}{out_label}"
                )
                current_stream = out_label if i < n - 1 else "[outv]"

            if not filter_parts:
                filter_str = "[0:v]copy[outv]"
            else:
                filter_str = ";".join(filter_parts)

            cmd = [
                self.ffmpeg_path,
                "-y",
                *inputs,
                "-filter_complex", filter_str,
                "-map", "[outv]",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                str(output_path),
            ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

            if proc.returncode != 0:
                logger.warning(f"Transition concat failed, falling back to simple concat: {stderr.decode()[:200]}")
                await self._simple_concat(scene_videos, output_path, concat_file)

        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Complex concat failed ({e}), using simple concat")
            await self._simple_concat(scene_videos, output_path, concat_file)

        # Cleanup
        try:
            concat_file.unlink()
        except Exception:
            pass

    async def _simple_concat(self, scene_videos: list[Path], output_path: Path, concat_file: Path) -> None:
        """Simple concatenation without transitions."""
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=120)

    async def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            return float(stdout.decode().strip())
        except Exception:
            return 8.0

    async def _create_fallback_video(self, output_path: Path) -> Path:
        """Create a minimal fallback video if assembly fails."""
        from PIL import Image, ImageDraw, ImageFont

        # Create a single frame
        img = Image.new("RGB", (self.width, self.height), (20, 10, 40))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        except OSError:
            font = ImageFont.load_default()

        text = "Anime AI Agent - Video Generation"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((self.width - tw) // 2, self.height // 2 - 30), text, fill=(255, 255, 255), font=font)

        frame_path = output_path.parent / "fallback_frame.png"
        img.save(str(frame_path))

        cmd = [
            self.ffmpeg_path, "-y",
            "-loop", "1", "-i", str(frame_path),
            "-c:v", "libx264", "-t", "5",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()

        frame_path.unlink(missing_ok=True)
        return output_path
