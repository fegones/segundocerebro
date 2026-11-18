import json

import httpx
import pytest

from notebook_conexion.errors import PermissionDenied, RemoteServiceError, SecurityError
from notebook_conexion.notebook import NotebookClient
from notebook_conexion.store import Profile
from notebook_conexion.transport import JsonTransport

NOTEBOOK = "notebooks/550e8400-e29b-41d4-a716-446655440000"


def client(monkeypatch, *, writes=False, handler=None):
    monkeypatch.setattr("notebook_conexion.notebook.access_token", lambda *a, **k: "FAKE-SECRET")
    if handler is None:
        def handler(request):
            return httpx.Response(200, json={"notebooks": []})
    transport = JsonTransport(
        "https://notebook.googleapis.com/v1", transport=httpx.MockTransport(handler)
    )
    return NotebookClient(Profile("uno", "my-cloud-project", "/not/needed", writes), transport=transport)


def test_readonly_lists(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"notebooks": []})

    assert client(monkeypatch, handler=handler).notebooks() == {"notebooks": []}
    assert seen[0].url.host == "notebook.googleapis.com"
    assert seen[0].headers["Authorization"] == "Bearer FAKE-SECRET"
    assert seen[0].headers["x-goog-user-project"] == "my-cloud-project"


def test_default_readonly_enforced_before_network(monkeypatch):
    def fail(_):
        raise AssertionError("No network allowed")
    c = client(monkeypatch, writes=False, handler=fail)
    with pytest.raises(PermissionDenied):
        c.create("Lab")
    with pytest.raises(PermissionDenied):
        c.add_text(NOTEBOOK, "Titulo", "Hola")


def test_create_and_update(monkeypatch):
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"name": NOTEBOOK})

    c = client(monkeypatch, writes=True, handler=handler)
    c.create("Cuaderno")
    c.rename(NOTEBOOK, "Renombrado")
    assert seen[0][0:2] == ("POST", "/v1/notebooks")
    assert seen[0][2] == {"display_name": "Cuaderno"}
    assert seen[1][0:2] == ("PATCH", f"/v1/{NOTEBOOK}")


def test_invalid_path_no_network(monkeypatch):
    c = client(monkeypatch, writes=True)
    with pytest.raises(SecurityError):
        c.notebook("../../private")


def test_redirect_not_followed(monkeypatch):
    c = client(monkeypatch, handler=lambda r: httpx.Response(302, headers={"Location": "https://attack.example"}))
    with pytest.raises(RemoteServiceError, match="302"):
        c.notebooks()


def test_no_body_leak(monkeypatch):
    c = client(monkeypatch, handler=lambda r: httpx.Response(403, text="SECRET_INTERNAL_REPLY"))
    with pytest.raises(RemoteServiceError) as e:
        c.notebooks()
    assert "SECRET_INTERNAL_REPLY" not in str(e.value)


def test_large_body_rejected(monkeypatch):
    c = client(monkeypatch, handler=lambda r: httpx.Response(200, content=b"x" * 2_000_001))
    with pytest.raises(RemoteServiceError, match="grande"):
        c.notebooks()


def test_untrusted_http_endpoint_rejected():
    with pytest.raises(ValueError):
        JsonTransport("http://localhost:8080")


def test_http_errors_do_not_include_auth(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("Bearer FAKE-SECRET", request=request)
    c = client(monkeypatch, handler=handler)
    with pytest.raises(RemoteServiceError) as e:
        c.notebooks()
    assert "FAKE-SECRET" not in str(e.value)
