import sys
import types

import pytest

from notebook_conexion.errors import ConfigurationError
from notebook_conexion.secrets import _backend


def test_reject_plaintext_backend(monkeypatch):
    class PlainText:
        priority = 1
    PlainText.__module__ = "keyrings.alt.file"
    fake = types.SimpleNamespace(get_keyring=lambda: PlainText())
    monkeypatch.setitem(sys.modules, "keyring", fake)
    with pytest.raises(ConfigurationError, match="backend nativo"):
        _backend()


def test_accept_native_windows_keyring_class(monkeypatch):
    class Native:
        priority = 2
    Native.__module__ = "keyring.backends.Windows"
    fake = types.SimpleNamespace(get_keyring=lambda: Native())
    monkeypatch.setitem(sys.modules, "keyring", fake)
    assert _backend() is fake


def test_reject_chainer_with_insecure_fallback(monkeypatch):
    class Native:
        priority = 2
    Native.__module__ = "keyring.backends.Windows"
    class Insecure:
        priority = 1
    Insecure.__module__ = "keyrings.alt.file"
    class Chainer:
        backends = [Native(), Insecure()]
    Chainer.__module__ = "keyring.backends.chainer"
    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(get_keyring=lambda: Chainer()))
    with pytest.raises(ConfigurationError):
        _backend()
