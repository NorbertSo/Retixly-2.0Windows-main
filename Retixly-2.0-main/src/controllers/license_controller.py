import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from ..models.license import License, LicenseStatus, LicenseType
from ..models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from ..services.encryption_service import get_encryption_service
from ..services.lemonsqueezy_api import LemonSqueezyAPI

logger = logging.getLogger(__name__)

class LicenseController(QObject):
    """Główny kontroler zarządzania licencją aplikacji."""
    
    # Sygnały
    license_status_changed = pyqtSignal(LicenseStatus)
    subscription_updated = pyqtSignal(Subscription)
    verification_required = pyqtSignal()
    grace_period_warning = pyqtSignal(int)  # dni pozostałe
    
    def __init__(self, app_data_dir: str = None):
        super().__init__()
        
        # **TRYB DEWELOPERSKI** - sprawdź zmienną środowiskową
        #self.dev_mode = os.getenv('DEV_MODE', 'false').lower() == 'true'
        self.dev_mode = True  # Wymuszenie trybu deweloperskiego
        if self.dev_mode:
            logger.info("🔧 DEV MODE ENABLED - All Pro features unlocked!")
            print("🔧 DEV MODE: All licensing restrictions bypassed")
        
        # Ścieżki
        self.app_data_dir = Path(app_data_dir) if app_data_dir else Path.cwd() / "data"
        self.app_data_dir.mkdir(exist_ok=True)
        self.license_file = self.app_data_dir / "license.enc"
        
        # Serwisy - tylko jeśli nie dev mode
        if not self.dev_mode:
            try:
                self.encryption_service = get_encryption_service()
                self.api = LemonSqueezyAPI()
            except Exception as e:
                logger.warning(f"Failed to initialize services in non-dev mode: {e}")
                self.encryption_service = None
                self.api = None
        else:
            self.encryption_service = None
            self.api = None
        
        # Aktualna licencja
        self._current_license: Optional[License] = None
        self._last_verification = None
        
        # Konfiguracja
        self.VERIFICATION_INTERVAL = timedelta(hours=24)
        self.GRACE_PERIOD_DAYS = 7
        
    def initialize(self) -> bool:
        """Inicjalizuje kontroler licencji przy starcie aplikacji."""
        try:
            logger.info("Inicjalizacja kontrolera licencji...")
            
            # **DEV MODE** - utwórz fałszywą licencję Pro
            if self.dev_mode:
                self.create_dev_pro_license()
                logger.info("🔧 DEV MODE: Created fake Pro license")
                return True
            
            # Załaduj licencję z pliku
            self.load_license_from_file()
            
            # Jeśli nie ma licencji, utwórz FREE
            if not self._current_license:
                self.create_free_license()
            
            # Sprawdź status licencji
            self.verify_license_status()
            
            logger.info(f"Licencja załadowana: {self._current_license.subscription.plan.value}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd inicjalizacji kontrolera licencji: {e}")
            # Fallback do FREE licencji
            self.create_free_license()
            return False
    
    def load_license_from_file(self) -> bool:
        """Ładuje licencję z zaszyfrowanego pliku lokalnego."""
        if self.dev_mode:
            return True  # Skip w dev mode
        try:
            if not self.license_file.exists():
                logger.info("Plik licencji nie istnieje")
                return False

            # Odszyfruj dane
            decrypted_data = self.encryption_service.decrypt_file(str(self.license_file))

            # POPRAWKA: decrypted_data już jest dict, nie string
            if isinstance(decrypted_data, dict):
                license_data = decrypted_data
            else:
                # Jeśli jest string, sparsuj JSON
                license_data = json.loads(decrypted_data)

            # Recreate license object
            self._current_license = License.from_dict(license_data)

            logger.info("Licencja załadowana z pliku")
            return True

        except Exception as e:
            logger.error(f"Błąd ładowania licencji z pliku: {e}")
            return False
    
    def save_license_to_file(self) -> bool:
        """Zapisuje licencję do zaszyfrowanego pliku lokalnego."""
        if self.dev_mode:
            return True  # Skip w dev mode
        try:
            if not self._current_license:
                return False

            # Pobierz słownik licencji (nie serializuj do JSON)
            license_data = self._current_license.to_dict()

            # Zaszyfruj i zapisz (encryption_service sam serializuje do JSON)
            self.encryption_service.encrypt_file(str(self.license_file), license_data)

            logger.info("Licencja zapisana do pliku")
            return True

        except Exception as e:
            logger.error(f"Błąd zapisywania licencji do pliku: {e}")
            return False
    
    def create_free_license(self) -> None:
        """Tworzy darmową licencję."""
        try:
            self._current_license = License.create_free_license()
            
            # Zapisz do pliku
            self.save_license_to_file()
            
            # Emit signal
            self.license_status_changed.emit(self._current_license.status)
            
            logger.info("Utworzono darmową licencję")
            
        except Exception as e:
            logger.error(f"Błąd tworzenia darmowej licencji: {e}")

    def create_dev_pro_license(self) -> None:
        """Tworzy fałszywą licencję Pro dla trybu deweloperskiego."""
        try:
            # Utwórz fałszywą subskrypcję Pro
            fake_subscription = Subscription(
                subscription_id="dev_fake_subscription",
                plan=SubscriptionPlan.PRO_YEARLY,
                status=SubscriptionStatus.ACTIVE,
                customer_email="dev@example.com",
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=365),  # Rok ważności
                price=99.99,
                currency="USD"
            )

            # Utwórz fałszywą licencję
            self._current_license = License(
                license_id="dev_fake_license",
                license_type=LicenseType.PRO,
                status=LicenseStatus.VALID,
                subscription=fake_subscription,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=365),
                last_verified_at=datetime.now()
            )

            # Emit signal
            self.license_status_changed.emit(self._current_license.status)

            logger.info("🔧 DEV MODE: Utworzono fałszywą licencję Pro")

        except Exception as e:
            logger.error(f"Błąd tworzenia dev licencji: {e}")
            # Fallback do FREE
            self.create_free_license()
    
    def verify_license_status(self) -> bool:
        """Weryfikuje aktualny status licencji."""
        if self.dev_mode:
            return True  # W dev mode zawsze valid
        try:
            if not self._current_license:
                return False
            
            # Sprawdź czy licencja jest ważna lokalnie
            if not self._current_license.is_valid():
                logger.warning("Licencja jest nieważna lokalnie")
                self.license_status_changed.emit(LicenseStatus.EXPIRED)
                return False
            
            # Sprawdź czy wymaga weryfikacji online
            if self._current_license.requires_online_verification():
                return self.verify_online()
            
            # Sprawdź grace period
            if self._current_license.status == LicenseStatus.GRACE_PERIOD:
                days_left = self._current_license.get_grace_period_days_left()
                self.grace_period_warning.emit(days_left)
                logger.warning(f"Grace period: {days_left} dni pozostało")
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd weryfikacji statusu licencji: {e}")
            return False
    
    def verify_online(self) -> bool:
        """Przeprowadza weryfikację online z LemonSqueezy."""
        if self.dev_mode:
            return True  # W dev mode zawsze valid
        try:
            if not self._current_license or not self._current_license.subscription.lemonsqueezy_subscription_id:
                logger.warning("Brak ID subskrypcji do weryfikacji online")
                return False
            
            # Pobierz aktualną subskrypcję z API
            subscription_data = self.api.get_subscription(
                self._current_license.subscription.lemonsqueezy_subscription_id
            )
            
            if not subscription_data:
                logger.error("Nie można pobrać danych subskrypcji")
                self._enter_grace_period()
                return False
            
            # Aktualizuj subskrypcję
            updated_subscription = Subscription.from_lemonsqueezy_data(subscription_data)
            self._current_license.subscription = updated_subscription
            self._current_license.last_online_verification = datetime.now()
            
            # Sprawdź nowy status
            if updated_subscription.is_active():
                self._current_license.status = LicenseStatus.ACTIVE
                logger.info("Licencja potwierdzona online - aktywna")
            else:
                self._current_license.status = LicenseStatus.EXPIRED
                logger.warning("Licencja wygasła - potwierdzono online")
            
            # Zapisz zmiany
            self.save_license_to_file()
            self.license_status_changed.emit(self._current_license.status)
            self.subscription_updated.emit(self._current_license.subscription)
            
            return self._current_license.status == LicenseStatus.ACTIVE
            
        except Exception as e:
            logger.error(f"Błąd weryfikacji online: {e}")
            self._enter_grace_period()
            return False
    
    def _enter_grace_period(self) -> None:
        """Aktywuje grace period."""
        if self.dev_mode:
            return  # Skip w dev mode
        if self._current_license:
            self._current_license.status = LicenseStatus.GRACE_PERIOD
            if not self._current_license.grace_period_start:
                self._current_license.grace_period_start = datetime.now()
            
            self.save_license_to_file()
            self.license_status_changed.emit(LicenseStatus.GRACE_PERIOD)
            
            days_left = self._current_license.get_grace_period_days_left()
            self.grace_period_warning.emit(days_left)
            logger.warning(f"Aktywowano grace period: {days_left} dni pozostało")
    
    def update_subscription_from_webhook(self, webhook_data: dict) -> bool:
        """Aktualizuje subskrypcję na podstawie danych z webhook."""
        if self.dev_mode:
            return True  # Skip w dev mode
        try:
            if not self._current_license:
                return False
            
            # Parse webhook data
            updated_subscription = Subscription.from_lemonsqueezy_data(webhook_data)
            
            # Sprawdź czy to ta sama subskrypcja
            if (self._current_license.subscription.lemonsqueezy_subscription_id != 
                updated_subscription.lemonsqueezy_subscription_id):
                logger.warning("Webhook dla innej subskrypcji")
                return False
            
            # Aktualizuj
            self._current_license.subscription = updated_subscription
            self._current_license.last_online_verification = datetime.now()
            
            # Aktualizuj status licencji
            if updated_subscription.is_active():
                self._current_license.status = LicenseStatus.ACTIVE
            else:
                self._current_license.status = LicenseStatus.EXPIRED
            
            # Zapisz
            self.save_license_to_file()
            
            # Emit signals
            self.license_status_changed.emit(self._current_license.status)
            self.subscription_updated.emit(updated_subscription)
            
            logger.info(f"Subskrypcja zaktualizowana z webhook: {updated_subscription.status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd aktualizacji z webhook: {e}")
            return False
    
    def activate_subscription(self, lemonsqueezy_subscription_id: str) -> bool:
        """Aktywuje subskrypcję po zakupie."""
        if self.dev_mode:
            return True  # Skip w dev mode
        try:
            # Pobierz dane subskrypcji
            subscription_data = self.api.get_subscription(lemonsqueezy_subscription_id)
            if not subscription_data:
                logger.error("Nie można pobrać danych nowej subskrypcji")
                return False
            
            # Utwórz nową subskrypcję
            new_subscription = Subscription.from_lemonsqueezy_data(subscription_data)
            
            # Utwórz nową licencję
            self._current_license = License.create_pro(new_subscription)
            
            # Zapisz
            self.save_license_to_file()
            
            # Emit signals
            self.license_status_changed.emit(self._current_license.status)
            self.subscription_updated.emit(new_subscription)
            
            logger.info(f"Aktywowano subskrypcję: {new_subscription.plan.value}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd aktywacji subskrypcji: {e}")
            return False
    
    # Publiczne metody do sprawdzania uprawnień
    
    def can_access_batch_processing(self) -> bool:
        """Sprawdza czy użytkownik może korzystać z batch processing."""
        if self.dev_mode:
            return True  # 🔧 DEV MODE: zawsze TRUE
        if not self._current_license:
            return False
        return self._current_license.can_access_pro_features()
    
    def can_access_csv_xml_import(self) -> bool:
        """Sprawdza czy użytkownik może korzystać z CSV/XML import."""
        if self.dev_mode:
            return True  # 🔧 DEV MODE: zawsze TRUE
        if not self._current_license:
            return False
        return self._current_license.can_access_pro_features()
    
    def can_access_pro_features(self) -> bool:
        """Sprawdza czy użytkownik może korzystać z funkcji PRO."""
        if self.dev_mode:
            return True  # 🔧 DEV MODE: zawsze TRUE
        if not self._current_license:
            return False
        return self._current_license.can_access_pro_features()
    
    # Gettery
    
    @property
    def current_license(self) -> Optional[License]:
        """Zwraca aktualną licencję."""
        return self._current_license
    
    @property
    def current_subscription(self) -> Optional[Subscription]:
        """Zwraca aktualną subskrypcję."""
        if self._current_license:
            return self._current_license.subscription
        return None
    
    @property
    def is_pro_user(self) -> bool:
        """Sprawdza czy użytkownik ma plan PRO."""
        if self.dev_mode:
            return True  # 🔧 DEV MODE: zawsze TRUE
        if not self._current_license:
            return False
        plan = self._current_license.subscription.plan
        return plan in [SubscriptionPlan.PRO_MONTHLY, SubscriptionPlan.PRO_YEARLY]
    
    @property
    def is_free_user(self) -> bool:
        """Sprawdza czy użytkownik ma plan FREE."""
        if self.dev_mode:
            return False  # 🔧 DEV MODE: zawsze FALSE (bo jesteś Pro)
        if not self._current_license:
            return True
        return self._current_license.subscription.plan == SubscriptionPlan.FREE
    
    def get_subscription_info(self) -> dict:
        """Zwraca informacje o subskrypcji dla UI."""
        if self.dev_mode:
            return {
                'plan': 'PRO_YEARLY',
                'status': 'ACTIVE',
                'expires_at': (datetime.now() + timedelta(days=365)).isoformat(),
                'days_until_expiry': 365,
                'in_grace_period': False,
                'grace_days_left': 0
            }
        if not self._current_license:
            return {
                'plan': 'FREE',
                'status': 'ACTIVE',
                'expires_at': None,
                'days_until_expiry': None,
                'in_grace_period': False,
                'grace_days_left': 0
            }
        
        subscription = self._current_license.subscription
        return {
            'plan': subscription.plan.value,
            'status': subscription.status.value,
            'expires_at': subscription.expires_at.isoformat() if subscription.expires_at else None,
            'days_until_expiry': subscription.days_until_expiry(),
            'in_grace_period': self._current_license.status == LicenseStatus.GRACE_PERIOD,
            'grace_days_left': self._current_license.get_grace_period_days_left() if self._current_license.status == LicenseStatus.GRACE_PERIOD else 0
        }
    
    def force_online_verification(self) -> bool:
        """Wymusza weryfikację online (dla przycisków refresh)."""
        try:
            logger.info("Wymuszanie weryfikacji online...")
            return self.verify_online()
        except Exception as e:
            logger.error(f"Błąd wymuszonej weryfikacji: {e}")
            return False
    
    def cleanup(self) -> None:
        """Czyści zasoby przed zamknięciem aplikacji."""
        try:
            if self._current_license and not self.dev_mode:
                self.save_license_to_file()
            logger.info("Kontroler licencji zamknięty")
        except Exception as e:
            logger.error(f"Błąd podczas zamykania kontrolera licencji: {e}")

# Singleton instance
_license_controller_instance = None

def get_license_controller(app_data_dir: str = None) -> LicenseController:
    """Zwraca singleton instancję LicenseController."""
    global _license_controller_instance
    if _license_controller_instance is None:
        _license_controller_instance = LicenseController(app_data_dir)
    return _license_controller_instance