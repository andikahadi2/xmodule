import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json(text: str):
    """Parse JSON out of an LLM response, tolerating markdown code fences and stray text."""
    match = _FENCE_RE.search(text)
    candidate = match.group(1) if match else text.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start = min((i for i in (candidate.find("["), candidate.find("{")) if i != -1), default=-1)
        end = max(candidate.rfind("]"), candidate.rfind("}"))
        if start == -1 or end == -1:
            raise
        return json.loads(candidate[start : end + 1])
