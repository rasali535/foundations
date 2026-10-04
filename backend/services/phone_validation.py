import re


def international_phone(value):
    raw = str(value or '').strip()
    # Only formatting punctuation is removed. Never infer a country code.
    clean = re.sub(r'[\s().-]', '', raw)
    if not re.fullmatch(r'\+[1-9]\d{7,14}', clean):
        raise ValueError('Enter a phone number with its country code, for example +26771234567.')
    return clean
