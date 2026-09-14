import subprocess

from app.core.config import settings


class FFmpegError(Exception):
    pass


def _ffprobe_path() -> str:
    path = settings.ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe")
    if path == settings.ffmpeg_path:
        path = path.replace("ffmpeg", "ffprobe")
    return path


def run(args: list[str], timeout: float = 120.0) -> None:
    try:
        result = subprocess.run(
            [settings.ffmpeg_path, "-y", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError(f"ffmpeg timed out after {timeout}s") from exc
    if result.returncode != 0:
        raise FFmpegError(result.stderr[-2000:])


def probe_duration_seconds(path: str, timeout: float = 30.0) -> float:
    try:
        result = subprocess.run(
            [
                _ffprobe_path(),
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError(f"ffprobe timed out after {timeout}s") from exc
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise FFmpegError(f"Could not probe duration for {path}: {result.stderr[-500:]}")


def extract_segment(
    source_path: str,
    output_path: str,
    start_seconds: float,
    duration_seconds: float,
    *,
    reformat_vertical: bool = False,
    subtitle_path: str | None = None,
    width: int = 1080,
    height: int = 1920,
) -> None:
    args = ["-ss", f"{start_seconds:.3f}", "-i", source_path, "-t", f"{duration_seconds:.3f}"]

    video_filters = []
    if reformat_vertical:
        video_filters.append(
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
        )
    if subtitle_path:
        escaped = subtitle_path.replace("\\", "/").replace(":", r"\:")
        video_filters.append(f"subtitles='{escaped}'")

    if video_filters:
        args += ["-vf", ",".join(video_filters)]

    args += ["-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", output_path]
    run(args, timeout=180.0)


FPS = 25


def build_vertical_video(
    image_paths: list[str],
    audio_path: str,
    subtitle_path: str | None,
    output_path: str,
    duration: float,
    width: int = 1080,
    height: int = 1920,
) -> None:
    if not image_paths:
        raise FFmpegError("No images provided")

    per_image = duration / len(image_paths)
    frames = max(round(per_image * FPS), 1)

    inputs: list[str] = []
    for path in image_paths:
        inputs += ["-loop", "1", "-t", f"{per_image:.3f}", "-i", path]
    inputs += ["-i", audio_path]

    # Oversize the source before zoompan so panning has room to move without
    # exposing empty edges, then zoompan (Ken Burns) back down to target size.
    filter_parts = []
    for i in range(len(image_paths)):
        zoom_in = i % 2 == 0
        zoom_expr = "'min(zoom+0.0015,1.2)'" if zoom_in else "'if(eq(on,1),1.2,max(zoom-0.0015,1.0))'"
        filter_parts.append(
            f"[{i}:v]scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
            f"crop={width * 2}:{height * 2},"
            f"zoompan=z={zoom_expr}:d={frames}:s={width}x{height}:fps={FPS},setsar=1[v{i}]"
        )
    concat_inputs = "".join(f"[v{i}]" for i in range(len(image_paths)))
    filter_complex = ";".join(filter_parts) + f";{concat_inputs}concat=n={len(image_paths)}:v=1:a=0[vout]"

    video_label = "vout"
    if subtitle_path:
        escaped = subtitle_path.replace("\\", "/").replace(":", r"\:")
        filter_complex += f";[vout]subtitles='{escaped}'[vsub]"
        video_label = "vsub"

    args = [
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{video_label}]",
        "-map", f"{len(image_paths)}:a",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    run(args, timeout=180.0)
