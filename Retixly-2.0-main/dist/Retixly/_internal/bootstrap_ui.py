# bootstrap_ui_WORKING.py - KONIEC Z BUGAMI!

import sys
import subprocess
import threading
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                           QTextEdit, QProgressBar, QApplication, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

class WorkingBootstrap(QDialog):
    """Bootstrap który NAPRAWDĘ działa - bez bugów!"""
    
    def __init__(self):
        super().__init__()
        self.installation_complete = False
        self.setup_ui()
        self.setModal(True)
        self.setWindowTitle("Retixly - First Time Setup")
        self.setFixedSize(500, 400)
        
        # Prevent closing until done
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🚀 Installing AI Components")
        title.setFont(QFont("Arial", 16))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #333; padding: 10px;")
        layout.addWidget(title)
        
        # Info
        info = QLabel("Retixly needs AI packages for background removal.\nThis will take 2-3 minutes.")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info)
        
        # Log
        self.log = QTextEdit()
        self.log.setMaximumHeight(150)
        self.log.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(self.log)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        
        # Install button
        self.install_btn = QPushButton("🚀 Start Installation")
        self.install_btn.clicked.connect(self.start_installation)
        self.install_btn.setStyleSheet("background: #007bff; color: white; padding: 15px; font-weight: bold;")
        layout.addWidget(self.install_btn)
        
        # Done button
        self.done_btn = QPushButton("✅ Continue to Retixly")
        self.done_btn.clicked.connect(self.finish_setup)
        self.done_btn.setVisible(False)
        self.done_btn.setStyleSheet("background: #28a745; color: white; padding: 15px; font-weight: bold;")
        layout.addWidget(self.done_btn)
    
    def start_installation(self):
        """Start package installation in background thread."""
        self.install_btn.setVisible(False)
        self.log.append("🚀 Starting installation...")
        self.log.append("📦 Installing AI packages...")
        
        # Start installation thread
        self.install_thread = PackageInstaller()
        self.install_thread.progress_updated.connect(self.update_progress)
        self.install_thread.installation_finished.connect(self.installation_finished)
        self.install_thread.start()
    
    def update_progress(self, progress, message):
        """Update progress bar and log message."""
        self.progress.setValue(progress)
        self.log.append(message)
    
    def installation_finished(self, success):
        """Handle installation completion."""
        if success:
            self.log.append("🎉 Installation finished!")
            
            # Create marker file
            marker = Path.home() / ".retixly_installed"
            marker.write_text("installed")
            self.log.append("📁 Setup completed - marker file created")
            
            self.installation_complete = True
            self.done_btn.setVisible(True)
        else:
            self.log.append("❌ Installation failed - please check log")
            self.install_btn.setVisible(True)  # Retry option
    
    def finish_setup(self):
        """Finish setup and close dialog."""
        self.accept()
    
    def closeEvent(self, event):
        """Prevent closing until installation is complete."""
        if not self.installation_complete:
            event.ignore()
            QMessageBox.warning(self, "Installation in Progress", 
                              "Please wait for installation to complete!")
        else:
            event.accept()

class PackageInstaller(QThread):
    """Thread do instalacji pakietów w tle."""
    
    progress_updated = pyqtSignal(int, str)  # progress, message
    installation_finished = pyqtSignal(bool)  # success
    
    def __init__(self):
        super().__init__()
        # Phase 1 - Critical packages (~250MB)
        self.core_packages = [
            ('PyQt6>=6.6.1', 'Core GUI Library'),
            ('Pillow>=10.1.0', 'Image Processing Library'),
            ('cryptography>=41.0.0', 'Security Library'),
            ('requests>=2.31.0', 'Network Library'),
            ('packaging>=23.0', 'Package Management')
        ]
        
        # Phase 2 - AI and additional packages (~5GB)
        self.ai_packages = [
            ('rembg>=2.0.50', 'AI Background Removal Engine'),
            ('numpy>=1.26.2', 'Numerical Computing Library'),
            ('opencv-python>=4.8.1.78', 'Computer Vision Library'),
            ('onnxruntime>=1.16.0', 'AI Model Runtime'),
            ('boto3>=1.34.7', 'Cloud Integration'),
            ('google-auth>=2.23.4', 'Google Services Authentication'),
            ('google-auth-oauthlib>=1.1.0', 'Google OAuth Library'),
            ('google-api-python-client>=2.108.0', 'Google API Client'),
            ('pillow-heif>=0.12.0', 'HEIC/HEIF Image Support')
        ]
        
        self.total_packages = len(self.core_packages) + len(self.ai_packages)
        self.current_phase = 1
        
    def install_package(self, package, description):
        """Install a single package with error handling."""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package, '--user', '--no-warn-script-location'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return True, f"✅ {description} installed successfully"
            else:
                return False, f"⚠️ {description} installation failed: {result.stderr[-100:]}"

        except Exception as e:
            return False, f"❌ {description} installation error: {str(e)[:100]}"
            
    def run(self):
        """Execute the two-phase installation process."""
        installed = 0
        total_installed = 0
        
        # Phase 1: Core Installation
        self.progress_updated.emit(0, "Starting core installation (Phase 1/2)...")
        for i, (package, description) in enumerate(self.core_packages):
            progress = int((i / len(self.core_packages)) * 50)  # Phase 1 = 0-50%
            self.progress_updated.emit(progress, f"Installing {description}...")
            
            success, message = self.install_package(package, description)
            if success:
                installed += 1
            self.progress_updated.emit(progress, message)
        
        total_installed += installed
        
        # Phase 2: AI Components
        self.current_phase = 2
        self.progress_updated.emit(50, "\nStarting AI components installation (Phase 2/2)...")
        installed = 0
        
        for i, (package, description) in enumerate(self.ai_packages):
            progress = 50 + int((i / len(self.ai_packages)) * 50)  # Phase 2 = 50-100%
            self.progress_updated.emit(progress, f"Installing {description}...")
            
            success, message = self.install_package(package, description)
            if success:
                installed += 1
            self.progress_updated.emit(progress, message)
        
        total_installed += installed
        
        # Installation complete
        success = total_installed > 0
        final_message = f"✨ Installation complete! {total_installed}/{self.total_packages} packages installed successfully."
        self.progress_updated.emit(100, final_message)
        self.installation_finished.emit(success)

def should_show_bootstrap():
    """Check if bootstrap should be shown."""
    marker = Path.home() / ".retixly_installed"
    return not marker.exists()

def check_and_bootstrap():
    """Main bootstrap function - called from main.py"""
    print("🔍 Bootstrap check...")
    
    marker = Path.home() / ".retixly_installed" 
    print(f"📁 Marker file: {marker}")
    print(f"✅ Marker exists: {marker.exists()}")
    
    if not marker.exists():
        print("🚀 First run detected - showing bootstrap dialog")
        
        # Ensure we have QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Show bootstrap dialog - this BLOCKS until complete
        dialog = WorkingBootstrap()
        result = dialog.exec()
        
        print(f"✅ Bootstrap result: {result}")
        return result == QDialog.DialogCode.Accepted
    else:
        print("ℹ️ Bootstrap not needed - marker exists")
        return True

# Test function
if __name__ == "__main__":
    print("Testing bootstrap...")
    app = QApplication(sys.argv)
    
    # Force bootstrap by removing marker
    marker = Path.home() / ".retixly_installed"
    if marker.exists():
        marker.unlink()
        print("Removed existing marker for testing")
    
    result = check_and_bootstrap()
    print(f"Bootstrap test result: {result}")