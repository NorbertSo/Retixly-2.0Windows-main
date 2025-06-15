# lazy_loader.py - Nowy moduł do lazy loading
import sys
import os
import logging
import importlib
from pathlib import Path
from typing import Dict, Optional, Any, Callable
from functools import wraps

logger = logging.getLogger(__name__)

class LazyComponentLoader:
    """Zaawansowany system lazy loading dla komponentów aplikacji."""
    
    def __init__(self):
        self._cached_modules = {}
        self._cached_classes = {}
        self._initialization_order = []
        self._splash_callback = None
        
    def set_splash_callback(self, callback: Callable[[str], None]):
        """Ustawia callback do aktualizacji splash screen."""
        self._splash_callback = callback
        
    def _update_splash(self, message: str):
        """Aktualizuje splash screen jeśli callback jest dostępny."""
        if self._splash_callback:
            self._splash_callback(message)
    
    def lazy_import(self, module_name: str, class_name: str = None, 
                   fallback_factory: Callable = None, 
                   critical: bool = False) -> Any:
        """
        Lazy import z obsługą fallback.
        
        Args:
            module_name: Nazwa modułu do importu
            class_name: Nazwa klasy w module (opcjonalne)
            fallback_factory: Funkcja tworząca fallback w przypadku błędu
            critical: Czy błąd importu powinien zatrzymać aplikację
        """
        cache_key = f"{module_name}.{class_name}" if class_name else module_name
        
        if cache_key in self._cached_classes:
            return self._cached_classes[cache_key]
            
        try:
            self._update_splash(f"Loading {module_name}...")
            
            # Import modułu
            if module_name in self._cached_modules:
                module = self._cached_modules[module_name]
            else:
                module = importlib.import_module(module_name)
                self._cached_modules[module_name] = module
                
            # Pobranie klasy z modułu
            if class_name:
                result = getattr(module, class_name)
            else:
                result = module
                
            self._cached_classes[cache_key] = result
            logger.info(f"✅ Lazy loaded: {cache_key}")
            return result
            
        except ImportError as e:
            error_msg = f"Failed to import {cache_key}: {e}"
            logger.error(error_msg)
            
            if critical:
                raise ImportError(f"Critical component {cache_key} failed to load: {e}")
                
            if fallback_factory:
                logger.warning(f"Using fallback for {cache_key}")
                result = fallback_factory()
                self._cached_classes[cache_key] = result
                return result
                
            # Return None for non-critical components
            return None
    
    def preload_critical_components(self) -> Dict[str, bool]:
        """Preładowuje krytyczne komponenty i zwraca status."""
        critical_components = {
            'PyQt6.QtWidgets': ['QApplication', 'QMessageBox', 'QMainWindow'],
            'PyQt6.QtCore': ['QTranslator', 'QLocale', 'Qt', 'QSettings'],
            'PyQt6.QtGui': ['QPixmap', 'QAction', 'QIcon'],
        }
        
        results = {}
        
        for module_name, classes in critical_components.items():
            try:
                self._update_splash(f"Preloading {module_name}...")
                module = importlib.import_module(module_name)
                self._cached_modules[module_name] = module
                
                for class_name in classes:
                    cache_key = f"{module_name}.{class_name}"
                    self._cached_classes[cache_key] = getattr(module, class_name)
                    
                results[module_name] = True
                logger.info(f"✅ Preloaded: {module_name}")
                
            except ImportError as e:
                results[module_name] = False
                logger.error(f"❌ Failed to preload {module_name}: {e}")
                
        return results
    
    def get_qt_classes(self) -> Dict[str, Any]:
        """Zwraca słownik z klasami Qt (kompatybilny z istniejącym kodem)."""
        qt_classes = {}
        
        qt_imports = {
            'QApplication': 'PyQt6.QtWidgets.QApplication',
            'QMessageBox': 'PyQt6.QtWidgets.QMessageBox',
            'QMainWindow': 'PyQt6.QtWidgets.QMainWindow',
            'QWidget': 'PyQt6.QtWidgets.QWidget',
            'QVBoxLayout': 'PyQt6.QtWidgets.QVBoxLayout',
            'QSplashScreen': 'PyQt6.QtWidgets.QSplashScreen',
            'QTranslator': 'PyQt6.QtCore.QTranslator',
            'QLocale': 'PyQt6.QtCore.QLocale',
            'Qt': 'PyQt6.QtCore.Qt',
            'QSettings': 'PyQt6.QtCore.QSettings',
            'QTimer': 'PyQt6.QtCore.QTimer',
            'QPixmap': 'PyQt6.QtGui.QPixmap',
            'QAction': 'PyQt6.QtGui.QAction',
            'QIcon': 'PyQt6.QtGui.QIcon',
        }
        
        for class_alias, full_path in qt_imports.items():
            module_name, class_name = full_path.rsplit('.', 1)
            qt_class = self.lazy_import(module_name, class_name, critical=True)
            qt_classes[class_alias] = qt_class
            
        return qt_classes

# Ulepszenia do głównego pliku main.py

def create_mock_settings():
    """Ulepszona wersja mock settings z lazy loading."""
    class MockSettings:
        def __init__(self):
            self.data = {
                'general.language': 'en',
                'general.theme': 'light'
            }
            logger.info("Created mock settings controller")
        
        def get_language(self):
            return self.data.get('general.language', 'en')
        
        def get_theme(self):
            return self.data.get('general.theme', 'light')
        
        def get_value(self, section, key, default=None):
            return self.data.get(f"{section}.{key}", default)
        
        def set_value(self, section, key, value):
            self.data[f"{section}.{key}"] = value
            logger.debug(f"Mock settings: {section}.{key} = {value}")
            
        def get_section(self, section):
            return {k.split('.', 1)[1]: v for k, v in self.data.items() 
                   if k.startswith(f"{section}.")}
    
    return MockSettings()

def lazy_import_with_fallback(loader: LazyComponentLoader, module_path: str, 
                            class_name: str = None, fallback=None):
    """Helper do importu z fallback."""
    try:
        return loader.lazy_import(module_path, class_name, critical=False)
    except ImportError:
        logger.warning(f"Using fallback for {module_path}.{class_name}")
        return fallback() if callable(fallback) else fallback

def improved_check_dependencies() -> tuple:
    """Ulepszona wersja check_dependencies z lazy loading."""
    required_packages = {
        'PyQt6': 'PyQt6',
        'Pillow': 'PIL', 
        'cryptography': 'cryptography',
        'requests': 'requests'
    }
    
    optional_packages_map = {
        'rembg': 'rembg',
        'numpy': 'numpy',
        'opencv-python': 'cv2',
        'boto3': 'boto3',
        'onnxruntime': 'onnxruntime'
    }
    
    missing_critical = []
    missing_optional = []
    
    # Sprawdź krytyczne pakiety
    for package_name, import_name in required_packages.items():
        try:
            importlib.import_module(import_name)
            logger.info(f"✅ Critical package {package_name} available")
        except ImportError:
            missing_critical.append(package_name)
            logger.error(f"❌ Critical package {package_name} missing")
    
    # Sprawdź opcjonalne pakiety (tylko jeśli krytyczne są dostępne)
    if not missing_critical:
        for package_name, import_name in optional_packages_map.items():
            try:
                importlib.import_module(import_name)
                logger.info(f"✅ Optional package {package_name} available")
            except ImportError:
                missing_optional.append(package_name)
                logger.warning(f"⚠️ Optional package {package_name} missing")
    
    return missing_critical, missing_optional

class LazyRetixlyApp:
    """Ulepszona wersja RetixlyApp z zaawansowanym lazy loading."""
    
    def __init__(self):
        self.loader = LazyComponentLoader()
        self.splash = None
        self.app = None
        self.main_window = None
        self.translator = None
        self.settings = None
        
        # Setup splash callback
        self.loader.set_splash_callback(self._update_splash_message)
        
        try:
            self._initialize_application()
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            self._show_critical_error("Initialization Error", str(e))
            sys.exit(1)
    
    def _update_splash_message(self, message: str):
        """Aktualizuje wiadomość na splash screen."""
        if self.splash:
            try:
                from PyQt6.QtCore import Qt
                self.splash.showMessage(
                    message, 
                    Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter
                )
                if self.app:
                    self.app.processEvents()
            except Exception as e:
                logger.warning(f"Failed to update splash: {e}")
    
    def _initialize_application(self):
        """Inicjalizuje aplikację z lazy loading."""
        # Preload critical Qt components
        self.loader.preload_critical_components()
        
        # Get Qt classes
        self.qt = self.loader.get_qt_classes()
        
        # Create QApplication
        if not sys.argv:
            sys.argv.append('')
        self.app = self.qt['QApplication'](sys.argv)
        
        # Setup application metadata
        self._setup_app_metadata()
        
        # Show splash screen
        self._show_splash_screen()
        
        # Initialize components with lazy loading
        self._init_components_lazy()
        
        # Finalize initialization
        self._finalize_initialization()
    
    def _setup_app_metadata(self):
        """Ustawia metadane aplikacji."""
        from main import APP_VERSION  # Import from main module
        
        self.app.setApplicationName("Retixly")
        self.app.setApplicationVersion(APP_VERSION)
        self.app.setOrganizationName("RetixlySoft")
        self.app.setOrganizationDomain("retixly.com")
    
    def _show_splash_screen(self):
        """Pokazuje splash screen z lazy loading."""
        splash_path = Path("assets/icons/splash.png")
        if splash_path.exists():
            try:
                splash_pixmap = self.qt['QPixmap'](str(splash_path))
                if not splash_pixmap.isNull():
                    self.splash = self.qt['QSplashScreen'](splash_pixmap)
                    self.splash.show()
                    self._update_splash_message("Initializing application...")
                    self.app.processEvents()
                else:
                    logger.warning("Splash image exists but cannot be loaded")
            except Exception as e:
                logger.warning(f"Cannot load splash screen: {e}")
    
    def _init_components_lazy(self):
        """Inicjalizuje komponenty z lazy loading."""
        # 1. Settings Controller
        self._init_settings_lazy()
        
        # 2. Main Window
        self._init_main_window_lazy()
        
        # 3. License System
        self._init_license_system_lazy()
        
        # 4. Auto-updater
        self._init_auto_updater_lazy()
        
        # 5. Image Engine
        self._init_image_engine_lazy()
    
    def _init_settings_lazy(self):
        """Lazy initialization of settings controller."""
        self._update_splash_message("Loading settings...")
        
        settings_controller = self.loader.lazy_import(
            'src.controllers.settings_controller', 
            'SettingsController',
            fallback_factory=create_mock_settings
        )
        
        if settings_controller:
            try:
                self.settings = settings_controller()
                logger.info("✅ Settings controller loaded")
            except Exception as e:
                logger.error(f"Settings controller creation failed: {e}")
                self.settings = create_mock_settings()
        else:
            self.settings = create_mock_settings()
    
    def _init_main_window_lazy(self):
        """Lazy initialization of main window."""
        self._update_splash_message("Creating main window...")
        
        main_window_class = self.loader.lazy_import(
            'src.views.main_window',
            'MainWindow'
        )
        
        if main_window_class:
            try:
                self.main_window = main_window_class(self.settings, app_instance=self)
                logger.info("✅ Main window created")
            except Exception as e:
                logger.error(f"Main window creation failed: {e}")
                self.main_window = self._create_emergency_window()
        else:
            self.main_window = self._create_emergency_window()
    
    def _init_license_system_lazy(self):
        """Lazy initialization of license system."""
        self._update_splash_message("Initializing license system...")
        
        try:
            get_license_controller = self.loader.lazy_import(
                'src.controllers.license_controller',
                'get_license_controller'
            )
            
            if get_license_controller:
                self.license_controller = get_license_controller(str(Path.cwd() / "data"))
                success = self.license_controller.initialize()
                
                if success:
                    logger.info("✅ License system initialized")
                else:
                    logger.warning("⚠️ License system initialized with warnings")
            else:
                logger.warning("⚠️ License system not available")
                
        except Exception as e:
            logger.error(f"License system initialization failed: {e}")
    
    def _init_auto_updater_lazy(self):
        """Lazy initialization of auto-updater."""
        self._update_splash_message("Setting up auto-updater...")
        
        try:
            auto_updater_class = self.loader.lazy_import(
                'src.core.updater',
                'AutoUpdater'
            )
            
            if auto_updater_class:
                from main import APP_VERSION
                self.updater = auto_updater_class(self.main_window, current_version=APP_VERSION)
                
                # Schedule update check
                self.qt['QTimer'].singleShot(
                    10000, 
                    lambda: self.updater.check_for_updates(silent=True)
                )
                logger.info("✅ Auto-updater initialized")
            else:
                logger.warning("⚠️ Auto-updater not available")
                
        except Exception as e:
            logger.error(f"Auto-updater initialization failed: {e}")
    
    def _init_image_engine_lazy(self):
        """Lazy initialization of image processing engine."""
        self._update_splash_message("Initializing image engine...")
        
        try:
            engine_manager = self.loader.lazy_import(
                'src.core.engine_manager',
                'engine_manager'
            )
            
            if engine_manager:
                engine_manager.initialize_engine(max_workers=4)
                logger.info("✅ Image engine initialized")
            else:
                logger.warning("⚠️ Image engine not available")
                
        except Exception as e:
            logger.warning(f"Image engine initialization failed: {e}")
    
    def _create_emergency_window(self):
        """Tworzy okno awaryjne."""
        from main import APP_VERSION
        
        window = self.qt['QMainWindow']()
        window.setWindowTitle(f"Retixly {APP_VERSION} - Emergency Mode")
        window.setMinimumSize(800, 600)
        
        central_widget = self.qt['QWidget']()
        layout = self.qt['QVBoxLayout'](central_widget)
        
        # Import QLabel locally
        QLabel = self.loader.lazy_import('PyQt6.QtWidgets', 'QLabel', critical=True)
        
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
        
        logger.info("Created emergency window")
        return window
    
    def _finalize_initialization(self):
        """Finalizuje inicjalizację."""
        # Hide splash and show main window
        if self.splash:
            self.splash.finish(self.main_window)
        
        self.main_window.show()
        
        # Load language and theme
        self._load_language_lazy()
        self._load_theme_lazy()
        
        # Create menu bar
        self._create_menu_bar_lazy()
    
    def _load_language_lazy(self):
        """Lazy loading języka."""
        try:
            locale = self.settings.get_language() if self.settings else 'en'
            
            if hasattr(self, 'translator') and self.translator:
                self.app.removeTranslator(self.translator)
            
            if locale == 'en':
                logger.info("Using default English language")
                self.translator = None
                return
            
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
    
    def _load_theme_lazy(self):
        """Lazy loading motywu."""
        try:
            theme = self.settings.get_theme() if self.settings else 'light'
            style_file = Path(f"assets/styles/{'dark' if theme == 'dark' else 'light'}.qss")
            
            if style_file.exists():
                with open(style_file, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                    self.app.setStyleSheet(stylesheet)
                    logger.info(f"✅ Loaded theme: {theme}")
            else:
                logger.warning(f"Style file not found: {style_file}")
                self._apply_default_styles()
                
        except Exception as e:
            logger.error(f"Theme loading error: {e}")
            self._apply_default_styles()
    
    def _apply_default_styles(self):
        """Aplikuje domyślne style."""
        default_style = """
        QMainWindow {
            background-color: #f5f5f5;
            color: #333333;
        }
        QPushButton {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #0056b3;
        }
        """
        self.app.setStyleSheet(default_style)
        logger.info("Applied default styles")
    
    def _create_menu_bar_lazy(self):
        """Lazy creation of menu bar."""
        try:
            if hasattr(self.main_window, 'menuBar'):
                menu_bar = self.main_window.menuBar()
                menu_bar.clear()
                
                # Create Help menu
                help_menu = menu_bar.addMenu("Help")
                
                # Add update check action
                check_updates_action = self.qt['QAction']("🔄 Check for Updates", self.main_window)
                if hasattr(self, 'updater'):
                    check_updates_action.triggered.connect(
                        lambda: self.updater.check_for_updates(silent=False)
                    )
                help_menu.addAction(check_updates_action)
                
                logger.info("✅ Menu bar created")
                
        except Exception as e:
            logger.error(f"Menu bar creation failed: {e}")
    
    def _show_critical_error(self, title: str, message: str):
        """Pokazuje krytyczny błąd."""
        try:
            if hasattr(self, 'qt') and self.qt:
                error_dialog = self.qt['QMessageBox']()
                error_dialog.setIcon(self.qt['QMessageBox'].Icon.Critical)
                error_dialog.setWindowTitle(title)
                error_dialog.setText(message)
                error_dialog.exec()
            else:
                print(f"CRITICAL ERROR: {title} - {message}")
        except Exception as e:
            print(f"CRITICAL ERROR (could not show dialog): {title} - {message}")
            print(f"Dialog error: {e}")
    
    def run(self):
        """Uruchamia aplikację."""
        try:
            return self.app.exec()
        except Exception as e:
            logger.error(f"Application execution error: {e}")
            self._show_critical_error("Execution Error", str(e))
            return 1
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Czyści zasoby."""
        try:
            if hasattr(self, 'license_controller'):
                self.license_controller.cleanup()
            if hasattr(self, 'updater'):
                self.updater.cleanup()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# Funkcja do zastąpienia głównej funkcji main()
def main_with_lazy_loading():
    """Główna funkcja z zaawansowanym lazy loading."""
    try:
        # Load environment config
        from main import load_environment_config, setup_environment, cleanup_temp_files
        load_environment_config()
        
        # Create minimal QApplication for dependency checking
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if not sys.argv:
                sys.argv.append('')
            temp_app = QApplication(sys.argv)
        except ImportError:
            print("CRITICAL: PyQt6 is not installed. Please run: pip install PyQt6")
            sys.exit(1)
        
        # Check dependencies with improved function
        missing_critical, missing_optional = improved_check_dependencies()
        
        if missing_critical:
            error_msg = f"Missing critical packages: {', '.join(missing_critical)}\n"
            error_msg += f"Please install: pip install {' '.join(missing_critical)}"
            
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Missing Dependencies")
            error_dialog.setText(error_msg)
            error_dialog.exec()
            sys.exit(1)
        
        if missing_optional:
            logger.warning(f"Missing optional packages: {', '.join(missing_optional)}")
        
        # Setup environment
        setup_environment()
        
        # Create and run application with lazy loading
        logger.info("🚀 Starting Retixly with lazy loading")
        
        # Cleanup temp app
        temp_app.quit()
        del temp_app
        
        # Start main application
        retixly_app = LazyRetixlyApp()
        exit_code = retixly_app.run()
        
        # Cleanup
        cleanup_temp_files()
        
        logger.info(f"Application closed with exit code: {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.critical(f"Critical application error: {e}")
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main_with_lazy_loading()