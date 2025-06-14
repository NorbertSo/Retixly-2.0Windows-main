#!/usr/bin/env python3
"""
Test integracji CarveKit Engine z trzema sekcjami Retixly
UMIEŚĆ W GŁÓWNYM KATALOGU PROJEKTU (tam gdzie main.py)
"""

import os
import sys
from pathlib import Path
from PIL import Image
import tempfile

# Dodaj główny katalog projektu do PYTHONPATH
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

# Sprawdź czy jesteśmy w odpowiednim katalogu
if not (current_dir / "main.py").exists():
    print("❌ Uruchom test z głównego katalogu projektu (tam gdzie jest main.py)")
    print(f"Obecny katalog: {current_dir}")
    print("Oczekiwane pliki: main.py, src/")
    sys.exit(1)

print(f"📁 Katalog projektu: {current_dir}")
print(f"📁 Katalog src: {current_dir / 'src'}")

# Sprawdź czy istnieje katalog src
if not (current_dir / "src").exists():
    print("❌ Brak katalogu src/ w projekcie!")
    sys.exit(1)

# Sprawdź czy istnieje carvekit_engine.py
carvekit_path = current_dir / "src" / "core" / "carvekit_engine.py"
if not carvekit_path.exists():
    print(f"❌ Brak pliku: {carvekit_path}")
    print("Upewnij się, że carvekit_engine.py jest w src/core/")
    sys.exit(1)

print("✅ Struktura projektu wygląda poprawnie")

def test_single_photo_integration():
    """Test integracji z Single Photo."""
    print("\n🧪 Test Single Photo Integration")
    print("-" * 40)
    
    try:
        # Import bezpośrednio z pełnej ścieżki
        from src.core.carvekit_engine import create_optimized_engine
        
        # Utwórz engine
        engine = create_optimized_engine(max_workers=2)
        print("✅ Engine utworzony")
        
        # Test image
        test_image = Image.new('RGB', (400, 400), (255, 255, 255))
        
        # Test settings jak w single_photo.py
        settings = {
            'bg_mode': 'remove',
            'force_binary_alpha': True,
            'edge_refinement': True,
            'preserve_holes': True
        }
        
        # Callback jak w ImageProcessingThread
        def progress_callback(percent, stage=None):
            print(f"  Progress: {percent}% - {stage or 'Processing...'}")
        
        # Test process_single
        result = engine.process_single(
            test_image,
            settings=settings,
            progress_callback=progress_callback
        )
        
        print(f"✅ Single Photo: {result.mode}, rozmiar: {result.size}")
        return True
        
    except Exception as e:
        print(f"❌ Single Photo test failed: {e}")
        import traceback
        print("🔍 Szczegóły błędu:")
        traceback.print_exc()
        return False

def test_batch_processing_integration():
    """Test integracji z Batch Processing."""
    print("\n🧪 Test Batch Processing Integration")
    print("-" * 40)
    
    try:
        from src.core.carvekit_engine import create_optimized_engine
        
        # Utwórz engine jak w BatchProcessor
        engine = create_optimized_engine(max_workers=4)
        print("✅ Batch engine utworzony")
        
        # Test settings jak w batch_processing.py
        engine_settings = {
            'remove_background': True,
            'new_background': None,
            'adjustments': {},
            'watermark': {},
            'marketplace': None
        }
        
        # Test image
        test_image = Image.new('RGB', (300, 300), (128, 128, 128))
        
        # Test process_single (użyte w BatchProcessor)
        result = engine.process_single(test_image, engine_settings)
        
        print(f"✅ Batch Processing: {result.mode}, rozmiar: {result.size}")
        return True
        
    except Exception as e:
        print(f"❌ Batch Processing test failed: {e}")
        import traceback
        print("🔍 Szczegóły błędu:")
        traceback.print_exc()
        return False

def test_csv_xml_integration():
    """Test integracji z CSV/XML Import."""
    print("\n🧪 Test CSV/XML Integration")
    print("-" * 40)
    
    try:
        from src.core.carvekit_engine import create_optimized_engine
        
        # Utwórz engine jak w CsvXmlProcessingThread
        engine = create_optimized_engine(max_workers=4)
        print("✅ CSV/XML engine utworzony")
        
        # Test settings jak w csv_xml_view.py
        settings = {
            'bg_mode': 'remove',
            'bg_color': '#FFFFFF',
            'bg_image': None,
            'preserve_holes': True,
            'edge_refinement': True,
            'force_binary_alpha': True
        }
        
        # Test image
        test_image = Image.new('RGB', (250, 250), (200, 150, 100))
        
        # Test process_single
        result = engine.process_single(test_image, settings)
        
        print(f"✅ CSV/XML: {result.mode}, rozmiar: {result.size}")
        return True
        
    except Exception as e:
        print(f"❌ CSV/XML test failed: {e}")
        import traceback
        print("🔍 Szczegóły błędu:")
        traceback.print_exc()
        return False

def test_background_changes():
    """Test zmiany tła."""
    print("\n🧪 Test Background Changes")
    print("-" * 40)
    
    try:
        from src.core.carvekit_engine import create_optimized_engine
        
        engine = create_optimized_engine()
        test_image = Image.new('RGB', (200, 200), (100, 100, 100))
        
        # Test 1: Usuń tło
        settings1 = {'bg_mode': 'remove'}
        result1 = engine.process_single(test_image, settings1)
        print(f"✅ Remove background: {result1.mode}")
        
        # Test 2: Kolor tła
        settings2 = {'bg_mode': 'color', 'bg_color': '#FF0000'}
        result2 = engine.process_single(test_image, settings2)
        print(f"✅ Color background: {result2.mode}")
        
        # Test 3: Obraz tła (bez pliku - powinna być graceful degradation)
        settings3 = {'bg_mode': 'image', 'bg_image': 'nonexistent.jpg'}
        result3 = engine.process_single(test_image, settings3)
        print(f"✅ Image background (fallback): {result3.mode}")
        
        return True
        
    except Exception as e:
        print(f"❌ Background changes test failed: {e}")
        import traceback
        print("🔍 Szczegóły błędu:")
        traceback.print_exc()
        return False

def test_carvekit_availability():
    """Test dostępności CarveKit i fallbacków."""
    print("\n🧪 Test CarveKit Availability")
    print("-" * 40)
    
    # Test CarveKit
    try:
        from carvekit.api.high import HiInterface
        print("✅ CarveKit jest dostępny")
        carvekit_available = True
    except ImportError as e:
        print(f"⚠️ CarveKit niedostępny: {e}")
        print("💡 Zainstaluj: pip install carvekit-colab")
        carvekit_available = False
    
    # Test U2NET fallback
    try:
        from rembg import remove
        print("✅ U2NET (rembg) jest dostępny")
        rembg_available = True
    except ImportError as e:
        print(f"⚠️ U2NET niedostępny: {e}")
        print("💡 Zainstaluj: pip install rembg")
        rembg_available = False
    
    # Test OpenCV
    try:
        import cv2
        print("✅ OpenCV jest dostępny")
        opencv_available = True
    except ImportError as e:
        print(f"⚠️ OpenCV niedostępny: {e}")
        print("💡 Zainstaluj: pip install opencv-python")
        opencv_available = False
    
    if not (carvekit_available or rembg_available):
        print("❌ Brak wszystkich silników do usuwania tła!")
        return False
    
    if not opencv_available:
        print("⚠️ Brak OpenCV - emergency fallback może nie działać")
    
    return True

def main():
    """Główny test integracji."""
    print("🚀 CarveKit Engine Integration Tests")
    print("=" * 50)
    
    # Sprawdź dostępność pakietów
    if not test_carvekit_availability():
        print("\n❌ Krytyczne błędy dostępności pakietów - test przerwany")
        return False
    
    results = []
    
    # Testy poszczególnych sekcji
    results.append(test_single_photo_integration())
    results.append(test_batch_processing_integration()) 
    results.append(test_csv_xml_integration())
    results.append(test_background_changes())
    
    # Podsumowanie
    print("\n📊 PODSUMOWANIE")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    
    print(f"Zaliczone testy: {passed}/{total}")
    
    if passed == total:
        print("🎉 WSZYSTKIE TESTY ZALICZONE!")
        print("✅ CarveKit Engine jest w pełni kompatybilny z trzema sekcjami")
    else:
        print("⚠️ Niektóre testy nie przeszły - sprawdź implementację")
        print("\n🔧 Możliwe rozwiązania:")
        print("1. Sprawdź czy carvekit_engine.py jest w src/core/")
        print("2. Zainstaluj brakujące pakiety (carvekit, rembg, opencv)")
        print("3. Sprawdź czy struktura projektu jest poprawna")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)