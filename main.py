#!/usr/bin/env python3
"""
DataMatrix Scanner v2.1 - Version optimisée avec améliorations qualité
Intègre toutes les optimisations du guide : performance, qualité photo, détection améliorée
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import serial
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
from pylibdmtx import pylibdmtx

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration globale
IMAGES_DIR = Path("images")
IMAGES_DIR.mkdir(exist_ok=True)

# Variables globales
app = FastAPI(title="DataMatrix Scanner", version="2.1.0")
camera: Optional[Picamera2] = None
serial_connection: Optional[serial.Serial] = None
current_websocket: Optional[WebSocket] = None

# Configuration des paramètres
app_settings = {
    "scan_mode": "datamatrix",
    "detection_mode": "automatique",
    "lighting_mode": "blanc",
    "quality_mode": "standard",  # NOUVEAU: standard, haute, expert
    "manual_of": ""
}

# NOUVEAUX signaux série étendus
SERIAL_SIGNALS = {
    "leds_blanches": b'\x01',
    "lampe_uv": b'\x02',
    "leds_faible": b'\x03',
    "leds_moyen": b'\x04',
    "leds_fort": b'\x05',
    "photo_mode": b'\x06',
    "uv_doux": b'\x07',
}

# Configurations qualité
QUALITY_CONFIGS = {
    "standard": {
        "resolution": (4624, 3472),
        "jpeg_quality": 85,
        "noise_reduction": False,
        "post_processing": False,
        "multiple_shots": 1
    },
    "haute": {
        "resolution": (4624, 3472),
        "jpeg_quality": 95,
        "noise_reduction": True,
        "post_processing": True,
        "multiple_shots": 3
    },
    "expert": {
        "resolution": (4624, 3472),
        "jpeg_quality": 98,
        "noise_reduction": True,
        "post_processing": True,
        "multiple_shots": 5,
        "bracket_exposure": True
    }
}

# Montage des fichiers statiques
app.mount("/images", StaticFiles(directory="images"), name="images")


class EnhancedCameraManager:
    """
    Gestionnaire de caméra optimisé avec améliorations qualité
    Intègre toutes les optimisations du guide
    """
    
    def __init__(self):
        self.picam2 = None
        self.is_streaming = False
        self.current_frame = None
        self.zoom_center = (0.5, 0.5)
        self.zoom_factor = 1.0
        self.preview_config = None
        self.still_config = None
        self._current_focus = None
        
        # Optimisations performance
        self._frame_buffer = []
        self._buffer_lock = threading.Lock()
        self._capture_thread = None
        self._stop_capture = False
        self._executor = ThreadPoolExecutor(max_workers=3)
        
        # Nouveaux paramètres qualité
        self._quality_config = QUALITY_CONFIGS["standard"]
        
    async def initialize(self):
        """Initialise la caméra avec optimisations complètes"""
        try:
            self.picam2 = Picamera2()
            
            from libcamera import controls
            
            # Configuration prévisualisation OPTIMISÉE
            self.preview_config = self.picam2.create_preview_configuration(
                main={"size": (1280, 720), "format": "RGB888"},
                controls={
                    "AfMode": controls.AfModeEnum.Continuous,
                    "AfSpeed": controls.AfSpeedEnum.Fast,
                    "AeEnable": True,
                    "AwbEnable": True,
                    "Brightness": 0.0,
                    "Contrast": 1.0,
                    "Saturation": 1.0,
                    "Sharpness": 1.0,
                    "NoiseReductionMode": controls.draft.NoiseReductionModeEnum.HighQuality,
                    "FrameRate": 30
                }
            )
            
            # Configuration photo AMÉLIORÉE
            self._create_enhanced_still_config()
            
            # Démarrage
            self.picam2.configure(self.preview_config)
            self.picam2.start()
            
            logger.info("Caméra initialisée avec optimisations complètes")
            
            # Focus initial
            await self._perform_initial_autofocus()
            
            # Thread de capture optimisé
            self._start_background_capture()
            
            self.is_streaming = True
            logger.info("Caméra prête - Mode haute performance + qualité")
            
        except Exception as e:
            logger.error(f"Erreur initialisation caméra: {e}")
            raise
    
    def _create_enhanced_still_config(self):
        """Crée la configuration photo améliorée selon le mode qualité"""
        from libcamera import controls
        
        quality_config = self._quality_config
        
        # Configuration avancée selon le mode
        if app_settings["quality_mode"] == "expert":
            # Mode expert avec paramètres manuels
            self.still_config = self.picam2.create_still_configuration(
                main={"size": quality_config["resolution"], "format": "RGB888"},
                controls={
                    "AfMode": controls.AfModeEnum.Manual,
                    "LensPosition": self._current_focus,
                    "AeEnable": False,
                    "AnalogueGain": 1.0,
                    "DigitalGain": 1.0,
                    "ExposureTime": 10000,
                    "AwbEnable": False,
                    "ColourGains": (1.4, 1.2),
                    "Sharpness": 1.2,
                    "Contrast": 1.1,
                    "NoiseReductionMode": controls.draft.NoiseReductionModeEnum.HighQuality
                }
            )
        else:
            # Mode standard/haute avec auto
            self.still_config = self.picam2.create_still_configuration(
                main={"size": quality_config["resolution"], "format": "RGB888"},
                controls={
                    "AfMode": controls.AfModeEnum.Manual,
                    "LensPosition": self._current_focus,
                    "AeEnable": True,
                    "AwbEnable": True,
                    "Brightness": 0.0,
                    "Contrast": 1.0,
                    "Saturation": 1.0,
                    "Sharpness": 1.0,
                    "NoiseReductionMode": controls.draft.NoiseReductionModeEnum.HighQuality
                }
            )
    
    def set_quality_mode(self, mode: str):
        """Change le mode qualité"""
        if mode in QUALITY_CONFIGS:
            self._quality_config = QUALITY_CONFIGS[mode]
            self._create_enhanced_still_config()
            logger.info(f"Mode qualité changé vers: {mode}")
    
    def _start_background_capture(self):
        """Thread de capture en arrière-plan optimisé"""
        self._stop_capture = False
        self._capture_thread = threading.Thread(target=self._background_capture_loop, daemon=True)
        self._capture_thread.start()
        logger.info("Thread capture optimisé démarré")
    
    def _background_capture_loop(self):
        """Boucle de capture optimisée avec contrôle FPS"""
        while not self._stop_capture:
            try:
                if not self.picam2 or not self.picam2.started:
                    time.sleep(0.1)
                    continue
                
                array = self.picam2.capture_array()
                
                frame_data = {
                    'array': array,
                    'timestamp': time.time()
                }
                
                with self._buffer_lock:
                    self._frame_buffer.append(frame_data)
                    if len(self._frame_buffer) > 3:
                        self._frame_buffer.pop(0)
                
                time.sleep(0.033)  # 30 FPS
                
            except Exception as e:
                logger.debug(f"Erreur capture arrière-plan: {e}")
                time.sleep(0.1)
    
    def _get_latest_frame(self):
        """Récupère la frame la plus récente"""
        with self._buffer_lock:
            if self._frame_buffer:
                return self._frame_buffer[-1]
        return None
    
    async def _perform_initial_autofocus(self):
        """Autofocus initial optimisé"""
        try:
            from libcamera import controls
            
            logger.info("Autofocus initial optimisé...")
            
            self.picam2.set_controls({
                "AfMode": controls.AfModeEnum.Continuous,
                "AfSpeed": controls.AfSpeedEnum.Fast
            })
            
            start_time = time.time()
            
            while time.time() - start_time < 8:
                metadata = self.picam2.capture_metadata()
                state = metadata.get("AfState")
                if state == 2:
                    break
                elif state == 3:
                    break
                await asyncio.sleep(0.1)
            
            lens_pos = metadata.get("LensPosition") or self.picam2.camera_controls.get("LensPosition")
            if isinstance(lens_pos, (list, tuple)):
                self._current_focus = lens_pos[0]
            else:
                self._current_focus = lens_pos
            
            self.picam2.set_controls({
                "AfMode": controls.AfModeEnum.Manual,
                "LensPosition": self._current_focus
            })
            
            logger.info(f"Autofocus initial terminé - Position: {self._current_focus}")
            
        except Exception as e:
            logger.warning(f"Erreur autofocus initial: {e}")
    
    async def get_video_stream(self):
        """Générateur flux vidéo optimisé"""
        frame_count = 0
        last_log_time = time.time()
        
        while True:
            try:
                while not self.is_streaming:
                    await asyncio.sleep(0.1)
                    continue
                
                frame_data = self._get_latest_frame()
                
                if frame_data is None:
                    waiting_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                    cv2.putText(waiting_frame, "Initialisation...", (400, 360), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    _, buffer = cv2.imencode('.jpg', waiting_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    await asyncio.sleep(0.1)
                    continue
                
                frame = cv2.cvtColor(frame_data['array'], cv2.COLOR_RGB2BGR)
                
                if self.zoom_factor > 1.0:
                    frame = self._apply_zoom_optimized(frame)
                
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                
                frame_count += 1
                current_time = time.time()
                if current_time - last_log_time > 10:
                    fps = frame_count / (current_time - last_log_time)
                    logger.info(f"Performance flux vidéo: {fps:.1f} FPS")
                    frame_count = 0
                    last_log_time = current_time
                
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.debug(f"Erreur flux vidéo: {e}")
                await asyncio.sleep(0.5)
    
    def _apply_zoom_optimized(self, frame):
        """Zoom optimisé"""
        h, w = frame.shape[:2]
        cx, cy = int(self.zoom_center[0] * w), int(self.zoom_center[1] * h)
        
        box_w = int(w / self.zoom_factor)
        box_h = int(h / self.zoom_factor)
        
        x1 = max(0, cx - box_w // 2)
        y1 = max(0, cy - box_h // 2)
        x2 = min(w, x1 + box_w)
        y2 = min(h, y1 + box_h)
        
        crop = frame[y1:y2, x1:x2]
        zoomed = cv2.resize(crop, (w, h), interpolation=cv2.INTER_LINEAR)
        return zoomed
    
    def enhance_image(self, frame):
        """Améliore la qualité de l'image selon le guide"""
        if not self._quality_config.get("post_processing", False):
            return frame
        
        try:
            # 1. Réduction du bruit
            if self._quality_config.get("noise_reduction", False):
                frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)
            
            # 2. Amélioration du contraste (CLAHE)
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            frame = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            
            # 3. Netteté (unsharp masking)
            gaussian = cv2.GaussianBlur(frame, (0, 0), 2.0)
            frame = cv2.addWeighted(frame, 1.5, gaussian, -0.5, 0)
            
            return frame
            
        except Exception as e:
            logger.warning(f"Erreur amélioration image: {e}")
            return frame
    
    def evaluate_image_quality(self, image):
        """Évalue la qualité d'une image (pour mode expert)"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Mesure de netteté
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Mesure de contraste
            contrast = gray.std()
            
            # Score combiné
            score = sharpness * 0.7 + contrast * 0.3
            
            return score
            
        except Exception as e:
            logger.warning(f"Erreur évaluation qualité: {e}")
            return 0
    
    async def capture_photo_enhanced(self, manual_of: str = None) -> str:
        """Capture photo avec toutes les améliorations"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if manual_of:
                filename = f"{timestamp}_{manual_of}.jpg"
            else:
                filename = f"{timestamp}.jpg"
                
            filepath = IMAGES_DIR / filename
            
            # Mode capture selon qualité
            if app_settings["quality_mode"] == "expert":
                return await self._capture_bracketed_photos(filepath, manual_of)
            elif app_settings["quality_mode"] == "haute":
                return await self._capture_multiple_shots(filepath, manual_of)
            else:
                return await self._capture_standard(filepath, manual_of)
                
        except Exception as e:
            logger.error(f"Erreur capture photo: {e}")
            self.is_streaming = True
            raise
    
    async def _capture_standard(self, filepath: Path, manual_of: str = None) -> str:
        """Capture standard optimisée"""
        self.is_streaming = False
        await asyncio.sleep(0.1)
        
        # Arrêt temporaire thread
        was_capturing = not self._stop_capture
        if was_capturing:
            self._stop_capture = True
            if self._capture_thread and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=1.0)
        
        try:
            # Éclairage optimisé selon mode
            if app_settings["lighting_mode"] == "blanc":
                send_serial_signal(SERIAL_SIGNALS["photo_mode"])
            else:
                send_serial_signal(SERIAL_SIGNALS["uv_doux"])
            
            await asyncio.sleep(0.2)
            
            # Capture
            self.picam2.stop()
            self.picam2.configure(self.still_config)
            self.picam2.start()
            await asyncio.sleep(0.3)
            
            array = self.picam2.capture_array()
            frame = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
            
            # Post-traitement
            frame = self.enhance_image(frame)
            
            # Sauvegarde avec qualité optimisée
            quality = self._quality_config["jpeg_quality"]
            await asyncio.get_event_loop().run_in_executor(
                self._executor, cv2.imwrite, str(filepath), frame, 
                [cv2.IMWRITE_JPEG_QUALITY, quality, cv2.IMWRITE_JPEG_OPTIMIZE, 1]
            )
            
            logger.info(f"Photo standard capturée: {filepath.name}")
            
            # Rétablissement rapide
            self.picam2.stop()
            self.picam2.configure(self.preview_config)
            self.picam2.start()
            await asyncio.sleep(0.3)
            
            if was_capturing:
                self._start_background_capture()
            
            self.is_streaming = True
            
        except Exception as e:
            logger.error(f"Erreur capture standard: {e}")
            # Rétablissement d'urgence
            try:
                self.picam2.stop()
                self.picam2.configure(self.preview_config)
                self.picam2.start()
                if was_capturing:
                    self._start_background_capture()
                self.is_streaming = True
            except:
                pass
            raise
        
        return str(filepath)
    
    async def _capture_multiple_shots(self, filepath: Path, manual_of: str = None) -> str:
        """Capture multiple pour mode haute qualité"""
        shots = self._quality_config.get("multiple_shots", 3)
        best_image = None
        best_score = 0
        
        self.is_streaming = False
        await asyncio.sleep(0.1)
        
        try:
            # Éclairage optimisé
            send_serial_signal(SERIAL_SIGNALS["photo_mode"])
            await asyncio.sleep(0.3)
            
            self.picam2.stop()
            self.picam2.configure(self.still_config)
            self.picam2.start()
            await asyncio.sleep(0.5)
            
            logger.info(f"Capture multiple - {shots} photos...")
            
            for i in range(shots):
                array = self.picam2.capture_array()
                frame = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
                
                # Évaluation qualité
                score = self.evaluate_image_quality(frame)
                
                if score > best_score:
                    best_score = score
                    best_image = frame.copy()
                
                await asyncio.sleep(0.2)
            
            # Post-traitement sur la meilleure image
            if best_image is not None:
                best_image = self.enhance_image(best_image)
                
                quality = self._quality_config["jpeg_quality"]
                await asyncio.get_event_loop().run_in_executor(
                    self._executor, cv2.imwrite, str(filepath), best_image,
                    [cv2.IMWRITE_JPEG_QUALITY, quality, cv2.IMWRITE_JPEG_OPTIMIZE, True]
                )
                
                logger.info(f"Photo haute qualité capturée: {filepath.name} (score: {best_score:.0f})")
            
            # Rétablissement
            self.picam2.stop()
            self.picam2.configure(self.preview_config)
            self.picam2.start()
            await asyncio.sleep(0.3)
            
            self.is_streaming = True
            
        except Exception as e:
            logger.error(f"Erreur capture multiple: {e}")
            self.is_streaming = True
            raise
        
        return str(filepath)
    
    async def _capture_bracketed_photos(self, filepath: Path, manual_of: str = None) -> str:
        """Capture avec bracketing d'exposition pour mode expert"""
        exposures = [8000, 10000, 12000, 15000]
        best_image = None
        best_score = 0
        
        self.is_streaming = False
        await asyncio.sleep(0.1)
        
        try:
            # Éclairage expert
            send_serial_signal(SERIAL_SIGNALS["photo_mode"])
            await asyncio.sleep(0.5)
            
            logger.info("Capture expert avec bracketing d'exposition...")
            
            for i, exposure_time in enumerate(exposures):
                from libcamera import controls
                
                config = self.picam2.create_still_configuration(
                    main={"size": self._quality_config["resolution"]},
                    controls={
                        "ExposureTime": exposure_time,
                        "AnalogueGain": 1.0,
                        "DigitalGain": 1.0,
                        "AfMode": controls.AfModeEnum.Manual,
                        "LensPosition": self._current_focus
                    }
                )
                
                self.picam2.stop()
                self.picam2.configure(config)
                self.picam2.start()
                await asyncio.sleep(0.5)
                
                array = self.picam2.capture_array()
                frame = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
                
                score = self.evaluate_image_quality(frame)
                
                if score > best_score:
                    best_score = score
                    best_image = frame.copy()
                
                logger.info(f"Exposition {exposure_time}µs: score={score:.0f}")
            
            # Post-traitement expert
            if best_image is not None:
                best_image = self.enhance_image(best_image)
                
                quality = self._quality_config["jpeg_quality"]
                await asyncio.get_event_loop().run_in_executor(
                    self._executor, cv2.imwrite, str(filepath), best_image,
                    [cv2.IMWRITE_JPEG_QUALITY, quality, cv2.IMWRITE_JPEG_OPTIMIZE, True]
                )
                
                logger.info(f"Photo expert capturée: {filepath.name} (meilleur score: {best_score:.0f})")
            
            # Rétablissement
            self.picam2.stop()
            self.picam2.configure(self.preview_config)
            self.picam2.start()
            await asyncio.sleep(0.5)
            
            self.is_streaming = True
            
        except Exception as e:
            logger.error(f"Erreur capture bracketed: {e}")
            self.is_streaming = True
            raise
        
        return str(filepath)
    
    async def focus_auto(self):
        """Focus auto optimisé"""
        try:
            from libcamera import controls
            
            logger.info("Autofocus optimisé...")
            
            self.picam2.set_controls({
                "AfMode": controls.AfModeEnum.Continuous,
                "AfSpeed": controls.AfSpeedEnum.Fast
            })
            
            start_time = time.time()
            
            while time.time() - start_time < 5:
                metadata = self.picam2.capture_metadata()
                state = metadata.get("AfState")
                if state == 2:
                    break
                elif state == 3:
                    break
                await asyncio.sleep(0.05)
            
            lens_pos = metadata.get("LensPosition") or self.picam2.camera_controls.get("LensPosition")
            if isinstance(lens_pos, (list, tuple)):
                self._current_focus = lens_pos[0]
            else:
                self._current_focus = lens_pos
            
            self.picam2.set_controls({
                "AfMode": controls.AfModeEnum.Manual,
                "LensPosition": self._current_focus
            })
            
            # Recréer la config still avec nouveau focus
            self._create_enhanced_still_config()
            
            logger.info(f"Autofocus terminé - Position: {self._current_focus}")
            
        except Exception as e:
            logger.error(f"Erreur autofocus: {e}")
    
    def set_zoom_point(self, x: float, y: float):
        """Définit le point de zoom"""
        self.zoom_center = (x, y)
        self.zoom_factor = 2.0
        logger.info(f"Zoom défini: ({x:.2f}, {y:.2f})")
    
    def reset_zoom(self):
        """Reset zoom"""
        self.zoom_factor = 1.0
        self.zoom_center = (0.5, 0.5)
        logger.info("Zoom réinitialisé")
    
    def stop(self):
        """Arrêt optimisé"""
        self.is_streaming = False
        
        self._stop_capture = True
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
        
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
            except:
                pass
            
        logger.info("Caméra arrêtée proprement")


def preprocess_for_datamatrix(image):
    """Pré-traitement optimisé pour DataMatrix selon le guide"""
    
    # 1. Conversion en niveaux de gris optimisée
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # 2. Égalisation d'histogramme adaptatif
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    # 3. Filtre gaussien pour réduire le bruit
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # 4. Netteté pour améliorer les contours
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    gray = cv2.filter2D(gray, -1, kernel)
    
    return gray


def enhanced_decode_datamatrix(image_path: str) -> Optional[str]:
    """Décodage DataMatrix amélioré avec multiples tentatives"""
    try:
        image = cv2.imread(image_path)
        if image is None:
            return None
        
        # Pré-traitement optimisé
        processed = preprocess_for_datamatrix(image)
        
        # Tentatives avec différents seuillages
        thresholds = [
            ("Otsu", lambda img: cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]),
            ("Adaptatif", lambda img: cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)),
            ("Adaptatif Mean", lambda img: cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 5)),
            ("Seuil fixe 128", lambda img: cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)[1])
        ]
        
        # Test avec chaque méthode et rotation
        for threshold_name, threshold_func in thresholds:
            binary = threshold_func(processed)
            
            for angle in [0, 90, 180, 270]:
                if angle != 0:
                    rotated = rotate_image(binary, angle)
                else:
                    rotated = binary
                
                # Sauvegarde debug
                debug_path = image_path.replace('.jpg', f'_debug_{threshold_name}_{angle}.jpg')
                cv2.imwrite(debug_path, rotated)
                
                try:
                    decoded = pylibdmtx.decode(rotated, max_count=1)
                    if decoded:
                        result = decoded[0].data.decode('utf-8')
                        logger.info(f"DataMatrix décodé avec {threshold_name} à {angle}°: {result}")
                        return result
                except Exception:
                    continue
        
        return None
        
    except Exception as e:
        logger.error(f"Erreur décodage: {e}")
        return None


def extract_white_label_enhanced(gray_image):
    """Extraction améliorée du label blanc avec debug"""
    try:
        # Seuillage plus strict pour isoler le blanc
        _, thresh = cv2.threshold(gray_image, 220, 255, cv2.THRESH_BINARY)
        
        # Morphologie pour nettoyer
        kernel = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        # Détection des contours
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Analyse améliorée des contours
        best_contour = None
        max_score = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filtre sur la taille (ajusté)
            if area < 1500 or area > gray_image.shape[0] * gray_image.shape[1] * 0.4:
                continue
            
            # Approximation du contour
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Vérification forme rectangulaire
            if len(approx) < 4 or len(approx) > 10:
                continue
            
            # Vérification aspect ratio
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = max(w, h) / min(w, h)
            
            if aspect_ratio > 5:  # Moins strict
                continue
            
            # Score amélioré
            rectangularity = len(approx) / 4.0
            compactness = area / (w * h)
            score = area * (2 - abs(rectangularity - 1)) * compactness
            
            if score > max_score:
                best_contour = contour
                max_score = score
        
        if best_contour is None:
            return None
        
        # Extraction avec marge adaptative
        x, y, w, h = cv2.boundingRect(best_contour)
        margin = min(15, w//8, h//8)  # Marge plus grande
        
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(gray_image.shape[1] - x, w + 2 * margin)
        h = min(gray_image.shape[0] - y, h + 2 * margin)
        
        extracted_label = gray_image[y:y+h, x:x+w]
        
        # Vérification finale du contenu blanc
        white_ratio = np.sum(extracted_label > 200) / (w * h)
        if white_ratio < 0.25:  # Moins strict
            return None
        
        return extracted_label
        
    except Exception as e:
        logger.error(f"Erreur extraction label: {e}")
        return None


def rotate_image(image, angle):
    """Rotation d'image optimisée"""
    if angle == 0:
        return image
    elif angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        # Rotation arbitraire
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, matrix, (w, h))


def decode_datamatrix(image_path: str) -> Optional[str]:
    """Décode un DataMatrix avec méthode améliorée"""
    try:
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Impossible de charger l'image: {image_path}")
            return None
        
        # Utilisation du décodage amélioré
        result = enhanced_decode_datamatrix(image_path)
        if result:
            return result
        
        # Fallback avec méthode classique
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        white_label = extract_white_label_enhanced(gray)
        
        if white_label is None:
            logger.warning("Aucun label blanc détecté")
            return None
        
        # Sauvegarde debug
        debug_path = image_path.replace('.jpg', '_label_debug.jpg')
        cv2.imwrite(debug_path, white_label)
        
        # Test avec rotations
        for angle in [0, 90, 180, 270]:
            if angle != 0:
                rotated = rotate_image(white_label, angle)
            else:
                rotated = white_label
            
            binary = cv2.adaptiveThreshold(
                rotated, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            try:
                decoded = pylibdmtx.decode(binary)
                if decoded:
                    result = decoded[0].data.decode('utf-8')
                    logger.info(f"DataMatrix décodé (rotation {angle}°): {result}")
                    return result
            except Exception:
                continue
        
        logger.warning("Label trouvé mais aucun code DataMatrix décodé")
        return None
        
    except Exception as e:
        logger.error(f"Erreur décodage DataMatrix: {e}")
        return None


def get_latest_images(count: int = 3) -> list:
    """Récupère les dernières images"""
    try:
        image_files = list(IMAGES_DIR.glob("*.jpg"))
        image_files = [f for f in image_files if "_debug" not in f.name]
        image_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return [f"/images/{f.name}" for f in image_files[:count]]
    except Exception as e:
        logger.error(f"Erreur récupération images: {e}")
        return []


def init_serial_connection():
    """Initialise la connexion série avec détection automatique"""
    global serial_connection
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0']
    
    for port in ports:
        try:
            serial_connection = serial.Serial(port, 9600, timeout=1)
            logger.info(f"Connexion série établie sur {port}")
            return True
        except Exception as e:
            logger.warning(f"Impossible de se connecter à {port}: {e}")
            continue
    
    logger.warning("Aucun port série disponible")
    return False


def send_serial_signal(signal_byte: bytes = b'\x01'):
    """Envoie un signal série avec gestion d'erreur"""
    try:
        if serial_connection and serial_connection.is_open:
            serial_connection.write(signal_byte)
            logger.info(f"Signal série envoyé: {signal_byte}")
            return True
        else:
            logger.warning("Connexion série non disponible")
            return False
    except Exception as e:
        logger.error(f"Erreur envoi signal série: {e}")
        return False


# Gestionnaire de caméra global
camera_manager = EnhancedCameraManager()


@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    logger.info("Démarrage du serveur DataMatrix Scanner v2.1...")
    await camera_manager.initialize()
    init_serial_connection()
    logger.info("Serveur prêt avec optimisations complètes")


@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    logger.info("Arrêt du serveur...")
    camera_manager.stop()
    if serial_connection:
        serial_connection.close()
    logger.info("Serveur arrêté proprement")


@app.get("/", response_class=HTMLResponse)
async def read_settings():
    """Page de paramétrage avec nouveau mode qualité"""
    with open("settings.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/app", response_class=HTMLResponse)
async def read_app():
    """Page d'application principale"""
    with open("app.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/settings")
async def update_settings(
    scan_mode: str = Form(...),
    detection_mode: str = Form(...),
    lighting_mode: str = Form(...),
    quality_mode: str = Form(default="standard"),
    manual_of: str = Form(default="")
):
    """Met à jour les paramètres avec nouveau mode qualité"""
    global app_settings
    
    app_settings.update({
        "scan_mode": scan_mode,
        "detection_mode": detection_mode,
        "lighting_mode": lighting_mode,
        "quality_mode": quality_mode,
        "manual_of": manual_of
    })
    
    logger.info(f"Paramètres mis à jour: {app_settings}")
    
    # Mise à jour du mode qualité de la caméra
    camera_manager.set_quality_mode(quality_mode)
    
    # Signal d'éclairage approprié
    if lighting_mode == "blanc":
        send_serial_signal(SERIAL_SIGNALS["leds_blanches"])
    elif lighting_mode == "uv":
        send_serial_signal(SERIAL_SIGNALS["lampe_uv"])
    
    return {"status": "success", "settings": app_settings}


@app.get("/api/settings")
async def get_settings():
    """Récupère les paramètres actuels"""
    return app_settings


@app.post("/api/test-lighting")
async def test_lighting(lighting_data: dict):
    """Test d'éclairage avec signaux étendus"""
    try:
        lighting_type = lighting_data.get("lighting_type")
        
        if lighting_type == "blanc":
            success = send_serial_signal(SERIAL_SIGNALS["leds_blanches"])
            message = "LEDs blanches activées" if success else "Erreur LEDs blanches"
        elif lighting_type == "uv":
            success = send_serial_signal(SERIAL_SIGNALS["lampe_uv"])
            message = "Lampe UV activée" if success else "Erreur lampe UV"
        else:
            success = False
            message = "Type d'éclairage inconnu"
        
        return {"success": success, "message": message}
        
    except Exception as e:
        logger.error(f"Erreur test éclairage: {e}")
        return {"success": False, "message": f"Erreur: {str(e)}"}


@app.get("/video_feed")
async def video_feed():
    """Flux vidéo MJPEG optimisé"""
    return StreamingResponse(
        camera_manager.get_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour pilotage optimisé"""
    global current_websocket
    await websocket.accept()
    current_websocket = websocket
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Message WebSocket reçu: {data}")
            
            try:
                message = json.loads(data)
                
                if "zoomTo" in message:
                    x, y = message["zoomTo"]
                    camera_manager.set_zoom_point(x, y)
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "message": f"Zoom défini sur ({x:.2f}, {y:.2f})"
                    }))
                
                elif "resetZoom" in message:
                    camera_manager.reset_zoom()
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "message": "Zoom réinitialisé"
                    }))
                
                elif "lighting" in message:
                    lighting_type = message["lighting"]
                    if lighting_type == "blanc":
                        success = send_serial_signal(SERIAL_SIGNALS["leds_blanches"])
                        status = "LEDs blanches activées" if success else "Erreur LEDs blanches"
                    elif lighting_type == "uv":
                        success = send_serial_signal(SERIAL_SIGNALS["lampe_uv"])
                        status = "Lampe UV activée" if success else "Erreur lampe UV"
                    else:
                        success = False
                        status = "Type d'éclairage inconnu"
                    
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "message": status
                    }))
                
                elif "quality_mode" in message:
                    # Nouveau: changement de mode qualité en temps réel
                    quality_mode = message["quality_mode"]
                    if quality_mode in QUALITY_CONFIGS:
                        app_settings["quality_mode"] = quality_mode
                        camera_manager.set_quality_mode(quality_mode)
                        await websocket.send_text(json.dumps({
                            "type": "status",
                            "message": f"Mode qualité changé vers: {quality_mode}"
                        }))
                
            except json.JSONDecodeError:
                if data == "capture":
                    await handle_capture_command(websocket)
                elif data == "focus":
                    await handle_focus_command(websocket)
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Commande inconnue: {data}"
                    }))
                    
    except WebSocketDisconnect:
        logger.info("WebSocket déconnecté")
        current_websocket = None
    except Exception as e:
        logger.error(f"Erreur WebSocket: {e}")
        current_websocket = None


async def handle_capture_command(websocket):
    """Version corrigée avec gestion d'erreur robuste"""
    try:
        logger.info("🚀 Début capture")
        
        # Message initial
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Capture en cours..."
        }))
        
        # OF manuel
        manual_of = None
        if app_settings["detection_mode"] == "manuel" and app_settings["manual_of"]:
            manual_of = app_settings["manual_of"]
        
        # Capture - SIMPLIFIÉE
        photo_path = await camera_manager.capture_photo(manual_of)
        logger.info(f"Photo capturée: {photo_path}")
        
        # Décodage - SIMPLIFIÉ
        datamatrix_result = None
        if app_settings["scan_mode"] == "datamatrix":
            try:
                # Import ici pour éviter les problèmes
                import cv2
                from pylibdmtx import pylibdmtx
                
                image = cv2.imread(photo_path)
                if image is not None:
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    decoded = pylibdmtx.decode(gray)
                    if decoded:
                        datamatrix_result = decoded[0].data.decode('utf-8')
                        logger.info(f"Code détecté: {datamatrix_result}")
            except Exception as e:
                logger.error(f"Erreur décodage: {e}")
                datamatrix_result = None
        elif app_settings["scan_mode"] == "lot":
            datamatrix_result = manual_of or "Mode Lot"
        
        # Images récentes
        latest_images = get_latest_images(3)
        
        # RÉSULTAT - OBLIGATOIRE
        result = {
            "type": "capture_result",
            "photo_path": f"/images/{Path(photo_path).name}",
            "datamatrix": datamatrix_result,
            "latest_images": latest_images,
            "timestamp": datetime.now().isoformat(),
            "scan_mode": app_settings["scan_mode"],
            "detection_mode": app_settings["detection_mode"]
        }
        
        # ENVOI RÉSULTAT - CRITIQUE
        await websocket.send_text(json.dumps(result))
        logger.info("✅ Résultat envoyé")
        
        # Message final
        final_msg = f"Code détecté: {datamatrix_result}" if datamatrix_result else "Capture terminée"
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": final_msg
        }))
        
    except Exception as e:
        logger.error(f"Erreur capture: {e}")
        # TOUJOURS envoyer une réponse, même en cas d'erreur
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Erreur: {str(e)}"
        }))


async def handle_focus_command(websocket: WebSocket):
    """Gère la commande de focus optimisée"""
    try:
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Autofocus optimisé en cours..."
        }))
        
        await camera_manager.focus_auto()
        
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Autofocus terminé avec succès"
        }))
        
    except Exception as e:
        logger.error(f"Erreur focus: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Erreur focus: {str(e)}"
        }))


def signal_handler(signum, frame):
    """Gestionnaire de signaux système"""
    logger.info(f"Signal {signum} reçu, arrêt en cours...")
    camera_manager.stop()
    if serial_connection:
        serial_connection.close()
    sys.exit(0)


if __name__ == "__main__":
    # Configuration des signaux système
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Démarrage DataMatrix Scanner v2.1 - Version optimisée")
    logger.info("Optimisations actives: performance, qualité photo, détection améliorée")
    
    # Lancement du serveur
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )