"""Crypto service for secure API key storage using AES-GCM."""

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64
import json
from typing import Dict, Any


class SecureCryptoService:
    """AES-GCM based encryption service for sensitive data like API keys."""

    def __init__(self, master_key: bytes):
        if len(master_key) != 32:
            raise ValueError("Master key must be exactly 32 bytes (256 bits)")
        self.key = master_key

    def encrypt_api_key(self, api_key: str) -> Dict[str, str]:
        aesgcm = AESGCM(self.key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, api_key.encode(), None)
        return {
            "nonce": base64.b64encode(nonce).decode(),
            "tag": base64.b64encode(ciphertext[-16:]).decode(),
            "ciphertext": base64.b64encode(ciphertext[:-16]).decode()
        }

    def decrypt_api_key(self, encrypted_dict: Dict[str, str]) -> str:
        aesgcm = AESGCM(self.key)
        nonce = base64.b64decode(encrypted_dict["nonce"])
        tag = base64.b64decode(encrypted_dict["tag"])
        ciphertext = base64.b64decode(encrypted_dict["ciphertext"])
        ciphertext_with_tag = ciphertext + tag
        decrypted = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return decrypted.decode()

    def encrypt(self, plaintext: str) -> str:
        """Convenience: encrypt and return as base64-encoded JSON dict for DB storage."""
        d = self.encrypt_api_key(plaintext)
        return base64.b64encode(json.dumps(d).encode()).decode()

    def decrypt(self, encoded: str) -> str:
        """Convenience: decode and decrypt value stored via encrypt()."""
        d = json.loads(base64.b64decode(encoded).decode())
        return self.decrypt_api_key(d)
