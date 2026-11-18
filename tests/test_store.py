import json
import os

import pytest

from notebook_conexion.errors import ConfigurationError, SecurityError
from notebook_conexion.store import Profile, ProfileStore


@pytest.fixture
def store(tmp_path):
    return ProfileStore(tmp_path / "private")


def test_profiles_isolate(store):
    store.save(Profile("uno", "my-cloud-project", "/fake/client.json"))
    store.save(Profile("dos", "my-cloud-project", "/fake/dos.json"))
    assert store.list_profiles() == ["dos", "uno"]
    assert store.load("uno").client_secrets != store.load("dos").client_secrets
    assert store.load("uno").allow_write is False


def test_does_not_implicitly_migrate(store, tmp_path):
    old = tmp_path / ".notebooklm"
    old.mkdir()
    (old / "storage_state.json").write_text("FAKE-OLD-COOKIE")
    store.save(Profile("personal", "my-cloud-project", "/fake/file"))
    assert "FAKE-OLD-COOKIE" not in store.path("personal").read_text()


def test_write_requires_acknowledgement(store):
    store.save(Profile("personal", "my-cloud-project", "/fake/file"))
    with pytest.raises(SecurityError):
        store.enable_write("personal", True, "wrong")
    assert not store.load("personal").allow_write
    store.enable_write("personal", True, "CONFIRMO-ESCRITURA")
    assert store.load("personal").allow_write
    store.enable_write("personal", False, "")
    assert not store.load("personal").allow_write


def test_permissions_posix(store):
    if os.name == "nt":
        pytest.skip("NTFS ACL handled by OS")
    store.save(Profile("personal", "my-cloud-project", "/fake/file"))
    assert store.path("personal").stat().st_mode & 0o077 == 0
    assert store.path("personal").parent.stat().st_mode & 0o077 == 0


def test_legacy_json_secret_not_in_profile(store):
    profile = Profile("personal", "my-cloud-project", "/fake/file")
    store.save(profile)
    assert set(json.loads(store.path("personal").read_text())) == {"name", "project_id", "client_secrets", "allow_write"}


def test_symlink_profile_rejected(store, tmp_path):
    target = tmp_path / "external.json"
    target.write_text("{}")
    p = store.path("personal")
    p.parent.mkdir(parents=True)
    try:
        p.symlink_to(target)
    except OSError:
        pytest.skip("Symlinks not available")
    with pytest.raises(SecurityError):
        store.load("personal")
    with pytest.raises(SecurityError):
        store.save(Profile("personal", "my-cloud-project", "/fake/file"))
    assert target.read_text() == "{}"


def test_bad_schema_rejected(store):
    p = store.path("personal")
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"name": "personal", "project_id": "my-cloud-project", "client_secrets": "/path", "allow_write": "yes"}))
    with pytest.raises(ConfigurationError):
        store.load("personal")


def test_wrong_identity_rejected(store):
    store.save(Profile("una", "my-cloud-project", "/fake/file"))
    p = store.path("una")
    obj = json.loads(p.read_text())
    obj["name"] = "otra"
    p.write_text(json.dumps(obj))
    with pytest.raises(SecurityError):
        store.load("una")
