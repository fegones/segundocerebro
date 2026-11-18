"""Detección transparente: coincidencia exacta, URL y similitud aproximada.

Los títulos solos nunca se presentan como prueba de identidad documental.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from collections import defaultdict
from itertools import combinations, islice
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .brain_scope import Binding
from .brain_store import BrainStore
from .errors import SecurityError

TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def normalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return ""
        params = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                  if not k.lower().startswith("utm_") and k.lower() not in TRACKING_KEYS]
        path = parsed.path.rstrip("/") or "/"
        # Evitar descartar parámetros de negocio; solamente se eliminan parámetros de rastreo habituales.
        host = parsed.hostname.lower()
        if parsed.port and parsed.port != (443 if parsed.scheme == "https" else 80):
            host += ":" + str(parsed.port)
        return urlunsplit((parsed.scheme.lower(), host, path, urlencode(sorted(params)), ""))
    except ValueError:
        return ""


def _document_key(row: dict) -> tuple[str, str, str]:
    return row["profile"], row["notebook"], row["source_id"]


def _entry(row: dict) -> dict:
    return {k: row.get(k, "") for k in ("profile", "notebook", "source_id", "title", "original_url")}


def _shingles(text: str, n: int = 5) -> set[str]:
    tokens = normalize_text(text).split()[:6000]
    return {" ".join(tokens[i:i+n]) for i in range(max(0, len(tokens) - n + 1))}


def audit_sources(store: BrainStore, bindings: tuple[Binding, ...], *, similarity: bool = True) -> dict:
    if not bindings:
        raise SecurityError("Seleccione al menos un cuaderno.")
    catalog = store.list_catalog(bindings)
    docs = store.list_documents(bindings, include_content=similarity)
    by_key = {_document_key(row): row for row in docs}
    records: dict[tuple[str, str, str], dict] = {}
    for row in catalog + docs:
        key = _document_key(row)
        if key not in records:
            records[key] = _entry(row)
        if key in by_key:
            records[key]["sha256"] = by_key[key]["sha256"]
    groups: list[dict] = []
    seen: set[tuple[str, tuple]] = set()
    indexes: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
    for key, row in records.items():
        if row.get("sha256"):
            indexes[("hash", row["sha256"])].append(key)
        url = normalize_url(row.get("original_url", ""))
        if url:
            indexes[("url", url)].append(key)
        title = normalize_text(row["title"])
        if title and len(title) >= 6:
            indexes[("title", title)].append(key)
    for (kind, value), keys in indexes.items():
        if len(keys) < 2:
            continue
        signature = (kind, tuple(sorted(keys)))
        if signature in seen:
            continue
        seen.add(signature)
        groups.append({"criterio": kind, "confianza": "exacta" if kind == "hash" else
                       "alta_por_url" if kind == "url" else "baja_por_titulo",
                       "valor": value[:160], "fuentes": [records[k] for k in sorted(keys)]})
    if similarity:
        eligible = [r for r in docs if len(r["content"].split()) >= 20]
        if len(eligible) <= 120:
            fingerprints = { _document_key(x): _shingles(x["content"]) for x in eligible }
            for left, right in combinations(eligible, 2):
                a, b = fingerprints[_document_key(left)], fingerprints[_document_key(right)]
                if not a or not b or left["sha256"] == right["sha256"]:
                    continue
                ratio = len(a & b) / len(a | b)
                if ratio >= .80:
                    groups.append({"criterio": "contenido_similar", "confianza": "probable_no_equivalencia_certificada",
                                   "similitud_jaccard_5_gramas": round(ratio, 3),
                                   "fuentes": [_entry(left), _entry(right)]})
        else:
            groups.append({"criterio": "limite_analisis", "nota": "Más de 120 documentos: se omitió comparación O(n²)."})
    return {"cuadernos_examinados": len(bindings), "fuentes_distintas": len(records),
            "documentos_indexados": len(docs), "grupos": groups,
            "advertencia": "Un título o una URL coincidente no comprueban que dos archivos tengan igual contenido."}


def audit_notebooks(store: BrainStore, bindings: tuple[Binding, ...]) -> dict:
    info = store.list_notebooks(bindings)
    sources = store.list_catalog(bindings)
    docs = store.list_documents(bindings)
    mapping: dict[tuple[str, str], set[str]] = defaultdict(set)
    for x in sources:
        identity = normalize_url(x["original_url"]) or "title:" + normalize_text(x["title"])
        if identity != "title:":
            mapping[(x["profile"], x["notebook"])].add(identity)
    for x in docs:
        mapping[(x["profile"], x["notebook"])].add("sha256:" + x["sha256"])
    matches = []
    for a, b in combinations(info, 2):
        ident_a = (a["profile"], a["notebook"])
        ident_b = (b["profile"], b["notebook"])
        title_equal = normalize_text(a["title"]) == normalize_text(b["title"]) and a["title"] != "(sin sincronizar)"
        left, right = mapping[ident_a], mapping[ident_b]
        intersection = len(left & right)
        union = len(left | right)
        overlap = intersection / union if union else 0
        if title_equal or (intersection >= 2 and overlap >= .65):
            matches.append({"cuadernos": [a, b], "titulo_coincidente": title_equal,
                            "fuentes_compartidas_por_indicio": intersection,
                            "superposicion_jaccard": round(overlap, 3),
                            "clasificacion": "posibles_duplicados_no_confirmados"})
    return {"cuadernos": len(info), "coincidencias": matches,
            "nota": "La coincidencia de título o fuentes no prueba igualdad completa de cuadernos."}


def compare_versions(store: BrainStore, binding: Binding, source_id: str, old: int, new: int) -> dict:
    rows = store.versions(binding, source_id)
    values = {r["version"]: r for r in rows}
    if old not in values or new not in values or old >= new:
        raise SecurityError("Seleccione dos versiones existentes en orden ascendente.")
    a, b = values[old], values[new]
    lines_a = [x[:1500] for x in a["content"].splitlines()[:3000]]
    lines_b = [x[:1500] for x in b["content"].splitlines()[:3000]]
    diff = list(islice(difflib.unified_diff(lines_a, lines_b,
                        fromfile=f"v{old}", tofile=f"v{new}", lineterm=""), 121))
    return {"cuaderno": binding.key, "fuente": source_id, "versiones": [old, new],
            "hashes_sha256": [a["sha256"], b["sha256"]],
            "identicos": a["sha256"] == b["sha256"],
            "diferencias": diff[:120], "truncado": len(diff) > 120}


def compare_documents(store: BrainStore, bindings: tuple[Binding, ...],
                      left: Binding, source_left: str, right: Binding, source_right: str) -> dict:
    """Compara dos fuentes indexadas incluso en cuentas distintas, si ambas están autorizadas."""
    if left not in bindings or right not in bindings:
        raise SecurityError("Ambas fuentes deben estar dentro del alcance autorizado.")
    rows = store.list_documents((left, right), include_content=True)
    def pick(binding, sid):
        found = [x for x in rows if x["profile"] == binding.profile and
                 x["notebook"] == binding.notebook and x["source_id"] == sid]
        if len(found) != 1:
            raise SecurityError("La fuente seleccionada no está indexada en su cuaderno.")
        return found[0]
    a = pick(left, source_left)
    b = pick(right, source_right)
    lines_a = [x[:1500] for x in a["content"].splitlines()[:3000]]
    lines_b = [x[:1500] for x in b["content"].splitlines()[:3000]]
    diff = list(islice(difflib.unified_diff(lines_a, lines_b,
                                    fromfile=left.key + "|" + source_left,
                                    tofile=right.key + "|" + source_right, lineterm=""), 121))
    return {"fuentes": [{"perfil":x["profile"], "cuaderno":x["notebook"], "fuente":x["source_id"],
                          "sha256":x["sha256"], "version":x["version"]} for x in (a,b)],
            "identicos_sha256": a["sha256"] == b["sha256"],
            "similitud_texto": round(difflib.SequenceMatcher(None, a["content"][:12000], b["content"][:12000]).quick_ratio(), 4),
            "diferencias": diff[:120], "truncado": len(diff)>120}
