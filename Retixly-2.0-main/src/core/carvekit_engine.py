"""
Optimized CarveKit Engine - Complete Version
Zoptymalizowany silnik z zachowaniem najważniejszych funkcji dla jakości
"""

import os
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import logging
import time
from typing import Optional, Dict, Any, Tuple, List
import cv2
from functools import lru_cache
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import tempfile
import gc

logger = logging.getLogger(__name__)

# Zoptymalizowana konfiguracja
OPTIMIZED_CONFIG = {
    'MAX_DIMENSION': 1024,  # Maksymalny wymiar dla przetwarzania
    'TIMEOUT': 30,  # Jednolity timeout
    'CACHE_SIZE': 50,  # Rozmiar cache
    'QUALITY_THRESHOLDS': {
        'noise_threshold': 0.2,
        'blur_threshold': 150.0,  # Laplacian variance
        'min_resolution': 200 * 200
    },
    'PRODUCT_HINTS': {
        'bottle': {'aspect_ratio': (1.5, 4.0), 'circularity': 0.6},
        'box': {'aspect_ratio': (0.7, 1.5), 'rectangularity': 0.8},
        'round': {'circularity': 0.7, 'aspect_ratio': (0.8, 1.2)}
    }
}

class FastProductDetector:
    """Szybki detektor typu produktu - uproszczona wersja."""
    
    @staticmethod
    @lru_cache(maxsize=100)
    def detect_product_type(image_hash: str, width: int, height: int, 
                           avg_color: Tuple[int, int, int]) -> str:
        """Cache'owana detekcja typu produktu."""
        try:
            aspect_ratio = width / height if height > 0 else 1.0
            
            # Podstawowa klasyfikacja na podstawie kształtu
            if 1.5 < aspect_ratio < 4.0:
                return 'bottle'
            elif 0.7 < aspect_ratio < 1.5 and avg_color[0] + avg_color[1] + avg_color[2] < 400:
                return 'box'
            elif 0.8 < aspect_ratio < 1.2:
                return 'round'
            else:
                return 'generic'
                
        except Exception:
            return 'generic'

class FastQualityAnalyzer:
    """Szybki analizator jakości obrazu."""
    
    @staticmethod
    def analyze_quality(image: Image.Image) -> Dict[str, Any]:
        """Szybka analiza jakości obrazu."""
        try:
            img_array = np.array(image.convert('RGB'))
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Analiza rozmycia (Laplacian variance)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            is_blurry = laplacian_var < OPTIMIZED_CONFIG['QUALITY_THRESHOLDS']['blur_threshold']
            
            # Analiza szumu (uproszczona)
            noise_estimate = np.std(gray) / 255.0
            is_noisy = noise_estimate > OPTIMIZED_CONFIG['QUALITY_THRESHOLDS']['noise_threshold']
            
            # Analiza rozmiaru
            pixel_count = image.size[0] * image.size[1]
            is_low_res = pixel_count < OPTIMIZED_CONFIG['QUALITY_THRESHOLDS']['min_resolution']
            
            # Ogólna jakość
            quality_score = 1.0
            if is_blurry:
                quality_score -= 0.3
            if is_noisy:
                quality_score -= 0.2
            if is_low_res:
                quality_score -= 0.3
            
            return {
                'blur_level': float(laplacian_var),
                'noise_level': float(noise_estimate),
                'is_low_quality': quality_score < 0.6,
                'quality_score': max(0.0, quality_score),
                'needs_enhancement': is_blurry or is_noisy or is_low_res
            }
            
        except Exception as e:
            logger.warning(f"Quality analysis failed: {e}")
            return {
                'blur_level': 150.0,
                'noise_level': 0.1,
                'is_low_quality': False,
                'quality_score': 0.7,
                'needs_enhancement': False
            }

class FastImageEnhancer:
    """Szybki enhancer obrazów."""
    
    @staticmethod
    def enhance_image(image: Image.Image, quality_info: Dict[str, Any]) -> Image.Image:
        """Szybka poprawa jakości obrazu."""
        try:
            if not quality_info.get('needs_enhancement', False):
                return image
            
            enhanced = image.copy()
            
            # Redukcja szumu (tylko jeśli potrzeba)
            if quality_info.get('noise_level', 0) > 0.15:
                enhanced = enhanced.filter(ImageFilter.MedianFilter(size=3))
            
            # Sharpening (tylko jeśli rozmyte)
            if quality_info.get('blur_level', 200) < 100:
                enhancer = ImageEnhance.Sharpness(enhanced)
                enhanced = enhancer.enhance(1.2)
            
            # Kontrast (lekka poprawa)
            if quality_info.get('quality_score', 1.0) < 0.5:
                enhancer = ImageEnhance.Contrast(enhanced)
                enhanced = enhancer.enhance(1.1)
            
            return enhanced
            
        except Exception as e:
            logger.warning(f"Image enhancement failed: {e}")
            return image

class OptimizedBackgroundRemover:
    """Zoptymalizowany procesor usuwania tła z najważniejszymi funkcjami."""
    
    def __init__(self):
        self.carvekit_available = False
        self.rembg_available = False
        self._rembg_session = None
        self._init_models()
        
    def _init_models(self):
        """Szybka inicjalizacja modeli."""
        # CarveKit
        try:
            from carvekit.api.high import HiInterface
            self.carvekit_interface = HiInterface(
                object_type="object",
                batch_size_seg=1,
                batch_size_matting=1,
                device='cpu',
                seg_mask_size=1024,  # ZWIĘKSZONY rozmiar maski dla jakości
                matting_mask_size=2048,  # ZWIĘKSZONY rozmiar mattingu
                trimap_prob_threshold=231,
                trimap_dilation=30,  # Większy dla lepszych krawędzi
                fp16=False
            )
            self.carvekit_available = True
            logger.info("✅ CarveKit initialized (high quality mode)")
        except Exception as e:
            logger.error(f"❌ CarveKit unavailable: {e}")
            self.carvekit_available = False
        # REMBG fallback
        try:
            from rembg import remove, new_session
            self._rembg_session = new_session('u2net')
            self.rembg_available = True
            logger.info("✅ REMBG initialized")
        except Exception as e:
            logger.warning(f"REMBG unavailable: {e}")
            self.rembg_available = False

    def remove_background_optimized(self, image: Image.Image, settings: Dict[str, Any] = None) -> Image.Image:
        """Główna metoda usuwania tła - zawsze próbuje CarveKit, potem rembg, na końcu fallback."""
        start_time = time.time()
        try:
            if settings is None:
                settings = {}
            original_size = image.size
            pixel_count = original_size[0] * original_size[1]
            avg_color = self._get_average_color(image)
            image_hash = str(hash(image.tobytes()[:1000]))
            product_type = FastProductDetector.detect_product_type(
                image_hash, original_size[0], original_size[1], avg_color
            )
            quality_info = FastQualityAnalyzer.analyze_quality(image)
            logger.info(f"Processing {product_type} image: {original_size}, quality: {quality_info['quality_score']:.2f}")
            processing_image = image
            if quality_info['needs_enhancement']:
                processing_image = FastImageEnhancer.enhance_image(image, quality_info)
            processing_image, scale_factor = self._smart_resize(processing_image, quality_info)
            # --- WYMUSZ CarveKit ---
            if self.carvekit_available:
                try:
                    result = self._carvekit_removal_enhanced(processing_image, product_type)
                    logger.info("✅ CarveKit result used")
                except Exception as e:
                    logger.error(f"CarveKit failed: {e}")
                    result = None
            else:
                logger.warning("CarveKit not available, using rembg fallback")
                result = None
            # --- Fallback do rembg ---
            if result is None and self.rembg_available:
                try:
                    result = self._rembg_removal_enhanced(processing_image, product_type)
                    logger.info("✅ REMBG fallback result used")
                except Exception as e:
                    logger.error(f"REMBG fallback failed: {e}")
                    result = None
            # --- Ostateczny fallback ---
            if result is None:
                logger.error("❌ All AI methods failed, using geometric fallback!")
                result = self._intelligent_fallback(processing_image, product_type)
            # Przywróć oryginalny rozmiar
            if scale_factor < 1.0:
                result = self._scale_back_enhanced(result, original_size, quality_info)
            # Post-processing specyficzne dla produktu
            result = self._apply_product_postprocessing(result, product_type, image)
            if settings.get('bg_mode') != 'remove':
                result = self._apply_background_enhanced(result, settings)
            processing_time = time.time() - start_time
            logger.info(f"✅ Optimized processing completed in {processing_time:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Optimized processing failed: {e}")
            return self._intelligent_fallback(image, product_type if 'product_type' in locals() else 'generic')
    
    def _get_average_color(self, image: Image.Image) -> Tuple[int, int, int]:
        """Szybkie obliczenie średniego koloru."""
        try:
            # Zmniejsz obraz dla szybkości
            small = image.resize((50, 50), Image.Resampling.NEAREST)
            img_array = np.array(small.convert('RGB'))
            return tuple(np.mean(img_array, axis=(0, 1)).astype(int))
        except Exception:
            return (128, 128, 128)
    
    def _smart_resize(self, image: Image.Image, quality_info: Dict[str, Any]) -> Tuple[Image.Image, float]:
        """Inteligentne skalowanie z uwzględnieniem jakości."""
        width, height = image.size
        max_dim = OPTIMIZED_CONFIG['MAX_DIMENSION']
        
        # Dla obrazów wysokiej jakości pozwól na większy rozmiar
        if quality_info.get('quality_score', 0.7) > 0.8:
            max_dim = int(max_dim * 1.2)
        
        if max(width, height) <= max_dim:
            return image, 1.0
            
        # Oblicz współczynnik skalowania
        scale_factor = max_dim / max(width, height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        # Upewnij się, że wymiary są parzyste
        new_width = new_width - (new_width % 2)
        new_height = new_height - (new_height % 2)
        
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return resized, scale_factor
    
    def _calculate_timeout(self, pixel_count: int, quality_info: Dict[str, Any]) -> int:
        """Inteligentne obliczenie timeout."""
        base_timeout = 20
        
        # Dostosuj na podstawie rozmiaru
        if pixel_count > 2_000_000:
            base_timeout += 15
        elif pixel_count > 1_000_000:
            base_timeout += 10
        elif pixel_count > 500_000:
            base_timeout += 5
        
        # Dostosuj na podstawie jakości
        if quality_info.get('is_low_quality', False):
            base_timeout += 10
        
        return min(base_timeout, 60)  # Max 60s
    
    def _process_with_advanced_timeout(self, image: Image.Image, timeout: int,
                                     product_type: str, quality_info: Dict[str, Any]) -> Image.Image:
        """Zaawansowane przetwarzanie z timeout i fallback."""
        def _advanced_worker():
            try:
                # Wybierz najlepszą metodę na podstawie typu produktu
                if self.carvekit_available and quality_info.get('quality_score', 0.7) > 0.6:
                    return self._carvekit_removal_enhanced(image, product_type)
                
                elif self.rembg_available:
                    return self._rembg_removal_enhanced(image, product_type)
                
                else:
                    return self._intelligent_fallback(image, product_type)
                    
            except Exception as e:
                logger.error(f"Advanced worker failed: {e}")
                return self._intelligent_fallback(image, product_type)
        
        # Wykonaj z timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_advanced_worker)
            try:
                result = future.result(timeout=timeout)
                if self._validate_result(result):
                    return result
                else:
                    logger.warning("Result validation failed, using fallback")
                    return self._intelligent_fallback(image, product_type)
            except TimeoutError:
                future.cancel()
                logger.warning(f"Processing timeout after {timeout}s, using fallback")
                return self._intelligent_fallback(image, product_type)
    
    def _carvekit_removal_enhanced(self, image: Image.Image, product_type: str) -> Image.Image:
        """CarveKit removal z optymalizacją dla typu produktu."""
        try:
            # Konwertuj do RGB jeśli potrzeba
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Lekka pre-enhancement dla niektórych typów produktów
            if product_type in ['bottle', 'round']:
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.05)
            
            # Przetwarzanie CarveKit
            images = [image]
            results = self.carvekit_interface(images)
            
            if results and len(results) > 0:
                result = results[0]
                
                if result.mode != 'RGBA':
                    result = result.convert('RGBA')
                
                # Cleanup memory
                del images, results
                gc.collect()
                
                return result
            else:
                raise Exception("CarveKit returned no results")
                
        except Exception as e:
            logger.error(f"CarveKit enhanced removal failed: {e}")
            raise
    
    def _rembg_removal_enhanced(self, image: Image.Image, product_type: str) -> Image.Image:
        """REMBG removal z post-processing."""
        try:
            from rembg import remove
            
            # Konwertuj do array
            img_array = np.array(image)
            
            # Przetwarzanie REMBG
            if self._rembg_session:
                result_array = remove(img_array, session=self._rembg_session)
            else:
                result_array = remove(img_array)
            
            result = Image.fromarray(result_array)
            
            if result.mode != 'RGBA':
                result = result.convert('RGBA')
            
            # Podstawowe post-processing
            result = self._apply_basic_morphology(result, product_type)
            
            # Cleanup memory
            del img_array, result_array
            gc.collect()
            
            return result
            
        except Exception as e:
            logger.error(f"REMBG enhanced removal failed: {e}")
            raise
    
    def _apply_basic_morphology(self, image: Image.Image, product_type: str) -> Image.Image:
        """Podstawowe operacje morfologiczne."""
        try:
            img_array = np.array(image)
            if img_array.shape[2] != 4:
                return image
            
            alpha = img_array[:, :, 3]
            
            # Kernel size na podstawie typu produktu
            kernel_size = {
                'bottle': (3, 3),
                'box': (5, 5), 
                'round': (4, 4),
                'generic': (3, 3)
            }.get(product_type, (3, 3))
            
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, kernel_size)
            
            # Close small gaps
            alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel)
            
            # Remove small noise
            alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, kernel)
            
            img_array[:, :, 3] = alpha
            return Image.fromarray(img_array)
            
        except Exception as e:
            logger.warning(f"Morphology failed: {e}")
            return image
    
    def _intelligent_fallback(self, image: Image.Image, product_type: str) -> Image.Image:
        """Inteligentny fallback na podstawie typu produktu."""
        try:
            img_array = np.array(image.convert('RGB'))
            height, width = img_array.shape[:2]
            
            # Różne strategie dla różnych typów produktów
            if product_type == 'bottle':
                mask = self._create_bottle_mask(img_array, width, height)
            elif product_type == 'box':
                mask = self._create_box_mask(img_array, width, height)
            elif product_type == 'round':
                mask = self._create_round_mask(img_array, width, height)
            else:
                mask = self._create_generic_mask(img_array, width, height)
            
            # Utwórz wynik RGBA
            result_array = np.dstack([img_array, mask])
            return Image.fromarray(result_array)
            
        except Exception as e:
            logger.error(f"Intelligent fallback failed: {e}")
            return image.convert('RGBA') if image.mode != 'RGBA' else image
    
    def _create_bottle_mask(self, img_array: np.ndarray, width: int, height: int) -> np.ndarray:
        """Inteligentna maska dla butelek oparta o analizę gradientów."""
        mask = np.zeros((height, width), dtype=np.uint8)
        try:
            # Konwertuj do grayscale
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            # Wykryj krawędzie
            edges = cv2.Canny(gray, 50, 150)
            # Znajdź kontury
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                # Wybierz największy kontur
                largest_contour = max(contours, key=cv2.contourArea)
                cv2.drawContours(mask, [largest_contour], -1, 255, -1)
            else:
                # Fallback do prostszej metody
                center_x, center_y = width // 2, height // 2
                radius_x, radius_y = width // 3, int(height * 0.4)
                cv2.ellipse(mask, (center_x, center_y), (radius_x, radius_y), 0, 0, 360, 255, -1)
            return mask
        except Exception:
            return mask

    def _create_box_mask(self, img_array: np.ndarray, width: int, height: int) -> np.ndarray:
        """Maska dla pudełek - prostokątna."""
        mask = np.zeros((height, width), dtype=np.uint8)
        margin_x, margin_y = width // 6, height // 6
        cv2.rectangle(mask, (margin_x, margin_y), (width - margin_x, height - margin_y), 255, -1)
        return mask
    
    def _create_round_mask(self, img_array: np.ndarray, width: int, height: int) -> np.ndarray:
        """Inteligentna maska dla okrągłych obiektów oparta o detekcję krawędzi."""
        mask = np.zeros((height, width), dtype=np.uint8)
        try:
            # Konwertuj do grayscale i rozmyj
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            blurred = cv2.GaussianBlur(gray, (9, 9), 2)
            
            # Adaptacyjne progowanie
            thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY_INV, 21, 4)
            
            # Znajdź kontury
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                # Wybierz kontur najbardziej zbliżony do okręgu
                most_circular = None
                best_circularity = 0
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > 100:  # Ignoruj małe kontury
                        perimeter = cv2.arcLength(contour, True)
                        if perimeter > 0:
                            circularity = 4 * np.pi * area / (perimeter * perimeter)
                            if circularity > best_circularity:
                                best_circularity = circularity
                                most_circular = contour
                
                if most_circular is not None:
                    cv2.drawContours(mask, [most_circular], -1, 255, -1)
                    return mask
            
            return mask
        except Exception:
            return mask
    
    def _create_generic_mask(self, img_array: np.ndarray, width: int, height: int) -> np.ndarray:
        """Inteligentna maska generyczna wykorzystująca segmentację."""
        mask = np.zeros((height, width), dtype=np.uint8)
        try:
            # Konwertuj do grayscale
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Adaptacyjne progowanie
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY_INV, 21, 4)
            
            # Usuń szum
            kernel = np.ones((3,3), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            
            # Znajdź kontury
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Wybierz największy kontur
                largest_contour = max(contours, key=cv2.contourArea)
                cv2.drawContours(mask, [largest_contour], -1, 255, -1)
            
            return mask
        except Exception:
            return mask
    
    def _apply_product_postprocessing(self, result: Image.Image, product_type: str, 
                                    original: Image.Image) -> Image.Image:
        """Post-processing specyficzne dla typu produktu."""
        try:
            if result.mode != 'RGBA':
                return result
            
            result_array = np.array(result)
            alpha = result_array[:, :, 3]
            
            # Specyficzne operacje dla typu produktu
            if product_type == 'bottle':
                # Usuń dziury wewnętrzne dla butelek
                alpha = self._remove_internal_holes_simple(alpha)
            elif product_type == 'box':
                # Wzmocnij krawędzie dla pudełek
                alpha = self._enhance_edges_simple(alpha)
            elif product_type == 'round':
                # Wygładź krawędzie dla okrągłych obiektów
                alpha = cv2.GaussianBlur(alpha, (3, 3), 0.5)
            
            result_array[:, :, 3] = alpha
            return Image.fromarray(result_array)
            
        except Exception as e:
            logger.warning(f"Product post-processing failed: {e}")
            return result
    
    def _remove_internal_holes_simple(self, alpha: np.ndarray) -> np.ndarray:
        """Proste usuwanie dziur wewnętrznych."""
        try:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            return cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel)
        except Exception:
            return alpha
    
    def _enhance_edges_simple(self, alpha: np.ndarray) -> np.ndarray:
        """Proste wzmocnienie krawędzi."""
        try:
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            enhanced = cv2.filter2D(alpha, -1, kernel)
            return np.clip(enhanced, 0, 255).astype(np.uint8)
        except Exception:
            return alpha
    
    def _scale_back_enhanced(self, result: Image.Image, target_size: Tuple[int, int],
                           quality_info: Dict[str, Any]) -> Image.Image:
        """Inteligentne przywracanie rozmiaru."""
        try:
            # Użyj lepszego resampling dla wysokiej jakości
            if quality_info.get('quality_score', 0.7) > 0.8:
                resampling = Image.Resampling.LANCZOS
            else:
                resampling = Image.Resampling.LANCZOS
            
            scaled_result = result.resize(target_size, resampling)
            
            # Lekkie sharpening po upscaling jeśli potrzeba
            current_size = result.size
            scale_factor = target_size[0] / current_size[0]
            
            if scale_factor > 1.5 and quality_info.get('blur_level', 200) < 100:
                try:
                    if scaled_result.mode == 'RGBA':
                        rgb = scaled_result.convert('RGB')
                        alpha = scaled_result.split()[-1]
                        
                        enhancer = ImageEnhance.Sharpness(rgb)
                        rgb = enhancer.enhance(1.1)
                        
                        scaled_result = Image.merge('RGBA', rgb.split() + (alpha,))
                except Exception:
                    pass  # Nie krytyczne
            
            return scaled_result
            
        except Exception as e:
            logger.error(f"Enhanced scaling back failed: {e}")
            return result.resize(target_size, Image.Resampling.LANCZOS)
    
    def _apply_background_enhanced(self, image: Image.Image, settings: Dict[str, Any]) -> Image.Image:
        """Ulepszone zastosowanie tła."""
        try:
            bg_mode = settings.get('bg_mode', 'remove')
            
            if bg_mode == 'color':
                bg_color = settings.get('bg_color', '#FFFFFF')
                
                # Parsuj kolor z lepszą obsługą błędów
                if isinstance(bg_color, str) and bg_color.startswith('#'):
                    hex_color = bg_color[1:]
                    if len(hex_color) == 6:
                        rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    elif len(hex_color) == 3:
                        rgb_color = tuple(int(hex_color[i], 16) * 17 for i in range(3))
                    else:
                        rgb_color = (255, 255, 255)
                else:
                    rgb_color = (255, 255, 255)
                
                # Utwórz tło z anty-aliasingiem
                background = Image.new('RGB', image.size, rgb_color)
                
                if image.mode == 'RGBA':
                    # Lekkie wygładzenie krawędzi alfa
                    alpha = image.split()[-1]
                    alpha_array = np.array(alpha)
                    alpha_array = cv2.GaussianBlur(alpha_array, (3, 3), 0.5)
                    alpha_smooth = Image.fromarray(alpha_array)
                    
                    background.paste(image, (0, 0), alpha_smooth)
                    return background
                else:
                    background.paste(image, (0, 0))
                    return background
                    
            elif bg_mode == 'image':
                bg_path = settings.get('bg_image')
                if bg_path and os.path.exists(bg_path):
                    try:
                        background = Image.open(bg_path).convert('RGB')
                        
                        # Inteligentne dopasowanie rozmiaru
                        if background.size != image.size:
                            background = self._smart_resize_background(background, image.size)
                        
                        if image.mode == 'RGBA':
                            alpha = image.split()[-1]
                            # Lekkie wygładzenie
                            alpha_array = np.array(alpha)
                            alpha_array = cv2.GaussianBlur(alpha_array, (3, 3), 0.5)
                            alpha_smooth = Image.fromarray(alpha_array)
                            
                            background.paste(image, (0, 0), alpha_smooth)
                            return background
                        else:
                            background.paste(image, (0, 0))
                            return background
                    except Exception as e:
                        logger.warning(f"Background image failed: {e}")
                        # Fallback to white
                        return self._apply_background_enhanced(image, {'bg_mode': 'color', 'bg_color': '#FFFFFF'})
            
            return image
            
        except Exception as e:
            logger.warning(f"Enhanced background application failed: {e}")
            return image
    
    def _smart_resize_background(self, background: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """Inteligentne dopasowanie tła."""
        try:
            bg_width, bg_height = background.size
            target_width, target_height = target_size
            
            # Oblicz współczynniki proporcji
            bg_ratio = bg_width / bg_height
            target_ratio = target_width / target_height
            
            if abs(bg_ratio - target_ratio) < 0.1:
                # Podobne proporcje - proste przeskalowanie
                return background.resize(target_size, Image.Resampling.LANCZOS)
            else:
                # Różne proporcje - przytnij i przeskaluj
                if bg_ratio > target_ratio:
                    # Tło szersze - przytnij szerokość
                    new_width = int(bg_height * target_ratio)
                    left = (bg_width - new_width) // 2
                    background = background.crop((left, 0, left + new_width, bg_height))
                else:
                    # Tło wyższe - przytnij wysokość
                    new_height = int(bg_width / target_ratio)
                    top = (bg_height - new_height) // 2
                    background = background.crop((0, top, bg_width, top + new_height))
                
                return background.resize(target_size, Image.Resampling.LANCZOS)
                
        except Exception:
            # Fallback do prostego resize
            return background.resize(target_size, Image.Resampling.LANCZOS)
    
    def _validate_result(self, result: Image.Image) -> bool:
        """Walidacja wyniku."""
        try:
            if result is None or not hasattr(result, 'mode'):
                return False
            
            if result.mode not in ['RGBA', 'RGB']:
                return False
            
            if not hasattr(result, 'size') or len(result.size) != 2:
                return False
            
            # Podstawowa walidacja dla RGBA
            if result.mode == 'RGBA':
                try:
                    alpha = np.array(result)[:, :, 3]
                    foreground_ratio = np.sum(alpha > 128) / alpha.size
                    
                    # Sprawdź czy jest sensowna ilość pierwszego planu
                    if not (0.05 <= foreground_ratio <= 0.95):
                        return False
                    
                    return True
                except Exception:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def cleanup(self):
        """Czyszczenie zasobów."""
        try:
            if hasattr(self, '_rembg_session'):
                self._rembg_session = None
            
            if hasattr(self, 'carvekit_interface'):
                del self.carvekit_interface
            
            # Wyczyść cache
            FastProductDetector.detect_product_type.cache_clear()
            
            gc.collect()
            
            logger.info("🧹 Optimized engine cleaned up")
            
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

class OptimizedImageEngine:
    """Zoptymalizowany silnik obrazów - główny interface."""
    
    def __init__(self):
        self.bg_remover = OptimizedBackgroundRemover()
        self.stats = {
            'processed': 0,
            'total_time': 0,
            'success_count': 0,
            'average_time': 0
        }
        logger.info("🚀 Optimized Image Engine initialized")
    
    def process_single(self, image, settings, progress_callback=None):
        """Główna metoda przetwarzania - kompatybilna z aplikacją."""
        start_time = time.time()
        
        try:
            original_size = image.size
            pixel_count = original_size[0] * original_size[1]
            
            logger.info(f"🎯 Processing: {image.mode}, {original_size} ({pixel_count:,} pixels)")
            
            if progress_callback:
                progress_callback(5, "Analyzing image...")
            
            # Główne przetwarzanie
            result = self.bg_remover.remove_background_optimized(image, settings)
            
            if progress_callback:
                progress_callback(100, "Completed!")
            
            # Aktualizuj statystyki
            processing_time = time.time() - start_time
            self._update_stats(processing_time, True)
            
            logger.info(f"✅ Processing completed: {result.mode}, {result.size} in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Process single failed: {e}")
            processing_time = time.time() - start_time
            self._update_stats(processing_time, False)
            
            # Awaryjny fallback
            return image.convert('RGBA') if image.mode != 'RGBA' else image
    
    def _update_stats(self, processing_time: float, success: bool):
        """Aktualizuje statystyki silnika."""
        try:
            self.stats['processed'] += 1
            self.stats['total_time'] += processing_time
            
            if success:
                self.stats['success_count'] += 1
            
            if self.stats['processed'] > 0:
                self.stats['average_time'] = self.stats['total_time'] / self.stats['processed']
                
        except Exception:
            pass  # Nie krytyczne
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Status silnika."""
        success_rate = self.stats['success_count'] / max(1, self.stats['processed'])
        
        return {
            'engine': 'Optimized CarveKit Engine',
            'version': '2.0-optimized',
            'processed': self.stats['processed'],
            'success_rate': f"{success_rate:.1%}",
            'average_time': f"{self.stats['average_time']:.2f}s",
            'carvekit_available': self.bg_remover.carvekit_available,
            'rembg_available': self.bg_remover.rembg_available,
            'features': [
                'Fast product detection',
                'Quality analysis',
                'Image enhancement', 
                'Intelligent fallback',
                'Product-specific processing'
            ]
        }
    
    def cleanup(self):
        """Czyszczenie zasobów."""
        try:
            self.bg_remover.cleanup()
            logger.info("📊 Final stats: {self.get_engine_status()}")
        except Exception as e:
            logger.warning(f"Engine cleanup failed: {e}")

# Backward compatibility alias
EnhancedImageEngine = OptimizedImageEngine

# Factory function - kompatybilna z aplikacją
def create_optimized_engine(max_workers=2):
    """Tworzy zoptymalizowany silnik - kompatybilny z aplikacją."""
    logger.info("🏗️ Creating Optimized CarveKit Engine")
    return OptimizedImageEngine()

# Test wydajności
def test_optimized_performance():
    """Test wydajności zoptymalizowanej wersji."""
    print("🚀 Optimized Performance Test with Quality Features")
    print("=" * 60)
    
    try:
        engine = create_optimized_engine()
        status = engine.get_engine_status()
        
        print(f"Engine: {status['engine']}")
        print(f"CarveKit: {status['carvekit_available']}")
        print(f"REMBG: {status['rembg_available']}")
        print(f"Features: {', '.join(status['features'])}")
        
        # Test różnych rozmiarów i typów
        test_scenarios = [
            ("Small bottle", (400, 600), {'bg_mode': 'remove'}),
            ("Medium box", (800, 800), {'bg_mode': 'color', 'bg_color': '#FF0000'}),
            ("Large round", (1200, 1000), {'bg_mode': 'remove'}),
            ("XL generic", (1600, 1200), {'bg_mode': 'color', 'bg_color': '#00FF00'})
        ]
        
        for name, size, settings in test_scenarios:
            print(f"\n🎯 Testing {name} ({size[0]}x{size[1]})")
            
            # Utwórz testowy obraz z wzorem
            test_image = Image.new('RGB', size, (100, 150, 200))
            
            # Dodaj wzór dla realistyczności
            import random
            pixels = test_image.load()
            for i in range(0, size[0], 20):
                for j in range(0, size[1], 20):
                    if random.random() > 0.7:
                        for di in range(min(15, size[0]-i)):
                            for dj in range(min(15, size[1]-j)):
                                pixels[i+di, j+dj] = (
                                    random.randint(50, 255),
                                    random.randint(50, 255), 
                                    random.randint(50, 255)
                                )
            
            def progress(p, s):
                print(f"  {p:3d}% - {s}")
            
            start_time = time.time()
            result = engine.process_single(test_image, settings, progress)
            end_time = time.time()
            
            print(f"✅ Result: {result.mode}, {result.size} in {end_time - start_time:.2f}s")
        
        # Pokaż finalne statystyki
        final_status = engine.get_engine_status()
        print(f"\n📊 Final Performance Stats:")
        print(f"Total processed: {final_status['processed']}")
        print(f"Success rate: {final_status['success_rate']}")
        print(f"Average time: {final_status['average_time']}")
        
        engine.cleanup()
        print("\n✅ Optimized performance test completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Uruchom test wydajności
    success = test_optimized_performance()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 OPTIMIZED CARVEKIT ENGINE READY!")
        print("=" * 60)
        print("Features included:")
        print("✅ Fast product type detection") 
        print("✅ Quality analysis and enhancement")
        print("✅ Intelligent scaling and timeout")
        print("✅ Product-specific post-processing")
        print("✅ Advanced background application")
        print("✅ Smart fallback methods")
        print("✅ Memory optimization")
        print("✅ Full application compatibility")
        print("=" * 60)