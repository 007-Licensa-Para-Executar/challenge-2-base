from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from uuid import UUID

import pytest
from cryptography.fernet import Fernet

from privacy.vault import Vault, VaultError


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    kind: str


def key() -> str:
    return Fernet.generate_key().decode("ascii")


def test_registration_uses_a_persistent_uuid_per_source_key(tmp_path):
    path = tmp_path / "vault.sqlite3"
    keys = [key()]
    vault = Vault(path, keys)
    first = vault.register("source-1", "Nome de Exemplo")
    second = vault.register("source-2", "Nome de Exemplo")

    assert UUID(first).version == 4
    assert UUID(second).version == 4
    assert first != second

    reopened = Vault(path, keys)
    assert reopened.register("source-1", "Nome de Exemplo") == first
    assert reopened.display_name(first) == "Nome de Exemplo"
    with pytest.raises(ValueError, match="different name"):
        reopened.register("source-1", "Outro Nome")
    with pytest.raises(KeyError):
        reopened.display_name(str(UUID(int=0)))


def test_records_and_entity_tokens_are_scoped_and_survive_restart(tmp_path):
    path = tmp_path / "vault.sqlite3"
    keys = [key()]
    vault = Vault(path, keys)
    first = vault.register("source-1", "Paciente A")
    second = vault.register("source-2", "Paciente B")
    title = "ANA  PÉROLA"
    text = "Ana Pérola disse oi."
    person = [Span(0, len("Ana Pérola"), "PERSON")]
    title_person = [Span(0, len(title), "PERSON")]

    treated_text, token, representation_id = vault.protect(
        first, "my-record", text, title, person, title_person, "detector-v1"
    )
    assert token.startswith("[PERSON_")
    assert treated_text == f"{token} disse oi."
    assert UUID(representation_id).version == 4
    with pytest.raises(KeyError):
        vault.original(second, "my-record")

    reopened = Vault(path, keys)
    assert reopened.protect(
        first, "my-record", text, title, person, title_person, "detector-v1"
    ) == (treated_text, token, representation_id)
    other_text, other_token, other_id = reopened.protect(
        second, "my-record", text, title, person, title_person, "detector-v1"
    )
    assert other_token != token
    assert other_id != representation_id
    assert other_text == f"{other_token} disse oi."
    assert reopened.original(first, "my-record") == {"text": text, "title": title}

    for conflicting_text, conflicting_title, conflicting_version in (
        ("Ana Pérola saiu.", title, "detector-v1"),
        (text, "Título", "detector-v1"),
        (text, title, "detector-v2"),
    ):
        with pytest.raises(ValueError, match="different content or version"):
            reopened.protect(
                first,
                "my-record",
                conflicting_text,
                conflicting_title,
                person,
                [],
                conflicting_version,
            )
    assert reopened.original(first, "my-record") == {"text": text, "title": title}


def test_queries_use_existing_tokens_and_never_register_unknown_entities(tmp_path):
    path = tmp_path / "vault.sqlite3"
    keys = [key()]
    vault = Vault(path, keys)
    patient = vault.register("source-1", "Paciente A")
    person = [Span(0, 10, "PERSON")]
    secret = "Ana Pérola"
    assert vault.protect(patient, None, secret, None, person, [], "v1")[:2] == ("[PERSON]", None)
    assert secret.encode() not in path.read_bytes()
    vault = Vault(path, keys)
    assert vault.protect(patient, None, secret, None, person, [], "v1")[0] == "[PERSON]"
    token, _, _ = vault.protect(patient, "record", secret, None, person, [], "v1")
    assert vault.protect(patient, None, "ANA PÉROLA", None, person, [], "v1")[0] == token


def test_direct_identifiers_leave_only_neutral_tags(tmp_path):
    vault = Vault(tmp_path / "vault.sqlite3", [key()])
    patient = vault.register("source-1", "Paciente A")
    cpf, phone, email = "792.390.470-27", "+55 11 99999-0000", "ana@example.test"
    text = f"{cpf} / {phone} / {email}"
    spans = [
        Span(text.index(value), text.index(value) + len(value), kind)
        for value, kind in [(cpf, "CPF"), (phone, "PHONE"), (email, "EMAIL")]
    ]
    assert vault.protect(patient, "record", text, None, spans, [], "v1")[0] == (
        "[CPF] / [PHONE] / [EMAIL]"
    )


def test_encrypts_originals_and_reads_previous_keys_during_rotation(tmp_path):
    path = tmp_path / "vault.sqlite3"
    old_key, new_key = key(), key()
    vault = Vault(path, [old_key])
    source_key, name = "sensitive-source-reference", "Nome particular do paciente"
    record_id = "sensitive-record-reference"
    entity = "Joana Pérola"
    original = f"{entity} compartilhou detalhes pessoais."
    title = "Detalhes sensíveis sobre a família"
    patient = vault.register(source_key, name)
    original_result = vault.protect(
        patient, record_id, original, title, [Span(0, len(entity), "PERSON")], [], "v1"
    )

    stored = path.read_bytes()
    for value in (source_key, name, record_id, entity, original, title, original_result[0]):
        assert value.encode() not in stored

    with pytest.raises(VaultError, match="could not be decrypted"):
        Vault(path, [new_key])

    rotated = Vault(path, [new_key, old_key])
    assert rotated.register(source_key, name) == patient
    assert rotated.display_name(patient) == name
    assert rotated.original(patient, record_id) == {"text": original, "title": title}
    assert (
        rotated.protect(
            patient, record_id, original, title, [Span(0, len(entity), "PERSON")], [], "v1"
        )
        == original_result
    )
    new_patient = rotated.register("second-source", "Paciente novo")
    assert Vault(path, [new_key, old_key]).display_name(new_patient) == "Paciente novo"
    with pytest.raises(VaultError, match="could not be decrypted"):
        vault.display_name(new_patient)


@pytest.mark.parametrize("keys", [[], ["password"], ["a" * 43 + "="], ["invalid base64"]])
def test_rejects_invalid_keys_before_creating_storage(tmp_path, keys):
    path = tmp_path / "vault.sqlite3"
    with pytest.raises(ValueError):
        Vault(path, keys)
    assert not path.exists()


def test_invalid_spans_leave_record_and_entity_names_unstored(tmp_path):
    vault = Vault(tmp_path / "vault.sqlite3", [key()])
    patient = vault.register("source-1", "Paciente A")
    person = [Span(0, 10, "PERSON")]
    secret = "Ana Pérola"

    with pytest.raises(ValueError, match="outside its input"):
        vault.protect(patient, "record", secret, None, person, person, "v1")
    with pytest.raises(ValueError, match="overlap"):
        vault.protect(patient, "record", secret, None, [*person, Span(0, 3, "ORG")], [], "v1")
    with pytest.raises(KeyError):
        vault.original(patient, "record")
    assert vault.protect(patient, None, secret, None, person, [], "v1")[0] == "[PERSON]"


def test_concurrent_registration_and_ingestion_replay_one_representation(tmp_path):
    vault = Vault(tmp_path / "vault.sqlite3", [key()])

    def ingest(_):
        patient = vault.register("source-1", "Paciente A")
        return patient, vault.protect(
            patient, "record", "Ana Pérola", None, [Span(0, 10, "PERSON")], [], "v1"
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = set(pool.map(ingest, range(8)))
    assert len(results) == 1

def test_first_name_alone_does_not_create_cross_record_link(tmp_path):
    vault = Vault(tmp_path / "first-name.sqlite3", [Fernet.generate_key().decode()])
    patient = vault.register("fictional", "Ana Fictícia")
    for record in ("one", "two"):
        result = vault.protect(patient, record, "Ana", None, [Span(0, 3, "PERSON")], [], "v1")
        assert result[0] == "[PERSON]"
