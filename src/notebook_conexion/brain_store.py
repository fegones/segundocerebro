"""Repositorio local: metadatos SQLite y contenido cifrado AES-256-GCM.

Cada registro se separa mediante (perfil, cuaderno, fuente), sin contraseñas ni
cookies en la base. Los fragmentos solo se descifran tras validar un alcance.
"""
from __future__ import annotations

from contextlib import contextmanager
import base64
import hashlib
import os
import re
import secrets as random_secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from platformdirs import user_data_path

from .brain_scope import Binding
from .errors import ConfigurationError, SecurityError
from .store import _ensure_secure_directory, SERVICE_NAME
from .validation import notebook_name, profile_name

MAX_DOCUMENT_BYTES = 2_000_000
MAX_RECORDS = 15000
MAX_QUERY_CONTENT = 25_000_000


def _key_from_os() -> bytes:
    from .secrets import _backend
    keyring = _backend()  # falla cerrado si solo hay backend en texto plano
    service = SERVICE_NAME + "-second-brain"
    name = "local-encryption-key"
    saved = keyring.get_password(service, name)
    if saved is None:
        candidate = random_secrets.token_bytes(32)
        keyring.set_password(service, name, base64.b64encode(candidate).decode("ascii"))
        saved = keyring.get_password(service, name)
        if saved is None:
            raise ConfigurationError("El almacén seguro del equipo no conservó la clave.")
    try:
        result = base64.b64decode(saved, validate=True)
    except (ValueError, TypeError) as exc:
        raise SecurityError("La clave local de cifrado es inválida.") from exc
    if len(result) != 32:
        raise SecurityError("Longitud de la clave local inválida.")
    return result


def _cipher(key: bytes):
    if not isinstance(key, bytes) or len(key) != 32:
        raise SecurityError("Se requiere una clave AES-256 válida.")
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM(key)


@dataclass(frozen=True)
class Document:
    profile: str
    notebook: str
    source_id: str
    title: str
    content: str
    kind: str = "source"
    url: str = ""

    def __post_init__(self):
        profile_name(self.profile)
        notebook_name(self.notebook)
        if not isinstance(self.source_id, str) or not (1 <= len(self.source_id) <= 250):
            raise SecurityError("Identificador de fuente inválido.")
        if self.source_id.startswith("local:"):
            if not re.fullmatch(r"local:[A-Za-z0-9_-]{1,80}", self.source_id):
                raise SecurityError("Identificador de fuente local inválido.")
        else:
            from .validation import source_name
            source_name(self.source_id)
            if not self.source_id.startswith(self.notebook + "/sources/"):
                raise SecurityError("Identificador de fuente externo a este cuaderno.")
        if not isinstance(self.title, str) or not 1 <= len(self.title.strip()) <= 500:
            raise SecurityError("Título inválido.")
        if self.kind not in {"source", "chat_export", "note_export", "artifact_export"}:
            raise SecurityError("Tipo de evidencia no admitido.")
        if not isinstance(self.content, str) or not self.content.strip() or len(self.content.encode("utf-8")) > MAX_DOCUMENT_BYTES:
            raise SecurityError("Contenido vacío o superior a 2 MB.")
        if not isinstance(self.url, str) or len(self.url) > 2048:
            raise SecurityError("URL no válida.")


class BrainStore:
    def __init__(self, path: Path | None = None, *, key: bytes | None = None):
        self.path = Path(path) if path is not None else Path(user_data_path("NotebookConexion", "IdeasInnovadoras")) / "second_brain" / "index.sqlite3"
        if self.path.is_symlink():
            raise SecurityError("Base de datos bajo enlace simbólico no permitida.")
        _ensure_secure_directory(self.path.parent)
        if not self.path.exists():
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
            try:
                fd = os.open(self.path, flags, 0o600)
                os.close(fd)
            except FileExistsError:
                pass
        if self.path.is_symlink():
            raise SecurityError("La base cambió a un enlace simbólico.")
        if os.name != "nt":
            self.path.chmod(0o600)
        self.key = key  # se solicita al almacén del SO solamente para leer/escribir contenidos
        with self._db() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS notebooks (
                    profile TEXT NOT NULL, notebook TEXT NOT NULL, title TEXT NOT NULL,
                    snapshot_time REAL NOT NULL, PRIMARY KEY(profile, notebook));
                CREATE TABLE IF NOT EXISTS source_catalog (
                    profile TEXT NOT NULL, notebook TEXT NOT NULL, source_id TEXT NOT NULL,
                    title TEXT NOT NULL, original_url TEXT NOT NULL DEFAULT '',
                    mime TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT '',
                    snapshot_time REAL NOT NULL,
                    PRIMARY KEY(profile, notebook, source_id));
                CREATE TABLE IF NOT EXISTS documents (
                    profile TEXT NOT NULL, notebook TEXT NOT NULL, source_id TEXT NOT NULL,
                    title TEXT NOT NULL, original_url TEXT NOT NULL DEFAULT '',
                    kind TEXT NOT NULL, version INTEGER NOT NULL,
                    sha256 TEXT NOT NULL, nonce BLOB NOT NULL, ciphertext BLOB NOT NULL,
                    updated_time REAL NOT NULL,
                    PRIMARY KEY(profile, notebook, source_id));
                CREATE TABLE IF NOT EXISTS document_history (
                    profile TEXT NOT NULL, notebook TEXT NOT NULL, source_id TEXT NOT NULL,
                    version INTEGER NOT NULL, sha256 TEXT NOT NULL,
                    nonce BLOB NOT NULL, ciphertext BLOB NOT NULL, archived_time REAL NOT NULL,
                    PRIMARY KEY(profile, notebook, source_id, version));
                CREATE INDEX IF NOT EXISTS idx_catalog_notebook ON source_catalog(profile, notebook);
                CREATE INDEX IF NOT EXISTS idx_document_notebook ON documents(profile, notebook);
            """)

    @contextmanager
    def _db(self):
        con = sqlite3.connect(self.path, timeout=10.0)
        try:
            con.execute("PRAGMA busy_timeout=10000")
            con.execute("PRAGMA trusted_schema=OFF")
            con.execute("PRAGMA secure_delete=ON")
            with con:
                yield con
        finally:
            con.close()

    def _aes(self):
        return _cipher(self.key if self.key is not None else _key_from_os())

    @staticmethod
    def _associated(profile: str, notebook: str, source: str, version: int) -> bytes:
        return f"notebook-conexion-v1.3|{profile}|{notebook}|{source}|{version}".encode("utf-8")

    def _encrypt(self, content: str, binding: Binding, source: str, version: int) -> tuple[bytes, bytes]:
        nonce = random_secrets.token_bytes(12)
        return nonce, self._aes().encrypt(nonce, content.encode("utf-8"),
                                          self._associated(binding.profile, binding.notebook, source, version))

    def _decrypt(self, row: sqlite3.Row) -> str:
        try:
            return self._aes().decrypt(row["nonce"], row["ciphertext"],
                self._associated(row["profile"], row["notebook"], row["source_id"], row["version"])).decode("utf-8")
        except Exception as exc:
            raise SecurityError("No fue posible descifrar un documento; no se ignora la falla.") from exc

    def save_catalog(self, binding: Binding, title: str, sources: list[dict]) -> dict:
        if len(sources) > 5000 or not isinstance(title, str) or len(title) > 500:
            raise SecurityError("Catálogo demasiado extenso.")
        rows = []
        for src in sources:
            if not isinstance(src, dict):
                raise SecurityError("Fuente remota con estructura inesperada.")
            sid = src.get("name")
            if not isinstance(sid, str) or not sid.startswith(binding.notebook + "/sources/") or len(sid) > 250:
                raise SecurityError("Fuente de otro cuaderno o identificador inválido.")
            rows.append((binding.profile, binding.notebook, sid, str(src.get("displayName", ""))[:500],
                         str(src.get("originalUrl", ""))[:2048], str(src.get("mimeType", ""))[:120],
                         str(src.get("state", ""))[:60], time.time()))
        if len({x[2] for x in rows}) != len(rows):
            raise SecurityError("Catálogo contiene IDs duplicados.")
        with self._db() as db:
            db.execute("INSERT OR REPLACE INTO notebooks VALUES (?,?,?,?)", (binding.profile, binding.notebook, title, time.time()))
            db.execute("DELETE FROM source_catalog WHERE profile=? AND notebook=?", (binding.profile, binding.notebook))
            db.executemany("INSERT INTO source_catalog VALUES (?,?,?,?,?,?,?,?)", rows)
        return {"cuaderno": binding.key, "fuentes": len(rows), "tipo": "metadatos"}

    def upsert(self, doc: Document) -> dict:
        binding = Binding(doc.profile, doc.notebook)
        digest = hashlib.sha256(doc.content.encode("utf-8")).hexdigest()
        with self._db() as db:
            count = db.execute("SELECT count(*) FROM documents").fetchone()[0]
            old = db.execute("SELECT version,sha256,nonce,ciphertext FROM documents WHERE profile=? AND notebook=? AND source_id=?",
                 (doc.profile, doc.notebook, doc.source_id)).fetchone()
            if old is None and count >= MAX_RECORDS:
                raise SecurityError("Número máximo de documentos alcanzado.")
            if old and old[1] == digest:
                return {"estado": "sin_cambios", "sha256": digest, "version": old[0]}
            version = (old[0] + 1) if old else 1
            nonce, ciphertext = self._encrypt(doc.content, binding, doc.source_id, version)
            if old:
                db.execute("INSERT INTO document_history VALUES (?,?,?,?,?,?,?,?)",
                    (doc.profile, doc.notebook, doc.source_id, old[0], old[1], old[2], old[3], time.time()))
            db.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (doc.profile, doc.notebook, doc.source_id, doc.title, doc.url, doc.kind, version, digest,
                 nonce, ciphertext, time.time()))
        return {"estado": "actualizado" if old else "agregado", "sha256": digest, "version": version}

    def list_catalog(self, bindings: Sequence[Binding]) -> list[dict]:
        if not bindings:
            raise SecurityError("La selección de cuadernos no puede estar vacía.")
        result = []
        with self._db() as db:
            db.row_factory = sqlite3.Row
            for binding in bindings:
                result.extend(dict(x) for x in db.execute(
                    "SELECT profile,notebook,source_id,title,original_url,mime,state,snapshot_time FROM source_catalog WHERE profile=? AND notebook=? ORDER BY title",
                    (binding.profile, binding.notebook)))
        return result

    def list_notebooks(self, bindings: Sequence[Binding]) -> list[dict]:
        result = []
        with self._db() as db:
            db.row_factory = sqlite3.Row
            for binding in bindings:
                row = db.execute("SELECT * FROM notebooks WHERE profile=? AND notebook=?",
                                 (binding.profile, binding.notebook)).fetchone()
                result.append(dict(row) if row else {"profile": binding.profile, "notebook": binding.notebook,
                                                      "title": "(sin sincronizar)", "snapshot_time": None})
        return result

    def list_documents(self, bindings: Sequence[Binding], *, include_content: bool = False) -> list[dict]:
        if not bindings:
            raise SecurityError("Sin cuadernos autorizados.")
        result = []
        total_content = 0
        with self._db() as db:
            db.row_factory = sqlite3.Row
            for binding in bindings:
                rows = db.execute("SELECT * FROM documents WHERE profile=? AND notebook=? ORDER BY title",
                                (binding.profile, binding.notebook))
                for row in rows:
                    record = {k: row[k] for k in ("profile", "notebook", "source_id", "title", "original_url",
                                                    "kind", "version", "sha256", "updated_time")}
                    if include_content:
                        total_content += len(row["ciphertext"])
                        if total_content > MAX_QUERY_CONTENT:
                            raise SecurityError("Hay más de 25 MB de texto en el alcance. Divida la selección de cuadernos para consultas y auditorías.")
                        record["content"] = self._decrypt(row)
                    result.append(record)
        return result

    def versions(self, binding: Binding, source_id: str) -> list[dict]:
        if not isinstance(source_id, str) or not 1 <= len(source_id) <= 250:
            raise SecurityError("Identificador de fuente incorrecto.")
        result = []
        with self._db() as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM document_history WHERE profile=? AND notebook=? AND source_id=? UNION ALL SELECT profile,notebook,source_id,version,sha256,nonce,ciphertext,updated_time AS archived_time FROM documents WHERE profile=? AND notebook=? AND source_id=? ORDER BY version",
                   (binding.profile, binding.notebook, source_id, binding.profile, binding.notebook, source_id))
            for row in rows:
                result.append({"version": row["version"], "sha256": row["sha256"], "content": self._decrypt(row)})
        return result
