"""Ventanas de permiso temporales que solo puede emitir el usuario local.

Ninguna herramienta MCP permite emitir, ampliar ni revocar grants.
Los grants NO sustituyen el consentimiento requerido por el agente para cada operación.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from .errors import PermissionDenied, SecurityError
from .store import ProfileStore, _write_private
from .validation import profile_name

ACTIONS = {"write", "gemini"}
MAX_GRANT_SECONDS = 1800


def _path(profile: str) -> Path:
    return ProfileStore().root / "authorizations" / f"{profile_name(profile)}.json"


def grant(profile: str, action: str, *, minutes: int = 10) -> float:
    if action not in ACTIONS or not isinstance(minutes, int) or isinstance(minutes, bool) or not 1 <= minutes <= 30:
        raise SecurityError("Permiso temporal inválido.")
    if not ProfileStore().load(profile).allow_write:
        raise PermissionDenied("El perfil no tiene autorización general de escritura/envíos.")
    now = time.time()
    old = _read(profile)
    old[action] = now + minutes * 60
    _write_private(_path(profile), json.dumps(old, ensure_ascii=False))
    return old[action]


def _read(profile: str) -> dict:
    f = _path(profile)
    if f.is_symlink():
        raise SecurityError("Enlace simbólico en permisos temporales.")
    if not f.exists():
        return {}
    if f.stat().st_size > 1024:
        raise SecurityError("Archivo de autorización inválido.")
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SecurityError("No se puede validar el estado de autorización.") from exc
    if not isinstance(data, dict) or any(k not in ACTIONS or not isinstance(v, (float, int)) for k, v in data.items()):
        raise SecurityError("Autorización local corrupta.")
    return data


def authorized(profile: str, action: str) -> bool:
    if action not in ACTIONS:
        return False
    try:
        valid = _read(profile).get(action, 0)
    except SecurityError:
        return False
    now = time.time()
    return isinstance(valid, (float, int)) and now <= valid <= now + MAX_GRANT_SECONDS


def revoke(profile: str) -> None:
    f = _path(profile)
    if f.is_symlink():
        raise SecurityError("Enlace simbólico en permisos temporales.")
    f.unlink(missing_ok=True)
