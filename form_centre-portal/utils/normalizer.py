import re

def normalize(text):
    if not text:
        return ""
    # 1. Remove newlines and tabs
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    # 2. Remove the asterisk (*) and extra whitespace
    text = text.replace("*", "").strip()
    # 3. Collapse multiple spaces into one
    text = re.sub(r'\s+', ' ', text)
    return text.lower()