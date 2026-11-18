import pytest
from notebook_conexion.grants import grant, authorized, revoke
from notebook_conexion.errors import PermissionDenied, SecurityError
from notebook_conexion.store import Profile, ProfileStore


def test_temporal_permission_required_and_revoke(tmp_path, monkeypatch):
    store = ProfileStore(tmp_path/'cfg')
    monkeypatch.setattr('notebook_conexion.grants.ProfileStore', lambda: store)
    store.save(Profile('personal','my-cloud-project','/tmp/oauth.json',True))
    assert not authorized('personal', 'write')
    grant('personal', 'write', minutes=10)
    assert authorized('personal', 'write')
    assert not authorized('personal', 'gemini')
    revoke('personal')
    assert not authorized('personal', 'write')


def test_refuses_disabled_write_and_long_grant(tmp_path, monkeypatch):
    store = ProfileStore(tmp_path/'cfg')
    monkeypatch.setattr('notebook_conexion.grants.ProfileStore', lambda: store)
    store.save(Profile('personal','my-cloud-project','/tmp/oauth.json',False))
    with pytest.raises(PermissionDenied):
        grant('personal','write')
    with pytest.raises(SecurityError):
        grant('personal','write',minutes=31)
