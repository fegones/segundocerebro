"""Operaciones de catálogo. La selección por nombre nunca elige coincidencias ambiguas."""
from __future__ import annotations
from .notebook import NotebookClient
from .errors import ConfigurationError, RemoteServiceError, SecurityError

MAX_PAGES = 20


def _collect(client: NotebookClient, kind: str, notebook: str = "") -> list[dict]:
    result = []
    token = ""
    seen = set()
    for _ in range(MAX_PAGES):
        page = client.notebooks(page_size=100, page_token=token) if kind == "notebooks" else client.sources(notebook, page_size=100, page_token=token)
        records = page.get(kind, [])
        if not isinstance(records, list):
            raise RemoteServiceError("La API devolvió un catálogo inesperado.")
        result.extend(record for record in records if isinstance(record, dict))
        token = page.get("nextPageToken", "")
        if not isinstance(token, str):
            raise RemoteServiceError("Token de paginación inválido.")
        if not token:
            return result
        if token in seen:
            raise RemoteServiceError("La API repitió un token de paginación.")
        seen.add(token)
    raise RemoteServiceError("Demasiadas páginas; no se entrega un listado incompleto como completo.")


def all_notebooks(client: NotebookClient) -> list[dict]:
    return _collect(client, "notebooks")


def all_sources(client: NotebookClient, notebook: str) -> list[dict]:
    return _collect(client, "sources", notebook)


def find_notebooks(client: NotebookClient, term: str) -> list[dict]:
    if not isinstance(term, str) or not 1 <= len(term.strip()) <= 200:
        raise SecurityError("Búsqueda inválida (1-200 caracteres).")
    query = term.strip().casefold()
    records = all_notebooks(client)
    exact = [n for n in records if (n.get("displayName") or n.get("display_name") or "").casefold() == query]
    if exact:
        return exact
    return [n for n in records if query in (n.get("displayName") or n.get("display_name") or "").casefold()]


def resolve_notebook(client: NotebookClient, value: str) -> str:
    from .validation import notebook_name
    if isinstance(value, str) and value.startswith("notebooks/"):
        return notebook_name(value)
    matches = find_notebooks(client, value)
    if len(matches) != 1:
        names = [f"{n.get('displayName', '?')} ({n.get('name', '?')})" for n in matches[:8]]
        raise ConfigurationError(
            "No se pudo identificar un cuaderno único: "
            + ("sin coincidencias" if not matches else "varias coincidencias")
            + (". Opciones: " + "; ".join(names) if names else "")
        )
    return notebook_name(matches[0]["name"])
