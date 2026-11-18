import io
import json
import pytest
from notebook_conexion.errors import PermissionDenied
from notebook_conexion.mcp_server import Settings, TOOLS, execute_tool, handle_message, serve
from notebook_conexion.store import Profile


def test_mcp_no_fastmcp_dependency():
    names = {t["name"] for t in TOOLS}
    assert {"listar_cuadernos", "listar_fuentes", "exportar_catalogo", "generar_archivo_gemini"} <= names


def test_stdio_handshake_and_tools_without_profiles():
    data = b'\n'.join([
        b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}',
        b'{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}',
        b'{"jsonrpc":"2.0","method":"notifications/initialized"}',
    ]) + b'\n'
    out = io.BytesIO()
    serve(Settings(), io.BytesIO(data), out)
    lines = [json.loads(line) for line in out.getvalue().splitlines()]
    assert len(lines) == 2
    assert lines[0]["result"]["serverInfo"]["version"] == "1.3.0"
    assert any(x["name"] == "listar_cuadernos" for x in lines[1]["result"]["tools"])


def test_call_rejects_unexpected_parameters():
    result = handle_message({"jsonrpc":"2.0","id":1,"method":"tools/call",
                             "params":{"name":"listar_cuadernos", "arguments":{"evil":"yes"}}}, Settings())
    assert result["result"]["isError"]


def test_untrusted_names_not_exec():
    result = handle_message({"jsonrpc":"2.0","id":1,"method":"tools/call",
                             "params":{"name":"__import__", "arguments":{}}}, Settings())
    assert result["result"]["isError"]


def test_agent_write_gate(monkeypatch):
    from notebook_conexion import operations
    monkeypatch.setattr("notebook_conexion.store.ProfileStore.load", lambda *_: Profile("personal", "my-cloud-project", "/fake", True))
    monkeypatch.setattr(operations, "NotebookClient", lambda _: object())
    with pytest.raises(PermissionDenied):
        execute_tool("crear_cuaderno", {"titulo":"Prueba"}, Settings())
    monkeypatch.setattr(operations.Operations, "create_notebook", lambda _s, name: {"name": name})
    assert execute_tool("crear_cuaderno", {"titulo":"Prueba"}, Settings(allow_writes=True)) == {"name":"Prueba"}


def test_protocol_invalid_json():
    out = io.BytesIO()
    serve(Settings(), io.BytesIO(b'{bad}\n'), out)
    assert json.loads(out.getvalue())["error"]["code"] == -32700


def test_mcp_errors_no_traceback():
    def fails(*_):
        raise RuntimeError('Bearer SUPER-SECRET-RAW-TOKEN')
    reply = handle_message({"jsonrpc":"2.0", "id":1,"method":"tools/call",
                            "params":{"name":"listar_cuadernos","arguments":{}}}, Settings(), executor=fails)
    s = json.dumps(reply)
    assert "SUPER-SECRET" not in s
    assert "Traceback" not in s
