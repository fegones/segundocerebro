import notebook_conexion.agent_install as agent


def test_skill_is_bundled():
    data = agent.skill_contents()
    assert data.startswith('---')
    assert 'name: notebook-conexion' in data
    assert 'No inventes' in data


def test_agent_cmd_does_not_embed_tokens(monkeypatch):
    monkeypatch.setattr(agent.shutil, 'which', lambda name: '/program/' + name)
    _, add = agent.commands('claude', profile='personal', allow_writes=True)
    assert '--allow-writes' in add
    assert any('notebook_conexion.mcp_server' == s for s in add)
    assert all('token' not in s.lower() and 'secret' not in s.lower() for s in add)
    _, add2 = agent.commands('codex')
    assert 'mcp' in add2 and 'add' in add2
