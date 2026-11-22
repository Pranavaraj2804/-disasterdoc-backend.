import os
import re
import time
import base64
import hashlib

class PrivacyService:
    def __init__(self, vault_dir: str = "backend/storage/secure_vault", retention_hours: int = 24):
        self.vault_dir = vault_dir
        self.retention_seconds = retention_hours * 3600
        os.makedirs(vault_dir, exist_ok=True)

    @staticmethod
    def mask_sensitive_text(text: str) -> str:
        # Mask 12-digit ID numbers -> [ID REDACTED - LAST4: XXXX]
        text = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?(\d{4})\b', r'[ID REDACTED - ****\1]', text)
        # Mask PAN numbers
        text = re.sub(r'\b[A-Z]{5}\d{4}[A-Z]\b', '[PAN REDACTED]', text)
        # Mask Bank Account numbers (9 to 18 digits)
        text = re.sub(r'\b\d{9,18}\b', '[ACCOUNT REDACTED]', text)
        return text

    def secure_store_bytes(self, filename: str, raw_bytes: bytes, secret_key: str = "disasterdoc-key") -> str:
        # XOR-obfuscated base64 storage wrapper for uploaded files at rest
        key_bytes = hashlib.sha256(secret_key.encode()).digest()
        encrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(raw_bytes))
        encoded = base64.b64encode(encrypted)
        safe_name = f"{int(time.time())}_{os.path.basename(filename)}.enc"
        out_path = os.path.join(self.vault_dir, safe_name)
        with open(out_path, "wb") as f:
            f.write(encoded)
        return out_path

    def purge_expired_files(self) -> int:
        now = time.time()
        removed = 0
        for fname in os.listdir(self.vault_dir):
            fpath = os.path.join(self.vault_dir, fname)
            if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > self.retention_seconds:
                os.remove(fpath)
                removed += 1
        return removed
