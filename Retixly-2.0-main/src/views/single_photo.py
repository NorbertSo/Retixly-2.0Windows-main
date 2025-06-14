from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFileDialog, QScrollArea, QSpinBox, 
                            QComboBox, QGroupBox, QProgressBar, QColorDialog,
                            QSlider, QCheckBox, QMessageBox, QSplitter,
                            QFormLayout, QFrame, QButtonGroup, QRadioButton,
                            QStackedWidget, QTabWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QPen, QFont
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass
from src.core.image_engine import create_optimized_engine
import os
import tempfile
from src.core.professional_bg_remover import EnhancedImageEngine
## from src.core.image_engine import create_optimized_engine

import logging

logger = logging.getLogger(__name__)


# Nowa, ulepszona wersja klasy ImageProcessingThread z profesjonalnym silnikiem
class ImageProcessingThread(QThread):
    """
    Profesjonalny wątek do przetwarzania obrazów z użyciem zoptymalizowanego silnika.
    Obsługuje postęp, błędy oraz fallback na prostsze przetwarzanie w razie problemów.
    """
    progress_updated = pyqtSignal(int, str)
    processing_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, image_path, settings):
        super().__init__()
        self.image_path = image_path
        self.settings = settings
        self.engine = None
        self.temp_file = None

    def run(self):
        try:
            self.progress_updated.emit(5, "Inicjalizacja silnika...")
            self.engine = self._create_professional_engine()
            self.progress_updated.emit(10, "Ładowanie obrazu...")

            image = Image.open(self.image_path)
            if image.mode != 'RGBA':
                image = image.convert('RGBA')

            self.progress_updated.emit(25, "Przetwarzanie obrazu...")
            processed_image = self._process_image_with_engine(image)

            self.progress_updated.emit(90, "Zapisywanie...")
            self.temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            processed_image.save(self.temp_file.name, 'PNG')

            self.progress_updated.emit(100, "Gotowe!")
            self.processing_finished.emit(self.temp_file.name)
        except Exception as e:
            import traceback
            logger.error(f"Błąd w ImageProcessingThread: {e}\n{traceback.format_exc()}")
            self.error_occurred.emit(f"Błąd podczas przetwarzania: {str(e)}")

    def _create_professional_engine(self):
        """Tworzy instancję zoptymalizowanego silnika przetwarzania obrazów."""
        try:
            from src.core.image_engine import create_optimized_engine
            return create_optimized_engine(max_workers=2)
        except ImportError as e:
            logger.warning(f"Nie można zaimportować silnika: {e}")
            return None
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia silnika: {e}")
            return None

    def _process_image_with_engine(self, image):
        try:
            engine_settings = self._convert_settings_for_engine()
            # Jeśli JAKIEKOLWIEK ustawienie wykracza poza samo wycinanie -> FALLBACK
            complex_edit = any([
                engine_settings["background"]["mode"] in ("color", "image"),
                self.settings.get("adjustments_enabled"),
                self.settings.get("effects_enabled"),
                self.settings.get("watermark_enabled"),
            ])
            if complex_edit or self.engine is None:
                return self._fallback_processing(image)
            # tu już tylko „remove”
            return self.engine.process_single(
                image, settings=engine_settings, progress_callback=self._progress_callback
            )
        except Exception as e:
            logger.error(f"Error in _process_image_with_engine: {e}")
            return self._fallback_processing(image)

    def _progress_callback(self, percent, stage=None):
        """Callback postępu do silnika."""
        txt = stage if stage else "Przetwarzanie..."
        self.progress_updated.emit(percent, txt)

    def _convert_settings_for_engine(self):
        """
        Konwertuje ustawienia UI na format wymagany przez silnik przetwarzania.
        """
        engine_settings = {
            "background": {
                "mode": self.settings.get("bg_mode", "remove"),
                "color": self.settings.get("bg_color", "#FFFFFF"),
                "image_path": self.settings.get("bg_image"),
            },
            "adjustments": {
                "enabled": self.settings.get("adjustments_enabled", False),
                "brightness": self.settings.get("brightness", 0),
                "contrast": self.settings.get("contrast", 0),
                "saturation": self.settings.get("saturation", 0),
                "sharpness": self.settings.get("sharpness", 0),
            },
            "effects": {
                "enabled": self.settings.get("effects_enabled", False),
                "blur": self.settings.get("blur", 0),
                "edge_enhance": self.settings.get("edge_enhance", False),
                "smooth": self.settings.get("smooth", False),
            },
            "watermark": {
                "enabled": self.settings.get("watermark_enabled", False),
                "path": self.settings.get("watermark_path"),
                "position": self.settings.get("watermark_position"),
                "opacity": self.settings.get("watermark_opacity"),
                "scale": self.settings.get("watermark_scale"),
            },
        }
        return engine_settings

    def _fallback_processing(self, image):
        """
        Prosty fallback przetwarzania, jeśli profesjonalny silnik jest niedostępny.
        """
        try:
            result = image.copy()
            # Obsługa tła
            bg_mode = self.settings.get("bg_mode", "remove")
            if bg_mode == "remove":
                result = self._simple_remove_bg(result)
            elif bg_mode == "color":
                no_bg = self._simple_remove_bg(result)
                bg_color = self.settings.get("bg_color", "#FFFFFF")
                rgb = (255, 255, 255)
                if isinstance(bg_color, str) and bg_color.startswith("#") and len(bg_color) == 7:
                    rgb = tuple(int(bg_color[i:i+2], 16) for i in (1,3,5))
                background = Image.new("RGB", result.size, rgb)
                if no_bg.mode == "RGBA":
                    background.paste(no_bg, mask=no_bg.split()[-1])
                else:
                    background.paste(no_bg)
                result = background.convert("RGBA")
            elif bg_mode == "image":
                no_bg = self._simple_remove_bg(result)
                bg_img_path = self.settings.get("bg_image")
                try:
                    bg_img = Image.open(bg_img_path).convert("RGBA")
                    bg_img = bg_img.resize(result.size)
                except Exception:
                    bg_img = Image.new("RGBA", result.size, (255,255,255,255))
                bg_img.paste(no_bg, (0,0), mask=no_bg.split()[-1] if no_bg.mode == "RGBA" else None)
                result = bg_img
            # Regulacje
            if self.settings.get("adjustments_enabled", False):
                result = self._basic_adjustments(result)
            # Efekty
            if self.settings.get("effects_enabled", False):
                blur = self.settings.get("blur", 0)
                if blur > 0:
                    result = result.filter(ImageFilter.GaussianBlur(radius=blur))
                if self.settings.get("edge_enhance", False):
                    result = result.filter(ImageFilter.EDGE_ENHANCE)
                if self.settings.get("smooth", False):
                    result = result.filter(ImageFilter.SMOOTH)
            # Watermark
            if self.settings.get("watermark_enabled", False):
                result = self._apply_watermark(result)
            return result
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return image

    def _simple_remove_bg(self, image):
        """Bardzo uproszczone usuwanie tła (fallback)."""
        try:
            from rembg import remove
            arr = np.array(image)
            out = remove(arr)
            if isinstance(out, Image.Image):
                return out
            elif isinstance(out, np.ndarray):
                return Image.fromarray(out)
            elif isinstance(out, bytes):
                from io import BytesIO
                return Image.open(BytesIO(out)).convert("RGBA")
        except Exception:
            # Geometric: elipsa w centrum
            arr = np.array(image)
            h, w = arr.shape[:2]
            mask = np.zeros((h, w), dtype=np.uint8)
            cx, cy = w // 2, h // 2
            import cv2
            cv2.ellipse(mask, (cx, cy), (w//3, h//3), 0, 0, 360, 255, -1)
            if arr.shape[-1] == 3:
                arr = cv2.cvtColor(arr, cv2.COLOR_RGB2RGBA)
            arr[:,:,3] = mask
            return Image.fromarray(arr)
        return image

    def _basic_adjustments(self, image):
        """Podstawowe regulacje obrazu."""
        result = image
        # Każda regulacja w osobnym try-except
        brightness = self.settings.get("brightness", 0)
        if brightness != 0:
            try:
                factor = 1.0 + (brightness / 100.0)
                result = ImageEnhance.Brightness(result).enhance(factor)
            except Exception as e:
                logger.error(f"Brightness adjustment failed: {e}")
        contrast = self.settings.get("contrast", 0)
        if contrast != 0:
            try:
                factor = 1.0 + (contrast / 100.0)
                result = ImageEnhance.Contrast(result).enhance(factor)
            except Exception as e:
                logger.error(f"Contrast adjustment failed: {e}")
        saturation = self.settings.get("saturation", 0)
        if saturation != 0:
            try:
                factor = 1.0 + (saturation / 100.0)
                result = ImageEnhance.Color(result).enhance(factor)
            except Exception as e:
                logger.error(f"Saturation adjustment failed: {e}")
        sharpness = self.settings.get("sharpness", 0)
        if sharpness != 0:
            try:
                factor = 1.0 + (sharpness / 100.0)
                result = ImageEnhance.Sharpness(result).enhance(factor)
            except Exception as e:
                logger.error(f"Sharpness adjustment failed: {e}")
        return result

    def _apply_watermark(self, image):
        """Nakłada prosty znak wodny na obraz."""
        try:
            path = self.settings.get("watermark_path")
            if not path or not os.path.isfile(path):
                return image
            watermark = Image.open(path).convert("RGBA")
            scale = self.settings.get("watermark_scale", 0.2)
            opacity = self.settings.get("watermark_opacity", 0.5)
            wm_size = (int(image.width * scale), int(image.height * scale))
            watermark = watermark.resize(wm_size, Image.LANCZOS)
            # Ustaw przezroczystość
            if opacity < 1.0:
                alpha = watermark.split()[-1].point(lambda p: int(p * opacity))
                watermark.putalpha(alpha)
            # Pozycja
            pos = self.settings.get("watermark_position", "bottom-right")
            margin = 10
            if pos == "bottom-right":
                xy = (image.width - watermark.width - margin, image.height - watermark.height - margin)
            elif pos == "bottom-left":
                xy = (margin, image.height - watermark.height - margin)
            elif pos == "top-right":
                xy = (image.width - watermark.width - margin, margin)
            elif pos == "top-left":
                xy = (margin, margin)
            elif pos == "center":
                xy = ((image.width - watermark.width)//2, (image.height - watermark.height)//2)
            else:
                xy = (image.width - watermark.width - margin, image.height - watermark.height - margin)
            out = image.copy()
            out.paste(watermark, xy, watermark)
            return out
        except Exception as e:
            logger.error(f"Watermark failed: {e}")
            return image

class ZoomableImageLabel(QLabel):
    """Label z możliwością powiększania obrazu."""
    def __init__(self):
        super().__init__()
        self.scale_factor = 1.0
        self.original_pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
    def setPixmap(self, pixmap):
        self.original_pixmap = pixmap
        self.scale_factor = 1.0  # Reset zoom to original size
        self.update_scaled_pixmap()
        
    def update_scaled_pixmap(self):
        if self.original_pixmap:
            if self.scale_factor == 1.0:
                # Show original size
                super().setPixmap(self.original_pixmap)
            else:
                scaled_size = self.original_pixmap.size() * self.scale_factor
                scaled_pixmap = self.original_pixmap.scaled(
                    scaled_size, 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                super().setPixmap(scaled_pixmap)
            
    def zoom_in(self):
        self.scale_factor = min(self.scale_factor * 1.2, 5.0)
        self.update_scaled_pixmap()
        
    def zoom_out(self):
        self.scale_factor = max(self.scale_factor / 1.2, 0.1)
        self.update_scaled_pixmap()
        
    def reset_zoom(self):
        self.scale_factor = 1.0
        self.update_scaled_pixmap()

class ImagePreviewWidget(QWidget):
    """Widget do wyświetlania podglądu obrazu bez scroll - poprawiony."""
    image_dropped = pyqtSignal(str)
    file_dialog_requested = pyqtSignal()

    def tr(self, text):
        from PyQt6.QtWidgets import QApplication
        # Use the parent view's context so strings match translation entries
        return QApplication.translate("SinglePhotoView", text)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Kontener obrazu bez QScrollArea
        self.image_container = QFrame()
        self.image_container.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 2px dashed #e0e6ed;
                border-radius: 12px;
                padding: 10px;
            }
            QFrame:hover {
                border-color: #0079e1;
                background: #f8fcff;
            }
        """)
        
        container_layout = QVBoxLayout(self.image_container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        
        # Widget obrazu bez scroll
        self.image_label = ZoomableImageLabel()
        self.image_label.setMinimumSize(500, 400)
        self.image_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #6c757d;
                font-size: 14px;
                font-weight: 500;
                border: none;
                min-height: 350px;
            }
        """)
        self.image_label.setText(self.tr("Drag a photo here or click to select"))
        self.image_label.setAcceptDrops(True)
        self.image_label.mousePressEvent = self.on_image_click
        self.image_label.dragEnterEvent = self.dragEnterEvent
        self.image_label.dropEvent = self.dropEvent
        
        container_layout.addWidget(self.image_label)
        layout.addWidget(self.image_container)
        
        # Kontrolki powiększania
        zoom_frame = QFrame()
        zoom_frame.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        zoom_layout = QHBoxLayout(zoom_frame)
        zoom_layout.setSpacing(6)
        
        zoom_buttons = [
            ("Powiększ", self.image_label.zoom_in),
            ("1:1", self.image_label.reset_zoom),
            ("Pomniejsz", self.image_label.zoom_out)
        ]
        
        for text, callback in zoom_buttons:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    background: #ffffff;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: 500;
                    font-size: 11px;
                    color: #495057;
                }
                QPushButton:hover {
                    background: #0079e1;
                    color: white;
                    border-color: #0079e1;
                }
                QPushButton:pressed {
                    background: #0056b3;
                }
            """)
            btn.clicked.connect(callback)
            zoom_layout.addWidget(btn)
        
        zoom_layout.addStretch()
        layout.addWidget(zoom_frame)
        
        self.setLayout(layout)

    def on_image_click(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.file_dialog_requested.emit()

    def setImage(self, image_path):
        """Załaduj obraz do widoku - POPRAWIONA WERSJA Z DEBUGIEM."""
        try:
            print(f"DEBUG: setImage called with: {image_path}")
            
            # Sprawdź czy plik istnieje
            if not os.path.exists(image_path):
                print(f"DEBUG: File does not exist: {image_path}")
                self.image_label.setText(self.tr("File not found"))
                return
            
            # Sprawdź rozmiar pliku
            file_size = os.path.getsize(image_path)
            print(f"DEBUG: File size: {file_size} bytes")
            
            # Załaduj obraz
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                print(f"DEBUG: QPixmap is null for: {image_path}")
                self.image_label.setText(self.tr("Cannot load image"))
                return
                
            print(f"DEBUG: Loaded QPixmap size: {pixmap.width()}x{pixmap.height()}")
            
            # Sprawdź czy obraz ma przezroczystość (dla debugu)
            if image_path.endswith('.png'):
                try:
                    from PIL import Image
                    import numpy as np
                    pil_image = Image.open(image_path)
                    if pil_image.mode == 'RGBA':
                        img_array = np.array(pil_image)
                        transparent_pixels = np.sum(img_array[:,:,3] < 255)
                        total_pixels = img_array.shape[0] * img_array.shape[1]
                        print(f"DEBUG: PNG has {transparent_pixels}/{total_pixels} transparent pixels ({transparent_pixels/total_pixels*100:.1f}%)")
                except Exception as e:
                    print(f"DEBUG: Could not analyze PNG transparency: {e}")
            
            # Skaluj obraz
            available_size = self.image_label.size()
            print(f"DEBUG: Available size: {available_size.width()}x{available_size.height()}")
            
            if available_size.width() > 20 and available_size.height() > 20:
                scaled_pixmap = pixmap.scaled(
                    available_size.width() - 20,
                    available_size.height() - 20,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                print(f"DEBUG: Scaled to: {scaled_pixmap.width()}x{scaled_pixmap.height()}")
            else:
                scaled_pixmap = pixmap
                print("DEBUG: Using original size (no scaling)")
            
            # KLUCZOWE: Wymuś aktualizację
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.repaint()  # Wymuś natychmiastowe przerysowanie
            self.image_label.update()   # Zaplanuj aktualizację
            
            # Aktualizuj aplikację
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()  # Przetwórz wszystkie oczekujące eventy
            
            print("DEBUG: Image display updated successfully")
            
        except Exception as e:
            print(f"DEBUG: Error in setImage: {e}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            self.image_label.setText(self.tr("Error: ") + str(e))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and self.is_image_file(urls[0].toLocalFile()):
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files and self.is_image_file(files[0]):
            self.image_dropped.emit(files[0])
            
    def is_image_file(self, filepath):
        valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif', '.webp'}
        return Path(filepath).suffix.lower() in valid_extensions

    def changeEvent(self, event):
        """Obsługuje zmianę języka."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.LanguageChange:
            if not hasattr(self, 'original_pixmap') or not self.original_pixmap:
                self.image_label.setText(self.tr("Drag a photo here or click to select"))
        super().changeEvent(event)

class ModernCard(QFrame):
    """Karta bez ramek - poprawiona."""
    def __init__(self, title="", collapsible=False):
        super().__init__()
        self.title = title
        self.collapsible = collapsible
        self.collapsed = False
        self.content_widget = None
        self.init_ui()
        
    def init_ui(self):
        # Usunięcie wszystkich ramek
        self.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 0px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Nagłówek bez ramki
        if self.title:
            self.header = QFrame()
            self.header.setStyleSheet("""
                QFrame {
                    background: #f8f9fa;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 16px;
                }
            """)
            
            header_layout = QHBoxLayout(self.header)
            header_layout.setContentsMargins(0, 0, 0, 0)
            
            self.title_label = QLabel(self.title)
            self.title_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    font-weight: 600;
                    color: #212529;
                    background: transparent;
                    border: none;
                    padding: 0px;
                }
            """)
            header_layout.addWidget(self.title_label)
            
            if self.collapsible:
                self.toggle_btn = QPushButton("−")
                self.toggle_btn.setFixedSize(20, 20)
                self.toggle_btn.setStyleSheet("""
                    QPushButton {
                        background: #0079e1;
                        color: white;
                        border: none;
                        border-radius: 10px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background: #0056b3;
                    }
                """)
                self.toggle_btn.clicked.connect(self.toggle_collapse)
                header_layout.addWidget(self.toggle_btn)
            
            layout.addWidget(self.header)
        
        # Obszar zawartości bez ramki
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("QWidget { border: none; }")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 12, 16, 16)
        
        layout.addWidget(self.content_widget)
        
    def toggle_collapse(self):
        self.collapsed = not self.collapsed
        self.content_widget.setVisible(not self.collapsed)
        self.toggle_btn.setText("+" if self.collapsed else "−")
        
    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

class ModernSlider(QWidget):
    """Suwak z mniejszym fontem."""
    valueChanged = pyqtSignal(int)
    
    def __init__(self, min_val=-100, max_val=100, default_val=0, suffix=""):
        super().__init__()
        self.suffix = suffix
        self.init_ui(min_val, max_val, default_val)
        
    def init_ui(self, min_val, max_val, default_val):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default_val)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: #f1f1f1;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #0079e1;
                border: 2px solid #0079e1;
                width: 14px;
                height: 14px;
                margin: -6px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #0056b3;
                border-color: #0056b3;
            }
            QSlider::sub-page:horizontal {
                background: #0079e1;
                border-radius: 2px;
            }
        """)
        
        self.value_label = QLabel(f"{default_val}{self.suffix}")
        self.value_label.setStyleSheet("""
            QLabel {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 2px 6px;
                font-weight: 500;
                font-size: 10px;
                color: #495057;
                min-width: 35px;
            }
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.slider)
        layout.addWidget(self.value_label)
        
        self.slider.valueChanged.connect(self.on_value_changed)
        
    def on_value_changed(self, value):
        self.value_label.setText(f"{value}{self.suffix}")
        self.valueChanged.emit(value)
        
    def value(self):
        return self.slider.value()
        
    def setValue(self, value):
        self.slider.setValue(value)

class ImageProcessingControls(QWidget):
    """Kontrolki przetwarzania bez ramek z mniejszymi fontami."""
    settings_changed = pyqtSignal()

    def tr(self, text):
        from PyQt6.QtWidgets import QApplication
        # Reuse the SinglePhotoView context so translations are found
        return QApplication.translate("SinglePhotoView", text)
    def __init__(self):
        super().__init__()
        self.bg_color = "#FFFFFF"
        self.bg_image_path = None
        self.watermark_path = None
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Zmniejszony font dla całej sekcji
        small_font_style = "font-size: 10px;"
        label_style = "font-size: 11px; font-weight: 600; color: #495057; margin-bottom: 4px;"

        # Sekcja tła - bez QGroupBox
        self.bg_label = QLabel(self.tr("Background processing"))
        self.bg_label.setStyleSheet(label_style)
        layout.addWidget(self.bg_label)
        
        # Wybór trybu tła
        bg_mode_widget = QWidget()
        bg_mode_layout = QVBoxLayout(bg_mode_widget)
        bg_mode_layout.setSpacing(6)
        
        mode_label = QLabel(self.tr("Choose option:"))
        mode_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        bg_mode_layout.addWidget(mode_label)
        
        self.bg_mode_group = QButtonGroup()
        self.bg_modes = {
            "remove": self.tr("Remove background"),
            "change": self.tr("Change background")
        }
        
        for key, text in self.bg_modes.items():
            radio = QRadioButton(text)
            radio.setStyleSheet(f"""
                QRadioButton {{
                    font-size: 10px;
                    color: #495057;
                    spacing: 6px;
                }}
                QRadioButton::indicator {{
                    width: 14px;
                    height: 14px;
                }}
                QRadioButton::indicator:unchecked {{
                    border: 2px solid #dee2e6;
                    border-radius: 7px;
                    background: white;
                }}
                QRadioButton::indicator:checked {{
                    border: 2px solid #0079e1;
                    border-radius: 7px;
                    background: #0079e1;
                }}
            """)
            if key == "remove":
                radio.setChecked(True)
            self.bg_mode_group.addButton(radio)
            setattr(self, f"bg_{key}_radio", radio)
            bg_mode_layout.addWidget(radio)
        
        layout.addWidget(bg_mode_widget)
        
        # Opcje zmiany tła
        self.bg_options_stack = QStackedWidget()
        
        # Widget koloru
        color_widget = QWidget()
        color_layout = QVBoxLayout(color_widget)
        color_layout.setSpacing(8)
        
        color_btn_layout = QHBoxLayout()
        self.bg_color_btn = QPushButton(self.tr("Choose color"))
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
        
        color_btn_layout.addWidget(self.bg_color_btn)
        color_btn_layout.addWidget(self.bg_color_display)
        color_btn_layout.addStretch()
        color_layout.addLayout(color_btn_layout)
        
        # Widget obrazu
        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        image_layout.setSpacing(8)
        
        self.bg_image_btn = QPushButton(self.tr("Choose background image"))
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
        self.bg_image_path = None
        image_layout.addWidget(self.bg_image_btn)
        
        # Widget dla opcji zmiany tła
        bg_change_widget = QWidget()
        bg_change_layout = QVBoxLayout(bg_change_widget)
        bg_change_layout.setSpacing(10)
        
        # Przyciski wyboru typu
        tab_frame = QFrame()
        tab_frame.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 3px;
            }
        """)
        tab_layout = QHBoxLayout(tab_frame)
        tab_layout.setSpacing(3)
        
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
        tab_layout.addWidget(self.bg_color_tab)
        tab_layout.addWidget(self.bg_image_tab)
        
        bg_change_layout.addWidget(tab_frame)
        
        # Stack dla opcji kolor/obraz
        self.bg_type_stack = QStackedWidget()
        self.bg_type_stack.addWidget(color_widget)
        self.bg_type_stack.addWidget(image_widget)
        bg_change_layout.addWidget(self.bg_type_stack)
        
        self.bg_options_stack.addWidget(QWidget())  # Pusty widget
        self.bg_options_stack.addWidget(bg_change_widget)
        
        layout.addWidget(self.bg_options_stack)

        # Separator
        layout.addSpacing(8)

        # Regulacje obrazu - bez QGroupBox
        self.adj_label = QLabel(self.tr("Image adjustments"))
        self.adj_label.setStyleSheet(label_style)
        layout.addWidget(self.adj_label)
        
        self.adjustments_enabled = QCheckBox(self.tr("Enable image adjustments"))
        self.adjustments_enabled.setStyleSheet(f"""
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
        layout.addWidget(self.adjustments_enabled)
        
        # Kontrolki regulacji
        self.adj_controls = QWidget()
        adj_controls_layout = QVBoxLayout(self.adj_controls)
        adj_controls_layout.setSpacing(8)

        adjustments = [
            (self.tr("Brightness"), "brightness_slider", -100, 100, 0),
            (self.tr("Contrast"), "contrast_slider", -100, 100, 0),
            (self.tr("Saturation"), "saturation_slider", -100, 100, 0),
            (self.tr("Sharpness"), "sharpness_slider", -100, 100, 0)
        ]

        for label_text, attr, min_val, max_val, default in adjustments:
            slider_widget = QWidget()
            slider_layout = QVBoxLayout(slider_widget)
            slider_layout.setSpacing(4)

            label_widget = QLabel(label_text)
            label_widget.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
            slider_layout.addWidget(label_widget)

            slider = ModernSlider(min_val, max_val, default)
            setattr(self, attr, slider)
            slider_layout.addWidget(slider)

            adj_controls_layout.addWidget(slider_widget)

        # Add reset adjustments button
        self.reset_adj_btn = QPushButton(self.tr("Reset adjustments"))
        self.reset_adj_btn.setStyleSheet("""
            QPushButton {
                background: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #e2e6ea;
                border-color: #adb5bd;
            }
        """)
        adj_controls_layout.addWidget(self.reset_adj_btn)

        self.adj_controls.hide()
        layout.addWidget(self.adj_controls)

        # Separator
        layout.addSpacing(8)

        # Efekty specjalne - bez QGroupBox
        self.effects_label = QLabel(self.tr("Special effects"))
        self.effects_label.setStyleSheet(label_style)
        layout.addWidget(self.effects_label)
        
        self.effects_enabled = QCheckBox(self.tr("Enable special effects"))
        self.effects_enabled.setStyleSheet(f"""
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
        layout.addWidget(self.effects_enabled)
        
        # Kontrolki efektów
        self.effects_controls = QWidget()
        effects_controls_layout = QVBoxLayout(self.effects_controls)
        effects_controls_layout.setSpacing(8)
        
        # Suwak rozmycia
        blur_widget = QWidget()
        blur_layout = QVBoxLayout(blur_widget)
        blur_layout.setSpacing(4)
        
        blur_label = QLabel(self.tr("Blur"))
        blur_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        blur_layout.addWidget(blur_label)
        
        self.blur_slider = ModernSlider(0, 10, 0)
        blur_layout.addWidget(self.blur_slider)
        effects_controls_layout.addWidget(blur_widget)
        
        # Opcje efektów
        effects_options = [
            ("edge_enhance", self.tr("Edge enhance")),
            ("smooth", self.tr("Smoothing"))
        ]
        
        for attr, text in effects_options:
            checkbox = QCheckBox(text)
            checkbox.setStyleSheet(f"""
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
            setattr(self, attr, checkbox)
            effects_controls_layout.addWidget(checkbox)
        
        self.effects_controls.hide()
        layout.addWidget(self.effects_controls)

        # Separator
        layout.addSpacing(8)

        # Znak wodny - bez QGroupBox
        self.watermark_label = QLabel(self.tr("Watermark"))
        self.watermark_label.setStyleSheet(label_style)
        layout.addWidget(self.watermark_label)
        
        self.watermark_enabled = QCheckBox(self.tr("Add watermark"))
        self.watermark_enabled.setStyleSheet(f"""
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
        layout.addWidget(self.watermark_enabled)
        
        # Kontrolki znaku wodnego
        self.watermark_controls = QWidget()
        watermark_controls_layout = QVBoxLayout(self.watermark_controls)
        watermark_controls_layout.setSpacing(8)
        
        # Wybór pliku
        file_layout = QVBoxLayout()
        file_label = QLabel(self.tr("Watermark file"))
        file_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        file_layout.addWidget(file_label)
        
        self.watermark_btn = QPushButton(self.tr("Choose file"))
        self.watermark_btn.setStyleSheet(f"""
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
        self.watermark_path = None
        file_layout.addWidget(self.watermark_btn)
        watermark_controls_layout.addLayout(file_layout)
        
        # Wybór pozycji
        position_layout = QVBoxLayout()
        position_label = QLabel(self.tr("Position"))
        position_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        position_layout.addWidget(position_label)
        
        self.watermark_position = QComboBox()
        self.watermark_position.addItems([
            self.tr("Bottom right"), self.tr("Bottom left"),
            self.tr("Top right"), self.tr("Top left"), self.tr("Center")
        ])
        self.watermark_position.setStyleSheet(f"""
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
        position_layout.addWidget(self.watermark_position)
        watermark_controls_layout.addLayout(position_layout)
        
        # Suwaki przezroczystości i rozmiaru
        opacity_widget = QWidget()
        opacity_layout = QVBoxLayout(opacity_widget)
        opacity_layout.setSpacing(4)
        
        opacity_label = QLabel(self.tr("Opacity"))
        opacity_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        opacity_layout.addWidget(opacity_label)
        
        self.watermark_opacity = ModernSlider(10, 100, 50, "%")
        opacity_layout.addWidget(self.watermark_opacity)
        watermark_controls_layout.addWidget(opacity_widget)
        
        scale_widget = QWidget()
        scale_layout = QVBoxLayout(scale_widget)
        scale_layout.setSpacing(4)
        
        scale_label = QLabel(self.tr("Scale"))
        scale_label.setStyleSheet("font-weight: 500; font-size: 10px; color: #495057;")
        scale_layout.addWidget(scale_label)
        
        self.watermark_scale = ModernSlider(5, 50, 20, "%")
        scale_layout.addWidget(self.watermark_scale)
        watermark_controls_layout.addWidget(scale_widget)
        
        self.watermark_controls.hide()
        layout.addWidget(self.watermark_controls)

        # Przyciski akcji
        layout.addSpacing(16)
        
        # Główny przycisk
        self.process_btn = QPushButton(self.tr("Process image"))
        self.process_btn.setStyleSheet(f"""
            QPushButton {{
                background: #0079e1;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 12px;
                font-weight: 600;
                text-align: center;
            }}
            QPushButton:hover {{
                background: #0056b3;
            }}
            QPushButton:pressed {{
                background: #004494;
            }}
            QPushButton:disabled {{
                background: #e9ecef;
                color: #6c757d;
            }}
        """)
        layout.addWidget(self.process_btn)
        
        # Przyciski drugorzędne
        secondary_layout = QHBoxLayout()
        secondary_layout.setSpacing(6)
        
        self.save_btn = QPushButton(self.tr("Save"))
        self.reset_btn = QPushButton(self.tr("Reset"))
        
        for btn in [self.save_btn, self.reset_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: white;
                    color: #495057;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-weight: 500;
                    {small_font_style}
                }}
                QPushButton:hover {{
                    background: #f8f9fa;
                    border-color: #adb5bd;
                }}
                QPushButton:disabled {{
                    color: #6c757d;
                    background: #f8f9fa;
                }}
            """)
        
        secondary_layout.addWidget(self.save_btn)
        secondary_layout.addWidget(self.reset_btn)
        layout.addLayout(secondary_layout)
        
        # Sekcja postępu
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.setSpacing(6)
        
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet(f"""
            QLabel {{
                color: #0079e1;
                font-weight: 500;
                {small_font_style}
            }}
        """)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.progress_label)
        
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                height: 6px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: linear-gradient(90deg, #0079e1 0%, #00a8ff 100%);
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self.progress)
        
        self.progress_widget.hide()
        layout.addWidget(self.progress_widget)

        layout.addStretch()
        self.setLayout(layout)
        
        # Początkowo wyłączone kontrolki
        self.save_btn.setEnabled(False)
        self.process_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        
        # Usunięcie wszystkich ramek
        self.setStyleSheet("QWidget { border: none; }")

    def connect_signals(self):
        """Połączenie wszystkich sygnałów UI."""
        # Zmiany trybu tła
        self.bg_remove_radio.toggled.connect(lambda checked: self.on_bg_mode_changed("remove") if checked else None)
        self.bg_change_radio.toggled.connect(lambda checked: self.on_bg_mode_changed("change") if checked else None)

        # Przyciski typu tła
        self.bg_color_tab.clicked.connect(self.select_color_background)
        self.bg_image_tab.clicked.connect(self.select_image_background)

        # Przyciski wyboru plików
        self.bg_color_btn.clicked.connect(self.choose_background_color)
        self.bg_image_btn.clicked.connect(self.choose_background_image)
        self.watermark_btn.clicked.connect(self.choose_watermark)

        # Włączanie/wyłączanie kontrolek
        self.adjustments_enabled.toggled.connect(self.toggle_adjustments)
        self.effects_enabled.toggled.connect(self.toggle_effects)
        self.watermark_enabled.toggled.connect(self.toggle_watermark)

        # Zmiany wartości
        self.brightness_slider.valueChanged.connect(self.settings_changed.emit)
        self.contrast_slider.valueChanged.connect(self.settings_changed.emit)
        self.saturation_slider.valueChanged.connect(self.settings_changed.emit)
        self.sharpness_slider.valueChanged.connect(self.settings_changed.emit)
        self.blur_slider.valueChanged.connect(self.settings_changed.emit)

        self.watermark_opacity.valueChanged.connect(self.settings_changed.emit)
        self.watermark_scale.valueChanged.connect(self.settings_changed.emit)

        # Inne kontrolki
        self.watermark_position.currentTextChanged.connect(self.settings_changed.emit)
        self.edge_enhance.toggled.connect(self.settings_changed.emit)
        self.smooth.toggled.connect(self.settings_changed.emit)

        # Reset adjustments button
        self.reset_adj_btn.clicked.connect(self.reset_adjustments)

    def reset_adjustments(self):
        """Resetuj wszystkie suwaki regulacji do zera."""
        self.brightness_slider.setValue(0)
        self.contrast_slider.setValue(0)
        self.saturation_slider.setValue(0)
        self.sharpness_slider.setValue(0)
        self.settings_changed.emit()

    def on_bg_mode_changed(self, mode):
        """Obsługa zmiany trybu tła."""
        if mode == "remove":
            self.bg_options_stack.setCurrentIndex(0)
        else:  # change
            self.bg_options_stack.setCurrentIndex(1)
        self.settings_changed.emit()

    def toggle_adjustments(self, enabled):
        """Pokazuj/ukryj kontrolki regulacji."""
        self.adj_controls.setVisible(enabled)
        self.settings_changed.emit()

    def toggle_effects(self, enabled):
        """Pokazuj/ukryj kontrolki efektów."""
        self.effects_controls.setVisible(enabled)
        self.settings_changed.emit()

    def toggle_watermark(self, enabled):
        """Pokazuj/ukryj kontrolki znaku wodnego."""
        self.watermark_controls.setVisible(enabled)
        self.settings_changed.emit()

    def select_color_background(self):
        """Ensure only the color tab is active and update the stack."""
        self.bg_color_tab.setChecked(True)
        self.bg_image_tab.setChecked(False)
        self.bg_type_stack.setCurrentIndex(0)
        self.settings_changed.emit()

    def select_image_background(self):
        """Ensure only the image tab is active and update the stack."""
        self.bg_color_tab.setChecked(False)
        self.bg_image_tab.setChecked(True)
        self.bg_type_stack.setCurrentIndex(1)
        self.settings_changed.emit()

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
            self.settings_changed.emit()

    def choose_background_image(self):
        """Wybór obrazu tła."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Wybierz obraz tła", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.heic *.HEIC)"
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
            self.settings_changed.emit()

    def choose_watermark(self):
        """Wybór pliku znaku wodnego."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Wybierz znak wodny", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.heic *.HEIC)"
        )
        if file_name:
            self.watermark_path = file_name
            self.watermark_btn.setText(f"✓ {Path(file_name).name}")
            self.watermark_btn.setStyleSheet("""
                QPushButton {
                    background: #d4edda;
                    color: #155724;
                    border: 2px solid #c3e6cb;
                    border-radius: 6px;
                    padding: 8px;
                    font-weight: 500;
                    font-size: 10px;
                }
            """)
            self.settings_changed.emit()

    def get_settings(self):
        """Pobierz aktualne ustawienia."""
        # Określ tryb tła
        bg_mode = "remove"
        if self.bg_remove_radio.isChecked():
            bg_mode = "remove"
        elif self.bg_change_radio.isChecked():
            if self.bg_color_tab.isChecked():
                bg_mode = "color"
            else:
                bg_mode = "image"

        # Mapowanie pozycji
        position_map = {
            self.tr("Bottom right"): "bottom-right",
            self.tr("Bottom left"): "bottom-left",
            self.tr("Top right"): "top-right",
            self.tr("Top left"): "top-left",
            self.tr("Center"): "center"
        }

        return {
            'bg_mode': bg_mode,
            'bg_color': self.bg_color,
            'bg_image': self.bg_image_path,
            'adjustments_enabled': self.adjustments_enabled.isChecked(),
            'brightness': self.brightness_slider.value(),
            'contrast': self.contrast_slider.value(),
            'saturation': self.saturation_slider.value(),
            'sharpness': self.sharpness_slider.value(),
            'effects_enabled': self.effects_enabled.isChecked(),
            'blur': self.blur_slider.value(),
            'edge_enhance': self.edge_enhance.isChecked(),
            'smooth': self.smooth.isChecked(),
            'watermark_enabled': self.watermark_enabled.isChecked(),
            'watermark_path': self.watermark_path,
            'watermark_position': position_map.get(self.watermark_position.currentText(), 'bottom-right'),
            'watermark_opacity': self.watermark_opacity.value() / 100.0,
            'watermark_scale': self.watermark_scale.value() / 100.0
        }

    def reset_settings(self):
        """Reset wszystkich ustawień do domyślnych."""
        self.bg_remove_radio.setChecked(True)
        self.bg_color = "#FFFFFF"
        self.bg_color_display.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 6px;
            }
        """)
        self.bg_image_path = None
        self.bg_image_btn.setText(self.tr("Choose background image"))
        self.bg_image_btn.setStyleSheet("""
            QPushButton {
                background: #0079e1;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)
        
        self.adjustments_enabled.setChecked(False)
        self.adj_controls.hide()
        self.brightness_slider.setValue(0)
        self.contrast_slider.setValue(0)
        self.saturation_slider.setValue(0)
        self.sharpness_slider.setValue(0)
        
        self.effects_enabled.setChecked(False)
        self.effects_controls.hide()
        self.blur_slider.setValue(0)
        self.edge_enhance.setChecked(False)
        self.smooth.setChecked(False)
        
        self.watermark_enabled.setChecked(False)
        self.watermark_controls.hide()
        self.watermark_path = None
        self.watermark_btn.setText(self.tr("Choose file"))
        self.watermark_btn.setStyleSheet("""
            QPushButton {
                background: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 6px;
                padding: 8px;
                color: #6c757d;
                font-weight: 500;
                font-size: 10px;
            }
            QPushButton:hover {
                border-color: #0079e1;
                color: #0079e1;
            }
        """)
        self.watermark_position.setCurrentIndex(0)
        self.watermark_opacity.setValue(50)
        self.watermark_scale.setValue(20)

    def enable_controls(self, enabled=True):
        """Włącz/wyłącz kontrolki przetwarzania."""
        self.process_btn.setEnabled(enabled)
        self.save_btn.setEnabled(enabled)
        self.reset_btn.setEnabled(enabled)

    def changeEvent(self, event):
        """Obsługuje zmianę języka."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def retranslate_ui(self):
        """Retransluje wszystkie teksty w kontrolkach."""
        try:
            # Sekcje główne
            self.bg_label.setText(self.tr("Background processing"))
            self.adj_label.setText(self.tr("Image adjustments"))
            self.effects_label.setText(self.tr("Special effects"))
            self.watermark_label.setText(self.tr("Watermark"))

            # Radio buttony tła
            self.bg_remove_radio.setText(self.tr("Remove background"))
            self.bg_change_radio.setText(self.tr("Change background"))

            # Przyciski
            self.bg_color_btn.setText(self.tr("Choose color"))
            self.bg_image_btn.setText(self.tr("Choose background image"))
            self.bg_color_tab.setText(self.tr("Color"))
            self.bg_image_tab.setText(self.tr("Image"))

            # Checkboxy
            self.adjustments_enabled.setText(self.tr("Enable image adjustments"))
            self.effects_enabled.setText(self.tr("Enable special effects"))
            self.watermark_enabled.setText(self.tr("Add watermark"))

            # Pozostałe przyciski
            self.reset_adj_btn.setText(self.tr("Reset adjustments"))
            self.watermark_btn.setText(self.tr("Choose file"))
            self.process_btn.setText(self.tr("Process image"))
            self.save_btn.setText(self.tr("Save"))
            self.reset_btn.setText(self.tr("Reset"))

            # ComboBox pozycji
            current_pos = self.watermark_position.currentIndex()
            self.watermark_position.clear()
            self.watermark_position.addItems([
                self.tr("Bottom right"), self.tr("Bottom left"),
                self.tr("Top right"), self.tr("Top left"), self.tr("Center")
            ])
            self.watermark_position.setCurrentIndex(current_pos)

        except Exception as e:
            logger.error(f"Error retranslating ImageProcessingControls: {e}")

class SinglePhotoView(QWidget):
    """Nowoczesny widok przetwarzania pojedynczego zdjęcia."""

    processing_started = pyqtSignal()
    processing_finished = pyqtSignal()
    processing_progress = pyqtSignal(int)

    def tr(self, text):
        from PyQt6.QtWidgets import QApplication
        return QApplication.translate("SinglePhotoView", text)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.current_image_path = None
        self.processed_image_path = None
        self.processing_thread = None
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Inicjalizacja nowoczesnego UI."""
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Lewa strona - Podgląd zdjęcia
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
        
        # Nagłówek z tytułem i przyciskiem wyboru
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel(self.tr("Photo Processing"))
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
        
        self.select_file_btn = QPushButton(self.tr("Select Photo"))
        self.select_file_btn.setStyleSheet("""
            QPushButton {
                background: #0079e1;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)
        header_layout.addWidget(self.select_file_btn)
        
        left_layout.addLayout(header_layout)
        
        # Podgląd obrazu
        self.preview = ImagePreviewWidget()
        left_layout.addWidget(self.preview)
        
        # Informacje o pliku
        self.file_info_label = QLabel(self.tr("No file selected"))
        self.file_info_label.setStyleSheet("""
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
        left_layout.addWidget(self.file_info_label)
        
        # Prawa strona - Kontrolki w obszarze przewijania
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
        
        self.controls = ImageProcessingControls()
        controls_scroll.setWidget(self.controls)
        
        # Główny układ
        main_layout.addWidget(left_widget, 2)
        main_layout.addWidget(controls_scroll, 1)
        
        self.setLayout(main_layout)
        
        # Tło głównego widgetu
        self.setStyleSheet("""
            SinglePhotoView {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #764ba2);
            }
        """)

    def connect_signals(self):
        """Połączenie sygnałów UI."""
        self.select_file_btn.clicked.connect(self.open_file_dialog)
        self.preview.image_dropped.connect(self.load_image)
        self.preview.file_dialog_requested.connect(self.open_file_dialog)
        
        self.controls.process_btn.clicked.connect(self.process_image)
        self.controls.save_btn.clicked.connect(self.save_image)
        self.controls.reset_btn.clicked.connect(self.reset_image)
        
        self.processing_started.connect(self.on_processing_start)
        self.processing_finished.connect(self.on_processing_end)

    def open_file_dialog(self):
        """Otwórz dialog wyboru pliku."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select a photo"), "",
            self.tr("Images (*.png *.jpg *.jpeg *.bmp *.tiff *.gif *.webp *.heic *.HEIC);;All Files (*)")
        )
        if file_name:
            self.load_image(file_name)

    def load_image(self, image_path):
        """Załaduj obraz do widoku."""
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError("Plik nie istnieje")
                
            self.current_image_path = image_path
            self.processed_image_path = None
            self.preview.setImage(image_path)
            
            file_info = self.get_file_info(image_path)
            self.file_info_label.setText(file_info)
            
            self.controls.enable_controls(True)
            
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Cannot load image:") + "\n" + str(e))

    def get_file_info(self, image_path):
        """Pobierz informacje o pliku."""
        try:
            path = Path(image_path)
            stat = path.stat()
            
            with Image.open(image_path) as img:
                width, height = img.size
                mode = img.mode
                
            size_mb = stat.st_size / (1024 * 1024)
            
            return (f"📁 {path.name}\n"
                   f"🖼️ {width} × {height} px\n"
                   f"🎨 {mode}\n"
                   f"💾 {size_mb:.1f} MB")
                   
        except Exception:
            return f"📁 {Path(image_path).name}"

    def process_image(self):
        """Przetwórz obraz z aktualnymi ustawieniami."""
        if not self.current_image_path:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please select a photo to process first."))
            return

        settings = self.controls.get_settings()

        # Ensure processing only starts after background is removed
        if settings.get('bg_mode') == 'keep' and (
            settings.get('adjustments_enabled') or settings.get('effects_enabled') or settings.get('watermark_enabled')
        ):
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please remove the background first before applying effects or watermark."))
            return

        if not self.has_changes(settings):
            QMessageBox.information(self, self.tr("Info"), self.tr("No changes detected to apply."))
            return

        self.processing_started.emit()
        
        self.processing_thread = ImageProcessingThread(self.current_image_path, settings)
        self.processing_thread.progress_updated.connect(self.update_progress_with_text)
        self.processing_thread.processing_finished.connect(self.on_image_processed)
        self.processing_thread.error_occurred.connect(self.on_processing_error)
        self.processing_thread.start()

    def has_changes(self, settings):
        """Sprawdź czy są jakieś zmiany do zastosowania."""
        return (settings.get('bg_mode') == 'remove' or
                settings.get('bg_mode') == 'color' or
                settings.get('bg_mode') == 'image' or
                settings.get('adjustments_enabled') or
                settings.get('effects_enabled') or
                settings.get('watermark_enabled'))

    def update_progress_with_text(self, value, text):
        """Aktualizuj pasek postępu z tekstem."""
        self.controls.progress.setValue(value)
        self.controls.progress_label.setText(text)

    def on_image_processed(self, processed_path):
        """Obsłuż zakończone przetwarzanie obrazu - Z DEBUGIEM."""
        print(f"DEBUG: on_image_processed called with: {processed_path}")
        
        # Sprawdź czy plik istnieje
        if not os.path.exists(processed_path):
            print(f"DEBUG: Processed file does not exist: {processed_path}")
            return
            
        file_size = os.path.getsize(processed_path)
        print(f"DEBUG: Processed file size: {file_size} bytes")
        
        self.processed_image_path = processed_path
        
        print("DEBUG: Calling preview.setImage...")
        self.preview.setImage(processed_path)
        print("DEBUG: preview.setImage completed")
        
        file_info = self.get_file_info(processed_path) + "\n✅ " + self.tr("Processed")
        self.file_info_label.setText(file_info)
        
        self.processing_finished.emit()
        
        # Pokaż komunikat sukcesu
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle(self.tr("Success"))
        msg.setText(self.tr("The image has been successfully processed!"))
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

    def on_processing_error(self, error_message):
        """Obsłuż błąd przetwarzania."""
        self.processing_finished.emit()
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(self.tr("Processing error"))
        msg.setText(error_message)
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

    def save_image(self):
        """Zapisz przetworzony obraz."""
        if not self.processed_image_path and not self.current_image_path:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("No image to save."))
            return

        source_path = self.processed_image_path or self.current_image_path
        
        original_name = Path(self.current_image_path).stem if self.current_image_path else "processed_image"
        default_name = f"{original_name}_processed.png"
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save image"), default_name,
            self.tr("PNG (*.png);;JPEG (*.jpg);;WebP (*.webp);;All Files (*)")
        )
        
        if save_path:
            try:
                save_extension = Path(save_path).suffix.lower()
                
                with Image.open(source_path) as img:
                    if save_extension in ['.jpg', '.jpeg']:
                        if img.mode in ('RGBA', 'LA', 'P'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                            img = background
                        img.save(save_path, 'JPEG', quality=90, optimize=True)
                    elif save_extension == '.webp':
                        img.save(save_path, 'WebP', quality=90, optimize=True)
                    else:
                        img.save(save_path, optimize=True)
                
                # Komunikat sukcesu
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle(self.tr("Success"))
                msg.setText(self.tr("Image saved as:") + f"\n{save_path}")
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
                
                self.settings.set_value('export', 'last_save_path', str(Path(save_path).parent))
                
            except Exception as e:
                QMessageBox.critical(self, self.tr("Saving error"), self.tr("Cannot save image:") + "\n" + str(e))

    def reset_image(self):
        """Resetuj wszystkie zmiany."""
        if not self.current_image_path:
            return
            
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(self.tr("Confirmation"))
        msg.setText(self.tr("Are you sure you want to reset all changes?"))
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.setStyleSheet("""
            QMessageBox {
                background: white;
                border-radius: 8px;
            }
            QMessageBox QPushButton {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                min-width: 80px;
            }
            QMessageBox QPushButton[text="Yes"] {
                background: #dc3545;
                color: white;
                border-color: #dc3545;
            }
            QMessageBox QPushButton[text="Yes"]:hover {
                background: #c82333;
            }
            QMessageBox QPushButton[text="No"] {
                background: #6c757d;
                color: white;
                border-color: #6c757d;
            }
            QMessageBox QPushButton[text="No"]:hover {
                background: #545b62;
            }
        """)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.controls.reset_settings()
            self.preview.setImage(self.current_image_path)
            self.processed_image_path = None
            
            file_info = self.get_file_info(self.current_image_path)
            self.file_info_label.setText(file_info)

    def on_processing_start(self):
        """Obsłuż rozpoczęcie przetwarzania."""
        self.controls.progress_widget.show()
        self.controls.process_btn.setEnabled(False)
        self.controls.save_btn.setEnabled(False)
        self.controls.reset_btn.setEnabled(False)
        self.select_file_btn.setEnabled(False)
        
        # Aktualizuj tekst przycisku
        self.controls.process_btn.setText(self.tr("Processing..."))
        self.controls.process_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 12px;
                font-weight: 600;
            }
        """)

    def on_processing_end(self):
        """Obsłuż zakończenie przetwarzania."""
        QTimer.singleShot(2000, self.hide_progress)
        
        self.controls.process_btn.setEnabled(True)
        self.controls.save_btn.setEnabled(True)
        self.controls.reset_btn.setEnabled(True)
        self.select_file_btn.setEnabled(True)
        
        # Przywróć przycisk
        self.controls.process_btn.setText(self.tr("Process image"))
        self.controls.process_btn.setStyleSheet("""
            QPushButton {
                background: #0079e1;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 12px;
                font-weight: 600;
                text-align: center;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)

    def retranslate_ui(self):
        """Update all UI texts for current language."""
        self.title_label.setText(self.tr("Photo Processing"))
        self.select_file_btn.setText(self.tr("Select Photo"))
        self.file_info_label.setText(self.tr("No file selected"))
        self.controls.bg_label.setText(self.tr("Background processing"))
        self.controls.adj_label.setText(self.tr("Image adjustments"))
        self.controls.effects_label.setText(self.tr("Special effects"))
        self.controls.watermark_label.setText(self.tr("Watermark"))
        self.controls.bg_color_btn.setText(self.tr("Choose color"))
        self.controls.bg_image_btn.setText(self.tr("Choose background image"))
        self.controls.bg_color_tab.setText(self.tr("Color"))
        self.controls.bg_image_tab.setText(self.tr("Image"))
        self.controls.adjustments_enabled.setText(self.tr("Enable image adjustments"))
        self.controls.reset_adj_btn.setText(self.tr("Reset adjustments"))
        self.controls.effects_enabled.setText(self.tr("Enable special effects"))
        self.controls.watermark_enabled.setText(self.tr("Add watermark"))
        self.controls.watermark_btn.setText(self.tr("Choose file"))
        self.controls.save_btn.setText(self.tr("Save"))
        self.controls.reset_btn.setText(self.tr("Reset"))
        self.controls.process_btn.setText(self.tr("Process image"))
        self.controls.watermark_position.clear()
        self.controls.watermark_position.addItems([
            self.tr("Bottom right"), self.tr("Bottom left"),
            self.tr("Top right"), self.tr("Top left"), self.tr("Center")
        ])

    def hide_progress(self):
        """Ukryj widget postępu."""
        self.controls.progress_widget.hide()

    def changeEvent(self, event):
        """Obsługuje zmianę języka."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def closeEvent(self, event):
        """Obsłuż zamknięcie widgetu."""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.terminate()
            self.processing_thread.wait()
            
        if self.processed_image_path and os.path.exists(self.processed_image_path):
            try:
                os.unlink(self.processed_image_path)
            except:
                pass
                
        event.accept()

    def get_current_image_for_export(self):
        """Pobierz aktualny obraz do eksportu."""
        return self.processed_image_path or self.current_image_path

    def get_processing_settings(self):
        """Pobierz aktualne ustawienia przetwarzania."""
        return self.controls.get_settings()