"""
Windows Enhanced AI Engine for background removal - IMPROVED VERSION
Combines REMBG AI models with GPU-accelerated traditional CV methods for optimal results
Focuses on fine detail preservation and edge quality
"""

import os
import logging
import numpy as np
import cv2
from PIL import Image, ImageFilter, ImageEnhance
from pathlib import Path
import time

# AI libraries with proper error handling
try:
    from rembg import remove, new_session
    HAS_REMBG = True
    logger.info("✅ REMBG available")
except ImportError:
    HAS_REMBG = False
    logger.warning("❌ REMBG not available")

try:
    from carvekit.api.high import HiInterface
    HAS_CARVEKIT = True
    logger.info("✅ CarveKit available") 
except ImportError:
    HAS_CARVEKIT = False
    logger.warning("❌ CarveKit not available")

try:
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

logger = logging.getLogger(__name__)

class WindowsImageEngine:
    """Enhanced Windows Image Engine with improved detail preservation"""
    
    def __init__(self):
        logger.info("🚀 Windows Enhanced AI Engine Initializing")
        self.name = "Windows Enhanced AI Engine"
        
        # Check CUDA first
        self.has_gpu = self._check_gpu_available()
        if self.has_gpu:
            logger.info("✅ CUDA GPU available - enabling GPU acceleration")
        else:
            logger.info("⚠️ No GPU detected - using CPU mode")
        
        # Initialize models
        self._init_ai_models()
        
        # Processing statistics
        self.processing_stats = {
            'processed': 0,
            'success_ai': 0, 
            'success_traditional': 0,
            'total_time': 0,
            'avg_quality_score': 0.0,
            'gpu_enabled': self.has_gpu
        }

    def _init_ai_models(self):
        """Initialize AI models with Windows-optimized settings"""
        self.rembg_sessions = {}
        self.carvekit_interface = None
        
        # Initialize multiple REMBG models for ensemble with error handling
        if HAS_REMBG:
            models_to_init = {
                'u2net': 0.4,         # Best general purpose - higher weight
                'isnet-general-use': 0.4, # Best for details - higher weight
                'silueta': 0.2,       # Best for edges - supplementary
            }
            
            for model_name, weight in models_to_init.items():
                try:
                    self.rembg_sessions[model_name] = {
                        'session': new_session(model_name),
                        'weight': weight
                    }
                    logger.info(f"✅ REMBG {model_name} initialized (weight: {weight})")
                except Exception as e:
                    logger.error(f"❌ REMBG {model_name} failed: {e}")
                    
        # Initialize CarveKit with optimized settings
        if HAS_CARVEKIT:
            try:
                device = 'cuda' if self.has_gpu else 'cpu'
                batch_size = 4 if self.has_gpu else 1
                self.carvekit_interface = HiInterface(
                    object_type="object",
                    batch_size_seg=batch_size,
                    batch_size_matting=batch_size,
                    device=device,
                    seg_mask_size=1024,  # Increased for better quality
                    matting_mask_size=2048,
                    trimap_prob_threshold=231,
                    trimap_dilation=30,
                    fp16=self.has_gpu,
                    models={
                        "segmentation": ["u2net"],
                        "matting": ["fba"]
                    }
                )
                logger.info(f"✅ CarveKit initialized on {device}")
            except Exception as e:
                logger.error(f"❌ CarveKit failed: {e}")
                self.carvekit_interface = None
        
        # Verify we have at least one working model
        if not self.rembg_sessions and not self.carvekit_interface:
            logger.warning("⚠️ No AI models available - will use traditional methods")

    def _check_gpu_available(self):
        """Check if CUDA GPU is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def process_single(self, image, settings=None, progress_callback=None, **kwargs):
        """Main processing method with improved quality"""
        start_time = time.time()
        
        try:
            logger.info(f"Windows Enhanced Engine - Processing: {image.mode}, {image.size}")
            
            if progress_callback:
                progress_callback(10, "Analyzing image...")
            
            # Convert to RGBA if needed
            original_mode = image.mode
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
                logger.info(f"Converted from {original_mode} to RGBA")
            
            if progress_callback:
                progress_callback(20, "Selecting optimal method...")
            
            # Analyze image to choose best method
            method = self._choose_optimal_method(image, settings)
            logger.info(f"Selected method: {method}")
            
            if progress_callback:
                progress_callback(30, f"Processing with {method}...")
            
            # Process with selected method
            if method == 'ai_ensemble':
                result = self._ai_ensemble_removal(image, progress_callback)
            elif method == 'carvekit':
                result = self._carvekit_removal(image, progress_callback)
            elif method == 'rembg_best':
                result = self._rembg_best_removal(image, progress_callback)
            else:
                result = self._enhanced_traditional_removal(image, progress_callback)
            
            if progress_callback:
                progress_callback(85, "Enhancing details...")
            
            # Post-process for better details
            result = self._enhance_details(result, image, settings)
            
            if progress_callback:
                progress_callback(100, "Completed!")
            
            # Update stats
            processing_time = time.time() - start_time
            self.processing_stats['processed'] += 1
            self.processing_stats['total_time'] += processing_time
            
            if method.startswith('ai') or method == 'carvekit':
                self.processing_stats['success_ai'] += 1
            else:
                self.processing_stats['success_traditional'] += 1
            
            logger.info(f"Processing completed in {processing_time:.2f}s using {method}")
            self._log_quality_metrics(result, image)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Windows Enhanced Engine: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return image.convert('RGBA')

    def _choose_optimal_method(self, image, settings):
        """Choose optimal processing method based on image analysis"""
        img_array = np.array(image.convert('RGB'))
        h, w = img_array.shape[:2]
        
        # Quality preference from settings
        quality = settings.get('bg_quality', 'high') if settings else 'high'
        
        # Image complexity analysis
        complexity = self._analyze_image_complexity(img_array)
        
        # Choose method based on complexity and quality settings
        if quality == 'ultra_high' and complexity['is_complex']:
            if self.carvekit_interface:
                return 'carvekit'
            elif len(self.rembg_sessions) >= 2:
                return 'ai_ensemble'
            elif 'u2net' in self.rembg_sessions:
                return 'rembg_best'
        elif quality in ['high', 'ultra_high']:
            if 'u2net' in self.rembg_sessions or 'isnet-general-use' in self.rembg_sessions:
                return 'rembg_best'
            elif self.carvekit_interface:
                return 'carvekit'
        
        return 'enhanced_traditional'

    def _analyze_image_complexity(self, img_array):
        """Analyze image complexity to choose optimal method"""
        h, w = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Edge density
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (h * w)
        
        # Color variance
        color_variance = np.var(img_array.reshape(-1, 3), axis=0).mean()
        
        # Texture analysis
        texture = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Background uniformity
        corners = [
            img_array[:50, :50],
            img_array[:50, -50:],
            img_array[-50:, :50],
            img_array[-50:, -50:]
        ]
        corner_variance = np.var([np.mean(corner) for corner in corners])
        
        complexity = {
            'edge_density': edge_density,
            'color_variance': color_variance,
            'texture': texture,
            'corner_variance': corner_variance,
            'is_complex': edge_density > 0.1 or color_variance > 1000 or texture > 500
        }
        
        logger.info(f"Image complexity: {complexity}")
        return complexity

    def _ai_ensemble_removal(self, image, progress_callback=None):
        """Use multiple AI models and combine results"""
        logger.info("Using AI ensemble method")
        
        results = []
        weights = []
        
        # Try different models
        model_priorities = ['u2net', 'isnet-general-use', 'silueta']
        
        for i, model_name in enumerate(model_priorities):
            if model_name in self.rembg_sessions:
                try:
                    if progress_callback:
                        progress_callback(40 + i * 15, f"Processing with {model_name}...")
                    
                    result = self._rembg_with_model(image, model_name)
                    if self._validate_ai_result(result):
                        results.append(result)
                        # Weights based on model quality for detail preservation
                        model_weights = {'u2net': 0.4, 'isnet-general-use': 0.4, 'silueta': 0.2}
                        weights.append(model_weights.get(model_name, 0.3))
                        logger.info(f"✅ {model_name} succeeded")
                    else:
                        logger.warning(f"❌ {model_name} result validation failed")
                except Exception as e:
                    logger.error(f"❌ {model_name} failed: {e}")
        
        if len(results) >= 2:
            # Ensemble fusion
            return self._ensemble_fusion(results, weights, image)
        elif results:
            return results[0]
        else:
            return self._enhanced_traditional_removal(image, progress_callback)

    def _rembg_best_removal(self, image, progress_callback=None):
        """Use best available REMBG model"""
        logger.info("Using best REMBG model")
        
        # Priority order for quality
        model_priority = ['isnet-general-use', 'u2net', 'silueta']
        
        for model_name in model_priority:
            if model_name in self.rembg_sessions:
                try:
                    if progress_callback:
                        progress_callback(50, f"Processing with {model_name}...")
                    
                    result = self._rembg_with_model(image, model_name)
                    if self._validate_ai_result(result):
                        logger.info(f"✅ {model_name} succeeded")
                        return result
                except Exception as e:
                    logger.error(f"❌ {model_name} failed: {e}")
        
        # Fallback
        return self._enhanced_traditional_removal(image, progress_callback)

    def _carvekit_removal(self, image, progress_callback=None):
        """Use CarveKit for highest quality"""
        logger.info("Using CarveKit method")
        
        try:
            if progress_callback:
                progress_callback(50, "Processing with CarveKit AI...")
            
            # Convert to RGB for CarveKit
            rgb_image = image.convert('RGB')
            
            # Process with CarveKit
            result_images = self.carvekit_interface([rgb_image])
            result = result_images[0]
            
            if self._validate_ai_result(result):
                logger.info("✅ CarveKit succeeded")
                return result
            else:
                logger.warning("❌ CarveKit result validation failed")
                return self._rembg_best_removal(image, progress_callback)
                
        except Exception as e:
            logger.error(f"❌ CarveKit failed: {e}")
            return self._rembg_best_removal(image, progress_callback)

    def _rembg_with_model(self, image, model_name):
        """Process with specific REMBG model"""
        if model_name not in self.rembg_sessions:
            raise ValueError(f"Model {model_name} not available")
        
        # Use the session directly
        session = self.rembg_sessions[model_name]['session']
        rgb_image = image.convert('RGB')
        
        # Process with REMBG
        result = remove(rgb_image, session=session)
        return result

    def _ensemble_fusion(self, results, weights, original_image):
        """Intelligent ensemble fusion with edge preservation"""
        try:
            if len(results) == 1:
                return results[0]

            # Convert results to numpy arrays with edge detection
            masks = []
            edges = []
            for result in results:
                # Get alpha channel
                if result.mode == 'RGBA':
                    mask = np.array(result)[:, :, 3]
                else:
                    gray = np.array(result.convert('L'))
                    mask = (gray > 128).astype(np.uint8) * 255
                
                # Detect edges in mask
                edges.append(cv2.Canny(mask, 50, 150))
                masks.append(mask)

            # Weighted average base
            weights = np.array(weights) / np.sum(weights)
            combined_mask = np.zeros_like(masks[0], dtype=np.float32)
            
            for mask, weight in zip(masks, weights):
                combined_mask += mask.astype(np.float32) * weight

            # Edge refinement
            edge_mask = np.zeros_like(combined_mask)
            for edge in edges:
                edge_mask = np.maximum(edge_mask, edge)
            
            # Preserve edges in final mask
            kernel = np.ones((3,3), np.uint8)
            dilated_edges = cv2.dilate(edge_mask, kernel, iterations=1)
            edge_pixels = dilated_edges > 0
            
            # Smart edge handling
            combined_mask[edge_pixels] = np.max([mask[edge_pixels] for mask in masks], axis=0)
            
            # Final cleanup
            final_mask = np.clip(combined_mask, 0, 255).astype(np.uint8)
            
            # Reconstruct with original RGB
            original_rgb = np.array(original_image.convert('RGB'))
            result_array = np.dstack([original_rgb, final_mask])
            
            return Image.fromarray(result_array)
            
        except Exception as e:
            logger.error(f"Ensemble fusion failed: {e}")
            # Return best individual result as fallback
            return max(results, key=lambda x: np.mean(np.array(x.split()[-1])))

    def _enhanced_traditional_removal(self, image, progress_callback=None):
        """Enhanced traditional methods with better detail preservation"""
        logger.info("Using enhanced traditional methods")
        
        img_array = np.array(image.convert('RGB'))
        h, w = img_array.shape[:2]
        
        if progress_callback:
            progress_callback(40, "Analyzing image structure...")
        
        # Multi-method approach
        methods = [
            self._smart_grabcut,
            self._advanced_edge_detection,
            self._color_based_segmentation
        ]
        
        best_mask = None
        best_score = 0
        
        for i, method in enumerate(methods):
            try:
                if progress_callback:
                    progress_callback(45 + i * 10, f"Trying method {i+1}...")
                
                mask = method(img_array)
                score = self._evaluate_mask_quality(mask, img_array)
                
                if score > best_score:
                    best_mask = mask
                    best_score = score
                    
            except Exception as e:
                logger.warning(f"Method {i+1} failed: {e}")
        
        if best_mask is None:
            logger.warning("All traditional methods failed, using fallback")
            best_mask = self._fallback_mask(img_array)
        
        # Apply advanced post-processing
        best_mask = self._enhance_mask_details(best_mask, img_array)
        
        # Combine with original
        result_array = np.dstack([img_array, best_mask])
        return Image.fromarray(result_array)

    def _smart_grabcut(self, img_array):
        """Improved GrabCut with better initialization"""
        h, w = img_array.shape[:2]
        
        # Smart rectangle initialization
        # Analyze image to find likely object center
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours to get object bounds
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Use largest contour as guide
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, rect_w, rect_h = cv2.boundingRect(largest_contour)
            
            # Add padding
            padding = 20
            rect = (max(0, x - padding), max(0, y - padding), 
                   min(w, rect_w + 2 * padding), min(h, rect_h + 2 * padding))
        else:
            # Fallback to center rectangle
            rect = (w//6, h//6, 2*w//3, 2*h//3)
        
        # Initialize GrabCut
        mask = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        # Run GrabCut
        cv2.grabCut(img_array, mask, rect, bgd_model, fgd_model, 8, cv2.GC_INIT_WITH_RECT)
        
        # Extract foreground
        mask2 = np.where((mask == 2) | (mask == 0), 0, 255).astype('uint8')
        
        return mask2

    def _advanced_edge_detection(self, img_array):
        """Advanced edge-based segmentation"""
        h, w = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Multi-scale edge detection
        edges = np.zeros_like(gray)
        
        for sigma in [0.5, 1.0, 2.0]:
            blurred = cv2.GaussianBlur(gray, (0, 0), sigma)
            edge = cv2.Canny(blurred, 50, 150)
            edges = cv2.bitwise_or(edges, edge)
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
        edges = cv2.morphologyEx(edges, cv2.MORPH_DILATE, kernel, iterations=1)
        
        # Fill holes
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask = np.zeros((h, w), dtype=np.uint8)
        
        if contours:
            # Filter and fill significant contours
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > (h * w) * 0.01:  # At least 1% of image
                    cv2.fillPoly(mask, [contour], 255)
        
        return mask

    def _color_based_segmentation(self, img_array):
        """Advanced color-based segmentation with clustering"""
        h, w = img_array.shape[:2]
        
        if HAS_SKLEARN:
            # Use K-means clustering
            pixels = img_array.reshape(-1, 3).astype(np.float32)
            
            # Cluster into foreground and background
            kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
            labels = kmeans.fit_predict(pixels)
            
            # Determine which cluster is background (usually corners)
            corner_labels = []
            corner_size = min(50, h//10, w//10)
            corners = [
                labels[:corner_size * corner_size],  # Top-left
                labels[w * corner_size - corner_size * corner_size:w * corner_size],  # Top-right
                labels[-w * corner_size:-w * corner_size + corner_size * corner_size],  # Bottom-left
                labels[-corner_size * corner_size:]  # Bottom-right
            ]
            
            # Most common label in corners is likely background
            corner_labels = np.concatenate(corners)
            bg_label = np.bincount(corner_labels).argmax()
            
            # Create mask
            mask = (labels != bg_label).astype(np.uint8) * 255
            mask = mask.reshape(h, w)
            
        else:
            # Fallback to simple thresholding
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 21, 4)
        
        return mask

    def _enhance_mask_details(self, mask, img_array):
        """Enhance mask details and edges"""
        # Bilateral filter for edge preservation
        mask_smooth = cv2.bilateralFilter(mask, 9, 75, 75)
        
        # Edge refinement
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Combine mask with edges for better boundaries
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edges_dilated = cv2.dilate(edges, kernel, iterations=1)
        
        # Apply edge guidance
        mask_enhanced = np.where(edges_dilated > 0, mask, mask_smooth)
        
        # Final smoothing
        mask_enhanced = cv2.medianBlur(mask_enhanced, 3)
        
        return mask_enhanced

    def _enhance_details(self, result, original_image, settings):
        """Enhanced detail preservation with smart edge handling"""
        if not result or result.mode != 'RGBA':
            return result
            
        try:
            # Extract channels
            result_array = np.array(result)
            alpha = result_array[:, :, 3]
            
            # Edge-aware enhancement
            if settings and settings.get('enhance_details', True):
                # Multi-scale detail enhancement
                scales = [0.5, 1.0, 2.0]
                enhanced_alpha = np.zeros_like(alpha, dtype=np.float32)
                
                for scale in scales:
                    # Gaussian pyramid detail extraction
                    blurred = cv2.GaussianBlur(alpha.astype(np.float32), (0,0), scale)
                    detail = alpha.astype(np.float32) - blurred
                    enhanced_alpha += detail
                
                # Normalize and apply
                enhanced_alpha = alpha + enhanced_alpha * 0.5
                enhanced_alpha = np.clip(enhanced_alpha, 0, 255).astype(np.uint8)
                
                # Update alpha channel
                result_array[:, :, 3] = enhanced_alpha
                result = Image.fromarray(result_array)
            
            # Apply edge refinement if requested
            edge_refinement = settings.get('edge_refinement', 0) if settings else 0
            if edge_refinement > 0:
                edge_kernel = np.ones((3,3), np.uint8)
                refined_alpha = cv2.morphologyEx(enhanced_alpha, cv2.MORPH_CLOSE, edge_kernel)
                result_array[:, :, 3] = refined_alpha
                result = Image.fromarray(result_array)
            
            # Apply feathering if requested
            feather = settings.get('feathering', 0) if settings else 0
            if feather > 0:
                result = self._apply_feathering(result, feather)
                
            return result
            
        except Exception as e:
            logger.error(f"Detail enhancement failed: {e}")
            return result

    def _apply_feathering(self, image, feather_radius):
        """Apply edge feathering for softer edges"""
        if feather_radius <= 0:
            return image
        
        # Extract alpha and apply Gaussian blur
        alpha = image.split()[-1]
        feathered_alpha = alpha.filter(ImageFilter.GaussianBlur(radius=feather_radius))
        
        # Recombine
        rgb = image.convert('RGB')
        return Image.merge('RGBA', rgb.split() + (feathered_alpha,))

    def _validate_ai_result(self, result):
        """Validate AI processing result"""
        try:
            if result is None or not hasattr(result, 'mode'):
                return False
            
            if result.mode not in ['RGBA', 'RGB']:
                return False
            
            # Check if result has transparency
            if result.mode == 'RGBA':
                alpha = np.array(result)[:, :, 3]
                foreground_ratio = np.sum(alpha > 128) / alpha.size
                
                # Should have reasonable amount of foreground (5-95%)
                if not (0.05 <= foreground_ratio <= 0.95):
                    return False
            
            return True
            
        except Exception:
            return False

    def _evaluate_mask_quality(self, mask, img_array):
        """Evaluate quality of generated mask"""
        try:
            # Check if mask has reasonable content
            if mask is None or mask.size == 0:
                return 0.0
            
            # Foreground ratio
            foreground_ratio = np.sum(mask > 128) / mask.size
            if not (0.05 <= foreground_ratio <= 0.95):
                return 0.0
            
            # Edge alignment score
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            mask_edges = cv2.Canny(mask, 50, 150)
            
            # Calculate overlap
            edge_overlap = np.sum((edges > 0) & (mask_edges > 0))
            total_edges = np.sum(edges > 0) + np.sum(mask_edges > 0) - edge_overlap
            
            if total_edges > 0:
                edge_score = edge_overlap / total_edges
            else:
                edge_score = 0.0
            
            # Combined score
            return 0.6 * (1.0 - abs(foreground_ratio - 0.5)) + 0.4 * edge_score
            
        except Exception:
            return 0.0

    def _fallback_mask(self, img_array):
        """Create basic fallback mask"""
        h, w = img_array.shape[:2]
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Simple threshold
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Basic morphology
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        return mask

    def _log_quality_metrics(self, result, original):
        """Log quality metrics for monitoring"""
        try:
            if result.mode == 'RGBA':
                alpha = np.array(result)[:, :, 3]
                transparent_pixels = np.sum(alpha < 255)
                total_pixels = alpha.size
                transparency_ratio = transparent_pixels / total_pixels
                
                logger.info(f"Quality metrics: {transparency_ratio:.1%} transparency, "
                          f"{result.size} output size")
        except Exception:
            pass

    def get_processing_stats(self):
        """Get processing statistics"""
        stats = self.processing_stats.copy()
        if stats['processed'] > 0:
            stats['average_time'] = stats['total_time'] / stats['processed']
            stats['ai_success_rate'] = stats['success_ai'] / stats['processed']
            stats['traditional_success_rate'] = stats['success_traditional'] / stats['processed']
        
        return stats

def create_windows_engine():
    """Create Windows enhanced engine"""
    return WindowsImageEngine()