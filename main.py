import sys
import importlib
import logging

logger = logging.getLogger(__name__)

def check_dependencies_lazy():
    """
    Sprawdza tylko KRYTYCZNE pakiety na starcie.
    Opcjonalne pakiety sprawdzane później.
    """
    critical_packages = {
        'PyQt6': 'PyQt6',
        'Pillow': 'PIL',
        'cryptography': 'cryptography',
        'requests': 'requests'
    }
    
    missing_critical = []
    
    for package_name, import_name in critical_packages.items():
        try:
            importlib.import_module(import_name)
            logger.info(f"✅ Critical package {package_name} loaded")
        except ImportError as e:
            logger.error(f"❌ Critical package {package_name} missing: {e}")
            missing_critical.append(package_name)
    
    return missing_critical

def check_optional_dependencies():
    """
    Sprawdza opcjonalne pakiety - wywoływane dopiero gdy potrzebne.
    """
    optional_packages = {
        'rembg': 'rembg',
        'numpy': 'numpy', 
        'opencv-python': 'cv2',
        'boto3': 'boto3',
        'onnxruntime': 'onnxruntime'
    }
    
    missing_optional = []
    available_optional = []
    
    for package_name, import_name in optional_packages.items():
        try:
            importlib.import_module(import_name)
            available_optional.append(package_name)
            logger.info(f"✅ Optional package {package_name} available")
        except ImportError:
            missing_optional.append(package_name)
            logger.warning(f"⚠️ Optional package {package_name} missing")
    
    return missing_optional, available_optional

def main():
    """Główna funkcja aplikacji z lazy loading."""
    try:
        load_environment_config()
        
        missing_critical = check_dependencies_lazy()
        
        if missing_critical:
            logger.warning(f"Missing critical packages: {missing_critical}")
            ensure_packages()
            
            missing_critical = check_dependencies_lazy()
            if missing_critical:
                print(f"❌ CRITICAL: Still missing: {missing_critical}")
                print("Please install manually: pip install " + " ".join(missing_critical))
                sys.exit(1)
        
        qt = import_qt()
        
        if not sys.argv:
            sys.argv.append('')
        
        app = qt['QApplication'](sys.argv)
        
        setup_environment()
        
        logger.info(f"🚀 Starting Retixly {APP_VERSION}")
        retixly_app = RetixlyApp()
        
        retixly_app.check_optional_packages_async()
        
        exit_code = retixly_app.run()
        
        cleanup_temp_files()
        
        logger.info("Application closed - exit code: %s", exit_code)
        sys.exit(exit_code)
        
    except ImportError as e:
        print(f"CRITICAL IMPORT ERROR: {e}")
        sys.exit(1)
        
    except Exception as e:
        logger.critical(f"Critical application error: {e}")
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)

class RetixlyApp:
    # ...existing code...

    def check_optional_packages_async(self):
        """
        Sprawdza opcjonalne pakiety w tle - nie blokuje interfejsu.
        """
        def check_packages():
            missing_optional, available_optional = check_optional_dependencies()
            
            if missing_optional:
                logger.info(f"⚠️ Optional packages missing: {missing_optional}")
                logger.info("Some features may be limited")
                
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'statusBar'):
                    self.main_window.statusBar().showMessage(
                        f"Note: {len(missing_optional)} optional packages missing - some features limited", 
                        10000
                    )
            else:
                logger.info("✅ All optional packages available")
        
        if hasattr(self, 'qt') and 'QTimer' in self.qt:
            self.qt['QTimer'].singleShot(3000, check_packages)
        else:
            check_packages()
    
    def install_missing_package_on_demand(self, package_name):
        """
        Instaluje pakiet na żądanie - gdy użytkownik próbuje użyć funkcji.
        """
        try:
            msg = self.qt['QMessageBox'](self.main_window)
            msg.setWindowTitle("Feature Requires Additional Package")
            msg.setText(f"This feature requires '{package_name}' package.")
            msg.setInformativeText(f"Would you like to install {package_name} now?")
            msg.setStandardButtons(
                self.qt['QMessageBox'].StandardButton.Yes | 
                self.qt['QMessageBox'].StandardButton.No
            )
            
            if msg.exec() == self.qt['QMessageBox'].StandardButton.Yes:
                self.show_installation_progress(package_name)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error in on-demand installation: {e}")
            return False
    
    def show_installation_progress(self, package_name):
        """
        Pokazuje progress podczas instalacji pakietu.
        """
        try:
            from PyQt6.QtWidgets import QProgressDialog
            progress = QProgressDialog(f"Installing {package_name}...", "Cancel", 0, 0, self.main_window)
            progress.setWindowModality(self.qt['Qt'].WindowModality.WindowModal)
            progress.show()
            
            import subprocess
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package_name
            ], capture_output=True, text=True)
            
            progress.close()
            
            if result.returncode == 0:
                msg = self.qt['QMessageBox'](self.main_window)
                msg.setWindowTitle("Installation Complete")
                msg.setText(f"{package_name} has been installed successfully!")
                msg.exec()
                return True
            else:
                msg = self.qt['QMessageBox'](self.main_window)
                msg.setIcon(self.qt['QMessageBox'].Icon.Warning)
                msg.setWindowTitle("Installation Failed")
                msg.setText(f"Failed to install {package_name}")
                msg.setDetailedText(result.stderr)
                msg.exec()
                return False
                
        except Exception as e:
            logger.error(f"Installation progress error: {e}")
            return False