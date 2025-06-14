#!/usr/bin/env python3
"""
Skrypt do kompilacji plików tłumaczeń .ts do .qm
Uruchom ten skrypt przed uruchomieniem aplikacji, aby zaktualizować tłumaczenia.
"""

import os
import subprocess
import sys
from pathlib import Path

def find_lrelease():
    """Znajdź program lrelease w systemie."""
    possible_paths = [
        'lrelease',
        'lrelease-qt6',
        '/usr/bin/lrelease',
        '/usr/local/bin/lrelease',
        '/opt/homebrew/bin/lrelease',
        'C:\\Qt\\6.5.0\\msvc2019_64\\bin\\lrelease.exe',
        'C:\\Qt\\Tools\\QtCreator\\bin\\lrelease.exe'
    ]
    
    for path in possible_paths:
        try:
            result = subprocess.run([path, '-version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                print(f"✅ Znaleziono lrelease: {path}")
                return path
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            continue
    
    return None

def compile_translations():
    """Kompiluje wszystkie pliki .ts do .qm"""
    # Znajdź katalog translations
    current_dir = Path(__file__).parent
    translations_dir = current_dir / "translations"
    
    if not translations_dir.exists():
        print(f"❌ Katalog tłumaczeń nie istnieje: {translations_dir}")
        return False
    
    # Znajdź lrelease
    lrelease_path = find_lrelease()
    if not lrelease_path:
        print("❌ Nie można znaleźć programu lrelease.")
        print("Zainstaluj Qt Creator lub Qt tools, aby uzyskać dostęp do lrelease.")
        return False
    
    # Znajdź wszystkie pliki .ts
    ts_files = list(translations_dir.glob("*.ts"))
    if not ts_files:
        print(f"❌ Nie znaleziono plików .ts w {translations_dir}")
        return False
    
    print(f"🔄 Kompilowanie {len(ts_files)} plików tłumaczeń...")
    
    success_count = 0
    for ts_file in ts_files:
        qm_file = ts_file.with_suffix('.qm')
        
        try:
            print(f"   Kompilowanie: {ts_file.name} -> {qm_file.name}")
            result = subprocess.run([lrelease_path, str(ts_file), '-qm', str(qm_file)], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=30)
            
            if result.returncode == 0:
                print(f"   ✅ Sukces: {qm_file.name}")
                success_count += 1
            else:
                print(f"   ❌ Błąd kompilacji {ts_file.name}:")
                print(f"      {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            print(f"   ❌ Timeout podczas kompilacji {ts_file.name}")
        except Exception as e:
            print(f"   ❌ Wyjątek podczas kompilacji {ts_file.name}: {e}")
    
    print(f"\n🎉 Zakończono kompilację: {success_count}/{len(ts_files)} plików")
    return success_count == len(ts_files)

def update_translations():
    """Aktualizuje pliki .ts na podstawie kodu źródłowego (opcjonalne)."""
    # Znajdź lupdate
    lupdate_paths = [
        'lupdate',
        'lupdate-qt6', 
        '/usr/bin/lupdate',
        '/usr/local/bin/lupdate',
        '/opt/homebrew/bin/lupdate'
    ]
    
    lupdate_path = None
    for path in lupdate_paths:
        try:
            result = subprocess.run([path, '-version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                lupdate_path = path
                break
        except:
            continue
    
    if not lupdate_path:
        print("⚠️  Nie znaleziono lupdate - pomijam aktualizację plików .ts")
        return True
    
    print("🔄 Aktualizowanie plików .ts...")
    
    # Znajdź pliki źródłowe
    current_dir = Path(__file__).parent
    source_dirs = ['src']
    
    # Przygotuj listę plików źródłowych
    source_files = []
    for src_dir in source_dirs:
        src_path = current_dir / src_dir
        if src_path.exists():
            source_files.extend(src_path.rglob("*.py"))
    
    if not source_files:
        print("❌ Nie znaleziono plików źródłowych")
        return False
    
    # Aktualizuj każdy plik .ts
    translations_dir = current_dir / "translations"
    ts_files = list(translations_dir.glob("*.ts"))
    
    for ts_file in ts_files:
        try:
            cmd = [lupdate_path] + [str(f) for f in source_files] + ['-ts', str(ts_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"   ✅ Zaktualizowano: {ts_file.name}")
            else:
                print(f"   ❌ Błąd aktualizacji {ts_file.name}: {result.stderr.strip()}")
                
        except Exception as e:
            print(f"   ❌ Wyjątek podczas aktualizacji {ts_file.name}: {e}")
    
    return True

def main():
    """Główna funkcja skryptu."""
    print("🌍 Retixly Translation Compiler")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--update':
        print("🔄 Tryb aktualizacji - najpierw aktualizujemy pliki .ts")
        if not update_translations():
            print("❌ Błąd podczas aktualizacji plików .ts")
            return 1
        print()
    
    # Kompiluj tłumaczenia
    if compile_translations():
        print("✅ Wszystkie tłumaczenia skompilowane pomyślnie!")
        print("🚀 Możesz teraz uruchomić aplikację.")
        return 0
    else:
        print("❌ Wystąpiły błędy podczas kompilacji.")
        return 1

if __name__ == "__main__":
    sys.exit(main())