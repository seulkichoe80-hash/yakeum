"""Shared single-request Gemini transport with a strict local request budget."""
from contextlib import contextmanager
from contextvars import ContextVar

from .config import GeminiSettings
from .prompt import SYSTEM_PROMPT

_counter = ContextVar('analysis_request_counter', default=None)


@contextmanager
def count_analysis_requests():
    """Count HTTP request starts, without retaining credentials or payloads."""
    counter = [0]
    token = _counter.set(counter)
    try:
        yield counter
    finally:
        _counter.reset(token)


def request_image(image_bytes: bytes, mime_type: str, settings: GeminiSettings) -> str:
    from google import genai
    from google.genai import types

    started = 0

    def before_request(request):
        nonlocal started
        if started >= 1:
            raise RuntimeError('Analysis request budget exceeded')
        started += 1
        counter = _counter.get()
        if counter is not None:
            counter[0] += 1

    options = types.HttpOptions(
        timeout=60000, retry_options=types.HttpRetryOptions(attempts=1),
        client_args={'event_hooks': {'request': [before_request]}},
    )
    with genai.Client(api_key=settings.api_key, vertexai=False, http_options=options) as client:
        response = client.models.generate_content(
            model=settings.model_name,
            contents=[SYSTEM_PROMPT, types.Part.from_bytes(
                data=image_bytes, mime_type=mime_type)],
            config=types.GenerateContentConfig(response_mime_type='application/json'),
        )
        return response.text
