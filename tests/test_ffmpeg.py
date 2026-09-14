import subprocess
from unittest.mock import patch

import pytest

from app.utils import ffmpeg


def test_run_wraps_timeout_as_ffmpeg_error():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=1)):
        with pytest.raises(ffmpeg.FFmpegError):
            ffmpeg.run(["-i", "in.mp4"], timeout=1)


def test_probe_duration_seconds_wraps_timeout_as_ffmpeg_error():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ffprobe", timeout=1)):
        with pytest.raises(ffmpeg.FFmpegError):
            ffmpeg.probe_duration_seconds("in.mp4", timeout=1)
