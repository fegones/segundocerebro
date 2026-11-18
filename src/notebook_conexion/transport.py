"""Transporte HTTPS restrictivo con salida limitada y cero redirecciones."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .errors import RemoteServiceError

MAX_RESPONSE_BYTES = 2_000_000


class JsonTransport:
    def __init__(self, base_url: str, *, transport: httpx.BaseTransport | None = None, timeout_seconds: int = 25):
        if base_url not in {
            "https://notebook.googleapis.com/v1",
            "https://generativelanguage.googleapis.com/v1beta",
        }:
            raise ValueError("Solo se permiten endpoints oficiales fijos.")
        if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or not 5 <= timeout_seconds <= 120:
            raise ValueError("Tiempo de espera HTTP fuera de rango permitido.")
        self.base_url = base_url
        self._transport = transport
        self.timeout_seconds = timeout_seconds

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str],
        payload: dict[str, Any] | None = None,
        params: Mapping[str, str | int] | None = None,
    ) -> dict[str, Any]:
        if method not in {"GET", "POST", "PATCH"} or not path.startswith("/"):
            raise ValueError("Método o ruta no admitidos.")
        if "//" in path or ".." in path or "?" in path or "#" in path:
            raise ValueError("Ruta HTTP insegura.")
        try:
            with httpx.Client(
                timeout=httpx.Timeout(self.timeout_seconds, connect=8),
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
            ) as client:
                with client.stream(
                    method,
                    self.base_url + path,
                    headers=dict(headers),
                    json=payload,
                    params=params,
                ) as response:
                    if response.status_code >= 300:
                        raise RemoteServiceError(
                            f"API remota: estado HTTP {response.status_code}. "
                            "No se muestra la respuesta para evitar filtraciones."
                        )
                    chunks: list[bytes] = []
                    used = 0
                    for piece in response.iter_bytes():
                        used += len(piece)
                        if used > MAX_RESPONSE_BYTES:
                            raise RemoteServiceError("Respuesta remota excesivamente grande.")
                        chunks.append(piece)
                    body = b"".join(chunks)
        except httpx.RequestError as exc:
            raise RemoteServiceError("Error de comunicación con el proveedor HTTPS.") from exc
        try:
            obj = __import__("json").loads(body)
        except (ValueError, UnicodeError) as exc:
            raise RemoteServiceError("Respuesta JSON del proveedor inválida.") from exc
        if not isinstance(obj, dict):
            raise RemoteServiceError("Estructura JSON inesperada.")
        return obj
