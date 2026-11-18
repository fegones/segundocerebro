import pytest

from notebook_conexion.errors import SecurityError
from notebook_conexion.validation import (
    display_name, model_name, notebook_name, profile_name,
    public_url, source_name, source_text,
)

NOTEBOOK = "notebooks/550e8400-e29b-41d4-a716-446655440000"
SOURCE = NOTEBOOK + "/sources/770e8400-e29b-41d4-a716-446655440111"


@pytest.mark.parametrize("value", ["", "../../etc", "alpha/beta", "a b", "a" * 41, ".hidden"])
def test_reject_bad_profiles(value):
    with pytest.raises(SecurityError):
        profile_name(value)


def test_accept_profile():
    assert profile_name("personal_2") == "personal_2"


@pytest.mark.parametrize("value", ["notebooks/../../admin", "https://evil/x", "notebooks/foo", "notebooks/550e8400-e29b-41d4-a716-446655440000/extra"])
def test_reject_untrusted_notebook(value):
    with pytest.raises(SecurityError):
        notebook_name(value)


def test_valid_resources():
    assert notebook_name(NOTEBOOK) == NOTEBOOK
    assert source_name(SOURCE) == SOURCE


@pytest.mark.parametrize("value", [
    "http://example.com", "https://127.0.0.1/", "https://localhost/", "https://site.local/x",
    "https://user:secret@example.org/x", "https://example.org:444/x",
    "https://[::1]/", "file:///etc/passwd", "https://example.org\nX", "https://metadata.google.internal/",
])
def test_reject_bad_urls(value):
    with pytest.raises(SecurityError):
        public_url(value)


def test_accept_public_url():
    assert public_url("https://www.youtube.com/watch?v=123") == "https://www.youtube.com/watch?v=123"


def test_limits():
    with pytest.raises(SecurityError):
        source_text("x" * 1_000_001)
    with pytest.raises(SecurityError):
        display_name(" ")
    with pytest.raises(SecurityError):
        display_name("x" * 501)
    with pytest.raises(SecurityError):
        model_name("../admin")
    assert source_text("Hola") == "Hola"
