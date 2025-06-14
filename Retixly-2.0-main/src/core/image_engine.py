"""
Professional Background Removal Engine for E-commerce
Ultra-high quality background removal optimized for product photography
"""

import os
import numpy as np
import cv2
from PIL import Image, ImageFilter, ImageEnhance
from pathlib import Path
import logging
from typing import Optional, Tuple, Dict, Any, List
import tempfile
from concurrent.futures import ThreadPoolExecutor
import time

# Advanced imports with fallbacks
try:
    from rembg import remove, new_session
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

try:
    import torch
    import torchvision.transforms as transforms
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    from scipy import ndimage, signal
    from scipy.spatial.distance import cdist
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

logger = logging.getLogger(__name__)


class ProductBackgroundRemover:
    """
    Ultra-high quality background removal specifically optimized for e-commerce product photography.
    Combines multiple advanced algorithms for maximum precision.
    """
    
    def __init__(self):
        self.models = {}
        self.initialize_models()
        
    def initialize_models(self):
        """Initialize all available AI models for background removal."""
        if HAS_REMBG:
            try:
                # Initialize best models for product photography
                self.models['u2net'] = new_session('u2net')  # Best general purpose
                self.models['silueta'] = new_session('silueta')  # Best for complex edges
                self.models['isnet'] = new_session('isnet-general-use')  # Best for fine details
                logger.info("✅ Initialized all rembg models successfully")
            except Exception as e:
                logger.warning(f"⚠️ Some rembg models failed to initialize: {e}")
                # Fallback to basic rembg
                self.models['basic'] = None
                
    def remove_background_professional(self, image: Image.Image, 
                                     quality_level: str = "ultra_high",
                                     preserve_holes: bool = True,
                                     edge_refinement: bool = True) -> Image.Image:
        """
        Professional background removal with multiple quality levels.
        
        Args:
            image: Input PIL Image
            quality_level: ignored, always uses ultra_high for product photos
            preserve_holes: always True for product photos
            edge_refinement: always True for product photos
            
        Returns:
            PIL Image with professionally removed background
        """
        # Wymuś ultra-high quality i zaawansowane post-processing
        from .carvekit_engine import OptimizedBackgroundRemover
        remover = OptimizedBackgroundRemover()
        settings = {
            'bg_mode': 'remove',
            'bg_quality': 'ultra_high',
            'preserve_holes': True,
            'edge_refinement': True
        }
        return remover.remove_background_optimized(image, settings)

    def _ultra_high_quality_removal(self, image: Image.Image, preserve_holes: bool) -> Image.Image:
        """Ultra-high quality removal using ensemble of best models."""
        logger.info("🎯 Applying ultra-high quality removal...")
        
        if not HAS_REMBG:
            return self._advanced_traditional_removal(image, preserve_holes)
        
        # Step 1: Get results from multiple models
        results = []
        confidence_scores = []
        
        # U2Net - Best general purpose
        if 'u2net' in self.models:
            try:
                u2net_result = self._rembg_with_model(image, 'u2net')
                results.append(u2net_result)
                confidence_scores.append(0.4)  # Weight for u2net
            except Exception as e:
                logger.warning(f"U2Net failed: {e}")
        
        # Silueta - Best for complex edges
        if 'silueta' in self.models:
            try:
                silueta_result = self._rembg_with_model(image, 'silueta')
                results.append(silueta_result)
                confidence_scores.append(0.3)  # Weight for silueta
            except Exception as e:
                logger.warning(f"Silueta failed: {e}")
        
        # ISNet - Best for fine details
        if 'isnet' in self.models:
            try:
                isnet_result = self._rembg_with_model(image, 'isnet')
                results.append(isnet_result)
                confidence_scores.append(0.3)  # Weight for isnet
            except Exception as e:
                logger.warning(f"ISNet failed: {e}")
        
        if not results:
            # Fallback to basic rembg
            return self._basic_rembg_removal(image)
        
        # Step 2: Ensemble fusion - combine results intelligently
        final_result = self._ensemble_fusion(results, confidence_scores, image)
        
        # Step 3: Hole preservation if requested
        if preserve_holes:
            final_result = self._preserve_product_holes(final_result, image)
        
        return final_result

    def _high_quality_removal(self, image: Image.Image, preserve_holes: bool) -> Image.Image:
        """High quality removal using best single model + refinements."""
        logger.info("🎯 Applying high quality removal...")
        
        if not HAS_REMBG:
            return self._advanced_traditional_removal(image, preserve_holes)
        
        # Use best available model
        if 'u2net' in self.models:
            result = self._rembg_with_model(image, 'u2net')
        elif 'isnet' in self.models:
            result = self._rembg_with_model(image, 'isnet')
        else:
            result = self._basic_rembg_removal(image)
        
        # Apply advanced post-processing
        result = self._advanced_mask_refinement(result, image)
        
        if preserve_holes:
            result = self._preserve_product_holes(result, image)
            
        return result

    def _medium_quality_removal(self, image: Image.Image) -> Image.Image:
        """Medium quality removal - balanced speed/quality."""
        logger.info("🎯 Applying medium quality removal...")
        
        if HAS_REMBG and 'u2net' in self.models:
            return self._rembg_with_model(image, 'u2net')
        else:
            return self._basic_rembg_removal(image)

    def _fast_quality_removal(self, image: Image.Image) -> Image.Image:
        """Fast removal for quick previews."""
        logger.info("🎯 Applying fast quality removal...")
        return self._basic_rembg_removal(image)

    def _rembg_with_model(self, image: Image.Image, model_name: str) -> Image.Image:
        """Apply rembg with specific model."""
        try:
            img_array = np.array(image)
            
            if model_name in self.models and self.models[model_name]:
                result_array = remove(img_array, session=self.models[model_name])
            else:
                # Fallback to basic rembg
                result_array = remove(img_array)
            
            return Image.fromarray(result_array)
            
        except Exception as e:
            logger.error(f"Rembg {model_name} failed: {e}")
            raise

    def _basic_rembg_removal(self, image: Image.Image) -> Image.Image:
        """Basic rembg removal without specific model."""
        try:
            if HAS_REMBG:
                img_array = np.array(image)
                result_array = remove(img_array)
                return Image.fromarray(result_array)
            else:
                return self._advanced_traditional_removal(image, False)
        except Exception as e:
            logger.error(f"Basic rembg failed: {e}")
            return self._advanced_traditional_removal(image, False)

    def _ensemble_fusion(self, results: List[Image.Image], 
                        confidence_scores: List[float], 
                        original: Image.Image) -> Image.Image:
        """
        Intelligently fuse multiple background removal results.
        Uses weighted voting on pixel level with confidence scores.
        """
        logger.info("🔀 Fusing ensemble results...")
        
        if len(results) == 1:
            return results[0]
        
        # Normalize confidence scores
        total_confidence = sum(confidence_scores)
        weights = [score / total_confidence for score in confidence_scores]
        
        # Convert results to arrays
        result_arrays = [np.array(result) for result in results]
        
        # Get alpha channels
        alpha_channels = []
        for result_array in result_arrays:
            if result_array.shape[2] == 4:
                alpha_channels.append(result_array[:, :, 3])
            else:
                # If no alpha, create one from luminance
                gray = cv2.cvtColor(result_array, cv2.COLOR_RGB2GRAY)
                alpha_channels.append(gray)
        
        # Weighted fusion of alpha channels
        fused_alpha = np.zeros_like(alpha_channels[0], dtype=np.float32)
        for alpha, weight in zip(alpha_channels, weights):
            fused_alpha += alpha.astype(np.float32) * weight
        
        # Apply advanced fusion rules
        fused_alpha = self._apply_fusion_rules(fused_alpha, alpha_channels, weights)
        
        # Create final result
        original_array = np.array(original)
        if original_array.shape[2] == 3:
            result_array = np.dstack([original_array, fused_alpha.astype(np.uint8)])
        else:
            result_array = original_array.copy()
            result_array[:, :, 3] = fused_alpha.astype(np.uint8)
        
        return Image.fromarray(result_array)

    def _apply_fusion_rules(self, fused_alpha: np.ndarray, 
                           alpha_channels: List[np.ndarray], 
                           weights: List[float]) -> np.ndarray:
        """Apply intelligent fusion rules for better results."""
        
        # Rule 1: If all models agree on background (low alpha), keep it background
        all_low = np.all([alpha < 50 for alpha in alpha_channels], axis=0)
        fused_alpha[all_low] = 0
        
        # Rule 2: If all models agree on foreground (high alpha), keep it foreground
        all_high = np.all([alpha > 200 for alpha in alpha_channels], axis=0)
        fused_alpha[all_high] = 255
        
        # Rule 3: For disagreement areas, use edge-aware fusion
        disagreement = ~(all_low | all_high)
        if np.any(disagreement):
            fused_alpha = self._edge_aware_fusion(fused_alpha, alpha_channels, weights, disagreement)
        
        return fused_alpha

    def _edge_aware_fusion(self, fused_alpha: np.ndarray, 
                          alpha_channels: List[np.ndarray], 
                          weights: List[float],
                          disagreement_mask: np.ndarray) -> np.ndarray:
        """Apply edge-aware fusion in disagreement areas."""
        
        # Calculate edge strength for each alpha channel
        edge_strengths = []
        for alpha in alpha_channels:
            edges = cv2.Canny(alpha.astype(np.uint8), 50, 150)
            edge_strength = cv2.GaussianBlur(edges.astype(np.float32), (5, 5), 2.0)
            edge_strengths.append(edge_strength)
        
        # In disagreement areas, favor results with stronger edges
        disagreement_coords = np.where(disagreement)
        for y, x in zip(disagreement_coords[0], disagreement_coords[1]):
            local_edge_strengths = [edges[y, x] for edges in edge_strengths]
            
            # Reweight based on edge strength
            if max(local_edge_strengths) > 10:  # Significant edge present
                edge_weights = np.array(local_edge_strengths) + 1  # Avoid division by zero
                edge_weights = edge_weights / np.sum(edge_weights)
                
                # Combine original weights with edge weights
                combined_weights = np.array(weights) * edge_weights
                combined_weights = combined_weights / np.sum(combined_weights)
                
                # Recalculate fused value
                fused_value = sum(alpha[y, x] * w for alpha, w in zip(alpha_channels, combined_weights))
                fused_alpha[y, x] = fused_value
        
        return fused_alpha

    def _preserve_product_holes(self, result: Image.Image, original: Image.Image) -> Image.Image:
        """
        Preserve holes in products (jewelry, handles, cutouts etc.)
        Uses advanced hole detection and preservation algorithms.
        """
        logger.info("🕳️ Preserving product holes...")
        
        result_array = np.array(result)
        original_array = np.array(original)
        
        if result_array.shape[2] != 4:
            return result  # No alpha channel
        
        alpha = result_array[:, :, 3]
        
        # Detect holes using multiple methods
        holes_mask = self._detect_product_holes(original_array, alpha)
        
        if np.any(holes_mask):
            # Apply hole mask to alpha channel
            alpha[holes_mask] = 0
            result_array[:, :, 3] = alpha
            
            logger.info(f"✅ Preserved {np.sum(holes_mask)} hole pixels")
        
        return Image.fromarray(result_array)

    def _detect_product_holes(self, original: np.ndarray, alpha: np.ndarray) -> np.ndarray:
        """Detect holes that should be preserved in the product."""
        
        # Method 1: Dark regions inside the product
        gray = cv2.cvtColor(original, cv2.COLOR_RGB2GRAY)
        dark_regions = gray < 50  # Very dark pixels
        
        # Method 2: Enclosed regions (topological holes)
        # Find the product mask
        product_mask = alpha > 128
        
        # Fill holes in product mask to find what should be holes
        filled_mask = cv2.morphologyEx(
            product_mask.astype(np.uint8), 
            cv2.MORPH_CLOSE, 
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        )
        
        # Holes are areas that are filled but weren't originally product
        holes_topo = (filled_mask == 1) & (product_mask == False)
        
        # Method 3: Edge-based hole detection
        edges = cv2.Canny(gray, 30, 100)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        holes_edge = np.zeros_like(gray, dtype=bool)
        for contour in contours:
            area = cv2.contourArea(contour)
            if 50 < area < 10000:  # Hole size range
                # Check if it's inside the product
                mask = np.zeros_like(gray)
                cv2.fillPoly(mask, [contour], 255)
                
                # If most of the contour area overlaps with product, it might be a hole
                overlap = np.sum((mask > 0) & product_mask) / np.sum(mask > 0)
                if overlap > 0.7:
                    holes_edge |= (mask > 0)
        
        # Combine all hole detection methods
        combined_holes = dark_regions | holes_topo | holes_edge
        
        # Filter out noise - only keep holes that are reasonably sized
        combined_holes = self._filter_hole_noise(combined_holes)
        
        return combined_holes

    def _filter_hole_noise(self, holes_mask: np.ndarray) -> np.ndarray:
        """Filter out noise from hole detection."""
        
        # Remove very small holes (noise)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        filtered = cv2.morphologyEx(holes_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
        
        # Remove very large holes (probably not real holes)
        contours, _ = cv2.findContours(filtered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        final_holes = np.zeros_like(holes_mask)
        for contour in contours:
            area = cv2.contourArea(contour)
            if 10 < area < 5000:  # Reasonable hole size
                cv2.fillPoly(final_holes, [contour], True)
        
        return final_holes

    def _refine_edges_advanced(self, result: Image.Image, original: Image.Image) -> Image.Image:
        """Apply advanced edge refinement algorithms."""
        logger.info("✨ Applying advanced edge refinement...")
        
        result_array = np.array(result)
        original_array = np.array(original)
        
        if result_array.shape[2] != 4:
            return result
        
        alpha = result_array[:, :, 3].astype(np.float32)
        
        # Step 1: Guided filter for edge-preserving smoothing
        alpha = self._guided_filter_alpha(alpha, original_array)
        
        # Step 2: Bilateral filter for noise reduction while preserving edges
        alpha = cv2.bilateralFilter(alpha.astype(np.uint8), 9, 75, 75).astype(np.float32)
        
        # Step 3: Edge-aware smoothing in transition zones
        alpha = self._edge_aware_smoothing(alpha, original_array)
        
        # Step 4: Anti-aliasing improvement
        alpha = self._improve_antialiasing(alpha, original_array)
        
        result_array[:, :, 3] = alpha.astype(np.uint8)
        return Image.fromarray(result_array)

    def _guided_filter_alpha(self, alpha: np.ndarray, guide: np.ndarray) -> np.ndarray:
        """Apply guided filter using original image as guide."""
        if not HAS_SCIPY:
            return alpha
        
        # Convert guide to grayscale
        if len(guide.shape) == 3:
            guide_gray = cv2.cvtColor(guide, cv2.COLOR_RGB2GRAY)
        else:
            guide_gray = guide
        
        # Simple guided filter implementation
        radius = 8
        epsilon = 0.1
        
        # Box filter implementation
        kernel = np.ones((radius*2+1, radius*2+1)) / ((radius*2+1)**2)
        
        mean_guide = cv2.filter2D(guide_gray.astype(np.float32), -1, kernel)
        mean_alpha = cv2.filter2D(alpha, -1, kernel)
        mean_guide_alpha = cv2.filter2D(guide_gray.astype(np.float32) * alpha, -1, kernel)
        
        var_guide = cv2.filter2D(guide_gray.astype(np.float32)**2, -1, kernel) - mean_guide**2
        cov_guide_alpha = mean_guide_alpha - mean_guide * mean_alpha
        
        a = cov_guide_alpha / (var_guide + epsilon)
        b = mean_alpha - a * mean_guide
        
        mean_a = cv2.filter2D(a, -1, kernel)
        mean_b = cv2.filter2D(b, -1, kernel)
        
        filtered_alpha = mean_a * guide_gray.astype(np.float32) + mean_b
        
        return np.clip(filtered_alpha, 0, 255)

    def _edge_aware_smoothing(self, alpha: np.ndarray, original: np.ndarray) -> np.ndarray:
        """Apply edge-aware smoothing to reduce jagged edges."""
        
        # Find edge regions (transition zones)
        grad_x = cv2.Sobel(alpha, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(alpha, cv2.CV_32F, 0, 1, ksize=3)
        edge_strength = np.sqrt(grad_x**2 + grad_y**2)
        
        # Define transition zones
        transition_mask = (edge_strength > 10) & (edge_strength < 100)
        
        if np.any(transition_mask):
            # Apply Gaussian smoothing only in transition zones
            smoothed = cv2.GaussianBlur(alpha, (5, 5), 1.0)
            alpha[transition_mask] = smoothed[transition_mask]
        
        return alpha

    def _improve_antialiasing(self, alpha: np.ndarray, original: np.ndarray) -> np.ndarray:
        """Improve anti-aliasing of edges."""
        
        # Find hard edges (where alpha jumps from 0 to 255)
        hard_edges = ((alpha > 200) & 
                     (cv2.dilate(alpha, np.ones((3,3)), iterations=1) < 50)) | \
                    ((alpha < 50) & 
                     (cv2.dilate(alpha, np.ones((3,3)), iterations=1) > 200))
        
        if np.any(hard_edges):
            # Create soft transition
            distance_transform = cv2.distanceTransform(
                (~hard_edges).astype(np.uint8), 
                cv2.DIST_L2, 3
            )
            
        transition_mask = (edge_strength > 10) & (edge_strength < 100)
        
        if np.any(transition_mask):
            # Apply Gaussian smoothing only in transition zones
            smoothed = cv2.GaussianBlur(alpha, (5, 5), 1.0)
            alpha[transition_mask] = smoothed[transition_mask]
        
        return alpha

    def _improve_antialiasing(self, alpha: np.ndarray, original: np.ndarray) -> np.ndarray:
        """Improve anti-aliasing of edges."""
        
        # Find hard edges (where alpha jumps from 0 to 255)
        hard_edges = ((alpha > 200) & 
                     (cv2.dilate(alpha, np.ones((3,3)), iterations=1) < 50)) | \
                    ((alpha < 50) & 
                     (cv2.dilate(alpha, np.ones((3,3)), iterations=1) > 200))
        
        if np.any(hard_edges):
            # Create soft transition
            distance_transform = cv2.distanceTransform(
                (~hard_edges).astype(np.uint8), 
                cv2.DIST_L2, 3
            )
            
            # Apply soft falloff
            falloff = np.clip(distance_transform / 3.0, 0, 1)
            alpha = alpha * falloff + (1 - falloff) * cv2.GaussianBlur(alpha, (3, 3), 1.0)
        
        return alpha

    def _advanced_mask_refinement(self, result: Image.Image, original: Image.Image) -> Image.Image:
        """Apply advanced mask refinement techniques."""
        
        result_array = np.array(result)
        if result_array.shape[2] != 4:
            return result
        
        alpha = result_array[:, :, 3]
        
        # Morphological refinement
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        
        # Close small gaps
        alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel)
        
        # Remove small noise
        alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, kernel)
        
        # Edge enhancement
        alpha = self._enhance_mask_edges(alpha)
        
        result_array[:, :, 3] = alpha
        return Image.fromarray(result_array)

    def _enhance_mask_edges(self, alpha: np.ndarray) -> np.ndarray:
        """Enhance mask edges for crisp results."""
        
        # Find edges
        edges = cv2.Canny(alpha, 50, 150)
        
        # Dilate edges slightly
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        edges_dilated = cv2.dilate(edges, kernel, iterations=1)
        
        # Enhance edges in alpha
        alpha_enhanced = alpha.copy()
        edge_coords = np.where(edges_dilated > 0)
        
        for y, x in zip(edge_coords[0], edge_coords[1]):
            # Apply local contrast enhancement
            local_region = alpha[max(0, y-2):min(alpha.shape[0], y+3), 
                               max(0, x-2):min(alpha.shape[1], x+3)]
            
            if local_region.size > 0:
                mean_val = np.mean(local_region)
                if alpha[y, x] > mean_val:
                    alpha_enhanced[y, x] = min(255, alpha[y, x] * 1.1)
                else:
                    alpha_enhanced[y, x] = max(0, alpha[y, x] * 0.9)
        
        return alpha_enhanced

    def _advanced_traditional_removal(self, image: Image.Image, preserve_holes: bool) -> Image.Image:
        """Advanced traditional background removal when AI models aren't available."""
        logger.info("🔧 Using advanced traditional removal...")
        
        img_array = np.array(image)
        
        # Multi-method approach
        methods_results = []
        
        # Method 1: Advanced GrabCut
        try:
            grabcut_result = self._advanced_grabcut(img_array)
            methods_results.append(grabcut_result)
        except Exception as e:
            logger.warning(f"GrabCut failed: {e}")
        
        # Method 2: Color-based segmentation
        try:
            color_result = self._color_based_segmentation(img_array)
            methods_results.append(color_result)
        except Exception as e:
            logger.warning(f"Color segmentation failed: {e}")
        
        # Method 3: Edge-based segmentation
        try:
            edge_result = self._edge_based_segmentation(img_array)
            methods_results.append(edge_result)
        except Exception as e:
            logger.warning(f"Edge segmentation failed: {e}")
        
        if not methods_results:
            return self._emergency_fallback(image)
        
        # Combine results
        if len(methods_results) == 1:
            final_mask = methods_results[0]
        else:
            final_mask = self._combine_traditional_masks(methods_results)
        
        # Create result
        result_array = np.dstack([img_array, final_mask])
        result_image = Image.fromarray(result_array)
        
        if preserve_holes:
            result_image = self._preserve_product_holes(result_image, image)
        
        return result_image

    def _advanced_grabcut(self, img_array: np.ndarray) -> np.ndarray:
        """Advanced GrabCut implementation."""
        
        height, width = img_array.shape[:2]
        
        # Auto-detect rectangle
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Use edge detection to find content
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Find largest contour and create bounding rectangle
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Add padding
            padding = 20
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(width - x, w + 2 * padding)
            h = min(height - y, h + 2 * padding)
            
            rect = (x, y, w, h)
        else:
            # Fallback rectangle
            margin = min(width, height) // 10
            rect = (margin, margin, width - 2*margin, height - 2*margin)
        
        # Initialize mask
        mask = np.zeros((height, width), np.uint8)
        
        # GrabCut models
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        # Apply GrabCut
        cv2.grabCut(img_array, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        
        # Refine with additional iterations
        cv2.grabCut(img_array, mask, None, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_MASK)
        
        # Extract foreground
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        final_mask = mask2 * 255
        
        return final_mask

    def _color_based_segmentation(self, img_array: np.ndarray) -> np.ndarray:
        """Advanced color-based segmentation."""
        
        if not HAS_SKLEARN:
            # Fallback to simple thresholding
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return mask
        
        # K-means clustering
        data = img_array.reshape((-1, 3))
        data = np.float32(data)
        
        # Use 4 clusters to better separate foreground/background
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        labels = kmeans.fit_predict(data)
        
        # Reshape back to image
        labels = labels.reshape(img_array.shape[:2])
        
        # Identify background cluster (most common on edges)
        edge_labels = np.concatenate([
            labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]
        ])
        background_cluster = np.bincount(edge_labels).argmax()
        
        # Create mask
        mask = (labels != background_cluster).astype(np.uint8) * 255
        
        return mask

    def _edge_based_segmentation(self, img_array: np.ndarray) -> np.ndarray:
        """Edge-based segmentation for complex products."""
        
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Multi-scale edge detection
        edges1 = cv2.Canny(gray, 30, 100)
        edges2 = cv2.Canny(gray, 50, 150)
        edges3 = cv2.Canny(gray, 100, 200)
        
        # Combine edges
        combined_edges = cv2.bitwise_or(cv2.bitwise_or(edges1, edges2), edges3)
        
        # Close gaps in edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        closed_edges = cv2.morphologyEx(combined_edges, cv2.MORPH_CLOSE, kernel)
        
        # Fill enclosed regions
        contours, _ = cv2.findContours(closed_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        mask = np.zeros_like(gray)
        
        # Find the largest contour (likely the product)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            cv2.fillPoly(mask, [largest_contour], 255)
        
        return mask

    def _combine_traditional_masks(self, masks: List[np.ndarray]) -> np.ndarray:
        """Combine multiple traditional segmentation results."""
        
        if len(masks) == 1:
            return masks[0]
        
        # Voting approach
        combined = np.zeros_like(masks[0], dtype=np.float32)
        
        for mask in masks:
            combined += mask.astype(np.float32) / 255.0
        
        # Majority vote
        combined = (combined > (len(masks) / 2)).astype(np.uint8) * 255
        
        return combined

    def _final_quality_check(self, result: Image.Image, original: Image.Image) -> Image.Image:
        """Final quality validation and correction."""
        
        result_array = np.array(result)
        
        if result_array.shape[2] != 4:
            return result
        
        alpha = result_array[:, :, 3]
        
        # Check for common issues and fix them
        
        # Issue 1: Too much background removed (over-segmentation)
        foreground_ratio = np.sum(alpha > 128) / alpha.size
        if foreground_ratio < 0.1:  # Less than 10% foreground
            logger.warning("⚠️ Possible over-segmentation detected, applying correction...")
            alpha = self._fix_over_segmentation(alpha, np.array(original))
        
        # Issue 2: Too little background removed (under-segmentation)
        elif foreground_ratio > 0.9:  # More than 90% foreground
            logger.warning("⚠️ Possible under-segmentation detected, applying correction...")
            alpha = self._fix_under_segmentation(alpha, np.array(original))
        
        # Issue 3: Fragmented mask
        alpha = self._fix_fragmentation(alpha)
        
        # Issue 4: Rough edges
        alpha = self._smooth_rough_edges(alpha)
        
        result_array[:, :, 3] = alpha
        return Image.fromarray(result_array)

    def _fix_over_segmentation(self, alpha: np.ndarray, original: np.ndarray) -> np.ndarray:
        """Fix over-segmentation by growing the foreground region."""
        
        # Find the largest connected component (main product)
        contours, _ = cv2.findContours(alpha, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Keep only the largest contour
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Create mask from largest contour
            mask = np.zeros_like(alpha)
            cv2.fillPoly(mask, [largest_contour], 255)
            
            # Grow the mask slightly
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.dilate(mask, kernel, iterations=2)
            
            return mask
        
        return alpha

    def _fix_under_segmentation(self, alpha: np.ndarray, original: np.ndarray) -> np.ndarray:
        """Fix under-segmentation by removing obvious background."""
        
        gray = cv2.cvtColor(original, cv2.COLOR_RGB2GRAY)
        
        # Find very uniform regions (likely background)
        blurred = cv2.GaussianBlur(gray, (21, 21), 0)
        variance = cv2.GaussianBlur((gray - blurred) ** 2, (21, 21), 0)
        
        # Low variance regions are likely uniform background
        uniform_mask = variance < 100
        
        # Remove uniform regions from edges
        h, w = alpha.shape
        edge_margin = 20
        
        # Create edge mask
        edge_mask = np.zeros_like(alpha, dtype=bool)
        edge_mask[:edge_margin, :] = True
        edge_mask[-edge_margin:, :] = True
        edge_mask[:, :edge_margin] = True
        edge_mask[:, -edge_margin:] = True
        
        # Remove uniform edge regions
        background_regions = uniform_mask & edge_mask
        alpha[background_regions] = 0
        
        return alpha

    def _fix_fragmentation(self, alpha: np.ndarray) -> np.ndarray:
        """Fix fragmented masks by connecting nearby regions."""
        
        # Close small gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel)
        
        # Remove small isolated regions
        contours, _ = cv2.findContours(alpha, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) > 1:
            # Keep only reasonably sized contours
            min_area = alpha.size * 0.01  # Minimum 1% of image
            
            filtered_mask = np.zeros_like(alpha)
            for contour in contours:
                if cv2.contourArea(contour) > min_area:
                    cv2.fillPoly(filtered_mask, [contour], 255)
            
            alpha = filtered_mask
        
        return alpha

    def _smooth_rough_edges(self, alpha: np.ndarray) -> np.ndarray:
        """Smooth rough edges while preserving fine details."""
        
        # Apply gentle smoothing
        alpha_smooth = cv2.GaussianBlur(alpha, (3, 3), 0.5)
        
        # Only apply smoothing to edges
        edges = cv2.Canny(alpha, 50, 150)
        edge_mask = cv2.dilate(edges, np.ones((3, 3)), iterations=1) > 0
        
        result = alpha.copy()
        result[edge_mask] = alpha_smooth[edge_mask]
        
        return result

    def _emergency_fallback(self, image: Image.Image) -> Image.Image:
        """Emergency fallback when all methods fail."""
        logger.warning("🚨 Using emergency fallback - simple thresholding")
        
        try:
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Simple Otsu thresholding
            _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Create RGBA result
            result_array = np.dstack([img_array, mask])
            return Image.fromarray(result_array)
            
        except Exception as e:
            logger.error(f"Emergency fallback failed: {e}")
            # Return original image with full alpha
            if image.mode != 'RGBA':
                return image.convert('RGBA')
            return image


# Integration with existing UnifiedImageEngine
class EnhancedImageEngine:
    """Enhanced image engine with professional background removal."""
    
    def __init__(self):
        self.bg_remover = ProductBackgroundRemover()
        
    def remove_background_professional(self, image: Image.Image, 
                                     quality: str = "high",
                                     preserve_holes: bool = True) -> Image.Image:
        """
        Professional background removal optimized for e-commerce.
        
        Args:
            image: Input PIL Image
            quality: "ultra_high", "high", "medium", "fast"
            preserve_holes: Preserve holes in products (jewelry, handles etc.)
            
        Returns:
            PIL Image with professionally removed background
        """
        return self.bg_remover.remove_background_professional(
            image=image,
            quality_level=quality,
            preserve_holes=preserve_holes,
            edge_refinement=True
        )
    
    def process_single_image_enhanced(self, image_path: str, settings: Dict[str, Any]) -> str:
        """Process single image with enhanced background removal."""
        try:
            # Load image
            image = Image.open(image_path)
            
            # Determine quality level from settings
            quality_map = {
                'fast': 'fast',
                'medium': 'medium', 
                'high': 'high',
                'ultra_high': 'ultra_high'
            }
            quality = quality_map.get(settings.get('bg_quality', 'high'), 'high')
            
            # Professional background removal
            if settings.get('bg_mode') == 'remove':
                result = self.remove_background_professional(
                    image=image,
                    quality=quality,
                    preserve_holes=settings.get('preserve_holes', True)
                )
            elif settings.get('bg_mode') == 'color':
                # Remove background first
                no_bg = self.remove_background_professional(
                    image=image,
                    quality=quality,
                    preserve_holes=settings.get('preserve_holes', True)
                )
                
                # Apply solid color background
                bg_color = settings.get('bg_color', '#FFFFFF')
                if isinstance(bg_color, str) and bg_color.startswith('#'):
                    hex_color = bg_color[1:]
                    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                else:
                    rgb = (255, 255, 255)
                
                background = Image.new('RGB', image.size, rgb)
                background.paste(no_bg, mask=no_bg.split()[-1])
                result = background
            else:
                result = image
            
            # Generate output path
            input_path = Path(image_path)
            output_path = str(input_path.parent / f"{input_path.stem}_processed.png")
            
            # Save result
            result.save(output_path, "PNG")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Enhanced processing failed: {e}")
            raise


# Factory function for easy integration
def create_enhanced_engine() -> EnhancedImageEngine:
    """Create enhanced image engine with professional background removal."""
    from .carvekit_engine import OptimizedImageEngine
    return OptimizedImageEngine()

import sys
import logging

logger = logging.getLogger(__name__)

def create_optimized_engine(max_workers=4):
    """Factory function that creates the appropriate engine based on platform."""
    if sys.platform == "win32":
        try:
            from .windows_engine import create_windows_engine
            logger.info("Using Windows-optimized engine")
            return create_windows_engine()
        except Exception as e:
            logger.error(f"Failed to create Windows engine: {e}, falling back to CarveKit")
            from .carvekit_engine import OptimizedImageEngine
            return OptimizedImageEngine()
    else:
        from .carvekit_engine import OptimizedImageEngine
        logger.info("Using CarveKit engine")
        return OptimizedImageEngine()