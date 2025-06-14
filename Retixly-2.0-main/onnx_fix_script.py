"""
Prosty Fix Script dla ONNX Runtime na Windows
"""

import subprocess
import sys
import os
import platform
import ctypes
from pathlib import Path

def run_command(cmd):
    """Uruchamia komendę i wyświetla wynik"""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def test_import(module_name, package_name=None):
    """Testuje import modułu"""
    try:
        __import__(module_name)
        print(f"✅ {package_name or module_name} - OK")
        return True
    except ImportError as e:
        print(f"❌ {package_name or module_name} - Failed: {e}")
        return False

def check_vcredist():
    """Sprawdza czy Visual C++ Redistributable jest zainstalowany"""
    try:
        dll_path = r"C:\Windows\System32\vcruntime140.dll"
        return os.path.exists(dll_path)
    except:
        return False

def get_system_info():
    """Zbiera informacje o systemie"""
    return {
        "system": platform.system(),
        "architecture": platform.architecture(),
        "python_version": sys.version,
        "vcredist": check_vcredist()
    }

def main():
    print("🔧 PROSTY FIX dla ONNX Runtime na Windows")
    print("=" * 50)
    
    # Sprawdź system
    sys_info = get_system_info()
    if sys_info["system"] != "Windows":
        print("❌ Ten skrypt działa tylko na Windows!")
        return
    
    print("\nInformacje systemowe:")
    for key, value in sys_info.items():
        print(f"{key}: {value}")
    
    if not sys_info["vcredist"]:
        print("\n⚠️ UWAGA: Nie wykryto Visual C++ Redistributable!")
        print("Zainstaluj go przed kontynuowaniem:")
        print("https://docs.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist")
    
    print("\n1. Sprawdzanie obecnej instalacji...")
    onnx_ok = test_import("onnxruntime", "ONNX Runtime")
    rembg_ok = test_import("rembg", "REMBG")
    
    if onnx_ok and rembg_ok:
        print("✅ Wszystko działa! Nie potrzebujesz naprawy.")
        return
    
    print("\n2. Usuwanie problematycznych pakietów...")
    packages_to_remove = ["onnxruntime", "onnxruntime-gpu", "rembg"]
    for package in packages_to_remove:
        run_command([sys.executable, "-m", "pip", "uninstall", package, "-y"])
    
    print("\n3. Instalowanie kompatybilnych wersji...")
    versions_to_try = [
        ("onnxruntime==1.16.3", "rembg==2.0.50"),
        ("onnxruntime==1.15.1", "rembg==2.0.38"),
        ("onnxruntime==1.13.1", "rembg==2.0.30"),
        ("onnxruntime", "rembg")  # Fallback to latest versions
    ]
    
    success = False
    for onnx_ver, rembg_ver in versions_to_try:
        print(f"\nPróbuję: {onnx_ver} + {rembg_ver}")
        try:
            if run_command([sys.executable, "-m", "pip", "install", "--no-cache-dir", onnx_ver]) and \
               run_command([sys.executable, "-m", "pip", "install", "--no-cache-dir", rembg_ver]):
                if test_import("onnxruntime") and test_import("rembg"):
                    success = True
                    print("✅ Sukces! Ta kombinacja działa.")
                    break
        except Exception as e:
            print(f"❌ Błąd instalacji: {e}")
            continue
    
    if success:
        print("\n🎉 NAPRAWIONE! Teraz uruchom aplikację ponownie.")
    else:
        print("\n❌ Automatyczna naprawa nie powiodła się.")
        if not sys_info["vcredist"]:
            print("\n🔴 KONIECZNE DZIAŁANIA:")
            print("1. Zainstaluj Visual C++ Redistributable")
            print("2. Zrestartuj komputer")
            print("3. Uruchom ten skrypt ponownie")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
    