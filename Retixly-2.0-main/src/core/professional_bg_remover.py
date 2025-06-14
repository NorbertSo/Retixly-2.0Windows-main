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

# --- FP16 autocast support for Tracer-B7 ---
try:
    from torch.cuda.amp import autocast
    HAS_AMP = True
except Exception:
    HAS_AMP = False

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
                logger.info("🚀 Initializing professional background removal models...")

                # Try to initialize multiple models for ensemble
                model_priorities = [
                    ('u2net', 'u2net'),
                    ('silueta', 'silueta'),
                    ('isnet', 'isnet-general-use'),
                    ('u2netp', 'u2netp'),
                    ('sam', 'sam'),
                    ('tracer_b7', 'tracer-b7')
                ]

                for model_key, model_name in model_priorities:
                    try:
                        session = new_session(model_name)
                        self.models[model_key] = session
                        logger.info(f"✅ Initialized {model_name} model")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to initialize {model_name}: {e}")

                if not self.models:
                    # Fallback to basic rembg
                    logger.info("🔄 Using basic rembg as fallback")
                    self.models['basic'] = None

            except Exception as e:
                logger.warning(f"⚠️ rembg initialization failed: {e}")
                self.models['basic'] = None
        else:
            logger.warning("⚠️ rembg not available - using traditional methods")

    # ---------- Auto‑classification helpers ----------
    def _quick_heuristics(self, img_array: np.ndarray) -> str:
        """
        Super‑fast heuristics to categorise the product shot:
        returns 'white_bg', 'dark_product', 'handles', or 'generic'.
        """
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY) if img_array.ndim == 3 else img_array
        h, w = gray.shape[:2]

        white_ratio = np.sum(gray > 220) / (h * w)
        black_ratio = np.sum(gray < 40) / (h * w)

        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (h * w)

        if white_ratio > 0.6:
            return 'white_bg'
        if black_ratio > 0.4:
            return 'dark_product'
        if edge_density > 0.10:
            return 'handles'
        # --- shape-based detector for tall / narrow objects (e.g. mascara wand)
        if np.any(edges):
            ys, xs = np.where(edges > 0)
            box_h, box_w = ys.ptp() + 1, xs.ptp() + 1
            if box_h and box_w:
                aspect = max(box_h / box_w, box_w / box_h)
                # very elongated and relatively thin object → treat as 'handles'
                if aspect > 3 and min(box_h, box_w) < 0.3 * min(h, w):
                    return 'handles'
        # --- detect mid‑tone, studio‑paper background -------------------------
        # If the four corners are very uniform in tone (low std) and neither very
        # dark nor very bright, we treat it as a solid backdrop that can be
        # cleanly segmented with the standard U‑2‑Net.
        corner = gray[: max(8, int(0.05 * h)), : max(8, int(0.05 * w))]
        bg_std  = float(np.std(corner))
        bg_mean = float(np.mean(corner))
        if bg_std < 10 and 40 < bg_mean < 220:
            return 'solid_bg'
        return 'generic'

    def _select_auto_config(self, category: str) -> dict:
        """Map heuristic category to default model & parameters."""
        mapping = {
            'dark_product': {
                'model_key': 'isnet',
                'preserve_holes': True,
                'force_binary_alpha': False,
                'edge_refinement': True
            },
            'generic': {
                'model_key': 'u2netp',
                'preserve_holes': True,
                'force_binary_alpha': True,
                'edge_refinement': True
            },
            'handles': {
                'model_key': 'isnet',
                'preserve_holes': True,
                'force_binary_alpha': True,
                'edge_refinement': True
            },
            'solid_bg': {
                'model_key': 'u2net',
                'preserve_holes': False,
                'force_binary_alpha': True,
                'edge_refinement': True
            },
            'white_bg': {
                'model_key': 'u2net',
                'preserve_holes': False,
                'force_binary_alpha': True,
                'edge_refinement': True
            }
        }
        return mapping.get(category, mapping['generic'])

    def _basic_quality_check(self, result_img: Image.Image) -> bool:
        """
        Quick sanity check for produced mask.
        Returns False if mask is empty, full, or obviously jagged.
        """
        try:
            arr = np.array(result_img)
            if arr.shape[2] != 4:
                return False
            alpha = arr[:, :, 3]
            covered = np.sum(alpha > 128) / (alpha.shape[0] * alpha.shape[1])
            if not (0.05 < covered < 0.95):
                return False
            edges = cv2.Canny(alpha, 50, 150)
            edge_density = np.sum(edges > 0) / (alpha.shape[0] * alpha.shape[1])
            return edge_density > 0.005
        except Exception:
            return False

    # ---------- mask utilities ----------
    def _cut_topological_holes(self, alpha: np.ndarray, skip_small_details: bool = False) -> np.ndarray:
        """
        Remove enclosed holes inside the product mask that standard models miss.
        Operates on binary alpha (0 / 255).
        Optionally skip cutting very small/thin internal details if skip_small_details is True.
        """
        # Ensure we operate on a contiguous, writable copy for OpenCV
        alpha = np.ascontiguousarray(alpha.copy())
        contours, hierarchy = cv2.findContours(alpha, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None:
            return alpha
        for idx, cnt in enumerate(contours):
            # contour with a parent is an interior hole
            if hierarchy[0][idx][3] != -1:
                area = cv2.contourArea(cnt)
                x, y, w, h = cv2.boundingRect(cnt)

                # decide if this interior contour should be removed
                remove_hole = 50 < area < 0.3 * alpha.size

                # keep extremely thin / small inner details when flag is on
                if skip_small_details:
                    if w < 6 or h < 6:
                        remove_hole = False

                if remove_hole:
                    cv2.drawContours(alpha, [cnt], -1, 0, -1)
        return alpha

    def _reattach_thin_components(self, alpha: np.ndarray) -> np.ndarray:
        """
        Re‑add very thin / elongated foreground components that were detached
        by hole‑cutting or thresholding (e.g. mascara wand, wire edges).
        Conditions:
          • component area < 0.5 % of main object
          • aspect ratio > 4  *or* min(width,height) < 8 px
        """
        # copy & ensure contiguous
        alpha_out = alpha.copy()
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            (alpha > 0).astype(np.uint8), connectivity=8)
        if num_labels < 2:
            return alpha_out

        # identify largest component = main product
        main_area = stats[1:, cv2.CC_STAT_AREA].max()
        areas = stats[:, cv2.CC_STAT_AREA]

        for lbl in range(1, num_labels):
            if areas[lbl] == main_area:
                continue
            area_ratio = areas[lbl] / main_area
            x, y, w, h, _ = stats[lbl]
            aspect = max(w / h, h / w) if h and w else 1
            if area_ratio < 0.005 and (aspect > 4 or min(w, h) < 8):
                alpha_out[labels == lbl] = 255  # keep it
        return alpha_out

    def remove_background_professional(self, image: Image.Image,
                                       quality_level: str = "high",
                                       preserve_holes: bool = True,
                                       edge_refinement: bool = True,
                                       model_name: str = None,
                                       debug_masks: bool = False,
                                       force_binary_alpha: bool = True,
                                       feathering: int = 0) -> Image.Image:
        """
        Professional background removal for product photos.
        Pipeline:
          1. Use U2NETP to segment the main product.
          2. If preserve_holes, try ISNET (if available) to refine holes.
          3. At the end, force binary mask and feathering if requested.
        """
        # Ensure fallback has a valid image even on early exceptions
        original_image = image.copy()
        try:
            start_time = time.time()
            logger.info(f"🎯 Starting professional background removal - Quality: {quality_level}")

            auto_mode = model_name in (None, 'auto')
            selected_model = 'u2netp'  # default fallback

            if auto_mode:
                category = self._quick_heuristics(np.array(image))
                auto_cfg = self._select_auto_config(category)
                selected_model = auto_cfg['model_key']
                preserve_holes = auto_cfg['preserve_holes']
                edge_refinement = auto_cfg['edge_refinement']
                force_binary_alpha = auto_cfg['force_binary_alpha']
                logger.info(f"🔀 Auto‑selected model '{selected_model}' for category '{category}'")
            else:
                selected_model = model_name

            original_image = image.copy()
            if image.mode not in ['RGB', 'RGBA']:
                image = image.convert('RGB')

            # Pre-process for e-commerce
            image = self._preprocess_for_removal(image)

            # 1. Use selected model to segment the main product
            first_pass = self._rembg_with_model(image, selected_model)
            if debug_masks and first_pass.mode == "RGBA":
                mask = np.array(first_pass)[:, :, 3]
                Image.fromarray(mask).save("debug_mask_first.png")

            result = first_pass

            # 2. If preserve_holes, cut holes using ISNET if available
            if preserve_holes:
                if 'isnet' in self.models:
                    try:
                        isnet_result = self._rembg_with_model(image, 'isnet')
                        mask_isnet = np.array(isnet_result)[:, :, 3]
                        mask_first = np.array(first_pass)[:, :, 3]

                        # Holes = where ISNET sees background (0) but first pass thinks foreground (255)
                        holes_mask = (mask_first == 255) & (mask_isnet == 0)

                        # --- NEW: keep holes only *inside* the largest connected component
                        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
                            (mask_first > 0).astype(np.uint8), connectivity=8
                        )
                        if num_labels > 1:
                            largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
                            main_obj = (labels == largest_label)
                            holes_mask &= main_obj  # cut holes only within main product

                        # Apply hole cut
                        mask_first[holes_mask] = 0
                        # also clear RGB where hole pixels are cut
                        first_pass_array = np.array(first_pass)
                        first_pass_array[holes_mask, :3] = 0
                        first_pass_array[:, :, 3] = mask_first
                        result = Image.fromarray(first_pass_array)
                        if debug_masks:
                            Image.fromarray(mask_isnet).save("debug_mask_isnet.png")
                            Image.fromarray(mask_first).save("debug_mask_first_holes.png")
                    except Exception as e:
                        logger.warning(f"ISNET hole detection failed: {e}")
                        # fallback: just use first_pass
                        result = first_pass
                else:
                    result = first_pass

            # 3. At the end: force binary mask if requested
            result_array = np.array(result)
            if force_binary_alpha and result_array.shape[2] == 4:
                alpha = result_array[:, :, 3]
                alpha = (alpha > 128).astype(np.uint8) * 255
                result_array[:, :, 3] = alpha
                result = Image.fromarray(result_array)

            # ensure no background tint remains where alpha is 0
            if result_array.shape[2] == 4:
                zero_rgb = result_array[:, :, 3] == 0
                if np.any(zero_rgb):
                    result_array[zero_rgb, :3] = 0

                # --- extra hole cutting & halo clean ---
                alpha_bin = result_array[:, :, 3]

                # For objects with handles we cut holes but keep very small/thin details
                if auto_mode and category == 'handles':
                    alpha_bin = self._cut_topological_holes(alpha_bin, skip_small_details=True)
                else:
                    alpha_bin = self._cut_topological_holes(alpha_bin)

                # one‑pixel halo clean for white products
                if auto_mode and category == 'white_bg':
                    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                    alpha_bin = cv2.morphologyEx(alpha_bin, cv2.MORPH_CLOSE, k)
                    alpha_bin = cv2.morphologyEx(alpha_bin, cv2.MORPH_OPEN, k)

                # restore thin detached parts (wand, wires)
                alpha_bin = self._reattach_thin_components(alpha_bin)

                # defringe single‑pixel glow around dense wires
                if auto_mode and category == 'handles':
                    alpha_bin = cv2.morphologyEx(alpha_bin, cv2.MORPH_ERODE,
                                                 cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)))
                    alpha_bin = cv2.morphologyEx(alpha_bin, cv2.MORPH_DILATE,
                                                 cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)))

                result_array[:, :, 3] = alpha_bin

            # re‑wrap numpy array into PIL after in‑place modifications
            result = Image.fromarray(result_array)

            # 4. Feathering if requested
            if feathering > 0:
                result = self._apply_feathering(result, feather_amount=feathering)

            # 5. Optionally: edge refinement (after holes/feathering/binarization)
            if edge_refinement:
                result = self._refine_edges_advanced(result, original_image)

            # 6. Quick QC and fallback to isnet if needed
            if not self._basic_quality_check(result) and selected_model != 'isnet' and 'isnet' in self.models:
                logger.info("🔁 QC failed – retrying with 'isnet' for robustness")
                try:
                    retry = self._rembg_with_model(image, 'isnet')
                    if self._basic_quality_check(retry):
                        result = retry
                except Exception as e:
                    logger.warning(f"Retry with isnet failed: {e}")
            # Second fallback – try SAM if still unsatisfactory
            if not self._basic_quality_check(result) and 'sam' in self.models:
                logger.info("🔁 QC still poor – trying 'sam' model")
                try:
                    retry_sam = self._rembg_with_model(image, 'sam')
                    if self._basic_quality_check(retry_sam):
                        result = retry_sam
                except Exception as e:
                    logger.warning(f"Retry with sam failed: {e}")

            # final clean‑up of RGB when fully transparent
            final_arr = np.array(result)
            if final_arr.shape[2] == 4:
                final_arr[final_arr[:, :, 3] == 0, :3] = 0
                result = Image.fromarray(final_arr)

            processing_time = time.time() - start_time
            logger.info(f"✅ Professional removal completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"❌ Professional background removal failed: {e}")
            return self._emergency_fallback(original_image)

    def _preprocess_for_removal(self, image: Image.Image) -> Image.Image:
        """Pre-process image to improve background removal quality."""
        try:
            img_array = np.array(image)
            # Convert to LAB color space
            lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            # Apply CLAHE to the L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            # Merge channels back
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
            # Apply subtle sharpening
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel * 0.1)
            # Blend with original
            result = cv2.addWeighted(enhanced, 0.7, sharpened, 0.3, 0)
            return Image.fromarray(result)
        except Exception as e:
            logger.warning(f"Preprocessing failed: {e}")
            return image

    def _high_quality_removal(self, image: Image.Image, preserve_holes: bool) -> Image.Image:
        """High quality removal using best single model + refinements."""
        logger.info("🎯 Applying high quality removal...")
        
        if not HAS_REMBG or not self.models:
            return self._advanced_traditional_removal(image, preserve_holes)
        
        # Use best available model
        result = None
        for model_key in ['u2net', 'isnet', 'silueta', 'u2netp']:
            if model_key in self.models:
                try:
                    result = self._rembg_with_model(image, model_key)
                    if result is not None:
                        logger.info(f"✅ Using {model_key} for high quality removal")
                        break
                except Exception as e:
                    logger.warning(f"⚠️ {model_key} failed: {e}")
                    continue
        
        if result is None:
            result = self._basic_rembg_removal(image)
        
        # Apply advanced post-processing
        result = self._advanced_mask_refinement(result, image)
        
        if preserve_holes:
            result = self._preserve_product_holes(result, image)
            
        return result

    def _ultra_high_quality_removal(self, image: Image.Image, preserve_holes: bool) -> Image.Image:
        logger.info("Dummy _ultra_high_quality_removal used (fallback)")
        return image.convert('RGBA')

    def _medium_quality_removal(self, image: Image.Image) -> Image.Image:
        """Medium quality removal - balanced speed/quality."""
        logger.info("🎯 Applying medium quality removal...")
        
        if HAS_REMBG and self.models:
            # Use any available model
            for model_key in ['isnet', 'silueta', 'u2net', 'u2netp']:
                if model_key in self.models:
                    try:
                        return self._rembg_with_model(image, model_key)
                    except Exception as e:
                        logger.warning(f"⚠️ {model_key} failed: {e}")
                        continue
        
        return self._basic_rembg_removal(image)

    def _fast_quality_removal(self, image: Image.Image) -> Image.Image:
        """Fast removal for quick previews."""
        logger.info("🎯 Applying fast quality removal...")
        
        if HAS_REMBG and 'u2netp' in self.models:
            try:
                return self._rembg_with_model(image, 'u2netp')
            except Exception as e:
                logger.warning(f"⚠️ Fast model failed: {e}")
        
        return self._basic_rembg_removal(image)

    def _rembg_with_model(self, image: Image.Image, model_key: str) -> Image.Image:
        """Apply rembg with specific model."""
        try:
            img_array = np.array(image)
            # --- dynamic parameters & FP16 support (Tracer‑B7 ready) ---
            base_size = max(512, min(img_array.shape[0], img_array.shape[1]) // 2)
            remove_kwargs = dict(
                alpha_matting=True,
                alpha_matting_foreground_threshold=230,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=10,
                alpha_matting_base_size=base_size
            )

            if model_key in self.models and self.models[model_key] is not None:
                # Tracer‑B7: enable mixed‑precision inference when env flag present
                use_amp = HAS_AMP and torch.cuda.is_available() and os.getenv('TRACER_B7', '0') == '1'
                if use_amp:
                    with torch.no_grad(), autocast():
                        result_array = remove(img_array, session=self.models[model_key], **remove_kwargs)
                else:
                    result_array = remove(img_array, session=self.models[model_key], **remove_kwargs)
            else:
                # Fallback to default model with the same tuned kwargs
                result_array = remove(img_array, **remove_kwargs)

            return Image.fromarray(result_array)

        except Exception as e:
            logger.error(f"Rembg {model_key} failed: {e}")
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
        try:
            # Convert guide to grayscale
            if len(guide.shape) == 3:
                guide_gray = cv2.cvtColor(guide, cv2.COLOR_RGB2GRAY)
            else:
                guide_gray = guide
            # try OpenCV's fast guided filter (if available)
            try:
                import cv2.ximgproc as xip
                return xip.guidedFilter(guide_gray, alpha.astype(np.uint8), 4, 1e-3)
            except Exception:
                # ximgproc not available – fall back to manual implementation below
                pass

            # Simple guided filter implementation
            radius = 8
            epsilon = 0.05  # tighter guidance, reduces glow on thin metal

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
        except Exception as e:
            logger.warning(f"Guided filter failed: {e}")
            return alpha

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
            y_min = max(0, y-2)
            y_max = min(alpha.shape[0], y+3)
            x_min = max(0, x-2)
            x_max = min(alpha.shape[1], x+3)
            local_region = alpha[y_min:y_max, x_min:x_max]

            if local_region.size > 0:
                mean_val = np.mean(local_region)
                if alpha[y, x] > mean_val:
                    alpha_enhanced[y, x] = min(255, alpha[y, x] * 1.1)
                else:
                    alpha_enhanced[y, x] = max(0, alpha[y, x] * 0.9)

        return alpha_enhanced

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
                if np.sum(mask > 0) > 0:
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
        final_holes = np.zeros_like(holes_mask, dtype=np.uint8)
        for contour in contours:
            area = cv2.contourArea(contour)
            if 10 < area < 5000:  # Reasonable hole size
                cv2.fillPoly(final_holes, [contour], 255)
        return final_holes

    def _emergency_fallback(self, image: Image.Image) -> Image.Image:
        logger.warning("🚨 Using emergency fallback - simple thresholding")
        try:
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            # Simple Otsu thresholding
            _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # Create RGBA image
            if img_array.shape[-1] == 3:
                result_array = np.dstack([img_array, mask])
            else:
                result_array = img_array.copy()
                result_array[:, :, 3] = mask
            return Image.fromarray(result_array.astype(np.uint8))
        except Exception as e:
            logger.error(f"Emergency fallback failed: {e}")
            if image.mode != 'RGBA':
                return image.convert('RGBA')
            return image

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
        
        # Combine results if we have multiple methods
        if methods_results:
            final_mask = self._combine_segmentation_results(methods_results)
        else:
            # Fallback to simple method
            final_mask = self._simple_background_removal(img_array)
        
        # Create RGBA result
        result = np.zeros((img_array.shape[0], img_array.shape[1], 4), dtype=np.uint8)
        result[:, :, :3] = img_array
        result[:, :, 3] = final_mask
        
        result_image = Image.fromarray(result)
        
        # Apply hole preservation if requested
        if preserve_holes:
            result_image = self._preserve_product_holes(result_image, image)
        
        return result_image

    def _advanced_grabcut(self, img_array: np.ndarray) -> np.ndarray:
        """Advanced GrabCut with automatic rectangle detection."""
        
        # Create mask
        mask = np.zeros(img_array.shape[:2], np.uint8)
        
        # Automatic rectangle detection (avoid edges)
        h, w = img_array.shape[:2]
        margin_h, margin_w = int(h * 0.1), int(w * 0.1)
        rect = (margin_w, margin_h, w - 2*margin_w, h - 2*margin_h)
        
        # Initialize background and foreground models
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        # Apply GrabCut
        cv2.grabCut(img_array, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        
        # Refine with probable foreground/background
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        
        # Post-process mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask2 = cv2.morphologyEx(mask2, cv2.MORPH_CLOSE, kernel)
        mask2 = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel)
        
        return mask2 * 255

    def _color_based_segmentation(self, img_array: np.ndarray) -> np.ndarray:
        """Advanced color-based background segmentation."""
        
        # Convert to different color spaces
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
        
        # Detect background colors (usually corners and edges)
        h, w = img_array.shape[:2]
        
        # Sample background colors from corners and edges
        bg_samples = []
        
        # Corner samples
        corner_size = min(h, w) // 10
        corners = [
            img_array[:corner_size, :corner_size],  # Top-left
            img_array[:corner_size, -corner_size:],  # Top-right
            img_array[-corner_size:, :corner_size],  # Bottom-left
            img_array[-corner_size:, -corner_size:]  # Bottom-right
        ]
        
        for corner in corners:
            bg_samples.extend(corner.reshape(-1, 3))
        
        # Edge samples
        edge_width = max(1, min(h, w) // 20)
        edges = [
            img_array[:edge_width, :],  # Top edge
            img_array[-edge_width:, :],  # Bottom edge
            img_array[:, :edge_width],  # Left edge
            img_array[:, -edge_width:]  # Right edge
        ]
        
        for edge in edges:
            bg_samples.extend(edge.reshape(-1, 3))
        
        bg_samples = np.array(bg_samples)
        
        # Cluster background colors
        from sklearn.cluster import KMeans
        try:
            kmeans = KMeans(n_clusters=min(5, len(bg_samples)//10), random_state=42)
            kmeans.fit(bg_samples)
            bg_colors = kmeans.cluster_centers_
        except:
            # Fallback: use mean color
            bg_colors = [np.mean(bg_samples, axis=0)]
        
        # Create mask based on distance to background colors
        mask = np.ones((h, w), dtype=np.uint8) * 255
        
        for bg_color in bg_colors:
            # Calculate color distance
            diff = np.linalg.norm(img_array - bg_color, axis=2)
            threshold = np.percentile(diff, 30)  # Adaptive threshold
            bg_mask = diff < threshold
            mask[bg_mask] = 0
        
        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask

    def _edge_based_segmentation(self, img_array: np.ndarray) -> np.ndarray:
        """Edge-based segmentation using watershed algorithm."""
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Find edges
        edges = cv2.Canny(blurred, 30, 80)
        
        # Distance transform
        dist_transform = cv2.distanceTransform(cv2.bitwise_not(edges), cv2.DIST_L2, 5)
        
        # Find local maxima (seeds)
        local_maxima = cv2.dilate(dist_transform, np.ones((20, 20))) == dist_transform
        local_maxima = local_maxima & (dist_transform > 0.3 * dist_transform.max())
        
        # Create markers
        markers = np.zeros_like(gray, dtype=np.int32)
        markers[local_maxima] = np.arange(1, np.sum(local_maxima) + 1)
        
        # Apply watershed
        markers = cv2.watershed(img_array, markers)
        
        # Create mask (assume largest region is foreground)
        unique_labels, counts = np.unique(markers[markers > 0], return_counts=True)
        if len(unique_labels) > 0:
            largest_label = unique_labels[np.argmax(counts)]
            mask = (markers == largest_label).astype(np.uint8) * 255
        else:
            mask = np.ones_like(gray, dtype=np.uint8) * 255
        
        return mask

    def _combine_segmentation_results(self, results: List[np.ndarray]) -> np.ndarray:
        """Combine multiple segmentation results using voting."""
        
        if len(results) == 1:
            return results[0]
        
        # Normalize all results to 0-1
        normalized_results = []
        for result in results:
            normalized = result.astype(np.float32) / 255.0
            normalized_results.append(normalized)
        
        # Voting: average of all methods
        combined = np.mean(normalized_results, axis=0)
        
        # Apply threshold
        threshold = 0.5
        final_mask = (combined > threshold).astype(np.uint8) * 255
        
        # Post-processing
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel)
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_OPEN, kernel)
        
        return final_mask

    def _simple_background_removal(self, img_array: np.ndarray) -> np.ndarray:
        """Simple fallback background removal."""
        
        # Use the most common color in corners as background
        h, w = img_array.shape[:2]
        corner_size = min(h, w) // 8
        
        corners = [
            img_array[:corner_size, :corner_size],
            img_array[:corner_size, -corner_size:],
            img_array[-corner_size:, :corner_size],
            img_array[-corner_size:, -corner_size:]
        ]
        
        corner_pixels = np.vstack([corner.reshape(-1, 3) for corner in corners])
        bg_color = np.median(corner_pixels, axis=0)
        
        # Create mask based on color similarity
        diff = np.linalg.norm(img_array - bg_color, axis=2)
        threshold = np.percentile(diff, 25)
        mask = (diff > threshold).astype(np.uint8) * 255
        
        # Clean up mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        return mask

    def _apply_feathering(self, result: Image.Image, feather_amount: int = 2) -> Image.Image:
        """Apply feathering to soften edges."""
        
        if feather_amount <= 0:
            return result
        
        result_array = np.array(result)
        if result_array.shape[2] != 4:
            return result
        
        alpha = result_array[:, :, 3].astype(np.float32)
        
        # Apply Gaussian blur to alpha channel
        sigma = feather_amount / 3.0
        alpha_feathered = cv2.GaussianBlur(alpha, (feather_amount*2+1, feather_amount*2+1), sigma)
        
        result_array[:, :, 3] = np.clip(alpha_feathered, 0, 255).astype(np.uint8)
        
        return Image.fromarray(result_array)

    def get_available_models(self) -> Dict[str, List[str]]:
        """Get list of available models for each provider."""
        available = {}
        
        # Check RemBG models
        try:
            import rembg
            available['rembg'] = ['u2net', 'u2netp', 'silueta', 'isnet-general-use']
        except ImportError:
            available['rembg'] = []
        
        # Check if other providers are available
        available['traditional'] = ['grabcut', 'watershed', 'color_segmentation']
        
        return available

    def benchmark_models(self, test_image: Image.Image, models: List[str] = None) -> Dict[str, Dict]:
        """Benchmark different models on a test image."""
        
        if models is None:
            available = self.get_available_models()
            models = []
            for provider_models in available.values():
                models.extend(provider_models)
        
        results = {}
        
        for model in models:
            logger.info(f"🧪 Benchmarking model: {model}")
            
            start_time = time.time()
            try:
                if model in ['u2net', 'u2netp', 'silueta', 'isnet-general-use']:
                    result = self._remove_with_rembg(test_image, model)
                else:
                    result = self._advanced_traditional_removal(test_image, preserve_holes=False)
                
                processing_time = time.time() - start_time
                
                # Calculate quality metrics
                metrics = self._calculate_quality_metrics(result, test_image)
                
                results[model] = {
                    'processing_time': processing_time,
                    'success': True,
                    'metrics': metrics
                }
                
                logger.info(f"✅ {model}: {processing_time:.2f}s")
                
            except Exception as e:
                results[model] = {
                    'processing_time': time.time() - start_time,
                    'success': False,
                    'error': str(e),
                    'metrics': None
                }
                logger.error(f"❌ {model} failed: {e}")
        
        return results

    def _calculate_quality_metrics(self, result: Image.Image, original: Image.Image) -> Dict[str, float]:
        """Calculate quality metrics for the result."""
        
        result_array = np.array(result)
        original_array = np.array(original)
        
        if result_array.shape[2] != 4:
            return {'error': 'No alpha channel'}
        
        alpha = result_array[:, :, 3]
        
        # Edge quality (how clean are the edges)
        edges = cv2.Canny(alpha, 50, 150)
        edge_quality = np.sum(edges > 0) / (alpha.shape[0] * alpha.shape[1])
        
        # Mask coverage (how much of the image is foreground)
        foreground_ratio = np.sum(alpha > 128) / (alpha.shape[0] * alpha.shape[1])
        
        # Alpha distribution (good masks have clear fg/bg separation)
        hist, _ = np.histogram(alpha, bins=256, range=(0, 256))
        # Good masks should have peaks at 0 and 255
        alpha_quality = (hist[0] + hist[255]) / np.sum(hist)
        
        # Smoothness (less noise is better)
        alpha_float = alpha.astype(np.float32)
        laplacian_var = cv2.Laplacian(alpha_float, cv2.CV_64F).var()
        smoothness = 1.0 / (1.0 + laplacian_var / 1000.0)  # Normalize
        
        return {
            'edge_quality': float(edge_quality),
            'foreground_ratio': float(foreground_ratio),
            'alpha_quality': float(alpha_quality),
            'smoothness': float(smoothness),
            'overall_score': float((edge_quality + alpha_quality + smoothness) / 3)
        }

    def batch_process(self, 
                     input_dir: str, 
                     output_dir: str,
                     model: str = 'auto',
                     preserve_holes: bool = True,
                     enhance_quality: bool = True,
                     max_workers: int = None) -> Dict[str, any]:
        """
        Process multiple images in batch.
        
        Args:
            input_dir: Directory containing input images
            output_dir: Directory to save processed images
            model: Model to use for processing
            preserve_holes: Whether to preserve holes in products
            enhance_quality: Whether to apply quality enhancements
            max_workers: Number of parallel workers (None for auto)
        
        Returns:
            Dictionary with processing results and statistics
        """
        
        import os
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from pathlib import Path
        
        # Setup directories
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Find all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        image_files = [
            f for f in input_path.iterdir() 
            if f.suffix.lower() in image_extensions
        ]
        
        if not image_files:
            return {'error': 'No image files found in input directory'}
        
        logger.info(f"🚀 Starting batch processing of {len(image_files)} images...")
        
        # Determine number of workers
        if max_workers is None:
            max_workers = min(4, len(image_files))  # Don't overwhelm the system
        
        results = {
            'total_files': len(image_files),
            'processed': 0,
            'failed': 0,
            'processing_times': [],
            'errors': [],
            'successful_files': []
        }
        
        def process_single_image(image_file):
            """Process a single image file."""
            try:
                start_time = time.time()
                
                # Load image
                image = Image.open(image_file)
                
                # Process image
                result = self.remove_background(
                    image=image,
                    model=model,
                    preserve_holes=preserve_holes,
                    enhance_quality=enhance_quality
                )
                
                # Save result
                output_file = output_path / f"{image_file.stem}_no_bg.png"
                result.save(output_file, 'PNG')
                
                processing_time = time.time() - start_time
                
                return {
                    'success': True,
                    'input_file': str(image_file),
                    'output_file': str(output_file),
                    'processing_time': processing_time
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'input_file': str(image_file),
                    'error': str(e),
                    'processing_time': time.time() - start_time if 'start_time' in locals() else 0
                }
        
        # Process images in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(process_single_image, img_file): img_file 
                for img_file in image_files
            }
            
            # Process completed tasks
            for future in as_completed(future_to_file):
                result = future.result()
                
                if result['success']:
                    results['processed'] += 1
                    results['processing_times'].append(result['processing_time'])
                    results['successful_files'].append(result['output_file'])
                    logger.info(f"✅ Processed: {Path(result['input_file']).name} ({result['processing_time']:.2f}s)")
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'file': result['input_file'],
                        'error': result['error']
                    })
                    logger.error(f"❌ Failed: {Path(result['input_file']).name} - {result['error']}")
        
        # Calculate statistics
        if results['processing_times']:
            results['avg_processing_time'] = sum(results['processing_times']) / len(results['processing_times'])
            results['total_processing_time'] = sum(results['processing_times'])
        else:
            results['avg_processing_time'] = 0
            results['total_processing_time'] = 0
        
        logger.info(f"🎉 Batch processing complete!")
        logger.info(f"   Processed: {results['processed']}/{results['total_files']}")
        logger.info(f"   Failed: {results['failed']}")
        logger.info(f"   Avg time: {results['avg_processing_time']:.2f}s per image")
        
        return results

    def create_composite(self, 
                        foreground: Image.Image, 
                        background: Image.Image,
                        blend_mode: str = 'normal',
                        opacity: float = 1.0) -> Image.Image:
        """
        Create a composite image by placing foreground on background.
        
        Args:
            foreground: Image with transparency (RGBA)
            background: Background image
            blend_mode: Blending mode ('normal', 'multiply', 'screen', 'overlay')
            opacity: Opacity of foreground (0.0 to 1.0)
        
        Returns:
            Composite image
        """
        
        # Ensure foreground has alpha channel
        if foreground.mode != 'RGBA':
            foreground = foreground.convert('RGBA')
        
        # Ensure background is RGB
        if background.mode != 'RGB':
            background = background.convert('RGB')
        
        # Resize background to match foreground if needed
        if background.size != foreground.size:
            background = background.resize(foreground.size, Image.Resampling.LANCZOS)
        
        # Convert to numpy arrays
        fg_array = np.array(foreground).astype(np.float32) / 255.0
        bg_array = np.array(background).astype(np.float32) / 255.0
        
        # Extract alpha channel
        alpha = fg_array[:, :, 3:4] * opacity
        fg_rgb = fg_array[:, :, :3]
        
        # Apply blending mode
        if blend_mode == 'normal':
            blended = fg_rgb
        elif blend_mode == 'multiply':
            blended = fg_rgb * bg_array
        elif blend_mode == 'screen':
            blended = 1 - (1 - fg_rgb) * (1 - bg_array)
        elif blend_mode == 'overlay':
            mask = bg_array < 0.5
            blended = np.where(mask, 2 * fg_rgb * bg_array, 1 - 2 * (1 - fg_rgb) * (1 - bg_array))
        else:
            blended = fg_rgb  # Default to normal
        
        # Composite using alpha blending
        result_rgb = alpha * blended + (1 - alpha) * bg_array
        
        # Convert back to PIL Image
        result_array = (np.clip(result_rgb, 0, 1) * 255).astype(np.uint8)
        result = Image.fromarray(result_array, 'RGB')
        
        return result

    def add_shadow(self, 
                   image: Image.Image,
                   shadow_blur: int = 10,
                   shadow_offset: tuple = (5, 5),
                   shadow_opacity: float = 0.3,
                   shadow_color: tuple = (0, 0, 0)) -> Image.Image:
        """
        Add a drop shadow to an image with transparency.
        
        Args:
            image: Input image with alpha channel
            shadow_blur: Blur radius for shadow
            shadow_offset: (x, y) offset for shadow
            shadow_opacity: Opacity of shadow (0.0 to 1.0)
            shadow_color: RGB color of shadow
        
        Returns:
            Image with shadow added
        """
        
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Create shadow layer
        shadow = Image.new('RGBA', image.size, (0, 0, 0, 0))
        
        # Extract alpha channel for shadow shape
        alpha = image.split()[3]
        
        # Create shadow color with alpha
        shadow_rgba = shadow_color + (int(255 * shadow_opacity),)
        
        # Fill shadow with color where alpha exists
        shadow_colored = Image.new('RGBA', image.size, shadow_rgba)
        shadow.paste(shadow_colored, (0, 0), alpha)
        
        # Apply blur to shadow
        if shadow_blur > 0:
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        
        # Create final composite with shadow offset
        final_size = (
            image.size[0] + abs(shadow_offset[0]) + shadow_blur,
            image.size[1] + abs(shadow_offset[1]) +
            shadow_blur
        )
        
        final = Image.new('RGBA', final_size, (0, 0, 0, 0))
        
        # Calculate positions
        shadow_pos = (
            max(0, shadow_offset[0]) + shadow_blur // 2,
            max(0, shadow_offset[1]) + shadow_blur // 2
        )
        
        image_pos = (
            max(0, -shadow_offset[0]) + shadow_blur // 2,
            max(0, -shadow_offset[1]) + shadow_blur // 2
        )
        
        # Paste shadow first, then original image
        final.paste(shadow, shadow_pos, shadow)
        final.paste(image, image_pos, image)
        
        return final

    def create_product_mockup(self,
                             product_image: Image.Image,
                             mockup_template: str = 'white_background',
                             scale: float = 1.0,
                             position: tuple = None,
                             add_reflection: bool = False) -> Image.Image:
        """
        Create a product mockup with the processed image.
        
        Args:
            product_image: Product image with background removed
            mockup_template: Template type ('white_background', 'gradient', 'lifestyle')
            scale: Scale factor for the product
            position: (x, y) position override
            add_reflection: Whether to add floor reflection
        
        Returns:
            Product mockup image
        """
        
        # Ensure product has transparency
        if product_image.mode != 'RGBA':
            product_image = product_image.convert('RGBA')
        
        # Scale product if needed
        if scale != 1.0:
            new_size = (int(product_image.size[0] * scale), int(product_image.size[1] * scale))
            product_image = product_image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Create background based on template
        canvas_size = (1200, 1200)  # Standard mockup size
        
        if mockup_template == 'white_background':
            background = Image.new('RGB', canvas_size, (255, 255, 255))
        elif mockup_template == 'gradient':
            background = self._create_gradient_background(canvas_size)
        elif mockup_template == 'lifestyle':
            background = self._create_lifestyle_background(canvas_size)
        else:
            background = Image.new('RGB', canvas_size, (255, 255, 255))
        
        # Calculate position
        if position is None:
            # Center the product
            pos_x = (canvas_size[0] - product_image.size[0]) // 2
            pos_y = (canvas_size[1] - product_image.size[1]) // 2
            
            # Adjust for reflection if needed
            if add_reflection:
                pos_y = pos_y - product_image.size[1] // 4
        else:
            pos_x, pos_y = position
        
        # Add reflection if requested
        if add_reflection:
            reflection = self._create_reflection(product_image)
            reflection_pos = (pos_x, pos_y + product_image.size[1])
            background.paste(reflection, reflection_pos, reflection)
        
        # Add shadow
        product_with_shadow = self.add_shadow(
            product_image,
            shadow_blur=15,
            shadow_offset=(8, 8),
            shadow_opacity=0.2
        )
        
        # Composite final image
        final = Image.new('RGB', canvas_size, (255, 255, 255))
        final.paste(background, (0, 0))
        final.paste(product_with_shadow, (pos_x - 15, pos_y - 15), product_with_shadow)
        
        return final

    def _create_gradient_background(self, size: tuple) -> Image.Image:
        """Create a gradient background."""
        
        width, height = size
        gradient = Image.new('RGB', size)
        
        # Create vertical gradient from light gray to white
        for y in range(height):
            # Gradient from RGB(240,240,240) to RGB(255,255,255)
            gray_value = int(240 + (255 - 240) * (y / height))
            color = (gray_value, gray_value, gray_value)
            
            # Draw horizontal line
            for x in range(width):
                gradient.putpixel((x, y), color)
        
        return gradient

    def _create_lifestyle_background(self, size: tuple) -> Image.Image:
        """Create a lifestyle background with subtle texture."""
        
        # Create base gradient
        background = self._create_gradient_background(size)
        
        # Add subtle noise texture
        import random
        width, height = size
        pixels = list(background.getdata())
        
        # Add very subtle noise
        for i in range(len(pixels)):
            r, g, b = pixels[i]
            noise = random.randint(-5, 5)
            r = max(0, min(255, r + noise))
            g = max(0, min(255, g + noise))
            b = max(0, min(255, b + noise))
            pixels[i] = (r, g, b)
        
        background.putdata(pixels)
        
        return background

    def _create_reflection(self, image: Image.Image) -> Image.Image:
        """Create a floor reflection of the image."""
        
        # Flip image vertically
        reflection = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        
        # Create gradient mask for fade effect
        width, height = reflection.size
        gradient_mask = Image.new('L', (width, height))
        
        for y in range(height):
            # Fade from 60% opacity at top to 0% at bottom
            opacity = int(60 * (1 - y / height))
            for x in range(width):
                gradient_mask.putpixel((x, y), opacity)
        
        # Apply gradient mask to reflection alpha
        if reflection.mode != 'RGBA':
            reflection = reflection.convert('RGBA')
        
        r, g, b, a = reflection.split()
        
        # Combine original alpha with gradient mask
        reflection_alpha = Image.new('L', (width, height))
        for y in range(height):
            for x in range(width):
                original_alpha = a.getpixel((x, y))
                gradient_alpha = gradient_mask.getpixel((x, y))
                combined_alpha = int((original_alpha / 255) * (gradient_alpha / 255) * 255)
                reflection_alpha.putpixel((x, y), combined_alpha)
        
        # Reconstruct reflection with new alpha
        reflection = Image.merge('RGBA', (r, g, b, reflection_alpha))
        
        return reflection

    def analyze_image_content(self, image: Image.Image) -> Dict[str, any]:
        """
        Analyze image content to suggest optimal processing parameters.
        
        Args:
            image: Input image to analyze
        
        Returns:
            Dictionary with analysis results and recommendations
        """
        
        img_array = np.array(image)
        
        analysis = {
            'image_info': {
                'size': image.size,
                'mode': image.mode,
                'format': image.format,
                'has_transparency': image.mode in ('RGBA', 'LA') or 'transparency' in image.info
            },
            'content_analysis': {},
            'recommendations': {}
        }
        
        # Color analysis
        if len(img_array.shape) == 3:
            # Color distribution
            colors = img_array.reshape(-1, img_array.shape[2])
            unique_colors = len(np.unique(colors.view(np.dtype((np.void, colors.dtype.itemsize * colors.shape[1])))))
            
            # Dominant colors (simplified)
            mean_color = np.mean(colors, axis=0)
            
            # Background detection (corner analysis)
            h, w = img_array.shape[:2]
            corner_size = min(h, w) // 10
            corners = [
                img_array[:corner_size, :corner_size],
                img_array[:corner_size, -corner_size:],
                img_array[-corner_size:, :corner_size],
                img_array[-corner_size:, -corner_size:]
            ]
            corner_colors = [np.mean(corner.reshape(-1, 3), axis=0) for corner in corners]
            corner_similarity = np.std([np.linalg.norm(c - corner_colors[0]) for c in corner_colors])
            
            analysis['content_analysis'].update({
                'unique_colors': int(unique_colors),
                'mean_color': mean_color.tolist(),
                'corner_similarity': float(corner_similarity),
                'likely_uniform_background': corner_similarity < 30
            })
        
        # Edge analysis
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY) if len(img_array.shape) == 3 else img_array
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        
        analysis['content_analysis']['edge_density'] = float(edge_density)
        analysis['content_analysis']['complex_edges'] = edge_density > 0.1
        
        # Contrast analysis
        contrast = gray.std()
        analysis['content_analysis']['contrast'] = float(contrast)
        analysis['content_analysis']['low_contrast'] = contrast < 30
        
        # Generate recommendations
        recommendations = []
        
        if analysis['content_analysis'].get('likely_uniform_background', False):
            recommendations.append({
                'parameter': 'model',
                'value': 'u2net',
                'reason': 'Uniform background detected - standard model should work well'
            })
        else:
            recommendations.append({
                'parameter': 'model',
                'value': 'isnet-general-use',
                'reason': 'Complex background detected - use more robust model'
            })
        
        if analysis['content_analysis'].get('complex_edges', False):
            recommendations.append({
                'parameter': 'enhance_quality',
                'value': True,
                'reason': 'Complex edges detected - quality enhancement recommended'
            })
            recommendations.append({
                'parameter': 'preserve_holes',
                'value': True,
                'reason': 'Complex structure may have holes to preserve'
            })
        
        if analysis['content_analysis'].get('low_contrast', False):
            recommendations.append({
                'parameter': 'enhance_quality',
                'value': True,
                'reason': 'Low contrast image - enhancement will help edge definition'
            })
        
        # Size recommendations
        width, height = image.size
        if width * height > 2000 * 2000:
            recommendations.append({
                'parameter': 'resize',
                'value': 'Consider resizing for faster processing',
                'reason': 'Large image detected - processing may be slow'
            })
        
        analysis['recommendations'] = recommendations
        
        return analysis

    def optimize_for_web(self, 
                        image: Image.Image,
                        max_size: tuple = (1200, 1200),
                        quality: int = 85,
                        format: str = 'PNG') -> Image.Image:
        """
        Optimize processed image for web use.
        
        Args:
            image: Processed image with transparency
            max_size: Maximum dimensions (width, height)
            quality: JPEG quality (if applicable)
            format: Output format ('PNG', 'WEBP')
        
        Returns:
            Optimized image
        """
        
        # Resize if too large
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Optimize based on format
        if format.upper() == 'WEBP':
            # WebP supports transparency and better compression
            from io import BytesIO
            buffer = BytesIO()
            image.save(buffer, format='WEBP', quality=quality, method=6)
            buffer.seek(0)
            optimized = Image.open(buffer)
            return optimized
        
        elif format.upper() == 'PNG':
            # Optimize PNG by reducing colors if possible
            if image.mode == 'RGBA':
                # Check if we can reduce to palette mode
                alpha = image.split()[3]
                if len(set(alpha.getdata())) <= 2:  # Only fully transparent or opaque
                    # Convert to palette mode with transparency
                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                    rgb_image.paste(image, mask=alpha)
                    
                    # Quantize colors
                    quantized = rgb_image.quantize(colors=256)
                    
                    # Add transparency back
                    quantized = quantized.convert('RGBA')
                    quantized.putalpha(alpha)
                    
                    return quantized
            
            return image
        
        else:
            return image

    def create_image_variants(self, 
                             image: Image.Image,
                             variants: List[str] = None) -> Dict[str, Image.Image]:
        """
        Create multiple variants of the processed image.
        
        Args:
            image: Base processed image
            variants: List of variant types to create
        
        Returns:
            Dictionary mapping variant names to images
        """
        
        if variants is None:
            variants = ['original', 'with_shadow', 'white_bg', 'transparent']
        
        results = {}
        
        for variant in variants:
            try:
                if variant == 'original':
                    results[variant] = image.copy()
                
                elif variant == 'with_shadow':
                    results[variant] = self.add_shadow(image)
                
                elif variant == 'white_bg':
                    # Create version with white background
                    white_bg = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'RGBA':
                        white_bg.paste(image, (0, 0), image)
                    else:
                        white_bg = image.convert('RGB')
                    results[variant] = white_bg
                
                elif variant == 'transparent':
                    # Ensure transparency
                    if image.mode != 'RGBA':
                        results[variant] = image.convert('RGBA')
                    else:
                        results[variant] = image.copy()
                
                elif variant == 'square_crop':
                    # Create square crop
                    size = min(image.size)
                    left = (image.size[0] - size) // 2
                    top = (image.size[1] - size) // 2
                    results[variant] = image.crop((left, top, left + size, top + size))
                
                elif variant == 'mockup':
                    # Create simple mockup
                    results[variant] = self.create_product_mockup(image)
                
                else:
                    logger.warning(f"Unknown variant type: {variant}")
            
            except Exception as e:
                logger.error(f"Failed to create variant '{variant}': {e}")
        
        return results

    def save_with_metadata(self, 
                          image: Image.Image,
                          filepath: str,
                          metadata: Dict[str, any] = None) -> None:
        """
        Save image with processing metadata.
        
        Args:
            image: Image to save
            filepath: Output file path
            metadata: Additional metadata to include
        """
        
        from PIL.PngImagePlugin import PngInfo
        import json
        from datetime import datetime
        
        # Prepare metadata
        meta = {
            'processed_by': 'AdvancedBackgroundRemover',
            'processed_at': datetime.now().isoformat(),
            'original_size': getattr(image, '_original_size', image.size),
            'processing_model': getattr(image, '_processing_model', 'unknown'),
            'version': '1.0'
        }
        
        if metadata:
            meta.update(metadata)
        
        # Save based on format
        file_ext = filepath.lower().split('.')[-1]
        
        if file_ext == 'png':
            # PNG supports text metadata
            pnginfo = PngInfo()
            for key, value in meta.items():
                pnginfo.add_text(key, str(value))
            image.save(filepath, 'PNG', pnginfo=pnginfo)
        
        elif file_ext in ['jpg', 'jpeg']:
            # JPEG with EXIF (limited)
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            # Add basic info to EXIF
            image.save(filepath, 'JPEG', quality=95)
        
        else:
            # Default save
            image.save(filepath)
        
        # Also save metadata as separate JSON file
        meta_filepath = filepath.rsplit('.', 1)[0] + '_metadata.json'
        with open(meta_filepath, 'w') as f:
            json.dump(meta, f, indent=2)

    def get_processing_stats(self) -> Dict[str, any]:
        """Get processing statistics and performance metrics."""
        
        return {
            'total_processed': getattr(self, '_total_processed', 0),
            'average_processing_time': getattr(self, '_avg_processing_time', 0),
            'preferred_model': getattr(self, '_preferred_model', 'auto'),
            'success_rate': getattr(self, '_success_rate', 0),
            'cache_hits': getattr(self, '_cache_hits', 0),
            'memory_usage': self._get_memory_usage()
        }

    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': process.memory_percent()
        }

    def cleanup_resources(self) -> None:
        """Clean up resources and temporary files."""
        
        # Clear any cached models
        if hasattr(self, '_model_cache'):
            self._model_cache.clear()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        logger.info("🧹 Resources cleaned up")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup_resources()


# Example usage and testing functions
def demo_advanced_removal():
    """Demonstrate advanced background removal capabilities."""
    
    print("🚀 Advanced Background Removal Demo")
    print("=" * 50)
    
    # Initialize the remover
    with AdvancedBackgroundRemover() as remover:
        
        # Example with a sample image (you would load your own)
        try:
            # Load test image
            test_image = Image.new('RGB', (400, 400), (255, 255, 255))
            # In practice, you'd load: test_image = Image.open('your_image.jpg')
            
            print("📊 Analyzing image content...")
            analysis = remover.analyze_image_content(test_image)
            print(f"   Image size: {analysis['image_info']['size']}")
            print(f"   Recommendations: {len(analysis['recommendations'])}")
            
            print("\n🎯 Removing background...")
            result = remover.remove_background(
                image=test_image,
                model='auto',
                preserve_holes=True,
                enhance_quality=True
            )
            
            print("✅ Background removed successfully!")
            
            print("\n🎨 Creating variants...")
            variants = remover.create_image_variants(
                result, 
                ['original', 'with_shadow', 'white_bg', 'mockup']
            )
            print(f"   Created {len(variants)} variants")
            
            print("\n💾 Saving results...")
            for variant_name, variant_image in variants.items():
                filename = f"demo_result_{variant_name}.png"
                remover.save_with_metadata(
                    variant_image, 
                    filename,
                    {'variant': variant_name, 'demo': True}
                )
                print(f"   Saved: {filename}")
            
            print("\n📈 Processing stats:")
            stats = remover.get_processing_stats()
            for key, value in stats.items():
                print(f"   {key}: {value}")
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")


if __name__ == "__main__":
    # Run demo
    demo_advanced_removal()
    
    # Example of batch processing
    print("\n" + "=" * 50)
    print("📁 Batch Processing Example")
    
    # Uncomment to test batch processing:
    # with AdvancedBackgroundRemover() as remover:
    #     results = remover.batch_process(
    #         input_dir='input_images/',
    #         output_dir='output_images/',
    #         model='u2net',
    #         preserve_holes=True,
    #         enhance_quality=True,
    #         max_workers=2
    #     )
    #     print(f"Batch processing completed: {results}")
class EnhancedImageEngine:
    """
    Wrapper na ProductBackgroundRemover z prostym interfejsem,
    by był zgodny z pipeline Retixly 3.0.
    """
    def __init__(self):
        self.bg_remover = ProductBackgroundRemover()

    def process_single(self, image, settings, progress_callback=None):
        """
        Unified API: obsługa wywołania z GUI.
        """
        quality = settings.get('bg_quality', 'high')
        preserve_holes = settings.get('preserve_holes', True)
        edge_refinement = settings.get('edge_refinement', True)
        bg_mode = settings.get('bg_mode', 'remove')
        model_name = settings.get('model_name', 'auto')
        debug_masks = settings.get('debug_masks', False)
        force_binary_alpha = settings.get('force_binary_alpha', True)
        feathering = settings.get('feathering', 0)

        if bg_mode == 'remove':
            return self.bg_remover.remove_background_professional(
                image=image,
                quality_level=quality,
                preserve_holes=preserve_holes,
                edge_refinement=edge_refinement,
                model_name=model_name,
                debug_masks=debug_masks,
                force_binary_alpha=force_binary_alpha,
                feathering=feathering
            )
        else:
            # domyślne fallback
            return image
