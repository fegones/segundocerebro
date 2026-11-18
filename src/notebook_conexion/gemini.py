"""Conector independiente Gemini Developer API con clave personal del usuario."""

from __future__ import annotations

from .errors import ConfigurationError, PermissionDenied, RemoteServiceError, SecurityError
from .secrets import get_secret
from .store import Profile
from .transport import JsonTransport
from .validation import model_name

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiClient:
    def __init__(self, profile: Profile, *, transport: JsonTransport | None = None):
        self.profile = profile
        self.transport = transport or JsonTransport(GEMINI_BASE, timeout_seconds=90)

    def generate(self, prompt: str, *, model: str = "gemini-3.8-flash", response_json: bool = False) -> str:
        if not self.profile.allow_write:
            raise PermissionDenied("Envió de contenido bloqueado. Habilite la política de escritura.")
        if not isinstance(prompt, str) or not prompt.strip():
            raise SecurityError("El prompt no puede estar vacío.")
        if len(prompt.encode("utf-8")) > 250_000:
            raise SecurityError("Prompt demasiado extenso para el cliente local.")
        key = get_secret(self.profile.name, "gemini-api-key")
        if not key:
            raise ConfigurationError("Configure su propia clave Gemini API.")
        result = self.transport.request(
            "POST",
            f"/models/{model_name(model)}:generateContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            payload={"contents": [{"parts": [{"text": prompt}]}],
                     **({"generationConfig": {"responseMimeType": "application/json"}} if response_json else {})},
        )
        candidates = result.get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            raise RemoteServiceError("El modelo no devolvió contenido de texto.")
        try:
            parts = candidates[0]["content"]["parts"]
            response = "\n".join(item["text"] for item in parts if isinstance(item.get("text"), str))
        except (KeyError, IndexError, TypeError) as exc:
            raise RemoteServiceError("Respuesta de Gemini no compatible con salida de texto.") from exc
        if not response:
            raise RemoteServiceError("Gemini no devolvió contenido de texto.")
        return response
