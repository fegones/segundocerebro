"""Chequeo offline mínimo, invocable antes de conectar cuentas reales."""
from __future__ import annotations
from . import __version__
from .mcp_server import Settings, handle_message
from .validation import display_name, project_id


def main():
    assert __version__ == "1.3.0"
    assert project_id("proyecto-demo-123") == "proyecto-demo-123"
    assert display_name(" Prueba ") == "Prueba"
    for name, expected in [("initialize", "serverInfo"), ("tools/list", "tools")]:
        response = handle_message({"jsonrpc":"2.0", "id":1, "method":name,"params":{}}, Settings())
        assert expected in response["result"]
    print("Diagnóstico local correcto: Notebook Conexión 1.3.0 y MCP stdio listos.")
    print("Para acceder a Google debe configurar OAuth desde el panel.")

if __name__ == "__main__":
    main()
