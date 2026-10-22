"""Gemini configuration with no guessed model default and no import-time I/O."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

MODEL_ENV_VAR = "YAKEUM_GEMINI_MODEL"
API_KEY_ENV_VAR = "GEMINI_API_KEY"


class GeminiConfigurationError(ValueError):
    """Safe configuration failure that never contains a credential value."""


@dataclass(frozen=True)
class GeminiSettings:
    model_name: str
    api_key: str

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "GeminiSettings":
        values = os.environ if environment is None else environment
        model_name = values.get(MODEL_ENV_VAR, "").strip()
        api_key = values.get(API_KEY_ENV_VAR, "").strip()
        if not model_name:
            raise GeminiConfigurationError(
                f"{MODEL_ENV_VAR} 환경변수에 실제 계정에서 확인한 모델명을 설정해야 합니다."
            )
        if not api_key:
            raise GeminiConfigurationError(
                f"{API_KEY_ENV_VAR} 환경변수를 설정해야 합니다."
            )
        return cls(model_name=model_name, api_key=api_key)
