"""Manually list models visible to the configured Gemini account.

Run explicitly with:
    python -m backend.services.extraction.scripts.check_models

This performs an external Gemini API request.  It is intentionally not called
by tests, imports, or the application runtime.
"""

from __future__ import annotations

from backend.services.extraction.config import GeminiSettings


def main() -> int:
    from google import genai  # Optional live dependency; import only on command.

    settings = GeminiSettings.from_environment()
    client = genai.Client(api_key=settings.api_key)
    for model in client.models.list():
        print(model.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
