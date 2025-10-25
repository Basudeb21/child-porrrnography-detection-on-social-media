# nsfw_detector.py
import tensorflow as tf
import numpy as np
import cv2
import os
import sys
import time
from colorama import init, Fore, Style

init()

tf.config.set_visible_devices([], 'GPU')
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

class NSFWDetector:
    def __init__(self, model_dir='mobilenet_v2_140_224'):
        """Initialize with enhanced classification logic"""
        try:
            self.model = tf.saved_model.load(model_dir)
            self.serve = self.model.signatures['serving_default']
            self.output_key = list(self.serve.structured_outputs.keys())[0]
            self.classes = ["natural", "hentai", "porn", "sexy"]
            print(f"NSFW detector initialized (Output key: {self.output_key})")
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {str(e)}")

    def preprocess_image(self, image_path, crop_center=False):
        """Optimized image preprocessing with optional center crop"""
        try:
            img = cv2.imread(image_path, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not read image file")
            
            if crop_center:
                h, w, _ = img.shape
                crop_size = min(h, w) // 2
                cx, cy = w // 2, h // 2
                img = img[cy - crop_size//2:cy + crop_size//2, cx - crop_size//2:cx + crop_size//2]

            img = cv2.cvtColor(cv2.resize(img, (224, 224)), cv2.COLOR_BGR2RGB)
            return (img.astype('float32') / 255.0)[np.newaxis, ...]
        except Exception as e:
            raise ValueError(f"Image processing failed: {str(e)}")

    def _analyze_content(self, img_array):
        """Enhanced content analysis with better skin detection"""
        img = (img_array[0] * 255).astype('uint8')
        
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        ycrcb = cv2.cvtColor(img, cv2.COLOR_RGB2YCrCb)
        
        lower_hsv = np.array([0, 30, 60], dtype=np.uint8)
        upper_hsv = np.array([25, 255, 255], dtype=np.uint8)
        hsv_mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
        
        lower_ycrcb = np.array([0, 133, 77], dtype=np.uint8)
        upper_ycrcb = np.array([255, 173, 127], dtype=np.uint8)
        ycrcb_mask = cv2.inRange(ycrcb, lower_ycrcb, upper_ycrcb)
        
        skin_mask = cv2.bitwise_and(hsv_mask, ycrcb_mask)
        skin_ratio = cv2.countNonZero(skin_mask) / (224 * 224)
        
        center_mask = np.zeros((224, 224), dtype=np.uint8)
        cv2.circle(center_mask, (112, 112), 75, 255, -1)
        center_focus = cv2.countNonZero(cv2.bitwise_and(skin_mask, center_mask)) / (np.pi * 75**2)
        
        return {
            'skin_ratio': skin_ratio,
            'center_focus': center_focus,
            'is_centered': center_focus > 0.4
        }

    def _classify(self, img_array):
        """Run model prediction and return original scores"""
        outputs = self.serve(tf.convert_to_tensor(img_array))
        predictions = outputs[self.output_key][0].numpy()
        return {
            "natural": (predictions[0] + predictions[2]) / 2,
            "hentai": predictions[1],
            "porn": predictions[3],
            "sexy": predictions[4]
        }

    def predict(self, image_path, threshold=0.8):
        """Advanced prediction with sexy/porn adjustment"""
        try:
            img_array = self.preprocess_image(image_path)
            features = self._analyze_content(img_array)
            base_scores = self._classify(img_array)

            center_array = self.preprocess_image(image_path, crop_center=True)
            center_scores = self._classify(center_array)

            porn_boost_center = center_scores['porn'] - base_scores['porn']

            if features['skin_ratio'] > 0.25:
                if porn_boost_center > 0.15:
                    base_scores['porn'] = min(base_scores['porn'] + porn_boost_center, 1.0)
                elif base_scores['porn'] > base_scores['sexy']:
                    base_scores['porn'] *= 0.8
                    base_scores['sexy'] = min(base_scores['sexy'] * 1.3, 1.0)
                elif base_scores['sexy'] > base_scores['porn'] and features['skin_ratio'] > 0.5:
                    base_scores['porn'] *= 1.1

            if base_scores['porn'] > 0.5 and features['skin_ratio'] < 0.4:
                base_scores['sexy'] = max(base_scores['sexy'], base_scores['porn'])
                base_scores['porn'] *= 0.5

            total = sum(base_scores.values())
            percentages = {k: float(v / total * 100) for k, v in base_scores.items()}

            is_nsfw = (
                percentages["porn"] > threshold*100 or
                percentages["hentai"] > threshold*100 or
                (percentages["sexy"] > 75 and features['skin_ratio'] > 0.35)
            )
            
            return {
                "filename": os.path.basename(image_path),
                "scores": percentages,
                "is_nsfw": is_nsfw,
                "skin_ratio": round(features['skin_ratio']*100, 2),
                "error": None
            }
        except Exception as e:
            return {
                "filename": os.path.basename(image_path),
                "error": str(e),
                "scores": None,
                "is_nsfw": None,
                "skin_ratio": None
            }

def print_results(result, threshold):
    if result.get('error'):
        print(f"\n{Fore.RED}Error:{Style.RESET_ALL} {result['error']}")
        return
    
    print(f"\nResults:")
    for cls, percent in sorted(result['scores'].items(), key=lambda x: x[1], reverse=True):
        if cls == 'natural':
            color = Fore.GREEN
        elif cls == 'sexy' and percent > 60:
            color = Fore.MAGENTA
        elif cls in ['porn','hentai'] and percent > threshold*100:
            color = Fore.RED
        else:
            color = Fore.YELLOW
        print(f"{color}{cls.upper()+':':<10} {percent:.2f}%{Style.RESET_ALL}")
    
    print(f"\nSkin Exposure: {result['skin_ratio']}%")
    
    nsfw_score = max(result['scores']['porn'], result['scores']['hentai'])
    conclusion = "NSFW" if result['is_nsfw'] else "Safe"
    color = Fore.RED if result['is_nsfw'] else Fore.GREEN
    
    print(f"\nNSFW Confidence: {nsfw_score:.2f}%")
    print(f"{color}Conclusion: {conclusion}{Style.RESET_ALL} (Threshold: {threshold*100}%)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <image.jpg> [threshold=0.8]")
        sys.exit(1)
    
    try:
        threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.8
        if not 0 <= threshold <= 1:
            raise ValueError
    except ValueError:
        print(f"{Fore.RED}Error:{Style.RESET_ALL} Threshold must be between 0 and 1")
        sys.exit(1)
    
    print("Initializing Advanced NSFW Detector...")
    start_time = time.time()
    
    try:
        detector = NSFWDetector()
        print(f"Model loaded in {time.time()-start_time:.2f}s")
        
        print(f"\nAnalyzing {sys.argv[1]} with enhanced classifier...")
        result = detector.predict(sys.argv[1], threshold)
        print_results(result, threshold)
        
    except Exception as e:
        print(f"{Fore.RED}Failed:{Style.RESET_ALL} {str(e)}")
        sys.exit(1)
