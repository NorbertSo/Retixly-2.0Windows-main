# test_bootstrap.py - Test bootstrap systemu
from pathlib import Path
import sys
import os

def check_bootstrap_status():
    """Debug bootstrap systemu"""
    print("🔍 BOOTSTRAP DEBUG")
    print("=" * 50)
    
    # Sprawdź marker file
    marker_file = Path.home() / ".retixly_installed"
    print(f"📁 Marker file path: {marker_file}")
    print(f"📂 Home directory: {Path.home()}")
    print(f"✅ Marker exists: {marker_file.exists()}")
    
    if marker_file.exists():
        content = marker_file.read_text()
        print(f"📄 Marker content: '{content}'")
        print(f"🕐 Marker created: {marker_file.stat().st_mtime}")
    
    # Sprawdź czy bootstrap powinien się uruchomić
    should_show = not marker_file.exists()
    print(f"🚀 Should show bootstrap: {should_show}")
    
    # Sprawdź krytyczne pakiety
    print("\n📦 CRITICAL PACKAGES CHECK:")
    critical_packages = {
        'PyQt6': 'PyQt6',
        'Pillow': 'PIL',
        'cryptography': 'cryptography', 
        'requests': 'requests'
    }
    
    missing_critical = []
    for package_name, import_name in critical_packages.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name}: OK")
        except ImportError:
            print(f"❌ {package_name}: MISSING")
            missing_critical.append(package_name)
    
    # Sprawdź opcjonalne pakiety AI
    print("\n🤖 AI PACKAGES CHECK:")
    ai_packages = {
        'rembg': 'rembg',
        'numpy': 'numpy',
        'opencv-python': 'cv2',
        'onnxruntime': 'onnxruntime'
    }
    
    missing_ai = []
    for package_name, import_name in ai_packages.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name}: OK")
        except ImportError:
            print(f"⚠️ {package_name}: MISSING")
            missing_ai.append(package_name)
    
    print(f"\n📊 SUMMARY:")
    print(f"Critical missing: {len(missing_critical)}")
    print(f"AI missing: {len(missing_ai)}")
    print(f"Should bootstrap: {should_show}")
    
    return should_show, missing_critical, missing_ai

def force_reset_bootstrap():
    """Wymuś reset bootstrap"""
    marker_file = Path.home() / ".retixly_installed"
    if marker_file.exists():
        marker_file.unlink()
        print(f"🗑️ Deleted marker file: {marker_file}")
    else:
        print(f"ℹ️ Marker file doesn't exist: {marker_file}")

if __name__ == "__main__":
    print("RETIXLY BOOTSTRAP TESTER")
    print("=" * 50)
    
    # Test current status
    should_show, missing_critical, missing_ai = check_bootstrap_status()
    
    print(f"\n🎯 DECISION:")
    if missing_critical:
        print("❌ CRITICAL ERROR: Missing critical packages")
        print("   → Application will show error dialog and exit")
    elif should_show:
        print("✅ BOOTSTRAP SHOULD SHOW")
        print("   → First run dialog should appear")
    else:
        print("ℹ️ BOOTSTRAP WILL BE SKIPPED")
        print("   → Marker file exists, going directly to main app")
        
        choice = input("\n🔄 Reset bootstrap? (y/n): ").lower()
        if choice == 'y':
            force_reset_bootstrap()
            print("🚀 Now run the application again!")