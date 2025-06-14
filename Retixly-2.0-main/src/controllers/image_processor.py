import cv2
import numpy as np
from PIL import Image, ImageEnhance
from rembg import remove
from PyQt6.QtCore import QObject, pyqtSignal
import os

class ImageProcessor(QObject):
    processing_progress = pyqtSignal(int, str)
    processing_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.current_image = None
        self.processed_image = None
        
    def process_image(self, image_path, settings):
        """Przetwarza pojedyncze zdjęcie zgodnie z ustawieniami."""
        try:
            self.processing_progress.emit(10, self.tr("Loading image..."))
            image = self.load_image(image_path)
            
            if settings.get('remove_background'):
                self.processing_progress.emit(30, self.tr("Removing background..."))
                image = self.remove_background(image)
            
            if settings.get('background_settings'):
                self.processing_progress.emit(50, self.tr("Applying new background..."))
                image = self.apply_background(image, settings['background_settings'])
            
            if settings.get('retouch'):
                self.processing_progress.emit(70, self.tr("Retouching..."))
                image = self.apply_retouch(image, settings['retouch_settings'])
            
            if settings.get('watermark'):
                self.processing_progress.emit(90, self.tr("Adding watermark..."))
                image = self.apply_watermark(image, settings['watermark_settings'])
            
            self.processed_image = image
            self.processing_progress.emit(100, self.tr("Processing complete"))
            return True
            
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False
            
    def load_image(self, image_path):
        """Wczytuje obraz z obsługą różnych formatów."""
        if image_path.lower().endswith('.heic'):
            # Obsługa formatu HEIC
            from pillow_heif import register_heif_opener
            register_heif_opener()
            
        image = Image.open(image_path)
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        return image
        
    def remove_background(self, image):
        """Usuwa tło ze zdjęcia używając rembg."""
        # Konwersja do formatu obsługiwanego przez rembg
        img_array = np.array(image)
        # Usunięcie tła
        result = remove(img_array)
        return Image.fromarray(result)
        
    def apply_background(self, image, background_settings):
        """Nakłada nowe tło zgodnie z ustawieniami."""
        bg_type = background_settings.get('type', 'color')
        
        if bg_type == 'color':
            # Tworzenie tła o jednolitym kolorze
            bg_color = background_settings.get('color', (255, 255, 255))
            bg = Image.new('RGBA', image.size, bg_color)
        else:
            # Wczytanie i dopasowanie obrazu tła
            bg_path = background_settings.get('image_path')
            bg = Image.open(bg_path)
            bg = bg.resize(image.size, Image.Resampling.LANCZOS)
            
        # Połączenie tła z obrazem
        bg.paste(image, mask=image.split()[3])
        return bg
        
    def apply_retouch(self, image, retouch_settings):
        """Aplikuje ustawienia retuszu."""
        # Tworzenie kopii obrazu do modyfikacji
        enhanced = image.copy()
        
        # Zastosowanie różnych ulepszeń
        if 'brightness' in retouch_settings:
            enhancer = ImageEnhance.Brightness(enhanced)
            enhanced = enhancer.enhance(retouch_settings['brightness'])
            
        if 'contrast' in retouch_settings:
            enhancer = ImageEnhance.Contrast(enhanced)
            enhanced = enhancer.enhance(retouch_settings['contrast'])
            
        if 'sharpness' in retouch_settings:
            enhancer = ImageEnhance.Sharpness(enhanced)
            enhanced = enhancer.enhance(retouch_settings['sharpness'])
            
        if 'color' in retouch_settings:
            enhancer = ImageEnhance.Color(enhanced)
            enhanced = enhancer.enhance(retouch_settings['color'])
            
        return enhanced
        
    def apply_watermark(self, image, watermark_settings):
        """Nakłada znak wodny na obraz."""
        watermark = Image.open(watermark_settings['path'])
        
        # Skalowanie znaku wodnego
        if 'scale' in watermark_settings:
            scale = watermark_settings['scale']
            new_size = tuple(int(dim * scale) for dim in watermark.size)
            watermark = watermark.resize(new_size, Image.Resampling.LANCZOS)
            
        # Określenie pozycji znaku wodnego
        position = watermark_settings.get('position', 'bottom-right')
        opacity = watermark_settings.get('opacity', 0.5)
        
        # Obliczenie współrzędnych
        if position == 'bottom-right':
            x = image.width - watermark.width - 10
            y = image.height - watermark.height - 10
        elif position == 'bottom-left':
            x = 10
            y = image.height - watermark.height - 10
        elif position == 'top-right':
            x = image.width - watermark.width - 10
            y = 10
        elif position == 'top-left':
            x = 10
            y = 10
        else:  # center
            x = (image.width - watermark.width) // 2
            y = (image.height - watermark.height) // 2
            
        # Nałożenie znaku wodnego z przezroczystością
        watermark.putalpha(int(255 * opacity))
        image.paste(watermark, (x, y), watermark)
        
        return image
        
    def prepare_for_marketplace(self, image, marketplace_settings):
        """Przygotowuje obraz zgodnie z wymaganiami marketplace."""
        # Pobranie wymaganych wymiarów
        target_size = marketplace_settings.get('size', (1000, 1000))
        
        # Skalowanie z zachowaniem proporcji
        image.thumbnail(target_size, Image.Resampling.LANCZOS)
        
        # Tworzenie nowego obrazu o dokładnych wymiarach
        new_image = Image.new('RGBA', target_size, (255, 255, 255, 0))
        
        # Wycentrowanie obrazu
        x = (target_size[0] - image.width) // 2
        y = (target_size[1] - image.height) // 2
        new_image.paste(image, (x, y))
        
        return new_image
        
    def save_image(self, image, output_path, format_settings):
        """Zapisuje obraz w określonym formacie."""
        # Przygotowanie formatu
        output_format = format_settings.get('format', 'PNG')
        quality = format_settings.get('quality', 85)
        
        # Optymalizacja
        if format_settings.get('optimize', True):
            if output_format.upper() == 'JPEG':
                image = image.convert('RGB')
                image.save(output_path, 
                         format=output_format,
                         quality=quality,
                         optimize=True)
            elif output_format.upper() == 'PNG':
                image.save(output_path,
                         format=output_format,
                         optimize=True,
                         compress_level=9)
            elif output_format.upper() == 'WEBP':
                image.save(output_path,
                         format=output_format,
                         quality=quality,
                         method=6)
        else:
            image.save(output_path, format=output_format, quality=quality)
