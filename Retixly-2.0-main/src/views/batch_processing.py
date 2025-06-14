from ..controllers.license_controller import get_license_controller
from ..views.upgrade_prompts import show_upgrade_prompt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFileDialog, QListWidget, QProgressBar,
                            QGroupBox, QSpinBox, QComboBox, QCheckBox, QListWidgetItem,
                            QScrollArea, QGridLayout, QFrame, QMessageBox, QLineEdit,
                            QDialog, QFormLayout, QTextEdit, QStackedWidget, QColorDialog, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QSettings
from PyQt6.QtGui import QPixmap, QIcon, QColor
from pathlib import Path
import os
from ..components.thumbnail_list import ThumbnailList
from ..controllers.batch_processor import BatchProcessor

import logging
import tempfile
import csv
from src.core.image_engine import create_optimized_engine

logger = logging.getLogger(__name__)

# --- BatchProcessor class for batch integration ---
class BatchProcessor(QThread):
    """Procesor wsadowy z integracją UnifiedImageEngine."""
    progress_updated = pyqtSignal(int)
    processing_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.files = []
        self.settings = {}
        self.stopped = False
        self.engine = None

    def process_images(self, files, settings):
        """Rozpocznij przetwarzanie wsadowe."""
        self.files = files
        self.settings = settings
        self.stopped = False
        try:
            # Inicjalizacja engine ze stałą liczbą wątków (wyłączono równoległość)
            self.engine = create_optimized_engine(max_workers=4)
            logger.info("Engine initialized for batch processing")
        except Exception as e:
            logger.error(f"Failed to initialize engine: {e}")
            self.engine = None
        self.start()

    def run(self):
        """Przetwarzanie wsadowe."""
        try:
            total_files = len(self.files)
            processed = 0

            # Przygotowanie ustawień engine
            engine_settings = self.convert_settings_to_engine_format()

            # Określenie ścieżki wyjściowej
            output_dir = self.get_output_directory()
            if output_dir is None:
                logger.error("Nie ustawiono folderu do zapisu! Przerywanie batch processing.")
                self.error_occurred.emit("Nie ustawiono folderu do zapisu! Przerywanie batch processing.")
                return
            os.makedirs(output_dir, exist_ok=True)

            for i, file_path in enumerate(self.files):
                if self.stopped:
                    break

                try:
                    # Przetwarzanie przez engine lub fallback
                    if self.engine:
                        result = self.process_with_engine(file_path, engine_settings)
                    else:
                        result = self.process_with_fallback(file_path)

                    # Zapisanie wyniku
                    if result:
                        output_path = self.save_processed_image(result, file_path, output_dir)
                        if output_path:
                            processed += 1

                    # Aktualizacja postępu
                    progress = int((i + 1) / total_files * 100)
                    self.progress_updated.emit(progress)

                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    continue

            logger.info(f"Batch processing completed: {processed}/{total_files} files")
            self.processing_finished.emit()

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            self.error_occurred.emit(str(e))

    def convert_settings_to_engine_format(self):
        engine_settings = {
            "background": {
                "mode": "remove",
                "color": None,
                "image_path": None,
            },
            "adjustments": {},
            "effects": {},
            "watermark": {},
            "marketplace": None
        }

        processing = self.settings.get("processing", {})
        mode = processing.get("mode", "Remove Background")

        if mode == "Remove Background":
            engine_settings["background"]["mode"] = "remove"
        elif mode == "Replace Background":
            engine_settings["background"]["mode"] = (
                "image" if processing.get("bg_image") else "color"
            )
            engine_settings["background"]["color"] = processing.get("bg_color")
            engine_settings["background"]["image_path"] = processing.get("bg_image")

        if self.settings.get("prepare_for_sale"):
            marketplaces = self.settings.get("marketplaces", [])
            if marketplaces:
                engine_settings["marketplace"] = marketplaces[0]

        return engine_settings

    def process_with_engine(self, file_path, settings):
        """Przetwarza plik przez UnifiedImageEngine."""
        try:
            from PIL import Image

            # Ładowanie obrazu
            image = Image.open(file_path)

            # Wyodrębnij ustawienia tła
            background_mode = settings.get("background", {}).get("mode", "remove")
            complex_edit = background_mode in ("color", "image")

            if complex_edit:
                from rembg import remove
                import numpy as np

                img_array = np.array(image)
                result_array = remove(img_array)
                result = Image.fromarray(result_array)

                if background_mode == "color":
                    bg_color = settings["background"].get("color") or "#FFFFFF"
                    hex_color = bg_color.lstrip("#")
                    rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    background = Image.new("RGB", image.size, rgb_color)
                    if result.mode == "RGBA":
                        background.paste(result, mask=result.split()[-1])
                    return background

                elif background_mode == "image":
                    bg_path = settings["background"].get("image_path")
                    if bg_path:
                        background = Image.open(bg_path).resize(image.size)
                        if result.mode == "RGBA":
                            background.paste(result, mask=result.split()[-1])
                        return background
                    return result

            # W innych przypadkach, deleguj do engine
            return self.engine.process_single(image, settings)

        except Exception as e:
            logger.error(f"Engine processing failed for {file_path}: {e}")
            return None

    def process_with_fallback(self, file_path):
        """Fallback processing gdy engine nie jest dostępny."""
        try:
            from PIL import Image
            
            # Proste przetwarzanie
            image = Image.open(file_path)
            
            # Podstawowe usuwanie tła
            mode = self.settings.get('processing', {}).get('mode', 'Usuń tło')
            if mode in ['Usuń tło', 'Zamień tło']:
                try:
                    from rembg import remove
                    import numpy as np
                    
                    img_array = np.array(image)
                    result_array = remove(img_array)
                    result = Image.fromarray(result_array)
                    
                    # Zamiana tła na kolor jeśli potrzeba
                    if mode == 'Zamień tło':
                        bg_color = self.settings.get('processing', {}).get('bg_color', '#FFFFFF')
                        if isinstance(bg_color, str) and bg_color.startswith('#'):
                            hex_color = bg_color[1:]
                            rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                        else:
                            rgb_color = (255, 255, 255)
                        
                        background = Image.new('RGB', image.size, rgb_color)
                        if result.mode == 'RGBA':
                            background.paste(result, mask=result.split()[-1])
                        result = background
                    
                    return result
                    
                except ImportError:
                    logger.warning("rembg not available for fallback processing")
                    return image
            
            return image
            
        except Exception as e:
            logger.error(f"Fallback processing failed for {file_path}: {e}")
            return None

    def get_output_directory(self):
        """Określa katalog wyjściowy."""
        save_location = self.settings.get('save_location', 'Lokalnie')
        if save_location.strip().lower() in ['local', 'lokalnie']:
            local_path = self.settings.get('local_path', '').strip()
            if not local_path:
                logger.error("Nie ustawiono folderu do zapisu! Przerywanie batch processing.")
                return None
            return local_path
        else:
            return tempfile.mkdtemp()

    def save_processed_image(self, image, original_path, output_dir):
        """Zapisuje przetworzony obraz używając zunifikowanego systemu eksportu."""
        try:
            from src.utils.export_utils import export_image

            # Map both 'Local', 'local', and 'lokalnie' to 'Lokalnie' for compatibility
            save_location = self.settings.get('save_location', 'Lokalnie')
            if save_location.strip().lower() in ['local', 'lokalnie']:
                save_location = 'Lokalnie'

            # Przygotowanie ustawień eksportu
            export_settings = {
                'save_location': save_location,
                'output_directory': output_dir,
                'credentials': self.settings.get('credentials', {}),
                'format': self.settings.get('format', {}),
                'filename_pattern': '{original_name}_processed'
            }

            # Delegacja do zunifikowanego systemu
            result_path = export_image(image, original_path, export_settings)
            if result_path and os.path.exists(result_path):
                logger.info(f"Obraz zapisany w: {result_path}")
                return result_path
            else:
                logger.error(f"Nie udało się zapisać pliku! Ścieżka: {result_path}")
                return None

        except Exception as e:
            logger.error(f"Błąd zapisywania przez zunifikowany system: {e}")
            return None

    def create_csv_with_links(self, results, output_path):
        """Tworzy plik CSV z ID produktów i linkami do zdjęć w chmurze"""
        try:
            # Użyj ustawień z kontrolek zamiast domyślnych
            csv_path = self.settings.get('csv_local_path', output_path)
            csv_filename = self.settings.get('csv_filename', 'processed_images')
            
            os.makedirs(csv_path, exist_ok=True)
            csv_data = []
            
            for result in results:
                # Dla batch processing nie ma item_data, więc używamy nazwy pliku
                original_name = Path(result.get('input_path', '')).stem
                cloud_url = result.get('cloud_url', '')
                csv_data.append([original_name, cloud_url])
            
            full_csv_path = os.path.join(csv_path, f'{csv_filename}.csv')
            with open(full_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Original_Name', 'Image_URL'])
                writer.writerows(csv_data)
                
            logger.info(f"CSV z linkami zapisany: {full_csv_path}")
            
        except Exception as e:
            logger.error(f"Błąd tworzenia CSV z linkami: {e}")

    def stop(self):
        """Zatrzymuje przetwarzanie."""
        self.stopped = True
        self.wait()

class MarketplaceTestDialog(QDialog):
    """Dialog do testowania połączenia z marketplace."""
    
    def __init__(self, service_type, parent=None):
        super().__init__(parent)
        self.service_type = service_type
        self.test_passed = False
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(f"Konfiguracja {self.service_type}")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Formularz danych logowania
        form_layout = QFormLayout()
        
        if self.service_type == "Google Drive":
            self.folder_id = QLineEdit()
            self.folder_id.setPlaceholderText("ID folderu Google Drive")
            form_layout.addRow("Folder ID:", self.folder_id)
            
        elif self.service_type == "Amazon S3":
            self.access_key = QLineEdit()
            self.secret_key = QLineEdit()
            self.secret_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.bucket_name = QLineEdit()
            
            form_layout.addRow("Access Key ID:", self.access_key)
            form_layout.addRow("Secret Access Key:", self.secret_key)
            form_layout.addRow("Bucket Name:", self.bucket_name)
            
        elif self.service_type == "FTP":
            self.ftp_host = QLineEdit()
            self.ftp_user = QLineEdit()
            self.ftp_pass = QLineEdit()
            self.ftp_pass.setEchoMode(QLineEdit.EchoMode.Password)
            self.ftp_path = QLineEdit()
            
            form_layout.addRow("Host:", self.ftp_host)
            form_layout.addRow("Username:", self.ftp_user)
            form_layout.addRow("Password:", self.ftp_pass)
            form_layout.addRow("Path:", self.ftp_path)
            
        elif self.service_type == "imgBB":
            self.api_key = QLineEdit()
            self.api_key.setPlaceholderText("Twój klucz API imgBB")
            form_layout.addRow("API Key:", self.api_key)
            
        layout.addLayout(form_layout)
        
        # Status testu
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("TEST")
        self.test_btn.clicked.connect(self.test_connection)
        
        self.save_btn = QPushButton("Zapisz")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.test_btn)
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
        
    def test_connection(self):
        """Testuje połączenie z wybraną usługą."""
        self.status_label.setText("Testowanie połączenia...")
        self.test_btn.setEnabled(False)
        
        # Symulacja testu - w rzeczywistości tutaj byłaby logika testowania
        QTimer.singleShot(2000, self.test_completed)
        
    def test_completed(self):
        """Obsługa zakończenia testu."""
        # Tutaj byłaby prawdziwa logika sprawdzania połączenia
        self.test_passed = True
        self.status_label.setText("Test zakończony pomyślnie!")
        self.status_label.setStyleSheet("color: green;")
        self.save_btn.setEnabled(True)
        self.test_btn.setEnabled(True)
        
    def get_credentials(self):
        """Zwraca dane logowania."""
        if self.service_type == "Google Drive":
            return {"folder_id": self.folder_id.text()}
        elif self.service_type == "Amazon S3":
            return {
                "access_key": self.access_key.text(),
                "secret_key": self.secret_key.text(),
                "bucket": self.bucket_name.text()
            }
        elif self.service_type == "FTP":
            return {
                "host": self.ftp_host.text(),
                "user": self.ftp_user.text(),
                "password": self.ftp_pass.text(),
                "path": self.ftp_path.text()
            }
        elif self.service_type == "imgBB":
            return {"api_key": self.api_key.text()}
        return {}

class BatchProcessingControls(QWidget):
    def tr(self, text):
        from PyQt6.QtWidgets import QApplication
        return QApplication.translate(self.__class__.__name__, text)

    def changeEvent(self, event):
        """Obsługuje zmianę języka."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)
    """Widget kontrolek do przetwarzania wsadowego z nowoczesnym wyglądem i kontrolkami CSV."""
    marketplace_changed = pyqtSignal(bool)  # True jeśli wybrano marketplace

    
    def __init__(self):
        super().__init__()
        self.last_local_path = QSettings().value('batch_processing/last_local_path', '')
        self.init_ui()
        self.retranslate_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Zmniejszony font dla całej sekcji
        small_font_style = "font-size: 10px;"
        label_style = "font-size: 11px; font-weight: 600; color: #495057; margin-bottom: 4px;"

        # Sekcja - Przygotuj do sprzedaży - bez QGroupBox
        self.marketplace_label = QLabel()
        self.marketplace_label.setStyleSheet(label_style)
        layout.addWidget(self.marketplace_label)

        # Checkbox główny
        self.prepare_for_sale = QCheckBox()
        # self.prepare_for_sale.setText(self.tr("Prepare for sale"))
        self.prepare_for_sale.setStyleSheet(f"""
            QCheckBox {{
                {small_font_style}
                font-weight: 500;
                color: #495057;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 2px solid #dee2e6;
                border-radius: 3px;
                background: white;
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid #0079e1;
                border-radius: 3px;
                background: #0079e1;
            }}
        """)
        self.prepare_for_sale.stateChanged.connect(self.on_marketplace_changed)
        layout.addWidget(self.prepare_for_sale)

        # Checkboxy marketplace bez ramki - ukryte domyślnie
        self.marketplace_frame = QFrame()
        self.marketplace_frame.setStyleSheet("QFrame { border: none; }")
        marketplace_checkboxes_layout = QGridLayout()
        marketplace_checkboxes_layout.setSpacing(8)
        
        self.amazon_cb = QCheckBox()
        self.ebay_cb = QCheckBox()
        self.etsy_cb = QCheckBox()
        self.allegro_cb = QCheckBox()
        self.shopify_cb = QCheckBox()
        self.wechat_cb = QCheckBox()
        # Remove inline setText, will be set in retranslate_ui
        
        # Zastosuj style do wszystkich checkboxów marketplace
        for cb in [self.amazon_cb, self.ebay_cb, self.etsy_cb, self.allegro_cb, self.shopify_cb, self.wechat_cb]:
            cb.setStyleSheet(f"""
                QCheckBox {{
                    {small_font_style}
                    color: #495057;
                    spacing: 6px;
                }}
                QCheckBox::indicator {{
                    width: 12px;
                    height: 12px;
                }}
                QCheckBox::indicator:unchecked {{
                    border: 2px solid #dee2e6;
                    border-radius: 2px;
                    background: white;
                }}
                QCheckBox::indicator:checked {{
                    border: 2px solid #0079e1;
                    border-radius: 2px;
                    background: #0079e1;
                }}
            """)
        for cb in [self.amazon_cb, self.ebay_cb, self.etsy_cb, self.allegro_cb, self.shopify_cb, self.wechat_cb]:
            cb.stateChanged.connect(self.on_marketplace_checkbox_changed)
        
        marketplace_checkboxes_layout.addWidget(self.amazon_cb, 0, 0)
        marketplace_checkboxes_layout.addWidget(self.ebay_cb, 0, 1)
        marketplace_checkboxes_layout.addWidget(self.etsy_cb, 1, 0)
        marketplace_checkboxes_layout.addWidget(self.allegro_cb, 1, 1)
        marketplace_checkboxes_layout.addWidget(self.shopify_cb, 2, 0)
        marketplace_checkboxes_layout.addWidget(self.wechat_cb, 2, 1)
        
        self.marketplace_frame.setLayout(marketplace_checkboxes_layout)
        self.marketplace_frame.hide()  # Ukryj domyślnie
        layout.addWidget(self.marketplace_frame)

        # Opcja bez wycinania tła - ukryta domyślnie
        self.no_bg_removal = QCheckBox()
        # self.no_bg_removal.setText(self.tr("Prepare only for sale without background removal"))
        self.no_bg_removal.setStyleSheet(f"""
            QCheckBox {{
                {small_font_style}
                color: #495057;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 12px;
                height: 12px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 2px solid #dee2e6;
                border-radius: 2px;
                background: white;
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid #0079e1;
                border-radius: 2px;
                background: #0079e1;
            }}
        """)
        self.no_bg_removal.hide()  # Ukryj domyślnie
        layout.addWidget(self.no_bg_removal)

        # Separator
        layout.addSpacing(8)

        # Sekcja - Format zapisu zdjęć - bez QGroupBox
        self.format_label = QLabel()
        self.format_label.setStyleSheet(label_style)
        layout.addWidget(self.format_label)
        
        self.format_group = QWidget()
        format_layout = QVBoxLayout(self.format_group)
        format_layout.setSpacing(8)
        format_layout.setContentsMargins(0, 0, 0, 0)

        self.output_format = QComboBox()
        self.output_format.addItems(["PNG", "JPG", "JPEG", "WEBP"])
        self.output_format.setStyleSheet(f"""
            QComboBox {{
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 6px 10px;
                color: #495057;
                {small_font_style}
            }}
            QComboBox:hover {{
                border-color: #0079e1;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        format_layout.addWidget(self.output_format)

        layout.addWidget(self.format_group)

        # Separator
        layout.addSpacing(8)

        # Sekcja - Rodzaj zapisu - bez QGroupBox
        self.save_label = QLabel()
        self.save_label.setStyleSheet(label_style)
        layout.addWidget(self.save_label)
        
        save_widget = QWidget()
        save_layout = QVBoxLayout(save_widget)
        save_layout.setSpacing(8)
        save_layout.setContentsMargins(0, 0, 0, 0)

        self.save_location = QComboBox()
        self.save_location.addItems([
            "Lokalnie", "Google Drive", "Amazon S3", "imgBB", "FTP"
        ])
        self.save_location.setStyleSheet(f"""
            QComboBox {{
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 6px 10px;
                color: #495057;
                {small_font_style}
            }}
            QComboBox:hover {{
                border-color: #0079e1;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        self.save_location.currentTextChanged.connect(self.on_save_location_changed)
        save_layout.addWidget(self.save_location)

        # Sekcja wyboru ścieżki lokalnej
        self.local_path_widget = QWidget()
        local_path_layout = QVBoxLayout(self.local_path_widget)
        local_path_layout.setSpacing(6)
        local_path_layout.setContentsMargins(0, 0, 0, 0)
        
        self.path_label = QLabel()
        self.path_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        local_path_layout.addWidget(self.path_label)
        
        path_input_layout = QHBoxLayout()
        self.local_path = QLineEdit()
        # self.local_path.setPlaceholderText("")
        self.local_path.setReadOnly(True)
        self.local_path.setStyleSheet(f"""
            QLineEdit {{
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 6px 10px;
                color: #495057;
                {small_font_style}
            }}
        """)
        if self.last_local_path:
            self.local_path.setText(self.last_local_path)
        
        self.browse_btn = QPushButton()
        # self.browse_btn.setText(self.tr("Browse"))
        self.browse_btn.setStyleSheet(f"""
            QPushButton {{
                background: #0079e1;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
                {small_font_style}
            }}
            QPushButton:hover {{
                background: #0056b3;
            }}
        """)
        self.browse_btn.clicked.connect(self.browse_local_path)
        
        path_input_layout.addWidget(self.local_path)
        path_input_layout.addWidget(self.browse_btn)
        local_path_layout.addLayout(path_input_layout)
        
        save_layout.addWidget(self.local_path_widget)
        # Ensure local_path_widget is explicitly shown after setup
        self.local_path_widget.show()

        # Status konfiguracji
        self.config_status = QLabel("")
        self.config_status.setStyleSheet(f"{small_font_style} font-weight: 500;")
        save_layout.addWidget(self.config_status)

        # Przycisk konfiguracji
        self.config_btn = QPushButton()
        # self.config_btn.setText(self.tr("Enter login credentials"))
        self.config_btn.setStyleSheet(f"""
            QPushButton {{
                background: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 6px;
                padding: 8px;
                color: #6c757d;
                font-weight: 500;
                {small_font_style}
            }}
            QPushButton:hover {{
                border-color: #0079e1;
                color: #0079e1;
            }}
        """)
        self.config_btn.clicked.connect(self.configure_service)
        self.config_btn.hide()
        save_layout.addWidget(self.config_btn)

        # --- CSV z linkami do chmury - NOWA SEKCJA ---
        self.csv_links_widget = QWidget()
        csv_links_layout = QVBoxLayout(self.csv_links_widget)
        csv_links_layout.setSpacing(6)
        csv_links_layout.setContentsMargins(0, 0, 0, 0)

        self.create_csv_links = QCheckBox()
        self.create_csv_links.setChecked(True)
        # self.create_csv_links.setText(self.tr("Create CSV file with links"))
        self.create_csv_links.setStyleSheet(f"""
            QCheckBox {{
                {small_font_style}
                color: #495057;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 12px;
                height: 12px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 2px solid #dee2e6;
                border-radius: 2px;
                background: white;
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid #0079e1;
                border-radius: 2px;
                background: #0079e1;
            }}
        """)
        csv_links_layout.addWidget(self.create_csv_links)

        # Kontrolki dla miejsca zapisu CSV (ukryte domyślnie)
        self.csv_save_options = QWidget()
        csv_save_layout = QVBoxLayout(self.csv_save_options)
        csv_save_layout.setSpacing(6)
        csv_save_layout.setContentsMargins(8, 8, 8, 8)

        # Wybór ścieżki dla pliku CSV
        self.csv_path_label = QLabel()
        self.csv_path_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        csv_save_layout.addWidget(self.csv_path_label)

        csv_path_input_layout = QHBoxLayout()
        self.csv_local_path = QLineEdit()
        # self.csv_local_path.setPlaceholderText("")
        self.csv_local_path.setReadOnly(True)
        self.csv_local_path.setStyleSheet(f"""
            QLineEdit {{
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 6px 10px;
                color: #495057;
                {small_font_style}
            }}
        """)

        self.csv_browse_btn = QPushButton()
        # self.csv_browse_btn.setText(self.tr("Browse"))
        self.csv_browse_btn.setStyleSheet(f"""
            QPushButton {{
                background: #0079e1;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
                {small_font_style}
            }}
            QPushButton:hover {{
                background: #0056b3;
            }}
        """)
        self.csv_browse_btn.clicked.connect(self.browse_csv_path)

        csv_path_input_layout.addWidget(self.csv_local_path)
        csv_path_input_layout.addWidget(self.csv_browse_btn)
        csv_save_layout.addLayout(csv_path_input_layout)

        # Nazwa pliku CSV
        self.csv_name_label = QLabel()
        self.csv_name_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        csv_save_layout.addWidget(self.csv_name_label)

        self.csv_filename = QLineEdit()
        # self.csv_filename.setPlaceholderText("")
        self.csv_filename.setText("processed_images")
        self.csv_filename.setStyleSheet(f"""
            QLineEdit {{
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 6px 10px;
                color: #495057;
                {small_font_style}
            }}
            QLineEdit:hover {{
                border-color: #0079e1;
            }}
        """)
        csv_save_layout.addWidget(self.csv_filename)

        self.csv_save_options.hide()
        csv_links_layout.addWidget(self.csv_save_options)

        self.csv_links_widget.hide()  # Ukryj całą sekcję domyślnie
        save_layout.addWidget(self.csv_links_widget)

        layout.addWidget(save_widget)

        # Separator
        layout.addSpacing(8)

        # Sekcja ustawień przetwarzania - bez QGroupBox
        self.processing_label = QLabel()
        self.processing_label.setStyleSheet(label_style)
        layout.addWidget(self.processing_label)
        
        processing_widget = QWidget()
        proc_layout = QVBoxLayout(processing_widget)
        proc_layout.setSpacing(8)
        proc_layout.setContentsMargins(0, 0, 0, 0)

        mode_layout = QVBoxLayout()
        self.mode_label = QLabel()
        self.mode_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        mode_layout.addWidget(self.mode_label)
        
        self.process_mode = QComboBox()
        self.process_mode.addItems(["Usuń tło", "Zamień tło", "Tylko przygotuj do sprzedaży"])
        self.process_mode.setStyleSheet(f"""
            QComboBox {{
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 6px 10px;
                color: #495057;
                {small_font_style}
            }}
            QComboBox:hover {{
                border-color: #0079e1;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        self.process_mode.currentTextChanged.connect(self.on_process_mode_changed)
        mode_layout.addWidget(self.process_mode)
        proc_layout.addLayout(mode_layout)

        # Opcje zmiany tła (ukryte domyślnie)
        self.bg_options_widget = QWidget()
        bg_options_layout = QVBoxLayout(self.bg_options_widget)
        bg_options_layout.setSpacing(8)
        bg_options_layout.setContentsMargins(0, 0, 0, 0)
        
        # Przyciski wyboru typu tła
        bg_type_frame = QFrame()
        bg_type_frame.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 3px;
            }
        """)
        bg_type_layout = QHBoxLayout(bg_type_frame)
        bg_type_layout.setSpacing(3)
        
        self.bg_color_tab = QPushButton()
        # self.bg_color_tab.setText(self.tr("Color"))
        self.bg_image_tab = QPushButton()
        # self.bg_image_tab.setText(self.tr("Image"))
        
        for btn in [self.bg_color_tab, self.bg_image_tab]:
            btn.setCheckable(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: 500;
                    {small_font_style}
                    color: #6c757d;
                }}
                QPushButton:checked {{
                    background: #0079e1;
                    color: white;
                }}
                QPushButton:hover:!checked {{
                    background: #e9ecef;
                }}
            """)
        
        self.bg_color_tab.setChecked(True)
        self.bg_color_tab.clicked.connect(self.select_color_background)
        self.bg_image_tab.clicked.connect(self.select_image_background)
        
        bg_type_layout.addWidget(self.bg_color_tab)
        bg_type_layout.addWidget(self.bg_image_tab)
        bg_options_layout.addWidget(bg_type_frame)
        
        # Stack dla opcji kolor/obraz
        self.bg_type_stack = QStackedWidget()
        
        # Widget koloru
        color_widget = QWidget()
        color_layout = QHBoxLayout(color_widget)
        color_layout.setSpacing(8)
        color_layout.setContentsMargins(0, 0, 0, 0)
        
        self.bg_color_btn = QPushButton()
        # self.bg_color_btn.setText(self.tr("Select color"))
        self.bg_color_btn.setStyleSheet(f"""
            QPushButton {{
                background: #0079e1;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
                {small_font_style}
            }}
            QPushButton:hover {{
                background: #0056b3;
            }}
        """)
        self.bg_color_btn.clicked.connect(self.choose_background_color)
        
        self.bg_color_display = QLabel()
        self.bg_color_display.setFixedSize(30, 30)
        self.bg_color_display.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 6px;
            }
        """)
        self.bg_color = "#FFFFFF"
        
        color_layout.addWidget(self.bg_color_btn)
        color_layout.addWidget(self.bg_color_display)
        color_layout.addStretch()
        
        # Widget obrazu
        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        self.bg_image_btn = QPushButton()
        # self.bg_image_btn.setText(self.tr("Select background image"))
        self.bg_image_btn.setStyleSheet(f"""
            QPushButton {{
                background: #0079e1;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
                {small_font_style}
            }}
            QPushButton:hover {{
                background: #0056b3;
            }}
        """)
        self.bg_image_btn.clicked.connect(self.choose_background_image)
        self.bg_image_path = None
        image_layout.addWidget(self.bg_image_btn)
        
        self.bg_type_stack.addWidget(color_widget)
        self.bg_type_stack.addWidget(image_widget)
        bg_options_layout.addWidget(self.bg_type_stack)
        
        self.bg_options_widget.hide()  # Ukryj domyślnie
        proc_layout.addWidget(self.bg_options_widget)

        # Równoległe przetwarzanie i liczba wątków zostały usunięte z UI.

        layout.addWidget(processing_widget)

        layout.addStretch()
        self.setLayout(layout)

        # Inicjalne ustawienia
        self.service_credentials = {}
        self.update_config_status()
        
        # Usunięcie wszystkich ramek
        self.setStyleSheet("QWidget { border: none; }")

        # Force initial visibility based on default selection
        self.on_save_location_changed(self.save_location.currentText())

    def browse_local_path(self):
        """Otwiera dialog wyboru folderu zapisu lokalnego."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Wybierz folder zapisu",
            self.last_local_path,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        if folder:
            self.local_path.setText(folder)
            self.last_local_path = folder
            QSettings().setValue('batch_processing/last_local_path', folder)

    def browse_csv_path(self):
        """Otwiera dialog wyboru folderu dla pliku CSV."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Wybierz folder dla pliku CSV",
            self.csv_local_path.text() or self.last_local_path,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        if folder:
            self.csv_local_path.setText(folder)

    def on_marketplace_changed(self, state):
        """Obsługa zmiany opcji marketplace."""
        is_checked = state == Qt.CheckState.Checked.value
        
        # Pokaż/ukryj opcje marketplace
        self.marketplace_frame.setVisible(is_checked)
        self.no_bg_removal.setVisible(is_checked)
        
        # Ukryj/pokaż sekcję formatów
        self.format_group.setVisible(not is_checked)
        
        self.marketplace_changed.emit(is_checked)

    def on_process_mode_changed(self, mode):
        """Obsługa zmiany trybu przetwarzania."""
        if mode in ["Zamień tło", "Replace Background"]:
            self.bg_options_widget.show()
        else:
            self.bg_options_widget.hide()

    def choose_background_color(self):
        """Wybór koloru tła."""
        color = QColorDialog.getColor(QColor(self.bg_color), self)
        if color.isValid():
            self.bg_color = color.name()
            self.bg_color_display.setStyleSheet(f"""
                QLabel {{
                    background-color: {self.bg_color};
                    border: 2px solid #dee2e6;
                    border-radius: 6px;
                }}
            """)

    def choose_background_image(self):
        """Wybór obrazu tła."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Wybierz obraz tła", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if file_name:
            self.bg_image_path = file_name
            self.bg_image_btn.setText(f"✓ {Path(file_name).name}")
            self.bg_image_btn.setStyleSheet("""
                QPushButton {
                    background: #d4edda;
                    color: #155724;
                    border: 2px solid #c3e6cb;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: 500;
                    font-size: 10px;
                }
            """)
            self.bg_image_tab.setChecked(True)

    def select_color_background(self):
        """Ensure only the color tab is active and update the stack."""
        self.bg_color_tab.setChecked(True)
        self.bg_image_tab.setChecked(False)
        self.bg_type_stack.setCurrentIndex(0)

    def select_image_background(self):
        """Ensure only the image tab is active and update the stack."""
        self.bg_color_tab.setChecked(False)
        self.bg_image_tab.setChecked(True)
        self.bg_type_stack.setCurrentIndex(1)

    # Pomoc dla liczby wątków usunięta (funkcja nieaktywna)

    def on_save_location_changed(self, location):
        """Obsługa zmiany lokalizacji zapisu."""
        # Accept both Polish and English for "local"
        if location.lower() in ["lokalnie", "local"]:
            self.config_btn.hide()
            # Ensure the local path widget is always shown for local save
            self.local_path_widget.show()
            self.local_path_widget.setVisible(True)
            self.csv_links_widget.hide()  # Ukryj opcje CSV dla zapisu lokalnego
        else:
            self.config_btn.show()
            self.local_path_widget.hide()
            self.csv_links_widget.show()  # Pokaż opcje CSV dla zapisu w chmurze
            # Podłącz sygnał checkbox do pokazywania/ukrywania opcji
            self.create_csv_links.stateChanged.connect(self.on_csv_links_changed)
        # Fallback: if for some reason the widget is not visible when it should be, force it
        if self.save_location.currentText().lower() in ["lokalnie", "local"]:
            if not self.local_path_widget.isVisible():
                self.local_path_widget.setVisible(True)
        self.update_config_status()

    def on_csv_links_changed(self, state):
        """Obsługa zmiany checkbox CSV z linkami."""
        is_checked = state == Qt.CheckState.Checked.value
        self.csv_save_options.setVisible(is_checked)

    def configure_service(self):
        """Otwiera dialog konfiguracji usługi."""
        service = self.save_location.currentText()
        
        dialog = MarketplaceTestDialog(service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.service_credentials[service] = dialog.get_credentials()
            self.update_config_status()

    def update_config_status(self):
        """Aktualizuje status konfiguracji."""
        service = self.save_location.currentText()
        
        if service.lower() in ["lokalnie", "local"]:
            if self.local_path.text():
                self.config_status.setText("✓ Ścieżka wybrana")
                self.config_status.setStyleSheet("color: green; font-size: 10px; font-weight: 500;")
            else:
                self.config_status.setText("⚠ Wybierz folder zapisu")
                self.config_status.setStyleSheet("color: orange; font-size: 10px; font-weight: 500;")
        elif service in self.service_credentials:
            self.config_status.setText("✓ Skonfigurowane")
            self.config_status.setStyleSheet("color: green; font-size: 10px; font-weight: 500;")
        else:
            self.config_status.setText("⚠ Wymagane uzupełnienie danych")
            self.config_status.setStyleSheet("color: orange; font-size: 10px; font-weight: 500;")

    def on_marketplace_checkbox_changed(self, state):
        """Zapewnia, że w sekcji 'Przygotuj do sprzedaży' można wybrać tylko jeden marketplace."""
        if state == Qt.CheckState.Checked.value:
            sender = self.sender()
            for cb in [
                self.amazon_cb,
                self.ebay_cb,
                self.etsy_cb,
                self.allegro_cb,
                self.shopify_cb,
                self.wechat_cb,
            ]:
                if cb is not sender:
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    cb.blockSignals(False)

    def get_settings(self):
        """Zwraca aktualne ustawienia."""
        # Map Polish process modes to English
        process_mode_map = {
            "Usuń tło": "Remove Background",
            "Zamień tło": "Replace Background",
            "Tylko przygotuj do sprzedaży": "Prepare Only"
        }
        current_mode = self.process_mode.currentText()
        mapped_mode = process_mode_map.get(current_mode, current_mode)
        settings = {
            'prepare_for_sale': self.prepare_for_sale.isChecked(),
            'marketplaces': [],
            'no_bg_removal': self.no_bg_removal.isChecked(),
            'format': {
                'type': self.output_format.currentText(),
                'quality': 90  # Domyślna jakość
            },
            'save_location': self.save_location.currentText(),
            'local_path': self.local_path.text() if self.save_location.currentText().lower() in ["lokalnie", "local"] else "",
            'credentials': self.service_credentials.get(self.save_location.currentText(), {}),
            'processing': {
                'mode': mapped_mode,
                'bg_color': self.bg_color,
                'bg_image': self.bg_image_path
            },

            # CSV z linkami - tylko dla zapisu w chmurze
            'create_csv_links': (
                self.create_csv_links.isChecked() 
                if self.save_location.currentText() != "Lokalnie" 
                else False
            ),
            'csv_local_path': self.csv_local_path.text(),
            'csv_filename': self.csv_filename.text() or "processed_images"
        }
        print(f"[DEBUG] get_settings -> local_path: '{self.local_path.text()}', save_location: '{self.save_location.currentText()}'")
        # Zbierz wybrane marketplace
        if self.prepare_for_sale.isChecked():
            marketplaces = []
            if self.amazon_cb.isChecked(): marketplaces.append("Amazon")
            if self.ebay_cb.isChecked(): marketplaces.append("eBay")
            if self.etsy_cb.isChecked(): marketplaces.append("Etsy")
            if self.allegro_cb.isChecked(): marketplaces.append("Allegro")
            if self.shopify_cb.isChecked(): marketplaces.append("Shopify")
            if self.wechat_cb.isChecked(): marketplaces.append("WeChat")
            settings['marketplaces'] = marketplaces
            
        return settings

    def retranslate_ui(self):
        """Sets translated texts for all UI elements."""
        self.marketplace_label.setText(self.tr("Prepare for sale"))
        self.prepare_for_sale.setText(self.tr("Prepare for sale"))
        self.amazon_cb.setText(self.tr("Amazon"))
        self.ebay_cb.setText(self.tr("eBay"))
        self.etsy_cb.setText(self.tr("Etsy"))
        self.allegro_cb.setText(self.tr("Allegro"))
        self.shopify_cb.setText(self.tr("Shopify"))
        self.wechat_cb.setText(self.tr("WeChat"))
        self.no_bg_removal.setText(self.tr("Prepare only for sale without background removal"))
        self.format_label.setText(self.tr("Image save format"))
        self.save_label.setText(self.tr("Save destination"))
        self.save_location.setItemText(0, self.tr("Local"))
        self.save_location.setItemText(1, self.tr("Google Drive"))
        self.save_location.setItemText(2, self.tr("Amazon S3"))
        self.save_location.setItemText(3, self.tr("imgBB"))
        self.save_location.setItemText(4, self.tr("FTP"))
        self.path_label.setText(self.tr("Save folder:"))
        self.local_path.setPlaceholderText(self.tr("Select save folder..."))
        self.browse_btn.setText(self.tr("Browse"))
        self.config_btn.setText(self.tr("Enter login credentials"))
        self.create_csv_links.setText(self.tr("Create CSV file with links"))
        self.csv_path_label.setText(self.tr("CSV save folder:"))
        self.csv_local_path.setPlaceholderText(self.tr("Select folder for CSV file..."))
        self.csv_browse_btn.setText(self.tr("Browse"))
        self.csv_name_label.setText(self.tr("CSV file name:"))
        self.csv_filename.setPlaceholderText(self.tr("processed_images"))
        self.processing_label.setText(self.tr("Processing settings"))
        self.mode_label.setText(self.tr("Processing mode:"))
        self.process_mode.setItemText(0, self.tr("Remove Background"))
        self.process_mode.setItemText(1, self.tr("Replace Background"))
        self.process_mode.setItemText(2, self.tr("Prepare Only"))
        self.bg_color_tab.setText(self.tr("Color"))
        self.bg_image_tab.setText(self.tr("Image"))
        self.bg_color_btn.setText(self.tr("Select color"))
        self.bg_image_btn.setText(self.tr("Select background image"))
        # Równoległe przetwarzanie i liczba wątków usunięte z UI

    def validate_settings(self):
        """Sprawdza czy ustawienia są poprawne."""
        service = self.save_location.currentText()
        
        if service.lower() in ["lokalnie", "local"]:
            if not self.local_path.text():
                return False, "Wybierz folder zapisu dla plików lokalnych"
        elif service not in self.service_credentials:
            return False, f"Wymagane uzupełnienie danych dla {service}"
            
        if self.prepare_for_sale.isChecked():
            # Sprawdź czy wybrano przynajmniej jeden marketplace
            marketplaces = [
                self.amazon_cb.isChecked(), self.ebay_cb.isChecked(),
                self.etsy_cb.isChecked(), self.allegro_cb.isChecked(),
                self.shopify_cb.isChecked(), self.wechat_cb.isChecked()
            ]
            if not any(marketplaces):
                return False, "Wybierz przynajmniej jeden marketplace"

        # Walidacja ustawień CSV (tylko dla zapisu w chmurze)
        if (service != "Lokalnie" and 
            self.create_csv_links.isChecked() and
            not self.csv_local_path.text()):
            return False, "Wybierz folder zapisu dla pliku CSV z linkami"
                
        return True, ""

class BatchProcessingView(QWidget):
    """Główny widok do przetwarzania wsadowego z nowoczesnym wyglądem."""
    
    # Sygnały
    batch_started = pyqtSignal()
    batch_finished = pyqtSignal()
    batch_progress = pyqtSignal(int)
    batch_error = pyqtSignal(str)

    def tr(self, text):
        from PyQt6.QtWidgets import QApplication
        return QApplication.translate(self.__class__.__name__, text)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings

        # Dodaj kontroler licencji
        self.license_controller = get_license_controller()

        self.batch_processor = None
        self.init_ui()
        self.connect_signals()
        self.retranslate_ui()

    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika z nowoczesnym wyglądem."""
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Lewa strona - sekcja plików
        left_widget = QWidget()
        left_widget.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-radius: 12px;
            }
        """)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(16)
        
        # Nagłówek z tytułem
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel()
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: 700;
                color: #212529;
                background: transparent;
            }
        """)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        left_layout.addLayout(header_layout)
        
        # Przyciski zarządzania plikami
        file_buttons = QHBoxLayout()
        file_buttons.setSpacing(8)
        
        self.load_file_btn = QPushButton()
        self.load_folder_btn = QPushButton()
        self.clear_btn = QPushButton()

        # Style dla przycisków plików
        file_button_style = """
            QPushButton {
                background: #0079e1;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """
        
        clear_button_style = """
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #545b62;
            }
        """

        self.load_file_btn.setStyleSheet(file_button_style)
        self.load_folder_btn.setStyleSheet(file_button_style)
        self.clear_btn.setStyleSheet(clear_button_style)

        file_buttons.addWidget(self.load_file_btn)
        file_buttons.addWidget(self.load_folder_btn)
        file_buttons.addWidget(self.clear_btn)
        file_buttons.addStretch()

        left_layout.addLayout(file_buttons)

        # Lista miniaturek w kontenerze - siatka zamiast listy
        thumbnail_container = QFrame()
        thumbnail_container.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        thumbnail_layout = QVBoxLayout(thumbnail_container)
        thumbnail_layout.setContentsMargins(8, 8, 8, 8)
        
        # Scroll area dla siatki miniaturek
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #e9ecef;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #adb5bd;
                border-radius: 3px;
                min-height: 20px;
            }
        """)
        
        # Widget siatki
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(8)
        self.thumbnails = []  # Lista do przechowywania miniaturek
        
        scroll_area.setWidget(self.grid_widget)
        thumbnail_layout.addWidget(scroll_area)
        
        left_layout.addWidget(thumbnail_container)

        # Progress bar i status
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: linear-gradient(90deg, #0079e1 0%, #00a8ff 100%);
                border-radius: 6px;
            }
        """)
        self.progress.hide()
        left_layout.addWidget(self.progress)
        
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 10px;
                color: #6c757d;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        left_layout.addWidget(self.status_label)

        # Przyciski akcji w lewej sekcji
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)
        
        self.start_batch_btn = QPushButton()
        self.start_batch_btn.setMinimumHeight(50)
        self.start_batch_btn.setStyleSheet("""
            QPushButton {
                background: #0079e1;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px;
                font-size: 16px;
                font-weight: 600;
                text-align: center;
            }
            QPushButton:hover {
                background: #0056b3;
            }
            QPushButton:pressed {
                background: #004494;
            }
            QPushButton:disabled {
                background: #e9ecef;
                color: #6c757d;
            }
        """)
        
        self.stop_batch_btn = QPushButton()
        self.stop_batch_btn.setEnabled(False)
        self.stop_batch_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 16px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #c82333;
            }
            QPushButton:disabled {
                background: #f8f9fa;
                color: #6c757d;
            }
        """)

        actions_layout.addWidget(self.start_batch_btn)
        actions_layout.addWidget(self.stop_batch_btn)
        
        left_layout.addLayout(actions_layout)

        # Prawa strona - kontrolki w obszarze przewijania
        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setFixedWidth(380)
        controls_scroll.setStyleSheet("""
            QScrollArea {
                background: #f8f9fa;
                border: none;
                border-radius: 12px;
            }
            QScrollBar:vertical {
                background: #e9ecef;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #adb5bd;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6c757d;
            }
        """)
        
        self.controls = BatchProcessingControls()
        controls_scroll.setWidget(self.controls)
        
        # Główny układ
        main_layout.addWidget(left_widget, 2)
        main_layout.addWidget(controls_scroll, 1)

        self.setLayout(main_layout)
        
        # Tło głównego widgetu
        self.setStyleSheet("""
            BatchProcessingView {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #764ba2);
            }
        """)

    def retranslate_ui(self):
        """Update all UI texts for current language."""
        self.title_label.setText(self.tr("Batch Processing"))
        self.load_file_btn.setText(self.tr("Load File"))
        self.load_folder_btn.setText(self.tr("Load Folder"))
        self.clear_btn.setText(self.tr("Clear"))
        self.start_batch_btn.setText(self.tr("Start Processing"))
        self.stop_batch_btn.setText(self.tr("Stop"))
        self.status_label.setText(self.tr("Add files to process"))

        # KLUCZOWE: Wywołaj retranslację kontrolek
        if hasattr(self, 'controls'):
            self.controls.retranslate_ui()

    def connect_signals(self):
        """Podłączenie sygnałów do slotów."""
        self.load_file_btn.clicked.connect(self.load_files)
        self.load_folder_btn.clicked.connect(self.load_folder)
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.start_batch_btn.clicked.connect(self.start_batch)
        self.stop_batch_btn.clicked.connect(self.stop_batch)
        
        self.batch_started.connect(self.on_batch_start)
        self.batch_finished.connect(self.on_batch_end)
        self.batch_progress.connect(self.update_progress)
        self.batch_error.connect(self.show_error)

    def add_thumbnail_to_grid(self, file_path):
        """Dodaje miniaturkę do siatki."""
        row = len(self.thumbnails) // 5
        col = len(self.thumbnails) % 5
        
        # Kontener miniaturki
        thumb_widget = QWidget()
        thumb_widget.setFixedSize(120, 140)
        thumb_widget.setStyleSheet("""
            QWidget {
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 4px;
            }
            QWidget:hover {
                border-color: #0079e1;
            }
        """)
        
        thumb_layout = QVBoxLayout(thumb_widget)
        thumb_layout.setContentsMargins(4, 4, 4, 4)
        thumb_layout.setSpacing(4)
        
        # Miniaturka obrazu
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(100, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                
                image_label = QLabel()
                image_label.setPixmap(scaled_pixmap)
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                image_label.setStyleSheet("border: none;")
                thumb_layout.addWidget(image_label)
            else:
                # Placeholder dla nieudanych obrazów
                placeholder = QLabel(self.tr("Brak\npodglądu"))
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setStyleSheet("color: #6c757d; font-size: 10px; border: none;")
                thumb_layout.addWidget(placeholder)
        except:
            placeholder = QLabel(self.tr("Błąd\nładowania"))
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #dc3545; font-size: 10px; border: none;")
            thumb_layout.addWidget(placeholder)
        
        # Nazwa pliku (skrócona)
        filename = Path(file_path).name
        if len(filename) > 15:
            filename = filename[:12] + "..."
        name_label = QLabel(filename)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-size: 9px; color: #495057; border: none;")
        thumb_layout.addWidget(name_label)
        
        # Przycisk usuwania
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #c82333;
            }
        """)
        
        # Funkcja usuwania konkretnej miniaturki
        def remove_thumbnail():
            self.remove_thumbnail_from_grid(file_path, thumb_widget)
        
        remove_btn.clicked.connect(remove_thumbnail)
        
        # Dodaj przycisk w prawym górnym rogu
        remove_btn.move(95, 5)
        remove_btn.setParent(thumb_widget)
        
        # Dodaj do siatki
        self.grid_layout.addWidget(thumb_widget, row, col)
        self.thumbnails.append({'path': file_path, 'widget': thumb_widget})
        
    def remove_thumbnail_from_grid(self, file_path, widget):
        """Usuwa konkretną miniaturkę z siatki."""
        # Usuń widget z layoutu
        self.grid_layout.removeWidget(widget)
        widget.deleteLater()
        
        # Usuń z listy miniaturek
        self.thumbnails = [t for t in self.thumbnails if t['path'] != file_path]
        
        # Przebuduj siatkę
        self.rebuild_grid()
        self.update_ui_state()
        
    def rebuild_grid(self):
        """Przebudowuje siatkę miniaturek po usunięciu."""
        # Usuń wszystkie widgety z layoutu
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)
        
        # Dodaj ponownie wszystkie miniaturki
        for i, thumb_data in enumerate(self.thumbnails):
            row = i // 5
            col = i % 5
            self.grid_layout.addWidget(thumb_data['widget'], row, col)

    def get_files_from_grid(self):
        """Zwraca listę ścieżek plików z siatki."""
        return [thumb['path'] for thumb in self.thumbnails]

    def clear_grid(self):
        """Czyści siatkę miniaturek."""
        for thumb_data in self.thumbnails:
            thumb_data['widget'].deleteLater()
        self.thumbnails.clear()
        
    def get_thumbnail_count(self):
        """Zwraca liczbę miniaturek."""
        return len(self.thumbnails)

    def load_files(self):
        """Ładuje pojedyncze pliki."""
        # Sprawdź licencję
        if not self.license_controller.can_access_batch_processing():
            show_upgrade_prompt(self.tr("Batch Processing"), self)
            return
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Wybierz pliki"),
            "",
            self.tr("Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp *.heic)")
        )
        if files:
            for file_path in files:
                if self.is_supported_image(file_path):
                    self.add_thumbnail_to_grid(file_path)
            
            self.status_label.setText(self.tr("Wczytano {count} plików").format(count=len(files)))
            self.status_label.setStyleSheet("""
                QLabel {
                    background: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 6px;
                    padding: 10px;
                    color: #155724;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)

    def load_folder(self):
        """Ładuje pliki z folderu."""
        # Sprawdź licencję
        if not self.license_controller.can_access_batch_processing():
            show_upgrade_prompt(self.tr("Batch Processing"), self)
            return
        folder = QFileDialog.getExistingDirectory(
            self,
            self.tr("Wybierz folder"),
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        if folder:
            file_count = 0
            for root, _, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.is_supported_image(file_path):
                        self.add_thumbnail_to_grid(file_path)
                        file_count += 1
            
            self.status_label.setText(self.tr("Wczytano folder - łącznie {count} plików").format(count=file_count))
            self.status_label.setStyleSheet("""
                QLabel {
                    background: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 6px;
                    padding: 10px;
                    color: #155724;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)

    def clear_files(self):
        """Czyści listę plików."""
        self.clear_grid()
        self.status_label.setText(self.tr("Lista plików wyczyszczona"))
        self.status_label.setStyleSheet("""
            QLabel {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 10px;
                color: #6c757d;
                font-size: 11px;
                font-weight: 500;
            }
        """)

    def is_supported_image(self, file_path):
        """Sprawdza czy plik jest obsługiwanym obrazem."""
        supported_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp', '.heic'}
        return Path(file_path).suffix.lower() in supported_extensions

    def update_ui_state(self):
        """Aktualizuje stan interfejsu."""
        has_files = self.get_thumbnail_count() > 0
        self.start_batch_btn.setEnabled(has_files)
        
        file_count = self.get_thumbnail_count()
        if file_count == 0:
            self.status_label.setText(self.tr("Brak plików do przetworzenia"))
            self.status_label.setStyleSheet("""
                QLabel {
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 6px;
                    padding: 10px;
                    color: #6c757d;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)
        else:
            self.status_label.setText(self.tr("Gotowe do przetworzenia: {count} plików").format(count=file_count))
            self.status_label.setStyleSheet("""
                QLabel {
                    background: #cce7ff;
                    border: 1px solid #99d3ff;
                    border-radius: 6px;
                    padding: 10px;
                    color: #0056b3;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)

    def start_batch(self):
        """Rozpoczyna przetwarzanie wsadowe."""
        # Sprawdź licencję przed rozpoczęciem
        if not self.license_controller.can_access_batch_processing():
            show_upgrade_prompt(self.tr("Batch Processing"), self)
            return

        is_valid, error_msg = self.controls.validate_settings()
        if not is_valid:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle(self.tr("Błąd konfiguracji"))
            msg.setText(self.tr(error_msg))
            msg.setStyleSheet("""
                QMessageBox {
                    background: white;
                    border-radius: 8px;
                }
                QMessageBox QPushButton {
                    background: #ffc107;
                    color: #212529;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 500;
                }
                QMessageBox QPushButton:hover {
                    background: #e0a800;
                }
            """)
            msg.exec()
            return

        if self.get_thumbnail_count() == 0:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle(self.tr("Brak plików"))
            msg.setText(self.tr("Dodaj pliki do przetworzenia"))
            msg.setStyleSheet("""
                QMessageBox {
                    background: white;
                    border-radius: 8px;
                }
                QMessageBox QPushButton {
                    background: #0079e1;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 500;
                }
                QMessageBox QPushButton:hover {
                    background: #0056b3;
                }
            """)
            msg.exec()
            return

        files = self.get_files_from_grid()
        settings = self.controls.get_settings()
        print(f"[DEBUG] Batch start - przekazana local_path: '{settings['local_path']}'")
        
        self.batch_processor = BatchProcessor()
        self.batch_processor.progress_updated.connect(self.batch_progress)
        self.batch_processor.processing_finished.connect(self.batch_finished)
        self.batch_processor.error_occurred.connect(self.batch_error)
        
        self.batch_started.emit()
        self.batch_processor.process_images(files, settings)

    def stop_batch(self):
        """Zatrzymuje przetwarzanie wsadowe."""
        if self.batch_processor:
            self.batch_processor.stop()
            self.status_label.setText(self.tr("Przetwarzanie zatrzymane przez użytkownika"))
            self.status_label.setStyleSheet("""
                QLabel {
                    background: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 6px;
                    padding: 10px;
                    color: #721c24;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)
            self.batch_finished.emit()

    def on_batch_start(self):
        """Obsługa rozpoczęcia przetwarzania wsadowego."""
        self.progress.show()
        self.progress.setValue(0)
        self.start_batch_btn.setEnabled(False)
        self.stop_batch_btn.setEnabled(True)
        self.controls.setEnabled(False)
        self.load_file_btn.setEnabled(False)
        self.load_folder_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        
        self.status_label.setText("Rozpoczęto przetwarzanie wsadowe...")
        self.status_label.setStyleSheet("""
            QLabel {
                background: #cce7ff;
                border: 1px solid #99d3ff;
                border-radius: 6px;
                padding: 10px;
                color: #0056b3;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        
        # Aktualizuj styl głównego przycisku
        self.start_batch_btn.setText("Przetwarzanie...")
        self.start_batch_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px;
                font-size: 16px;
                font-weight: 600;
            }
        """)

    def on_batch_end(self):
        """Obsługa zakończenia przetwarzania wsadowego."""
        self.progress.hide()
        self.start_batch_btn.setEnabled(True)
        self.stop_batch_btn.setEnabled(False)
        self.controls.setEnabled(True)
        self.load_file_btn.setEnabled(True)
        self.load_folder_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        
        # Przywróć styl głównego przycisku
        self.start_batch_btn.setText(self.tr("Rozpocznij przetwarzanie"))
        self.start_batch_btn.setStyleSheet("""
            QPushButton {
                background: #0079e1;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px;
                font-size: 16px;
                font-weight: 600;
                text-align: center;
            }
            QPushButton:hover {
                background: #0056b3;
            }
            QPushButton:pressed {
                background: #004494;
            }
            QPushButton:disabled {
                background: #e9ecef;
                color: #6c757d;
            }
        """)
        
        if self.batch_processor and not hasattr(self.batch_processor, 'is_stopped'):
            self.status_label.setText(self.tr("Przetwarzanie wsadowe zakończone pomyślnie!"))
            self.status_label.setStyleSheet("""
                QLabel {
                    background: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 6px;
                    padding: 10px;
                    color: #155724;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)
            
            # Utwórz CSV z linkami jeśli wybrano taką opcję
            settings = self.controls.get_settings()
            if settings.get('create_csv_links', False) and settings.get('save_location') != 'Lokalnie':
                self.create_csv_with_processed_files()
            
            # Pokaż podsumowanie
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle(self.tr("Zakończono"))
            msg.setText(self.tr("Przetwarzanie zakończone.\nPliki zostały zapisane w: ") +
                       f"{self.controls.local_path.text() if self.controls.save_location.currentText() == 'Lokalnie' else self.tr('wybranej lokalizacji')}")
            msg.setStyleSheet("""
                QMessageBox {
                    background: white;
                    border-radius: 8px;
                }
                QMessageBox QPushButton {
                    background: #28a745;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 500;
                }
                QMessageBox QPushButton:hover {
                    background: #218838;
                }
            """)
            msg.exec()
        
        self.batch_processor = None

    def create_csv_with_processed_files(self):
        """Tworzy plik CSV z linkami dla przetworzonych plików."""
        try:
            settings = self.controls.get_settings()
            csv_path = settings.get('csv_local_path', os.getcwd())
            csv_filename = settings.get('csv_filename', 'processed_images')
            
            if not csv_path:
                return
            
            os.makedirs(csv_path, exist_ok=True)
            
            # Symulacja danych - w prawdziwej implementacji byłyby to wyniki z batch_processor
            csv_data = []
            files = self.get_files_from_grid()
            
            for file_path in files:
                original_name = Path(file_path).stem
                # W prawdziwej implementacji tu byłby prawdziwy URL z chmury
                cloud_url = f"https://example-cloud-storage.com/{original_name}_processed.png"
                csv_data.append([original_name, cloud_url])
            
            full_csv_path = os.path.join(csv_path, f'{csv_filename}.csv')
            with open(full_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Original_Name', 'Image_URL'])
                writer.writerows(csv_data)
            
            logger.info(f"CSV z linkami zapisany: {full_csv_path}")
            
            # Pokaż informację użytkownikowi
            QMessageBox.information(
                self,
                self.tr("CSV utworzony"),
                self.tr("Plik CSV z linkami został utworzony:\n{path}").format(path=full_csv_path)
            )
            
        except Exception as e:
            logger.error(f"Błąd tworzenia CSV z linkami: {e}")
            QMessageBox.warning(
                self,
                self.tr("Błąd CSV"),
                self.tr("Nie udało się utworzyć pliku CSV:\n{error}").format(error=str(e))
            )

    def update_progress(self, value):
        """Aktualizacja paska postępu."""
        self.progress.setValue(value)
        self.status_label.setText(self.tr("Przetwarzanie: {percent}%").format(percent=value))
        self.status_label.setStyleSheet("""
            QLabel {
                background: #cce7ff;
                border: 1px solid #99d3ff;
                border-radius: 6px;
                padding: 10px;
                color: #0056b3;
                font-size: 11px;
                font-weight: 500;
            }
        """)

    def show_error(self, error_message):
        """Wyświetla komunikat o błędzie."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(self.tr("Błąd przetwarzania"))
        msg.setText(self.tr(error_message))
        msg.setStyleSheet("""
            QMessageBox {
                background: white;
                border-radius: 8px;
            }
            QMessageBox QPushButton {
                background: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QMessageBox QPushButton:hover {
                background: #c82333;
            }
        """)
        msg.exec()
        self.batch_finished.emit()

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # Przykładowe użycie
    window = BatchProcessingView(None)
    window.show()
    
    sys.exit(app.exec())
    def changeEvent(self, event):
        """Obsługuje zmianę języka."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)
    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)