# simple_bootstrap.py - PROSTY bootstrap bez problemów
import sys
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar, QTextEdit, QMessageBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class SimpleInstaller(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.packages = ['rembg', 'numpy', 'opencv-python', 'onnxruntime', 'boto3']
    
    def run(self):
        success = True
        for package in self.packages:
            self.progress.emit(f"Installing {package}...")
            try:
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', package, '--user'
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    self.progress.emit(f"✅ {package} OK")
                else:
                    self.progress.emit(f"❌ {package} FAILED")
                    success = False
            except:
                self.progress.emit(f"❌ {package} ERROR")
                success = False
        
        self.finished.emit(success)

class SimpleBootstrap(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Retixly Setup")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🚀 Install AI Components")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin: 20px;")
        layout.addWidget(title)
        
        # Info
        info = QLabel("Retixly needs AI packages for background removal.\nThis will take 2-3 minutes.")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("margin: 10px;")
        layout.addWidget(info)
        
        # Log
        self.log = QTextEdit()
        self.log.setMaximumHeight(200)
        layout.addWidget(self.log)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        self.install_btn = QPushButton("Install Now")
        self.install_btn.clicked.connect(self.install)
        self.install_btn.setStyleSheet("background: #007bff; color: white; padding: 10px; font-weight: bold;")
        layout.addWidget(self.install_btn)
        
        self.skip_btn = QPushButton("Skip (Limited Features)")
        self.skip_btn.clicked.connect(self.skip)
        self.skip_btn.setStyleSheet("background: #6c757d; color: white; padding: 10px;")
        layout.addWidget(self.skip_btn)
        
        self.done_btn = QPushButton("Continue to Retixly")
        self.done_btn.clicked.connect(self.accept)
        self.done_btn.setVisible(False)
        self.done_btn.setStyleSheet("background: #28a745; color: white; padding: 15px; font-weight: bold;")
        layout.addWidget(self.done_btn)
        
        self.installer = None
    
    def install(self):
        self.install_btn.setVisible(False)
        self.skip_btn.setVisible(False)
        self.progress_bar.setVisible(True)
        
        self.log.append("🚀 Starting installation...")
        
        self.installer = SimpleInstaller()
        self.installer.progress.connect(self.log.append)
        self.installer.finished.connect(self.installation_done)
        self.installer.start()
    
    def installation_done(self, success):
        self.progress_bar.setVisible(False)
        
        if success:
            self.log.append("🎉 Installation complete!")
            # Create marker
            marker = Path.home() / ".retixly_installed"
            marker.write_text("installed")
        else:
            self.log.append("⚠️ Some packages failed - app will work with limited features")
            marker = Path.home() / ".retixly_installed"
            marker.write_text("partial")
        
        self.done_btn.setVisible(True)
    
    def skip(self):
        reply = QMessageBox.question(self, "Skip Setup?", 
                                   "Skip AI installation? Features will be limited.")
        if reply == QMessageBox.StandardButton.Yes:
            marker = Path.home() / ".retixly_installed"
            marker.write_text("skipped")
            self.reject()

def should_show_bootstrap():
    """Sprawdza czy pokazać bootstrap"""
    marker = Path.home() / ".retixly_installed"
    return not marker.exists()

def show_simple_bootstrap():
    """Pokazuje prosty bootstrap"""
    dialog = SimpleBootstrap()
    return dialog.exec() == QDialog.DialogCode.Accepted

# GŁÓWNA FUNKCJA DO UŻYCIA W MAIN.PY
def check_and_bootstrap():
    """Główna funkcja bootstrap - PROSTA!"""
    print("🔍 Checking if bootstrap needed...")
    
    if should_show_bootstrap():
        print("🚀 Showing bootstrap...")
        return show_simple_bootstrap()
    else:
        print("ℹ️ Bootstrap not needed")
        return True