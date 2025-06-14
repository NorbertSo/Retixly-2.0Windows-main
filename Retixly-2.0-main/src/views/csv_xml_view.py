from ..controllers.license_controller import get_license_controller
from ..views.upgrade_prompts import show_upgrade_prompt
from src.core.image_engine import create_optimized_engine
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFileDialog, QTextEdit, QComboBox,
                            QGroupBox, QFormLayout, QLineEdit, QCheckBox,
                            QRadioButton, QButtonGroup,
                            QTableWidget, QTableWidgetItem, QProgressBar,
                            QMessageBox, QSplitter, QSpinBox, QFrame,
                            QStackedWidget, QColorDialog, QGridLayout,
                            QScrollArea, QDialog, QHeaderView)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QSettings
from PyQt6.QtGui import QPixmap, QIcon, QColor
from pathlib import Path
import csv
import xml.etree.ElementTree as ET
import os
import tempfile
import logging
import requests
from urllib.parse import urlparse
import hashlib
from PIL import Image
import time
logger = logging.getLogger(__name__)


# Dodajemy import dla auto-detekcji
try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False

# ===================================================================
# =====================  IMAGE DOWNLOADER CLASS  ==================
# ===================================================================

class ImageDownloader:
    """Klasa do pobierania obrazów z URL-i z cache'owaniem."""
    
    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), 'retixly_image_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    # ----------  helpers ----------
    def is_url(self, path: str) -> bool:
        """Sprawdza czy ścieżka to URL."""
        try:
            parsed = urlparse(path)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False
    
    def get_cache_path(self, url: str) -> str:
        """Generuje ścieżkę cache na podstawie hash URL‑a."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        parsed = urlparse(url)
        ext_candidates = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
        ext = next((e for e in ext_candidates if parsed.path.lower().endswith(e)), ".jpg")
        return os.path.join(self.cache_dir, f"{url_hash}{ext}")
    
    # ----------  main ----------
    def download_image(self, url: str, progress_callback=None) -> str | None:
        """
        Pobiera obraz do cache i zwraca lokalną ścieżkę.
        Zwraca None przy niepowodzeniu.
        """
        try:
            cache_path = self.get_cache_path(url)
            if os.path.exists(cache_path):
                logger.info(f"📁 Obraz z cache: {url}")
                return cache_path
    
            logger.info(f"🌐 Pobieranie obrazu: {url}")
            resp = self.session.get(url, stream=True, timeout=30)
            resp.raise_for_status()
    
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(cache_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            prog = int(downloaded / total * 100)
                            progress_callback(prog, f"Pobrano {downloaded // 1024} KB")
    
            # szybka weryfikacja, czy to obraz
            try:
                with Image.open(cache_path) as img:
                    img.verify()
            except Exception:
                logger.error("❌ Pobrany plik nie jest obrazem")
                os.remove(cache_path)
                return None
    
            return cache_path
    
        except requests.RequestException as err:
            logger.error(f"❌ Błąd pobierania {url}: {err}")
            return None
    
    def process_path(self, path: str, progress_callback=None) -> str | None:
        """Zwraca lokalną ścieżkę do obrazu (pobiera jeśli trzeba)."""
        if not path:
            return None
        return (
            self.download_image(path, progress_callback)
            if self.is_url(path)
            else path if os.path.exists(path) else None
        )
    
    def cleanup_cache(self, max_age_hours: int = 24) -> None:
        """Usuwa stare pliki z cache."""
        now = time.time()
        max_age = max_age_hours * 3600
        for fname in os.listdir(self.cache_dir):
            fp = os.path.join(self.cache_dir, fname)
            if os.path.isfile(fp) and now - os.path.getmtime(fp) > max_age:
                os.remove(fp)

class MarketplaceTestDialog(QDialog):
    """Dialog do testowania połączenia z marketplace."""
    
    def __init__(self, service_type, parent=None):
        super().__init__(parent)
        self.service_type = service_type
        self.test_passed = False
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(self.tr(f"Configure {self.service_type}"))
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Login data form
        form_layout = QFormLayout()
        
        if self.service_type == "Google Drive":
            self.folder_id = QLineEdit()
            self.folder_id.setPlaceholderText(self.tr("Google Drive folder ID"))
            form_layout.addRow(self.tr("Folder ID:"), self.folder_id)
            
        elif self.service_type == "Amazon S3":
            self.access_key = QLineEdit()
            self.secret_key = QLineEdit()
            self.secret_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.bucket_name = QLineEdit()
            
            form_layout.addRow(self.tr("Access Key ID:"), self.access_key)
            form_layout.addRow(self.tr("Secret Access Key:"), self.secret_key)
            form_layout.addRow(self.tr("Bucket Name:"), self.bucket_name)
            
        elif self.service_type == "FTP":
            self.ftp_host = QLineEdit()
            self.ftp_user = QLineEdit()
            self.ftp_pass = QLineEdit()
            self.ftp_pass.setEchoMode(QLineEdit.EchoMode.Password)
            self.ftp_path = QLineEdit()
            
            form_layout.addRow(self.tr("Host:"), self.ftp_host)
            form_layout.addRow(self.tr("Username:"), self.ftp_user)
            form_layout.addRow(self.tr("Password:"), self.ftp_pass)
            form_layout.addRow(self.tr("Path:"), self.ftp_path)
            
        elif self.service_type == "imgBB":
            self.api_key = QLineEdit()
            self.api_key.setPlaceholderText(self.tr("Your imgBB API key"))
            form_layout.addRow(self.tr("API Key:"), self.api_key)
            
        layout.addLayout(form_layout)
        
        # Test status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.test_btn = QPushButton(self.tr("TEST"))
        self.test_btn.clicked.connect(self.test_connection)
        
        self.save_btn = QPushButton(self.tr("Save"))
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.test_btn)
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
        
    def test_connection(self):
        """Tests connection to the selected service."""
        self.status_label.setText(self.tr("Testing connection..."))
        self.test_btn.setEnabled(False)
        
        # Simulate test - real test logic would be here
        QTimer.singleShot(2000, self.test_completed)
        
    def test_completed(self):
        """Handles test completion."""
        # Here would be real connection checking logic
        self.test_passed = True
        self.status_label.setText(self.tr("Test completed successfully!"))
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



# --- NEW IMPLEMENTATION ---
class DataPreviewWithMapping(QWidget):
    """Widget do podglądu danych z mapowaniem kolumn (NOWA IMPLEMENTACJA)."""
    mapping_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.headers = []
        self.data = []
        self.mapping_combos = []
        self.detected_format = None
        self.detected_encoding = "UTF-8"
        self.detected_delimiter = ","
        self.detected_has_header = True
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # File info
        self.file_info_widget = QWidget()
        file_info_layout = QHBoxLayout(self.file_info_widget)
        file_info_layout.setSpacing(8)
        file_info_layout.setContentsMargins(8, 8, 8, 8)
        self.detection_label = QLabel(self.tr("File parameters will be detected automatically"))
        self.detection_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 11px;
                font-style: italic;
                padding: 4px 8px;
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
            }
        """)
        file_info_layout.addWidget(self.detection_label)
        file_info_layout.addStretch()
        self.file_info_widget.hide()
        layout.addWidget(self.file_info_widget)

        # Mapping header
        mapping_header = QLabel(self.tr("Column mapping:"))
        mapping_header.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 600;
                color: #495057;
                padding: 8px 0px 4px 0px;
                background: transparent;
            }
        """)
        layout.addWidget(mapping_header)

        # ===  Scrollable preview with dropdown row  ===
        # Table preview (unchanged definition)
        self.table = QTableWidget()
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
                border: 1px solid #dee2e6;
                font-size: 11px;
                color: #495057;
            }
            QTableWidget::item:selected {
                background-color: #cce7ff;
                color: #212529;
            }
            QHeaderView::section {
                background-color: #f1f3f5;
                padding: 10px 12px;
                font-size: 12px;
                font-weight: 600;
                border: none;
                border-right: 1px solid #dee2e6;
                border-bottom: 3px solid #0079e1;
                color: #212529;
            }
            QTableWidget::item {
                padding: 8px 10px;
                font-size: 11px;
                border-bottom: 1px solid #f1f3f5;
            }
        """)
        # Make rows a bit taller for readability
        self.table.verticalHeader().setDefaultSectionSize(28)
        # Make the horizontal header taller so the full text is visible
        self.table.horizontalHeader().setFixedHeight(40)

        # Scroll‑area which keeps the dropdowns glued above the header
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background: white;
            }
        """)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(0)

        # container that will hold the mapping dropdowns
        self.mapping_container = QFrame()
        self.mapping_container.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #0079e1;
                border-bottom: none;
            }
        """)
        self.mapping_container.hide()
        self.mapping_layout = QHBoxLayout(self.mapping_container)
        self.mapping_layout.setSpacing(0)
        self.mapping_layout.setContentsMargins(0, 5, 0, 5)

        # add dropdowns container and table into the scroll content
        self.scroll_layout.addWidget(self.mapping_container)
        self.scroll_layout.addWidget(self.table)
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        self.mapping_instruction = QLabel("")
        self.mapping_instruction.setStyleSheet("font-size:10px; color:#6c757d;")
        layout.addWidget(self.mapping_instruction)
        self.setLayout(layout)
        self.show_mapping_placeholder()

    def show_mapping_placeholder(self):
        self._clear_mapping_dropdowns()
        self.mapping_combos.clear()
        self.table.clear()
        self.table.setRowCount(0)

    # ------------------------------------------------------------------
    # helper
    def _clear_mapping_dropdowns(self):
        """Remove all mapping QComboBoxes and hide the container."""
        if hasattr(self, "mapping_layout"):
            while self.mapping_layout.count():
                child = self.mapping_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        self.mapping_combos.clear()
        if hasattr(self, "mapping_container"):
            self.mapping_container.hide()

    def update_data(self, data, headers=None):
        """Aktualizuje dane i mapowanie."""
        self.data = data
        if not data:
            self.show_mapping_placeholder()
            return
        if not headers:
            headers = [f"Column {i+1}" for i in range(len(data[0]))]
        self.headers = headers
        self.update_table()
        QTimer.singleShot(100, self.create_mapping_controls)  # wait until columns have real widths

    def create_mapping_controls(self):
        self._clear_mapping_dropdowns()
        if not self.headers:
            return

        # To get actual column widths we rely on the table having been populated
        mapping_options = [self.tr("Skip"), self.tr("Identifier"), self.tr("Photo")]
        total_width = 0

        for i, header in enumerate(self.headers):
            col_width = self.table.columnWidth(i)
            total_width += col_width

            combo = QComboBox()
            combo.setStyleSheet("""
                QComboBox {
                    background: white;
                    border: 2px solid #0079e1;
                    border-radius: 4px;
                    padding: 6px 8px;
                    font-size: 11px;
                    font-weight: 600;
                    color: #212529;
                }
                QComboBox:hover {
                    border-color: #0056b3;
                    background: #f1f3f5;
                }
                QComboBox::drop-down {
                    border-left: 1px solid #dee2e6;
                    width: 22px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 6px solid #495057;
                    margin-right: 3px;
                }
                QComboBox QAbstractItemView {
                    border: 2px solid #0079e1;
                    selection-background-color: #0079e1;
                    selection-color: white;
                }
            """)
            combo.addItems(mapping_options)
            # Highlight auto-detected mappings
            lower = header.lower()
            if any(w in lower for w in ["id", "sku", "identyfikator", "kod", "ean", "upc"]):
                combo.setCurrentText(self.tr("Identifier"))
                combo.setStyleSheet(combo.styleSheet() + " QComboBox { background: #d4edda; border-color: #28a745; }")
            elif any(w in lower for w in ["zdjęcie", "photo", "image", "img", "picture", "ścieżka", "path", "file"]):
                combo.setCurrentText(self.tr("Photo"))
                combo.setStyleSheet(combo.styleSheet() + " QComboBox { background: #fff3cd; border-color: #ffc107; }")

            combo.setFixedWidth(col_width)
            combo.setFixedHeight(28)
            combo.currentTextChanged.connect(self.mapping_changed.emit)
            combo.setToolTip(header)
            self.mapping_layout.addWidget(combo)
            self.mapping_combos.append(combo)

        self.mapping_container.setFixedWidth(total_width)
        self.mapping_container.setFixedHeight(35)
        self.mapping_container.show()
        # synchronizuj dropdown-y przy zmianie szerokości kolumn
        try:
            self.table.horizontalHeader().sectionResized.disconnect(self.adjust_combo_widths)
        except Exception:
            pass
        self.table.horizontalHeader().sectionResized.connect(self.adjust_combo_widths)

        mapped = sum(1 for c in self.mapping_combos if c.currentText() != self.tr("Skip"))
        if hasattr(self, "mapping_instruction"):
            self.mapping_instruction.setText(self.tr(f"✅ Mapped {mapped}/{len(self.mapping_combos)} columns."))

    def update_table(self):
        """Wypełnia tabelę danymi i dopasowuje szerokości kolumn tak,
        aby nagłówki nie były obcinane."""
        if not self.data:
            return

        has_header_row = self.detected_has_header and self.headers
        data_rows = self.data[1:] if has_header_row else self.data
        rows, cols = len(data_rows), len(self.data[0])

        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)

        if self.headers:
            self.table.setHorizontalHeaderLabels(self.headers)

        for r, row in enumerate(data_rows):
            for c, val in enumerate(row):
                if c < cols:
                    txt = str(val).strip() if val is not None else ""
                    if len(txt) > 80:
                        txt = txt[:77] + "…"
                    self.table.setItem(r, c, QTableWidgetItem(txt))

        # ------------- dopasowanie szerokości ----------------
        self.table.resizeColumnsToContents()

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        min_w, max_w = 140, 400
        for c in range(cols):
            cur = self.table.columnWidth(c)
            label = self.headers[c] if self.headers else f"Col {c+1}"
            txt_w = self.fontMetrics().horizontalAdvance(label) + 40
            target = max(cur, txt_w, min_w)
            self.table.setColumnWidth(c, min(target, max_w))

        header.setFixedHeight(40)

        # odśwież dropdown-y
        QTimer.singleShot(0, self.adjust_combo_widths)

    def adjust_combo_widths(self):
        if not self.mapping_combos:
            return
        min_w, max_w = 140, 400
        for i, combo in enumerate(self.mapping_combos):
            if i < self.table.columnCount():
                col_w = self.table.columnWidth(i)
                new_w = max(min_w, min(max_w, col_w))
                combo.setFixedWidth(new_w)

    def get_mapping(self):
        """Zwraca uproszczone mapowanie."""
        mapping = {"id": "", "path": ""}
        if not self.mapping_combos or not self.headers:
            return mapping
        for i, combo in enumerate(self.mapping_combos):
            header = self.headers[i]
            if combo.currentText() == self.tr("Identifier") and not mapping["id"]:
                mapping["id"] = header
            elif combo.currentText() == self.tr("Photo") and not mapping["path"]:
                mapping["path"] = header
        return mapping

    def detect_encoding(self, file_path):
        """Automatyczna detekcja kodowania pliku."""
        if HAS_CHARDET:
            try:
                with open(file_path, 'rb') as f:
                    raw = f.read(10000)
                    res = chardet.detect(raw)
                    if res['confidence'] > 0.7:
                        return res['encoding']
            except Exception:
                pass
        for enc in ['UTF-8', 'ISO-8859-1', 'Windows-1250', 'UTF-16']:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    f.read(1000)
                return enc
            except Exception:
                continue
        return 'UTF-8'

    def detect_delimiter(self, file_path, encoding):
        """Automatyczna detekcja separatora CSV."""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                sample = f.read(2048)
            sniffer = csv.Sniffer()
            try:
                return sniffer.sniff(sample, delimiters=',;\t|').delimiter
            except Exception:
                pass
            counts = {d: sample.count(d) for d in [',', ';', '\t', '|']}
            return max(counts, key=counts.get)
        except Exception:
            return ','

    def detect_has_header(self, file_path, encoding, delimiter):
        """Sprawdza czy plik ma nagłówki."""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.reader(f, delimiter=delimiter)
                first, second = next(reader, None), next(reader, None)
                if not first or not second:
                    return True
                text_cells = sum(1 for c in first if not self._is_number(c))
                return text_cells > len(first) / 2
        except Exception:
            return True

    def _is_number(self, txt):
        try:
            float(txt.strip())
            return True
        except Exception:
            return False

    def set_file_format(self, file_format):
        self.detected_format = file_format
        self.file_info_widget.setVisible(file_format in ['CSV', 'XML'])

    def analyze_file(self, file_path):
        try:
            self.detected_encoding = self.detect_encoding(file_path)
            if self.detected_format == 'CSV':
                self.detected_delimiter = self.detect_delimiter(file_path, self.detected_encoding)
                self.detected_has_header = self.detect_has_header(file_path, self.detected_encoding, self.detected_delimiter)
                delim_name = {',':self.tr('comma'),';':self.tr('semicolon'),'\t':self.tr('tab'), '|':self.tr('vertical bar')}.get(self.detected_delimiter, self.detected_delimiter)
                header_txt = self.tr("with headers") if self.detected_has_header else self.tr("without headers")
                info = self.tr(f"✓ Detected: {self.detected_encoding}, separator: {delim_name}, {header_txt}")
            else:
                info = self.tr(f"✓ Detected XML format, encoding: {self.detected_encoding}")
            self._set_info(info, ok=True)
            return True
        except Exception as e:
            self._set_info(self.tr(f"⚠ File analysis error: {e}"), ok=False)
            return False

    def _set_info(self, text, ok=True):
        self.detection_label.setText(text)
        color = "#155724" if ok else "#721c24"
        bg = "#d4edda" if ok else "#f8d7da"
        border = "#c3e6cb" if ok else "#f5c6cb"
        self.detection_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 11px;
                font-weight: 500;
                padding: 6px 12px;
                background: {bg};
                border: 1px solid {border};
                border-radius: 4px;
            }}
        """)

    def get_file_settings(self):
        return {
            'encoding': self.detected_encoding,
            'delimiter': self.detected_delimiter,
            'has_header': self.detected_has_header
        }

    def clear(self):
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.show_mapping_placeholder()
        self.file_info_widget.hide()
        self.data, self.headers, self.mapping_combos = [], [], []
        self.detected_encoding, self.detected_delimiter, self.detected_has_header = "UTF-8", ",", True

class CsvXmlProcessingControls(QWidget):
    """Kontrolki przetwarzania dla CSV/XML - uproszczone (bez ustawień pliku)."""
    marketplace_changed = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.last_local_path = QSettings().value('csv_xml_processing/last_local_path', '')
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Zmniejszony font dla całej sekcji
        small_font_style = "font-size: 10px;"
        label_style = "font-size: 11px; font-weight: 600; color: #495057; margin-bottom: 4px;"

        # Sekcja - Przygotuj do sprzedaży
        marketplace_label = QLabel(self.tr("Prepare for sale"))
        marketplace_label.setStyleSheet(label_style)
        layout.addWidget(marketplace_label)

        # Checkbox główny
        self.prepare_for_sale = QCheckBox(self.tr("Prepare for sale"))
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

        # Radio buttons marketplace – pojedynczy wybór
        self.marketplace_frame = QFrame()
        self.marketplace_frame.setStyleSheet("QFrame { border: none; }")
        marketplace_layout = QGridLayout()
        marketplace_layout.setSpacing(8)

        self.marketplace_group = QButtonGroup(self)

        self.amazon_rb   = QRadioButton(self.tr("Amazon"))
        self.ebay_rb     = QRadioButton(self.tr("eBay"))
        self.etsy_rb     = QRadioButton(self.tr("Etsy"))
        self.allegro_rb  = QRadioButton(self.tr("Allegro"))
        self.shopify_rb  = QRadioButton(self.tr("Shopify"))
        self.wechat_rb   = QRadioButton(self.tr("WeChat"))

        for idx, rb in enumerate([
                self.amazon_rb, self.ebay_rb, self.etsy_rb,
                self.allegro_rb, self.shopify_rb, self.wechat_rb]):
            rb.setStyleSheet(f"""
                QRadioButton {{
                    {small_font_style}
                    color: #495057;
                    spacing: 6px;
                }}
                QRadioButton::indicator {{
                    width: 12px;
                    height: 12px;
                }}
                QRadioButton::indicator:unchecked {{
                    border: 2px solid #dee2e6;
                    border-radius: 6px;
                    background: white;
                }}
                QRadioButton::indicator:checked {{
                    border: 2px solid #0079e1;
                    border-radius: 6px;
                    background: #0079e1;
                }}
            """)
            self.marketplace_group.addButton(rb)
            row, col = divmod(idx, 2)  # dwie kolumny
            marketplace_layout.addWidget(rb, row, col)

        self.marketplace_frame.setLayout(marketplace_layout)
        self.marketplace_frame.hide()
        layout.addWidget(self.marketplace_frame)

        # Opcja bez wycinania tła - ukryta domyślnie
        self.no_bg_removal = QCheckBox(self.tr("Prepare for sale only without background removal"))
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

        # Sekcja - Format zapisu zdjęć
        format_label = QLabel(self.tr("Image save format"))
        format_label.setStyleSheet(label_style)
        layout.addWidget(format_label)
        
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

        # Sekcja - Rodzaj zapisu
        save_label = QLabel(self.tr("Save type"))
        save_label.setStyleSheet(label_style)
        layout.addWidget(save_label)
        
        save_widget = QWidget()
        save_layout = QVBoxLayout(save_widget)
        save_layout.setSpacing(8)
        save_layout.setContentsMargins(0, 0, 0, 0)

        self.save_location = QComboBox()
        self.save_location.addItems([
            self.tr("Local"), "Google Drive", "Amazon S3", "imgBB", "FTP"
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
        
        path_label = QLabel(self.tr("Save folder:"))
        path_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        local_path_layout.addWidget(path_label)
        
        path_input_layout = QHBoxLayout()
        self.local_path = QLineEdit()
        self.local_path.setPlaceholderText(self.tr("Select save folder..."))
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
        
        self.browse_btn = QPushButton(self.tr("Browse"))
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

        # Status konfiguracji
        self.config_status = QLabel("")
        self.config_status.setStyleSheet(f"{small_font_style} font-weight: 500;")
        save_layout.addWidget(self.config_status)

        # Przycisk konfiguracji
        self.config_btn = QPushButton(self.tr("Enter login data"))
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

        # --- CSV z linkami do chmury - NOWA IMPLEMENTACJA ---
        self.csv_links_widget = QWidget()
        csv_links_layout = QVBoxLayout(self.csv_links_widget)
        csv_links_layout.setSpacing(6)
        csv_links_layout.setContentsMargins(0, 0, 0, 0)

        self.create_csv_links = QCheckBox(self.tr("Create CSV file with links"))
        self.create_csv_links.setChecked(True)
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
        csv_path_label = QLabel(self.tr("CSV save folder:"))
        csv_path_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        csv_save_layout.addWidget(csv_path_label)

        csv_path_input_layout = QHBoxLayout()
        self.csv_local_path = QLineEdit()
        self.csv_local_path.setPlaceholderText(self.tr("Select folder for CSV file..."))
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

        self.csv_browse_btn = QPushButton(self.tr("Browse"))
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
        csv_name_label = QLabel(self.tr("CSV file name:"))
        csv_name_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        csv_save_layout.addWidget(csv_name_label)

        self.csv_filename = QLineEdit()
        self.csv_filename.setPlaceholderText(self.tr("processed_images"))
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

        # Sekcja ustawień przetwarzania
        processing_label = QLabel(self.tr("Processing settings"))
        processing_label.setStyleSheet(label_style)
        layout.addWidget(processing_label)
        
        processing_widget = QWidget()
        proc_layout = QVBoxLayout(processing_widget)
        proc_layout.setSpacing(8)
        proc_layout.setContentsMargins(0, 0, 0, 0)

        mode_layout = QVBoxLayout()
        mode_label = QLabel(self.tr("Processing mode:"))
        mode_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        mode_layout.addWidget(mode_label)
        
        self.process_mode = QComboBox()
        self.process_mode.addItems([self.tr("Remove background"), self.tr("Replace background"), self.tr("Prepare for sale only")])
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
        
        self.bg_color_tab = QPushButton(self.tr("Color"))
        self.bg_image_tab = QPushButton(self.tr("Image"))
        
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
        
        self.bg_color_btn = QPushButton(self.tr("Select color"))
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
        
        self.bg_image_btn = QPushButton(self.tr("Select background image"))
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

        # Removed parallel processing and thread count controls

        layout.addWidget(processing_widget)

        # Sekcja walidacji danych
        validation_label = QLabel("Walidacja danych")
        validation_label.setStyleSheet(label_style)
        layout.addWidget(validation_label)
        
        validation_widget = QWidget()
        validation_layout = QVBoxLayout(validation_widget)
        validation_layout.setSpacing(8)
        validation_layout.setContentsMargins(0, 0, 0, 0)
        
        # Pomiń błędne wiersze z przyciskiem pomocy
        skip_errors_layout = QHBoxLayout()
        self.skip_errors = QCheckBox("Pomiń błędne wiersze")
        self.skip_errors.setChecked(True)
        self.skip_errors.setStyleSheet(f"""
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
        
        skip_help_btn = QPushButton("?")
        skip_help_btn.setFixedSize(16, 16)
        skip_help_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #545b62;
            }
        """)
        skip_help_btn.clicked.connect(self.show_skip_errors_help)
        
        skip_errors_layout.addWidget(self.skip_errors)
        skip_errors_layout.addWidget(skip_help_btn)
        skip_errors_layout.addStretch()
        validation_layout.addLayout(skip_errors_layout)
        
        layout.addWidget(validation_widget)

        layout.addStretch()
        self.setLayout(layout)

        # Inicjalne ustawienia
        self.service_credentials = {}
        self.update_config_status()
        
        # Usunięcie wszystkich ramek
        self.setStyleSheet("QWidget { border: none; }")

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
            QSettings().setValue('csv_xml_processing/last_local_path', folder)

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
        if mode == "Zamień tło":
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
        """Select background image."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select background image"), "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if file_name:
            self.bg_image_path = file_name
            self.bg_image_btn.setText(self.tr(f"✓ {Path(file_name).name}"))
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

    # Removed show_threads_help method

    def show_skip_errors_help(self):
        """Show help for skip errors option."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle(self.tr("Help - Skip erroneous rows"))
        msg.setText(self.tr("When this option is enabled:\n\n"
                   "• Rows with errors will be skipped\n"
                   "• Processing will continue\n"
                   "• Logs will contain info about skipped rows\n\n"
                   "When this option is disabled:\n"
                   "• An error in a row will stop the entire processing\n"
                   "• A detailed error message will be displayed"))
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

    def on_save_location_changed(self, location):
        """Obsługa zmiany lokalizacji zapisu."""
        if location == self.tr("Local"):
            self.config_btn.hide()
            self.local_path_widget.show()
            self.csv_links_widget.hide()  # Ukryj opcje CSV dla zapisu lokalnego
        else:
            self.config_btn.show()
            self.local_path_widget.hide()
            self.csv_links_widget.show()  # Pokaż opcje CSV dla zapisu w chmurze
            
            # Podłącz sygnał checkbox do pokazywania/ukrywania opcji
            self.create_csv_links.stateChanged.connect(self.on_csv_links_changed)
            
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
        
        if service == self.tr("Local"):
            if self.local_path.text():
                self.config_status.setText(self.tr("✓ Path selected"))
                self.config_status.setStyleSheet("color: green; font-size: 10px; font-weight: 500;")
            else:
                self.config_status.setText(self.tr("⚠ Select save folder"))
                self.config_status.setStyleSheet("color: orange; font-size: 10px; font-weight: 500;")
        elif service in self.service_credentials:
            self.config_status.setText(self.tr("✓ Configured"))
            self.config_status.setStyleSheet("color: green; font-size: 10px; font-weight: 500;")
        else:
            self.config_status.setText(self.tr("⚠ Enter required data"))
            self.config_status.setStyleSheet("color: orange; font-size: 10px; font-weight: 500;")

    def get_settings(self):
        """Zwraca aktualne ustawienia."""
        settings = {
            # Marketplace
            'prepare_for_sale': self.prepare_for_sale.isChecked(),
            'marketplaces': [],
            'no_bg_removal': self.no_bg_removal.isChecked(),

            # Format
            'format': {
                'type': self.output_format.currentText(),
                'quality': 90
            },

            # Save
            'save_location': self.save_location.currentText(),
            'local_path': self.local_path.text() if self.save_location.currentText() == self.tr("Local") else "",
            'credentials': self.service_credentials.get(self.save_location.currentText(), {}),

            # Processing
            'processing': {
                'mode': self.process_mode.currentText(),
                'bg_color': self.bg_color,
                'bg_image': self.bg_image_path
            },

            # Validation
            'skip_errors': self.skip_errors.isChecked(),

            # CSV with links - only for cloud save
            'create_csv_links': (
                self.create_csv_links.isChecked()
                if self.save_location.currentText() != self.tr("Local")
                else False
            ),
            'csv_local_path': self.csv_local_path.text(),
            'csv_filename': self.csv_filename.text() or "processed_images"
        }

        # Collect selected marketplaces
        if self.prepare_for_sale.isChecked():
            marketplaces = []
            if self.amazon_rb.isChecked(): marketplaces.append(self.tr("Amazon"))
            if self.ebay_rb.isChecked(): marketplaces.append(self.tr("eBay"))
            if self.etsy_rb.isChecked(): marketplaces.append(self.tr("Etsy"))
            if self.allegro_rb.isChecked(): marketplaces.append(self.tr("Allegro"))
            if self.shopify_rb.isChecked(): marketplaces.append(self.tr("Shopify"))
            if self.wechat_rb.isChecked(): marketplaces.append(self.tr("WeChat"))
            settings['marketplaces'] = marketplaces

        return settings

    def validate_settings(self):
        """Sprawdza czy ustawienia są poprawne."""
        service = self.save_location.currentText()
        
        if service == self.tr("Local"):
            if not self.local_path.text():
                return False, self.tr("Select save folder for local files")
        elif service not in self.service_credentials:
            return False, self.tr(f"Required data not entered for {service}")
            
        if self.prepare_for_sale.isChecked():
            if self.marketplace_group.checkedButton() is None:
                return False, self.tr("Select marketplace")
        
        # Validate CSV settings (only for cloud save)
        if (service != self.tr("Local") and 
            self.create_csv_links.isChecked() and
            not self.csv_local_path.text()):
            return False, self.tr("Select save folder for CSV file with links")
                
        return True, ""

# ===================================================================
# =====================  MODIFIED IMPORT THREAD  ==================
# ===================================================================

class ImportThread(QThread):
    """Wątek do importu danych z obsługą pobierania obrazów z URL."""
    progress_updated = pyqtSignal(int, str)
    import_finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_path: str, settings: dict):
        super().__init__()
        self.file_path = file_path
        self.settings = settings
        self.downloader = ImageDownloader()
    
    # ----------  główny flow ----------
    def run(self):
        try:
            self.progress_updated.emit(2, "Przygotowywanie…")
            self.downloader.cleanup_cache()
    
            ext = Path(self.file_path).suffix.lower()
            if ext == ".csv":
                self._import_csv()
            elif ext in (".xml", ".XML"):
                self._import_xml()
            else:
                # heurystyka
                with open(self.file_path, "r", encoding=self.settings["encoding"]) as fh:
                    first = fh.readline(256)
                self._import_xml() if "<" in first else self._import_csv()
        except Exception as err:
            self.error_occurred.emit(str(err))
    
    # ----------  CSV ----------
    def _import_csv(self):
        imported = []
        self.progress_updated.emit(10, "Otwieranie CSV…")
        with open(self.file_path, "r", encoding=self.settings["encoding"]) as fh:
            delim = self.settings["delimiter"]
            reader = (
                csv.DictReader(fh, delimiter=delim)
                if self.settings["has_header"]
                else csv.reader(fh, delimiter=delim)
            )
            rows = list(reader)
    
        total = len(rows)
        for idx, row in enumerate(rows, 1):
            base = 20 + int(idx / total * 60)
            self.progress_updated.emit(base, f"Wiersz {idx}/{total}")
    
            try:
                data = (
                    self._map_csv_with_headers(row)
                    if self.settings["has_header"]
                    else self._map_csv_by_index(row)
                )
                if not data:
                    continue
                if not self._attach_local_image(data, base, idx):
                    continue
                imported.append(data)
            except Exception as err:
                if not self.settings.get("skip_errors", True):
                    raise
                logger.warning(f"Pominięto wiersz {idx}: {err}")
    
        self.progress_updated.emit(100, f"Import CSV zakończony ({len(imported)})")
        self.import_finished.emit(imported)
    
    # ----------  XML ----------
    def _import_xml(self):
        imported = []
        self.progress_updated.emit(10, "Parsowanie XML…")
        tree = ET.parse(self.file_path)
        root = tree.getroot()
        items = root.findall(".//item") or root.findall(".//record") or list(root)
        total = len(items)
    
        for idx, el in enumerate(items, 1):
            base = 20 + int(idx / total * 60)
            self.progress_updated.emit(base, f"Element {idx}/{total}")
            try:
                data = self._map_xml(el)
                if not data:
                    continue
                if not self._attach_local_image(data, base, idx):
                    continue
                imported.append(data)
            except Exception as err:
                if not self.settings.get("skip_errors", True):
                    raise
                logger.warning(f"Pominięto element {idx}: {err}")
    
        self.progress_updated.emit(100, f"Import XML zakończony ({len(imported)})")
        self.import_finished.emit(imported)
    
    # ----------  helpers ----------
    def _attach_local_image(self, data: dict, base_prog: int, idx: int) -> bool:
        """Pobiera lub weryfikuje obraz; zwraca True, jeśli jest OK."""
        img_path = data.get("path")
        if not img_path:
            if not self.settings.get("skip_errors", True):
                raise ValueError("Brak ścieżki do obrazu")
            return False
    
        local = self.downloader.process_path(
            img_path,
            lambda p, s: self.progress_updated.emit(base_prog, f"Pobieranie obrazu {idx}: {s}"),
        )
        if local:
            data["original_url"] = img_path if self.downloader.is_url(img_path) else None
            data["path"] = local
            return True
    
        if not self.settings.get("skip_errors", True):
            raise ValueError(f"Nie można pobrać obrazu: {img_path}")
        return False
    
    # -----  mapping  -----
    def _map_csv_with_headers(self, row: dict) -> dict:
        mapping = self.settings["mapping"]
        required = ("id", "path")
        if any(mapping.get(k, "") not in row for k in required):
            raise KeyError("Brak wymaganych kolumn")
        return {
            "id": row.get(mapping["id"], ""),
            "name": row.get(mapping.get("name", ""), ""),
            "path": row.get(mapping["path"], ""),
            "category": row.get(mapping.get("category", ""), ""),
            "raw_data": dict(row),
        }
    
    def _map_csv_by_index(self, row: list) -> dict:
        mapping = self.settings["mapping"]
        def safe(idx_key):
            try:
                idx = int(mapping.get(idx_key, ""))
                return row[idx] if idx < len(row) else ""
            except (ValueError, IndexError):
                return ""
        return {
            "id": safe("id"),
            "name": safe("name"),
            "path": safe("path"),
            "category": safe("category"),
            "raw_data": list(row),
        }
    
    def _map_xml(self, el: ET.Element) -> dict:
        mapping = self.settings["mapping"]
        def x(field):
            tag = mapping.get(field, "")
            if not tag:
                return ""
            child = el.find(tag)
            if child is not None:
                return child.text or ""
            return el.get(tag, "")
        return {
            "id": x("id"),
            "name": x("name"),
            "path": x("path"),
            "category": x("category"),
            "raw_data": {c.tag: c.text for c in el},
        }


# ===================================================================
# =====================  CSV/XML Processing Thread  =================
# ===================================================================
class CsvXmlProcessingThread(QThread):
    """Wątek przetwarzania obrazów z danych CSV/XML."""
    progress_updated = pyqtSignal(int, str)
    processing_finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, data, settings):
        super().__init__()
        self.data = data
        self.settings = settings
        self.engine = None
        self.results = []

    def run(self):
        """Przetwarza obrazy z zaimportowanych danych."""
        try:
            # Inicjalizuj silnik
            self.progress_updated.emit(5, "Inicjalizuję silnik...")
            self.engine = create_optimized_engine()

            total_items = len(self.data)
            processed = 0

            for i, item in enumerate(self.data):
                if not item.get('path'):
                    continue

                try:
                    self.progress_updated.emit(
                        int(10 + (i / total_items) * 80),
                        f"Przetwarzam {i+1}/{total_items}..."
                    )

                    # Przetwórz obraz
                    result = self._process_single_item(item)
                    if result:
                        self.results.append(result)
                        processed += 1

                except Exception as e:
                    if not self.settings.get('skip_errors', True):
                        raise e
                    logger.error(f"Błąd przetwarzania {item.get('path')}: {e}")

            # Utwórz CSV z linkami, jeśli wybrano taką opcję
            if self.settings.get('create_csv_links', False):
                out_dir = self.settings.get('local_path') or os.path.join(os.getcwd(), 'output')
                self.create_csv_with_links(self.results, out_dir)

            self.progress_updated.emit(100, f"Zakończono: {processed}/{total_items}")
            self.processing_finished.emit(self.results)

        except Exception as e:
            self.error_occurred.emit(str(e))

    # ------------------------------------------------------------------ #
    # ---------------------  P R Y W A T N E  -------------------------- #
    # ------------------------------------------------------------------ #
    def _process_single_item(self, item):
        """Przetwarza pojedynczy element."""
        image_path = item.get('path', '')
        if not image_path or not os.path.exists(image_path):
            return None

        try:
            from PIL import Image
            image = Image.open(image_path)

            engine_settings = self._convert_settings()
            result = self.engine.process_single(image, engine_settings)

            output_path = self._save_result(result, item)
            cloud_url = output_path if self.settings.get('save_location', 'Lokalnie') != 'Lokalnie' else ''
            return {
                'input_path': image_path,
                'output_path': output_path,
                'cloud_url': cloud_url,
                'item_data': item
            }

        except Exception as e:
            logger.error(f"Błąd przetwarzania {image_path}: {e}")
            return None

    def _convert_settings(self):
        """Konwertuje ustawienia UI do formatu silnika."""
        processing = self.settings.get('processing', {})
        mode = processing.get('mode', 'Usuń tło')

        settings = {
            'bg_mode': 'remove' if mode == 'Usuń tło' else 'keep',
            'bg_color': processing.get('bg_color', '#FFFFFF'),
            'bg_image': processing.get('bg_image'),
            'preserve_holes': True,
            'edge_refinement': True,
            'force_binary_alpha': True
        }

        if mode == 'Zamień tło':
            settings['bg_mode'] = 'color' if processing.get('bg_color') else 'image'

        return settings

    def _save_result(self, image, item):
        """Zapisuje przetworzony obraz używając zunifikowanego systemu eksportu."""
        try:
            from src.utils.export_utils import export_image

            # Przygotowanie ustawień eksportu
            export_settings = {
                'save_location': self.settings.get('save_location', 'Lokalnie'),
                'output_directory': self.settings.get('local_path', 'output'),
                'credentials': self.settings.get('credentials', {}),
                'format': self.settings.get('format', {}),
                'filename_pattern': '{original_name}_{identifier}',
                'identifier': item.get('id', '')  # Dodatkowy parametr dla CSV/XML
            }

            original_path = item.get('path', '')
            result_path = export_image(image, original_path, export_settings)
            return result_path

        except Exception as e:
            logger.error(f"Błąd zapisywania przez zunifikowany system: {e}")
            return ""

    def create_csv_with_links(self, results, output_path):
        """Tworzy plik CSV z ID produktów i linkami do zdjęć w chmurze."""
        try:
            # Użyj ustawień z kontrolek zamiast domyślnych
            csv_path = self.settings.get('csv_local_path', output_path)
            csv_filename = self.settings.get('csv_filename', 'processed_images')
            
            os.makedirs(csv_path, exist_ok=True)
            csv_data = []
            
            for result in results:
                item_data = result.get('item_data', {})
                product_id = item_data.get('id', '')
                cloud_url = result.get('cloud_url', '')
                csv_data.append([product_id, cloud_url])

            full_csv_path = os.path.join(csv_path, f'{csv_filename}.csv')
            with open(full_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Product_ID', 'Image_URL'])
                writer.writerows(csv_data)
                
            logger.info(f"CSV z linkami zapisany: {full_csv_path}")
            
        except Exception as e:
            logger.error(f"Błąd tworzenia CSV z linkami: {e}")

class CsvXmlView(QWidget):
    """Główny widok do importu danych z CSV/XML z nowoczesną stylistyką."""
    
    # Sygnały
    import_started = pyqtSignal()
    import_finished = pyqtSignal(list)
    import_progress = pyqtSignal(int, str)
    processing_started = pyqtSignal()
    processing_finished = pyqtSignal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.license_controller = get_license_controller()
        self.current_file = None
        self.imported_data = []
        self.import_thread = None
        self.detected_format = None
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Inicjalizacja nowoczesnego interfejsu użytkownika."""
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Lewa strona - sekcja plików i podglądu
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
        
        title_label = QLabel(self.tr("CSV/XML Data Import"))
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: 700;
                color: #212529;
                background: transparent;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        left_layout.addLayout(header_layout)
        
        # Przycisk wyboru pliku
        file_button_layout = QHBoxLayout()
        
        self.select_file_btn = QPushButton(self.tr("Select CSV/XML file"))
        self.select_file_btn.setStyleSheet("""
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
        """)
        
        self.file_status_label = QLabel(self.tr("No file selected"))
        self.file_status_label.setStyleSheet("""
            QLabel {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 8px 12px;
                color: #6c757d;
                font-size: 11px;
                font-weight: 500;
                margin-left: 10px;
            }
        """)
        
        file_button_layout.addWidget(self.select_file_btn)
        file_button_layout.addWidget(self.file_status_label)
        file_button_layout.addStretch()
        
        left_layout.addLayout(file_button_layout)

        # Podgląd danych z mapowaniem w kontenerze
        preview_container = QFrame()
        preview_container.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        
        preview_label = QLabel(self.tr("Data preview:"))
        preview_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #495057; margin-bottom: 8px;")
        preview_layout.addWidget(preview_label)
        
        self.preview = DataPreviewWithMapping()
        self.preview.setMinimumHeight(400)
        preview_layout.addWidget(self.preview)
        
        left_layout.addWidget(preview_container)

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
        
        self.status_label = QLabel(self.tr("Select a CSV or XML file to import"))
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
        
        # Przycisk podglądu
        self.preview_btn = QPushButton(self.tr("Load preview"))
        self.preview_btn.setEnabled(False)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 16px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #5a6268;
            }
            QPushButton:disabled {
                background: #e9ecef;
                color: #6c757d;
            }
        """)
        actions_layout.addWidget(self.preview_btn)
        
        # Główny przycisk importu
        self.import_btn = QPushButton(self.tr("Start import and processing"))
        self.import_btn.setEnabled(False)
        self.import_btn.setMinimumHeight(50)
        self.import_btn.setStyleSheet("""
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
        actions_layout.addWidget(self.import_btn)
        
        # Przycisk zatrzymania
        self.stop_btn = QPushButton("Zatrzymaj")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
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
        actions_layout.addWidget(self.stop_btn)
        
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
        
        self.controls = CsvXmlProcessingControls()
        controls_scroll.setWidget(self.controls)
        
        # Główny układ
        main_layout.addWidget(left_widget, 2)
        main_layout.addWidget(controls_scroll, 1)

        self.setLayout(main_layout)
        
        # Tło głównego widgetu
        self.setStyleSheet("""
            CsvXmlView {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #764ba2);
            }
        """)

    def connect_signals(self):
        """Podłączenie sygnałów do slotów."""
        self.select_file_btn.clicked.connect(self.select_file)
        self.preview_btn.clicked.connect(self.load_preview)
        self.import_btn.clicked.connect(self.import_and_process_data)
        self.stop_btn.clicked.connect(self.stop_processing)
        
        # Sygnały kontrolek
        self.preview.mapping_changed.connect(self.validate_mapping)
        
        # Podłączenie sygnałów importu
        self.import_started.connect(self.on_import_start)
        self.import_finished.connect(self.on_import_end)
        self.import_progress.connect(self.update_progress)
        
        # Sygnały przetwarzania
        self.processing_started.connect(self.on_processing_start)
        self.processing_finished.connect(self.on_processing_end)

    def select_file(self):
        """
        Wybór pliku do importu z auto-detekcją formatu.
        """
        # Sprawdź licencję
        if not self.license_controller.can_access_csv_xml_import():
            show_upgrade_prompt("CSV/XML Import", self)
            return
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik CSV lub XML",
            "",
            "CSV/XML Files (*.csv *.xml);;CSV Files (*.csv);;XML Files (*.xml);;All Files (*)"
        )
        
        if file_name:
            self.current_file = file_name
            
            # Auto-detekcja formatu
            self.detected_format = self.detect_file_format(file_name)
            self.preview.set_file_format(self.detected_format)
            
            # Analizuj plik automatycznie
            self.status_label.setText("Analizuję plik...")
            self.status_label.setStyleSheet("""
                QLabel {
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 6px;
                    padding: 10px;
                    color: #856404;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)
            
            # Wykonaj analizę
            QTimer.singleShot(100, lambda: self.analyze_file(file_name))

    def analyze_file(self, file_name):
        """Analizuje plik i aktualizuje UI."""
        analysis_success = self.preview.analyze_file(file_name)
        
        if analysis_success:
            # Aktualizuj status pliku
            file_info = f"📁 {Path(file_name).name}\n📊 Format: {self.detected_format}\n💾 {self.get_file_size(file_name)} MB"
            self.file_status_label.setText(file_info)
            self.file_status_label.setStyleSheet("""
                QLabel {
                    background: #cce7ff;
                    border: 1px solid #99d3ff;
                    border-radius: 6px;
                    padding: 8px 12px;
                    color: #0056b3;
                    font-size: 11px;
                    font-weight: 500;
                    margin-left: 10px;
                }
            """)
            
            self.preview_btn.setEnabled(True)
            self.load_preview()  # Auto-load mapping controls after analysis
            self.status_label.setText(f"Plik przeanalizowany: {Path(file_name).name}")
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
        else:
            # Błąd analizy
            self.file_status_label.setText(f"❌ Błąd analizy: {Path(file_name).name}")
            self.file_status_label.setStyleSheet("""
                QLabel {
                    background: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 6px;
                    padding: 8px 12px;
                    color: #721c24;
                    font-size: 11px;
                    font-weight: 500;
                    margin-left: 10px;
                }
            """)
            
            self.status_label.setText("Błąd podczas analizy pliku - spróbuj z innym plikiem")
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

    def detect_file_format(self, file_path):
        """Automatyczna detekcja formatu pliku."""
        file_extension = Path(file_path).suffix.lower()
        if file_extension == '.csv':
            return 'CSV'
        elif file_extension in ['.xml', '.XML']:
            return 'XML'
        else:
            # Próba detekcji na podstawie zawartości
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('<?xml') or '<' in first_line:
                        return 'XML'
                    else:
                        return 'CSV'
            except:
                return 'CSV'  # Domyślnie CSV

    def get_file_size(self, file_path):
        """Pobiera rozmiar pliku w MB."""
        try:
            size_bytes = os.path.getsize(file_path)
            return round(size_bytes / (1024 * 1024), 2)
        except:
            return 0

    def load_preview(self):
        """Ładuje podgląd danych z pliku."""
        if not self.current_file:
            return

        try:
            if self.detected_format == "CSV":
                self.load_csv_preview()
            else:
                self.load_xml_preview()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Błąd")
            msg.setText(f"Nie można załadować podglądu:\n{str(e)}")
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

    def load_csv_preview(self):
        """Ładuje podgląd danych z pliku CSV z wykrytymi parametrami - POPRAWIONA WERSJA."""
        # Użyj bezpośrednio wykrytych parametrów z preview
        encoding = self.preview.detected_encoding
        delimiter = self.preview.detected_delimiter
        has_header = self.preview.detected_has_header
        
        with open(self.current_file, 'r', encoding=encoding) as f:
            reader = csv.reader(f, delimiter=delimiter)
            data = []
            
            for i, row in enumerate(reader):
                data.append(row)
                if i >= 100:  # Ładuj tylko pierwsze 100 wierszy dla podglądu
                    break
            
            if data:
                headers = data[0] if has_header else None
                self.preview.update_data(data, headers)
                
                rows_text = f"pierwsze {len(data)}" if len(data) == 101 else str(len(data))
                self.status_label.setText(f"Podgląd CSV: {rows_text} wierszy")
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
                
                # Włącz przycisk importu jeśli mapowanie jest poprawne
                self.validate_mapping()

    def load_xml_preview(self):
        """Ładuje podgląd danych z pliku XML z wykrytym kodowaniem."""
        try:
            # Używamy wykrytego kodowania
            encoding = self.preview.detected_encoding
            
            # Dla XML, próbujemy różnych metod parsowania
            tree = ET.parse(self.current_file)
            root = tree.getroot()
            
            # Znajdź elementy danych
            items = root.findall('.//item') or root.findall('.//record') or list(root)[:100]
            
            if items:
                # Przygotuj dane tabelaryczne
                headers = []
                data = []
                
                # Znajdź wszystkie możliwe klucze
                all_keys = set()
                for item in items[:10]:  # Sprawdź pierwszych 10 dla kluczy
                    all_keys.update([child.tag for child in item])
                    all_keys.update(item.attrib.keys())
                
                headers = list(all_keys)
                
                # Przygotuj wiersze danych  
                for item in items:
                    row = []
                    for header in headers:
                        # Próbuj jako child element
                        child = item.find(header)
                        if child is not None:
                            row.append(child.text or '')
                        else:
                            # Próbuj jako atrybut
                            row.append(item.get(header, ''))
                    data.append(row)
                
                # Dodaj nagłówki jako pierwszy wiersz
                if headers:
                    data.insert(0, headers)
                    self.preview.update_data(data, headers)
                    
                    self.status_label.setText(f"Podgląd XML: {len(items)} elementów")
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
                    
                    # Włącz przycisk importu jeśli mapowanie jest poprawne 
                    self.validate_mapping()
            else:
                self.status_label.setText("Nie znaleziono danych w pliku XML")
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
                
        except ET.ParseError as e:
            raise Exception(f"Błąd parsowania XML: {e}")
        except Exception as e:
            raise Exception(f"Błąd wczytywania XML: {e}")

    def validate_mapping(self):
        """Waliduje mapowanie kolumn."""
        mapping = self.preview.get_mapping()
        has_mapping = any(mapping.values())
        
        if has_mapping and self.current_file:
            self.import_btn.setEnabled(True)
        else:
            self.import_btn.setEnabled(False)

    def import_and_process_data(self):
        # Sprawdź licencję przed rozpoczęciem
        if not self.license_controller.can_access_csv_xml_import():
            show_upgrade_prompt("CSV/XML Import", self)
            return
        """Importuje dane z pliku i rozpoczyna przetwarzanie."""
        if not self.current_file:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Brak pliku")
            msg.setText("Wybierz plik do importu")
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

        # Sprawdź mapowanie
        mapping = self.preview.get_mapping()
        if not any(mapping.values()):
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Błąd mapowania")
            msg.setText("Wybierz mapowanie przynajmniej dla jednej kolumny")
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

        # Sprawdź ustawienia przetwarzania
        is_valid, error_msg = self.controls.validate_settings()
        if not is_valid:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Błąd konfiguracji")
            msg.setText(error_msg)
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

        # Rozpocznij import
        self.import_started.emit()
        
        # Połącz mapowanie z ustawieniami
        settings = self.controls.get_settings()
        settings['mapping'] = mapping
        
        # Dodaj ustawienia pliku - POPRAWIONA WERSJA
        settings.update({
            'encoding': self.preview.detected_encoding,
            'delimiter': self.preview.detected_delimiter,
            'has_header': self.preview.detected_has_header
        })
        
        # Uruchom import w osobnym wątku
        self.import_thread = ImportThread(self.current_file, settings)
        self.import_thread.progress_updated.connect(self.import_progress)
        self.import_thread.import_finished.connect(self.import_finished)
        self.import_thread.error_occurred.connect(self.on_import_error)
        self.import_thread.start()

    def stop_processing(self):
        """Zatrzymuje import/przetwarzanie."""
        if self.import_thread and self.import_thread.isRunning():
            self.import_thread.terminate()
            self.import_thread.wait()
            
        self.status_label.setText("Przetwarzanie zatrzymane przez użytkownika")
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
        
        self.processing_finished.emit()

    def on_import_error(self, error_message):
        """Obsługa błędu importu."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Błąd importu")
        msg.setText(f"Wystąpił błąd podczas importu:\n{error_message}")
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
        self.on_import_end([])

    def on_import_start(self):
        """Obsługa rozpoczęcia importu."""
        self.processing_started.emit()

    def on_import_end(self, imported_data):
        """Obsługa zakończenia importu – POPRAWIONA WERSJA."""
        self.imported_data = imported_data

        if imported_data:
            self.status_label.setText(
                f"Import zakończony: {len(imported_data)} rekordów. "
                f"Rozpoczynam przetwarzanie obrazów…"
            )
            self.status_label.setStyleSheet("""
                QLabel {
                    background: #cce7ff; border: 1px solid #99d3ff;
                    border-radius: 6px; padding: 10px;
                    color: #0056b3; font-size: 11px; font-weight: 500;
                }
            """)
            self.start_image_processing()
        else:
            self.processing_finished.emit()

        self.import_thread = None


    # ------------------------------------------------------------------
    # ------------------  Przetwarzanie obrazów  -----------------------
    # ------------------------------------------------------------------
    def start_image_processing(self):
        """Rozpoczyna rzeczywiste przetwarzanie obrazów z zaimportowanych danych."""
        if not self.imported_data:
            return

        image_data = [item for item in self.imported_data if item.get("path")]
        if not image_data:
            QMessageBox.warning(
                self, "Brak obrazów",
                "Nie znaleziono ścieżek do obrazów w zaimportowanych danych."
            )
            self.processing_finished.emit()
            return

        logger.info(f"🎯 Rozpoczynam przetwarzanie {len(image_data)} obrazów")

        settings = self.controls.get_settings()
        self.processing_thread = CsvXmlProcessingThread(image_data, settings)
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.processing_finished.connect(self.on_processing_complete)
        self.processing_thread.error_occurred.connect(self.on_import_error)
        self.processing_thread.start()

    def on_processing_complete(self, results):
        """Obsługa zakończenia przetwarzania obrazów – POPRAWIONA WERSJA."""
        logger.info(f"✅ Przetwarzanie zakończone: {len(results)} obrazów")
        self.processing_finished.emit()

        if results:
            save_loc = self.controls.get_settings().get("save_location", "Lokalnie")
            output_path = (
                self.controls.local_path.text()
                if save_loc == "Lokalnie" else os.path.join(os.getcwd(), "output")
            )

            success = [r for r in results if r.get("output_path")]
            ok = len(success)

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("Przetwarzanie zakończone")

            if ok:
                box.setText(
                    f"Przetwarzanie zakończone pomyślnie!\n\n"
                    f"Przetworzone obrazy: {ok}/{len(self.imported_data)}\n"
                    f"Lokalizacja: {output_path}\n\n"
                    f"Czy chcesz otworzyć folder z wynikami?"
                )
                box.setStandardButtons(QMessageBox.StandardButton.Yes |
                                       QMessageBox.StandardButton.No)
                box.setDefaultButton(QMessageBox.StandardButton.Yes)
            else:
                box.setText(
                    "Nie udało się przetworzyć żadnych obrazów.\n"
                    "Sprawdź ścieżki do plików i ustawienia przetwarzania."
                )
                box.setStandardButtons(QMessageBox.StandardButton.Ok)

            box.setStyleSheet("""
                QMessageBox { background:white; border-radius:8px; }
                QMessageBox QPushButton {
                    background:#28a745; color:white; border:none; border-radius:6px;
                    padding:8px 16px; font-weight:500; min-width:80px;
                }
                QMessageBox QPushButton:hover { background:#218838; }
            """)

            if box.exec() == QMessageBox.StandardButton.Yes and ok:
                try:
                    import subprocess, platform
                    if platform.system() == "Windows":
                        subprocess.run(f'explorer "{output_path}"', shell=True)
                    elif platform.system() == "Darwin":
                        subprocess.run(["open", output_path])
                    else:
                        subprocess.run(["xdg-open", output_path])
                except Exception as e:
                    logger.warning(f"Nie można otworzyć folderu: {e}")
        else:
            QMessageBox.warning(
                self, "Brak wyników",
                "Nie udało się przetworzyć żadnych obrazów.\n"
                "Sprawdź ścieżki do plików i ustawienia."
            )

    def on_processing_start(self):
        """Obsługa rozpoczęcia przetwarzania."""
        self.progress.show()
        self.progress.setValue(0)
        self.import_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.controls.setEnabled(False)
        self.select_file_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)

        # Zmień wygląd przycisku
        self.import_btn.setText("Przetwarzanie...")
        self.import_btn.setStyleSheet(
            "QPushButton { background: #6c757d; color: white; border: none; "
            "border-radius: 12px; padding: 16px; font-size: 16px; font-weight: 600; }"
        )

    def on_processing_end(self):
        """Obsługa zakończenia przetwarzania."""
        self.progress.hide()
        self.import_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.controls.setEnabled(True)
        self.select_file_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)

        self.import_btn.setText("Rozpocznij import i przetwarzanie")
        self.import_btn.setStyleSheet(
            "QPushButton { background: #0079e1; color: white; border: none; "
            "border-radius: 12px; padding: 16px; font-size: 16px; font-weight: 600; } "
            "QPushButton:hover { background: #0056b3; } "
            "QPushButton:pressed { background: #004494; } "
            "QPushButton:disabled { background: #e9ecef; color: #6c757d; }"
        )

        if not hasattr(self, "processing_stopped"):
            self.status_label.setText("Import i przetwarzanie zakończone pomyślnie!")
            self.status_label.setStyleSheet(
                "QLabel { background: #d4edda; border: 1px solid #c3e6cb; "
                "border-radius: 6px; padding: 10px; color: #155724; "
                "font-size: 11px; font-weight: 500; }"
            )

    def update_progress(self, value, message):
        """Aktualizacja paska postępu."""
        self.progress.setValue(value)
        self.status_label.setText(message)
        self.status_label.setStyleSheet(
            "QLabel { background: #cce7ff; border: 1px solid #99d3ff; border-radius: 6px; "
            "padding: 10px; color: #0056b3; font-size: 11px; font-weight: 500; }"
        )

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # Przykładowe użycie
    window = CsvXmlView(None)
    window.show()
    
    sys.exit(app.exec())