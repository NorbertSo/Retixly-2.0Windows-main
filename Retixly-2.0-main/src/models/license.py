"""
License model for Retixly application.

This module contains classes for managing local license validation and caching.
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import hashlib
import platform
import uuid
from .subscription import Subscription, SubscriptionPlan, SubscriptionStatus


class LicenseStatus(Enum):
    """Enum representing possible license statuses."""
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"
    UNVERIFIED = "unverified"
    GRACE_PERIOD = "grace_period"
    OFFLINE_VALID = "offline_valid"


class LicenseType(Enum):
    """Enum representing license types."""
    FREE = "free"
    PRO = "pro"
    TRIAL = "trial"


class License:
    """
    Model representing a local license cache.
    
    This class manages local license validation, offline access,
    and hardware fingerprinting for security.
    """
    
    def __init__(self,
                 license_id: Optional[str] = None,
                 license_type: LicenseType = LicenseType.FREE,
                 status: LicenseStatus = LicenseStatus.VALID,
                 subscription: Optional[Subscription] = None,
                 created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None,
                 last_verified_at: Optional[datetime] = None,
                 expires_at: Optional[datetime] = None,
                 hardware_fingerprint: Optional[str] = None,
                 verification_token: Optional[str] = None,
                 offline_grace_days: int = 7,
                 max_offline_days: int = 30):
        """
        Initialize a new License instance.
        
        Args:
            license_id: Unique license identifier
            license_type: Type of license (free, pro, trial)
            status: Current license status
            subscription: Associated subscription object
            created_at: When the license was created
            updated_at: When the license was last updated
            last_verified_at: When the license was last verified online
            expires_at: When the license expires
            hardware_fingerprint: Hardware-based fingerprint for security
            verification_token: Token for online verification
            offline_grace_days: Days allowed offline before requiring verification
            max_offline_days: Maximum days allowed offline
        """
        self.license_id = license_id or str(uuid.uuid4())
        self.license_type = license_type
        self.status = status
        self.subscription = subscription or Subscription.create_free_subscription()
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.last_verified_at = last_verified_at
        self.expires_at = expires_at
        self.hardware_fingerprint = hardware_fingerprint or self._generate_hardware_fingerprint()
        self.verification_token = verification_token
        self.offline_grace_days = offline_grace_days
        self.max_offline_days = max_offline_days
    
    def _generate_hardware_fingerprint(self) -> str:
        """
        Generate a hardware fingerprint for this machine.
        
        Returns:
            str: Hardware fingerprint hash
        """
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
    
    def is_valid_hardware(self) -> bool:
        """
        Check if the license is valid for this hardware.
        
        Returns:
            bool: True if hardware matches, False otherwise
        """
        current_fingerprint = self._generate_hardware_fingerprint()
        return current_fingerprint == self.hardware_fingerprint
    
    def is_valid(self) -> bool:
        """
        Check if the license is currently valid.
        
        Returns:
            bool: True if license is valid, False otherwise
        """
        # Free licenses are always valid
        if self.license_type == LicenseType.FREE:
            return True
        
        # Check hardware fingerprint
        if not self.is_valid_hardware():
            return False
        
        # Check expiration
        if self.expires_at and self.expires_at <= datetime.now():
            return False
        
        # Check subscription validity
        if not self.subscription.is_active():
            # Check if we're in grace period
            return self.is_in_grace_period()
        
        return True
    
    def is_expired(self) -> bool:
        """
        Check if the license has expired.
        
        Returns:
            bool: True if expired, False otherwise
        """
        if self.license_type == LicenseType.FREE:
            return False
        
        return (self.expires_at is not None and 
                self.expires_at <= datetime.now())
    
    def is_in_grace_period(self) -> bool:
        """
        Check if the license is in grace period.
        
        Returns:
            bool: True if in grace period, False otherwise
        """
        if self.license_type == LicenseType.FREE:
            return False
        
        # Check subscription grace period
        if self.subscription.is_in_grace_period():
            return True
        
        # Check offline grace period
        if self.last_verified_at:
            days_offline = (datetime.now() - self.last_verified_at).days
            return days_offline <= self.offline_grace_days
        
        return False
    
    def requires_online_verification(self) -> bool:
        """
        Check if the license requires online verification.
        
        Returns:
            bool: True if verification is required, False otherwise
        """
        if self.license_type == LicenseType.FREE:
            return False
        
        # If never verified, require verification
        if not self.last_verified_at:
            return True
        
        # Check if too much time has passed since last verification
        days_since_verification = (datetime.now() - self.last_verified_at).days
        return days_since_verification >= self.offline_grace_days
    
    def can_work_offline(self) -> bool:
        """
        Check if the license can work offline.
        
        Returns:
            bool: True if can work offline, False otherwise
        """
        if self.license_type == LicenseType.FREE:
            return True
        
        if not self.last_verified_at:
            return False
        
        days_offline = (datetime.now() - self.last_verified_at).days
        return days_offline < self.max_offline_days
    
    def update_from_subscription(self, subscription: Subscription) -> None:
        """
        Update license information from subscription.
        
        Args:
            subscription: Subscription object to update from
        """
        self.subscription = subscription
        self.updated_at = datetime.now()
        self.last_verified_at = datetime.now()
        
        # Update license type based on subscription
        if subscription.plan == SubscriptionPlan.FREE:
            self.license_type = LicenseType.FREE
        elif subscription.is_trial():
            self.license_type = LicenseType.TRIAL
        else:
            self.license_type = LicenseType.PRO
        
        # Update expiration
        if subscription.ends_at:
            self.expires_at = subscription.ends_at
        elif subscription.trial_ends_at:
            self.expires_at = subscription.trial_ends_at
        
        # Update status
        if subscription.is_active():
            self.status = LicenseStatus.VALID
        elif subscription.is_expired():
            if self.is_in_grace_period():
                self.status = LicenseStatus.GRACE_PERIOD
            else:
                self.status = LicenseStatus.EXPIRED
        else:
            self.status = LicenseStatus.INVALID
    
    def mark_verification_failed(self) -> None:
        """Mark that online verification failed."""
        self.status = LicenseStatus.UNVERIFIED
        self.updated_at = datetime.now()
    
    def can_access_pro_features(self) -> bool:
        """
        Check if license allows access to pro features.
        
        Returns:
            bool: True if can access pro features, False otherwise
        """
        if self.license_type == LicenseType.FREE:
            return False
        
        return self.is_valid() or self.is_in_grace_period()
    
    def can_access_batch_processing(self) -> bool:
        """
        Check if license allows access to batch processing.
        
        Returns:
            bool: True if can access batch processing, False otherwise
        """
        return self.can_access_pro_features()
    
    def can_access_csv_xml_import(self) -> bool:
        """
        Check if license allows access to CSV/XML import.
        
        Returns:
            bool: True if can access CSV/XML import, False otherwise
        """
        return self.can_access_pro_features()
    
    def days_until_expiry(self) -> Optional[int]:
        """
        Get number of days until license expires.
        
        Returns:
            Optional[int]: Number of days until expiry, None if not applicable
        """
        if not self.expires_at:
            return None
        
        delta = self.expires_at - datetime.now()
        return max(0, delta.days)
    
    def days_since_last_verification(self) -> Optional[int]:
        """
        Get number of days since last online verification.
        
        Returns:
            Optional[int]: Days since verification, None if never verified
        """
        if not self.last_verified_at:
            return None
        
        delta = datetime.now() - self.last_verified_at
        return delta.days
    
    def get_status_message(self) -> str:
        """
        Get human-readable status message.
        
        Returns:
            str: Status message
        """
        if self.license_type == LicenseType.FREE:
            return "Free License - Single Photo Processing Available"
        
        if self.status == LicenseStatus.VALID:
            if self.license_type == LicenseType.TRIAL:
                days_left = self.days_until_expiry()
                if days_left is not None:
                    return f"Trial License - {days_left} days remaining"
                return "Trial License - Active"
            return "Pro License - Active"
        
        elif self.status == LicenseStatus.GRACE_PERIOD:
            return "License in Grace Period - Renew Soon"
        
        elif self.status == LicenseStatus.EXPIRED:
            return "License Expired - Upgrade Required"
        
        elif self.status == LicenseStatus.UNVERIFIED:
            return "License Unverified - Check Internet Connection"
        
        elif self.status == LicenseStatus.OFFLINE_VALID:
            days_offline = self.days_since_last_verification()
            if days_offline is not None:
                return f"Offline Mode - {days_offline} days since verification"
            return "Offline Mode - Active"
        
        else:
            return "Invalid License"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert license to dictionary for serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation of license
        """
        def serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
            return dt.isoformat() if dt else None
        
        return {
            'license_id': self.license_id,
            'license_type': self.license_type.value,
            'status': self.status.value,
            'subscription': self.subscription.to_dict() if self.subscription else None,
            'created_at': serialize_datetime(self.created_at),
            'updated_at': serialize_datetime(self.updated_at),
            'last_verified_at': serialize_datetime(self.last_verified_at),
            'expires_at': serialize_datetime(self.expires_at),
            'hardware_fingerprint': self.hardware_fingerprint,
            'verification_token': self.verification_token,
            'offline_grace_days': self.offline_grace_days,
            'max_offline_days': self.max_offline_days
        }
    
    def to_json(self) -> str:
        """
        Convert license to JSON string.
        
        Returns:
            str: JSON representation of license
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'License':
        """
        Create license from dictionary.
        
        Args:
            data: Dictionary containing license data
            
        Returns:
            License: New license instance
        """
        def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
            if not dt_str:
                return None
            try:
                return datetime.fromisoformat(dt_str)
            except (ValueError, TypeError):
                return None
        
        def parse_enum(enum_class, value):
            if not value:
                return None
            try:
                return enum_class(value)
            except ValueError:
                return None
        
        # Parse subscription
        subscription = None
        if data.get('subscription'):
            from .subscription import Subscription
            subscription = Subscription.from_dict(data['subscription'])
        
        return cls(
            license_id=data.get('license_id'),
            license_type=parse_enum(LicenseType, data.get('license_type')) or LicenseType.FREE,
            status=parse_enum(LicenseStatus, data.get('status')) or LicenseStatus.VALID,
            subscription=subscription,
            created_at=parse_datetime(data.get('created_at')),
            updated_at=parse_datetime(data.get('updated_at')),
            last_verified_at=parse_datetime(data.get('last_verified_at')),
            expires_at=parse_datetime(data.get('expires_at')),
            hardware_fingerprint=data.get('hardware_fingerprint'),
            verification_token=data.get('verification_token'),
            offline_grace_days=data.get('offline_grace_days', 7),
            max_offline_days=data.get('max_offline_days', 30)
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'License':
        """
        Create license from JSON string.
        
        Args:
            json_str: JSON string containing license data
            
        Returns:
            License: New license instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def create_free_license(cls) -> 'License':
        """
        Create a free license instance.
        
        Returns:
            License: Free license instance
        """
        return cls(
            license_type=LicenseType.FREE,
            status=LicenseStatus.VALID,
            subscription=Subscription.create_free_subscription()
        )
    
    def __str__(self) -> str:
        """String representation of license."""
        return f"License(type={self.license_type.value}, status={self.status.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation of license."""
        return (f"License(id={self.license_id}, type={self.license_type}, "
                f"status={self.status}, valid={self.is_valid()})")
