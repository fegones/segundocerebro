"""Acciones reutilizables por CLI, MCP y GUI."""
from __future__ import annotations
from .catalog import all_notebooks, all_sources, find_notebooks, resolve_notebook
from .exports import export_generated, export_records
from .notebook import NotebookClient
from .gemini import GeminiClient
from .errors import PermissionDenied, SecurityError
from .store import Profile

class Operations:
    def __init__(self, profile: Profile, *, agent_writes: bool = False, agent_gemini: bool = False):
        self.profile = profile
        self.notebooks = NotebookClient(profile)
        self.agent_writes = agent_writes
        self.agent_gemini = agent_gemini

    def _writes(self):
        from .grants import authorized
        if not self.agent_writes:
            raise PermissionDenied("Cambios desde agentes desactivados. Revise la guía para habilitarlos.")
        if not authorized(self.profile.name, "write"):
            raise PermissionDenied("Abra el panel local y autorice modificaciones MCP por 10 minutos.")

    def list_notebooks(self) -> list[dict]:
        return all_notebooks(self.notebooks)

    def find_notebooks(self, text: str) -> list[dict]:
        return find_notebooks(self.notebooks, text)

    def get_notebook(self, notebook: str) -> dict:
        return self.notebooks.notebook(resolve_notebook(self.notebooks, notebook))

    def list_sources(self, notebook: str) -> list[dict]:
        name = resolve_notebook(self.notebooks, notebook)
        return all_sources(self.notebooks, name)

    def get_source(self, name: str) -> dict:
        return self.notebooks.source(name)

    def create_notebook(self, title: str) -> dict:
        self._writes()
        return self.notebooks.create(title)

    def rename_notebook(self, notebook: str, title: str) -> dict:
        self._writes()
        return self.notebooks.rename(resolve_notebook(self.notebooks, notebook), title)

    def add_url(self, notebook: str, title: str, url: str) -> dict:
        self._writes()
        return self.notebooks.add_url(resolve_notebook(self.notebooks, notebook), title, url)

    def add_text(self, notebook: str, title: str, text: str, markdown: bool = False) -> dict:
        self._writes()
        return self.notebooks.add_text(resolve_notebook(self.notebooks, notebook), title, text, markdown=markdown)

    def export_catalog(self, kind: str, filename: str, fmt: str, notebook: str = "") -> dict:
        if kind not in {"notebooks", "sources"}:
            raise SecurityError("Debe elegir notebooks o sources.")
        if kind == "sources" and not notebook:
            raise SecurityError("Debe seleccionar el cuaderno para exportar fuentes.")
        data = self.list_notebooks() if kind == "notebooks" else self.list_sources(notebook)
        out = export_records(data, stem=filename, fmt=fmt, title="Catálogo: " + kind)
        return {"archivo": str(out), "registros": len(data), "tipo": kind}

    def generate_text(self, prompt: str, model: str = "gemini-3.8-flash") -> dict:
        if not self.agent_gemini:
            raise PermissionDenied("Generación con Gemini desactivada para el agente.")
        from .grants import authorized
        if not authorized(self.profile.name, "gemini"):
            raise PermissionDenied("Abra el panel local y autorice envíos a Gemini API por 10 minutos.")
        return {"texto": GeminiClient(self.profile).generate(prompt, model=model),
                "nota": "Generado por Gemini API; NO es una respuesta fundamentada automáticamente en NotebookLM."}

    def generate_file(self, prompt: str, filename: str, fmt: str = "md", model: str = "gemini-3.8-flash") -> dict:
        if not self.agent_gemini:
            raise PermissionDenied("Generación con Gemini desactivada para el agente.")
        from .grants import authorized
        if not authorized(self.profile.name, "gemini"):
            raise PermissionDenied("Abra el panel local y autorice envíos a Gemini API por 10 minutos.")
        text = GeminiClient(self.profile).generate(prompt, model=model)
        out = export_generated(text, stem=filename, fmt=fmt)
        return {"archivo": str(out), "nota": "Contenido de Gemini API; no equivale a chat con NotebookLM."}
