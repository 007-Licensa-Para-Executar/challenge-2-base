"""Testes unitários para o módulo de segurança, criptografia em repouso e conformidade LGPD."""

import io
import sqlite3
import sys
from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet

from agents.extractor import cli
from agents.extractor.contracts import (
    Extraction,
    ProcessingResult,
    RunMetadata,
    ValidationMetrics,
)
from agents.extractor.storage import (
    delete_result,
    purge_records,
    read_result_text,
    save_result,
)
from security.encryption import (
    DiaryEncryptor,
    decrypt_diary_text,
    encrypt_diary_text,
    pseudonymize_patient_id,
    rotate_diary_text,
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
    # Padrão: 16 caracteres hex (64 bits de entropia) + 'PAC-' = 20 caracteres
    assert len(pseudo1) == 20
    # O identificador original não deve vazar
    assert "123" not in pseudo1
    assert "456" not in pseudo1

    # Permite customizar tamanho (ex: 8 hex chars para compatibilidade legada)
    pseudo_curto = encryptor.pseudonymize(cpf_ou_prontuario, length=8)
    assert len(pseudo_curto) == 12

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


def test_key_rotation_multi_fernet():
    """Valida rotação de chaves sem downtime com MultiFernet."""
    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()

    # Cifra originalmente com a chave antiga
    old_encryptor = DiaryEncryptor(key=old_key)
    cifrado_antigo = old_encryptor.encrypt("Relato de sessão de 6 meses atrás.")

    # Encryptor atualizado com nova chave primária e antiga como fallback
    rotator = DiaryEncryptor(key=[new_key, old_key])

    # Consegue descriptografar com a chave antiga
    assert rotator.decrypt(cifrado_antigo) == "Relato de sessão de 6 meses atrás."

    # Rotaciona o token para a nova chave
    cifrado_rotacionado = rotator.rotate(cifrado_antigo)
    assert cifrado_rotacionado != cifrado_antigo

    # Agora a nova chave sozinha consegue descriptografar
    new_only_encryptor = DiaryEncryptor(key=new_key)
    assert new_only_encryptor.decrypt(cifrado_rotacionado) == "Relato de sessão de 6 meses atrás."


def test_delete_result_lgpd_art18(tmp_path):
    """Valida exclusão definitiva de registros a pedido do titular (LGPD Art. 18, VI)."""
    db_file = tmp_path / "titular_deletion.db"
    item1 = sample_result()
    item2 = sample_result()

    save_result(db_file, "Relato Paciente 1", item1, encrypt=True)
    save_result(db_file, "Relato Paciente 2", item2, encrypt=True)

    # Exclui item1
    assert delete_result(db_file, item1.id) is True
    assert read_result_text(db_file, item1.id) is None

    # item2 permanece intacto
    assert read_result_text(db_file, item2.id) == "Relato Paciente 2"

    # Tentativa de excluir ID inexistente retorna False
    assert delete_result(db_file, "inexistente") is False


def test_purge_records_retention_policy(tmp_path):
    """Valida expurgo de registros antigos para política de retenção (LGPD Art. 16)."""
    db_file = tmp_path / "retention.db"
    antigo = sample_result()
    recente = sample_result()

    save_result(db_file, "Relato Antigo", antigo, encrypt=True)
    save_result(db_file, "Relato Recente", recente, encrypt=True)

    # Altera artificialmente a data do registro antigo para 100 dias atrás
    passado = (datetime.now(UTC) - timedelta(days=100)).isoformat()
    with sqlite3.connect(db_file) as conn:
        conn.execute("UPDATE runs SET created_at = ? WHERE id = ?", (passado, antigo.id))

    # Expurga registros com mais de 30 dias
    removidos = purge_records(db_file, older_than_days=30)
    assert removidos == 1

    # Verifica que apenas o recente permaneceu
    assert read_result_text(db_file, antigo.id) is None
    assert read_result_text(db_file, recente.id) == "Relato Recente"


def test_cli_encrypt_and_no_encrypt_flags(tmp_path, monkeypatch, capsys):
    """Valida que as flags --encrypt e --no-encrypt funcionam via CLI."""
    class FakeExtractor:
        def __init__(self, settings):
            self.settings = settings

        def extract(self, text):
            return sample_result()

    monkeypatch.setattr(cli, "OllamaExtractor", FakeExtractor)

    db_file = tmp_path / "cli_test.db"
    text = "Relato pelo terminal."

    # 1. Com flag --encrypt
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    code = cli.main(["--synthetic", "--db", str(db_file), "--encrypt"])
    assert code == 0

    with sqlite3.connect(db_file) as conn:
        row = conn.execute("SELECT input_text FROM runs ORDER BY created_at DESC LIMIT 1").fetchone()
    assert row[0].startswith("ENC:")

    # 2. Com flag --no-encrypt
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    code = cli.main(["--synthetic", "--db", str(db_file), "--no-encrypt"])
    assert code == 0

    with sqlite3.connect(db_file) as conn:
        row = conn.execute("SELECT input_text FROM runs ORDER BY created_at DESC LIMIT 1").fetchone()
    assert row[0] == text


def test_convenience_functions():
    """Valida funções de conveniência em nível de módulo."""
    texto = "Teste de função utilitária."
    cifrado = encrypt_diary_text(texto)
    assert cifrado.startswith("ENC:")
    decifrado = decrypt_diary_text(cifrado)
    assert decifrado == texto

    rotacionado = rotate_diary_text(cifrado)
    assert rotacionado.startswith("ENC:")

    pseudo = pseudonymize_patient_id("PACIENTE-X", prefix="CLI")
    assert pseudo.startswith("CLI-")
    assert len(pseudo) == 20
