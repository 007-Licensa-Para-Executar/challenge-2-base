"""A ingestão científica recusa documento sem autorização ligada ao texto."""

import hashlib
import json
from datetime import UTC, datetime

import pytest

from agents.copilot.contracts import DiaryRecord, Query
from agents.copilot.literature import (
    LITERATURE_MANIFEST,
    LicenseError,
    LiteratureStore,
    build_document,
    literature_test_scope,
    load_catalog,
)
from agents.copilot.storage import DiaryStore

BODY = "Texto fictício sobre sono e rotina, sem paciente e sem artigo real."
OTHER = "Outro texto fictício, diferente do que foi autorizado."


def article(text=BODY, **extra):
    values = {
        "document_id": "artigo_ok",
        "title": "Estudo fictício",
        "authors": ["Autora"],
        "year": 2026,
        "doi": "10.0000/ficticio",
        "license": "CC BY 4.0",
        "original_text": text,
        "synthetic": False,
    }
    values.update(extra)
    return build_document(**values)


def trust(monkeypatch, path, document, **extra):
    row = {
        "document_id": document.document_id,
        "title": document.title,
        "license": document.license,
        "doi": document.doi,
        "status": "aprovada",
        "text_sha256": hashlib.sha256(document.original_text.encode()).hexdigest(),
    }
    row.update(extra)
    path.write_text(json.dumps({"documents": [row]}), encoding="utf-8")
    monkeypatch.setattr("agents.copilot.literature.LITERATURE_MANIFEST", path)


def official(document_id):
    payload = json.loads(LITERATURE_MANIFEST.read_text(encoding="utf-8"))
    return next(row for row in payload["documents"] if row["document_id"] == document_id)


def test_approved_text_is_stored(tmp_path, monkeypatch):
    document = article()
    trust(monkeypatch, tmp_path / "manifesto.json", document)
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    assert store.save(document) == "saved"
    saved = store.list_documents()[0]
    assert saved.document_id == "artigo_ok"
    assert saved.original_text == BODY
    assert saved.license == "CC BY 4.0"


def test_missing_license_writes_nothing(tmp_path):
    store = LiteratureStore(tmp_path / "nova" / "literatura.sqlite3")
    with pytest.raises(LicenseError) as refused:
        store.save(article())
    assert refused.value.code == "license_missing"
    assert not store.db_path.exists()
    assert not store.db_path.parent.exists()


def test_pending_and_denied_licenses_are_refused(tmp_path, monkeypatch):
    document = article()
    manifest = tmp_path / "manifesto.json"
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    trust(monkeypatch, manifest, document, status="pendente")
    with pytest.raises(LicenseError) as pending:
        store.save(document)
    assert pending.value.code == "license_pending"
    trust(monkeypatch, manifest, document, status="negada")
    with pytest.raises(LicenseError) as denied:
        store.save(document)
    assert denied.value.code == "license_denied"
    assert not store.db_path.exists()


def test_inconsistent_metadata_is_refused(tmp_path, monkeypatch):
    document = article()
    trust(monkeypatch, tmp_path / "manifesto.json", document, text_sha256="CC BY 4.0")
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    with pytest.raises(LicenseError) as refused:
        store.save(document)
    assert refused.value.code == "license_inconsistent"
    assert not store.db_path.exists()


def test_forged_pt001_cannot_replace_the_approved_identity(tmp_path):
    record = official("PT-001")
    document = article(
        document_id="PT-001",
        title=record["title"],
        doi=record["doi"],
        license=record["license"],
    )
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    with pytest.raises(LicenseError) as refused:
        store.save(document)
    assert refused.value.code == "license_identity_mismatch"
    with pytest.raises(TypeError):
        store.save(document, {"document_id": "PT-001", "status": "aprovada"})
    assert not store.db_path.exists()


def test_changed_text_keeps_the_approved_row(tmp_path, monkeypatch):
    document = article()
    trust(monkeypatch, tmp_path / "manifesto.json", document)
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    store.save(document)
    before = store.db_path.read_bytes()
    changed = article(OTHER)
    with pytest.raises(LicenseError) as refused:
        store.save(changed)
    assert refused.value.code == "license_identity_mismatch"
    assert store.db_path.read_bytes() == before
    assert store.list_documents()[0].original_text == BODY


def test_medpt_without_authorization_is_refused(tmp_path):
    document = article(
        "Registro fictício que não é o corpus MedPT.",
        document_id="medpt",
        title="MedPT",
        doi=None,
        license="CC BY 4.0",
    )
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    with pytest.raises(TypeError):
        store.save(document, {"document_id": "medpt", "status": "aprovada", "license": "CC BY 4.0"})
    with pytest.raises(LicenseError) as missing:
        store.save(document)
    assert missing.value.code == "license_missing"
    assert not store.db_path.exists()


def test_official_pending_ids_stay_blocked(tmp_path):
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    for document_id in ("PT-003", "PT-004"):
        record = official(document_id)
        document = article(
            document_id=document_id, title=record["title"], doi=record["doi"], license=None,
        )
        with pytest.raises(LicenseError) as refused:
            store.save(document)
        assert refused.value.code == "license_pending"
    assert not store.db_path.exists()


def test_fixture_text_requires_the_test_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("LITERATURE_FIXTURES", raising=False)
    document = article(synthetic=True, license=None, doi=None)
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    with pytest.raises(LicenseError) as refused:
        store.save(document)
    assert refused.value.code == "license_missing"
    assert not store.db_path.exists()
    monkeypatch.setenv("LITERATURE_FIXTURES", "1")
    with pytest.raises(LicenseError) as still_closed:
        store.save(document)
    assert still_closed.value.code == "license_missing"
    with literature_test_scope():
        assert store.save(document) == "saved"
    assert store.list_documents()[0].synthetic is True


def test_fixture_scope_outside_pytest_stays_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("LITERATURE_FIXTURES", "1")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    document = article(synthetic=True, license=None, doi=None, document_id="nota_fora")
    store = LiteratureStore(tmp_path / "fora.sqlite3")
    with literature_test_scope(), pytest.raises(LicenseError) as refused:
        store.save(document)
    assert refused.value.code == "license_missing"
    assert not store.db_path.exists()


def test_diary_records_do_not_need_a_scientific_license(tmp_path):
    store = DiaryStore(tmp_path / "diarios.sqlite3")
    store.save(DiaryRecord(
        record_id="d1",
        patient_id="patient_ana",
        recorded_at=datetime(2026, 11, 15, tzinfo=UTC),
        original_text="Relato fictício sobre o dia.",
    ))
    found = store.list_records(Query(patient_id="patient_ana", question="dia"))
    assert found[0].original_text == "Relato fictício sobre o dia."


def test_demo_catalog_loads_and_an_extra_file_does_not(tmp_path, monkeypatch):
    monkeypatch.delenv("LITERATURE_FIXTURES", raising=False)
    store = LiteratureStore(tmp_path / "literatura.sqlite3")
    assert load_catalog(store) == 3
    root = tmp_path / "colecao"
    root.mkdir()
    (root / "novo.txt").write_text("Texto fictício fora do catálogo autorizado.", encoding="utf-8")
    (root / "catalog.jsonl").write_text(json.dumps({
        "document_id": "novo_texto",
        "title": "Novo",
        "authors": ["Autora"],
        "year": 2026,
        "path": "novo.txt",
        "synthetic": True,
    }) + "\n", encoding="utf-8")
    extra = LiteratureStore(tmp_path / "extra.sqlite3")
    with pytest.raises(LicenseError) as refused:
        load_catalog(extra, root)
    assert refused.value.code == "license_missing"
    assert not extra.db_path.exists()
