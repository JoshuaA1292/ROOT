"""
Text embedding service using Google's text-embedding-004 model via google.genai SDK.
Supports both Vertex AI and Google AI Studio auth modes.
"""
from __future__ import annotations

import os
from google import genai as genai_client
from google.genai import types as genai_types
from app.config import settings

_client: genai_client.Client | None = None
EMBED_MODEL = "gemini-embedding-001"


def _get_client() -> genai_client.Client:
    global _client
    if _client is None:
        api_key = (
            settings.google_ai_studio_key
            or settings.gemini_api_key
            or os.environ.get("GOOGLE_AI_STUDIO_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )
        if api_key:
            _client = genai_client.Client(api_key=api_key)
        elif settings.google_cloud_project:
            _client = genai_client.Client(
                vertexai=True,
                project=settings.google_cloud_project,
                location=settings.google_cloud_location,
            )
        else:
            raise RuntimeError(
                "No Google AI credentials found. Set GOOGLE_AI_STUDIO_KEY or GOOGLE_CLOUD_PROJECT."
            )
    return _client


EMBED_DIMS = 768  # must match Atlas Vector Search index dimension


def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns a 768-dimensional float vector."""
    client = _get_client()
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
        config=genai_types.EmbedContentConfig(output_dimensionality=EMBED_DIMS),
    )
    return response.embeddings[0].values


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single API call."""
    client = _get_client()
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=genai_types.EmbedContentConfig(output_dimensionality=EMBED_DIMS),
    )
    return [e.values for e in response.embeddings]
