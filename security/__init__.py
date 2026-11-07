"""Módulo de segurança, criptografia em repouso e conformidade com LGPD."""

from security.encryption import (
    DiaryEncryptor,
    decrypt_diary_text,
    encrypt_diary_text,
    get_default_encryptor,
    pseudonymize_patient_id,
)

__all__ = [
    "DiaryEncryptor",
    "decrypt_diary_text",
    "encrypt_diary_text",
    "get_default_encryptor",
    "pseudonymize_patient_id",
]
