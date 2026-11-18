"""Módulo de segurança, criptografia em repouso e conformidade com LGPD."""

from security.encryption import (
    DiaryEncryptor,
    EncryptionError,
    decrypt_diary_text,
    encrypt_diary_text,
    get_default_encryptor,
    pseudonymize_patient_id,
    rotate_diary_text,
)

__all__ = [
    "DiaryEncryptor",
    "EncryptionError",
    "decrypt_diary_text",
    "encrypt_diary_text",
    "get_default_encryptor",
    "pseudonymize_patient_id",
    "rotate_diary_text",
]
