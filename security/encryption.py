"""Módulo de criptografia em repouso e pseudonimização para conformidade com a LGPD.

Atende ao Art. 5º, II e Art. 46 da Lei Geral de Proteção de Dados (Lei 13.709/2018):
- Criptografia de relatos íntimos e desabafos de saúde mental em repouso (AES-128-CBC + HMAC-SHA256 via Fernet);
- Pseudonimização determinística e irreversível de identificadores de pacientes (HMAC-SHA256);
- Gestão segura de chaves com variáveis de ambiente (DIARY_ENCRYPTION_KEY) ou arquivos com permissão 0600.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

ENCRYPTION_PREFIX = "ENC:"
DEFAULT_KEY_FILE = Path(".diary_encryption.key")


class EncryptionError(Exception):
    """Exceção sanitizada de criptografia, sem vazar chaves ou texto puro."""


class DiaryEncryptor:
    """Gerenciador de criptografia e pseudonimização de dados sensíveis de saúde mental."""

    def __init__(self, key: bytes | str | None = None, key_file: Path | str | None = None) -> None:
        if key is not None:
            self._key = self._normalize_key(key)
        else:
            self._key = self._resolve_key(key_file)
        self._fernet = Fernet(self._key)

    @staticmethod
    def _normalize_key(key: bytes | str) -> bytes:
        if isinstance(key, str):
            key_bytes = key.strip().encode("utf-8")
        else:
            key_bytes = key
        # Valida formato base64 URL-safe de 32 bytes (Fernet)
        try:
            decoded = base64.urlsafe_b64decode(key_bytes)
            if len(decoded) != 32:
                # Se não for uma chave Fernet válida de 32 bytes, deriva via SHA256
                key_bytes = base64.urlsafe_b64encode(hashlib.sha256(key_bytes).digest())
        except (ValueError, TypeError, binascii.Error):
            key_bytes = base64.urlsafe_b64encode(hashlib.sha256(key_bytes).digest())
        return key_bytes

    @classmethod
    def generate_key(cls) -> str:
        """Gera uma nova chave Fernet URL-safe de 32 bytes em formato string."""
        return Fernet.generate_key().decode("utf-8")

    def _resolve_key(self, key_file: Path | str | None = None) -> bytes:
        # 1. Variável de ambiente (recomendado em produção / contêineres)
        env_key = os.environ.get("DIARY_ENCRYPTION_KEY")
        if env_key and env_key.strip():
            return self._normalize_key(env_key)

        # 2. Arquivo de chave local
        target_path = Path(key_file or DEFAULT_KEY_FILE)
        if target_path.exists():
            try:
                content = target_path.read_bytes().strip()
                if content:
                    return self._normalize_key(content)
            except OSError:
                pass

        # 3. Geração automática e persistência com permissões restritas (0600)
        new_key = Fernet.generate_key()
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            mode = 0o600
            fd = os.open(target_path, flags, mode)
            with os.fdopen(fd, "wb") as f:
                f.write(new_key)
        except OSError:
            # Em ambientes somente leitura, mantém a chave em memória
            pass

        return new_key

    def encrypt(self, plaintext: str) -> str:
        """Criptografa um texto em UTF-8 com AES-128-CBC + HMAC-SHA256."""
        if not isinstance(plaintext, str):
            raise TypeError("O texto a ser criptografado deve ser uma string.")
        if not plaintext:
            return ""
        try:
            token = self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
            return f"{ENCRYPTION_PREFIX}{token}"
        except Exception as e:
            raise EncryptionError("Falha ao criptografar dado sensível.") from e

    def decrypt(self, ciphertext: str) -> str:
        """Descriptografa o texto cifrado. Se não for cifrado, retorna como está."""
        if not isinstance(ciphertext, str):
            raise TypeError("O texto a ser descriptografado deve ser uma string.")
        if not ciphertext:
            return ""
        if not self.is_encrypted(ciphertext):
            # Compatibilidade com registros legados gravados em texto claro
            return ciphertext
        token = ciphertext[len(ENCRYPTION_PREFIX) :].encode("utf-8")
        try:
            decrypted_bytes = self._fernet.decrypt(token)
            return decrypted_bytes.decode("utf-8")
        except InvalidToken as e:
            raise EncryptionError("Chave de criptografia inválida ou dado corrompido.") from e
        except UnicodeDecodeError as e:
            raise EncryptionError("Falha na decodificação UTF-8 após descriptografia.") from e

    def is_encrypted(self, text: str) -> bool:
        """Verifica se o texto possui o prefixo de encriptação."""
        return isinstance(text, str) and text.startswith(ENCRYPTION_PREFIX)

    def pseudonymize(self, raw_id: str, prefix: str = "PAC") -> str:
        """Gera um pseudônimo determinístico irreversível para o paciente (LGPD Art. 13).

        Exemplo: '123.456.789-00' -> 'PAC-B4F1A02E'
        """
        if not isinstance(raw_id, str) or not raw_id.strip():
            raise ValueError("Identificador bruto para pseudonimização não pode ser vazio.")
        signature = hmac.new(
            self._key, raw_id.strip().encode("utf-8"), hashlib.sha256
        ).hexdigest()
        short_token = signature[:8].upper()
        return f"{prefix}-{short_token}"


# Instância global reutilizável
_DEFAULT_ENCRYPTOR: DiaryEncryptor | None = None


def get_default_encryptor() -> DiaryEncryptor:
    """Retorna o singleton de encriptação configurado."""
    global _DEFAULT_ENCRYPTOR
    if _DEFAULT_ENCRYPTOR is None:
        _DEFAULT_ENCRYPTOR = DiaryEncryptor()
    return _DEFAULT_ENCRYPTOR


def encrypt_diary_text(text: str) -> str:
    """Função utilitária para encriptação rápida de relato."""
    return get_default_encryptor().encrypt(text)


def decrypt_diary_text(ciphertext: str) -> str:
    """Função utilitária para decriptação rápida de relato."""
    return get_default_encryptor().decrypt(ciphertext)


def pseudonymize_patient_id(raw_id: str, prefix: str = "PAC") -> str:
    """Função utilitária para pseudonimização de identificador."""
    return get_default_encryptor().pseudonymize(raw_id, prefix=prefix)
