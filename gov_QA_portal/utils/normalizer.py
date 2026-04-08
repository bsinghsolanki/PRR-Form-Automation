import re

def normalize(text: str) -> str:
    """
    Lowercase, strip punctuation, collapse whitespace.
    'Date From:' → 'date from'
    """
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()