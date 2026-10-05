"""
Small, dependency-free helpers to compute the provenance metadata CASE
expects for a File/ContentDataFacet (size, hashes, entropy, a magic-number
guess).
"""
import hashlib
import math


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = {}
    for byte in data:
        freq[byte] = freq.get(byte, 0) + 1
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


def sniff_magic(header: bytes) -> str:
    # Only recognizes the handful of formats this dataset actually contains
    # (SQLite, JSON/text). Extend it if new data sources are added later.
    # TODO: extend this with python-magic.
    if header.startswith(b"SQLite format 3\x00"):
        return "SQLite 3.x database"
    stripped = header.lstrip()
    if stripped[:1] in (b"{", b"["):
        return "JSON text data"
    return "data"


def md5_hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_stats(path: str):
    """Return (size_in_bytes, entropy, magic_number, md5_hex, sha256_hex)
    for a file. Both hashes are computed off the same read so they're
    guaranteed consistent with each other and with sizeInBytes/entropy."""
    with open(path, "rb") as f:
        data = f.read()
    return len(data), shannon_entropy(data), sniff_magic(data), md5_hex(data), sha256_hex(data)
