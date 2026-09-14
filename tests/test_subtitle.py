from app.utils.subtitle import generate_srt


def test_generate_srt_basic_structure():
    srt = generate_srt("Hook line\nProblem line\nSolution line", duration=9.0)

    assert "1\n00:00:00,000 --> " in srt
    assert "Hook line" in srt
    assert "Problem line" in srt
    assert "Solution line" in srt
    assert srt.count("-->") == 3


def test_generate_srt_empty_script_returns_empty():
    assert generate_srt("", duration=10.0) == ""


def test_generate_srt_proportional_to_line_length():
    srt = generate_srt("short\na much longer line than the first one", duration=10.0)
    blocks = srt.strip().split("\n\n")
    assert len(blocks) == 2

    def start_end(block: str):
        timing = block.splitlines()[1]
        start, end = timing.split(" --> ")
        return start, end

    first_start, first_end = start_end(blocks[0])
    second_start, second_end = start_end(blocks[1])
    assert first_start == "00:00:00,000"
    assert first_end == second_start
