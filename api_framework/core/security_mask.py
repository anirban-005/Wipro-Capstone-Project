"""Protection for credentials included in diagnostic evidence."""
import re


_BEARER_TOKEN = re.compile(r"Bearer\s+[a-zA-Z0-9\-_\.]+", re.IGNORECASE)


def mask_sensitive_data(log_string: str) -> str:
    """Replace Bearer credentials in arbitrary HTTP or JSON diagnostic text."""
    return _BEARER_TOKEN.sub("Bearer [REDACTED_TOKEN]", str(log_string))
