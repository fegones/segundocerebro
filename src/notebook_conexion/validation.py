"""Validación estricta antes de construir rutas de API o solicitudes."""

from __future__ import annotations

import ipaddress
import re
import uuid
from urllib.parse import urlsplit

from .errors import SecurityError

_PROFILE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,39}\Z")
_PROJECT = re.compile(r"[a-z][a-z0-9-]{4,62}[a-z0-9]\Z")
_MODEL = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}\Z")


def profile_name(value: str) -> str:
    if not isinstance(value, str) or not _PROFILE.fullmatch(value):
        raise SecurityError("Nombre de perfil inválido: use letras, números, - o _ (1-40).")
    return value


def project_id(value: str) -> str:
    if not isinstance(value, str) or not _PROJECT.fullmatch(value):
        raise SecurityError("Identificador de proyecto Google Cloud inválido.")
    return value


def notebook_name(value: str) -> str:
    pieces = value.split("/") if isinstance(value, str) else []
    if len(pieces) != 2 or pieces[0] != "notebooks":
        raise SecurityError("Se esperaba notebooks/<UUID>.")
    try:
        parsed = uuid.UUID(pieces[1])
    except (ValueError, AttributeError) as exc:
        raise SecurityError("UUID de cuaderno inválido.") from exc
    if str(parsed) != pieces[1].lower():
        raise SecurityError("Formato de UUID no canónico.")
    return f"notebooks/{parsed}"


def source_name(value: str) -> str:
    pieces = value.split("/") if isinstance(value, str) else []
    if len(pieces) != 4 or pieces[2] != "sources":
        raise SecurityError("Se esperaba notebooks/<UUID>/sources/<UUID>.")
    notebook_name("/".join(pieces[:2]))
    try:
        source_uuid = uuid.UUID(pieces[3])
    except (ValueError, AttributeError) as exc:
        raise SecurityError("UUID de fuente inválido.") from exc
    if str(source_uuid) != pieces[3].lower():
        raise SecurityError("Formato de UUID de fuente no canónico.")
    return value


def display_name(value: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise SecurityError("El título debe contener entre 1 y 500 caracteres.")
    return value.strip()


def public_url(value: str) -> str:
    """No descarga URLs; evita enviar destinos privados obvios al proveedor."""
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 32 for c in value):
        raise SecurityError("URL inválida o demasiado extensa.")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise SecurityError("URL no válida.") from exc
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        raise SecurityError("Solo se admiten URLs HTTPS públicas sin credenciales.")
    if port not in (None, 443):
        raise SecurityError("No se admiten puertos no estándar.")
    host = host.rstrip(".").lower()
    if host in {"localhost", "metadata.google.internal"} or host.endswith(
        (".localhost", ".local", ".internal")
    ):
        raise SecurityError("El destino no puede ser una red privada.")
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        if "." not in host:
            raise SecurityError("Se requiere un dominio público con puntos.")
    else:
        raise SecurityError("No se admiten direcciones IP literales.")
    return value


def source_text(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SecurityError("La fuente de texto no puede estar vacía.")
    if len(value.encode("utf-8")) > 1_000_000:
        raise SecurityError("La fuente excede el límite de 1 MB de la API.")
    return value


def model_name(value: str) -> str:
    if not isinstance(value, str) or not _MODEL.fullmatch(value):
        raise SecurityError("Nombre del modelo Gemini inválido.")
    return value
