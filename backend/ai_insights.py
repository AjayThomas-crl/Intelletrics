"""
Gemini / Groq AI Insights — scalable multi-provider client for dataset analysis.

Uses the official google-genai SDK for Gemini, and the OpenAI-compatible
Groq API as fallback.  When Gemini rate-limits (429), Groq is tried
automatically.

Design: one abstract interface (``AIClient``) implemented by:
  - ``GeminiClient``  — structured output via response_schema / Pydantic
  - ``GroqClient``    — JSON-mode fallback (OpenAI-compatible endpoint)

Add a new provider = implement ``AIClient`` + register in ``_ProviderChain``.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx
from groq import AsyncGroq, APIStatusError as GroqAPIError
from google import genai
from google.genai import types
from google.genai import errors as gemini_errors
from pydantic import BaseModel, Field
from typing_extensions import TypeVar

# ── Config ──────────────────────────────────────────────────────────────────

DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def _load_env_var(name: str) -> str | None:
    """Load *name* from backend/.env (inline comment‑safe)."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip()
        cpos = val.find(" #")
        if cpos != -1:
            val = val[:cpos].strip()
        if key.strip() == name:
            return val
    return None


def _load_gemini_env() -> str | None:
    return _load_env_var("GEMINI_API_KEY")


def _load_groq_env() -> str | None:
    return _load_env_var("GROQ_API_KEY")


# ── Shared structured-output schemas ────────────────────────────────────────

class DatasetInsight(BaseModel):
    """A single structured insight about the dataset."""
    title: str = Field(description="Short title (5-8 words)")
    detail: str = Field(
        description="1-2 sentence insight, with actual numbers from the profile"
    )
    category: str = Field(
        description="One of: data_quality, distribution, pattern, outlier, "
        "correlation, recommendation"
    )
    affected_columns: list[str] = Field(
        description="Column names this insight refers to"
    )


class InsightsResult(BaseModel):
    """Complete structured insights for one dataset."""
    summary: str = Field(
        description="One-paragraph executive summary (3-4 sentences)"
    )
    insights: list[DatasetInsight] = Field(
        description="3-5 structured insights"
    )


# ── Prompt builder ─────────────────────────────────────────────────────────

def build_insights_prompt(
    profiles: list[dict],
    filename: str = "",
    rows: int = 0,
    columns: int = 0,
) -> str:
    """Build the LLM prompt from dataset profiling data."""
    lines = [
        f"Dataset: {filename or 'unknown'}",
        f"Rows: {rows}, Columns: {columns}",
        "",
        "Column Profiles:",
    ]
    for p in profiles:
        name = p.get("name", "?")
        kind = p.get("type", "?")
        missing = p.get("missing", {})
        unique = p.get("uniqueness", {})
        stats = p.get("statistics")
        dist = p.get("distribution")

        parts = [f"  - {name} ({kind})"]
        parts.append(
            f"missing={missing.get('count', '?')} "
            f"({missing.get('percentage', '?')}%)"
        )
        parts.append(
            f"unique={unique.get('count', '?')} "
            f"({unique.get('ratio', '?')}%)"
        )

        if stats:
            parts.append(
                f"mean={stats.get('mean','?')} "
                f"median={stats.get('median','?')} "
                f"min={stats.get('min','?')} "
                f"max={stats.get('max','?')} "
                f"q1={stats.get('q1','?')} "
                f"q3={stats.get('q3','?')}"
            )
        if dist:
            parts.append(
                f"top={dist.get('top_value','?')} "
                f"({dist.get('top_count','?')} rows)"
            )
        lines.append(" | ".join(parts))

    return f"""You are a data analyst. Given the following dataset profile, produce:
1. A one-paragraph executive summary (3-4 sentences).
2. 3-5 structured insights covering data quality, distributions/patterns, and actionable observations.

Use actual numbers from the profile. Be specific.

{chr(10).join(lines)}"""


# ── Abstract client interface ──────────────────────────────────────────────

_T = TypeVar("_T", bound=BaseModel)


class AIClient(ABC):
    """Abstract interface every provider implements."""
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: type[_T],
        max_tokens: int = 4096,
    ) -> _T:
        ...
        
    async def generate_insights(
        self,
        profiles,
        filename="",
        rows=0,
        columns=0,
    ):
        prompt = build_insights_prompt(
            profiles,
            filename,
            rows,
            columns,
        )

        return await self.generate_structured(
            prompt,
            InsightsResult,
        )


    


# ── Gemini provider ─────────────────────────────────────────────────────────

class GeminiClient(AIClient):
    """Gemini provider — uses official google-genai SDK with response_schema."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_GEMINI_MODEL,
    ):
        key = api_key or _load_gemini_env()
        if not key:
            raise ValueError("GEMINI_API_KEY not found in backend/.env")
        self._client = genai.Client(api_key=key)
        self.model = model

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[_T],
        max_tokens: int = 4096,
    ) -> _T:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_model,
            max_output_tokens=max_tokens,
            temperature=0.3,
        )
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        if response.parsed is not None and isinstance(response.parsed, BaseModel):
            return response.parsed  # type: ignore[return-value]

        raw = response.text
        if raw is None:
            raise ValueError("Gemini returned no text content")
        return _parse_json_fallback(raw, response_model)


# ── Groq provider (OpenAI-compatible) ──────────────────────────────────────

class GroqClient(AIClient):
    """Groq provider — uses the official ``groq`` SDK (OpenAI-compatible).

    Groq doesn't support ``response_schema``, so we use JSON-mode
    (``response_format={"type": "json_object"}``) + server-side validation.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_GROQ_MODEL,
    ):
        key = api_key or _load_groq_env()
        if not key:
            raise ValueError("GROQ_API_KEY not found in backend/.env")
        self._client = AsyncGroq(api_key=key)
        self.model = model

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[_T],
        max_tokens: int = 4096,
    ) -> _T:
        chat = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a data analyst. Always respond with valid JSON "
                        f"matching the schema: {response_model.model_json_schema()}"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
            temperature=0.3,
        )

        raw = chat.choices[0].message.content
        if raw is None:
            raise ValueError("Groq returned no text content")

        return _parse_json_fallback(raw, response_model)


# ── JSON fallback parser (shared) ──────────────────────────────────────────

def _parse_json_fallback(raw: str, model: type[_T]) -> _T:
    """Parse raw JSON text into *model*, stripping markdown fences if needed."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    data: dict[str, Any] = json.loads(text)
    return model.model_validate(data)


# ── Provider registry + auto-fallback ──────────────────────────────────────

class _ProviderChain:
    """Tries providers in order; skips to next on 429 / auth errors."""

    _instance: _ProviderChain | None = None

    def __init__(self) -> None:
        self._providers: list[AIClient] = []

        # 1 — Gemini
        gemini_key = _load_gemini_env()
        if gemini_key:
            self._providers.append(GeminiClient(api_key=gemini_key))

        # 2 — Groq
        groq_key = _load_groq_env()
        if groq_key:
            self._providers.append(GroqClient(api_key=groq_key))

        if not self._providers:
            raise RuntimeError(
                "No AI provider configured. Set GEMINI_API_KEY and/or "
                "GROQ_API_KEY in backend/.env"
            )

    def list_providers(self) -> list[str]:
        return [type(p).__name__ for p in self._providers]

    async def generate_insights(
        self,
        profiles: list[dict],
        filename: str = "",
        rows: int = 0,
        columns: int = 0,
    ) -> InsightsResult:
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                return await provider.generate_insights(
                    profiles=profiles,
                    filename=filename,
                    rows=rows,
                    columns=columns,
                )
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    continue
                raise
            except gemini_errors.ClientError as e:
                last_error = e
                if e.code == 429:
                    continue
                raise
            except GroqAPIError as e:
                last_error = e
                if e.status_code == 429:
                    continue
                raise
            except Exception as e:
                last_error = e
                # Surface non‑rate‑limit errors from the last provider only
                if provider is self._providers[-1]:
                    raise
                continue

        raise RuntimeError(
            "All AI providers exhausted their quotas. "
            "Check GEMINI_API_KEY and GROQ_API_KEY limits, or try again later."
        ) from last_error


def get_provider_chain() -> _ProviderChain:
    if _ProviderChain._instance is None:
        _ProviderChain._instance = _ProviderChain()
    return _ProviderChain._instance


# ── Public convenience function (backward‑compatible) ───────────────────────

async def generate_insights(
    profiles: list[dict],
    filename: str = "",
    rows: int = 0,
    columns: int = 0,
) -> str:
    """Generate insights, auto‑falling back across configured providers.

    Returns a plain bullet‑point string (backward‑compatible with the frontend
    which expects ``summary: string``).
    """
    try:
        chain = get_provider_chain()
        result = await chain.generate_insights(
            profiles=profiles, filename=filename, rows=rows, columns=columns
        )
        bullets = "\n".join(f"- {i.detail}" for i in result.insights)
        return f"{result.summary}\n\n{bullets}"
    except Exception as e:
        return f"Error generating insights: {type(e).__name__}: {e}"
