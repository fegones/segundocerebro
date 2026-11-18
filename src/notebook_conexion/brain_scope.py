"""Alcance explícito y persistente. Los agentes MCP no pueden ampliarlo.

Una autorización de cuadernos se configura desde la aplicación local o CLI
interactivo por el propietario; la selección no se toma de prompts ni fuentes.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .errors import ConfigurationError, SecurityError
from .store import ProfileStore, _write_private
from .validation import notebook_name, profile_name

MAX_BINDINGS = 40


@dataclass(frozen=True, order=True)
class Binding:
    profile: str
    notebook: str

    def __post_init__(self):
        profile_name(self.profile)
        notebook_name(self.notebook)

    @property
    def key(self) -> str:
        return f"{self.profile}|{self.notebook}"


class ScopeStore:
    def __init__(self, root: Path | None = None, profiles: ProfileStore | None = None):
        self.profiles = profiles or ProfileStore()
        self.root = Path(root) if root is not None else self.profiles.root

    @property
    def path(self) -> Path:
        return self.root / "second_brain" / "scope.json"

    def load(self) -> tuple[Binding, ...]:
        path = self.path
        if path.is_symlink() or path.parent.is_symlink():
            raise SecurityError("Alcance local en ruta no autorizada.")
        if not path.exists():
            return ()
        if path.stat().st_size > 16_000:
            raise SecurityError("Archivo de alcance excesivo.")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or set(raw) != {"schema", "bindings"} or raw["schema"] != 1:
                raise ValueError("Esquema no reconocido")
            values = raw["bindings"]
            if not isinstance(values, list) or len(values) > MAX_BINDINGS:
                raise ValueError("Alcance inválido")
            parsed = []
            for value in values:
                if not isinstance(value, dict) or set(value) != {"profile", "notebook"}:
                    raise ValueError("Binding inválido")
                parsed.append(Binding(**value))
            if len(set(parsed)) != len(parsed):
                raise ValueError("Bindings repetidos")
            return tuple(parsed)
        except (OSError, ValueError, TypeError, SecurityError) as exc:
            raise SecurityError("No se puede validar el alcance protegido.") from exc

    def set(self, values: list[Binding] | tuple[Binding, ...], *, verify_profiles: bool = True) -> tuple[Binding, ...]:
        if not 1 <= len(values) <= MAX_BINDINGS or len(set(values)) != len(values):
            raise SecurityError("Seleccione entre 1 y 40 cuadernos distintos.")
        for item in values:
            if not isinstance(item, Binding):
                raise SecurityError("Selección inválida.")
            if verify_profiles:
                self.profiles.load(item.profile)
        ordered = tuple(sorted(values))
        _write_private(self.path, json.dumps({"schema": 1, "bindings": [asdict(x) for x in ordered]},
                                             ensure_ascii=False, indent=2))
        return ordered

    def clear(self) -> None:
        if self.path.is_symlink():
            raise SecurityError("Enlace simbólico no permitido.")
        self.path.unlink(missing_ok=True)

    def require(self, profile: str, notebook: str) -> Binding:
        binding = Binding(profile, notebook)
        if binding not in self.load():
            raise SecurityError("Cuaderno fuera del alcance autorizado. Solo el propietario puede ampliar la selección.")
        return binding

    def active(self) -> tuple[Binding, ...]:
        bindings = self.load()
        if not bindings:
            raise ConfigurationError("No hay cuadernos autorizados. Selecciónelos desde el panel local o CLI.")
        return bindings
