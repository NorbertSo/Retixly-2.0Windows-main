import os
import sys
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import cv2
import numpy as np
import logging
import io

# Konfiguracja loggera
logger = logging.getLogger(__name__)

def create_thumbnail(image_path, size=(150, 150)):
    """Tworzy miniaturę obrazu."""
    try:
        # Sprawdź czy plik istnieje
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Nie znaleziono pliku: {image_path}")
            
        # Wczytanie obrazu
        image = Image.open(image_path)
        
        # Konwersja do RGB jeśli potrzeba
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Utworzenie miniatury zachowując proporcje
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Konwersja do QPixmap
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Wczytaj do QPixmap
        pixmap = QPixmap()
        success = pixmap.loadFromData(img_bytes.getvalue())
        
        if not success:
            raise Exception("Nie udało się utworzyć QPixmap")
            
        return pixmap
        
    except Exception as e:
        logger.error(f"Błąd tworzenia miniatury dla {image_path}: {str(e)}")
        # Zwróć pustą miniaturę
        pixmap = QPixmap(size[0], size[1])
        pixmap.fill(Qt.GlobalColor.lightGray)
        return pixmap

def resize_image(image, target_size, maintain_aspect=True):
    """Zmienia rozmiar obrazu."""
    try:
        if maintain_aspect:
            image.thumbnail(target_size, Image.Resampling.LANCZOS)
        else:
            image = image.resize(target_size, Image.Resampling.LANCZOS)
        return image
    except Exception as e:
        logger.error(f"Błąd podczas zmiany rozmiaru obrazu: {e}")
        return None

def apply_filters(image, filters_dict):
    """Aplikuje filtry do obrazu."""
    try:
        if 'brightness' in filters_dict:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(filters_dict['brightness'])
        
        if 'contrast' in filters_dict:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(filters_dict['contrast'])
        
        if 'saturation' in filters_dict:
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(filters_dict['saturation'])
        
        if 'sharpness' in filters_dict:
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(filters_dict['sharpness'])
        
        return image
    except Exception as e:
        logger.error(f"Błąd podczas aplikowania filtrów: {e}")
        return None

def remove_background(image_path):
    """Usuwa tło z obrazu używając rembg."""
    try:
        from rembg import remove
        
        # Wczytaj obraz
        with open(image_path, 'rb') as input_file:
            input_data = input_file.read()
        
        # Usuń tło
        output_data = remove(input_data)
        
        # Konwertuj do PIL Image
        image = Image.open(io.BytesIO(output_data))
        
        return image
        
    except Exception as e:
        logger.error(f"Błąd usuwania tła: {e}")
        return Image.open(image_path)

def add_background(foreground_image, background_color_or_image):
    """Dodaje tło do obrazu."""
    try:
        if isinstance(background_color_or_image, tuple):
            # Kolor tła
            background = Image.new('RGB', foreground_image.size, background_color_or_image)
        else:
            # Obraz tła
            background = background_color_or_image.resize(foreground_image.size)
            if background.mode != 'RGB':
                background = background.convert('RGB')
        
        # Połącz obrazy
        if foreground_image.mode == 'RGBA':
            background.paste(foreground_image, mask=foreground_image.split()[-1])
        else:
            background.paste(foreground_image)
        
        return background
    except Exception as e:
        logger.error(f"Błąd podczas dodawania tła: {e}")
        return None

def optimize_for_marketplace(image, marketplace):
    """Optymalizuje obraz dla konkretnego marketplace."""
    try:
        marketplace_specs = {
            'Amazon': {'size': (2000, 2000), 'format': 'JPEG', 'quality': 85},
            'eBay': {'size': (1600, 1600), 'format': 'JPEG', 'quality': 85},
            'Etsy': {'size': (2000, 2000), 'format': 'JPEG', 'quality': 90},
            'Allegro': {'size': (1600, 1600), 'format': 'JPEG', 'quality': 85},
            'Shopify': {'size': (2048, 2048), 'format': 'JPEG', 'quality': 85},
            'WeChat': {'size': (800, 800), 'format': 'JPEG', 'quality': 80}
        }
        
        if marketplace not in marketplace_specs:
            return image
        
        spec = marketplace_specs[marketplace]
        
        # Zmień rozmiar zachowując proporcje
        image.thumbnail(spec['size'], Image.Resampling.LANCZOS)
        
        # Wycentruj na białym tle
        new_image = Image.new('RGB', spec['size'], 'white')
        
        # Oblicz pozycję do wycentrowania
        x = (spec['size'][0] - image.width) // 2
        y = (spec['size'][1] - image.height) // 2
        
        new_image.paste(image, (x, y))
        
        return new_image
    except Exception as e:
        logger.error(f"Błąd podczas optymalizacji dla marketplace {marketplace}: {e}")
        return None

def process_image(image_path, settings):
    """Główna funkcja przetwarzania obrazu."""
    try:
        # Wczytaj obraz
        image = Image.open(image_path)
        
        # Usuń tło jeśli wymagane
        if settings.get('remove_background', False):
            image = remove_background(image_path)
        
        # Dodaj nowe tło
        if settings.get('new_background'):
            bg_settings = settings['new_background']
            if bg_settings['type'] == 'color':
                image = add_background(image, bg_settings['color'])
            elif bg_settings['type'] == 'image':
                bg_image = Image.open(bg_settings['path'])
                image = add_background(image, bg_image)
        
        # Zastosuj filtry
        if settings.get('filters'):
            image = apply_filters(image, settings['filters'])
        
        # Optymalizuj dla marketplace
        if settings.get('marketplace'):
            for marketplace in settings['marketplace']:
                image = optimize_for_marketplace(image, marketplace)
        
        return image
        
    except Exception as e:
        logger.error(f"Błąd przetwarzania obrazu {image_path}: {e}")
        return None

def get_image_info(image_path):
    """Zwraca informacje o obrazie."""
    try:
        with Image.open(image_path) as img:
            info = {
                'width': img.width,
                'height': img.height,
                'mode': img.mode,
                'format': img.format,
                'size_mb': os.path.getsize(image_path) / (1024 * 1024),
                'dpi': img.info.get('dpi', (72, 72)),
                'has_exif': hasattr(img, '_getexif') and img._getexif() is not None
            }
            return info
    except Exception as e:
        logger.error(f"Błąd odczytu informacji o obrazie: {e}")
        return None

def convert_image_format(image, target_format, quality=85):
    """Konwertuje format obrazu."""
    try:
        if target_format.upper() == 'JPEG' and image.mode in ('RGBA', 'LA'):
            # Konwertuj na białe tło dla JPEG
            background = Image.new('RGB', image.size, 'white')
            if image.mode == 'RGBA':
                background.paste(image, mask=image.split()[-1])
            else:
                background.paste(image)
            image = background
        
        # Przygotuj parametry zapisu
        save_kwargs = {'format': target_format}
        if target_format.upper() in ['JPEG', 'WEBP']:
            save_kwargs['quality'] = quality
        if target_format.upper() == 'PNG':
            save_kwargs['optimize'] = True
        
        # Zapisz do bufora
        output = io.BytesIO()
        image.save(output, **save_kwargs)
        output.seek(0)
        
        return Image.open(output)
    except Exception as e:
        logger.error(f"Błąd konwersji formatu obrazu: {e}")
        return None

def apply_watermark(image, watermark_settings):
    """Nakłada znak wodny na obraz."""
    try:
        if not watermark_settings.get('enabled', False):
            return image
            
        # Wczytaj znak wodny
        watermark = Image.open(watermark_settings['path'])
        
        # Przeskaluj znak wodny
        scale = watermark_settings.get('scale', 0.2)
        w = int(image.width * scale)
        h = int(w * watermark.height / watermark.width)
        watermark = watermark.resize((w, h), Image.Resampling.LANCZOS)
        
        # Ustaw przezroczystość
        if watermark.mode == 'RGBA':
            watermark.putalpha(int(255 * watermark_settings.get('opacity', 0.5)))
        
        # Oblicz pozycję
        position = watermark_settings.get('position', 'bottom-right')
        margin_x = watermark_settings.get('margin_x', 10)
        margin_y = watermark_settings.get('margin_y', 10)
        
        if 'bottom' in position:
            y = image.height - h - margin_y
        elif 'top' in position:
            y = margin_y
        else:
            y = (image.height - h) // 2
            
        if 'right' in position:
            x = image.width - w - margin_x
        elif 'left' in position:
            x = margin_x
        else:
            x = (image.width - w) // 2
        
        # Przygotuj obraz wynikowy
        result = image.copy()
        if watermark.mode == 'RGBA':
            result.paste(watermark, (x, y), watermark)
        else:
            result.paste(watermark, (x, y))
        
        return result
    except Exception as e:
        logger.error(f"Błąd podczas nakładania znaku wodnego: {e}")
        return image

if __name__ == "__main__":
    # Przykład użycia
    try:
        # Ustawienia testowe
        test_settings = {
            'remove_background': True,
            'new_background': {
                'type': 'color',
                'color': (255, 255, 255)
            },
            'filters': {
                'brightness': 1.2,
                'contrast': 1.1,
                'saturation': 1.1,
                'sharpness': 1.2
            },
            'marketplace': ['Amazon']
        }
        
        # Test przetwarzania obrazu
        test_image_path = "test_image.jpg"
        if os.path.exists(test_image_path):
            result = process_image(test_image_path, test_settings)
            if result:
                result.save("output_test.jpg")
                print("Test zakończony sukcesem")
            else:
                print("Błąd przetwarzania obrazu")
    except Exception as e:
        print(f"Błąd podczas testu: {e}")
