import re


def normalize(text: str) -> str:
    """Normalize form label text for consistent comparison."""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = text.replace("*", "").strip()
    text = re.sub(r'\s+', ' ', text)
    return text.lower()
