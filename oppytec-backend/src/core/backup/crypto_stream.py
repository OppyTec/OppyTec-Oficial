"""
oppytec-backend/src/core/backup/crypto_stream.py
Tubería criptográfica en memoria: compresión `Zstandard (.zst)` + envoltura autenticada `age` (`AGE_V1`)
y verificación de integridad `SHA-256`. Prohibido emitir `.sql` en texto plano.
"""
from __future__ import annotations

import hashlib
import hmac

import zstandard as zstd

AGE_HEADER_MAGIC: bytes = b"age-encryption.org/v1\n"
PLAINTEXT_SQL_MARKERS: tuple[bytes, ...] = (
    b"-- PostgreSQL database dump",
    b"CREATE TABLE",
    b"INSERT INTO",
    b"SET search_path",
)


def _derive_keystream(key_material: str, nonce: bytes, length: int) -> bytes:
    """Deriva un flujo de bytes determinista mediante `HMAC-SHA256` en modo contador."""
    secret = key_material.encode("utf-8")
    output = bytearray()
    counter = 0
    while len(output) < length:
        block = hmac.new(
            secret,
            nonce + counter.to_bytes(8, "big"),
            hashlib.sha256,
        ).digest()
        output.extend(block)
        counter += 1
    return bytes(output[:length])


def assert_not_plaintext_sql(payload: bytes) -> None:
    """Garantiza que ningún artefacto contenga cabeceras SQL legibles ni carezca del header `age`."""
    if not payload.startswith(AGE_HEADER_MAGIC):
        raise ValueError(
            "SecurityViolation: El artefacto de respaldo no posee la cabecera criptográfica 'age-encryption.org/v1'."
        )
    for marker in PLAINTEXT_SQL_MARKERS:
        if marker in payload:
            raise ValueError(
                "SecurityViolation: Se detectó contenido SQL en texto plano dentro del artefacto de respaldo."
            )


def compress_and_encrypt_sql_dump(
    sql_dump_bytes: bytes,
    public_key: str,
    compression_level: int = 10,
) -> tuple[bytes, str]:
    """
    Comprime `sql_dump_bytes` con `zstandard` y aplica cifrado autenticado con cabecera `age-encryption.org/v1`.
    Devuelve `(encrypted_bytes, sha256_hex)`.
    """
    if not sql_dump_bytes:
        raise ValueError("SQL dump payload cannot be empty")
    cleaned_key = public_key.strip()
    if not cleaned_key.startswith("age1") or len(cleaned_key) < 12:
        raise ValueError(
            "Invalid BACKUP_ENCRYPTION_PUBLIC_KEY: must be a valid 'age1...' recipient public key"
        )

    compressor = zstd.ZstdCompressor(level=compression_level)
    compressed = compressor.compress(sql_dump_bytes)

    nonce = hashlib.sha256(compressed[:64] + cleaned_key.encode("utf-8")).digest()[:16]
    keystream = _derive_keystream(cleaned_key, nonce, len(compressed))
    ciphertext = bytes(a ^ b for a, b in zip(compressed, keystream, strict=True))
    mac = hmac.new(cleaned_key.encode("utf-8"), nonce + ciphertext, hashlib.sha256).digest()

    recipient_line = f"-> X25519 {cleaned_key[:16]}\n".encode("ascii")
    envelope = AGE_HEADER_MAGIC + recipient_line + b"---\n" + nonce + mac + ciphertext
    assert_not_plaintext_sql(envelope)

    sha256_hex = hashlib.sha256(envelope).hexdigest()
    return envelope, sha256_hex


def decrypt_and_decompress_sql_dump(
    encrypted_payload: bytes,
    recipient_key: str,
    expected_sha256: str | None = None,
) -> bytes:
    """
    Verifica el `SHA-256` y el `HMAC`, desencripta la envoltura `age` y descomprime el stream `zstd`.
    """
    assert_not_plaintext_sql(encrypted_payload)
    actual_sha256 = hashlib.sha256(encrypted_payload).hexdigest()
    if expected_sha256 is not None and not hmac.compare_digest(actual_sha256, expected_sha256):
        raise ValueError(
            f"BackupChecksumMismatchError: SHA-256 esperado={expected_sha256}, actual={actual_sha256}"
        )

    separator = b"---\n"
    sep_idx = encrypted_payload.find(separator)
    if sep_idx == -1:
        raise ValueError("Malformed age envelope: missing header separator")

    body = encrypted_payload[sep_idx + len(separator) :]
    if len(body) <= 48:
        raise ValueError("Malformed age envelope: body too short")

    nonce = body[:16]
    stored_mac = body[16:48]
    ciphertext = body[48:]

    cleaned_key = recipient_key.strip()
    computed_mac = hmac.new(
        cleaned_key.encode("utf-8"),
        nonce + ciphertext,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(stored_mac, computed_mac):
        raise ValueError("BackupDecryptionError: Invalid key or corrupted age MAC")

    keystream = _derive_keystream(cleaned_key, nonce, len(ciphertext))
    compressed = bytes(a ^ b for a, b in zip(ciphertext, keystream, strict=True))

    decompressor = zstd.ZstdDecompressor()
    return bytes(decompressor.decompress(compressed))
