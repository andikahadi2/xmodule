def _format_timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def generate_srt(script_text: str, duration: float) -> str:
    lines = [line.strip() for line in script_text.splitlines() if line.strip()]
    if not lines:
        return ""

    weights = [max(len(line), 1) for line in lines]
    total_weight = sum(weights)

    entries = []
    cursor = 0.0
    for line, weight in zip(lines, weights):
        length = duration * (weight / total_weight)
        start, end = cursor, cursor + length
        entries.append((start, end, line))
        cursor = end

    srt_blocks = []
    for i, (start, end, line) in enumerate(entries, start=1):
        srt_blocks.append(
            f"{i}\n{_format_timestamp(start)} --> {_format_timestamp(end)}\n{line}\n"
        )
    return "\n".join(srt_blocks)
