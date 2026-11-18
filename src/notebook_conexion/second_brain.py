"""Capa de orquestación multi-cuenta: la selección se valida en cada llamada."""
from __future__ import annotations

from pathlib import Path

from .brain_audit import audit_notebooks, audit_sources, compare_versions, compare_documents
from .brain_import import import_file
from .brain_retrieval import answer_extractive, retrieve
from .brain_scope import Binding, ScopeStore
from .brain_store import BrainStore, Document
from .catalog import all_sources
from .errors import SecurityError
from .notebook import NotebookClient
from .store import ProfileStore


class SecondBrain:
    def __init__(self, scope: ScopeStore | None = None, store: BrainStore | None = None,
                 profiles: ProfileStore | None = None, *, client_factory=None):
        self.profiles = profiles or ProfileStore()
        self.scope = scope or ScopeStore(profiles=self.profiles)
        self.store = store or BrainStore()
        self.client_factory = client_factory or (lambda profile: NotebookClient(profile))

    def active(self) -> tuple[Binding, ...]:
        bindings = self.scope.active()
        for item in bindings:
            self.profiles.load(item.profile)
        return bindings

    def status(self) -> dict:
        bindings = self.scope.load()
        return {"modo": "estricto" if bindings else "sin_alcance", "cuadernos_autorizados":
                [{"perfil": x.profile, "cuaderno": x.notebook} for x in bindings],
                "cuadernos_sincronizados": self.store.list_notebooks(bindings) if bindings else [],
                "aviso": "El alcance MCP no restringe otras herramientas externas de Claude/Codex."
                " Las fuentes remotas sin texto no están automáticamente disponibles para responder."}

    def catalog(self) -> dict:
        bindings = self.active()
        return {"cuadernos": self.store.list_notebooks(bindings),
                "fuentes": self.store.list_catalog(bindings)}

    def documents(self) -> dict:
        values = self.store.list_documents(self.active())
        return {"documentos": values, "total": len(values), "contenido": "cifrado_local_no_incluido"}

    def sync(self, *, include_text: bool = False) -> dict:
        bindings = self.active()
        results = []
        for binding in bindings:
            profile = self.profiles.load(binding.profile)
            client = self.client_factory(profile)
            notebook = client.notebook(binding.notebook)  # Se evita listar otros cuadernos.
            if notebook.get("name") != binding.notebook:
                raise SecurityError("Respuesta del proveedor no coincide con el cuaderno autorizado.")
            sources = all_sources(client, binding.notebook)
            results.append(self.store.save_catalog(binding, str(notebook.get("displayName", ""))[:500], sources))
            imported = 0
            unavailable = 0
            if include_text:
                if len(sources) > 300:
                    raise SecurityError("Para recuperar texto, sincronice cuadernos con máximo 300 fuentes.")
                for src in sources:
                    name = src.get("name", "")
                    if not isinstance(name, str) or not name.startswith(binding.notebook + "/sources/"):
                        raise SecurityError("La fuente no pertenece al cuaderno autorizado.")
                    detail = client.source(name)
                    if detail.get("name") != name:
                        raise SecurityError("GetSource devolvió un identificador distinto del solicitado.")
                    spec = detail.get("textContent") or detail.get("text_content") or {}
                    content = spec.get("content", "") if isinstance(spec, dict) else ""
                    if not isinstance(content, str) or not content.strip():
                        unavailable += 1
                        continue
                    self.store.upsert(Document(binding.profile, binding.notebook, name,
                        str(detail.get("displayName", "Documento de texto"))[:500], content,
                        url=str(detail.get("originalUrl", ""))[:2048]))
                    imported += 1
            results[-1].update({"textos_obtenidos": imported, "sin_texto_recuperable": unavailable,
                                "nota": "GetSource no garantiza entregar el texto completo de URL, PDFs ni recursos."})
        return {"resultado": results, "cuadernos_sincronizados": len(results),
                "modo": "solo_cuadernos_autorizados"}

    def import_local(self, binding: Binding, file: Path, *, title: str = "",
                     kind: str = "source", source_id: str = "") -> dict:
        self.scope.require(binding.profile, binding.notebook)
        return import_file(self.store, binding, file, title=title, kind=kind, source_id=source_id)

    def audit_sources(self, *, similarity: bool = True) -> dict:
        return audit_sources(self.store, self.active(), similarity=similarity)

    def audit_notebooks(self) -> dict:
        return audit_notebooks(self.store, self.active())

    def compare(self, binding: Binding, source_id: str, version_a: int, version_b: int) -> dict:
        self.scope.require(binding.profile, binding.notebook)
        return compare_versions(self.store, binding, source_id, version_a, version_b)

    def compare_documents(self, left: Binding, source_left: str, right: Binding, source_right: str) -> dict:
        return compare_documents(self.store, self.active(), left, source_left, right, source_right)

    def evidence(self, question: str) -> dict:
        return retrieve(self.store, self.active(), question)

    def answer(self, question: str, *, mode: str = "extractive", allow_gemini: bool = False,
               model: str = "gemini-3.8-flash") -> dict:
        bindings = self.active()
        if mode == "extractive":
            return answer_extractive(self.store, bindings, question)
        if mode != "gemini" or not allow_gemini:
            raise SecurityError("Modo generativo no permitido. Se necesita autorización temporal de Gemini.")
        from .brain_answers import answer_with_gemini
        return answer_with_gemini(self.store, bindings, question, model=model)
