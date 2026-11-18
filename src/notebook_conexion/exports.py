"""Exportación local con alcance limitado y sin rutas suministradas por agentes."""
from __future__ import annotations
import csv
import io
import json
import os
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape
from platformdirs import user_documents_path
from .errors import SecurityError

_SAFE_NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,70}\Z")
FORMATS = {"csv", "json", "md", "txt", "docx"}


def export_directory() -> Path:
    return Path(user_documents_path()) / "Notebook Conexion" / "Exportaciones"


def _safe_directory(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink():
            raise SecurityError("No se permite exportar mediante enlaces simbólicos.")
    path.mkdir(parents=True, exist_ok=True)


def _safe_csv_cell(value: object) -> str:
    text = str(value if value is not None else "")
    if text.lstrip().startswith(("=", "+", "-", "@")) or text[:1] in ("\t", "\r", "\n"):
        return "'" + text
    return text


def _as_csv(records: list[dict]) -> bytes:
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    columns = ["name", "displayName", "state", "mimeType", "createTime", "originalUrl"]
    writer.writerow(columns)
    for item in records:
        writer.writerow([_safe_csv_cell(item.get(k, "")) for k in columns])
    return out.getvalue().encode("utf-8-sig")


def _as_markdown(records: list[dict], title: str) -> str:
    rows = ["# " + title, "", "| Nombre | ID | Estado |", "|---|---|---|"]
    for x in records:
        def esc(v: object) -> str:
            return str(v or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ")
        rows.append("| " + " | ".join([esc(x.get("displayName")), esc(x.get("name")), esc(x.get("state"))]) + " |")
    rows.append("")
    return "\n".join(rows)


def _docx(contents: str) -> bytes:
    if len(contents.encode("utf-8")) > 300_000:
        raise SecurityError("Contenido demasiado extenso para Word.")
    paragraphs = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{escape(line)}</w:t></w:r></w:p>'
        for line in contents.splitlines()
    )
    if not paragraphs:
        paragraphs = "<w:p/>"
    doc = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' \
          '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' \
          '<w:body>' + paragraphs + '</w:body></w:document>'
    buf = io.BytesIO()
    with ZipFile(buf, "w", compression=ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
        z.writestr('word/document.xml', doc)
    return buf.getvalue()


def save_export(stem: str, fmt: str, content: str | bytes, *, base: Path | None = None) -> Path:
    if not _SAFE_NAME.fullmatch(stem):
        raise SecurityError("Nombre de archivo inseguro: use letras, números, guiones o _. ")
    if fmt not in FORMATS:
        raise SecurityError("Formato de salida no permitido.")
    directory = base if base is not None else export_directory()
    _safe_directory(directory)
    data = content.encode("utf-8") if isinstance(content, str) else content
    if len(data) > 3_000_000:
        raise SecurityError("Exportación excede el máximo local de 3 MB.")
    # Política de no sobreescritura. Nombres consecutivos y no dependientes de rutas de agente.
    dest = directory / f"{stem}.{fmt}"
    num = 2
    while dest.exists() or dest.is_symlink():
        if num > 5000:
            raise SecurityError("Demasiados archivos con el mismo nombre.")
        dest = directory / f"{stem}_{num}.{fmt}"
        num += 1
    # O_EXCL impide sobrescritura incluso ante carreras; cero ruta arbitraria del agente.
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    fd = os.open(dest, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as fp:
            fp.write(data)
            fp.flush()
            os.fsync(fp.fileno())
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    return dest


def export_records(records: list[dict], *, stem: str, fmt: str, title: str, base: Path | None = None) -> Path:
    if fmt == "csv":
        data = _as_csv(records)
    elif fmt == "json":
        data = (json.dumps(records, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    elif fmt in {"md", "txt", "docx"}:
        content = _as_markdown(records, title)
        data = _docx(content) if fmt == "docx" else content.encode("utf-8")
    else:
        raise SecurityError("Formato no disponible.")
    return save_export(stem, fmt, data, base=base)


def export_generated(text: str, *, stem: str, fmt: str, base: Path | None = None) -> Path:
    if not isinstance(text, str) or len(text.encode("utf-8")) > 300_000:
        raise SecurityError("Resultado de Gemini demasiado largo.")
    if fmt not in {"md", "txt", "docx"}:
        raise SecurityError("Generación admite Markdown, texto y Word (docx).")
    return save_export(stem, fmt, _docx(text) if fmt == "docx" else text, base=base)
