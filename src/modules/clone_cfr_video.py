# src/modules/clone_cfr_video_worker.py

from pathlib import Path
import imageio_ffmpeg as ffmpeg

import subprocess
from src.config import cfg, logger
from src.models.video_metadata import VideoMetadata


class CloneCFRVideo:
    @staticmethod
    def run(input_video_path: Path, output_video_path: Path) -> VideoMetadata:

        # Clone the original video to the session directory with CFR at the target fps.
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        command = [
            ffmpeg_path,
            "-y",
            "-i", str(input_video_path),
            "-loglevel", "quiet",
            "-vsync", "cfr",
            "-r", str(cfg.video.fps),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-an",
            str(output_video_path)
        ]

        process = subprocess.Popen(command)
        process.wait()

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {process.stderr.read()}")

        logger.info(f"Raw video processed and cloned with CFR to {output_video_path}")
        return VideoMetadata.from_file(output_video_path)
