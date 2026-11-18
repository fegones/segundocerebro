"""Importación local voluntaria. Nunca descarga URL externas ni abre macros."""
from __future__ import annotations

import csv
import io
import json
import uuid
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from .brain_scope import Binding
from .brain_store import BrainStore, Document, MAX_DOCUMENT_BYTES
from .errors import ConfigurationError, SecurityError

MAX_INPUT_BYTES = 15_000_000
EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".json", ".html", ".htm", ".docx", ".pdf"}


class _HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items: list[str] = []
        self.suppress = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "svg"}:
            self.suppress += 1
        if tag in {"p", "div", "li", "h1", "h2", "h3", "br"}:
            self.items.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "svg"} and self.suppress:
            self.suppress -= 1
        if tag in {"p", "div", "li", "h1", "h2", "h3"}:
            self.items.append("\n")

    def handle_data(self, data):
        if not self.suppress:
            self.items.append(data)


def _docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > 150 or sum(i.file_size for i in members) > 40_000_000:
                raise SecurityError("Documento Word excesivamente grande.")
            raw = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError, OSError) as exc:
        raise ConfigurationError("Word inválido o sin texto principal.") from exc
    if len(raw) > 30_000_000 or b"<!DOCTYPE" in raw.upper():
        raise SecurityError("XML de Word no autorizado.")
    root = ElementTree.fromstring(raw)
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    lines: list[str] = []
    for paragraph in root.iter(ns + "p"):
        lines.append("".join(node.text or "" for node in paragraph.iter(ns + "t")))
    return "\n".join(lines)


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ConfigurationError("Para importar PDF instale la dependencia adicional pypdf.") from exc
    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted or len(reader.pages) > 200:
            raise SecurityError("PDF cifrado o con más de 200 páginas: no se importa.")
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
            if sum(len(x) for x in parts) > MAX_DOCUMENT_BYTES:
                raise SecurityError("Texto PDF supera 2 MB.")
        return "\n\n".join(parts)
    except SecurityError:
        raise
    except Exception as exc:
        raise ConfigurationError("PDF inválido o sin texto extraíble.") from exc


def read_file(path: Path) -> str:
    if not isinstance(path, Path) or not path.is_file() or path.is_symlink():
        raise SecurityError("Debe seleccionar un archivo regular sin enlaces simbólicos.")
    if path.suffix.lower() not in EXTENSIONS or path.stat().st_size > MAX_INPUT_BYTES:
        raise SecurityError("Formato o tamaño no admitido para importación documental.")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        result = _pdf_text(path)
    elif suffix == ".docx":
        result = _docx_text(path)
    else:
        try:
            data = path.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError) as exc:
            raise ConfigurationError("Archivo no es texto UTF-8 válido.") from exc
        if suffix in {".htm", ".html"}:
            parser = _HTMLText()
            parser.feed(data)
            result = "".join(parser.items)
        elif suffix == ".json":
            try:
                obj = json.loads(data)
            except ValueError as exc:
                raise ConfigurationError("JSON no válido.") from exc
            result = json.dumps(obj, ensure_ascii=False, indent=2)
        elif suffix == ".csv":
            reader = csv.reader(io.StringIO(data))
            rows = []
            for row in reader:
                if len(rows) >= 20000:
                    raise SecurityError("CSV demasiado extenso.")
                rows.append(" | ".join(row))
            result = "\n".join(rows)
        else:
            result = data
    if not result.strip():
        raise ConfigurationError("No se extrajo texto legible; un PDF escaneado necesita OCR externo.")
    if len(result.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise SecurityError("Texto extraído supera el máximo de 2 MB.")
    return result


def import_file(store: BrainStore, binding: Binding, file: Path, *, title: str = "",
                kind: str = "source", source_id: str = "") -> dict:
    content = read_file(file)
    identifier = source_id or f"local:{uuid.uuid4()}"
    if not identifier.startswith("local:"):
        raise SecurityError("Los archivos importados manualmente deben usar identificador local:*. No se suplantan fuentes remotas.")
    result = store.upsert(Document(binding.profile, binding.notebook, identifier,
                                   title or file.stem, content, kind=kind))
    return {**result, "perfil": binding.profile, "cuaderno": binding.notebook,
            "identificador": identifier, "caracteres": len(content), "origen": "archivo local elegido explícitamente"}
