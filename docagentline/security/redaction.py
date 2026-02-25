"""Data redaction utilities."""

import re
from typing import Any

from docagentline.config import get_settings


class Redactor:
    """Data redaction for sensitive fields."""

    def __init__(self):
        self.settings = get_settings()
        self.redact_fields = set(field.lower() for field in self.settings.redact_fields)

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive fields in dictionary.

        Args:
            data: Dictionary to redact

        Returns:
            Redacted dictionary copy
        """
        if not self.redact_fields:
            return data

        redacted = {}
        for key, value in data.items():
            if key.lower() in self.redact_fields:
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self.redact_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted[key] = value

        return redacted

    def redact_text(self, text: str) -> str:
        """Redact sensitive patterns in text.

        Args:
            text: Text to redact

        Returns:
            Redacted text
        """
        # SSN pattern
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN-REDACTED]", text)
        text = re.sub(r"\b\d{9}\b", "[SSN-REDACTED]", text)

        # Credit card pattern
        text = re.sub(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CC-REDACTED]", text)

        return text
