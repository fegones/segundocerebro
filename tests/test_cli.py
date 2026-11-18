import json

import pytest

from notebook_conexion.cli import execute, parser
from notebook_conexion.errors import ConfigurationError
from notebook_conexion.store import Profile, ProfileStore


def test_cli_parses():
    args = parser().parse_args(["list", "--profile", "personal"])
    assert args.command == "list" and args.profile == "personal"


def test_init_from_user_oauth_file(tmp_path, capsys):
    client_file = tmp_path / "client_secret-personal.json"
    client_file.write_text(json.dumps({"installed": {"client_id": "example-app-id", "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth", "token_uri": "https://oauth2.googleapis.com/token", "redirect_uris": ["http://localhost"]}}))
    store = ProfileStore(tmp_path / "profiles")
    args = parser().parse_args(["init", "--profile", "personal", "--project-id", "my-cloud-project", "--client-secrets", str(client_file)])
    execute(args, store)
    assert store.load("personal").allow_write is False
    assert "created" in capsys.readouterr().out
    with pytest.raises(ConfigurationError):
        execute(args, store)


def test_doctor_has_no_secret(tmp_path, monkeypatch, capsys):
    store = ProfileStore(tmp_path / "profiles")
    f = tmp_path / "oauth.json"
    f.write_text(json.dumps({"installed": {"client_id": "fake", "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth", "token_uri": "https://oauth2.googleapis.com/token", "redirect_uris": ["http://localhost"]}}))
    store.save(Profile("personal", "my-cloud-project", str(f)))
    monkeypatch.setattr("notebook_conexion.secrets._backend", lambda: object())
    execute(parser().parse_args(["doctor"]), store)
    assert "fake" not in capsys.readouterr().out


def test_policy_requires_ack(tmp_path):
    store = ProfileStore(tmp_path / "config")
    store.save(Profile("personal", "my-cloud-project", "/fake"))
    with pytest.raises(Exception):
        execute(parser().parse_args(["policy", "--writes", "on"]), store)
    execute(parser().parse_args(["policy", "--writes", "on", "--ack", "CONFIRMO-ESCRITURA"]), store)
    assert store.load("personal").allow_write
