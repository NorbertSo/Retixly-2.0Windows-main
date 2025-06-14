from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                           QLabel, QSpinBox, QCheckBox, QGroupBox)
from PyQt6.QtCore import Qt

class MarketplaceSettings(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Wybór marketplace'u
        marketplace_group = QGroupBox(self.tr("Marketplace"))
        marketplace_layout = QVBoxLayout()
        
        self.marketplace_combo = QComboBox()
        self.marketplace_combo.addItems([
            "Amazon", "eBay", "Allegro", "Shopify", "Custom"
        ])
        self.marketplace_combo.currentTextChanged.connect(self.update_requirements)
        marketplace_layout.addWidget(self.marketplace_combo)
        
        marketplace_group.setLayout(marketplace_layout)
        layout.addWidget(marketplace_group)
        
        # Wymiary zdjęć
        size_group = QGroupBox(self.tr("Image Size"))
        size_layout = QVBoxLayout()
        
        # Predefiniowane rozmiary
        self.size_combo = QComboBox()
        self.size_combo.addItems([
            "1000x1000 px", "1500x1500 px", "2000x2000 px", "Custom"
        ])
        self.size_combo.currentTextChanged.connect(self.update_size_inputs)
        size_layout.addWidget(self.size_combo)
        
        # Własne wymiary
        custom_size_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 10000)
        self.width_spin.setValue(1000)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 10000)
        self.height_spin.setValue(1000)
        
        custom_size_layout.addWidget(QLabel(self.tr("Width:")))
        custom_size_layout.addWidget(self.width_spin)
        custom_size_layout.addWidget(QLabel(self.tr("Height:")))
        custom_size_layout.addWidget(self.height_spin)
        size_layout.addLayout(custom_size_layout)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # Format pliku
        format_group = QGroupBox(self.tr("File Format"))
        format_layout = QVBoxLayout()
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "PNG", "WebP"])
        format_layout.addWidget(self.format_combo)
        
        # Jakość JPEG
        quality_layout = QHBoxLayout()
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(85)
        quality_layout.addWidget(QLabel(self.tr("Quality:")))
        quality_layout.addWidget(self.quality_spin)
        format_layout.addLayout(quality_layout)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # Dodatkowe opcje
        options_group = QGroupBox(self.tr("Additional Options"))
        options_layout = QVBoxLayout()
        
        self.optimize_cb = QCheckBox(self.tr("Optimize file size"))
        self.optimize_cb.setChecked(True)
        options_layout.addWidget(self.optimize_cb)
        
        self.metadata_cb = QCheckBox(self.tr("Remove metadata"))
        self.metadata_cb.setChecked(True)
        options_layout.addWidget(self.metadata_cb)
        
        self.naming_cb = QCheckBox(self.tr("Apply marketplace naming convention"))
        self.naming_cb.setChecked(True)
        options_layout.addWidget(self.naming_cb)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def update_requirements(self, marketplace):
        # Aktualizacja wymagań w zależności od wybranego marketplace
        requirements = {
            "Amazon": {"size": "1500x1500", "format": "JPEG"},
            "eBay": {"size": "1600x1600", "format": "JPEG"},
            "Allegro": {"size": "2000x2000", "format": "JPEG"},
            "Shopify": {"size": "2048x2048", "format": "JPEG"}
        }
        
        if marketplace in requirements:
            req = requirements[marketplace]
            self.size_combo.setCurrentText(f"{req['size']} px")
            self.format_combo.setCurrentText(req['format'])
            
    def update_size_inputs(self, size_text):
        is_custom = size_text == "Custom"
        self.width_spin.setEnabled(is_custom)
        self.height_spin.setEnabled(is_custom)
        
        if not is_custom:
            size = size_text.split('x')[0]
            self.width_spin.setValue(int(size))
            self.height_spin.setValue(int(size))
            
    def get_settings(self):
        return {
            'marketplace': self.marketplace_combo.currentText(),
            'size': {
                'width': self.width_spin.value(),
                'height': self.height_spin.value()
            },
            'format': {
                'type': self.format_combo.currentText(),
                'quality': self.quality_spin.value()
            },
            'optimize': self.optimize_cb.isChecked(),
            'remove_metadata': self.metadata_cb.isChecked(),
            'use_naming_convention': self.naming_cb.isChecked()
        }
