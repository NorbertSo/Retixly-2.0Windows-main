
import sys
import os
import subprocess
from pathlib import Path

REQUIRED_PACKAGES = [
    'rembg>=2.0.50',
    'numpy>=1.26.2', 
    'opencv-python>=4.8.1.78',
    'boto3>=1.34.7',
    'onnxruntime',
    'google-auth>=2.23.4',
    'google-auth-oauthlib>=1.1.0',
    'google-api-python-client>=2.108.0',
    'pillow-heif>=0.12.0'
]

def check_first_run():
    marker_file = Path.home() / ".retixly_installed"
    return not marker_file.exists()

def create_install_marker():
    marker_file = Path.home() / ".retixly_installed"
    marker_file.write_text("installed")

def install_packages_console():
    print("RETIXLY - Pierwsza instalacja")
    print("=" * 50)
    print("Instalowanie pakietow AI...")
    print()
    
    for i, package in enumerate(REQUIRED_PACKAGES, 1):
        package_name = package.split('>=')[0]
        print(f"[{i}/{len(REQUIRED_PACKAGES)}] Instalowanie {package_name}...")
        
        try:
            cmd = [sys.executable, '-m', 'pip', 'install', package, '--user', '--no-warn-script-location']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"OK: {package_name}")
            else:
                print(f"BLAD: {package_name}")
                
        except Exception as e:
            print(f"BLAD: {package_name} - {str(e)[:50]}")
    
    print()
    print("Instalacja zakonczona!")
    create_install_marker()
    return True

def ensure_packages():
    if check_first_run():
        print("Retixly - Pierwsze uruchomienie")
        print("Instalowanie pakietow AI...")
        
        try:
            install_packages_console()
        except Exception as e:
            print(f"Blad bootstrap: {e}")
        
        print("Uruchamianie aplikacji...")

if __name__ == "__main__":
    ensure_packages()
