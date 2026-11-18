"""Configuración sin tokens. Los secretos persisten exclusivamente en keyring nativo."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from platformdirs import user_config_path

from .errors import ConfigurationError, SecurityError
from .validation import profile_name, project_id

SERVICE_NAME = "notebook-conexion-v1"


def _ensure_secure_directory(directory: Path) -> None:
    """Rechaza carpetas symlink y aplica modo privado en POSIX."""
    for parent in (directory, *directory.parents):
        if parent.is_symlink():
            raise SecurityError("La ruta de configuración contiene un enlace simbólico.")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        directory.chmod(0o700)


def _write_private(path: Path, contents: str) -> None:
    _ensure_secure_directory(path.parent)
    if path.is_symlink():
        raise SecurityError("No se permite escribir sobre enlaces simbólicos.")
    fd, temporary = tempfile.mkstemp(prefix=".nb-", dir=path.parent)
    try:
        if os.name != "nt":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@dataclass(frozen=True)
class Profile:
    name: str
    project_id: str
    client_secrets: str
    allow_write: bool = False

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "Profile":
        if set(value) != {"name", "project_id", "client_secrets", "allow_write"}:
            raise ConfigurationError("Estructura de perfil incompatible.")
        name = profile_name(value["name"])
        project = project_id(value["project_id"])
        secrets = value["client_secrets"]
        if not isinstance(secrets, str) or not secrets.strip():
            raise ConfigurationError("Ruta de cliente OAuth no configurada.")
        if not isinstance(value["allow_write"], bool):
            raise ConfigurationError("Valor de permisos incorrecto.")
        return cls(name, project, secrets, value["allow_write"])


class ProfileStore:
    def __init__(self, root: Path | None = None):
        self.root = root or user_config_path("NotebookConexion", "IdeasInnovadoras")

    def path(self, name: str) -> Path:
        return self.root / "profiles" / f"{profile_name(name)}.json"

    def save(self, profile: Profile) -> None:
        validated = Profile.from_mapping(asdict(profile))
        # Evita mezclar sesión OAuth de una cuenta vieja con nuevo cliente/proyecto.
        if self.path(validated.name).exists():
            previous = self.load(validated.name)
            if (previous.project_id, previous.client_secrets) != (validated.project_id, validated.client_secrets):
                raise SecurityError("No reutilice un perfil para otra cuenta/proyecto: cree un nombre de perfil distinto y vincule Google de nuevo.")
        # No migration from any previous package or browser cookies.
        _write_private(self.path(validated.name), json.dumps(asdict(validated), indent=2))

    def load(self, name: str) -> Profile:
        path = self.path(name)
        if path.is_symlink():
            raise SecurityError("Enlace simbólico no permitido para perfiles.")
        try:
            content = path.read_text(encoding="utf-8")
            obj = json.loads(content)
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError("Perfil no encontrado o corrupto.") from exc
        if not isinstance(obj, dict):
            raise ConfigurationError("El perfil no es un objeto JSON.")
        result = Profile.from_mapping(obj)
        if result.name != name:
            raise SecurityError("No coincide el identificador del perfil.")
        return result

    def enable_write(self, name: str, enabled: bool, acknowledgment: str) -> None:
        if enabled and acknowledgment != "CONFIRMO-ESCRITURA":
            raise SecurityError("Para habilitar cambios escriba CONFIRMO-ESCRITURA.")
        current = self.load(name)
        self.save(Profile(current.name, current.project_id, current.client_secrets, enabled))

    def list_profiles(self) -> list[str]:
        directory = self.root / "profiles"
        if not directory.exists() or directory.is_symlink():
            return []
        return sorted(p.stem for p in directory.glob("*.json") if not p.is_symlink())
