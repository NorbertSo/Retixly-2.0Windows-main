"""
Subscription model for Retixly application.

This module contains classes for managing user subscriptions through LemonSqueezy.
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json


class SubscriptionStatus(Enum):
    """Enum representing possible subscription statuses."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    TRIALING = "trialing"
    PAUSED = "paused"


class SubscriptionPlan(Enum):
    """Enum representing available subscription plans."""
    FREE = "free"
    PRO_MONTHLY = "pro_monthly"
    PRO_YEARLY = "pro_yearly"


class Subscription:
    """
    Model representing a user subscription.
    
    This class handles all subscription-related data and provides methods
    for checking subscription validity and features access.
    """
    
    def __init__(self, 
                 subscription_id: Optional[str] = None,
                 plan: SubscriptionPlan = SubscriptionPlan.FREE,
                 status: SubscriptionStatus = SubscriptionStatus.INACTIVE,
                 customer_id: Optional[str] = None,
                 customer_email: Optional[str] = None,
                 product_id: Optional[str] = None,
                 variant_id: Optional[str] = None,
                 created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None,
                 trial_ends_at: Optional[datetime] = None,
                 billing_anchor: Optional[int] = None,
                 urls: Optional[Dict[str, str]] = None,
                 renews_at: Optional[datetime] = None,
                 ends_at: Optional[datetime] = None,
                 price: Optional[float] = None,
                 currency: str = "USD"):
        """
        Initialize a new Subscription instance.
        
        Args:
            subscription_id: Unique subscription ID from LemonSqueezy
            plan: The subscription plan type
            status: Current subscription status
            customer_id: LemonSqueezy customer ID
            customer_email: Customer email address
            product_id: LemonSqueezy product ID
            variant_id: LemonSqueezy variant ID
            created_at: When the subscription was created
            updated_at: When the subscription was last updated
            trial_ends_at: When the trial period ends
            billing_anchor: Day of month for billing
            urls: Dictionary containing update_payment_method and customer_portal URLs
            renews_at: When the subscription renews
            ends_at: When the subscription ends
            price: Subscription price
            currency: Currency code
        """
        self.subscription_id = subscription_id
        self.plan = plan
        self.status = status
        self.customer_id = customer_id
        self.customer_email = customer_email
        self.product_id = product_id
        self.variant_id = variant_id
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.trial_ends_at = trial_ends_at
        self.billing_anchor = billing_anchor
        self.urls = urls or {}
        self.renews_at = renews_at
        self.ends_at = ends_at
        self.price = price
        self.currency = currency
        
    def is_active(self) -> bool:
        """
        Check if the subscription is currently active.
        
        Returns:
            bool: True if subscription is active, False otherwise
        """
        if self.plan == SubscriptionPlan.FREE:
            return True
            
        active_statuses = [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING
        ]
        
        return (self.status in active_statuses and 
                (self.ends_at is None or self.ends_at > datetime.now()))
    
    def is_expired(self) -> bool:
        """
        Check if the subscription has expired.
        
        Returns:
            bool: True if subscription has expired, False otherwise
        """
        if self.plan == SubscriptionPlan.FREE:
            return False
            
        return (self.status == SubscriptionStatus.EXPIRED or 
                (self.ends_at is not None and self.ends_at <= datetime.now()))
    
    def is_in_grace_period(self) -> bool:
        """
        Check if the subscription is in grace period (recently expired but still usable).
        
        Returns:
            bool: True if in grace period, False otherwise
        """
        if not self.is_expired():
            return False
            
        # Grace period of 7 days after expiration
        grace_period = timedelta(days=7)
        if self.ends_at:
            return datetime.now() <= (self.ends_at + grace_period)
        
        return False
    
    def can_access_pro_features(self) -> bool:
        """
        Check if user can access pro features.
        
        Returns:
            bool: True if can access pro features, False otherwise
        """
        return self.is_active() or self.is_in_grace_period()
    
    def can_access_batch_processing(self) -> bool:
        """
        Check if user can access batch processing feature.
        
        Returns:
            bool: True if can access batch processing, False otherwise
        """
        return self.can_access_pro_features()
    
    def can_access_csv_xml_import(self) -> bool:
        """
        Check if user can access CSV/XML import feature.
        
        Returns:
            bool: True if can access CSV/XML import, False otherwise
        """
        return self.can_access_pro_features()
    
    def days_until_expiry(self) -> Optional[int]:
        """
        Get number of days until subscription expires.
        
        Returns:
            Optional[int]: Number of days until expiry, None if no expiry date
        """
        if not self.ends_at:
            return None
        
        delta = self.ends_at - datetime.now()
        return max(0, delta.days)
    
    def days_until_renewal(self) -> Optional[int]:
        """
        Get number of days until subscription renews.
        
        Returns:
            Optional[int]: Number of days until renewal, None if no renewal date
        """
        if not self.renews_at:
            return None
        
        delta = self.renews_at - datetime.now()
        return max(0, delta.days)
    
    def is_trial(self) -> bool:
        """
        Check if subscription is in trial period.
        
        Returns:
            bool: True if in trial, False otherwise
        """
        return (self.status == SubscriptionStatus.TRIALING and
                self.trial_ends_at is not None and
                self.trial_ends_at > datetime.now())
    
    def trial_days_remaining(self) -> Optional[int]:
        """
        Get number of trial days remaining.
        
        Returns:
            Optional[int]: Number of trial days remaining, None if not in trial
        """
        if not self.is_trial() or not self.trial_ends_at:
            return None
        
        delta = self.trial_ends_at - datetime.now()
        return max(0, delta.days)
    
    def get_plan_display_name(self) -> str:
        """
        Get human-readable plan name.
        
        Returns:
            str: Display name for the plan
        """
        plan_names = {
            SubscriptionPlan.FREE: "Free",
            SubscriptionPlan.PRO_MONTHLY: "Pro Monthly",
            SubscriptionPlan.PRO_YEARLY: "Pro Yearly"
        }
        return plan_names.get(self.plan, "Unknown")
    
    def get_status_display_name(self) -> str:
        """
        Get human-readable status name.
        
        Returns:
            str: Display name for the status
        """
        status_names = {
            SubscriptionStatus.ACTIVE: "Active",
            SubscriptionStatus.INACTIVE: "Inactive",
            SubscriptionStatus.CANCELLED: "Cancelled",
            SubscriptionStatus.EXPIRED: "Expired",
            SubscriptionStatus.PAST_DUE: "Past Due",
            SubscriptionStatus.UNPAID: "Unpaid",
            SubscriptionStatus.TRIALING: "Trial",
            SubscriptionStatus.PAUSED: "Paused"
        }
        return status_names.get(self.status, "Unknown")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert subscription to dictionary for serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation of subscription
        """
        def serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
            return dt.isoformat() if dt else None
        
        return {
            'subscription_id': self.subscription_id,
            'plan': self.plan.value if self.plan else None,
            'status': self.status.value if self.status else None,
            'customer_id': self.customer_id,
            'customer_email': self.customer_email,
            'product_id': self.product_id,
            'variant_id': self.variant_id,
            'created_at': serialize_datetime(self.created_at),
            'updated_at': serialize_datetime(self.updated_at),
            'trial_ends_at': serialize_datetime(self.trial_ends_at),
            'billing_anchor': self.billing_anchor,
            'urls': self.urls,
            'renews_at': serialize_datetime(self.renews_at),
            'ends_at': serialize_datetime(self.ends_at),
            'price': self.price,
            'currency': self.currency
        }
    
    def to_json(self) -> str:
        """
        Convert subscription to JSON string.
        
        Returns:
            str: JSON representation of subscription
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subscription':
        """
        Create subscription from dictionary.
        
        Args:
            data: Dictionary containing subscription data
            
        Returns:
            Subscription: New subscription instance
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
        
        return cls(
            subscription_id=data.get('subscription_id'),
            plan=parse_enum(SubscriptionPlan, data.get('plan')),
            status=parse_enum(SubscriptionStatus, data.get('status')),
            customer_id=data.get('customer_id'),
            customer_email=data.get('customer_email'),
            product_id=data.get('product_id'),
            variant_id=data.get('variant_id'),
            created_at=parse_datetime(data.get('created_at')),
            updated_at=parse_datetime(data.get('updated_at')),
            trial_ends_at=parse_datetime(data.get('trial_ends_at')),
            billing_anchor=data.get('billing_anchor'),
            urls=data.get('urls', {}),
            renews_at=parse_datetime(data.get('renews_at')),
            ends_at=parse_datetime(data.get('ends_at')),
            price=data.get('price'),
            currency=data.get('currency', 'USD')
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Subscription':
        """
        Create subscription from JSON string.
        
        Args:
            json_str: JSON string containing subscription data
            
        Returns:
            Subscription: New subscription instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def create_free_subscription(cls) -> 'Subscription':
        """
        Create a free subscription instance.
        
        Returns:
            Subscription: Free subscription instance
        """
        return cls(
            plan=SubscriptionPlan.FREE,
            status=SubscriptionStatus.ACTIVE,
            price=0.0
        )
    
    def __str__(self) -> str:
        """String representation of subscription."""
        return f"Subscription(plan={self.get_plan_display_name()}, status={self.get_status_display_name()})"
    
    def __repr__(self) -> str:
        """Detailed string representation of subscription."""
        return (f"Subscription(id={self.subscription_id}, plan={self.plan}, "
                f"status={self.status}, active={self.is_active()})")

    @property
    def expires_at(self) -> Optional[datetime]:
        """Alias for ends_at for backward compatibility."""
        return self.ends_at

    @property
    def lemonsqueezy_subscription_id(self) -> Optional[str]:
        """Alias for subscription_id for LemonSqueezy integration."""
        return self.subscription_id