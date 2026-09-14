from faster_whisper import WhisperModel

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel("small", device="cpu", compute_type="int8")
    return _model


def _format_timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def transcribe_to_srt(audio_or_video_path: str, language: str = "id") -> str:
    model = _get_model()
    segments, _info = model.transcribe(audio_or_video_path, language=language, vad_filter=True)

    blocks = []
    for i, segment in enumerate(segments, start=1):
        text = segment.text.strip()
        if not text:
            continue
        blocks.append(
            f"{i}\n{_format_timestamp(segment.start)} --> {_format_timestamp(segment.end)}\n{text}\n"
        )
    return "\n".join(blocks)
