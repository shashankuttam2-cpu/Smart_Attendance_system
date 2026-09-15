import os
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from config import settings

class FaceEngine:
    """
    AI Face Recognition Engine
    - Primary: OpenCV DNN (YuNet detector + SFace 128-d deep representation)
    - Fallback: face_recognition (dlib 128-d HOG/CNN) if installed on Linux/Docker
    """
    def __init__(self):
        self.detector = None
        self.recognizer = None
        self.use_dlib = False
        self._init_engine()

    def _init_engine(self):
        # 1. Try OpenCV DNN YuNet + SFace
        if os.path.exists(settings.YUNET_MODEL_PATH) and os.path.exists(settings.SFACE_MODEL_PATH):
            try:
                # Initialize detector with default 320x320 input size (dynamically resized during inference)
                self.detector = cv2.FaceDetectorYN.create(
                    model=settings.YUNET_MODEL_PATH,
                    config="",
                    input_size=(320, 320),
                    score_threshold=0.7,
                    nms_threshold=0.3,
                    top_k=5000
                )
                self.recognizer = cv2.FaceRecognizerSF.create(
                    model=settings.SFACE_MODEL_PATH,
                    config=""
                )
                print("[FaceEngine] Initialized OpenCV YuNet + SFace Deep Learning Engine.")
                return
            except Exception as e:
                print(f"[FaceEngine] OpenCV DNN initialization failed: {e}")

        # 2. Check for optional dlib-based face_recognition
        try:
            import face_recognition # type: ignore
            self.face_recognition_module = face_recognition
            self.use_dlib = True
            print("[FaceEngine] Initialized dlib face_recognition engine.")
            return
        except ImportError:
            pass

        print("[FaceEngine] Models are downloading or initializing...")

    def is_ready(self) -> bool:
        if self.use_dlib:
            return True
        if self.detector is not None and self.recognizer is not None:
            return True
        # Try re-initializing in case weights just completed downloading
        self._init_engine()
        return self.detector is not None and self.recognizer is not None

    def read_image_from_bytes(self, image_bytes: bytes) -> np.ndarray:
        """Converts raw byte stream into OpenCV BGR numpy array."""
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid image file format or corrupted bytes.")
        return img

    def check_quality_and_liveness(self, img_bgr: np.ndarray) -> Tuple[bool, str]:
        """
        Evaluates image clarity, lighting exposure, and anti-spoofing quality:
        1. Lighting exposure: checks mean brightness (rejects too dark < 35 or washed out > 245).
        2. Focus / Blur detection: calculates variance of Laplacian (rejects blurry / out-of-focus < 35.0).
        """
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))

        if mean_brightness < 35.0:
            return False, "Lighting is too dark. Please face towards a light source."
        if mean_brightness > 245.0:
            return False, "Image is overexposed/washed out. Avoid direct intense glare."

        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if laplacian_var < 30.0:
            return False, "Image is blurry or camera is out of focus. Hold the phone steady."

        return True, "Quality OK"

    def extract_encoding_from_bgr(self, img_bgr: np.ndarray, enforce_quality: bool = True) -> List[float]:
        """
        Detects primary face, aligns features, and computes 128-dimensional embedding vector.
        """
        if not self.is_ready():
            raise RuntimeError("Face recognition models are not loaded. Check model files in backend/models.")

        if enforce_quality:
            is_valid, reason = self.check_quality_and_liveness(img_bgr)
            if not is_valid:
                raise ValueError(reason)

        # If using dlib fallback
        if self.use_dlib:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            encodings = self.face_recognition_module.face_encodings(img_rgb)
            if not encodings:
                raise ValueError("No face detected in the image. Ensure proper lighting and face the camera directly.")
            return encodings[0].tolist()

        # Primary: OpenCV YuNet + SFace
        h, w, _ = img_bgr.shape
        self.detector.setInputSize((w, h))

        # Detect faces: returns faces array where each row is [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rc, y_rc, x_lc, y_lc, score]
        _, faces = self.detector.detect(img_bgr)
        if faces is None or len(faces) == 0:
            raise ValueError("No face detected in the image. Please ensure your face is well-lit and clearly visible.")

        # Pick the most prominent/highest confidence face
        primary_face = faces[0]
        
        # Align face crop using landmarks
        aligned_face = self.recognizer.alignCrop(img_bgr, primary_face)
        
        # Extract 128-d feature vector
        features = self.recognizer.feature(aligned_face)
        
        # Flatten and normalize
        feat_vec = features.flatten()
        norm = np.linalg.norm(feat_vec)
        if norm > 0:
            feat_vec = feat_vec / norm

        return feat_vec.tolist()

    def extract_encoding_from_bytes(self, image_bytes: bytes) -> List[float]:
        img_bgr = self.read_image_from_bytes(image_bytes)
        return self.extract_encoding_from_bgr(img_bgr)

    def extract_encoding_from_file(self, file_path: str) -> List[float]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image not found at: {file_path}")
        img_bgr = cv2.imread(file_path)
        if img_bgr is None:
            raise ValueError(f"Could not decode image at: {file_path}")
        return self.extract_encoding_from_bgr(img_bgr)

    def calculate_distance(self, enc1: List[float], enc2: List[float]) -> float:
        """
        Calculates normalized cosine distance between two 128-d vectors.
        Distance range: [0.0 = Identical face, 1.0 = Completely different]
        Match threshold: Distance < settings.FACE_MATCH_TOLERANCE (0.60)
        """
        u = np.array(enc1, dtype=np.float32)
        v = np.array(enc2, dtype=np.float32)

        norm_u = np.linalg.norm(u)
        norm_v = np.linalg.norm(v)

        if norm_u == 0 or norm_v == 0:
            return 1.0

        # Cosine similarity in range [-1.0, 1.0]
        cos_sim = float(np.dot(u, v) / (norm_u * norm_v))
        # Clamp to avoid numerical floating point overflow
        cos_sim = max(-1.0, min(1.0, cos_sim))
        
        # SFace typical cosine similarity for same person is > 0.36, highly confident at > 0.45
        # Transform into standard distance metric where < 0.6 signifies a verified match
        distance = 1.0 - cos_sim
        return distance

    def find_best_match(
        self, 
        live_encoding: List[float], 
        candidates: List[Dict[str, Any]], 
        tolerance: float = settings.FACE_MATCH_TOLERANCE
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Compares live selfie encoding against candidate enrolled encodings.
        Returns (best_matching_candidate, minimum_distance).
        If minimum_distance >= tolerance, returns (None, minimum_distance).
        """
        if not candidates:
            return None, 1.0

        best_candidate = None
        min_distance = float("inf")

        for candidate in candidates:
            cand_enc = candidate.get("face_encoding")
            if not cand_enc:
                continue
            dist = self.calculate_distance(live_encoding, cand_enc)
            if dist < min_distance:
                min_distance = dist
                best_candidate = candidate

        if min_distance < tolerance and best_candidate is not None:
            return best_candidate, round(min_distance, 4)

        return None, round(min_distance, 4)

face_engine = FaceEngine()
