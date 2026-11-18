"""OAuth de escritorio por cuenta. No extrae cookies ni reutiliza sesiones previas."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import ConfigurationError
from .secrets import get_secret, set_secret
from .store import Profile

READ_SCOPE = "https://www.googleapis.com/auth/notebook.readonly"
WRITE_SCOPE = "https://www.googleapis.com/auth/notebook"


def _client_secrets(profile: Profile) -> str:
    file_path = Path(profile.client_secrets).expanduser()
    if not file_path.is_file() or file_path.is_symlink():
        raise ConfigurationError("Archivo OAuth del usuario inexistente o no válido.")
    if file_path.stat().st_size > 64_000:
        raise ConfigurationError("El archivo de configuración OAuth excede el límite.")
    try:
        obj = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError("El archivo OAuth no contiene JSON válido.") from exc
    if not isinstance(obj, dict) or "installed" not in obj:
        raise ConfigurationError("Se requiere un cliente OAuth de tipo Desktop app.")
    installed = obj["installed"]
    if not isinstance(installed, dict) or not installed.get("client_id"):
        raise ConfigurationError("El cliente OAuth no tiene un client_id.")
    if installed.get("auth_uri") not in {
        "https://accounts.google.com/o/oauth2/auth",
        "https://accounts.google.com/o/oauth2/v2/auth",
    }:
        raise ConfigurationError("El endpoint OAuth de autorización no pertenece a Google.")
    if installed.get("token_uri") != "https://oauth2.googleapis.com/token":
        raise ConfigurationError("El endpoint OAuth para tokens no pertenece a Google.")
    allowed_redirects = {"http://localhost", "http://127.0.0.1"}
    redirects = installed.get("redirect_uris")
    if (
        not isinstance(redirects, list)
        or not redirects
        or any(not isinstance(item, str) or item not in allowed_redirects for item in redirects)
    ):
        raise ConfigurationError("El cliente OAuth requiere redirección de loopback de Google.")
    return str(file_path)


def login(profile: Profile, write: bool = False) -> None:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise ConfigurationError("Instale las dependencias de autenticación OAuth.") from exc
    if write and not profile.allow_write:
        raise ConfigurationError("Primero debe habilitar escritura en la política del perfil.")
    scopes = [WRITE_SCOPE if write else READ_SCOPE]
    path = _client_secrets(profile)
    flow = InstalledAppFlow.from_client_secrets_file(path, scopes=scopes)
    try:
        credentials = flow.run_local_server(host="127.0.0.1", port=0, open_browser=True)
    except Exception as exc:
        raise ConfigurationError("No pudo completarse el consentimiento OAuth local.") from exc
    if not credentials.valid or not credentials.refresh_token:
        raise ConfigurationError("No se recibió una sesión renovable. Revise el consentimiento OAuth.")
    # Reemplaza SOLO la credencial de este perfil.
    set_secret(profile.name, "google-oauth", credentials.to_json())


def access_token(profile: Profile, *, needs_write: bool = False) -> str:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise ConfigurationError("Faltan dependencias Google OAuth.") from exc
    raw = get_secret(profile.name, "google-oauth")
    if not raw:
        raise ConfigurationError("Perfil sin cuenta vinculada: ejecute 'login'.")
    try:
        creds = Credentials.from_authorized_user_info(json.loads(raw))
    except (ValueError, TypeError, KeyError) as exc:
        raise ConfigurationError("Credencial inválida. Vuelva a iniciar sesión.") from exc
    # La renovación OAuth jamás debe enviar un refresh_token a otro servidor.
    if creds.token_uri != "https://oauth2.googleapis.com/token":
        raise ConfigurationError("El token fue configurado con un endpoint inesperado.")
    path = _client_secrets(profile)
    client_id_expected = json.loads(Path(path).read_text(encoding="utf-8"))["installed"]["client_id"]
    if creds.client_id != client_id_expected:
        raise ConfigurationError("El token no corresponde al cliente OAuth del perfil.")
    scopes = set(creds.scopes or [])
    if needs_write and (not profile.allow_write or WRITE_SCOPE not in scopes):
        raise ConfigurationError("Acceso de escritura deshabilitado o sin scope OAuth.")
    if not needs_write and not ({READ_SCOPE, WRITE_SCOPE} & scopes):
        raise ConfigurationError("Scope de Notebook no presente.")
    if not creds.valid:
        if not creds.refresh_token:
            raise ConfigurationError("Sesión expirada: vincule nuevamente su cuenta.")
        try:
            creds.refresh(Request())
        except Exception as exc:
            raise ConfigurationError("No se pudo renovar la sesión de Google.") from exc
        set_secret(profile.name, "google-oauth", creds.to_json())
    if not creds.token:
        raise ConfigurationError("El proveedor no emitió un token OAuth válido.")
    return creds.token
