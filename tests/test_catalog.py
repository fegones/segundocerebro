import pytest
from notebook_conexion.catalog import all_notebooks, find_notebooks, resolve_notebook
from notebook_conexion.errors import ConfigurationError, RemoteServiceError

N1 = 'notebooks/550e8400-e29b-41d4-a716-446655440000'
N2 = 'notebooks/770e8400-e29b-41d4-a716-446655440111'

class Stub:
    def __init__(self):
        self.calls = []
    def notebooks(self, *, page_size, page_token):
        self.calls.append((page_size, page_token))
        if not page_token:
            return {'notebooks': [{'name':N1,'displayName':'Musáceas'}], 'nextPageToken':'next'}
        return {'notebooks':[{'name':N2,'displayName':'Musáceas — producción'}]}


def test_pagination_and_unicode_search():
    c = Stub()
    assert len(all_notebooks(c)) == 2
    assert c.calls == [(100,''),(100,'next')]
    assert find_notebooks(c,'musáceas')[0]['name'] == N1


def test_name_selection_exact_and_ambiguous():
    c = Stub()
    assert resolve_notebook(c,'Musáceas') == N1
    assert resolve_notebook(c,'producción') == N2
    with pytest.raises(ConfigurationError):
        resolve_notebook(c,'Musá')
    with pytest.raises(ConfigurationError):
        resolve_notebook(c,'sin resultados')


def test_reject_cycle_pagination():
    class Cycling:
        def notebooks(self, **_):
            return {'notebooks': [], 'nextPageToken': 'loop'}
    with pytest.raises(RemoteServiceError):
        all_notebooks(Cycling())
