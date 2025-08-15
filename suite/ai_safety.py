import re, json

BAD_PHRASES = [
    r"\baccording to\b",
    r"\b(as|a)\s+study\s+(shows?|found)\b",
    r"\bsurvey(ed|s)?\b",
    r"\breports?\s+indicate\b",
]

def strip_unverifiable_phrases(text: str) -> str:
    out = text
    for p in BAD_PHRASES:
        out = re.sub(p, "[TBD source]", out, flags=re.I)
    return out

def allowed_numbers_from_facts(facts: dict) -> set[str]:
    joined = " ".join(
        str(v) if not isinstance(v, (list, dict, tuple, set)) else " ".join(map(str, v))
        for v in facts.values()
    )
    # capture bare numbers and percents present in facts
    return set(re.findall(r"\d+%?", joined))

def enforce_no_unverified_numbers(text: str, allowed: set[str]) -> str:
    # allow 4-digit years if present in text AND in allowed numbers (facts)
    tokens = re.findall(r'(?<!\w)(\d+%?)(?!\w)', text)
    bad = [t for t in tokens if t not in allowed]
    if bad:
        for t in set(bad):
            text = re.sub(rf'(?<!\w){re.escape(t)}(?!\w)', '[TBD]', text)
        text += "\n\n[Note: Removed unverified numbers; please replace with confirmed values.]"
    return text

def parse_model_json(s: str) -> dict:
    """Parse a JSON object from a model string output.

    Models occasionally wrap JSON in markdown fences or add prose before or
    after the JSON block. This helper attempts to extract the first JSON
    object it can find and raises a clear error when none is present.
    """

    s = s.strip()
    # Remove any markdown ```json fences or plain ``` fences wherever they
    # appear. This is more forgiving than requiring them to be at the very
    # start or end of the string.
    s = re.sub(r"```(?:json)?", "", s, flags=re.I)

    if not s:
        raise ValueError("Empty model response")

    # Find the first JSON object within the string. This handles cases where
    # the model prepends explanatory text before the JSON output.
    match = re.search(r"\{.*\}", s, flags=re.S)
    if not match:
        raise ValueError("No JSON object found in model response")

    return json.loads(match.group(0))
