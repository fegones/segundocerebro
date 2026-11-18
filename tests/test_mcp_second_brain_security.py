"""Asegura que el modo protegido no pueda sortearse usando herramientas antiguas."""
from __future__ import annotations

import pytest
from notebook_conexion.brain_scope import Binding
from notebook_conexion.mcp_server import Settings, handle_message, execute_tool, PROTECTED_TOOLS

NB = "notebooks/550e8400-e29b-41d4-a716-446655440000"


class FakeScope:
    def load(self):
        return (Binding("segunda", NB),)


def test_strict_mcp_hides_insecure_tools(monkeypatch):
    monkeypatch.setattr("notebook_conexion.brain_scope.ScopeStore", lambda: FakeScope())
    out = handle_message({"jsonrpc":"2.0", "method":"tools/list", "id":2}, Settings())
    names = {t["name"] for t in out["result"]["tools"]}
    assert "buscar_evidencia_segura" in names
    assert "generar_archivo_gemini" not in names
    assert "listar_cuadernos" not in names
    assert names == PROTECTED_TOOLS


@pytest.mark.parametrize("tool,args", [
    ("listar_cuadernos",{}),
    ("buscar_cuadernos",{"texto":"privado"}),
    ("ver_cuaderno",{"cuaderno":NB}),
    ("listar_fuentes",{"cuaderno":NB}),
    ("ver_fuente",{"nombre":NB+"/sources/770e8400-e29b-41d4-a716-446655440000"}),
    ("crear_cuaderno",{"titulo":"Abrir alcance"}),
    ("agregar_fuente_texto",{"cuaderno":NB,"titulo":"Fuente","texto":"valor"}),
    ("generar_texto_gemini",{"instruccion":"datos"}),
    ("exportar_catalogo",{"tipo":"notebooks","archivo":"export", "formato":"json"}),
])
def test_old_tool_denied_under_strict_scope(monkeypatch,tool,args):
    monkeypatch.setattr("notebook_conexion.brain_scope.ScopeStore",lambda:FakeScope())
    with pytest.raises(ValueError,match="MODO ESTRICTO"):
        execute_tool(tool,args,Settings("personal",True,True))


def test_strict_status_without_personal_profile(monkeypatch):
    monkeypatch.setattr("notebook_conexion.brain_scope.ScopeStore",lambda:FakeScope())
    val=execute_tool("estado_notebook_conexion",{},Settings())
    assert val["modo"]=="estricto"
    assert val["cuentas_seleccionadas"]==["segunda"]


def test_schema_rejects_malformed_int():
    out=handle_message({"jsonrpc":"2.0","id":3,"method":"tools/call",
                        "params":{"name":"comparar_versiones_fuente", "arguments":{
                            "perfil":"cuenta1","cuaderno":NB,"fuente":"local:uno",
                            "version_anterior":True,"version_nueva":2}}},Settings())
    assert out["result"]["isError"]


def test_mcp_source_has_no_scope_changing_tool():
    assert not any(k.startswith("activar_") or "alcance_set" in k or "desbloquear" in k
                   for k in PROTECTED_TOOLS)
