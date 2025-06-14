import os
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from PyQt6.QtCore import QObject, pyqtSignal

from ..models.subscription import Subscription, SubscriptionPlan
from ..services.lemonsqueezy_api import LemonSqueezyAPI

logger = logging.getLogger(__name__)

class SubscriptionController(QObject):
    """Kontroler zarządzania subskrypcjami - wrapper dla LemonSqueezy API."""
    
    # Sygnały
    checkout_url_generated = pyqtSignal(str)  # URL do checkout
    subscription_cancelled = pyqtSignal()
    subscription_resumed = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.api = LemonSqueezyAPI()
        self._license_controller = None  # Lazy initialization
        
        # Product IDs - te wartości powinny pochodzić z konfiguracji
        self.PRODUCT_IDS = {
            SubscriptionPlan.PRO_MONTHLY: {
                'product_id': os.getenv('LEMONSQUEEZY_PRO_MONTHLY_PRODUCT_ID'),
                'variant_id': os.getenv('LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID')
            },
            SubscriptionPlan.PRO_YEARLY: {
                'product_id': os.getenv('LEMONSQUEEZY_PRO_YEARLY_PRODUCT_ID'),
                'variant_id': os.getenv('LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID')
            }
        }
    
    @property
    def license_controller(self):
        """Lazy loading license controller to avoid circular imports."""
        if self._license_controller is None:
            from .license_controller import get_license_controller
            self._license_controller = get_license_controller()
        return self._license_controller
    
    def create_checkout_url(self, plan: SubscriptionPlan, customer_email: str = None) -> Optional[str]:
        """Tworzy URL do checkout dla wybranego planu."""
        try:
            print(f"🔍 DEBUG: Tworzenie checkout dla planu: {plan}")
            
            # Pobierz variant_id bezpośrednio z environment
            if plan == SubscriptionPlan.PRO_MONTHLY:
                variant_id = os.getenv('LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID')
                print(f"🔍 Monthly variant_id: {variant_id}")
            elif plan == SubscriptionPlan.PRO_YEARLY:
                variant_id = os.getenv('LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID')
                print(f"🔍 Yearly variant_id: {variant_id}")
            else:
                print(f"❌ Nieobsługiwany plan: {plan}")
                self.error_occurred.emit(f"Nieobsługiwany plan: {plan.value}")
                return None
            
            if not variant_id:
                print(f"❌ Brak variant_id dla planu: {plan}")
                self.error_occurred.emit("Błąd konfiguracji produktu - brak variant_id")
                return None
            
            # Utwórz prosty checkout URL
            store_name = "Retixly"  # Twoja nazwa sklepu
            checkout_url = f"https://{store_name}.lemonsqueezy.com/checkout/buy/{variant_id}"
            
            # Dodaj parametry jeśli potrzebne
            if customer_email:
                checkout_url += f"?email={customer_email}"
            
            print(f"✅ Checkout URL utworzony: {checkout_url}")
            self.checkout_url_generated.emit(checkout_url)
            return checkout_url
            
        except Exception as e:
            print(f"❌ Błąd tworzenia checkout URL: {e}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"Błąd tworzenia linku płatności: {str(e)}")
            return None
    
    def get_current_subscription_details(self) -> Optional[Dict[str, Any]]:
        """Pobiera szczegóły aktualnej subskrypcji."""
        try:
            current_subscription = self.license_controller.current_subscription
            if not current_subscription or not current_subscription.lemonsqueezy_subscription_id:
                return None
            
            # Pobierz dane z API
            subscription_data = self.api.get_subscription(
                current_subscription.lemonsqueezy_subscription_id
            )
            
            if subscription_data:
                logger.info("Pobrano szczegóły subskrypcji")
                return subscription_data
            else:
                logger.warning("Nie udało się pobrać szczegółów subskrypcji")
                return None
                
        except Exception as e:
            logger.error(f"Błąd pobierania szczegółów subskrypcji: {e}")
            self.error_occurred.emit(f"Błąd pobierania danych subskrypcji: {str(e)}")
            return None
    
    def cancel_subscription(self) -> bool:
        """Anuluje aktualną subskrypcję."""
        try:
            current_subscription = self.license_controller.current_subscription
            if not current_subscription or not current_subscription.lemonsqueezy_subscription_id:
                logger.error("Brak aktualnej subskrypcji do anulowania")
                self.error_occurred.emit("Brak aktywnej subskrypcji")
                return False
            
            # Anuluj przez API
            success = self.api.cancel_subscription(
                current_subscription.lemonsqueezy_subscription_id
            )
            
            if success:
                logger.info("Subskrypcja została anulowana")
                self.subscription_cancelled.emit()
                
                # Odśwież status licencji
                self.license_controller.force_online_verification()
                return True
            else:
                logger.error("Nie udało się anulować subskrypcji")
                self.error_occurred.emit("Nie udało się anulować subskrypcji")
                return False
                
        except Exception as e:
            logger.error(f"Błąd anulowania subskrypcji: {e}")
            self.error_occurred.emit(f"Błąd anulowania subskrypcji: {str(e)}")
            return False
    
    def resume_subscription(self) -> bool:
        """Wznawia anulowaną subskrypcję."""
        try:
            current_subscription = self.license_controller.current_subscription
            if not current_subscription or not current_subscription.lemonsqueezy_subscription_id:
                logger.error("Brak subskrypcji do wznowienia")
                self.error_occurred.emit("Brak subskrypcji do wznowienia")
                return False
            
            # Wznów przez API
            success = self.api.resume_subscription(
                current_subscription.lemonsqueezy_subscription_id
            )
            
            if success:
                logger.info("Subskrypcja została wznowiona")
                self.subscription_resumed.emit()
                
                # Odśwież status licencji
                self.license_controller.force_online_verification()
                return True
            else:
                logger.error("Nie udało się wznowić subskrypcji")
                self.error_occurred.emit("Nie udało się wznowić subskrypcji")
                return False
                
        except Exception as e:
            logger.error(f"Błąd wznawiania subskrypcji: {e}")
            self.error_occurred.emit(f"Błąd wznawiania subskrypcji: {str(e)}")
            return False
    
    def update_payment_method(self) -> Optional[str]:
        """Zwraca URL do aktualizacji metody płatności."""
        try:
            current_subscription = self.license_controller.current_subscription
            if not current_subscription or not current_subscription.lemonsqueezy_subscription_id:
                logger.error("Brak aktualnej subskrypcji")
                self.error_occurred.emit("Brak aktywnej subskrypcji")
                return None
            
            # Wygeneruj URL do customer portal
            portal_url = self.api.get_customer_portal_url(
                current_subscription.lemonsqueezy_subscription_id
            )
            
            if portal_url:
                logger.info("Wygenerowano URL do customer portal")
                return portal_url
            else:
                logger.error("Nie udało się wygenerować URL do customer portal")
                self.error_occurred.emit("Nie udało się wygenerować linku do zarządzania płatnościami")
                return None
                
        except Exception as e:
            logger.error(f"Błąd generowania URL customer portal: {e}")
            self.error_occurred.emit(f"Błąd generowania linku: {str(e)}")
            return None
    
    def handle_webhook(self, webhook_data: dict, signature: str) -> bool:
        """Obsługuje webhook z LemonSqueezy."""
        try:
            # Zweryfikuj sygnaturę
            if not self.api.verify_webhook_signature(webhook_data, signature):
                logger.error("Nieprawidłowa sygnatura webhook")
                return False
            
            # Przetwórz webhook
            processed = self.api.process_webhook(webhook_data)
            
            if processed:
                # Zaktualizuj licencję na podstawie webhook
                self.license_controller.update_subscription_from_webhook(webhook_data)
                logger.info("Webhook przetworzony pomyślnie")
                return True
            else:
                logger.warning("Webhook nie został przetworzony")
                return False
                
        except Exception as e:
            logger.error(f"Błąd obsługi webhook: {e}")
            return False
    
    def activate_subscription_from_checkout(self, subscription_id: str) -> bool:
        """Aktywuje subskrypcję po zakończeniu checkout."""
        try:
            # Aktywuj przez license controller
            success = self.license_controller.activate_subscription(subscription_id)
            
            if success:
                logger.info(f"Subskrypcja {subscription_id} została aktywowana")
                return True
            else:
                logger.error(f"Nie udało się aktywować subskrypcji {subscription_id}")
                self.error_occurred.emit("Nie udało się aktywować subskrypcji")
                return False
                
        except Exception as e:
            logger.error(f"Błąd aktywacji subskrypcji: {e}")
            self.error_occurred.emit(f"Błąd aktywacji subskrypcji: {str(e)}")
            return False
    
    def get_upgrade_options(self) -> Dict[str, Any]:
        """Zwraca dostępne opcje upgrade dla UI."""
        try:
            current_plan = (self.license_controller.current_subscription.plan 
                          if self.license_controller.current_subscription 
                          else SubscriptionPlan.FREE)
            
            options = []
            
            # Jeśli FREE, pokaż wszystkie opcje PRO
            if current_plan == SubscriptionPlan.FREE:
                options.extend([
                    {
                        'plan': SubscriptionPlan.PRO_MONTHLY,
                        'name': 'Retixly Pro Monthly',
                        'price': '$9.99/month',
                        'features': [
                            'Batch Processing (unlimited)',
                            'CSV/XML Import',
                            'Advanced Export Options',
                            'Priority Support'
                        ]
                    },
                    {
                        'plan': SubscriptionPlan.PRO_YEARLY,
                        'name': 'Retixly Pro Yearly',
                        'price': '$99.99/year',
                        'features': [
                            'Batch Processing (unlimited)',
                            'CSV/XML Import', 
                            'Advanced Export Options',
                            'Priority Support',
                            '2 months FREE!'
                        ],
                        'recommended': True
                    }
                ])
            
            # Jeśli PRO Monthly, pokaż opcję zmiany na Yearly
            elif current_plan == SubscriptionPlan.PRO_MONTHLY:
                options.append({
                    'plan': SubscriptionPlan.PRO_YEARLY,
                    'name': 'Switch to Yearly',
                    'price': '$99.99/year',
                    'features': [
                        'Same features as Monthly',
                        'Save $20 per year!'
                    ],
                    'action': 'switch'
                })
            
            return {
                'current_plan': current_plan.value,
                'options': options,
                'can_upgrade': len(options) > 0
            }
            
        except Exception as e:
            logger.error(f"Błąd pobierania opcji upgrade: {e}")
            return {
                'current_plan': 'FREE',
                'options': [],
                'can_upgrade': False
            }
    
    def test_connection(self) -> bool:
        """Testuje połączenie z LemonSqueezy API."""
        try:
            success = self.api.test_connection()
            if success:
                logger.info("Test połączenia z LemonSqueezy: OK")
            else:
                logger.error("Test połączenia z LemonSqueezy: FAILED")
                self.error_occurred.emit("Nie można połączyć z LemonSqueezy")
            return success
        except Exception as e:
            logger.error(f"Błąd testu połączenia: {e}")
            self.error_occurred.emit(f"Błąd połączenia: {str(e)}")
            return False

    def create_checkout_url_simple(self, plan: SubscriptionPlan, customer_email: str = None) -> Optional[str]:
        """Tworzy URL do checkout - wersja uproszczona."""
        try:
            print(f"🔍 Tworzenie checkout dla: {plan}")
            
            # Pobierz variant_id
            if plan == SubscriptionPlan.PRO_MONTHLY:
                variant_id = os.getenv('LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID')
                print(f"🔍 Monthly variant_id: {variant_id}")
            elif plan == SubscriptionPlan.PRO_YEARLY:
                variant_id = os.getenv('LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID')
                print(f"🔍 Yearly variant_id: {variant_id}")
            else:
                print(f"❌ Nieobsługiwany plan: {plan}")
                return None
            
            if not variant_id:
                print(f"❌ Brak variant_id dla planu: {plan}")
                return None
            
            # ZMIEŃ 'your-store' na nazwę swojego sklepu z LemonSqueezy!
            store_name = "Retixly"  # <-- ZMIEŃ TO!
            checkout_url = f"https://{store_name}.lemonsqueezy.com/checkout/buy/{variant_id}"
            
            print(f"✅ Checkout URL: {checkout_url}")
            return checkout_url
            
        except Exception as e:
            print(f"❌ Błąd: {e}")
            import traceback
            traceback.print_exc()
            return None

# Singleton instance
_subscription_controller_instance = None

def get_subscription_controller() -> SubscriptionController:
    """Zwraca singleton instancję SubscriptionController."""
    global _subscription_controller_instance
    if _subscription_controller_instance is None:
        _subscription_controller_instance = SubscriptionController()
    return _subscription_controller_instance