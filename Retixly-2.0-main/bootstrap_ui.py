# bootstrap_ui.py - Ładny interfejs bootstrap

import sys
import os
import subprocess
import threading
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QProgressBar, QTextEdit, QApplication,
                           QFrame, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QFont, QPalette, QColor

class PackageInstaller(QThread):
    """Thread do instalacji pakietów w tle."""
    
    progress_updated = pyqtSignal(int, str)  # progress, message
    installation_finished = pyqtSignal(bool)  # success
    
    def __init__(self):
        super().__init__()
        self.packages = [
            ('rembg>=2.0.50', 'AI Background Removal Engine'),
            ('numpy>=1.26.2', 'Numerical Computing Library'),
            ('opencv-python>=4.8.1.78', 'Computer Vision Library'),
            ('boto3>=1.34.7', 'AWS Cloud Integration'),
            ('onnxruntime', 'AI Model Runtime Engine'),
            ('google-auth>=2.23.4', 'Google Services Authentication'),
            ('google-auth-oauthlib>=1.1.0', 'Google OAuth Library'),
            ('google-api-python-client>=2.108.0', 'Google API Client'),
            ('pillow-heif>=0.12.0', 'HEIC/HEIF Image Support')
        ]
        self.total_packages = len(self.packages)
    
    def run(self):
        """Instaluje pakiety jeden po drugim."""
        installed = 0
        
        for i, (package, description) in enumerate(self.packages):
            package_name = package.split('>=')[0]
            
            # Aktualizuj progress
            progress = int((i / self.total_packages) * 100)
            self.progress_updated.emit(progress, f"Installing {description}...")
            
            try:
                # Instaluj pakiet
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', package, '--user', '--no-warn-script-location'
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    installed += 1
                    self.progress_updated.emit(
                        int(((i + 1) / self.total_packages) * 100), 
                        f"✅ {description} installed successfully"
                    )
                else:
                    self.progress_updated.emit(
                        int(((i + 1) / self.total_packages) * 100), 
                        f"⚠️ {description} installation failed"
                    )
                    
            except Exception as e:
                self.progress_updated.emit(
                    int(((i + 1) / self.total_packages) * 100), 
                    f"❌ {description} installation error"
                )
        
        # Zakończ
        self.progress_updated.emit(100, f"Installation complete! {installed}/{self.total_packages} packages installed.")
        self.installation_finished.emit(installed > 0)

class BootstrapDialog(QDialog):
    """Ładny dialog bootstrap do pierwszego uruchomienia."""
    
    def __init__(self):
        super().__init__()
        self.installer_thread = None
        self.init_ui()
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint)
        self.setModal(True)
    
    def init_ui(self):
        """Inicjalizuje interfejs użytkownika."""
        self.setWindowTitle("Retixly - First Time Setup")
        self.setFixedSize(600, 500)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
            }
            QLabel {
                color: #343a40;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                text-align: center;
                font-weight: 600;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 6px;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Logo/Header
        header_layout = QVBoxLayout()
        
        # Tytuł
        title_label = QLabel("🚀 Welcome to Retixly!")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #007bff; margin: 10px;")
        
        # Podtytuł
        subtitle_label = QLabel("AI-Powered Background Removal Tool")
        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #6c757d; margin-bottom: 20px;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #dee2e6;")
        
        # Info text
        info_label = QLabel("""
        <b>First Time Setup Required</b><br><br>
        Retixly needs to install AI components to provide the best background removal experience:
        <br><br>
        • <b>AI Background Removal Engine</b> - Core AI models<br>
        • <b>Computer Vision Library</b> - Advanced image processing<br>
        • <b>Cloud Integration</b> - Optional cloud features<br>
        • <b>Additional Format Support</b> - HEIC, RAW files<br>
        <br>
        <i>This is a one-time setup and may take 2-5 minutes depending on your internet connection.</i>
        """)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #dee2e6;")
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Skip button
        self.skip_button = QPushButton("Skip Setup")
        self.skip_button.clicked.connect(self.skip_setup)
        self.skip_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        
        # Install button
        self.install_button = QPushButton("Install AI Components")
        self.install_button.clicked.connect(self.start_installation)
        
        button_layout.addWidget(self.skip_button)
        button_layout.addStretch()
        button_layout.addWidget(self.install_button)
        
        # Progress area (initially hidden)
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_frame)
        
        self.progress_label = QLabel("Preparing installation...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(QLabel("Installation Log:"))
        progress_layout.addWidget(self.log_text)
        
        # Close button (initially hidden)
        self.close_button = QPushButton("Continue to Retixly")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setVisible(False)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 16px;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        
        # Add all to main layout
        layout.addLayout(header_layout)
        layout.addWidget(separator)
        layout.addWidget(info_label)
        layout.addLayout(button_layout)
        layout.addWidget(self.progress_frame)
        layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def start_installation(self):
        """Rozpoczyna instalację pakietów."""
        # Ukryj przyciski, pokaż progress
        self.install_button.setVisible(False)
        self.skip_button.setVisible(False)
        self.progress_frame.setVisible(True)
        
        # Rozpocznij instalację w osobnym wątku
        self.installer_thread = PackageInstaller()
        self.installer_thread.progress_updated.connect(self.update_progress)
        self.installer_thread.installation_finished.connect(self.installation_completed)
        self.installer_thread.start()
    
    def update_progress(self, progress, message):
        """Aktualizuje progress bar i log."""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def installation_completed(self, success):
        """Obsługuje zakończenie instalacji."""
        if success:
            self.progress_label.setText("🎉 Installation completed successfully!")
            self.close_button.setText("Continue to Retixly")
            # Utwórz marker pliku
            marker_file = Path.home() / ".retixly_installed"
            marker_file.write_text("installed")
        else:
            self.progress_label.setText("⚠️ Installation completed with some issues")
            self.close_button.setText("Continue Anyway")
        
        self.close_button.setVisible(True)
    
    def skip_setup(self):
        """Pomija setup - aplikacja będzie działać bez AI pakietów."""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self, 
            "Skip Setup?",
            "Are you sure you want to skip the AI components installation?\n\n"
            "You can install them later from the application menu, but some features will be limited.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Utwórz marker pliku aby nie pokazywać tego dialogu ponownie
            marker_file = Path.home() / ".retixly_installed"
            marker_file.write_text("skipped")
            self.reject()

def check_first_run():
    """Sprawdza czy to pierwsze uruchomienie."""
    marker_file = Path.home() / ".retixly_installed"
    return not marker_file.exists()

def show_bootstrap_dialog():
    """Pokazuje dialog bootstrap jeśli potrzebny."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    dialog = BootstrapDialog()
    result = dialog.exec()
    
    return result == QDialog.DialogCode.Accepted

def check_dependencies_with_ui():
    """Sprawdza zależności i pokazuje UI bootstrap jeśli potrzebny."""
    import importlib
    
    # Pakiety krytyczne
    critical_packages = {
        'PyQt6': 'PyQt6',
        'Pillow': 'PIL',
        'cryptography': 'cryptography', 
        'requests': 'requests'
    }
    
    missing_critical = []
    
    # Sprawdź tylko krytyczne pakiety
    for package_name, import_name in critical_packages.items():
        try:
            importlib.import_module(import_name)
            print(f"✅ {package_name} available")
        except ImportError:
            missing_critical.append(package_name)
            print(f"❌ Critical: {package_name} missing")
    
    # Jeśli pierwsze uruchomienie - pokaż ładny dialog
    if check_first_run():
        print("🚀 First run detected - showing bootstrap dialog")
        success = show_bootstrap_dialog()
        if not success:
            print("User skipped bootstrap setup")
    
    return missing_critical, []  # Opcjonalne pakiety obsługuje bootstrap UI
    
    
    
    return missing_critical, []  # Opcjonalne pakiety obsługuje bootstrap UI
     