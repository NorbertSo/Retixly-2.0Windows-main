from PyQt6.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLabel, QComboBox, QCheckBox,
                           QSpinBox, QDoubleSpinBox, QLineEdit, QFileDialog,
                           QGroupBox, QFormLayout, QColorDialog, QSlider,
                           QMessageBox, QTextEdit, QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class ProcessingSettingsTab(QWidget):
    """Zakładka ustawień przetwarzania."""
    
    def __init__(self, settings_controller):
        super().__init__()
        self.settings = settings_controller
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Grupa Ustawienia przetwarzania
        processing_group = QGroupBox("Ustawienia przetwarzania obrazów")
        processing_layout = QFormLayout()
        
        # Domyślna jakość JPEG
        self.jpeg_quality = QSpinBox()
        self.jpeg_quality.setRange(1, 100)
        self.jpeg_quality.setValue(85)
        self.jpeg_quality.setSuffix("%")
        processing_layout.addRow("Jakość JPEG:", self.jpeg_quality)
        
        # Domyślne tło
        self.default_background = QLineEdit()
        self.default_background.setText("#FFFFFF")
        self.default_background.setPlaceholderText("#FFFFFF lub nazwa koloru")
        
        self.bg_color_btn = QPushButton("Wybierz kolor")
        self.bg_color_btn.clicked.connect(self.choose_background_color)
        
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(self.default_background)
        bg_layout.addWidget(self.bg_color_btn)
        processing_layout.addRow("Domyślne tło:", bg_layout)
        
        # Optymalizacja wyjścia
        self.optimize_output = QCheckBox("Optymalizuj pliki wyjściowe")
        self.optimize_output.setChecked(True)
        processing_layout.addRow("", self.optimize_output)
        
        # Zachowywanie metadanych
        self.preserve_metadata = QCheckBox("Zachowuj metadane EXIF")
        self.preserve_metadata.setChecked(False)
        processing_layout.addRow("", self.preserve_metadata)
        
        processing_group.setLayout(processing_layout)
        layout.addWidget(processing_group)
        
        # Grupa Wydajność
        performance_group = QGroupBox("Wydajność")
        performance_layout = QFormLayout()
        
        # Liczba wątków
        self.thread_count = QSpinBox()
        self.thread_count.setRange(1, 16)
        self.thread_count.setValue(4)
        performance_layout.addRow("Liczba wątków:", self.thread_count)
        
        # Rozmiar cache
        self.cache_size = QSpinBox()
        self.cache_size.setRange(100, 5000)
        self.cache_size.setValue(500)
        self.cache_size.setSuffix(" MB")
        performance_layout.addRow("Rozmiar cache:", self.cache_size)
        
        # GPU acceleration
        self.gpu_acceleration = QCheckBox("Użyj przyspieszenia GPU (jeśli dostępne)")
        self.gpu_acceleration.setChecked(False)
        performance_layout.addRow("", self.gpu_acceleration)
        
        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)
        
        # Grupa Automatyzacja
        automation_group = QGroupBox("Automatyzacja")
        automation_layout = QVBoxLayout()
        
        self.auto_backup = QCheckBox("Automatyczne tworzenie kopii zapasowych")
        self.auto_backup.setChecked(True)
        automation_layout.addWidget(self.auto_backup)
        
        self.auto_resize = QCheckBox("Automatyczne dopasowanie rozmiaru dla marketplace")
        self.auto_resize.setChecked(True)
        automation_layout.addWidget(self.auto_resize)
        
        self.batch_notifications = QCheckBox("Powiadomienia o zakończeniu przetwarzania wsadowego")
        self.batch_notifications.setChecked(True)
        automation_layout.addWidget(self.batch_notifications)
        
        automation_group.setLayout(automation_layout)
        layout.addWidget(automation_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def choose_background_color(self):
        """Wybór koloru tła."""
        current_color = QColor(self.default_background.text())
        color = QColorDialog.getColor(current_color, self)
        if color.isValid():
            self.default_background.setText(color.name())
        
    def load_settings(self):
        """Wczytuje ustawienia z kontrolera."""
        try:
            processing_settings = self.settings.get_section('processing')
            
            self.jpeg_quality.setValue(processing_settings.get('jpeg_quality', 85))
            self.default_background.setText(processing_settings.get('default_background', '#FFFFFF'))
            self.optimize_output.setChecked(processing_settings.get('optimize_output', True))
            self.preserve_metadata.setChecked(processing_settings.get('preserve_metadata', False))
            
            # Performance settings
            self.thread_count.setValue(processing_settings.get('thread_count', 4))
            self.cache_size.setValue(processing_settings.get('cache_size', 500))
            self.gpu_acceleration.setChecked(processing_settings.get('gpu_acceleration', False))
            
            # Automation settings  
            self.auto_backup.setChecked(processing_settings.get('auto_backup', True))
            self.auto_resize.setChecked(processing_settings.get('auto_resize', True))
            self.batch_notifications.setChecked(processing_settings.get('batch_notifications', True))
            
        except Exception as e:
            print(f"Error loading processing settings: {e}")

    def save_settings(self):
        """Zapisuje ustawienia do kontrolera."""
        try:
            # Processing settings
            self.settings.set_value('processing', 'jpeg_quality', self.jpeg_quality.value())
            self.settings.set_value('processing', 'default_background', self.default_background.text())
            self.settings.set_value('processing', 'optimize_output', self.optimize_output.isChecked())
            self.settings.set_value('processing', 'preserve_metadata', self.preserve_metadata.isChecked())
            
            # Performance settings
            self.settings.set_value('processing', 'thread_count', self.thread_count.value())
            self.settings.set_value('processing', 'cache_size', self.cache_size.value())
            self.settings.set_value('processing', 'gpu_acceleration', self.gpu_acceleration.isChecked())
            
            # Automation settings
            self.settings.set_value('processing', 'auto_backup', self.auto_backup.isChecked())
            self.settings.set_value('processing', 'auto_resize', self.auto_resize.isChecked())
            self.settings.set_value('processing', 'batch_notifications', self.batch_notifications.isChecked())
            
        except Exception as e:
            print(f"Error saving processing settings: {e}")

class GeneralSettingsTab(QWidget):
    """Zakładka ustawień ogólnych."""
    
    def __init__(self, settings_controller):
        super().__init__()
        self.settings = settings_controller
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Grupa Język i Region
        language_group = QGroupBox(self.tr("Language & Localization"))
        lang_layout = QFormLayout()
        
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            self.tr('English'),
            self.tr('Polish'),
            self.tr('German'),
            self.tr('French')
        ])
        lang_layout.addRow("Język interfejsu:", self.language_combo)
        
        language_group.setLayout(lang_layout)
        layout.addWidget(language_group)
        
        # Grupa Wygląd
        appearance_group = QGroupBox(self.tr("Appearance"))
        appearance_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            self.tr('Light'),
            self.tr('Dark'),
            self.tr('Auto')
        ])
        appearance_layout.addRow("Motyw:", self.theme_combo)
        
        self.ui_scale = QSpinBox()
        self.ui_scale.setRange(80, 200)
        self.ui_scale.setValue(100)
        self.ui_scale.setSuffix("%")
        appearance_layout.addRow("Skala interfejsu:", self.ui_scale)
        
        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)
        
        # Grupa Zachowanie
        behavior_group = QGroupBox("Zachowanie aplikacji")
        behavior_layout = QVBoxLayout()
        
        self.auto_save = QCheckBox("Automatyczny zapis projektów")
        self.auto_save.setChecked(True)
        behavior_layout.addWidget(self.auto_save)
        
        self.check_updates = QCheckBox("Sprawdzaj aktualizacje przy starcie")
        self.check_updates.setChecked(True)
        behavior_layout.addWidget(self.check_updates)
        
        self.confirm_exit = QCheckBox("Potwierdź wyjście z aplikacji")
        self.confirm_exit.setChecked(True)
        behavior_layout.addWidget(self.confirm_exit)
        
        self.remember_window = QCheckBox("Zapamiętuj rozmiar i pozycję okna")
        self.remember_window.setChecked(True)
        behavior_layout.addWidget(self.remember_window)
        
        behavior_group.setLayout(behavior_layout)
        layout.addWidget(behavior_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def load_settings(self):
        """Wczytuje ustawienia z kontrolera."""
        # Język
        current_lang = self.settings.get_language()
        lang_map = {'en': 'English', 'pl': 'Polski', 'de': 'Deutsch', 'fr': 'Français'}
        self.language_combo.setCurrentText(lang_map.get(current_lang, 'English'))
        
        # Motyw
        self.theme_combo.setCurrentText(self.settings.get_theme().capitalize())
        
        # Inne ustawienia
        self.auto_save.setChecked(self.settings.get_value('general', 'auto_save', True))
        self.check_updates.setChecked(self.settings.get_value('general', 'check_updates', True))
        self.confirm_exit.setChecked(self.settings.get_value('general', 'confirm_exit', True))
        self.remember_window.setChecked(self.settings.get_value('general', 'remember_window', True))
        self.ui_scale.setValue(self.settings.get_value('general', 'ui_scale', 100))

    def save_settings(self):
        """Zapisuje ustawienia do kontrolera."""
        # Mapowanie języków
        lang_map = {'English': 'en', 'Polski': 'pl', 'Deutsch': 'de', 'Français': 'fr'}
        self.settings.set_language(lang_map.get(self.language_combo.currentText(), 'en'))
        
        # Motyw
        self.settings.set_theme(self.theme_combo.currentText().lower())
        
        # Inne ustawienia
        self.settings.set_value('general', 'auto_save', self.auto_save.isChecked())
        self.settings.set_value('general', 'check_updates', self.check_updates.isChecked())
        self.settings.set_value('general', 'confirm_exit', self.confirm_exit.isChecked())
        self.settings.set_value('general', 'remember_window', self.remember_window.isChecked())
        self.settings.set_value('general', 'ui_scale', self.ui_scale.value())


class WatermarkSettingsTab(QWidget):
    """Zakładka ustawień znaku wodnego."""
    
    def __init__(self, settings_controller):
        super().__init__()
        self.settings = settings_controller
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Grupa Podstawowe ustawienia
        basic_group = QGroupBox("Podstawowe ustawienia")
        basic_layout = QVBoxLayout()
        
        self.watermark_enabled = QCheckBox("Włącz znak wodny")
        self.watermark_enabled.stateChanged.connect(self.toggle_watermark_options)
        basic_layout.addWidget(self.watermark_enabled)
        
        # Wybór pliku znaku wodnego
        file_layout = QHBoxLayout()
        self.watermark_path = QLineEdit()
        self.watermark_path.setPlaceholderText("Wybierz plik znaku wodnego...")
        self.browse_watermark = QPushButton("Przeglądaj")
        self.browse_watermark.clicked.connect(self.browse_watermark_file)
        
        file_layout.addWidget(QLabel("Plik znaku wodnego:"))
        file_layout.addWidget(self.watermark_path)
        file_layout.addWidget(self.browse_watermark)
        basic_layout.addLayout(file_layout)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # Grupa Pozycjonowanie
        position_group = QGroupBox("Pozycjonowanie")
        position_layout = QFormLayout()
        
        self.watermark_position = QComboBox()
        self.watermark_position.addItems([
            "Góra-lewo", "Góra-środek", "Góra-prawo",
            "Środek-lewo", "Środek", "Środek-prawo", 
            "Dół-lewo", "Dół-środek", "Dół-prawo"
        ])
        self.watermark_position.setCurrentText("Dół-prawo")
        position_layout.addRow("Pozycja:", self.watermark_position)
        
        self.margin_x = QSpinBox()
        self.margin_x.setRange(0, 500)
        self.margin_x.setValue(10)
        self.margin_x.setSuffix(" px")
        position_layout.addRow("Margines X:", self.margin_x)
        
        self.margin_y = QSpinBox()
        self.margin_y.setRange(0, 500)
        self.margin_y.setValue(10)
        self.margin_y.setSuffix(" px")
        position_layout.addRow("Margines Y:", self.margin_y)
        
        position_group.setLayout(position_layout)
        layout.addWidget(position_group)
        
        # Grupa Wygląd
        appearance_group = QGroupBox("Wygląd")
        appearance_layout = QFormLayout()
        
        # Przezroczystość
        opacity_layout = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(50)
        self.opacity_value = QLabel("50%")
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_value.setText(f"{v}%")
        )
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_value)
        appearance_layout.addRow("Przezroczystość:", opacity_layout)
        
        # Skala
        scale_layout = QHBoxLayout()
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(5, 100)
        self.scale_slider.setValue(20)
        self.scale_value = QLabel("20%")
        self.scale_slider.valueChanged.connect(
            lambda v: self.scale_value.setText(f"{v}%")
        )
        scale_layout.addWidget(self.scale_slider)
        scale_layout.addWidget(self.scale_value)
        appearance_layout.addRow("Skala:", scale_layout)
        
        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)
        
        # Grupa Opcje zaawansowane
        advanced_group = QGroupBox("Opcje zaawansowane")
        advanced_layout = QVBoxLayout()
        
        self.rotate_watermark = QCheckBox("Obróć znak wodny o 45°")
        advanced_layout.addWidget(self.rotate_watermark)
        
        self.tile_watermark = QCheckBox("Kafelkuj znak wodny")
        advanced_layout.addWidget(self.tile_watermark)
        
        self.adaptive_size = QCheckBox("Dostosuj rozmiar do obrazu")
        self.adaptive_size.setChecked(True)
        advanced_layout.addWidget(self.adaptive_size)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # Początkowo wyłącz opcje znaku wodnego
        self.watermark_options_widget = QWidget()
        options_layout = QVBoxLayout()
        options_layout.addWidget(position_group)
        options_layout.addWidget(appearance_group)
        options_layout.addWidget(advanced_group)
        self.watermark_options_widget.setLayout(options_layout)
        self.watermark_options_widget.setEnabled(False)
        
        layout.addWidget(self.watermark_options_widget)
        layout.addStretch()
        self.setLayout(layout)
        
    def toggle_watermark_options(self, state):
        """Włącza/wyłącza opcje znaku wodnego."""
        enabled = state == Qt.CheckState.Checked.value
        self.watermark_options_widget.setEnabled(enabled)
        
    def browse_watermark_file(self):
        """Wybór pliku znaku wodnego."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik znaku wodnego",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.svg);;All Files (*)"
        )
        if file_name:
            self.watermark_path.setText(file_name)
        
    def load_settings(self):
        """Wczytuje ustawienia z kontrolera."""
        watermark_settings = self.settings.get_watermark_settings()
        
        self.watermark_enabled.setChecked(watermark_settings.get('enabled', False))
        self.watermark_path.setText(watermark_settings.get('path', ''))
        
        # Pozycja - mapowanie z angielskiego na polski
        position_map = {
            'top-left': 'Góra-lewo', 'top-center': 'Góra-środek', 'top-right': 'Góra-prawo',
            'center-left': 'Środek-lewo', 'center': 'Środek', 'center-right': 'Środek-prawo',
            'bottom-left': 'Dół-lewo', 'bottom-center': 'Dół-środek', 'bottom-right': 'Dół-prawo'
        }
        pos = watermark_settings.get('position', 'bottom-right')
        self.watermark_position.setCurrentText(position_map.get(pos, 'Dół-prawo'))
        
        # Inne ustawienia
        self.margin_x.setValue(watermark_settings.get('margin_x', 10))
        self.margin_y.setValue(watermark_settings.get('margin_y', 10))
        
        opacity = int(watermark_settings.get('opacity', 0.5) * 100)
        self.opacity_slider.setValue(opacity)
        self.opacity_value.setText(f"{opacity}%")
        
        scale = int(watermark_settings.get('scale', 0.2) * 100)
        self.scale_slider.setValue(scale)
        self.scale_value.setText(f"{scale}%")
        
        # Opcje zaawansowane
        self.rotate_watermark.setChecked(watermark_settings.get('rotate', False))
        self.tile_watermark.setChecked(watermark_settings.get('tile', False))
        self.adaptive_size.setChecked(watermark_settings.get('adaptive_size', True))
        
        # Aktualizuj stan widgetu opcji
        self.toggle_watermark_options(
            Qt.CheckState.Checked.value if self.watermark_enabled.isChecked() 
            else Qt.CheckState.Unchecked.value
        )

    def save_settings(self):
        """Zapisuje ustawienia do kontrolera."""
        # Mapowanie pozycji z polskiego na angielski
        position_map = {
            'Góra-lewo': 'top-left', 'Góra-środek': 'top-center', 'Góra-prawo': 'top-right',
            'Środek-lewo': 'center-left', 'Środek': 'center', 'Środek-prawo': 'center-right',
            'Dół-lewo': 'bottom-left', 'Dół-środek': 'bottom-center', 'Dół-prawo': 'bottom-right'
        }
        
        watermark_settings = {
            'enabled': self.watermark_enabled.isChecked(),
            'path': self.watermark_path.text(),
            'position': position_map.get(self.watermark_position.currentText(), 'bottom-right'),
            'margin_x': self.margin_x.value(),
            'margin_y': self.margin_y.value(),
            'opacity': self.opacity_slider.value() / 100.0,
            'scale': self.scale_slider.value() / 100.0,
            'rotate': self.rotate_watermark.isChecked(),
            'tile': self.tile_watermark.isChecked(),
            'adaptive_size': self.adaptive_size.isChecked()
        }
        
        # Zapisz każde ustawienie osobno
        for key, value in watermark_settings.items():
            self.settings.set_value('watermark', key, value)

class ExportSettingsTab(QWidget):
    """Zakładka ustawień eksportu."""
    
    def __init__(self, settings_controller):
        super().__init__()
        self.settings = settings_controller
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Grupa Domyślne ustawienia
        defaults_group = QGroupBox("Domyślne ustawienia eksportu")
        defaults_layout = QFormLayout()
        
        self.default_format = QComboBox()
        self.default_format.addItems(['PNG', 'JPEG', 'WEBP', 'BMP', 'TIFF'])
        defaults_layout.addRow("Domyślny format:", self.default_format)
        
        # Domyślna ścieżka
        path_layout = QHBoxLayout()
        self.default_path = QLineEdit()
        self.browse_path = QPushButton("Przeglądaj")
        self.browse_path.clicked.connect(self.browse_default_path)
        path_layout.addWidget(self.default_path)
        path_layout.addWidget(self.browse_path)
        defaults_layout.addRow("Domyślna ścieżka:", path_layout)
        
        # Wzorzec nazwy pliku
        self.filename_pattern = QLineEdit()
        self.filename_pattern.setText("{original_name}_{size}")
        self.filename_pattern.setPlaceholderText("np. {original_name}_{timestamp}")
        defaults_layout.addRow("Wzorzec nazwy:", self.filename_pattern)
        
        # Podpowiedzi dla wzorca
        pattern_help = QLabel(
            "Dostępne zmienne: {original_name}, {timestamp}, {date}, {time}, {size}, {format}"
        )
        pattern_help.setStyleSheet("color: #666; font-size: 11px;")
        defaults_layout.addRow("", pattern_help)
        
        defaults_group.setLayout(defaults_layout)
        layout.addWidget(defaults_group)
        
        # Grupa Marketplace
        marketplace_group = QGroupBox("Ustawienia Marketplace")
        marketplace_layout = QFormLayout()
        
        self.default_marketplace = QComboBox()
        self.default_marketplace.addItems(['Amazon', 'eBay', 'Etsy', 'Allegro', 'Shopify', 'WeChat'])
        marketplace_layout.addRow("Domyślny marketplace:", self.default_marketplace)
        
        self.auto_resize_marketplace = QCheckBox("Automatycznie dostosuj rozmiar dla marketplace")
        self.auto_resize_marketplace.setChecked(True)
        marketplace_layout.addRow("", self.auto_resize_marketplace)
        
        self.marketplace_naming = QCheckBox("Użyj konwencji nazewnictwa marketplace")
        self.marketplace_naming.setChecked(True)
        marketplace_layout.addRow("", self.marketplace_naming)
        
        marketplace_group.setLayout(marketplace_layout)
        layout.addWidget(marketplace_group)
        
        # Grupa Opcje zaawansowane
        advanced_group = QGroupBox("Opcje zaawansowane")
        advanced_layout = QVBoxLayout()
        
        self.create_subdirs = QCheckBox("Twórz podkatalogi według daty")
        advanced_layout.addWidget(self.create_subdirs)
        
        self.overwrite_existing = QCheckBox("Zastępuj istniejące pliki")
        advanced_layout.addWidget(self.overwrite_existing)
        
        self.export_log = QCheckBox("Twórz log eksportu")
        self.export_log.setChecked(True)
        advanced_layout.addWidget(self.export_log)
        
        self.compress_output = QCheckBox("Kompresuj pliki wyjściowe (ZIP)")
        advanced_layout.addWidget(self.compress_output)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def browse_default_path(self):
        """Wybór domyślnej ścieżki eksportu."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Wybierz domyślny folder eksportu"
        )
        if folder:
            self.default_path.setText(folder)
        
    def load_settings(self):
        """Wczytuje ustawienia z kontrolera."""
        export_settings = self.settings.get_export_settings()
        
        self.default_format.setCurrentText(export_settings.get('default_format', 'PNG'))
        self.default_path.setText(export_settings.get('default_path', ''))
        self.filename_pattern.setText(export_settings.get('filename_pattern', '{original_name}_{size}'))
        
        marketplace_settings = self.settings.get_marketplace_settings()
        self.default_marketplace.setCurrentText(marketplace_settings.get('default', 'Amazon'))
        self.auto_resize_marketplace.setChecked(marketplace_settings.get('auto_resize', True))
        self.marketplace_naming.setChecked(marketplace_settings.get('naming_convention', True))
        
        # Opcje zaawansowane
        self.create_subdirs.setChecked(export_settings.get('create_subdirs', False))
        self.overwrite_existing.setChecked(export_settings.get('overwrite_existing', False))
        self.export_log.setChecked(export_settings.get('export_log', True))
        self.compress_output.setChecked(export_settings.get('compress_output', False))

    def save_settings(self):
        """Zapisuje ustawienia do kontrolera."""
        # Ustawienia eksportu
        self.settings.set_value('export', 'default_format', self.default_format.currentText())
        self.settings.set_value('export', 'default_path', self.default_path.text())
        self.settings.set_value('export', 'filename_pattern', self.filename_pattern.text())
        self.settings.set_value('export', 'create_subdirs', self.create_subdirs.isChecked())
        self.settings.set_value('export', 'overwrite_existing', self.overwrite_existing.isChecked())
        self.settings.set_value('export', 'export_log', self.export_log.isChecked())
        self.settings.set_value('export', 'compress_output', self.compress_output.isChecked())
        
        # Ustawienia marketplace
        self.settings.set_value('marketplace', 'default', self.default_marketplace.currentText())
        self.settings.set_value('marketplace', 'auto_resize', self.auto_resize_marketplace.isChecked())
        self.settings.set_value('marketplace', 'naming_convention', self.marketplace_naming.isChecked())

class CloudSettingsTab(QWidget):
    """Zakładka ustawień usług chmurowych."""
    
    def __init__(self, settings_controller):
        super().__init__()
        self.settings = settings_controller
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Grupa Google Drive
        gdrive_group = QGroupBox("Google Drive")
        gdrive_layout = QVBoxLayout()
        
        self.gdrive_enabled = QCheckBox("Włącz integrację z Google Drive")
        gdrive_layout.addWidget(self.gdrive_enabled)
        
        gdrive_creds_layout = QFormLayout()
        self.gdrive_folder_id = QLineEdit()
        self.gdrive_folder_id.setPlaceholderText("ID folderu Google Drive")
        gdrive_creds_layout.addRow("Folder ID:", self.gdrive_folder_id)
        
        self.gdrive_test = QPushButton("Testuj połączenie")
        self.gdrive_test.clicked.connect(lambda: self.test_connection('gdrive'))
        gdrive_creds_layout.addRow("", self.gdrive_test)
        
        gdrive_layout.addLayout(gdrive_creds_layout)
        gdrive_group.setLayout(gdrive_layout)
        layout.addWidget(gdrive_group)
        
        # Grupa Amazon S3
        s3_group = QGroupBox("Amazon S3")
        s3_layout = QVBoxLayout()
        
        self.s3_enabled = QCheckBox("Włącz integrację z Amazon S3")
        s3_layout.addWidget(self.s3_enabled)
        
        s3_creds_layout = QFormLayout()
        self.s3_access_key = QLineEdit()
        self.s3_access_key.setPlaceholderText("Access Key ID")
        s3_creds_layout.addRow("Access Key:", self.s3_access_key)
        
        self.s3_secret_key = QLineEdit()
        self.s3_secret_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.s3_secret_key.setPlaceholderText("Secret Access Key")
        s3_creds_layout.addRow("Secret Key:", self.s3_secret_key)
        
        self.s3_bucket = QLineEdit()
        self.s3_bucket.setPlaceholderText("Nazwa bucketu")
        s3_creds_layout.addRow("Bucket:", self.s3_bucket)
        
        self.s3_region = QComboBox()
        self.s3_region.addItems(['us-east-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 'ap-southeast-1'])
        s3_creds_layout.addRow("Region:", self.s3_region)
        
        self.s3_test = QPushButton("Testuj połączenie")
        self.s3_test.clicked.connect(lambda: self.test_connection('s3'))
        s3_creds_layout.addRow("", self.s3_test)
        
        s3_layout.addLayout(s3_creds_layout)
        s3_group.setLayout(s3_layout)
        layout.addWidget(s3_group)
        
        # Grupa FTP
        ftp_group = QGroupBox("FTP")
        ftp_layout = QVBoxLayout()
        
        self.ftp_enabled = QCheckBox("Włącz integrację z FTP")
        ftp_layout.addWidget(self.ftp_enabled)
        
        ftp_creds_layout = QFormLayout()
        self.ftp_host = QLineEdit()
        self.ftp_host.setPlaceholderText("ftp.example.com")
        ftp_creds_layout.addRow("Host:", self.ftp_host)
        
        self.ftp_port = QSpinBox()
        self.ftp_port.setRange(1, 65535)
        self.ftp_port.setValue(21)
        ftp_creds_layout.addRow("Port:", self.ftp_port)
        
        self.ftp_user = QLineEdit()
        self.ftp_user.setPlaceholderText("Nazwa użytkownika")
        ftp_creds_layout.addRow("Użytkownik:", self.ftp_user)
        
        self.ftp_password = QLineEdit()
        self.ftp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.ftp_password.setPlaceholderText("Hasło")
        ftp_creds_layout.addRow("Hasło:", self.ftp_password)
        
        self.ftp_path = QLineEdit()
        self.ftp_path.setPlaceholderText("/public_html/images/")
        ftp_creds_layout.addRow("Ścieżka:", self.ftp_path)
        
        self.ftp_test = QPushButton("Testuj połączenie")
        self.ftp_test.clicked.connect(lambda: self.test_connection('ftp'))
        ftp_creds_layout.addRow("", self.ftp_test)
        
        ftp_layout.addLayout(ftp_creds_layout)
        ftp_group.setLayout(ftp_layout)
        layout.addWidget(ftp_group)
        
        # Grupa imgBB
        imgbb_group = QGroupBox("imgBB")
        imgbb_layout = QVBoxLayout()
        
        self.imgbb_enabled = QCheckBox("Włącz integrację z imgBB")
        imgbb_layout.addWidget(self.imgbb_enabled)
        
        imgbb_creds_layout = QFormLayout()
        self.imgbb_api_key = QLineEdit()
        self.imgbb_api_key.setPlaceholderText("API Key z imgBB")
        imgbb_creds_layout.addRow("API Key:", self.imgbb_api_key)
        
        self.imgbb_test = QPushButton("Testuj klucz API")
        self.imgbb_test.clicked.connect(lambda: self.test_connection('imgbb'))
        imgbb_creds_layout.addRow("", self.imgbb_test)
        
        imgbb_layout.addLayout(imgbb_creds_layout)
        imgbb_group.setLayout(imgbb_layout)
        layout.addWidget(imgbb_group)
        
        layout.addStretch()
        self.setLayout(layout)

    def test_connection(self, service):
        """Testuje połączenie z wybraną usługą."""
        QMessageBox.information(
            self,
            "Test połączenia",
            f"Test połączenia z {service} - funkcja będzie dostępna w pełnej wersji."
        )
        
    def load_settings(self):
        """Wczytuje ustawienia z kontrolera."""
        cloud_settings = self.settings.get_section('cloud')
        
        # Google Drive
        self.gdrive_enabled.setChecked(cloud_settings.get('gdrive_enabled', False))
        self.gdrive_folder_id.setText(cloud_settings.get('gdrive_folder_id', ''))
        
        # Amazon S3
        self.s3_enabled.setChecked(cloud_settings.get('s3_enabled', False))
        self.s3_access_key.setText(cloud_settings.get('s3_access_key', ''))
        self.s3_secret_key.setText(cloud_settings.get('s3_secret_key', ''))
        self.s3_bucket.setText(cloud_settings.get('s3_bucket', ''))
        self.s3_region.setCurrentText(cloud_settings.get('s3_region', 'us-east-1'))
        
        # FTP
        self.ftp_enabled.setChecked(cloud_settings.get('ftp_enabled', False))
        self.ftp_host.setText(cloud_settings.get('ftp_host', ''))
        self.ftp_port.setValue(cloud_settings.get('ftp_port', 21))
        self.ftp_user.setText(cloud_settings.get('ftp_user', ''))
        self.ftp_password.setText(cloud_settings.get('ftp_password', ''))
        self.ftp_path.setText(cloud_settings.get('ftp_path', ''))
        
        # imgBB
        self.imgbb_enabled.setChecked(cloud_settings.get('imgbb_enabled', False))
        self.imgbb_api_key.setText(cloud_settings.get('imgbb_api_key', ''))

    def save_settings(self):
        """Zapisuje ustawienia do kontrolera."""
        # Google Drive
        self.settings.set_value('cloud', 'gdrive_enabled', self.gdrive_enabled.isChecked())
        self.settings.set_value('cloud', 'gdrive_folder_id', self.gdrive_folder_id.text())
        
        # Amazon S3
        self.settings.set_value('cloud', 's3_enabled', self.s3_enabled.isChecked())
        self.settings.set_value('cloud', 's3_access_key', self.s3_access_key.text())
        self.settings.set_value('cloud', 's3_secret_key', self.s3_secret_key.text())
        self.settings.set_value('cloud', 's3_bucket', self.s3_bucket.text())
        self.settings.set_value('cloud', 's3_region', self.s3_region.currentText())
        
        # FTP
        self.settings.set_value('cloud', 'ftp_enabled', self.ftp_enabled.isChecked())
        self.settings.set_value('cloud', 'ftp_host', self.ftp_host.text())
        self.settings.set_value('cloud', 'ftp_port', self.ftp_port.value())
        self.settings.set_value('cloud', 'ftp_user', self.ftp_user.text())
        self.settings.set_value('cloud', 'ftp_password', self.ftp_password.text())
        self.settings.set_value('cloud', 'ftp_path', self.ftp_path.text())
        
        # imgBB
        self.settings.set_value('cloud', 'imgbb_enabled', self.imgbb_enabled.isChecked())
        self.settings.set_value('cloud', 'imgbb_api_key', self.imgbb_api_key.text())

class SettingsDialog(QDialog):
    """Główne okno dialogowe ustawień."""
    
    def __init__(self, settings_controller, parent=None):
        super().__init__(parent)
        self.settings = settings_controller
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Ustawienia Retixly")
        self.setMinimumSize(700, 600)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Zakładki ustawień
        self.tabs = QTabWidget()
        
        # Dodaj zakładki
        self.general_tab = GeneralSettingsTab(self.settings)
        self.processing_tab = ProcessingSettingsTab(self.settings)
        self.watermark_tab = WatermarkSettingsTab(self.settings)
        self.export_tab = ExportSettingsTab(self.settings)
        self.cloud_tab = CloudSettingsTab(self.settings)
        
        self.tabs.addTab(self.general_tab, "Ogólne")
        self.tabs.addTab(self.processing_tab, "Przetwarzanie")
        self.tabs.addTab(self.watermark_tab, "Znak wodny")
        self.tabs.addTab(self.export_tab, "Eksport")
        self.tabs.addTab(self.cloud_tab, "Usługi chmurowe")
        
        layout.addWidget(self.tabs)
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        
        # Przyciski po lewej stronie
        self.import_btn = QPushButton("Importuj ustawienia")
        self.import_btn.clicked.connect(self.import_settings)
        
        self.export_btn = QPushButton("Eksportuj ustawienia")
        self.export_btn.clicked.connect(self.export_settings)
        
        self.reset_btn = QPushButton("Przywróć domyślne")
        self.reset_btn.clicked.connect(self.reset_settings)
        
        buttons_layout.addWidget(self.import_btn)
        buttons_layout.addWidget(self.export_btn)
        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addStretch()
        
        # Przyciski po prawej stronie
        self.apply_btn = QPushButton("Zastosuj")
        self.apply_btn.clicked.connect(self.apply_settings)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept_settings)
        self.ok_btn.setDefault(True)
        
        self.cancel_btn = QPushButton("Anuluj")
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.apply_btn)
        buttons_layout.addWidget(self.ok_btn)
        buttons_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
        
        # Stylowanie przycisków
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
                min-width: 80px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
                min-width: 80px;
                border: none;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
                min-width: 80px;
                border: none;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        
    def apply_settings(self):
        """Zastosowuje ustawienia bez zamykania okna."""
        try:
            self.general_tab.save_settings()
            self.processing_tab.save_settings()
            self.watermark_tab.save_settings()
            self.export_tab.save_settings()
            self.cloud_tab.save_settings()
            
            QMessageBox.information(self, "Sukces", "Ustawienia zostały zapisane")
            
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można zapisać ustawień:\n{str(e)}")
            
    def accept_settings(self):
        """Zapisuje ustawienia i zamyka okno."""
        try:
            self.apply_settings()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można zapisać ustawień:\n{str(e)}")
            
    def reset_settings(self):
        """Przywraca ustawienia domyślne."""
        reply = QMessageBox.question(
            self,
            "Przywróć domyślne",
            "Czy na pewno chcesz przywrócić wszystkie ustawienia do wartości domyślnych?\n"
            "Ta operacja nie może zostać cofnięta.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Resetuj wszystkie sekcje
                sections = ['general', 'processing', 'watermark', 'export', 'marketplace', 'cloud']
                for section in sections:
                    self.settings.reset_section(section)
                
                # Przeładuj interfejs
                self.general_tab.load_settings()
                self.processing_tab.load_settings()
                self.watermark_tab.load_settings()
                self.export_tab.load_settings()
                self.cloud_tab.load_settings()
                
                QMessageBox.information(self, "Sukces", "Ustawienia zostały przywrócone do wartości domyślnych")
                
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie można przywrócić ustawień:\n{str(e)}")
                
    def import_settings(self):
        """Importuje ustawienia z pliku."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Importuj ustawienia",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_name:
            try:
                success = self.settings.import_settings(file_name)
                if success:
                    # Przeładuj interfejs
                    self.general_tab.load_settings()
                    self.processing_tab.load_settings()
                    self.watermark_tab.load_settings()
                    self.export_tab.load_settings()
                    self.cloud_tab.load_settings()
                    
                    QMessageBox.information(self, "Sukces", "Ustawienia zostały zaimportowane")
                else:
                    QMessageBox.critical(self, "Błąd", "Nie można zaimportować ustawień")
                    
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Błąd importu ustawień:\n{str(e)}")
                
    def export_settings(self):
        """Eksportuje ustawienia do pliku."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Eksportuj ustawienia",
            "retixly_settings.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_name:
            try:
                self.settings.export_settings(file_name)
                QMessageBox.information(
                    self, 
                    "Sukces", 
                    f"Ustawienia zostały wyeksportowane do:\n{file_name}"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    "Błąd", 
                    f"Nie można wyeksportować ustawień:\n{str(e)}"
                )
                
    def closeEvent(self, event):
        """Obsługa zamknięcia okna."""
        # Możesz tutaj dodać logikę sprawdzania niezapisanych zmian
        event.accept()

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from ..controllers.settings_controller import SettingsController
    
    app = QApplication(sys.argv)
    
    # Przykładowe użycie
    settings_controller = SettingsController()
    dialog = SettingsDialog(settings_controller)
    dialog.show()
    
    sys.exit(app.exec())