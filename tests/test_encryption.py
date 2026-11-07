"""Testes unitários para o módulo de segurança, criptografia em repouso e conformidade LGPD."""

import sqlite3

from agents.extractor.contracts import (
    Extraction,
    ProcessingResult,
    RunMetadata,
    ValidationMetrics,
)
from agents.extractor.storage import read_result_text, save_result
from security.encryption import (
    DiaryEncryptor,
    decrypt_diary_text,
    encrypt_diary_text,
    pseudonymize_patient_id,
)


def sample_result() -> ProcessingResult:
    return ProcessingResult(
        status="ok",
        extraction=Extraction(
            tema="familia", sentimento="alegria", indicio_textual_risco="nao_identificado"
        ),
        validation=ValidationMetrics(
            nlp_polaridade="POSITIVO",
            nlp_score=0.8,
            discrepancia_detectada=False,
            distancia_polaridade=0.2,
        ),
        metadata=RunMetadata(model="fake", model_digest="sha256:test"),
    )


def test_encryptor_roundtrip():
    """Valida que o texto criptografado é recuperado perfeitamente na descriptografia."""
    encryptor = DiaryEncryptor()
    secret_text = "Relato confidencial com dados sensíveis de saúde mental e família."

    encrypted = encryptor.encrypt(secret_text)
    assert encryptor.is_encrypted(encrypted)
    assert secret_text not in encrypted
    assert encrypted.startswith("ENC:")

    decrypted = encryptor.decrypt(encrypted)
    assert decrypted == secret_text


def test_encryptor_backward_compatibility():
    """Garante que texto em claro legado não falha e é retornado intacto."""
    encryptor = DiaryEncryptor()
    plain = "Texto antigo não criptografado."
    assert not encryptor.is_encrypted(plain)
    assert encryptor.decrypt(plain) == plain


def test_pseudonymization_deterministic_and_anonymized():
    """Valida pseudonimização determinística de identificadores (LGPD Art. 13)."""
    encryptor = DiaryEncryptor()
    cpf_ou_prontuario = "123.456.789-00"

    pseudo1 = encryptor.pseudonymize(cpf_ou_prontuario)
    pseudo2 = encryptor.pseudonymize(cpf_ou_prontuario)

    # Determinístico para a mesma chave
    assert pseudo1 == pseudo2
    assert pseudo1.startswith("PAC-")
    assert len(pseudo1) == 12  # 'PAC-' + 8 caracteres hex
    # O identificador original não deve vazar
    assert "123" not in pseudo1
    assert "456" not in pseudo1

    # Identificadores diferentes geram pseudônimos diferentes
    pseudo_outro = encryptor.pseudonymize("987.654.321-99")
    assert pseudo_outro != pseudo1


def test_storage_encryption_at_rest(tmp_path):
    """Valida que save_result com encrypt=True grava o texto cifrado no SQLite (LGPD Art. 46)."""
    db_file = tmp_path / "encrypted_diary.db"
    sensivel = "Desabafo íntimo: estou tendo pensamentos desesperadores sobre meu casamento."
    item = sample_result()

    save_result(db_file, sensivel, item, encrypt=True)

    # Inspeciona diretamente o banco SQLite sem descriptografar
    with sqlite3.connect(db_file) as conn:
        raw_row = conn.execute("SELECT input_text FROM runs WHERE id = ?", (item.id,)).fetchone()
        stored_raw = raw_row[0]

    # O texto no disco deve ser um ciphertext (ininteligível sem a chave)
    assert stored_raw.startswith("ENC:")
    assert sensivel not in stored_raw
    assert "casamento" not in stored_raw

    # Recuperação transparente via read_result_text
    recovered = read_result_text(db_file, item.id)
    assert recovered == sensivel


def test_storage_encryption_via_env_var(tmp_path, monkeypatch):
    """Valida ativação global de criptografia via variável de ambiente."""
    monkeypatch.setenv("ENABLE_DIARY_ENCRYPTION", "true")

    db_file = tmp_path / "env_encrypted.db"
    sensivel = "Relato protegido por configuração de ambiente."
    item = sample_result()

    save_result(db_file, sensivel, item)

    with sqlite3.connect(db_file) as conn:
        stored_raw = conn.execute("SELECT input_text FROM runs WHERE id = ?", (item.id,)).fetchone()[0]

    assert stored_raw.startswith("ENC:")
    assert sensivel not in stored_raw

    recovered = read_result_text(db_file, item.id)
    assert recovered == sensivel


def test_convenience_functions():
    """Valida funções de conveniência em nível de módulo."""
    texto = "Teste de função utilitária."
    cifrado = encrypt_diary_text(texto)
    assert cifrado.startswith("ENC:")
    decifrado = decrypt_diary_text(cifrado)
    assert decifrado == texto

    pseudo = pseudonymize_patient_id("PACIENTE-X", prefix="CLI")
    assert pseudo.startswith("CLI-")
