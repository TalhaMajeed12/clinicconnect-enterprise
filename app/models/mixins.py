# ENCRYPTION MIXIN
# ============================================
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


class EncryptionMixin:
    _fernet = None
    _fernet_key = None
    
    @classmethod
    def _get_fernet(cls):
        key = current_app.config['ENCRYPTION_KEY']
        encoded_key = key.encode() if isinstance(key, str) else key
        if cls._fernet is None or cls._fernet_key != encoded_key:
            cls._fernet = Fernet(encoded_key)
            cls._fernet_key = encoded_key
        return cls._fernet
    
    def encrypt_field(self, value):
        if value is None:
            return None
        fernet = self._get_fernet()
        return fernet.encrypt(value.encode()).decode()
    
    def decrypt_field(self, encrypted_value):
        if encrypted_value is None:
            return None
        try:
            fernet = self._get_fernet()
            return fernet.decrypt(encrypted_value.encode()).decode()
        except (InvalidToken, ValueError, TypeError):
            current_app.logger.warning(
                'Unable to decrypt a protected field; verify ENCRYPTION_KEY without rotating it'
            )
            return None
 
