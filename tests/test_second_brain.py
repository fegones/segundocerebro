"""Pruebas offline: seguridad de selección, cifrado, duplicados y abstención."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from notebook_conexion.brain_audit import (audit_notebooks, audit_sources, compare_documents,
                                            compare_versions, normalize_url)
from notebook_conexion.brain_answers import verify_response, answer_with_gemini
from notebook_conexion.brain_import import read_file, import_file
from notebook_conexion.brain_retrieval import ABSTENTION, answer_extractive, chunks, retrieve, terms
from notebook_conexion.brain_scope import Binding, ScopeStore
from notebook_conexion.brain_store import BrainStore, Document
from notebook_conexion.errors import ConfigurationError, SecurityError, PermissionDenied
from notebook_conexion.store import ProfileStore, Profile
from notebook_conexion.second_brain import SecondBrain

NB1 = "notebooks/550e8400-e29b-41d4-a716-446655440000"
NB2 = "notebooks/550e8400-e29b-41d4-a716-446655440001"
SRC1 = NB1 + "/sources/770e8400-e29b-41d4-a716-446655440000"
SRC2 = NB2 + "/sources/770e8400-e29b-41d4-a716-446655440001"
LEFT = Binding("cuenta1", NB1)
RIGHT = Binding("cuenta2", NB2)
CONTENT = "El plátano verde contiene almidón. El contenido de humedad debe medirse antes y después de cada tratamiento térmico. El balance de masa debe documentar entradas y salidas. " * 8


@pytest.fixture
def db(tmp_path):
    return BrainStore(tmp_path / "private" / "db.sqlite3", key=b"a"*32)


def write(db, binding=LEFT, source="local:a", title="Plátano", content=CONTENT, url="", kind="source"):
    return db.upsert(Document(binding.profile, binding.notebook, source, title, content, url=url, kind=kind))


def test_multiple_account_bindings_unique():
    assert LEFT.key.startswith("cuenta1|")
    assert RIGHT != LEFT


@pytest.mark.parametrize("invalid", ["", "notebooks/no-uuid", "notebooks/../etc/passwd", "notebooks/abc/other", "notebooks/"+"a"*50])
def test_invalid_notebooks_fail_closed(invalid):
    with pytest.raises(SecurityError):
        Binding("personal", invalid)


def test_scope_explicit_and_persistent(tmp_path):
    scope = ScopeStore(root=tmp_path)
    assert scope.load() == ()
    scope.set([RIGHT, LEFT], verify_profiles=False)
    assert scope.active() == (LEFT, RIGHT)
    scope.require(LEFT.profile, LEFT.notebook)
    with pytest.raises(SecurityError):
        scope.require("cuenta1", NB2)
    scope.clear()
    with pytest.raises(ConfigurationError):
        scope.active()


def test_scope_duplicate_and_corrupt(tmp_path):
    s = ScopeStore(root=tmp_path)
    with pytest.raises(SecurityError):
        s.set([LEFT, LEFT], verify_profiles=False)
    s.path.parent.mkdir(parents=True)
    s.path.write_text('{"schema":1,"bindings":[{"profile":"/etc","notebook":"%s"}]}' % NB1)
    with pytest.raises(SecurityError):
        s.load()


def test_store_encrypts_text_and_keeps_versions(db):
    r1=write(db)
    assert r1["version"] == 1
    assert write(db)["estado"] == "sin_cambios"
    changed = CONTENT.replace("almidón", "fibra")
    assert write(db,content=changed)["version"] == 2
    raw=db.path.read_bytes()
    assert b"El pl" not in raw
    assert b"contenido de humedad" not in raw
    doc = db.list_documents((LEFT,), include_content=True)
    assert doc[0]["content"] == changed
    hist=db.versions(LEFT,"local:a")
    assert len(hist)==2 and hist[0]["content"] == CONTENT


def test_store_wrong_key_refuses_decrypt(tmp_path):
    path=tmp_path/"idx.sqlite"
    a=BrainStore(path,key=b"x"*32)
    write(a)
    b=BrainStore(path,key=b"z"*32)
    with pytest.raises(SecurityError):
        b.list_documents((LEFT,),include_content=True)


def test_store_no_cross_account_leak(db):
    write(db, LEFT, content="Plátano melón papaya "*10)
    write(db, RIGHT, source="local:b", content="Confidencial oferta comercial "*10)
    only=db.list_documents((LEFT,),include_content=True)
    assert len(only)==1
    assert "Confidencial" not in json.dumps(only)
    assert len(db.list_documents((LEFT,RIGHT)))==2


def test_catalog_validates_membership(db):
    with pytest.raises(SecurityError):
        db.save_catalog(LEFT,"Cuaderno",[{"name":SRC2,"displayName":"no autorizado"}])
    assert db.list_catalog((LEFT,)) == []
    db.save_catalog(LEFT,"Cuaderno",[{"name":SRC1,"displayName":"Almidón", "originalUrl":"https://example.org/a"}])
    assert len(db.list_catalog((LEFT,)))==1


def test_hash_and_url_duplicates_cross_profiles(db):
    write(db, LEFT, "local:a", "Documento original", CONTENT)
    write(db, RIGHT, "local:b", "Documento cambiado de nombre", CONTENT)
    db.save_catalog(LEFT,"Plátano",[{"name":SRC1,"displayName":"Estudio", "originalUrl":"https://abc.org/a?utm_source=x"}])
    db.save_catalog(RIGHT,"Plátano",[{"name":SRC2,"displayName":"Estudio", "originalUrl":"https://abc.org/a"}])
    audit=audit_sources(db,(LEFT,RIGHT),similarity=False)
    criteria={x["criterio"] for x in audit["grupos"]}
    assert "hash" in criteria and "url" in criteria
    assert "title" in criteria
    assert audit["fuentes_distintas"] == 4


def test_normalize_url_keeps_business_params():
    assert normalize_url("https://example.com/a/?utm_medium=x&ref=2026#section") == "https://example.com/a?ref=2026"
    assert normalize_url("file:///etc/passwd") == ""


def test_notebook_duplicates_are_probable(db):
    db.save_catalog(LEFT,"Patacones",[{"name":SRC1,"displayName":"Manual", "originalUrl":"https://example.com/a"}])
    db.save_catalog(RIGHT,"Patacones",[{"name":SRC2,"displayName":"Manual", "originalUrl":"https://example.com/a"}])
    result=audit_notebooks(db,(LEFT,RIGHT))
    assert result["coincidencias"][0]["titulo_coincidente"]
    assert result["coincidencias"][0]["clasificacion"]=="posibles_duplicados_no_confirmados"


def test_version_comparison(db):
    write(db)
    write(db, content=CONTENT.replace("almidón", "proteína"))
    result=compare_versions(db,LEFT,"local:a",1,2)
    assert not result["identicos"]
    assert result["diferencias"]
    with pytest.raises(SecurityError):
        compare_versions(db,LEFT,"local:a",2,1)


def test_cross_notebook_comparison_guard(db):
    write(db, LEFT, content=CONTENT)
    write(db, RIGHT, source="local:b", content=CONTENT)
    with pytest.raises(SecurityError):
        compare_documents(db,(LEFT,),LEFT,"local:a",RIGHT,"local:b")
    result=compare_documents(db,(LEFT,RIGHT),LEFT,"local:a",RIGHT,"local:b")
    assert result["identicos_sha256"]


def test_evidence_and_abstention(db):
    write(db, LEFT)
    result=retrieve(db,(LEFT,),"¿Cómo documentar el balance de masa y humedad del plátano?")
    assert result["estado"]=="con_evidencia"
    assert result["evidencias"][0]["fuente"]=="local:a"
    assert "balance de masa" in result["evidencias"][0]["fragmento_literal"]
    no=answer_extractive(db,(LEFT,),"¿Cuáles fueron las ventas del conglomerado petrolero?")
    assert no["respuesta"]==ABSTENTION and not no["evidencias"]


def test_retrieval_stays_in_selected_account(db):
    write(db, LEFT, content="Musáceas agricultura alimentos"*15)
    write(db, RIGHT, source="local:b", content="precios confidenciales contratos claves"*15)
    result=retrieve(db,(LEFT,),"precios confidenciales")
    assert result["estado"]=="sin_evidencia"


def test_terms_and_chunks():
    assert "humedad" in terms("¿Qué información sobre humedad?")
    assert len(chunks("palabra "*1000))>1
    with pytest.raises(ValueError):
        chunks("hola",length=100)


def test_import_txt_docx_and_html(tmp_path,db):
    p=tmp_path/"fuente.txt"
    p.write_text(CONTENT,encoding="utf-8")
    result=import_file(db,LEFT,p)
    assert result["version"]==1
    from notebook_conexion.exports import _docx
    x=tmp_path/"evidencia.docx"
    x.write_bytes(_docx("Documento técnica\nBalance de masas"))
    assert "Balance de masas" in read_file(x)
    h=tmp_path/"pagina.html"
    h.write_text('<style>maligno</style><h1>Prueba</h1><script>alert(1)</script><p>Texto</p>')
    assert "Texto" in read_file(h) and "alert" not in read_file(h)


def test_import_symlink_refused(tmp_path):
    p=tmp_path/"doc.txt"
    p.write_text("texto")
    link=tmp_path/"link.txt"
    try:
        link.symlink_to(p)
    except OSError:
        pytest.skip("No symlink privilege")
    with pytest.raises(SecurityError):
        read_file(link)


def test_import_reuses_id_for_history(db,tmp_path):
    p=tmp_path/"doc.md"
    p.write_text("Recomendación: medir pH del producto.")
    import_file(db,LEFT,p,source_id="local:manual")
    p.write_text("Recomendación: medir humedad del producto.")
    out=import_file(db,LEFT,p,source_id="local:manual")
    assert out["version"]==2


def test_answer_validation_validates_literal_quote(db):
    write(db)
    evidence=retrieve(db,(LEFT,),"balance de masa humedad plátano")["evidencias"]
    quote="El contenido de humedad debe medirse antes y después de cada tratamiento térmico."
    good=json.dumps({"respuesta":"La humedad debe medirse [F1]", "citas":[{"id":"[F1]","texto_literal":quote}], "insuficiente":False})
    assert verify_response(good,evidence)["estado"]=="respuesta_con_citas_literales"
    for bad in ["no json", json.dumps({"respuesta":"cambio","citas":[{"id":"[F5]","texto_literal":quote}],"insuficiente":False}),
                json.dumps({"respuesta":"cambio [F1]","citas":[{"id":"[F1]","texto_literal":"Inventado que nunca apareció en fuente"}],"insuficiente":False})]:
        assert verify_response(bad,evidence)["estado"]=="rechazado"


def test_gemini_rejects_any_missing_grant(db,monkeypatch):
    write(db, LEFT)
    profiles=ProfileStore(root=Path(db.path).parent/'profiles_root')
    profiles.save(Profile("cuenta1","proyecto-demo-123","/tmp/demo.json",True))
    monkeypatch.setattr("notebook_conexion.brain_answers.ProfileStore",lambda:profiles)
    with pytest.raises(PermissionDenied):
        answer_with_gemini(db,(LEFT,),"balance masa humedad",grant_checker=lambda p,a: False,
                                                        generator=lambda prompt: "{}")


class FakeClient:
    def __init__(self, name, return_text=True):
        self.name=name
        self.return_text=return_text
    def notebook(self, name):
        return {"name":name,"displayName":"Manual de Plátano"}
    def sources(self, notebook, *, page_size, page_token):
        return {"sources":[{"name": notebook+"/sources/770e8400-e29b-41d4-a716-446655440000", "displayName":"Balance de masa"}]}
    def source(self,name):
        return {"name":name,"displayName":"Balance de masa", "textContent":{"content":CONTENT} if self.return_text else {}}


def test_multiaccount_sync_respects_scope(tmp_path, db):
    profiles=ProfileStore(root=tmp_path/'profile_root')
    for name in ('cuenta1','cuenta2'):
        profiles.save(Profile(name,'proyecto-demo-123','/tmp/demo.json'))
    scope=ScopeStore(root=tmp_path/'scope_root',profiles=profiles)
    scope.set((LEFT,RIGHT))
    brain=SecondBrain(scope=scope,store=db,profiles=profiles,client_factory=lambda profile:FakeClient(profile.name))
    result=brain.sync(include_text=True)
    assert result["cuadernos_sincronizados"]==2
    assert len(brain.documents()["documentos"])==2
    assert {x["profile"] for x in db.list_documents((LEFT,RIGHT))} == {"cuenta1","cuenta2"}
    with pytest.raises(SecurityError):
        brain.import_local(Binding('cuenta1',NB2),tmp_path/'missing.txt')


def test_multiaccount_unavailable_text_not_fabricated(tmp_path,db):
    profiles=ProfileStore(root=tmp_path/'profiles')
    profiles.save(Profile('cuenta1','proyecto-demo-123','/tmp/demo.json'))
    scope=ScopeStore(root=tmp_path/'scope',profiles=profiles)
    scope.set((LEFT,))
    brain=SecondBrain(scope=scope,store=db,profiles=profiles,client_factory=lambda profile:FakeClient(profile.name,False))
    result=brain.sync(include_text=True)
    assert result["resultado"][0]["sin_texto_recuperable"]==1
    assert brain.answer('balance de masa')['respuesta']==ABSTENTION
