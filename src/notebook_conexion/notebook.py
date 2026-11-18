"""Operaciones oficiales Gemini Notebook v1. Sin APIs privadas."""

from __future__ import annotations

from typing import Any

from .errors import PermissionDenied, SecurityError
from .oauth import access_token
from .store import Profile
from .transport import JsonTransport
from .validation import display_name, notebook_name, public_url, source_name, source_text

API_BASE = "https://notebook.googleapis.com/v1"


class NotebookClient:
    def __init__(self, profile: Profile, *, transport: JsonTransport | None = None):
        self.profile = profile
        self.transport = transport or JsonTransport(API_BASE)

    def _call(
        self,
        method: str,
        path: str,
        *,
        write: bool = False,
        body: dict[str, Any] | None = None,
        params: dict[str, str | int] | None = None,
    ) -> dict[str, Any]:
        if write and not self.profile.allow_write:
            raise PermissionDenied("Escritura bloqueada por política local.")
        token = access_token(self.profile, needs_write=write)
        return self.transport.request(
            method,
            path,
            headers={
                "Authorization": f"Bearer {token}",
                "x-goog-user-project": self.profile.project_id,
                "Content-Type": "application/json",
            },
            payload=body,
            params=params,
        )

    def notebooks(self, *, page_size: int = 50, page_token: str = "") -> dict[str, Any]:
        if not 1 <= page_size <= 100:
            raise SecurityError("page_size debe estar entre 1 y 100.")
        params: dict[str, str | int] = {"pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        return self._call("GET", "/notebooks", params=params)

    def notebook(self, name: str) -> dict[str, Any]:
        return self._call("GET", "/" + notebook_name(name))

    def create(self, title: str) -> dict[str, Any]:
        return self._call(
            "POST", "/notebooks", write=True, body={"display_name": display_name(title)}
        )

    def rename(self, name: str, title: str) -> dict[str, Any]:
        return self._call(
            "PATCH",
            "/" + notebook_name(name),
            write=True,
            params={"updateMask": "displayName"},
            body={"display_name": display_name(title)},
        )

    def sources(self, notebook: str, *, page_size: int = 50, page_token: str = ""):
        if not 1 <= page_size <= 100:
            raise SecurityError("page_size debe estar entre 1 y 100.")
        params: dict[str, str | int] = {"pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        return self._call(
            "GET", "/" + notebook_name(notebook) + "/sources", params=params
        )

    def source(self, name: str) -> dict[str, Any]:
        return self._call("GET", "/" + source_name(name))

    def add_url(self, notebook: str, title: str, url: str) -> dict[str, Any]:
        return self._call(
            "POST",
            "/" + notebook_name(notebook) + "/sources",
            write=True,
            body={"display_name": display_name(title), "web_content": {"url": public_url(url)}},
        )

    def add_text(
        self, notebook: str, title: str, content: str, *, markdown: bool = False
    ) -> dict[str, Any]:
        return self._call(
            "POST",
            "/" + notebook_name(notebook) + "/sources",
            write=True,
            body={
                "display_name": display_name(title),
                "mime_type": "text/markdown" if markdown else "text/plain",
                "text_content": {"content": source_text(content)},
            },
        )
