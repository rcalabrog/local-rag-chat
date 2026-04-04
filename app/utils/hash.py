import hashlib


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
