from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QWidget, 
                           QVBoxLayout, QMenuBar, QToolBar, QStatusBar,
                           QFileDialog, QMessageBox)
import logging
logger = logging.getLogger(__name__)
from PyQt6.QtCore import Qt, QSettings  # USUNIĘTO QThread
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTranslator, QLocale
from PyQt6.QtGui import QActionGroup
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QAction
from pathlib import Path

# Pomocnicza funkcja tłumacząca - NAJWAŻNIEJSZA ZMIANA
def tr(context, text):
    """
    Używa QApplication.translate() zamiast self.tr() dla lepszej kompatybilności.
    To rozwiązuje problemy z kontekstami w PyQt6.
    """
    return QApplication.translate(context, text)

from ..controllers.license_controller import get_license_controller
from ..models.subscription import SubscriptionPlan

# Safe imports with fallbacks
try:
    from ..views.subscription_dialog import SubscriptionDialog
except ImportError:
    SubscriptionDialog = None

try:
    from ..views.upgrade_prompts import QuickUpgradeBar, should_show_upgrade_bar, show_upgrade_prompt
except ImportError:
    QuickUpgradeBar = None
    def should_show_upgrade_bar():
        return False
    def show_upgrade_prompt(*args, **kwargs):
        QMessageBox.information(None, "Demo Mode", "Upgrade functionality not available in demo mode.")

# Importy widoków z obsługą błędów
try:
    from src.views.single_photo import SinglePhotoView
except ImportError:
    SinglePhotoView = None

try:
    from src.views.batch_processing import BatchProcessingView
except ImportError:
    BatchProcessingView = None

try:
    from src.views.csv_xml_view import CsvXmlView
except ImportError:
    CsvXmlView = None

try:
    from src.views.settings_dialog import SettingsDialog
except ImportError:
    SettingsDialog = None

class MainWindow(QMainWindow):
    def __init__(self, settings_controller, app_instance=None):
        super().__init__()
        self.settings = settings_controller
        self._app_instance = app_instance  # DODAJ TĘ LINIĘ
        self.license_controller = get_license_controller()
        self.subscription_dialog = None
        self.upgrade_bar = None
        self.translator = None
        self.language_group = None
        self.init_ui()
        self.connect_license_signals()
        self.load_saved_language()

    def tr(self, text):
        """Zastąpiona metoda tr() - używa QApplication.translate() z kontekstem MainWindow."""
        return QApplication.translate("MainWindow", text)
    def load_saved_language(self):
        """Ładuje zapisany język przy starcie aplikacji."""
        saved_lang = self.settings.get_value("general", "language", "en")
        if saved_lang != "en":
            lang_file = None
            if saved_lang == "pl":
                lang_file = "retixly_pl.qm"
            
            if lang_file:
                self.change_language(saved_lang, lang_file, save_setting=False)

    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika."""
        self.setWindowTitle(self.get_window_title())
        self.setMinimumSize(1200, 800)
        
        # Centralny widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Pasek menu
        self.create_menu_bar()
        
        # Pasek narzędzi
        self.create_toolbar()
        # Ukryj pasek narzędzi (tymczasowo wyłączony)
        if hasattr(self, 'toolbar'):
            self.toolbar.setVisible(False)
        
        # Zakładki - ZAWSZE pokazuj wszystkie
        self.tabs = QTabWidget()
        self.setup_all_tabs()
        layout.addWidget(self.tabs)

        # Pasek statusu z informacją o subskrypcji
        self.create_status_bar_with_subscription_info()
        
        # Pasek statusu
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

        # Pasek szybkiej aktualizacji (wyłączony)
        # self.setup_upgrade_bar()
        
        # Wczytanie stanu okna
        self.load_window_state()
        # Ukryj pasek narzędzi po przywróceniu stanu okna
        if hasattr(self, 'toolbar'):
            self.toolbar.setVisible(False)

    def get_window_title(self):
        title = "Retixly"
        try:
            if self.license_controller.is_pro_user:
                title += " Pro"
        except:
            pass
        return title

    def setup_all_tabs(self):
        """Konfiguracja wszystkich zakładek - zawsze dostępne, ale z kontrolą przetwarzania."""
        # Single Photo - zawsze dostępne
        if SinglePhotoView:
            self.single_photo_view = SinglePhotoView(self.settings)
            self.tabs.addTab(self.single_photo_view, self.tr("Single Photo"))

        # Batch Processing - ZAWSZE dostępne, ale z kontrolą podczas przetwarzania
        if BatchProcessingView:
            self.batch_processing_view = BatchProcessingView(self.settings)
            # Podłącz kontrolę licencji do przycisku przetwarzania
            self.connect_batch_processing_controls()
            self.tabs.addTab(self.batch_processing_view, self.tr("Batch Processing"))
        else:
            # Placeholder jeśli widok nie jest dostępny
            placeholder = self.create_info_placeholder(self.tr("Batch Processing"), self.tr("This feature is being loaded..."))
            self.tabs.addTab(placeholder, self.tr("Batch Processing"))

        # CSV/XML Import - ZAWSZE dostępne, ale z kontrolą podczas przetwarzania  
        if CsvXmlView:
            try:
                self.csv_xml_view = CsvXmlView(self.settings)
                from PyQt6.QtWidgets import QWidget
                if self.csv_xml_view is not None and isinstance(self.csv_xml_view, QWidget):
                    self.connect_csv_xml_controls()
                    self.tabs.addTab(self.csv_xml_view, self.tr("CSV/XML Import"))
                else:
                    raise TypeError("CsvXmlView is not a QWidget")
            except Exception as e:
                print(f"⚠️ Error initializing CsvXmlView: {e}")
                placeholder = self.create_info_placeholder(self.tr("CSV/XML Import"), self.tr("This feature could not be loaded."))
                self.tabs.addTab(placeholder, self.tr("CSV/XML Import"))
        else:
            placeholder = self.create_info_placeholder(self.tr("CSV/XML Import"), self.tr("This feature is being loaded..."))
            self.tabs.addTab(placeholder, self.tr("CSV/XML Import"))

    def connect_batch_processing_controls(self):
        """Podłącza kontrolę licencji do Batch Processing."""
        if hasattr(self.batch_processing_view, 'process_btn'):
            # Zastąp oryginalny handler
            try:
                self.batch_processing_view.process_btn.clicked.disconnect()
            except TypeError:
                pass
            self.batch_processing_view.process_btn.clicked.connect(self.handle_batch_processing_request)
        
        # Jeśli są inne przyciski przetwarzania, też je podłącz
        if hasattr(self.batch_processing_view, 'start_processing_btn'):
            try:
                self.batch_processing_view.start_processing_btn.clicked.disconnect()
            except TypeError:
                pass
            self.batch_processing_view.start_processing_btn.clicked.connect(self.handle_batch_processing_request)
        
        # NOWA OBSŁUGA - poprawny przycisk z batch_processing.py
        if hasattr(self.batch_processing_view, 'start_batch_btn'):
            try:
                self.batch_processing_view.start_batch_btn.clicked.disconnect()
            except TypeError:
                pass
            self.batch_processing_view.start_batch_btn.clicked.connect(self.handle_batch_processing_request)

    def connect_csv_xml_controls(self):
        """Podłącza kontrolę licencji do CSV/XML Import."""
        try:
            if hasattr(self.csv_xml_view, 'import_btn'):
                try:
                    self.csv_xml_view.import_btn.clicked.disconnect()
                except (TypeError, RuntimeError):
                    pass
                self.csv_xml_view.import_btn.clicked.connect(self.handle_csv_xml_processing_request)
            else:
                print("⚠️ DEBUG: import_btn not found in csv_xml_view")
        except Exception as e:
            print(f"Error connecting CSV/XML controls: {e}")

    def handle_batch_processing_request(self):
        """Obsługuje żądanie przetwarzania wsadowego."""
        try:
            if self.license_controller.can_access_batch_processing():
                # Użytkownik Pro - kontynuuj normalne przetwarzanie
                if hasattr(self.batch_processing_view, 'start_batch'):
                    self.batch_processing_view.start_batch()
                elif hasattr(self.batch_processing_view, 'start_processing'):
                    self.batch_processing_view.start_processing()
                elif hasattr(self.batch_processing_view, 'process_images'):
                    self.batch_processing_view.process_images()
                else:
                    # Fallback - wywołaj oryginalną metodę
                    print("⚠️ DEBUG: No batch processing method found, trying fallback")
            else:
                # Użytkownik FREE - pokaż upgrade prompt
                self.show_feature_upgrade_prompt("Batch Processing")
        except Exception as e:
            print(f"Error in batch processing request: {e}")
            # Fallback do upgrade prompt
            self.show_feature_upgrade_prompt("Batch Processing")

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

    def show_feature_upgrade_prompt(self, feature_name):
        """Pokazuje atrakcyjny prompt upgrade dla konkretnej funkcji."""
        try:
            # Użyj dedykowanego upgrade prompt
            show_upgrade_prompt(feature_name=feature_name, parent=self)
        except:
            # Fallback do prostego MessageBox
            reply = QMessageBox.question(
                self,
                f"{feature_name} - Pro Feature",
                f"<h3>🚀 {feature_name} is a Pro Feature!</h3>"
                f"<p>Unlock powerful {feature_name.lower()} capabilities with Retixly Pro:</p>"
                f"<ul>"
                f"<li>✅ Unlimited batch processing</li>"
                f"<li>✅ Advanced export options</li>"
                f"<li>✅ Priority support</li>"
                f"<li>✅ Regular updates</li>"
                f"</ul>"
                f"<p><b>Ready to upgrade?</b></p>",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.show_upgrade_dialog()

    def create_info_placeholder(self, title, message):
        """Tworzy placeholder z informacją (nie upgrade prompt)."""
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
        from PyQt6.QtCore import Qt

        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        # Gradient tło
        widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #f8f9fa, stop:1 #e9ecef);
            }
        """)
        
        # Ikona
        icon_label = QLabel("⏳")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Tytuł
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 700;
                color: #212529;
                background: transparent;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Wiadomość
        message_label = QLabel(message)
        message_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #6c757d;
                background: transparent;
            }
        """)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label)
        
        widget.setLayout(layout)
        return widget

    def create_status_bar_with_subscription_info(self):
        """Tworzy pasek statusu z informacją o subskrypcji."""
        self.subscription_status_widget = self.create_subscription_status_widget()
        self.statusBar().addPermanentWidget(self.subscription_status_widget)

    def create_subscription_status_widget(self):
        """Tworzy widżet wyświetlający status subskrypcji."""
        from PyQt6.QtWidgets import QLabel
        label = QLabel()
        self.update_subscription_status_widget(label)
        return label

    def update_subscription_status_widget(self, widget=None):
        """Aktualizuje widżet statusu subskrypcji."""
        if widget is None:
            widget = self.subscription_status_widget
        
        try:
            if self.license_controller.is_pro_user:
                widget.setText(self.tr("Subscription: Pro"))
            else:
                widget.setText(self.tr("Subscription: Free"))
        except:
            widget.setText(self.tr("Subscription: Free"))

    def connect_license_signals(self):
        """Podłącza sygnały licencji do odpowiednich metod."""
        try:
            self.license_controller.license_status_changed.connect(self.on_license_status_changed)
            self.license_controller.subscription_updated.connect(self.on_subscription_updated)
            self.license_controller.grace_period_warning.connect(self.on_grace_period_warning)
        except Exception as e:
            print(f"Nie można podłączyć sygnałów licencji: {e}")

    def on_license_status_changed(self):
        """Reaguje na zmianę statusu licencji."""
        self.setWindowTitle(self.get_window_title())
        self.update_subscription_status_widget()

    def on_subscription_updated(self):
        """Reaguje na aktualizację subskrypcji."""
        self.update_subscription_status_widget()

    def on_grace_period_warning(self):
        """Wyświetla ostrzeżenie o okresie karencji."""
        QMessageBox.warning(
            self,
            self.tr("Subscription Warning"),
            self.tr("Your subscription is about to expire soon.")
        )

    def show_subscription_dialog(self):
        """Wyświetla okno dialogowe subskrypcji."""
        if SubscriptionDialog:
            if not self.subscription_dialog:
                self.subscription_dialog = SubscriptionDialog(self)
            self.subscription_dialog.show()
            self.subscription_dialog.raise_()
            self.subscription_dialog.activateWindow()
        else:
            QMessageBox.information(
                self,
                "Demo Mode",
                "Subscription management is not available in demo mode."
            )

    def show_upgrade_dialog(self):
        """Wyświetla okno dialogowe aktualizacji."""
        show_upgrade_prompt(parent=self)

    def refresh_license(self):
        """Odświeża status licencji."""
        try:
            self.license_controller.force_online_verification()
        except Exception as e:
            QMessageBox.information(
                self,
                "Demo Mode",
                f"License refresh not available in demo mode.\nError: {str(e)}"
            )

    def create_menu_bar(self):
        """Tworzenie paska menu z obsługą wyboru języka."""
        menubar = self.menuBar()

        # Menu File
        file_menu = menubar.addMenu(self.tr("File"))

        new_action = QAction(self.tr("New Project"), self)
        new_action.setShortcut("Ctrl+N")
        new_action.setStatusTip(self.tr("Create a new project"))
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction(self.tr("Open"), self)
        open_action.setShortcut("Ctrl+O")
        open_action.setStatusTip(self.tr("Open an existing project"))
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        save_action = QAction(self.tr("Save"), self)
        save_action.setShortcut("Ctrl+S")
        save_action.setStatusTip(self.tr("Save the current project"))
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction(self.tr("Save As..."), self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.setStatusTip(self.tr("Save the project with a new name"))
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        settings_action = QAction(self.tr("Settings"), self)
        settings_action.setStatusTip(self.tr("Application settings"))
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction(self.tr("Exit"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip(self.tr("Exit application"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Menu Subscription
        subscription_menu = menubar.addMenu(self.tr("Subscription"))

        subscription_info_action = QAction(self.tr("Subscription Info"), self)
        subscription_info_action.setStatusTip(self.tr("View your subscription details"))
        subscription_info_action.triggered.connect(self.show_subscription_dialog)
        subscription_menu.addAction(subscription_info_action)

        try:
            if not self.license_controller.is_pro_user:
                upgrade_action = QAction(self.tr("Upgrade to Pro"), self)
                upgrade_action.setStatusTip(self.tr("Upgrade your subscription to Pro"))
                upgrade_action.triggered.connect(self.show_upgrade_dialog)
                subscription_menu.addAction(upgrade_action)
        except:
            # Dodaj upgrade action w każdym przypadku dla demo
            upgrade_action = QAction(self.tr("Upgrade to Pro"), self)
            upgrade_action.setStatusTip(self.tr("Upgrade your subscription to Pro"))
            upgrade_action.triggered.connect(self.show_upgrade_dialog)
            subscription_menu.addAction(upgrade_action)

        subscription_menu.addSeparator()

        refresh_license_action = QAction(self.tr("Refresh License"), self)
        refresh_license_action.setStatusTip(self.tr("Refresh license status"))
        refresh_license_action.triggered.connect(self.refresh_license)
        subscription_menu.addAction(refresh_license_action)

        # Buy Pro actions
        monthly_action = QAction(self.tr("Buy Pro Monthly ($9.99)"), self)
        monthly_action.triggered.connect(self.buy_monthly)
        subscription_menu.addAction(monthly_action)

        yearly_action = QAction(self.tr("Buy Pro Yearly ($99.99)"), self)
        yearly_action.triggered.connect(self.buy_yearly)
        subscription_menu.addAction(yearly_action)

        # Menu Edit
        edit_menu = menubar.addMenu(self.tr("Edit"))

        undo_action = QAction(self.tr("Undo"), self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.setStatusTip(self.tr("Undo last action"))
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction(self.tr("Redo"), self)
        redo_action.setShortcut("Ctrl+Shift+Z")
        redo_action.setStatusTip(self.tr("Redo last undone action"))
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        preferences_action = QAction(self.tr("Preferences"), self)
        preferences_action.setStatusTip(self.tr("Edit application preferences"))
        preferences_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(preferences_action)

        # Menu View
        view_menu = menubar.addMenu(self.tr("View"))

        toolbar_action = QAction(self.tr("Toolbar"), self)
        toolbar_action.setCheckable(True)
        toolbar_action.setChecked(True)
        toolbar_action.triggered.connect(self.toggle_toolbar)
        view_menu.addAction(toolbar_action)

        statusbar_action = QAction(self.tr("Statusbar"), self)
        statusbar_action.setCheckable(True)
        statusbar_action.setChecked(True)
        statusbar_action.triggered.connect(self.toggle_statusbar)
        view_menu.addAction(statusbar_action)

        # Menu Language (NEW)
        self.create_language_menu(menubar)

        # Menu Help
        help_menu = menubar.addMenu(self.tr("Help"))

        documentation_action = QAction(self.tr("Documentation"), self)
        documentation_action.setStatusTip(self.tr("Show documentation"))
        documentation_action.triggered.connect(self.show_documentation)
        help_menu.addAction(documentation_action)

        about_action = QAction(self.tr("About"), self)
        about_action.setStatusTip(self.tr("About Retixly"))
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_language_menu(self, menubar):
        """Tworzy menu wyboru języka."""
        language_menu = menubar.addMenu(self.tr("Language"))

        available_languages = [
            {"code": "en", "name": "English", "flag": "🇺🇸", "file": None},
            {"code": "pl", "name": "Polski", "flag": "🇵🇱", "file": "retixly_pl.qm"},
        ]

        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)

        current_lang = self.settings.get_value("general", "language", "en")

        for lang in available_languages:
            display_name = f"{lang['flag']} {lang['name']}"
            action = QAction(display_name, self)
            action.setCheckable(True)
            action.setData(lang["code"])
            
            if lang["code"] == current_lang:
                action.setChecked(True)
            
            action.triggered.connect(
                lambda checked, code=lang["code"], file=lang["file"]: 
                self.change_language(code, file)
            )
            
            self.language_group.addAction(action)
            language_menu.addAction(action)

        # Opcja ponownej kompilacji tłumaczeń (dla devów)
        language_menu.addSeparator()
        recompile_action = QAction(self.tr("Recompile Translations"), self)
        recompile_action.triggered.connect(self.recompile_translations)
        language_menu.addAction(recompile_action)

    def change_language(self, lang_code, qm_file=None, save_setting=True):
        """DEPRECATED - używaj change_language_unified z main.py"""
        try:
            # Znajdź instancję RetixlyApp
            app_instance = self._app_instance  # Użyj zapisanej referencji
            
            if app_instance and hasattr(app_instance, 'change_language_unified'):
                app_instance.change_language_unified(lang_code)
                logger.info(f"✅ Delegated language change to unified method: {lang_code}")
            else:
                logger.warning("❌ Unified language change method not found")
                logger.warning(f"app_instance: {app_instance}")
                if app_instance:
                    logger.warning(f"Available methods: {[m for m in dir(app_instance) if 'language' in m.lower()]}")

        except Exception as e:
            logger.error(f"❌ Error in deprecated change_language: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def retranslate_ui_safe(self):
        """Bezpieczna retranslacja UI."""
        try:
            logger.info("Starting UI retranslation...")
            
            # Zaktualizuj tytuł okna
            self.setWindowTitle(self.get_window_title())
            
            # Zaktualizuj tytuły zakładek
            if hasattr(self, 'tabs'):
                tab_titles = [
                    self.tr("Single Photo"),
                    self.tr("Batch Processing"), 
                    self.tr("CSV/XML Import")
                ]
                for i, title in enumerate(tab_titles):
                    if i < self.tabs.count():
                        self.tabs.setTabText(i, title)
            
            # Status bar - POPRAWIONY
            if hasattr(self, 'statusBar'):
                self.statusBar.showMessage(self.tr("Ready"))
            
            logger.info("UI retranslation completed successfully")
            
        except Exception as e:
            logger.error(f"Error during UI retranslation: {e}")




    def update_menu_texts(self):
        self.menuBar().clear()
        self.create_menu_bar()

    def update_tab_titles(self):
        if hasattr(self, 'tabs'):
            tab_titles = [
                self.tr("Single Photo"),
                self.tr("Batch Processing"),
                self.tr("CSV/XML Import")
            ]
            for i, title in enumerate(tab_titles):
                if i < self.tabs.count():
                    self.tabs.setTabText(i, title)

    def retranslate_views(self):
        """Retransluje wszystkie widoki."""
        views = []

        # Zbierz wszystkie widoki
        if hasattr(self, 'single_photo_view') and self.single_photo_view:
            views.append(self.single_photo_view)
        if hasattr(self, 'batch_processing_view') and self.batch_processing_view:
            views.append(self.batch_processing_view)
        if hasattr(self, 'csv_xml_view') and self.csv_xml_view:
            views.append(self.csv_xml_view)

        # Retransluj każdy widok
        for view in views:
            if hasattr(view, 'retranslate_ui'):
                try:
                    view.retranslate_ui()
                    logger.info(f"Retranslated view: {type(view).__name__}")
                except Exception as e:
                    logger.error(f"Error retranslating view {type(view).__name__}: {e}")

    def recompile_translations(self):
        """Przeprowadza rekompilację plików tłumaczeń (tylko dla devów)."""
        import subprocess
        translations_dir = Path(__file__).resolve().parents[2] / "translations"
        ts_files = list(translations_dir.glob("*.ts"))
        if not ts_files:
            QMessageBox.information(self, "Translations", "No .ts files found to compile.")
            return
        for ts in ts_files:
            qm = ts.with_suffix(".qm")
            try:
                subprocess.run(["lrelease", str(ts), "-qm", str(qm)], check=True)
            except Exception as e:
                QMessageBox.warning(self, "Translation Compile Error", f"Could not compile {ts.name}: {e}")
        QMessageBox.information(self, "Translations", "Translations recompiled. Please restart the app to apply changes.")

    def tr(self, text):
        """Zastąpiona metoda tr() - używa QApplication.translate() z kontekstem MainWindow."""
        return QApplication.translate("MainWindow", text)
        
    def create_toolbar(self):
        """Tworzenie paska narzędzi."""
        self.toolbar = QToolBar()
        self.toolbar.setObjectName("MainToolBar")
        self.addToolBar(self.toolbar)
        
        # Dodawanie akcji do paska narzędzi
        new_action = QAction(self.tr("New"), self)
        new_action.setStatusTip(self.tr("Create new project"))
        new_action.triggered.connect(self.new_project)
        self.toolbar.addAction(new_action)
        
        open_action = QAction(self.tr("Open"), self)
        open_action.setStatusTip(self.tr("Open project"))
        open_action.triggered.connect(self.open_project)
        self.toolbar.addAction(open_action)
        
        save_action = QAction(self.tr("Save"), self)
        save_action.setStatusTip(self.tr("Save project"))
        save_action.triggered.connect(self.save_project)
        self.toolbar.addAction(save_action)
        
        self.toolbar.addSeparator()
        
        process_action = QAction(self.tr("Process"), self)
        process_action.setStatusTip(self.tr("Process images"))
        process_action.triggered.connect(self.process_images)
        self.toolbar.addAction(process_action)
        
        export_action = QAction(self.tr("Export"), self)
        export_action.setStatusTip(self.tr("Export processed images"))
        export_action.triggered.connect(self.export_images)
        self.toolbar.addAction(export_action)

    def load_window_state(self):
        """Wczytuje zapisany stan okna."""
        try:
            settings = QSettings()
            geometry = settings.value("MainWindow/Geometry")
            if geometry:
                self.restoreGeometry(geometry)
            state = settings.value("MainWindow/State")
            if state:
                self.restoreState(state)
        except Exception as e:
            print(f"Nie można wczytać stanu okna: {e}")
        
    def save_window_state(self):
        """Zapisuje stan okna."""
        try:
            settings = QSettings()
            settings.setValue("MainWindow/Geometry", self.saveGeometry())
            settings.setValue("MainWindow/State", self.saveState())
        except Exception as e:
            print(f"Nie można zapisać stanu okna: {e}")

    # Metody akcji
    def new_project(self):
        """Tworzenie nowego projektu."""
        if self.maybe_save():
            self.statusBar.showMessage(self.tr("Created new project"))

    def open_project(self):
        """Otwieranie projektu."""
        if self.maybe_save():
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("Open Project"),
                "",
                self.tr("Retixly Project (*.rtx)")
            )
            if file_name:
                self.statusBar.showMessage(f"Opened project: {file_name}")

    def save_project(self):
        """Zapisywanie projektu."""
        if not hasattr(self, 'current_file'):
            return self.save_project_as()
        
        self.statusBar.showMessage(f"Project saved: {self.current_file}")
        return True

    def save_project_as(self):
        """Zapisywanie projektu pod nową nazwą."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Project"),
            "",
            self.tr("Retixly Project (*.rtx)")
        )
        if file_name:
            self.current_file = file_name
            return self.save_project()
        return False

    def show_settings(self):
        """Wyświetlanie okna ustawień."""
        if SettingsDialog:
            settings_dialog = SettingsDialog(self.settings, self)
            settings_dialog.exec()
        else:
            QMessageBox.information(
                self,
                "Demo Mode",
                "Settings dialog is not available in demo mode."
            )

    def show_preferences(self):
        """Wyświetlanie okna preferencji."""
        QMessageBox.information(
            self,
            "Coming Soon",
            "Preferences will be available in a future update."
        )

    def undo(self):
        """Cofnięcie ostatniej operacji."""
        self.statusBar.showMessage(self.tr("Undo"))

    def redo(self):
        """Ponowienie cofniętej operacji."""
        self.statusBar.showMessage(self.tr("Redo"))

    def process_images(self):
        """Przetwarzanie obrazów."""
        self.statusBar.showMessage(self.tr("Processing images..."))

    def export_images(self):
        """Eksportowanie obrazów."""
        self.statusBar.showMessage(self.tr("Exporting images..."))

    def toggle_toolbar(self, state):
        """Przełączanie widoczności paska narzędzi."""
        if hasattr(self, 'toolbar'):
            self.toolbar.setVisible(state)

    def toggle_statusbar(self, state):
        """Przełączanie widoczności paska statusu."""
        self.statusBar.setVisible(state)

    def show_documentation(self):
        """Wyświetlanie dokumentacji."""
        QMessageBox.information(
            self,
            self.tr("Documentation"),
            self.tr("Documentation will be available soon.")
        )

    def show_about(self):
        """Wyświetlanie informacji o programie."""
        QMessageBox.about(
            self,
            self.tr("About Retixly"),
            "Retixly 3.0\n\n"
            "Professional Image Processing Tool\n"
            "© 2025 RetixlySoft"
        )

    def maybe_save(self):
        """Sprawdza czy trzeba zapisać zmiany przed zamknięciem."""
        return True

    def buy_monthly(self):
        """Kup miesięczną subskrypcję."""
        self.buy_plan(SubscriptionPlan.PRO_MONTHLY)

    def buy_yearly(self):
        """Kup roczną subskrypcję."""
        self.buy_plan(SubscriptionPlan.PRO_YEARLY)

    def buy_plan(self, plan):
        """Kup wybrany plan."""
        try:
            from src.controllers.subscription_controller import get_subscription_controller
            controller = get_subscription_controller()
            checkout_url = controller.create_checkout_url(plan)
            if checkout_url:
                import webbrowser
                webbrowser.open(checkout_url)
                QMessageBox.information(
                    self,
                    "Checkout Opened",
                    "Checkout page opened in browser.\nComplete the payment to activate Pro features."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Could not generate checkout link."
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def closeEvent(self, event):
        """Obsługa zamknięcia aplikacji."""
        try:
            if self.maybe_save():
                self.save_window_state()
                
                # Bezpieczne zamknięcie kontrolera licencji
                if hasattr(self, 'license_controller') and self.license_controller:
                    try:
                        self.license_controller.cleanup()
                    except Exception:
                        pass  # Ignoruj błędy podczas cleanup
                
                event.accept()
            else:
                event.ignore()
        except Exception as e:
            print(f"Error during close: {e}")
            event.accept()  # Wymuś zamknięcie mimo błędu
    def changeEvent(self, event):
        """Obsługuje LanguageChange event."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui_safe()
        super().changeEvent(event)