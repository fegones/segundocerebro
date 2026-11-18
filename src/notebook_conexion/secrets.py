"""Persistencia exclusivamente en el almacén seguro del sistema."""

from __future__ import annotations

from .errors import ConfigurationError
from .store import SERVICE_NAME
from .validation import profile_name


def _backend():
    try:
        import keyring

        backend = keyring.get_keyring()
    except Exception as exc:
        raise ConfigurationError("No se encontró un almacén seguro de credenciales.") from exc

    def secure(item) -> bool:
        module = type(item).__module__.lower()
        if module.startswith("keyring.backends.chainer"):
            # Rechazar cualquier fallback que pueda acabar escribiendo texto plano.
            chain = getattr(item, "backends", [])
            return bool(chain) and all(secure(child) for child in chain)
        valid_module = (
            "keyring.backends.windows",  # Windows Credential Manager
            "keyring.backends.macos",    # Apple Keychain
            "keyring.backends.secretservice",  # Linux Secret Service
            "keyring.backends.kwallet",  # Linux KWallet
            "keyring.backends.libsecret",  # Linux libsecret
        )
        return (
            module.startswith(valid_module)
            and getattr(item, "priority", 0) >= 1
        )

    if not secure(backend):
        raise ConfigurationError(
            "El almacén de credenciales no es un backend nativo conocido. "
            "Configure Windows Credential Manager, macOS Keychain o Linux Secret Service."
        )
    return keyring


def _identifier(profile: str, kind: str) -> str:
    profile_name(profile)
    if kind not in {"google-oauth", "gemini-api-key"}:
        raise ConfigurationError("Tipo de secreto desconocido.")
    return f"{profile}/{kind}"


def set_secret(profile: str, kind: str, value: str) -> None:
    if not value or not isinstance(value, str):
        raise ConfigurationError("No se admite un secreto vacío.")
    try:
        _backend().set_password(SERVICE_NAME, _identifier(profile, kind), value)
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError("No fue posible almacenar el secreto localmente.") from exc


def get_secret(profile: str, kind: str) -> str | None:
    try:
        return _backend().get_password(SERVICE_NAME, _identifier(profile, kind))
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError("No fue posible recuperar el secreto local.") from exc


def delete_secret(profile: str, kind: str) -> None:
    key = _identifier(profile, kind)
    try:
        # keyring puede lanzar si la clave no existe; es seguro ignorarlo.
        _backend().delete_password(SERVICE_NAME, key)
    except ConfigurationError:
        raise
    except Exception:
        pass
