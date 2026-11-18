import httpx
import pytest

from notebook_conexion.errors import PermissionDenied, RemoteServiceError, SecurityError
from notebook_conexion.gemini import GeminiClient, GEMINI_BASE
from notebook_conexion.store import Profile
from notebook_conexion.transport import JsonTransport


def make_client(monkeypatch, writes, handler):
    monkeypatch.setattr("notebook_conexion.gemini.get_secret", lambda *a: "SECRET-API-KEY")
    return GeminiClient(Profile("personal", "my-cloud-project", "x", writes), transport=JsonTransport(GEMINI_BASE, transport=httpx.MockTransport(handler)))


def test_gemini_policy_blocks(monkeypatch):
    def fail(_):
        raise AssertionError("network")
    c = make_client(monkeypatch, False, fail)
    with pytest.raises(PermissionDenied):
        c.generate("Hola")


def test_gemini_works_with_own_key(monkeypatch):
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Respuesta verificada"}]}}]})
    c = make_client(monkeypatch, True, handler)
    assert c.generate("Hola") == "Respuesta verificada"
    assert seen[0].headers["x-goog-api-key"] == "SECRET-API-KEY"
    assert seen[0].url.host == "generativelanguage.googleapis.com"


def test_gemini_validates_model(monkeypatch):
    c = make_client(monkeypatch, True, lambda _: httpx.Response(200, json={}))
    with pytest.raises(SecurityError):
        c.generate("Hola", model="../../foo")


def test_gemini_no_candidates(monkeypatch):
    c = make_client(monkeypatch, True, lambda _: httpx.Response(200, json={"candidates": []}))
    with pytest.raises(RemoteServiceError):
        c.generate("Hola")
