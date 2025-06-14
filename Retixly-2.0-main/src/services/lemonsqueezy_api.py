"""
LemonSqueezy API client for Retixly application.

This module provides a client for interacting with LemonSqueezy's API
for subscription management and license verification.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import time

# Try to import requests
try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from ..models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus

logger = logging.getLogger(__name__)


class LemonSqueezyError(Exception):
    """Exception raised for LemonSqueezy API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class LemonSqueezyAPI:
    """
    Client for LemonSqueezy API interactions.
    
    Handles subscription management, license verification, and webhook processing.
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 store_id: Optional[str] = None,
                 base_url: str = "https://api.lemonsqueezy.com/v1",
                 timeout: int = 30,
                 max_retries: int = 3):
        """
        Initialize LemonSqueezy API client.
        
        Args:
            api_key: LemonSqueezy API key
            store_id: LemonSqueezy store ID
            base_url: API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        if not HAS_REQUESTS:
            raise LemonSqueezyError(
                "Requests library not available. Install with: pip install requests"
            )
        
        # Get API key from environment if not provided
        self.api_key = api_key or os.getenv('LEMONSQUEEZY_API_KEY')
        self.store_id = store_id or os.getenv('LEMONSQUEEZY_STORE_ID')
        
        if not self.api_key:
            raise LemonSqueezyError("LemonSqueezy API key is required")
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Setup session with retry strategy
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/vnd.api+json',
            'Content-Type': 'application/vnd.api+json'
        })
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Product configuration
        self.products = {
            SubscriptionPlan.PRO_MONTHLY: {
                'product_id': os.getenv('LEMONSQUEEZY_PRO_MONTHLY_PRODUCT_ID'),
                'variant_id': os.getenv('LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID')
            },
            SubscriptionPlan.PRO_YEARLY: {
                'product_id': os.getenv('LEMONSQUEEZY_PRO_YEARLY_PRODUCT_ID'),
                'variant_id': os.getenv('LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID')
            }
        }
        
        logger.info("LemonSqueezy API client initialized")
    
    def _make_request(self, 
                     method: str, 
                     endpoint: str, 
                     data: Optional[Dict] = None,
                     params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make HTTP request to LemonSqueezy API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            data: Request body data
            params: Query parameters
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            LemonSqueezyError: If request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self._make_request(method, endpoint, data, params)
            
            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {'message': response.text}
            
            # Check for errors
            if not response.ok:
                error_message = self._extract_error_message(response_data)
                logger.error(f"API request failed: {error_message} (Status: {response.status_code})")
                raise LemonSqueezyError(
                    error_message, 
                    status_code=response.status_code,
                    response_data=response_data
                )
            
            logger.debug(f"Request successful: {response.status_code}")
            return response_data
            
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            raise LemonSqueezyError("Request timeout")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error")
            raise LemonSqueezyError("Connection error - check internet connection")
        except LemonSqueezyError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise LemonSqueezyError(f"Unexpected error: {e}")
    
    def _extract_error_message(self, response_data: Dict[str, Any]) -> str:
        """
        Extract error message from API response.
        
        Args:
            response_data: API response data
            
        Returns:
            str: Error message
        """
        if 'errors' in response_data:
            errors = response_data['errors']
            if isinstance(errors, list) and errors:
                return errors[0].get('detail', 'Unknown error')
            elif isinstance(errors, dict):
                return errors.get('detail', 'Unknown error')
        
        return response_data.get('message', 'Unknown error')
    
    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """
        Get subscription details by ID.
        
        Args:
            subscription_id: LemonSqueezy subscription ID
            
        Returns:
            Optional[Subscription]: Subscription object or None if not found
        """
        try:
            logger.info(f"Fetching subscription: {subscription_id}")
            
            response = self._make_request('GET', f'subscriptions/{subscription_id}')
            
            if 'data' in response:
                return self._parse_subscription(response['data'])
            
            return None
            
        except LemonSqueezyError as e:
            if e.status_code == 404:
                logger.warning(f"Subscription not found: {subscription_id}")
                return None
            raise
    
    def get_customer_subscriptions(self, customer_email: str) -> List[Subscription]:
        """
        Get all subscriptions for a customer.
        
        Args:
            customer_email: Customer email address
            
        Returns:
            List[Subscription]: List of customer subscriptions
        """
        try:
            logger.info(f"Fetching subscriptions for customer: {customer_email}")
            
            params = {
                'filter[customer_email]': customer_email,
                'include': 'customer'
            }
            
            response = self._make_request('GET', 'subscriptions', params=params)
            
            subscriptions = []
            if 'data' in response:
                for item in response['data']:
                    subscription = self._parse_subscription(item)
                    if subscription:
                        subscriptions.append(subscription)
            
            logger.info(f"Found {len(subscriptions)} subscriptions for {customer_email}")
            return subscriptions
            
        except LemonSqueezyError:
            logger.error(f"Failed to fetch subscriptions for {customer_email}")
            return []
    
    def _parse_subscription(self, data: Dict[str, Any]) -> Optional[Subscription]:
        """
        Parse subscription data from LemonSqueezy API response.
        
        Args:
            data: Subscription data from API
            
        Returns:
            Optional[Subscription]: Parsed subscription object
        """
        try:
            attributes = data.get('attributes', {})
            
            # Parse dates
            def parse_date(date_str: Optional[str]) -> Optional[datetime]:
                if not date_str:
                    return None
                try:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    return None
            
            # Determine plan based on product/variant ID
            plan = SubscriptionPlan.FREE
            product_id = str(attributes.get('product_id', ''))
            variant_id = str(attributes.get('variant_id', ''))
            
            for plan_type, config in self.products.items():
                if (config.get('product_id') == product_id or 
                    config.get('variant_id') == variant_id):
                    plan = plan_type
                    break
            
            # Parse status
            raw_status = attributes.get('status', 'inactive')
            try:
                status = SubscriptionStatus(raw_status)
            except ValueError:
                status = SubscriptionStatus.INACTIVE
            
            return Subscription(
                subscription_id=data.get('id'),
                plan=plan,
                status=status,
                customer_id=str(attributes.get('customer_id', '')),
                customer_email=attributes.get('customer_email'),
                product_id=product_id,
                variant_id=variant_id,
                created_at=parse_date(attributes.get('created_at')),
                updated_at=parse_date(attributes.get('updated_at')),
                trial_ends_at=parse_date(attributes.get('trial_ends_at')),
                billing_anchor=attributes.get('billing_anchor'),
                urls=attributes.get('urls', {}),
                renews_at=parse_date(attributes.get('renews_at')),
                ends_at=parse_date(attributes.get('ends_at')),
                price=float(attributes.get('unit_price', 0)) / 100,  # Convert cents to dollars
                currency=attributes.get('currency', 'USD')
            )
            
        except Exception as e:
            logger.error(f"Failed to parse subscription data: {e}")
            return None
    
    def create_checkout_url(self, 
                           plan: SubscriptionPlan,
                           customer_email: Optional[str] = None,
                           custom_data: Optional[Dict] = None) -> str:
        """
        Create checkout URL for subscription purchase.
        
        Args:
            plan: Subscription plan to purchase
            customer_email: Customer email address
            custom_data: Custom data to include in checkout
            
        Returns:
            str: Checkout URL
            
        Raises:
            LemonSqueezyError: If checkout creation fails
        """
        # Problem może być tutaj - sprawdź co zwraca
        product_config = self.products.get(plan)
        if not product_config:
            print(f"❌ Brak konfiguracji dla planu: {plan}")
            return None

        variant_id = product_config.get('variant_id')
        if not variant_id:
            print(f"❌ Brak variant_id dla planu: {plan}")
            return None

        print(f"✅ Próba utworzenia checkout dla variant_id: {variant_id}")

        if plan not in self.products:
            raise LemonSqueezyError(f"Product configuration not found for plan: {plan}")
        
        product_config = self.products[plan]
        variant_id = product_config.get('variant_id')
        
        if not variant_id:
            raise LemonSqueezyError(f"Variant ID not configured for plan: {plan}")
        
        try:
            logger.info(f"Creating checkout URL for plan: {plan}")
            
            checkout_data = {
                'data': {
                    'type': 'checkouts',
                    'attributes': {
                        'product_options': {
                            'enabled_variants': [int(variant_id)],
                            'redirect_url': custom_data.get('redirect_url') if custom_data else None,
                            'receipt_link_url': custom_data.get('receipt_url') if custom_data else None,
                            'receipt_thank_you_note': custom_data.get('thank_you_note') if custom_data else None
                        },
                        'checkout_options': {
                            'embed': False,
                            'media': True,
                            'logo': True
                        },
                        'checkout_data': {
                            'email': customer_email,
                            'name': custom_data.get('customer_name') if custom_data else None,
                            'billing_address': custom_data.get('billing_address') if custom_data else None,
                            'tax_number': custom_data.get('tax_number') if custom_data else None,
                            'discount_code': custom_data.get('discount_code') if custom_data else None,
                            'custom': custom_data.get('custom_fields') if custom_data else None
                        },
                        'expires_at': (datetime.now() + timedelta(hours=1)).isoformat()
                    },
                    'relationships': {
                        'store': {
                            'data': {
                                'type': 'stores',
                                'id': self.store_id
                            }
                        },
                        'variant': {
                            'data': {
                                'type': 'variants',
                                'id': variant_id
                            }
                        }
                    }
                }
            }
            
            response = self._make_request('POST', 'checkouts', data=checkout_data)
            
            checkout_url = response.get('data', {}).get('attributes', {}).get('url')
            if not checkout_url:
                raise LemonSqueezyError("Checkout URL not returned from API")
            
            logger.info(f"Checkout URL created successfully for plan: {plan}")
            return checkout_url
            
        except LemonSqueezyError:
            raise
        except Exception as e:
            logger.error(f"Failed to create checkout URL: {e}")
            raise LemonSqueezyError(f"Failed to create checkout URL: {e}")
    
    def verify_webhook_signature(self, payload: bytes, signature: str, webhook_secret: str) -> bool:
        """
        Verify webhook signature from LemonSqueezy.
        
        Args:
            payload: Raw webhook payload
            signature: Signature from webhook headers
            webhook_secret: Webhook secret key
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            import hmac
            import hashlib
            
            expected_signature = hmac.new(
                webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Remove 'sha256=' prefix if present
            if signature.startswith('sha256='):
                signature = signature[7:]
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False
    
    def process_webhook(self, payload: Dict[str, Any]) -> Optional[Subscription]:
        """
        Process webhook payload from LemonSqueezy.
        
        Args:
            payload: Webhook payload data
            
        Returns:
            Optional[Subscription]: Updated subscription if applicable
        """
        try:
            event_name = payload.get('meta', {}).get('event_name')
            logger.info(f"Processing webhook event: {event_name}")
            
            if event_name in ['subscription_created', 'subscription_updated', 'subscription_resumed']:
                subscription_data = payload.get('data')
                if subscription_data:
                    return self._parse_subscription(subscription_data)
            
            elif event_name == 'subscription_cancelled':
                subscription_data = payload.get('data')
                if subscription_data:
                    subscription = self._parse_subscription(subscription_data)
                    if subscription:
                        subscription.status = SubscriptionStatus.CANCELLED
                    return subscription
            
            elif event_name == 'subscription_expired':
                subscription_data = payload.get('data')
                if subscription_data:
                    subscription = self._parse_subscription(subscription_data)
                    if subscription:
                        subscription.status = SubscriptionStatus.EXPIRED
                    return subscription
            
            logger.info(f"Webhook event processed: {event_name}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to process webhook: {e}")
            return None
    
    def update_subscription(self, subscription_id: str, updates: Dict[str, Any]) -> Optional[Subscription]:
        """
        Update subscription settings.
        
        Args:
            subscription_id: Subscription ID to update
            updates: Dictionary of updates to apply
            
        Returns:
            Optional[Subscription]: Updated subscription object
        """
        try:
            logger.info(f"Updating subscription: {subscription_id}")
            
            update_data = {
                'data': {
                    'type': 'subscriptions',
                    'id': subscription_id,
                    'attributes': updates
                }
            }
            
            response = self._make_request('PATCH', f'subscriptions/{subscription_id}', data=update_data)
            
            if 'data' in response:
                return self._parse_subscription(response['data'])
            
            return None
            
        except LemonSqueezyError:
            logger.error(f"Failed to update subscription: {subscription_id}")
            return None
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Subscription ID to cancel
            
        Returns:
            bool: True if cancelled successfully, False otherwise
        """
        try:
            logger.info(f"Cancelling subscription: {subscription_id}")
            
            response = self._make_request('DELETE', f'subscriptions/{subscription_id}')
            
            # Check if cancellation was successful
            if 'data' in response:
                subscription = self._parse_subscription(response['data'])
                return subscription and subscription.status == SubscriptionStatus.CANCELLED
            
            return True  # Assume success if no data returned
            
        except LemonSqueezyError:
            logger.error(f"Failed to cancel subscription: {subscription_id}")
            return False
    
    def resume_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """
        Resume a cancelled subscription.
        
        Args:
            subscription_id: Subscription ID to resume
            
        Returns:
            Optional[Subscription]: Resumed subscription object
        """
        try:
            logger.info(f"Resuming subscription: {subscription_id}")
            
            response = self._make_request('PATCH', f'subscriptions/{subscription_id}/resume')
            
            if 'data' in response:
                return self._parse_subscription(response['data'])
            
            return None
            
        except LemonSqueezyError:
            logger.error(f"Failed to resume subscription: {subscription_id}")
            return None
    
    def get_customer_portal_url(self, customer_id: str) -> Optional[str]:
        """
        Get customer portal URL for subscription management.
        
        Args:
            customer_id: LemonSqueezy customer ID
            
        Returns:
            Optional[str]: Customer portal URL
        """
        try:
            logger.info(f"Getting customer portal URL for: {customer_id}")
            
            response = self._make_request('GET', f'customers/{customer_id}')
            
            customer_data = response.get('data', {})
            urls = customer_data.get('attributes', {}).get('urls', {})
            
            return urls.get('customer_portal')
            
        except LemonSqueezyError:
            logger.error(f"Failed to get customer portal URL for: {customer_id}")
            return None
    
    def validate_license_key(self, license_key: str, instance_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a license key (if using license key system).
        
        Args:
            license_key: License key to validate
            instance_id: Instance ID for activation
            
        Returns:
            Dict[str, Any]: License validation result
        """
        try:
            logger.info("Validating license key")
            
            validation_data = {
                'license_key': license_key,
                'instance_name': instance_id or 'Retixly Desktop'
            }
            
            response = self._make_request('POST', 'licenses/validate', data=validation_data)
            
            return {
                'valid': response.get('valid', False),
                'license_key': response.get('license_key', {}),
                'instance': response.get('instance', {}),
                'error': response.get('error')
            }
            
        except LemonSqueezyError as e:
            logger.error(f"License validation failed: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def get_store_info(self) -> Optional[Dict[str, Any]]:
        """
        Get store information.
        
        Returns:
            Optional[Dict[str, Any]]: Store information
        """
        try:
            if not self.store_id:
                raise LemonSqueezyError("Store ID not configured")
            
            logger.info(f"Getting store info: {self.store_id}")
            
            response = self._make_request('GET', f'stores/{self.store_id}')
            
            return response.get('data', {}).get('attributes', {})
            
        except LemonSqueezyError:
            logger.error("Failed to get store info")
            return None
    
    def get_products(self) -> List[Dict[str, Any]]:
        """
        Get all products from the store.
        
        Returns:
            List[Dict[str, Any]]: List of products
        """
        try:
            logger.info("Getting store products")
            
            params = {}
            if self.store_id:
                params['filter[store_id]'] = self.store_id
            
            response = self._make_request('GET', 'products', params=params)
            
            products = []
            if 'data' in response:
                for item in response['data']:
                    products.append({
                        'id': item.get('id'),
                        'name': item.get('attributes', {}).get('name'),
                        'description': item.get('attributes', {}).get('description'),
                        'price': item.get('attributes', {}).get('price'),
                        'status': item.get('attributes', {}).get('status')
                    })
            
            return products
            
        except LemonSqueezyError:
            logger.error("Failed to get products")
            return []
    
    def test_connection(self) -> bool:
        """
        Test API connection and authentication.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info("Testing LemonSqueezy API connection")
            
            response = self._make_request('GET', 'users/me')
            
            if 'data' in response:
                user_name = response['data'].get('attributes', {}).get('name', 'Unknown')
                logger.info(f"API connection successful. User: {user_name}")
                return True
            
            return False
            
        except LemonSqueezyError as e:
            logger.error(f"API connection test failed: {e}")
            return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get API usage statistics (if available).
        
        Returns:
            Dict[str, Any]: Usage statistics
        """
        try:
            # This endpoint might not exist in LemonSqueezy API
            # but keeping for future compatibility
            response = self._make_request('GET', 'usage')
            return response.get('data', {})
            
        except LemonSqueezyError:
            # Return empty stats if endpoint doesn't exist
            return {}
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        if hasattr(self, 'session'):
            self.session.close()


# Configuration helper
class LemonSqueezyConfig:
    """Configuration helper for LemonSqueezy integration."""
    
    @staticmethod
    def from_environment() -> Dict[str, str]:
        """
        Load configuration from environment variables.
        
        Returns:
            Dict[str, str]: Configuration dictionary
        """
        return {
            'api_key': os.getenv('LEMONSQUEEZY_API_KEY', ''),
            'store_id': os.getenv('LEMONSQUEEZY_STORE_ID', ''),
            'webhook_secret': os.getenv('LEMONSQUEEZY_WEBHOOK_SECRET', ''),
            'pro_monthly_product_id': os.getenv('LEMONSQUEEZY_PRO_MONTHLY_PRODUCT_ID', ''),
            'pro_monthly_variant_id': os.getenv('LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID', ''),
            'pro_yearly_product_id': os.getenv('LEMONSQUEEZY_PRO_YEARLY_PRODUCT_ID', ''),
            'pro_yearly_variant_id': os.getenv('LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID', '')
        }
    
    @staticmethod
    def validate_config(config: Dict[str, str]) -> List[str]:
        """
        Validate configuration and return list of missing keys.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List[str]: List of missing configuration keys
        """
        required_keys = [
            'api_key',
            'store_id',
            'pro_monthly_variant_id',
            'pro_yearly_variant_id'
        ]
        
        missing = []
        for key in required_keys:
            if not config.get(key):
                missing.append(key)
        
        return missing
    
    @staticmethod
    def is_configured() -> bool:
        """
        Check if LemonSqueezy is properly configured.
        
        Returns:
            bool: True if configured, False otherwise
        """
        config = LemonSqueezyConfig.from_environment()
        missing = LemonSqueezyConfig.validate_config(config)
        return len(missing) == 0


# Singleton instance for global use
_lemonsqueezy_api = None


def get_lemonsqueezy_api() -> Optional[LemonSqueezyAPI]:
    """
    Get singleton LemonSqueezy API instance.
    
    Returns:
        Optional[LemonSqueezyAPI]: API instance or None if not configured
    """
    global _lemonsqueezy_api
    
    if _lemonsqueezy_api is None:
        try:
            if LemonSqueezyConfig.is_configured():
                _lemonsqueezy_api = LemonSqueezyAPI()
            else:
                logger.warning("LemonSqueezy API not configured")
                return None
        except Exception as e:
            logger.error(f"Failed to initialize LemonSqueezy API: {e}")
            return None
    
    return _lemonsqueezy_api


def reset_lemonsqueezy_api():
    """Reset the singleton API instance (mainly for testing)."""
    global _lemonsqueezy_api
    _lemonsqueezy_api = None
    def create_checkout_url_v2(self, plan: SubscriptionPlan, customer_email: str = None, custom_data: dict = None) -> str:
        """Create checkout URL for subscription purchase."""
        try:
            print(f"🔍 Creating checkout for plan: {plan}")
            
            # Get variant ID
            if plan == SubscriptionPlan.PRO_MONTHLY:
                variant_id = os.getenv('LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID')
            elif plan == SubscriptionPlan.PRO_YEARLY:
                variant_id = os.getenv('LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID')
            else:
                raise LemonSqueezyError(f"Unsupported plan: {plan}")
            
            if not variant_id:
                raise LemonSqueezyError(f"Variant ID not configured for plan: {plan}")
            
            print(f"🔍 Using variant_id: {variant_id}")
            
            # Create checkout data according to LemonSqueezy API v1
            checkout_data = {
                "data": {
                    "type": "checkouts",
                    "attributes": {
                        "product_options": {
                            "enabled_variants": [int(variant_id)]
                        },
                        "checkout_options": {
                            "embed": False,
                            "media": True,
                            "logo": True
                        },
                        "checkout_data": {}
                    },
                    "relationships": {
                        "store": {
                            "data": {
                                "type": "stores",
                                "id": str(self.store_id)
                            }
                        },
                        "variant": {
                            "data": {
                                "type": "variants", 
                                "id": str(variant_id)
                            }
                        }
                    }
                }
            }
            
            # Add customer email if provided
            if customer_email:
                checkout_data["data"]["attributes"]["checkout_data"]["email"] = customer_email
            
            # Add custom data
            if custom_data:
                checkout_data["data"]["attributes"]["checkout_data"]["custom"] = custom_data
            
            print(f"🔍 Checkout data: {checkout_data}")
            
            # Make API request
            response = self._make_request('POST', 'checkouts', data=checkout_data)
            
            print(f"🔍 API Response: {response}")
            
            # Extract checkout URL
            checkout_url = response.get('data', {}).get('attributes', {}).get('url')
            
            if not checkout_url:
                raise LemonSqueezyError("Checkout URL not returned from API")
            
            print(f"✅ Checkout URL created: {checkout_url}")
            return checkout_url
            
        except Exception as e:
            print(f"❌ Error creating checkout: {e}")
            raise LemonSqueezyError(f"Failed to create checkout URL: {e}")