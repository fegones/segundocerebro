import json

import pytest

from notebook_conexion.errors import ConfigurationError
from notebook_conexion.oauth import _client_secrets
from notebook_conexion.store import Profile


def test_malicious_oauth_host_rejected(tmp_path):
    client = tmp_path / "oauth.json"
    client.write_text(json.dumps({"installed": {
        "client_id": "user-client",
        "auth_uri": "https://fake-login.invalid/authorize",
        "token_uri": "https://fake-login.invalid/token",
        "redirect_uris": ["http://localhost"]
    }}))
    with pytest.raises(ConfigurationError):
        _client_secrets(Profile("personal", "my-cloud-project", str(client)))


def test_malicious_callback_rejected(tmp_path):
    client = tmp_path / "oauth.json"
    client.write_text(json.dumps({"installed": {
        "client_id": "user-client",
        "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["https://evil.invalid/callback"]
    }}))
    with pytest.raises(ConfigurationError):
        _client_secrets(Profile("personal", "my-cloud-project", str(client)))


def test_readonly_scope_is_distinct():
    from notebook_conexion.oauth import READ_SCOPE, WRITE_SCOPE
    assert READ_SCOPE != WRITE_SCOPE
