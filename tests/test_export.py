import csv
import io
import json
from zipfile import ZipFile
import pytest
from notebook_conexion.exports import export_records, export_generated, save_export
from notebook_conexion.errors import SecurityError


def test_export_no_arbitrary_path(tmp_path):
    with pytest.raises(SecurityError):
        save_export("../../evil", "json", "hi", base=tmp_path)
    with pytest.raises(SecurityError):
        save_export("foo", "exe", "hi", base=tmp_path)


def test_export_never_overwrites(tmp_path):
    x = save_export("catalogo", "txt", "A", base=tmp_path)
    y = save_export("catalogo", "txt", "B", base=tmp_path)
    assert x.read_text() == "A" and y.read_text() == "B" and x != y


def test_csv_spreadsheet_injection(tmp_path):
    p = export_records([{"name": "=HYPERLINK(1)", "displayName": "+attack"}],
                       stem="informe", fmt="csv", title="Demo", base=tmp_path)
    rows = list(csv.reader(io.StringIO(p.read_text(encoding="utf-8-sig"))))
    assert rows[1][0].startswith("'=")
    assert rows[1][1].startswith("'+")


def test_docx_is_valid_zip_with_xml_escaped(tmp_path):
    p = export_generated("Hola < & >\nMundo", stem="informe", fmt="docx", base=tmp_path)
    with ZipFile(p) as z:
        assert z.testzip() is None
        doc = z.read("word/document.xml").decode()
        assert "&lt;" in doc and "&amp;" in doc
        assert 'Hola < &' not in doc


def test_symlink_export_directory_rejected(tmp_path):
    link = tmp_path / 'link'
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip('Symlinks are not allowed here')
    with pytest.raises(SecurityError):
        save_export("nota", "txt", "x", base=link)


def test_export_json_is_array(tmp_path):
    p = export_records([{"name":"notebooks/abc"}], stem="out", fmt="json", title="Demo", base=tmp_path)
    assert json.loads(p.read_text())[0]["name"] == "notebooks/abc"
