"""
Windows Detail Enhancement Module
Specialized algorithms for improving edge quality and fine details
"""

import numpy as np
import cv2
from PIL import Image, ImageFilter, ImageEnhance
import logging

logger = logging.getLogger(__name__)

class WindowsDetailEnhancer:
    """Enhances fine details and edges specifically for Windows processing"""
    
    def __init__(self):
        self.name = "Windows Detail Enhancer"
        
    def enhance_mask_details(self, mask, original_image, enhancement_level='high'):
        """
        Enhanced detail preservation for masks
        
        Args:
            mask: Binary mask (numpy array)
            original_image: Original PIL Image
            enhancement_level: 'low', 'medium', 'high', 'ultra'
        """
        try:
            if mask is None or original_image is None:
                return mask
                
            # Convert to numpy if needed
            if isinstance(mask, Image.Image):
                mask = np.array(mask)
            
            original_array = np.array(original_image.convert('RGB'))
            
            # Enhancement parameters based on level
            enhancement_params = {
                'low': {'blur_radius': 1.0, 'unsharp_strength': 0.3, 'edge_weight': 0.2},
                'medium': {'blur_radius': 0.8, 'unsharp_strength': 0.5, 'edge_weight': 0.4},
                'high': {'blur_radius': 0.6, 'unsharp_strength': 0.8, 'edge_weight': 0.6},
                'ultra': {'blur_radius': 0.4, 'unsharp_strength': 1.2, 'edge_weight': 0.8}
            }
            
            params = enhancement_params.get(enhancement_level, enhancement_params['high'])
            
            # Step 1: Edge-guided smoothing
            enhanced_mask = self._edge_guided_smoothing(
                mask, original_array, params['blur_radius']
            )
            
            # Step 2: Unsharp masking for alpha channel
            enhanced_mask = self._unsharp_mask_alpha(
                enhanced_mask, params['unsharp_strength']
            )
            
            # Step 3: Edge reinforcement
            enhanced_mask = self._reinforce_edges(
                enhanced_mask, original_array, params['edge_weight']
            )
            
            # Step 4: Anti-aliasing
            enhanced_mask = self._apply_anti_aliasing(enhanced_mask)
            
            logger.info(f"Detail enhancement completed with level: {enhancement_level}")
            return enhanced_mask
            
        except Exception as e:
            logger.error(f"Detail enhancement failed: {e}")
            return mask
    
    def _edge_guided_smoothing(self, mask, original_array, blur_radius):
        """Apply edge-guided smoothing to preserve important boundaries"""
        try:
            # Convert mask to float for processing
            mask_float = mask.astype(np.float32) / 255.0
            
            # Detect edges in original image
            gray = cv2.cvtColor(original_array, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edges_float = edges.astype(np.float32) / 255.0
            
            # Create edge guidance map
            edge_guidance = cv2.GaussianBlur(edges_float, (5, 5), 1.0)
            edge_guidance = 1.0 - edge_guidance  # Invert so edges preserve detail
            
            # Apply guided filtering
            blurred_mask = cv2.GaussianBlur(mask_float, (0, 0), blur_radius)
            
            # Blend based on edge guidance
            guided_mask = mask_float * edge_guidance + blurred_mask * (1.0 - edge_guidance)
            
            return (guided_mask * 255).astype(np.uint8)
            
        except Exception as e:
            logger.error(f"Edge-guided smoothing failed: {e}")
            return mask
    
    def _unsharp_mask_alpha(self, mask, strength):
        """Apply unsharp masking to enhance alpha channel details"""
        try:
            mask_float = mask.astype(np.float32) / 255.0
            
            # Create blurred version
            blurred = cv2.GaussianBlur(mask_float, (0, 0), 1.0)
            
            # Unsharp mask formula: original + strength * (original - blurred)
            unsharp = mask_float + strength * (mask_float - blurred)
            
            # Clip to valid range
            unsharp = np.clip(unsharp, 0.0, 1.0)
            
            return (unsharp * 255).astype(np.uint8)
            
        except Exception as e:
            logger.error(f"Unsharp masking failed: {e}")
            return mask
    
    def _reinforce_edges(self, mask, original_array, edge_weight):
        """Reinforce edges using original image information"""
        try:
            # Detect edges in both mask and original
            mask_edges = cv2.Canny(mask, 50, 150)
            
            gray = cv2.cvtColor(original_array, cv2.COLOR_RGB2GRAY)
            image_edges = cv2.Canny(gray, 30, 100)
            
            # Combine edge information
            combined_edges = cv2.bitwise_or(mask_edges, image_edges)
            
            # Dilate edges slightly for better integration
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            combined_edges = cv2.dilate(combined_edges, kernel, iterations=1)
            
            # Apply edge reinforcement
            mask_float = mask.astype(np.float32)
            edge_mask = combined_edges.astype(np.float32) / 255.0
            
            # Enhance edges
            reinforced = mask_float + edge_weight * edge_mask * 50
            reinforced = np.clip(reinforced, 0, 255)
            
            return reinforced.astype(np.uint8)
            
        except Exception as e:
            logger.error(f"Edge reinforcement failed: {e}")
            return mask
    
    def _apply_anti_aliasing(self, mask):
        """Apply anti-aliasing for smoother edges"""
        try:
            # Convert to float for sub-pixel precision
            mask_float = mask.astype(np.float32) / 255.0
            
            # Apply slight Gaussian blur for anti-aliasing
            anti_aliased = cv2.GaussianBlur(mask_float, (3, 3), 0.5)
            
            return (anti_aliased * 255).astype(np.uint8)
            
        except Exception as e:
            logger.error(f"Anti-aliasing failed: {e}")
            return mask
    
    def enhance_transparency_quality(self, image, quality_level='high'):
        """
        Enhance transparency quality for final output
        
        Args:
            image: PIL Image with RGBA mode
            quality_level: 'medium', 'high', 'ultra'
        """
        try:
            if image.mode != 'RGBA':
                return image
                
            # Extract channels
            r, g, b, a = image.split()
            
            # Enhance alpha channel
            enhanced_alpha = self._enhance_alpha_channel(np.array(a), quality_level)
            enhanced_alpha_pil = Image.fromarray(enhanced_alpha)
            
            # Reconstruct image
            enhanced_image = Image.merge('RGBA', (r, g, b, enhanced_alpha_pil))
            
            logger.info(f"Transparency quality enhanced: {quality_level}")
            return enhanced_image
            
        except Exception as e:
            logger.error(f"Transparency enhancement failed: {e}")
            return image
    
    def _enhance_alpha_channel(self, alpha_array, quality_level):
        """Enhance alpha channel with different quality levels"""
        try:
            if quality_level == 'medium':
                # Basic enhancement
                enhanced = cv2.bilateralFilter(alpha_array, 5, 50, 50)
                return enhanced
                
            elif quality_level == 'high':
                # Advanced enhancement
                # Step 1: Bilateral filter for edge preservation
                enhanced = cv2.bilateralFilter(alpha_array, 9, 75, 75)
                
                # Step 2: Slight unsharp mask
                blurred = cv2.GaussianBlur(enhanced.astype(np.float32), (0, 0), 1.0)
                enhanced_float = enhanced.astype(np.float32)
                enhanced = enhanced_float + 0.3 * (enhanced_float - blurred)
                enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
                
                return enhanced
                
            elif quality_level == 'ultra':
                # Ultra-high quality enhancement
                alpha_float = alpha_array.astype(np.float32) / 255.0
                
                # Step 1: Multi-scale bilateral filtering
                scales = [3, 5, 7]
                enhanced = np.zeros_like(alpha_float)
                
                for scale in scales:
                    filtered = cv2.bilateralFilter(
                        (alpha_float * 255).astype(np.uint8), 
                        scale, 75, 75
                    ).astype(np.float32) / 255.0
                    enhanced += filtered / len(scales)
                
                # Step 2: Edge-preserving smoothing
                kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]) * 0.1
                enhanced = cv2.filter2D(enhanced, -1, kernel)
                
                # Step 3: Final unsharp mask
                blurred = cv2.GaussianBlur(enhanced, (0, 0), 0.8)
                enhanced = enhanced + 0.5 * (enhanced - blurred)
                
                enhanced = np.clip(enhanced * 255, 0, 255).astype(np.uint8)
                return enhanced
                
            else:
                return alpha_array
                
        except Exception as e:
            logger.error(f"Alpha channel enhancement failed: {e}")
            return alpha_array
    
    def refine_hair_and_fur(self, mask, original_image):
        """Special refinement for hair and fur details"""
        try:
            original_array = np.array(original_image.convert('RGB'))
            gray = cv2.cvtColor(original_array, cv2.COLOR_RGB2GRAY)
            
            # Detect fine structures (hair, fur)
            # Use multiple scales to catch different hair thicknesses
            fine_details = np.zeros_like(gray, dtype=np.float32)
            
            for sigma in [0.5, 1.0, 1.5]:
                # Gaussian of different scales
                g1 = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), sigma)
                g2 = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), sigma * 1.6)
                
                # Difference of Gaussians to detect fine structures
                dog = g1 - g2
                fine_details += np.abs(dog)
            
            # Normalize
            fine_details = fine_details / fine_details.max() * 255
            
            # Create hair/fur mask
            _, hair_mask = cv2.threshold(fine_details.astype(np.uint8), 30, 255, cv2.THRESH_BINARY)
            
            # Refine original mask in hair regions
            mask_float = mask.astype(np.float32)
            hair_regions = hair_mask.astype(np.float32) / 255.0
            
            # In hair regions, use more conservative thresholding
            conservative_mask = cv2.GaussianBlur(mask_float, (3, 3), 0.5)
            refined_mask = mask_float * (1 - hair_regions) + conservative_mask * hair_regions
            
            return refined_mask.astype(np.uint8)
            
        except Exception as e:
            logger.error(f"Hair/fur refinement failed: {e}")
            return mask
    
    def create_soft_edges(self, image, feather_radius=2):
        """Create soft, natural-looking edges"""
        try:
            if image.mode != 'RGBA':
                return image
                
            # Extract alpha channel
            alpha = np.array(image.split()[-1])
            
            # Create distance transform for soft edges
            # Find edges first
            edges = cv2.Canny(alpha, 50, 150)
            
            # Distance transform from edges
            dist_transform = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 5)
            
            # Create soft transition
            soft_alpha = alpha.astype(np.float32)
            edge_regions = dist_transform < feather_radius
            
            if np.any(edge_regions):
                # Apply Gaussian blur in edge regions
                blurred_alpha = cv2.GaussianBlur(soft_alpha, (feather_radius*2+1, feather_radius*2+1), feather_radius/3)
                soft_alpha[edge_regions] = blurred_alpha[edge_regions]
            
            # Reconstruct image
            rgb = image.convert('RGB')
            soft_alpha_pil = Image.fromarray(soft_alpha.astype(np.uint8))
            
            return Image.merge('RGBA', rgb.split() + (soft_alpha_pil,))
            
        except Exception as e:
            logger.error(f"Soft edge creation failed: {e}")
            return image

def create_detail_enhancer():
    """Factory function to create detail enhancer"""
    return WindowsDetailEnhancer()