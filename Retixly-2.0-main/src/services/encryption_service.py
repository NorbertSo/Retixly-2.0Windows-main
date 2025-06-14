"""
Encryption service for Retixly application.

This module provides secure encryption and decryption for license data
using AES-256 encryption with key derivation.
"""

import os
import base64
import hashlib
import hmac
import secrets
from typing import Union, Optional
import json
import logging

# Try to import cryptography library
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes, padding
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Exception raised for encryption/decryption errors."""
    pass


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.
    
    Uses AES-256-CBC encryption with PBKDF2 key derivation and HMAC authentication.
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service.
        
        Args:
            master_key: Optional master key. If not provided, will be generated.
        """
        if not HAS_CRYPTOGRAPHY:
            raise EncryptionError(
                "Cryptography library not available. Install with: pip install cryptography"
            )
        
        self.master_key = master_key or self._generate_master_key()
        self.salt_length = 16
        self.iv_length = 16
        self.iterations = 100000  # PBKDF2 iterations
        
    def _generate_master_key(self) -> str:
        """
        Generate a secure master key based on system characteristics.
        
        Returns:
            str: Generated master key
        """
        # Use system-specific information for key generation
        import platform
        import uuid
        
        system_info = {
            'platform': platform.platform(),
            'node': platform.node(),
            'processor': platform.processor(),
            'machine': platform.machine(),
        }
        
        # Try to get MAC address
        try:
            mac = hex(uuid.getnode())
            system_info['mac'] = mac
        except:
            pass
        
        # Create base key from system info
        base_key = json.dumps(system_info, sort_keys=True).encode()
        
        # Add some application-specific salt
        app_salt = b'Retixly-v3.0-encryption-key'
        
        # Generate final key
        combined = base_key + app_salt
        key_hash = hashlib.sha256(combined).hexdigest()
        
        return key_hash
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Password to derive key from
            salt: Salt for key derivation
            
        Returns:
            bytes: Derived key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=self.iterations,
            backend=default_backend()
        )
        return kdf.derive(password.encode())
    
    def encrypt(self, data: Union[str, dict]) -> str:
        """
        Encrypt data and return base64 encoded result.
        
        Args:
            data: Data to encrypt (string or dictionary)
            
        Returns:
            str: Base64 encoded encrypted data
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Convert data to JSON string if it's a dict
            if isinstance(data, dict):
                plaintext = json.dumps(data, separators=(',', ':'))
            else:
                plaintext = str(data)
            
            plaintext_bytes = plaintext.encode('utf-8')
            
            # Generate random salt and IV
            salt = os.urandom(self.salt_length)
            iv = os.urandom(self.iv_length)
            
            # Derive key
            key = self._derive_key(self.master_key, salt)
            
            # Pad plaintext to AES block size
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(plaintext_bytes)
            padded_data += padder.finalize()
            
            # Encrypt
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()
            
            # Create HMAC for authentication
            auth_key = self._derive_key(self.master_key + "_auth", salt)
            h = hmac.new(auth_key, salt + iv + ciphertext, hashlib.sha256)
            mac = h.digest()
            
            # Combine salt + iv + mac + ciphertext
            combined = salt + iv + mac + ciphertext
            
            # Encode as base64
            return base64.b64encode(combined).decode('ascii')
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt(self, encrypted_data: str) -> Union[str, dict]:
        """
        Decrypt base64 encoded data.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Union[str, dict]: Decrypted data (parsed as JSON if possible)
            
        Raises:
            EncryptionError: If decryption fails
        """
        try:
            # Decode from base64
            combined = base64.b64decode(encrypted_data)
            
            # Extract components
            salt = combined[:self.salt_length]
            iv = combined[self.salt_length:self.salt_length + self.iv_length]
            mac = combined[self.salt_length + self.iv_length:self.salt_length + self.iv_length + 32]
            ciphertext = combined[self.salt_length + self.iv_length + 32:]
            
            # Verify HMAC
            auth_key = self._derive_key(self.master_key + "_auth", salt)
            h = hmac.new(auth_key, salt + iv + ciphertext, hashlib.sha256)
            expected_mac = h.digest()
            
            if not hmac.compare_digest(mac, expected_mac):
                raise EncryptionError("Authentication failed - data may be corrupted")
            
            # Derive key
            key = self._derive_key(self.master_key, salt)
            
            # Decrypt
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove padding
            unpadder = padding.PKCS7(128).unpadder()
            plaintext_bytes = unpadder.update(padded_plaintext)
            plaintext_bytes += unpadder.finalize()
            
            plaintext = plaintext_bytes.decode('utf-8')
            
            # Try to parse as JSON
            try:
                return json.loads(plaintext)
            except json.JSONDecodeError:
                return plaintext
                
        except EncryptionError:
            raise
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Decryption failed: {e}")
    
    def encrypt_file(self, file_path: str, data: Union[str, dict]) -> None:
        """
        Encrypt data and save to file.
        
        Args:
            file_path: Path to save encrypted file
            data: Data to encrypt
            
        Raises:
            EncryptionError: If encryption or file operation fails
        """
        try:
            encrypted_data = self.encrypt(data)
            
            # Ensure directory exists, but only if directory is not empty
            dir_name = os.path.dirname(file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
                
            logger.info(f"Data encrypted and saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to encrypt file {file_path}: {e}")
            raise EncryptionError(f"Failed to encrypt file: {e}")
    
    def decrypt_file(self, file_path: str) -> Union[str, dict]:
        """
        Read and decrypt data from file.
        
        Args:
            file_path: Path to encrypted file
            
        Returns:
            Union[str, dict]: Decrypted data
            
        Raises:
            EncryptionError: If decryption or file operation fails
        """
        try:
            if not os.path.exists(file_path):
                raise EncryptionError(f"File not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                encrypted_data = f.read().strip()
            
            decrypted_data = self.decrypt(encrypted_data)
            logger.info(f"Data decrypted from {file_path}")
            
            return decrypted_data
            
        except EncryptionError:
            raise
        except Exception as e:
            logger.error(f"Failed to decrypt file {file_path}: {e}")
            raise EncryptionError(f"Failed to decrypt file: {e}")
    
    def change_master_key(self, new_master_key: str, old_data: Union[str, dict]) -> str:
        """
        Change master key and re-encrypt data.
        
        Args:
            new_master_key: New master key
            old_data: Data to re-encrypt with new key
            
        Returns:
            str: Data encrypted with new key
            
        Raises:
            EncryptionError: If re-encryption fails
        """
        try:
            # Store old key
            old_key = self.master_key
            
            # Set new key and encrypt
            self.master_key = new_master_key
            new_encrypted = self.encrypt(old_data)
            
            logger.info("Master key changed successfully")
            return new_encrypted
            
        except Exception as e:
            # Restore old key on failure
            self.master_key = old_key
            logger.error(f"Failed to change master key: {e}")
            raise EncryptionError(f"Failed to change master key: {e}")
    
    def verify_integrity(self, encrypted_data: str) -> bool:
        """
        Verify the integrity of encrypted data without decrypting.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            bool: True if data integrity is valid, False otherwise
        """
        try:
            # Decode from base64
            combined = base64.b64decode(encrypted_data)
            
            # Check minimum length
            min_length = self.salt_length + self.iv_length + 32  # salt + iv + mac
            if len(combined) < min_length:
                return False
            
            # Extract components
            salt = combined[:self.salt_length]
            iv = combined[self.salt_length:self.salt_length + self.iv_length]
            mac = combined[self.salt_length + self.iv_length:self.salt_length + self.iv_length + 32]
            ciphertext = combined[self.salt_length + self.iv_length + 32:]
            
            # Verify HMAC
            auth_key = self._derive_key(self.master_key + "_auth", salt)
            h = hmac.new(auth_key, salt + iv + ciphertext, hashlib.sha256)
            expected_mac = h.digest()
            
            return hmac.compare_digest(mac, expected_mac)
            
        except Exception as e:
            logger.error(f"Integrity verification failed: {e}")
            return False
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.
        
        Args:
            length: Length of token in bytes
            
        Returns:
            str: Secure random token (hex encoded)
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def hash_data(data: str, salt: Optional[str] = None) -> str:
        """
        Create a secure hash of data.
        
        Args:
            data: Data to hash
            salt: Optional salt (generated if not provided)
            
        Returns:
            str: Hash in format "salt:hash"
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Create hash
        combined = (data + salt).encode('utf-8')
        hash_value = hashlib.sha256(combined).hexdigest()
        
        return f"{salt}:{hash_value}"
    
    @staticmethod
    def verify_hash(data: str, hashed: str) -> bool:
        """
        Verify data against a hash.
        
        Args:
            data: Original data
            hashed: Hash in format "salt:hash"
            
        Returns:
            bool: True if data matches hash, False otherwise
        """
        try:
            salt, expected_hash = hashed.split(':', 1)
            actual_hash = EncryptionService.hash_data(data, salt)
            return hmac.compare_digest(hashed, actual_hash)
        except Exception:
            return False


# Singleton instance for global use
_encryption_service = None


def get_encryption_service(master_key: Optional[str] = None) -> EncryptionService:
    """
    Get singleton encryption service instance.
    
    Args:
        master_key: Optional master key for first initialization
        
    Returns:
        EncryptionService: Singleton instance
    """
    global _encryption_service
    
    if _encryption_service is None:
        _encryption_service = EncryptionService(master_key)
    
    return _encryption_service


def reset_encryption_service():
    """Reset the singleton encryption service (mainly for testing)."""
    global _encryption_service
    _encryption_service = None


# Add hardware fingerprint methods to EncryptionService
def _encryption_service_add_fingerprint_methods():
    def get_hardware_fingerprint(self) -> str:
        """
        Get hardware fingerprint for this machine.

        Returns:
            str: Hardware fingerprint
        """
        return self._generate_hardware_fingerprint()

    def _generate_hardware_fingerprint(self) -> str:
        """
        Generate a hardware fingerprint for this machine.

        Returns:
            str: Hardware fingerprint hash
        """
        import platform
        import uuid
        import json
        import hashlib

        # Collect system information
        system_info = {
            'platform': platform.platform(),
            'processor': platform.processor(),
            'machine': platform.machine(),
            'node': platform.node(),
        }

        # Try to get MAC address
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff)
                           for i in range(0, 48, 8)][::-1])
            system_info['mac'] = mac
        except:
            pass

        # Create a hash of the system information
        info_string = json.dumps(system_info, sort_keys=True)
        fingerprint = hashlib.sha256(info_string.encode()).hexdigest()

        return fingerprint[:32]  # Use first 32 characters

    EncryptionService.get_hardware_fingerprint = get_hardware_fingerprint
    EncryptionService._generate_hardware_fingerprint = _generate_hardware_fingerprint

_encryption_service_add_fingerprint_methods()