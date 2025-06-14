from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PIL import Image, ImageEnhance
import os
import cv2
import numpy as np
from pathlib import Path
import tempfile
import shutil

# Import rembg tylko jeśli dostępny
try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

class BatchProcessor(QObject):
    progress_updated = pyqtSignal(int, int, str)  # current, total, message
    processing_finished = pyqtSignal(list)  # lista przetworzonych plików
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_paused = False
        self.current_thread = None

    def process_images(self, image_files, settings):
        print(f"DEBUG: BatchProcessor.process_images called with {len(image_files)} files")
        print(f"DEBUG: Settings: {settings}")
        
        self.is_running = True
        self.is_paused = False
        
        # Utworzenie wątku przetwarzającego
        self.current_thread = ProcessingThread(image_files, settings)
        self.current_thread.progress_updated.connect(self.progress_updated)
        self.current_thread.error_occurred.connect(self.error_occurred)
        self.current_thread.finished_with_results.connect(self.processing_finished)
        
        self.current_thread.start()

    def pause(self):
        self.is_paused = True
        if self.current_thread:
            self.current_thread.pause()

    def resume(self):
        self.is_paused = False
        if self.current_thread:
            self.current_thread.resume()

    def stop(self):
        print("DEBUG: BatchProcessor.stop() called")
        self.is_running = False
        if self.current_thread:
            self.current_thread.stop()
            self.current_thread.wait()
            self.current_thread = None

class ProcessingThread(QThread):
    progress_updated = pyqtSignal(int, int, str)  # current, total, message
    error_occurred = pyqtSignal(str)
    finished_with_results = pyqtSignal(list)  # lista przetworzonych plików
    
    def __init__(self, image_files, settings):
        super().__init__()
        self.image_files = image_files
        self.settings = settings
        self.is_running = True
        self.is_paused = False
        self.processed_files = []

    def run(self):
        print(f"DEBUG: ProcessingThread.run() started with {len(self.image_files)} files")
        total = len(self.image_files)
        
        # Przygotuj katalog wyjściowy
        output_dir = self.prepare_output_directory()
        print(f"DEBUG: Output directory: {output_dir}")
        
        for i, image_file in enumerate(self.image_files, 1):
            if not self.is_running:
                print("DEBUG: Processing stopped by user")
                break
                
            while self.is_paused:
                self.msleep(100)
                
            try:
                print(f"DEBUG: Processing file {i}/{total}: {image_file}")
                
                # Sprawdź czy plik istnieje
                if not os.path.exists(image_file):
                    print(f"DEBUG: File not found: {image_file}")
                    continue
                
                # Aktualizuj progress
                self.progress_updated.emit(i, total, f"Przetwarzanie {Path(image_file).name}...")
                
                # Przetwórz obraz
                processed_image = self.process_single_image(image_file)
                
                if processed_image:
                    # Zapisz obraz
                    output_path = self.save_processed_image(processed_image, image_file, output_dir)
                    if output_path:
                        self.processed_files.append({
                            'original': image_file,
                            'processed': output_path,
                            'success': True
                        })
                        print(f"DEBUG: Successfully processed: {output_path}")
                    else:
                        self.processed_files.append({
                            'original': image_file,
                            'processed': None,
                            'success': False,
                            'error': 'Failed to save'
                        })
                else:
                    self.processed_files.append({
                        'original': image_file,
                        'processed': None,
                        'success': False,
                        'error': 'Failed to process'
                    })
                
            except Exception as e:
                print(f"DEBUG: Error processing {image_file}: {str(e)}")
                self.processed_files.append({
                    'original': image_file,
                    'processed': None,
                    'success': False,
                    'error': str(e)
                })
                
                # Jeśli nie ma opcji pomijania błędów, zatrzymaj
                if not self.settings.get('skip_errors', True):
                    self.error_occurred.emit(f"Błąd podczas przetwarzania {Path(image_file).name}: {str(e)}")
                    return

        if self.is_running:
            successful = len([f for f in self.processed_files if f['success']])
            print(f"DEBUG: Processing complete. {successful}/{total} files processed successfully")
            self.progress_updated.emit(total, total, f"Zakończono! Przetworzono {successful}/{total} plików")
            
        # Wyślij wyniki
        self.finished_with_results.emit(self.processed_files)

    def prepare_output_directory(self):
        """Przygotowuje katalog wyjściowy."""
        save_location = self.settings.get('save_location', 'Lokalnie')
        
        if save_location == 'Lokalnie':
            local_path = self.settings.get('local_path', '')
            if local_path and os.path.exists(local_path):
                return local_path
        
        # Fallback - utwórz katalog w folderze aplikacji
        default_output = Path.cwd() / "processed_images"
        default_output.mkdir(exist_ok=True)
        print(f"DEBUG: Using default output directory: {default_output}")
        return str(default_output)

    def process_single_image(self, image_path):
        """Przetwarza pojedynczy obraz zgodnie z ustawieniami."""
        try:
            print(f"DEBUG: Loading image: {image_path}")
            
            # Wczytaj obraz
            image = Image.open(image_path)
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            # Sprawdź tryb przetwarzania
            processing_mode = self.settings.get('processing', {}).get('mode', 'Usuń tło')
            print(f"DEBUG: Processing mode: {processing_mode}")
            
            # Przetwarzanie tła
            if processing_mode == 'Usuń tło':
                image = self.remove_background(image)
            elif processing_mode == 'Zamień tło':
                image = self.replace_background(image)
            elif processing_mode == 'Tylko przygotuj do sprzedaży':
                pass  # Nie rób nic z tłem
            
            # Przygotuj do marketplace jeśli wybrano
            if self.settings.get('prepare_for_sale', False):
                image = self.prepare_for_marketplace(image)
            
            return image
            
        except Exception as e:
            print(f"DEBUG: Error in process_single_image: {str(e)}")
            raise

    def remove_background(self, image):
        """Usuwa tło z obrazu."""
        try:
            if HAS_REMBG:
                print("DEBUG: Using rembg for background removal")
                # Konwertuj PIL do numpy array
                img_array = np.array(image)
                # Usuń tło
                result = rembg_remove(img_array)
                return Image.fromarray(result)
            else:
                print("DEBUG: rembg not available, using simple background removal")
                return self.simple_background_removal(image)
        except Exception as e:
            print(f"DEBUG: Error in remove_background: {str(e)}")
            return self.simple_background_removal(image)

    def simple_background_removal(self, image):
        """Prosta metoda usuwania tła bez rembg."""
        try:
            # Konwertuj do OpenCV
            img_array = np.array(image)
            if img_array.shape[2] == 4:  # RGBA
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
            
            # Tworzenie maski (bardzo proste - może nie działać idealnie)
            mask = np.zeros(img_array.shape[:2], np.uint8)
            bgd_model = np.zeros((1, 65), np.float64)
            fgd_model = np.zeros((1, 65), np.float64)
            
            height, width = img_array.shape[:2]
            # Prostokąt zakładający że obiekt jest w środku
            rectangle = (int(width*0.1), int(height*0.1), int(width*0.9), int(height*0.9))
            
            cv2.grabCut(img_array, mask, rectangle, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
            mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
            
            # Zastosuj maskę
            result = img_array * mask2[:, :, np.newaxis]
            
            # Dodaj kanał alpha
            alpha = mask2 * 255
            result = np.dstack((result, alpha))
            
            return Image.fromarray(result, 'RGBA')
            
        except Exception as e:
            print(f"DEBUG: Error in simple_background_removal: {str(e)}")
            # Fallback - zwróć oryginalny obraz
            return image

    def replace_background(self, image):
        """Zamienia tło obrazu."""
        try:
            # Najpierw usuń tło
            no_bg_image = self.remove_background(image)
            
            processing_settings = self.settings.get('processing', {})
            
            # Sprawdź typ tła
            if self.settings.get('bg_color_tab', True):
                # Kolor tła
                bg_color = processing_settings.get('bg_color', '#FFFFFF')
                if bg_color.startswith('#'):
                    # Konwertuj hex na RGB
                    bg_color = tuple(int(bg_color[i:i+2], 16) for i in (1, 3, 5))
                
                # Utwórz tło
                background = Image.new('RGBA', image.size, bg_color + (255,))
            else:
                # Obraz tła
                bg_image_path = processing_settings.get('bg_image')
                if bg_image_path and os.path.exists(bg_image_path):
                    background = Image.open(bg_image_path)
                    background = background.resize(image.size, Image.Resampling.LANCZOS)
                    background = background.convert('RGBA')
                else:
                    # Fallback na biały
                    background = Image.new('RGBA', image.size, (255, 255, 255, 255))
            
            # Połącz obrazy
            background.paste(no_bg_image, mask=no_bg_image.split()[3])
            return background
            
        except Exception as e:
            print(f"DEBUG: Error in replace_background: {str(e)}")
            return image

    def prepare_for_marketplace(self, image):
        """Przygotowuje obraz dla wybranych marketplace."""
        try:
            marketplaces = self.settings.get('marketplaces', [])
            if not marketplaces:
                return image
            
            # Użyj pierwszego wybranego marketplace
            marketplace = marketplaces[0]
            print(f"DEBUG: Preparing for marketplace: {marketplace}")
            
            # Specyfikacje marketplace
            specs = {
                'Amazon': {'size': (2000, 2000), 'bg_color': (255, 255, 255)},
                'eBay': {'size': (1600, 1600), 'bg_color': (255, 255, 255)},
                'Etsy': {'size': (2000, 2000), 'bg_color': (255, 255, 255)},
                'Allegro': {'size': (1600, 1600), 'bg_color': (255, 255, 255)},
                'Shopify': {'size': (2048, 2048), 'bg_color': (255, 255, 255)},
                'WeChat': {'size': (800, 800), 'bg_color': (255, 255, 255)}
            }
            
            spec = specs.get(marketplace, {'size': (1600, 1600), 'bg_color': (255, 255, 255)})
            target_size = spec['size']
            bg_color = spec['bg_color']
            
            # Zmień rozmiar zachowując proporcje
            image.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # Utwórz nowe tło o docelowym rozmiarze
            new_image = Image.new('RGBA', target_size, bg_color + (255,))
            
            # Wycentruj obraz
            x = (target_size[0] - image.width) // 2
            y = (target_size[1] - image.height) // 2
            
            if image.mode == 'RGBA':
                new_image.paste(image, (x, y), image)
            else:
                new_image.paste(image, (x, y))
            
            return new_image
            
        except Exception as e:
            print(f"DEBUG: Error in prepare_for_marketplace: {str(e)}")
            return image

    def save_processed_image(self, image, original_path, output_dir):
        """Zapisuje przetworzony obraz."""
        try:
            # Przygotuj nazwę pliku
            original_name = Path(original_path).stem
            
            # Format zapisu
            output_format = self.settings.get('format', {}).get('type', 'PNG')
            quality = self.settings.get('format', {}).get('quality', 90)
            
            # Rozszerzenie
            if output_format.upper() == 'JPEG':
                extension = '.jpg'
            else:
                extension = f'.{output_format.lower()}'
            
            # Pełna ścieżka
            output_filename = f"{original_name}_processed{extension}"
            output_path = os.path.join(output_dir, output_filename)
            
            # Jeśli plik istnieje, dodaj numer
            counter = 1
            while os.path.exists(output_path):
                output_filename = f"{original_name}_processed_{counter}{extension}"
                output_path = os.path.join(output_dir, output_filename)
                counter += 1
            
            # Przygotuj obraz do zapisu
            save_image = image
            if output_format.upper() == 'JPEG':
                # JPEG nie obsługuje przezroczystości
                if image.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'RGBA':
                        background.paste(image, mask=image.split()[3])
                    else:
                        background.paste(image)
                    save_image = background
            
            # Zapisz
            save_kwargs = {'format': output_format}
            if output_format.upper() in ['JPEG', 'WEBP']:
                save_kwargs['quality'] = quality
            if output_format.upper() == 'PNG':
                save_kwargs['optimize'] = True
            
            save_image.save(output_path, **save_kwargs)
            print(f"DEBUG: Saved: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"DEBUG: Error saving image: {str(e)}")
            return None

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        print("DEBUG: ProcessingThread.stop() called")
        self.is_running = False