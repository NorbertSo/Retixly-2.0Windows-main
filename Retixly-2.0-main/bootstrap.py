import sys
import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Core packages required for basic functionality
CORE_PACKAGES = [
    'PyQt6>=6.6.1',
    'Pillow>=10.1.0',
    'requests>=2.31.0',
    'cryptography>=41.0.0',
    'packaging>=23.0',
    'psutil>=5.9.7'
]

# AI and additional packages for full functionality
AI_PACKAGES = [
    'rembg>=2.0.50',
    'numpy>=1.26.2',
    'opencv-python>=4.8.1.78',
    'onnxruntime>=1.16.0',
    'boto3>=1.34.7',
    'google-auth>=2.23.4',
    'google-auth-oauthlib>=1.1.0',
    'google-api-python-client>=2.108.0',
    'pillow-heif>=0.12.0'
]

def check_first_run() -> bool:
    """Check if this is the first run of the application."""
    marker_file = Path.home() / ".retixly_installed"
    return not marker_file.exists()

def create_install_marker(state: str = "installed"):
    """Create a marker file to indicate installation state."""
    marker_file = Path.home() / ".retixly_installed"
    marker_file.write_text(state)

def check_system_requirements() -> Tuple[bool, str]:
    """Check if the system meets minimum requirements."""
    try:
        import psutil
        
        # Check Windows version
        if not sys.platform.startswith('win'):
            return False, "Retixly requires Windows operating system"
        
        # Check Python version
        if sys.version_info < (3, 9):
            return False, "Retixly requires Python 3.9 or later"
        
        # Check 64-bit
        if not sys.maxsize > 2**32:
            return False, "Retixly requires 64-bit Python"
        
        # Check RAM
        ram_gb = psutil.virtual_memory().total / (1024**3)
        if ram_gb < 8:
            return False, "Retixly requires at least 8GB RAM"
        
        # Check disk space
        program_files = os.environ.get('ProgramFiles')
        if program_files:
            free_space = psutil.disk_usage(program_files).free / (1024**3)
            if free_space < 8:
                return False, "Retixly requires at least 8GB free disk space"
        
        return True, "System requirements met"
        
    except ImportError:
        return True, "Unable to check system requirements"

def install_packages_console(packages: list) -> bool:
    """Install packages using pip in console mode."""
    success_count = 0
    total = len(packages)
    
    for i, package in enumerate(packages, 1):
        package_name = package.split('>=')[0]
        print(f"[{i}/{total}] Installing {package_name}...")
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package, '--user', '--no-warn-script-location'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print(f"✅ {package_name} installed successfully")
                success_count += 1
            else:
                print(f"⚠️ {package_name} installation failed: {result.stderr[-100:]}")
                
        except Exception as e:
            print(f"❌ {package_name} installation error: {str(e)[:100]}")
    
    return success_count > 0

def ensure_core_packages():
    """Ensure critical packages are installed."""
    if check_first_run():
        print("Retixly - First Time Setup")
        print("=" * 50)
        
        # Check system requirements
        sys_ok, sys_msg = check_system_requirements()
        if not sys_ok:
            print(f"❌ System Check Failed: {sys_msg}")
            return False
        
        print("Installing core packages...")
        try:
            success = install_packages_console(CORE_PACKAGES)
            if success:
                create_install_marker("core_installed")
                print("✅ Core installation complete")
                return True
            else:
                print("❌ Core installation failed")
                return False
        except Exception as e:
            print(f"❌ Installation error: {e}")
            return False
    return True

if __name__ == "__main__":
    if not ensure_core_packages():
        sys.exit(1)
