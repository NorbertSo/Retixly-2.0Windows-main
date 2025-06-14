import sys
import os
from pathlib import Path
import logging
import importlib
from functools import partial

if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Napraw konsole output
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('retixly.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Diagnostyka środowiska
logger.debug("Python executable: %s", sys.executable)
logger.debug("PYTHONPATH: %s", os.environ.get('PYTHONPATH'))
logger.debug("Current working directory: %s", os.getcwd())

# Dodaj katalog główny projektu do PYTHONPATH
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

# WERSJA APLIKACJI - ZMIEŃ TU PRZY KAŻDEJ NOWEJ WERSJI
APP_VERSION = "1.0.0"

def import_qt():
    """Bezpieczny import PyQt6."""
    try:
        from PyQt6.QtWidgets import (QApplication, QMessageBox, QSplashScreen,
                                   QMainWindow, QWidget, QVBoxLayout)
        from PyQt6.QtCore import QTranslator, QLocale, Qt, QSettings, QTimer
        from PyQt6.QtGui import QPixmap, QAction, QIcon
        return {
            'QApplication': QApplication,
            'QMessageBox': QMessageBox,
            'QSplashScreen': QSplashScreen,
            'QTranslator': QTranslator,
            'QLocale': QLocale,
            'Qt': Qt,
            'QPixmap': QPixmap,
            'QAction': QAction,
            'QIcon': QIcon,
            'QMainWindow': QMainWindow,
            'QWidget': QWidget,
            'QVBoxLayout': QVBoxLayout,
            'QSettings': QSettings,
            'QTimer': QTimer
        }
    except ImportError as e:
        logger.error(f"Błąd importu PyQt6: {e}")
        raise ImportError("PyQt6 nie jest zainstalowany. Użyj: pip install PyQt6")

def check_dependencies():
    """Sprawdza czy wszystkie wymagane biblioteki są zainstalowane."""
    required_packages = {
        'PyQt6': 'PyQt6',
        'Pillow': 'PIL',
        'rembg': 'rembg',
        'numpy': 'numpy',
        'opencv-python': 'cv2',
        'boto3': 'boto3',
        'requests': 'requests',
        'onnxruntime': 'onnxruntime',
        'cryptography': 'cryptography'  # Nowy wymóg dla systemu licencji
    }
    
    missing_packages = []
    optional_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            importlib.import_module(import_name)
            logger.info(f"Pakiet {package_name} załadowany pomyślnie")
        except ImportError as e:
            logger.error(f"Nie można załadować {package_name}: {e}")
            
            # Rozróżnij pakiety krytyczne od opcjonalnych
            if package_name in ['PyQt6', 'Pillow', 'cryptography', 'requests']:
                missing_packages.append(package_name)
            else:
                optional_packages.append(package_name)
            
    return missing_packages, optional_packages

def setup_environment():
    """Sprawdza i tworzy wymagane katalogi."""
    required_dirs = [
        'assets/styles',
        'assets/icons',
        'translations',
        'temp',
        'logs',
        'data'  # Katalog dla danych licencji
    ]
    
    for directory in required_dirs:
        path = Path(directory)
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Katalog {directory} utworzony/sprawdzony")
        except Exception as e:
            logger.warning(f"Nie można utworzyć katalogu {directory}: {e}")

def load_environment_config():
    """Ładuje konfigurację z pliku .env jeśli istnieje."""
    env_file = Path('.env')
    logger.debug("Szukam pliku .env w: %s", env_file.absolute())
    
    if env_file.exists():
        logger.debug("Znaleziono plik .env")
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
                        logger.debug("Załadowano: %s=...", key.strip())
            logger.info("Załadowano konfigurację z pliku .env")
        except Exception as e:
            logger.warning(f"Błąd ładowania pliku .env: {e}")
            logger.debug("BŁĄD ładowania .env: %s", e)
    else:
        logger.debug("Plik .env nie znaleziony!")
        logger.info("Plik .env nie znaleziony - używam domyślnej konfiguracji")

class RetixlyApp:
    def __init__(self):
        # Importuj klasy Qt
        self.qt = import_qt()
        self.translator = None
        try:
            # Upewnij się, że mamy argumenty dla QApplication
            if not sys.argv:
                sys.argv.append('')
                
            self.app = self.qt['QApplication'](sys.argv)
            self.app.setApplicationName("Retixly")
            self.app.setApplicationVersion(APP_VERSION)
            self.app.setOrganizationName("RetixlySoft")
            self.app.setOrganizationDomain("retixly.com")
            
            # Pokaż ekran powitalny jeśli istnieje
            self.show_splash_screen()
            
            # Inicjalizacja komponentów
            self.init_components()
            # Ustaw domyślny format QSettings na INI
            self.qt['QSettings'].setDefaultFormat(self.qt['QSettings'].Format.IniFormat)
            
            # Wczytaj język przed utworzeniem głównego okna
            self.load_language()
            
            # Inicjalizacja systemu licencji
            self.init_license_system()
            
            # *** NOWE: Inicjalizacja systemu auto-updater ***
            self.init_auto_updater()
            
            # Ukryj ekran powitalny i pokaż główne okno
            if hasattr(self, 'splash'):
                self.splash.finish(self.main_window)
            
            self.main_window.show()
            
            # Sprawdź status licencji po uruchomieniu
            self.check_license_notifications()
            
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji aplikacji: {e}")
            self.show_error_message("Błąd inicjalizacji", str(e))
            sys.exit(1)

    def init_auto_updater(self):
        """Inicjalizuje system automatycznych aktualizacji"""
        try:
            if hasattr(self, 'splash'):
                self.splash.showMessage("Inicjalizacja systemu aktualizacji...", 
                                      self.qt['Qt'].AlignmentFlag.AlignBottom | self.qt['Qt'].AlignmentFlag.AlignCenter)
                self.app.processEvents()
            
            from src.core.updater import AutoUpdater
            self.updater = AutoUpdater(self.main_window, current_version=APP_VERSION)
            
            # Sprawdź aktualizacje przy starcie (po 10 sekundach)
            self.qt['QTimer'].singleShot(10000, lambda: self.updater.check_for_updates(silent=True))
            
            logger.info(f"Auto-updater zainicjalizowany z wersją {APP_VERSION}")
            
        except Exception as e:
            logger.error(f"Błąd inicjalizacji auto-updater: {e}")
            # Kontynuuj bez auto-updater - aplikacja będzie działać normalnie
    
    def check_for_updates_manually(self):
        """Ręczne sprawdzanie aktualizacji (dla menu)"""
        try:
            if hasattr(self, 'updater'):
                self.updater.check_for_updates(silent=False)
            else:
                msg = self.qt['QMessageBox'](self.main_window)
                msg.setWindowTitle("Auto-updater niedostępny")
                msg.setText("System aktualizacji nie jest dostępny.")
                msg.exec()
        except Exception as e:
            logger.error(f"Błąd ręcznego sprawdzania aktualizacji: {e}")

    def show_splash_screen(self):
        """Pokazuje ekran powitalny jeśli istnieje."""
        splash_path = Path("assets/icons/splash.png")
        if splash_path.exists():
            try:
                splash_pixmap = self.qt['QPixmap'](str(splash_path))
                if not splash_pixmap.isNull():
                    self.splash = self.qt['QSplashScreen'](splash_pixmap)
                    self.splash.show()
                    self.splash.showMessage("Inicjalizacja aplikacji...", 
                                          self.qt['Qt'].AlignmentFlag.AlignBottom | self.qt['Qt'].AlignmentFlag.AlignCenter)
                    self.app.processEvents()
                else:
                    logger.warning("Plik splash.png istnieje ale nie można go załadować")
            except Exception as e:
                logger.warning(f"Nie można załadować ekranu powitalnego: {e}")

    def init_components(self):
        """Inicjalizacja głównych komponentów aplikacji."""
        try:
            # Bezpieczne importy wewnętrzne
            try:
                from src.controllers.settings_controller import SettingsController
                self.settings = SettingsController()
                logger.info("SettingsController załadowany pomyślnie")
            except ImportError as e:
                logger.error(f"Nie można załadować SettingsController: {e}")
                # Stwórz podstawowy mock jeśli nie można załadować
                self.settings = self.create_mock_settings()
            
            try:
                from src.views.main_window import MainWindow
                try:
                    self.main_window = MainWindow(self.settings, app_instance=self)
                except TypeError as e:
                    logger.error(f"Błąd tworzenia MainWindow (możliwy problem z sygnałami): {e}")
                    self.main_window = self.create_emergency_window()
                logger.info("MainWindow załadowany pomyślnie")
            except ImportError as e:
                logger.error(f"Nie można załadować MainWindow: {e}")
                # Stwórz podstawowe okno awaryjne
                self.main_window = self.create_emergency_window()
            
            # Translator will be initialized in load_language()
            
            # Konfiguracja aplikacji
            self.setup_application()

            # Utwórz pasek menu języka
            self.create_menu_bar()

            # Inicjalizacja silnika obrazów
            try:
                from src.core.engine_manager import engine_manager
                engine_manager.initialize_engine(max_workers=4)
                logger.info("Image engine initialized")
            except Exception as e:
                logger.warning(f"Image engine initialization failed: {e}")
                
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji komponentów: {e}")
            raise

    def init_license_system(self):
        """Inicjalizuje system licencji."""
        try:
            if hasattr(self, 'splash'):
                self.splash.showMessage("Inicjalizacja systemu licencji...", 
                                      self.qt['Qt'].AlignmentFlag.AlignBottom | self.qt['Qt'].AlignmentFlag.AlignCenter)
                self.app.processEvents()
            
            # Inicjalizuj kontroler licencji
            from src.controllers.license_controller import get_license_controller
            self.license_controller = get_license_controller(str(Path.cwd() / "data"))
            
            # Inicjalizuj kontroler - sprawdzi licencję i utworzy FREE jeśli potrzeba
            success = self.license_controller.initialize()
            
            if success:
                logger.info("System licencji zainicjalizowany pomyślnie")
                
                # Podłącz sygnały licencji
                self.license_controller.license_status_changed.connect(self.on_license_status_changed)
                self.license_controller.subscription_updated.connect(self.on_subscription_updated)
                self.license_controller.grace_period_warning.connect(self.on_grace_period_warning)
                
            else:
                logger.warning("System licencji zainicjalizowany z ostrzeżeniami - kontynuuję z licencją FREE")
                
        except Exception as e:
            logger.error(f"Błąd inicjalizacji systemu licencji: {e}")
            # Kontynuuj bez systemu licencji - aplikacja będzie działać w trybie FREE
            logger.warning("Kontynuuję bez systemu licencji - wszystkie funkcje będą dostępne")

    def check_license_notifications(self):
        """Sprawdza czy trzeba pokazać notyfikacje dotyczące licencji."""
        try:
            if not hasattr(self, 'license_controller'):
                return
                
            subscription_info = self.license_controller.get_subscription_info()
            
            # Sprawdź czy subskrypcja wygasa w ciągu 7 dni
            days_until_expiry = subscription_info.get('days_until_expiry')
            if days_until_expiry is not None and 0 < days_until_expiry <= 7:
                self.show_expiry_warning(days_until_expiry)
            
            # Sprawdź grace period
            if subscription_info.get('in_grace_period'):
                grace_days = subscription_info.get('grace_days_left', 0)
                if grace_days <= 3:
                    self.show_grace_period_warning(grace_days)
                    
        except Exception as e:
            logger.error(f"Błąd sprawdzania notyfikacji licencji: {e}")

    def show_expiry_warning(self, days_left: int):
        """Pokazuje ostrzeżenie o wygasającej subskrypcji."""
        try:
            msg = self.qt['QMessageBox'](self.main_window)
            msg.setIcon(self.qt['QMessageBox'].Icon.Warning)
            msg.setWindowTitle("Subscription Expiring Soon")
            msg.setText(f"Your Retixly Pro subscription will expire in {days_left} days.")
            msg.setInformativeText("Would you like to manage your subscription now?")
            
            msg.setStandardButtons(
                self.qt['QMessageBox'].StandardButton.Yes | 
                self.qt['QMessageBox'].StandardButton.Later
            )
            msg.setDefaultButton(self.qt['QMessageBox'].StandardButton.Later)
            
            result = msg.exec()
            if result == self.qt['QMessageBox'].StandardButton.Yes:
                # Otwórz dialog subskrypcji
                if hasattr(self.main_window, 'show_subscription_dialog'):
                    self.main_window.show_subscription_dialog()
                    
        except Exception as e:
            logger.error(f"Błąd pokazywania ostrzeżenia o wygaśnięciu: {e}")

    def show_grace_period_warning(self, days_left: int):
        """Pokazuje ostrzeżenie o grace period."""
        try:
            msg = self.qt['QMessageBox'](self.main_window)
            msg.setIcon(self.qt['QMessageBox'].Icon.Critical)
            msg.setWindowTitle("License Verification Required")
            msg.setText(f"Your license verification is required within {days_left} days.")
            msg.setInformativeText(
                "Please check your internet connection and subscription status.\n"
                "You can continue using Pro features during this grace period."
            )
            msg.exec()
        except Exception as e:
            logger.error(f"Błąd pokazywania ostrzeżenia grace period: {e}")

    def on_license_status_changed(self, status):
        """Obsługuje zmianę statusu licencji."""
        logger.info(f"Status licencji zmieniony na: {status}")
        
    def on_subscription_updated(self, subscription):
        """Obsługuje aktualizację subskrypcji."""
        logger.info(f"Subskrypcja zaktualizowana: {subscription.plan.value}")
        
    def on_grace_period_warning(self, days_left):
        """Obsługuje ostrzeżenie grace period."""
        if days_left <= 1:  # Krytyczne ostrzeżenie
            self.show_grace_period_warning(days_left)

    def create_mock_settings(self):
        """Tworzy podstawowy mock settings controlera."""
        class MockSettings:
            def __init__(self):
                self.data = {}
            
            def get_language(self):
                return 'en'
            
            def get_theme(self):
                return 'light'
            
            def get_value(self, section, key, default=None):
                return self.data.get(f"{section}.{key}", default)
            
            def set_value(self, section, key, value):
                self.data[f"{section}.{key}"] = value
                
            def get_section(self, section):
                return {}
        
        logger.info("Używam mock settings controlera")
        return MockSettings()

    def create_emergency_window(self):
        """Tworzy podstawowe okno awaryjne."""
        from PyQt6.QtWidgets import QLabel
        window = self.qt['QMainWindow']()
        window.setWindowTitle(f"Retixly {APP_VERSION} - Emergency Mode")
        window.setMinimumSize(800, 600)
        
        central_widget = self.qt['QWidget']()
        layout = self.qt['QVBoxLayout'](central_widget)
        
        label = QLabel(f"""
        <h1>Retixly {APP_VERSION} - Emergency Mode</h1>
        <p>The application is running in emergency mode due to missing components.</p>
        <p>Please check the installation and ensure all required files are present.</p>
        <br>
        <p><b>Missing components will be loaded as they become available.</b></p>
        """)
        label.setStyleSheet("""
            QLabel {
                color: #333333;
                background-color: #f8f9fa;
                padding: 30px;
                border-radius: 10px;
                font-size: 14px;
            }
        """)
        layout.addWidget(label)
        
        window.setCentralWidget(central_widget)
        logger.info("Utworzono okno awaryjne")
        return window

    def setup_application(self):
        """Konfiguracja ustawień aplikacji."""
        try:
            # Wczytanie języka i motywu
            self.load_language()
            self.load_theme()
            logger.info("Domyślna konfiguracja stylu i języka ustawiona")
        except Exception as e:
            logger.error(f"Błąd podczas konfiguracji aplikacji: {e}")
            # Kontynuuj z domyślnymi ustawieniami

    def load_language(self):
        """Uproszczone ładowanie języka."""
        try:
            locale = self.settings.get_language() if hasattr(self, 'settings') else 'en'

            # Usuń poprzedni translator
            if hasattr(self, 'translator') and self.translator:
                self.app.removeTranslator(self.translator)

            # Angielski = domyślny, nie potrzeba plików
            if locale == 'en':
                logger.info("Using default English language")
                self.translator = None
                return

            # Ładuj tylko jeśli nie jest angielskim
            self.translator = self.qt['QTranslator']()
            base_dir = Path(__file__).resolve().parent
            translation_file = base_dir / f"retixly_{locale}.qm"
            if not translation_file.exists():
                translation_file = base_dir / "translations" / f"retixly_{locale}.qm"

            if translation_file.exists():
                if self.translator.load(str(translation_file.absolute())):
                    self.app.installTranslator(self.translator)
                    logger.info(f"✅ Loaded translation: {locale}")
                else:
                    logger.warning(f"❌ Failed to load: {translation_file}")
                    self.translator = None
            else:
                logger.info(f"📁 Translation file not found: {translation_file}")
                self.translator = None

        except Exception as e:
            logger.error(f"Language loading error: {e}")
            self.translator = None

    def retranslate_all_widgets(self):
        """Ponownie tłumaczy wszystkie widgety w aplikacji."""
        try:
            from PyQt6.QtCore import QEvent
            from PyQt6.QtWidgets import QApplication
            language_change_event = QEvent(QEvent.Type.LanguageChange)
            for widget in QApplication.allWidgets():
                QApplication.sendEvent(widget, language_change_event)
            logger.info("Wysłano LanguageChange event do wszystkich widgetów")
        except Exception as e:
            logger.error(f"Błąd podczas retranslacji widgetów: {e}")

    def change_language_unified(self, lang_code):
        """Zmienia język aplikacji - POPRAWIONA WERSJA."""
        try:
            # Zapisz ustawienie języka
            if hasattr(self, "settings"):
                self.settings.set_value("general", "language", lang_code)

            # Usuń poprzedni translator jeśli istnieje
            if hasattr(self, 'translator') and self.translator:
                self.app.removeTranslator(self.translator)
                self.translator = None

            # Angielski = domyślny język, nie potrzeba plików
            if lang_code == 'en':
                logger.info("Switched to default English language")
                self.retranslate_all_widgets()
                self.update_language_menu_selection(lang_code)
                return

            # Dla innych języków - próbuj załadować plik tłumaczenia
            self.translator = self.qt['QTranslator']()
            base_dir = Path(__file__).resolve().parent
            translation_file = base_dir / f"retixly_{lang_code}.qm"
            if not translation_file.exists():
                translation_file = base_dir / "translations" / f"retixly_{lang_code}.qm"

            if translation_file.exists():
                if self.translator.load(str(translation_file.absolute())):
                    self.app.installTranslator(self.translator)
                    logger.info(f"✅ Language switched to: {lang_code}")
                else:
                    logger.warning(f"❌ Failed to load translation: {translation_file}")
                    self.translator = None
            else:
                logger.info(f"📁 Translation file not found: {translation_file}")
                logger.info("Staying with default English")
                self.translator = None

            # Przetłumacz interfejs
            self.retranslate_all_widgets()
            self.update_language_menu_selection(lang_code)

            # Opcjonalnie: pokaż komunikat o zmianie języka
            if hasattr(self, 'main_window'):
                self.main_window.statusBar().showMessage(f"Language changed to: {lang_code}", 3000)

        except Exception as e:
            logger.error(f"Error changing language: {e}")
            # W przypadku błędu - przywróć angielski
            if hasattr(self, 'translator') and self.translator:
                self.app.removeTranslator(self.translator)
                self.translator = None
            if hasattr(self, "settings"):
                self.settings.set_value("general", "language", "en")

    def send_language_change_event(self):
        """Wysyła LanguageChange event do wszystkich widgetów."""
        try:
            from PyQt6.QtCore import QEvent
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            language_change_event = QEvent(QEvent.Type.LanguageChange)
            app.sendEvent(self, language_change_event)
            for widget in app.topLevelWidgets():
                app.sendEvent(widget, language_change_event)
            app.processEvents()
            logger.info("Wysłano LanguageChange event")
        except Exception as e:
            logger.error(f"Błąd wysyłania LanguageChange event: {e}")

    def update_ui_after_language_change(self):
        """Aktualizuje UI po zmianie języka."""
        try:
            self.setWindowTitle(self.get_window_title())
            self.menuBar().clear()
            self.create_menu_bar()
            if hasattr(self, 'tabs'):
                tab_titles = [
                    self.tr("Single Photo"),
                    self.tr("Batch Processing"), 
                    self.tr("CSV/XML Import")
                ]
                for i, title in enumerate(tab_titles):
                    if i < self.tabs.count():
                        self.tabs.setTabText(i, title)
            if hasattr(self, 'statusBar'):
                self.statusBar.showMessage(self.tr("Ready"))
            self.update_subscription_status_widget()
            self.retranslate_views()
        except Exception as e:
            logger.error(f"Błąd aktualizacji UI: {e}")

    def retranslate_views(self):
        """Wywołuje retranslate_ui na wszystkich widokach."""
        views = []
        if hasattr(self, 'single_photo_view') and self.single_photo_view:
            views.append(self.single_photo_view)
        if hasattr(self, 'batch_processing_view') and self.batch_processing_view:
            views.append(self.batch_processing_view)
        if hasattr(self, 'csv_xml_view') and self.csv_xml_view:
            views.append(self.csv_xml_view)
        for view in views:
            if hasattr(view, 'retranslate_ui'):
                try:
                    view.retranslate_ui()
                    logger.info(f"Retranslated view: {type(view).__name__}")
                except Exception as e:
                    logger.error(f"Error retranslating view {type(view).__name__}: {e}")
    def handle_csv_xml_processing_request(self):
        """Obsługuje żądanie przetwarzania CSV/XML."""
        try:
            if self.license_controller.can_access_csv_xml_import():
                # Użytkownik Pro - kontynuuj normalne przetwarzanie
                self.csv_xml_view.import_and_process_data()
            else:
                # Użytkownik FREE - pokaż upgrade prompt
                self.show_feature_upgrade_prompt("CSV/XML Import")
        except Exception as e:
            print(f"Error in CSV/XML processing request: {e}")
            # Fallback do upgrade prompt
            self.show_feature_upgrade_prompt("CSV/XML Import")
    def changeEvent(self, event):
        """Obsługuje LanguageChange event."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui_safe()
        super().changeEvent(event)

    def load_theme(self):
        """Wczytuje plik stylu dla wybranego motywu."""
        try:
            theme = self.settings.get_theme()
            style_file = Path(f"assets/styles/{'dark' if theme == 'dark' else 'light'}.qss")
            
            if style_file.exists():
                try:
                    with open(style_file, 'r', encoding='utf-8') as f:
                        stylesheet = f.read()
                        self.app.setStyleSheet(stylesheet)
                        logger.info(f"Załadowano motyw: {theme}")
                except Exception as e:
                    logger.error(f"Błąd wczytywania pliku stylu: {e}")
                    self.apply_default_styles()
            else:
                logger.warning(f"Nie znaleziono pliku stylu: {style_file}")
                self.apply_default_styles()
                
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania motywu: {e}")
            self.apply_default_styles()

    def apply_default_styles(self):
        """Aplikuje podstawowe style jeśli plik nie istnieje."""
        default_style = """
        QMainWindow {
            background-color: #f5f5f5;
            color: #333333;
        }
        QLabel {
            color: #333333;
            background-color: transparent;
        }
        QPushButton {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #0056b3;
        }
        QPushButton:disabled {
            background-color: #e9ecef;
            color: #6c757d;
        }
        QComboBox QAbstractItemView {
            background: white;
            color: #333333;
        }
        """
        self.app.setStyleSheet(default_style)
        logger.info("Zastosowano domyślne style")

    def create_menu_bar(self):
        """Tworzy pasek menu z wyborem języka i opcjami aktualizacji."""
        if not hasattr(self, "main_window"):
            return
        # Dostępne języki
        languages = [
            {"code": "en", "name": "English", "flag": "🇺🇸"},
            {"code": "pl", "name": "Polski", "flag": "🇵🇱"},
            {"code": "de", "name": "Deutsch", "flag": "🇩🇪"},
            {"code": "es", "name": "Español", "flag": "🇪🇸"},
            # Dodaj inne języki jeśli chcesz
        ]
        main_window = self.main_window
        menu_bar = main_window.menuBar() if hasattr(main_window, "menuBar") else None
        if not menu_bar:
            return
        
        # Usuń istniejące menu (jeśli istnieje)
        menu_bar.clear()
        
        # Menu Help/Pomoc
        help_menu = menu_bar.addMenu("Help")
        
        # Akcja sprawdzania aktualizacji
        check_updates_action = self.qt['QAction']("🔄 Check for Updates", main_window)
        check_updates_action.triggered.connect(self.check_for_updates_manually)
        help_menu.addAction(check_updates_action)
        
        # Separator
        help_menu.addSeparator()
        
        # Informacje o wersji
        about_action = self.qt['QAction'](f"ℹ️ About Retixly {APP_VERSION}", main_window)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
        # Utwórz menu języka
        language_menu = menu_bar.addMenu("Language")
        # Przechowuj akcje językowe
        self.language_actions = {}
        current_lang = self.settings.get_language() if hasattr(self, "settings") else "en"
        for lang in languages:
            action = self.qt['QAction'](f"{lang['flag']} {lang['name']}", main_window)
            action.setCheckable(True)
            action.setChecked(lang["code"] == current_lang)
            action.triggered.connect(partial(self.change_language_safe, lang["code"]))
            language_menu.addAction(action)
            self.language_actions[lang["code"]] = action
        language_menu.setTitle("Language")
        # Zapamiętaj menu do retranslacji
        self._language_menu = language_menu
        self._help_menu = help_menu

    def show_about_dialog(self):
        """Pokazuje dialog z informacjami o aplikacji."""
        try:
            msg = self.qt['QMessageBox'](self.main_window)
            msg.setWindowTitle("About Retixly")
            msg.setIcon(self.qt['QMessageBox'].Icon.Information)
            msg.setText(f"<h2>Retixly {APP_VERSION}</h2>")
            msg.setInformativeText(
                f"<p><b>Version:</b> {APP_VERSION}</p>"
                "<p><b>Developer:</b> RetixlySoft</p>"
                "<p><b>License:</b> MIT License</p>"
                "<br>"
                "<p>Advanced AI-powered background removal tool</p>"
                "<p>Built with PyQt6 and modern AI models</p>"
            )
            msg.setStandardButtons(self.qt['QMessageBox'].StandardButton.Ok)
            msg.exec()
        except Exception as e:
            logger.error(f"Błąd pokazywania dialogu About: {e}")

    def change_language_safe(self, lang_code):
        """Bezpieczna zmiana języka - POPRAWIONA."""
        try:
            logger.info(f"🌍 Changing language to: {lang_code}")
            logger.info(f"🔍 Available language actions: {list(self.language_actions.keys()) if hasattr(self, 'language_actions') else 'None'}")
            
            # Zapisz ustawienie
            if hasattr(self, "settings"):
                self.settings.set_value("general", "language", lang_code)
            
            # POPRAWKA: Zawsze usuń translator przed zmianą
            if hasattr(self, 'translator') and self.translator:
                self.app.removeTranslator(self.translator)
            self.translator = None
            
            # Dla angielskiego - resetuj do domyślnego
            if lang_code == 'en':
                logger.info("✅ Reset to default English language")
                self.update_language_menu_selection(lang_code)
                # WAŻNE: Wywołaj retranslację dla angielskiego też!
                self.force_retranslate_ui()
                return
            
            # Dla innych języków - spróbuj załadować
            base_dir = Path(__file__).resolve().parent
            
            # Sprawdź różne lokalizacje
            possible_paths = [
                base_dir / f"retixly_{lang_code}.qm",  # główny katalog
                base_dir / "translations" / f"retixly_{lang_code}.qm",  # podkatalog
            ]
            
            translation_file = None
            for path in possible_paths:
                if path.exists():
                    translation_file = path
                    break
            
            if translation_file:
                self.translator = self.qt['QTranslator']()
                
                if self.translator.load(str(translation_file.absolute())):
                    self.app.installTranslator(self.translator)
                    logger.info(f"✅ Language switched to: {lang_code} from {translation_file}")
                else:
                    logger.warning(f"❌ Failed to load: {translation_file}")
                    self.translator = None
                    lang_code = 'en'
            else:
                logger.info(f"📁 Translation file not found for: {lang_code}")
                logger.info(f"📂 Searched in: {[str(p) for p in possible_paths]}")
                self.translator = None
                lang_code = 'en'
            
            # Aktualizuj menu
            self.update_language_menu_selection(lang_code)
            
            # ZAWSZE wywołaj retranslację
            self.force_retranslate_ui()
            
        except Exception as e:
            logger.error(f"❌ Language change error: {e}")
            # W przypadku błędu - wróć do angielskiego
            if hasattr(self, 'translator') and self.translator:
                self.app.removeTranslator(self.translator)
            self.translator = None
            self.update_language_menu_selection('en')

    def force_retranslate_ui(self):
        """Wymusza retranslację całego UI."""
        try:
            from PyQt6.QtCore import QEvent
            from PyQt6.QtWidgets import QApplication
            
            # Wyślij tylko LanguageChange event
            language_change_event = QEvent(QEvent.Type.LanguageChange)
            QApplication.sendEvent(self.main_window, language_change_event)
            
            logger.info("✅ Forced UI retranslation completed")
            
        except Exception as e:
            logger.error(f"Error during forced retranslation: {e}")

    def update_language_menu_selection(self, lang_code):
        """Aktualizuje zaznaczenie w menu języka."""
        try:
            if hasattr(self, 'language_actions'):
                for code, action in self.language_actions.items():
                    action.setChecked(code == lang_code)
                logger.info(f"✅ Updated language menu selection to: {lang_code}")
            else:
                logger.warning("❌ language_actions not found")
        except Exception as e:
            logger.error(f"Menu update error: {e}")

    def retranslate_ui(self):
        """Aktualizuje teksty UI po zmianie języka."""
        # Przetłumacz tytuł okna
        if hasattr(self, "main_window"):
            try:
                _ = self.app.translate
            except AttributeError:
                _ = lambda context, text: text
            try:
                self.main_window.setWindowTitle(_("Retixly", f"Retixly {APP_VERSION}"))
            except Exception as e:
                logger.warning(f"Nie można ustawić tytułu głównego okna: {e}")
            # Przetłumacz menu języka jeśli istnieje
            if hasattr(self, "_language_menu"):
                self._language_menu.setTitle(_("Menu", "Language"))
            if hasattr(self, "_help_menu"):
                self._help_menu.setTitle(_("Menu", "Help"))
        # Sygnalizuj dzieciom do retranslacji jeśli mają taką metodę
        if hasattr(self, "main_window") and hasattr(self.main_window, "retranslate_ui"):
            try:
                self.main_window.retranslate_ui()
            except Exception:
                pass

    def show_error_message(self, title, message):
        """Wyświetla okno dialogowe z błędem."""
        try:
            error_dialog = self.qt['QMessageBox']()
            error_dialog.setIcon(self.qt['QMessageBox'].Icon.Critical)
            error_dialog.setWindowTitle(title)
            error_dialog.setText(message)
            error_dialog.exec()
        except Exception as e:
            logger.error(f"Nie można wyświetlić okna błędu: {e}")
            print(f"CRITICAL ERROR: {title} - {message}")

    def run(self):
        """Uruchamia główną pętlę aplikacji."""
        try:
            return self.app.exec()
        except Exception as e:
            logger.error(f"Błąd podczas wykonywania aplikacji: {e}")
            self.show_error_message("Błąd wykonania", str(e))
            return 1
        finally:
            # Czyści zasoby przy zamknięciu
            if hasattr(self, 'license_controller'):
                try:
                    self.license_controller.cleanup()
                except Exception as e:
                    logger.error(f"Błąd podczas czyszczenia licencji: {e}")
                    
            if hasattr(self, 'updater'):
                try:
                    self.updater.cleanup()
                except Exception as e:
                    logger.error(f"Błąd podczas czyszczenia auto-updater: {e}")

def main():
    """Główna funkcja aplikacji."""
    try:
        # Załaduj konfigurację środowiska
        load_environment_config()
        
        # Importuj klasy Qt
        qt = import_qt()
        
        # Upewnij się, że mamy argumenty dla QApplication
        if not sys.argv:
            sys.argv.append('')
        
        # Utworzenie QApplication przed sprawdzeniem zależności
        app = qt['QApplication'](sys.argv)
        
        # Sprawdzenie zależności
        missing_packages, optional_packages = check_dependencies()
        
        if missing_packages:
            error_msg = f"Brakujące pakiety krytyczne: {', '.join(missing_packages)}\n"
            error_msg += f"Zainstaluj je używając: pip install {' '.join(missing_packages)}"
            
            error_dialog = qt['QMessageBox']()
            error_dialog.setIcon(qt['QMessageBox'].Icon.Critical)
            error_dialog.setWindowTitle("Brakujące zależności")
            error_dialog.setText(error_msg)
            error_dialog.setDetailedText(
                "Wymagane pakiety dla pełnej funkcjonalności:\n\n"
                "• PyQt6 - interfejs użytkownika\n"
                "• Pillow - przetwarzanie obrazów\n"
                "• cryptography - system licencji\n"
                "• requests - sprawdzanie aktualizacji\n"
                "• rembg - usuwanie tła (opcjonalne)\n"
                "• numpy - operacje na obrazach (opcjonalne)\n"
                "• opencv-python - zaawansowane przetwarzanie (opcjonalne)\n"
                "• boto3 - integracja z AWS S3 (opcjonalne)\n"
                "• onnxruntime - modele AI dla rembg (opcjonalne)"
            )
            error_dialog.exec()
            sys.exit(1)
        
        if optional_packages:
            logger.warning(f"Brakujące pakiety opcjonalne: {', '.join(optional_packages)}")
            logger.warning("Niektóre funkcje mogą być niedostępne")
            
            # Pokaż ostrzeżenie ale kontynuuj
            warning_dialog = qt['QMessageBox']()
            warning_dialog.setIcon(qt['QMessageBox'].Icon.Warning)
            warning_dialog.setWindowTitle("Brakujące pakiety opcjonalne")
            warning_dialog.setText(f"Niektóre pakiety opcjonalne nie są zainstalowane: {', '.join(optional_packages)}")
            warning_dialog.setInformativeText("Aplikacja będzie działać, ale niektóre funkcje mogą być niedostępne.")
            warning_dialog.setStandardButtons(qt['QMessageBox'].StandardButton.Ok)
            warning_dialog.exec()
        
        # Sprawdzenie i utworzenie katalogów
        setup_environment()
        
        # Uruchomienie aplikacji
        logger.info(f"🚀 Uruchamianie Retixly {APP_VERSION}")
        retixly_app = RetixlyApp()
        exit_code = retixly_app.run()
        
        # Czyszczenie plików tymczasowych
        cleanup_temp_files()
        
        logger.info("Zamykanie aplikacji - kod wyjścia: %s", exit_code)
        sys.exit(exit_code)
        
    except ImportError as e:
        print(f"CRITICAL IMPORT ERROR: {e}")
        if 'qt' in locals():
            try:
                error_dialog = qt['QMessageBox']()
                error_dialog.setIcon(qt['QMessageBox'].Icon.Critical)
                error_dialog.setWindowTitle("Błąd importu")
                error_dialog.setText(f"Nie można zaimportować wymaganych bibliotek:\n{str(e)}")
                error_dialog.exec()
            except:
                pass
        sys.exit(1)
        
    except Exception as e:
        logger.critical(f"Krytyczny błąd aplikacji: {e}")
        if 'qt' in locals():
            try:
                error_dialog = qt['QMessageBox']()
                error_dialog.setIcon(qt['QMessageBox'].Icon.Critical)
                error_dialog.setWindowTitle("Błąd krytyczny")
                error_dialog.setText(f"Wystąpił błąd podczas uruchamiania aplikacji:\n{str(e)}")
                error_dialog.setDetailedText(
                    "Możliwe przyczyny:\n"
                    "• Brakujące pliki aplikacji\n"
                    "• Problemy z uprawnieniami\n"
                    "• Uszkodzone pliki konfiguracyjne\n"
                    "• Niezgodność wersji pakietów\n\n"
                    "Spróbuj ponownie zainstalować aplikację."
                )
                error_dialog.exec()
            except:
                print(f"CRITICAL ERROR (could not show dialog): {e}")
        else:
            print(f"CRITICAL ERROR: {e}")
        sys.exit(1)

def cleanup_temp_files():
    """Czyści pliki tymczasowe."""
    try:
        temp_dir = Path('temp')
        if temp_dir.exists():
            for temp_file in temp_dir.glob('*'):
                try:
                    if temp_file.is_file():
                        temp_file.unlink()
                        logger.info(f"Usunięto plik tymczasowy: {temp_file}")
                    elif temp_file.is_dir():
                        import shutil
                        shutil.rmtree(temp_file)
                        logger.info(f"Usunięto katalog tymczasowy: {temp_file}")
                except Exception as e:
                    logger.warning(f"Nie można usunąć pliku tymczasowego {temp_file}: {e}")
    except Exception as e:
        logger.warning(f"Błąd podczas czyszczenia plików tymczasowych: {e}")

if __name__ == "__main__":
    main()