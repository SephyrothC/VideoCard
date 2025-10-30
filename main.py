#!/usr/bin/env python3
"""
CameraManager optimisé pour flux vidéo rapide avec bonnes couleurs
NOUVEAU: Système de paramétrage avec modes DataMatrix/Lot et Automatique/Manuel
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
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
from pylibdmtx import pylibdmtx

# Import du gestionnaire de stockage
from storage_manager import get_storage_manager

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialisation du gestionnaire de stockage
storage_manager = get_storage_manager()

# Configuration globale - IMAGES_DIR est maintenant géré dynamiquement par storage_manager
# Conservé pour compatibilité avec le montage des fichiers statiques
IMAGES_DIR = Path("images")
IMAGES_DIR.mkdir(exist_ok=True)

# Variables globales
app = FastAPI(title="DataMatrix Scanner", version="2.0.0")
camera: Optional[Picamera2] = None
serial_connection: Optional[serial.Serial] = None
current_websocket: Optional[WebSocket] = None

# NOUVELLES VARIABLES DE CONFIGURATION
app_settings = {
    "scan_mode": "datamatrix",  # "datamatrix" ou "lot"
    "detection_mode": "automatique",  # "automatique" ou "manuel"
    "lighting_mode": "blanc",  # "blanc" ou "uv"
    "manual_of": ""  # OF manuel si mode manuel
}

# Montage des fichiers statiques
# Note: Ce montage est conservé pour compatibilité, mais les images peuvent aussi
# être servies depuis le réseau via la route /api/image/{filename}
app.mount("/images", StaticFiles(directory="images"), name="images")


class OptimizedCameraManager:
    """
    Gestionnaire de caméra optimisé pour performance - Style ancien qui marchait
    AMÉLIORATIONS PERFORMANCE:
    - Buffer de frames en arrière-plan
    - Thread dédié pour la capture
    - Réduction des conversions de couleur
    - Cache des frames
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
        
        # NOUVEAUX ÉLÉMENTS PERFORMANCE
        self._frame_buffer = []
        self._buffer_lock = threading.Lock()
        self._capture_thread = None
        self._stop_capture = False
        self._last_frame_time = 0
        self._frame_cache = None
        self._cache_time = 0
        
        # ThreadPool pour les opérations non-bloquantes
        self._executor = ThreadPoolExecutor(max_workers=2)
        
    async def initialize(self):
        """Initialise la caméra avec optimisations performance"""
        try:
            self.picam2 = Picamera2()
            
            # Import libcamera controls (obligatoire pour votre ancien style)
            from libcamera import controls
            
            # Configuration prévisualisation OPTIMISÉE pour performance
            self.preview_config = self.picam2.create_preview_configuration(
                main={"size": (1280, 720), "format": "RGB888"},  # Format direct
                controls={
                    "AfMode": controls.AfModeEnum.Continuous,
                    "AfSpeed": controls.AfSpeedEnum.Fast,
                    "FrameRate": 30  # Framerate explicite
                }
            )
            
            # Configuration photo (inchangée - votre ancien style)  
            self.still_config = self.picam2.create_still_configuration(
                main={"size": (4624, 3472)},
                controls={"AfMode": controls.AfModeEnum.Manual}
            )
            
            # Démarrage avec la configuration preview
            self.picam2.configure(self.preview_config)
            self.picam2.start()
            
            logger.info("Caméra initialisée avec optimisations performance")
            
            # FOCUS AUTOMATIQUE INITIAL (comme votre ancien code)
            await self._perform_initial_autofocus()
            
            # DÉMARRAGE DU THREAD DE CAPTURE OPTIMISÉ
            self._start_background_capture()
            
            self.is_streaming = True
            logger.info("Caméra prête - Mode haute performance activé")
            
        except Exception as e:
            logger.error(f"Erreur initialisation caméra: {e}")
            raise
    
    def _start_background_capture(self):
        """Démarre la capture en arrière-plan pour performance maximale"""
        self._stop_capture = False
        self._capture_thread = threading.Thread(target=self._background_capture_loop, daemon=True)
        self._capture_thread.start()
        logger.info("Thread de capture en arrière-plan démarré")
    
    def _background_capture_loop(self):
        """Boucle de capture en arrière-plan - PERFORMANCE OPTIMISÉE"""
        while not self._stop_capture:
            try:
                if not self.picam2 or not self.picam2.started:
                    time.sleep(0.1)
                    continue
                
                # Capture directe sans conversion couleur immédiate
                array = self.picam2.capture_array()
                
                # Stockage avec timestamp
                frame_data = {
                    'array': array,
                    'timestamp': time.time()
                }
                
                # Mise à jour du buffer (taille limitée pour mémoire)
                with self._buffer_lock:
                    self._frame_buffer.append(frame_data)
                    # Garder seulement les 3 dernières frames
                    if len(self._frame_buffer) > 3:
                        self._frame_buffer.pop(0)
                
                # Contrôle framerate (30 FPS max)
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                logger.debug(f"Erreur capture arrière-plan: {e}")
                time.sleep(0.1)
    
    def _get_latest_frame(self):
        """Récupère la frame la plus récente du buffer"""
        with self._buffer_lock:
            if self._frame_buffer:
                return self._frame_buffer[-1]
        return None
    
    async def _perform_initial_autofocus(self):
        """Effectue l'autofocus initial EXACTEMENT comme votre ancien code"""
        try:
            from libcamera import controls
            
            logger.info("Autofocus initial lancé...")
            
            # Méthode EXACTE de votre ancien code
            self.picam2.set_controls({
                "AfMode": controls.AfModeEnum.Continuous,
                "AfSpeed": controls.AfSpeedEnum.Fast
            })
            
            start_time = time.time()
            focused = False
            
            while time.time() - start_time < 8:
                metadata = self.picam2.capture_metadata()
                state = metadata.get("AfState")
                if state == 2:  # focused
                    focused = True
                    break
                elif state == 3:  # failed
                    break
                await asyncio.sleep(0.1)
            
            # Capturer la position du focus
            lens_pos = metadata.get("LensPosition") or self.picam2.camera_controls.get("LensPosition")
            if isinstance(lens_pos, (list, tuple)):
                self._current_focus = lens_pos[0]
            else:
                self._current_focus = lens_pos
            
            logger.info(f"Position focus capturée: {self._current_focus}")
            
            # Passer en mode manuel avec focus fixé
            self.picam2.set_controls({
                "AfMode": controls.AfModeEnum.Manual,
                "LensPosition": self._current_focus
            })
            
            logger.info("Autofocus initial terminé")
            
        except Exception as e:
            logger.warning(f"Erreur autofocus initial: {e}")
    
    async def get_video_stream(self):
        """Générateur pour le flux vidéo MJPEG ULTRA-OPTIMISÉ"""
        frame_count = 0
        last_log_time = time.time()
        
        while True:
            try:
                # Attendre que le streaming soit actif
                while not self.is_streaming:
                    await asyncio.sleep(0.1)
                    continue
                
                # Récupération optimisée de la frame depuis le buffer
                frame_data = self._get_latest_frame()
                
                if frame_data is None:
                    # Frame d'attente si buffer vide
                    waiting_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                    cv2.putText(waiting_frame, "Initialisation...", (400, 360), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    _, buffer = cv2.imencode('.jpg', waiting_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    await asyncio.sleep(0.1)
                    continue
                
                # Conversion couleur OPTIMISÉE (une seule fois)
                frame = cv2.cvtColor(frame_data['array'], cv2.COLOR_RGB2BGR)
                
                # Application du zoom si nécessaire (optimisé)
                if self.zoom_factor > 1.0:
                    frame = self._apply_zoom_optimized(frame)
                
                # Encodage JPEG avec qualité optimisée pour performance
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                
                # Statistiques de performance (log périodique)
                frame_count += 1
                current_time = time.time()
                if current_time - last_log_time > 10:  # Log toutes les 10 secondes
                    fps = frame_count / (current_time - last_log_time)
                    logger.info(f"Performance flux vidéo: {fps:.1f} FPS")
                    frame_count = 0
                    last_log_time = current_time
                
                # Délai optimisé pour 25-30 FPS réels
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.debug(f"Erreur flux vidéo: {e}")
                await asyncio.sleep(0.5)
    
    def _apply_zoom_optimized(self, frame):
        """Version optimisée du zoom - PERFORMANCE AMÉLIORÉE"""
        h, w = frame.shape[:2]
        cx, cy = int(self.zoom_center[0] * w), int(self.zoom_center[1] * h)
        
        box_w = int(w / self.zoom_factor)
        box_h = int(h / self.zoom_factor)
        
        x1 = max(0, cx - box_w // 2)
        y1 = max(0, cy - box_h // 2)
        x2 = min(w, x1 + box_w)
        y2 = min(h, y1 + box_h)
        
        # Crop direct sans copie intermédiaire
        crop = frame[y1:y2, x1:x2]
        
        # Resize optimisé avec interpolation plus rapide
        zoomed = cv2.resize(crop, (w, h), interpolation=cv2.INTER_LINEAR)
        return zoomed
    
    async def capture_photo(self, manual_of: str = None) -> str:
        """Capture photo OPTIMISÉE avec stockage réseau et fallback - Moins d'interruptions du flux"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Nom de fichier avec OF si manuel
            if manual_of:
                filename = f"{timestamp}_{manual_of}.jpg"
            else:
                filename = f"{timestamp}.jpg"

            # Le filepath sera déterminé par le storage_manager
            # Conservé pour compatibilité temporaire
            filepath = None
            
            # OPTIMISATION: Pause plus courte du streaming
            self.is_streaming = False
            await asyncio.sleep(0.1)  # Réduit de 0.2 à 0.1
            
            # ARRÊT TEMPORAIRE du thread de capture pour éviter conflicts
            was_capturing = not self._stop_capture
            if was_capturing:
                self._stop_capture = True
                if self._capture_thread and self._capture_thread.is_alive():
                    self._capture_thread.join(timeout=1.0)
            
            try:
                # Séquence capture EXACTE mais avec timings optimisés
                self.picam2.stop()
                self.picam2.configure(self.still_config)
                self.picam2.start()
                await asyncio.sleep(0.3)  # Réduit de 0.5 à 0.3
                
                # Capture
                array = self.picam2.capture_array()
                frame = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)

                # Sauvegarde avec storage_manager (supporte réseau + fallback)
                saved_path, success = await asyncio.get_event_loop().run_in_executor(
                    self._executor, storage_manager.save_file, filename, cv2.imwrite, frame
                )

                if not success or not saved_path:
                    raise Exception(f"Échec de la sauvegarde de {filename}")

                filepath = saved_path
                logger.info(f"Photo capturée: {filename} - {frame.shape} - Sauvegardé: {filepath}")
                
                # Rétablissement RAPIDE
                self.picam2.stop()
                self.picam2.configure(self.preview_config)
                self.picam2.start()
                
                # Attente réduite
                await asyncio.sleep(0.3)  # Réduit de 1.0 à 0.3
                
                # REDÉMARRAGE du thread de capture
                if was_capturing:
                    self._start_background_capture()
                
                # Reprise IMMÉDIATE du streaming
                self.is_streaming = True
                
            except Exception as e:
                logger.error(f"Erreur capture: {e}")
                # Rétablissement d'urgence RAPIDE
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
            
        except Exception as e:
            logger.error(f"Erreur capture photo: {e}")
            self.is_streaming = True
            raise
    
    async def focus_auto(self):
        """Focus manuel OPTIMISÉ - Moins d'interruption"""
        try:
            from libcamera import controls
            
            logger.info("Autofocus manuel optimisé...")
            
            # PAS d'arrêt complet - juste changement de contrôles
            self.picam2.set_controls({
                "AfMode": controls.AfModeEnum.Continuous,
                "AfSpeed": controls.AfSpeedEnum.Fast
            })
            
            start_time = time.time()
            focused = False
            
            # Timeout réduit pour plus de réactivité
            while time.time() - start_time < 5:  # Réduit de 8 à 5 secondes
                metadata = self.picam2.capture_metadata()
                state = metadata.get("AfState")
                if state == 2:  # focused
                    focused = True
                    break
                elif state == 3:  # failed
                    break
                await asyncio.sleep(0.05)  # Réduit de 0.1 à 0.05
            
            # Capturer nouvelle position
            lens_pos = metadata.get("LensPosition") or self.picam2.camera_controls.get("LensPosition")
            if isinstance(lens_pos, (list, tuple)):
                self._current_focus = lens_pos[0]
            else:
                self._current_focus = lens_pos
            
            # Repasser en mode manuel
            self.picam2.set_controls({
                "AfMode": controls.AfModeEnum.Manual,
                "LensPosition": self._current_focus
            })
            
            logger.info(f"Autofocus terminé - Position: {self._current_focus}")
            
        except Exception as e:
            logger.error(f"Erreur autofocus: {e}")
    
    def set_zoom_point(self, x: float, y: float):
        """Définit le point de zoom - OPTIMISÉ"""
        self.zoom_center = (x, y)
        self.zoom_factor = 2.0
        logger.info(f"Zoom défini: ({x:.2f}, {y:.2f})")
    
    def reset_zoom(self):
        """Reset zoom - OPTIMISÉ"""
        self.zoom_factor = 1.0
        self.zoom_center = (0.5, 0.5)
        logger.info("Zoom réinitialisé")
    
    def stop(self):
        """Arrêt optimisé avec nettoyage complet"""
        self.is_streaming = False
        
        # Arrêt du thread de capture
        self._stop_capture = True
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        
        # Nettoyage executor
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
        
        # Arrêt caméra
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
            except:
                pass
            
        logger.info("Caméra arrêtée proprement")


def decode_datamatrix(image_path: str) -> Optional[str]:
    """Décode un code DataMatrix à partir d'une image - supporte réseau et local"""
    try:
        # Si image_path est juste un nom de fichier, le chercher avec storage_manager
        if not os.path.isabs(image_path) and not os.path.exists(image_path):
            filename = Path(image_path).name
            found_path = storage_manager.get_file_path(filename)
            if found_path:
                image_path = str(found_path)
            else:
                logger.error(f"Fichier introuvable: {image_path}")
                return None

        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Impossible de charger l'image: {image_path}")
            return None
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        white_label = extract_white_label(gray)
        
        if white_label is None:
            logger.warning("Aucun label blanc détecté")
            return None
        
        debug_path = image_path.replace('.jpg', '_label_debug.jpg')
        cv2.imwrite(debug_path, white_label)
        
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
            except Exception as e:
                continue
        
        logger.warning("Label trouvé mais aucun code DataMatrix")
        return None
        
    except Exception as e:
        logger.error(f"Erreur décodage DataMatrix: {e}")
        return None


def extract_white_label(gray_image):
    """Extrait le label blanc"""
    try:
        _, thresh = cv2.threshold(gray_image, 220, 255, cv2.THRESH_BINARY)
        kernel = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        best_contour = None
        max_score = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 2000 or area > gray_image.shape[0] * gray_image.shape[1] * 0.3:
                continue
            
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            if len(approx) < 4 or len(approx) > 8:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = max(w, h) / min(w, h)
            
            if aspect_ratio > 4:
                continue
            
            rectangularity = len(approx) / 4.0
            score = area * (2 - abs(rectangularity - 1))
            
            if score > max_score:
                best_contour = contour
                max_score = score
        
        if best_contour is None:
            return None
        
        x, y, w, h = cv2.boundingRect(best_contour)
        margin = min(10, w//10, h//10)
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(gray_image.shape[1] - x, w + 2 * margin)
        h = min(gray_image.shape[0] - y, h + 2 * margin)
        
        extracted_label = gray_image[y:y+h, x:x+w]
        
        white_ratio = np.sum(extracted_label > 200) / (w * h)
        if white_ratio < 0.3:
            return None
        
        return extracted_label
        
    except Exception as e:
        logger.error(f"Erreur extraction label: {e}")
        return None


def rotate_image(image, angle):
    """Rotation d'image"""
    if angle == 0:
        return image
    elif angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)


def get_latest_images(count: int = 3) -> list:
    """Dernières images - utilise le storage_manager pour lister depuis réseau et local"""
    try:
        # Utiliser le storage_manager pour lister les images (réseau + local)
        image_files = storage_manager.list_files(pattern="*.jpg", limit=None)

        # Filtrer les fichiers de debug
        image_files = [f for f in image_files if "_debug" not in f.name and "_label_debug" not in f.name]

        # Limiter au nombre demandé
        image_files = image_files[:count]

        # Retourner les chemins relatifs pour l'API
        return [f"/images/{f.name}" for f in image_files]
    except Exception as e:
        logger.error(f"Erreur récupération images: {e}")
        return []


def init_serial_connection():
    """Initialise connexion série en testant automatiquement ttyUSB0 et ttyUSB1"""
    global serial_connection
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1']
    
    for port in ports:
        try:
            serial_connection = serial.Serial(port, 9600, timeout=1)
            logger.info(f"Connexion série établie sur {port}")
            return True
        except Exception as e:
            logger.warning(f"Impossible de se connecter à {port}: {e}")
            continue
    
    logger.warning("Aucun port série disponible sur ttyUSB0 ou ttyUSB1")
    return False


def send_serial_signal(signal_byte: bytes = b'\x01'):
    """Envoie signal série avec byte personnalisé"""
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
camera_manager = OptimizedCameraManager()


@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    logger.info("Démarrage du serveur...")
    await camera_manager.initialize()
    init_serial_connection()
    logger.info("Serveur prêt")


@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    logger.info("Arrêt du serveur...")
    camera_manager.stop()
    if serial_connection:
        serial_connection.close()
    logger.info("Serveur arrêté")


@app.get("/", response_class=HTMLResponse)
async def read_settings():
    """Page de paramétrage (nouvelle page d'accueil)"""
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
    manual_of: str = Form(default="")
):
    """Met à jour les paramètres"""
    global app_settings
    
    app_settings.update({
        "scan_mode": scan_mode,
        "detection_mode": detection_mode,
        "lighting_mode": lighting_mode,
        "manual_of": manual_of
    })
    
    logger.info(f"Paramètres mis à jour: {app_settings}")
    
    # Envoyer le signal d'éclairage approprié
    if lighting_mode == "blanc":
        send_serial_signal(b'\x01')
    elif lighting_mode == "uv":
        send_serial_signal(b'\x02')
    
    return {"status": "success", "settings": app_settings}


@app.get("/api/settings")
async def get_settings():
    """Récupère les paramètres actuels"""
    return app_settings


@app.get("/api/storage/status")
async def get_storage_status():
    """Récupère l'état du système de stockage"""
    try:
        status = storage_manager.get_storage_status()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Erreur récupération statut stockage: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.post("/api/storage/reset")
async def reset_storage_failures():
    """Réinitialise le compteur d'échecs réseau pour forcer une nouvelle tentative"""
    try:
        storage_manager.reset_failure_counter()
        return JSONResponse(content={
            "status": "success",
            "message": "Compteur d'échecs réinitialisé"
        })
    except Exception as e:
        logger.error(f"Erreur réinitialisation compteur: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.get("/api/image/{filename}")
async def get_image(filename: str):
    """
    Sert une image depuis n'importe quel emplacement de stockage (réseau ou local)
    Cette route permet d'accéder aux images même si elles sont sur le partage réseau
    """
    try:
        # Chercher le fichier avec storage_manager
        file_path = storage_manager.get_file_path(filename)

        if file_path is None or not file_path.exists():
            return JSONResponse(
                content={"error": f"Image non trouvée: {filename}"},
                status_code=404
            )

        # Lire et retourner l'image
        with open(file_path, 'rb') as f:
            image_data = f.read()

        from fastapi.responses import Response
        return Response(content=image_data, media_type="image/jpeg")

    except Exception as e:
        logger.error(f"Erreur récupération image {filename}: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.get("/video_feed")
async def video_feed():
    """Flux vidéo MJPEG OPTIMISÉ"""
    return StreamingResponse(
        camera_manager.get_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour pilotage à distance"""
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
                
                elif "serial" in message:
                    # Signal série générique
                    success = send_serial_signal()
                    status = "Signal série envoyé" if success else "Échec envoi signal série"
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "message": status
                    }))
                
                elif "lighting" in message:
                    # Contrôle d'éclairage spécifique
                    lighting_type = message["lighting"]
                    if lighting_type == "blanc":
                        success = send_serial_signal(b'\x01')
                        status = "LEDs blanches activées" if success else "Erreur LEDs blanches"
                    elif lighting_type == "uv":
                        success = send_serial_signal(b'\x02')
                        status = "Lampe UV activée" if success else "Erreur lampe UV"
                    else:
                        success = False
                        status = "Type d'éclairage inconnu"
                    
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "message": status
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


async def handle_capture_command(websocket: WebSocket):
    """Gère la commande de capture selon les paramètres"""
    try:
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Capture en cours..."
        }))
        
        # Détermine l'OF à utiliser
        manual_of = None
        if app_settings["detection_mode"] == "manuel" and app_settings["manual_of"]:
            manual_of = app_settings["manual_of"]
        
        # Capture de la photo
        photo_path = await camera_manager.capture_photo(manual_of)
        
        # Traitement selon le mode de scan
        datamatrix_result = None
        
        if app_settings["scan_mode"] == "datamatrix":
            # Mode DataMatrix - décodage automatique
            await websocket.send_text(json.dumps({
                "type": "status",
                "message": "Décodage DataMatrix..."
            }))
            datamatrix_result = decode_datamatrix(photo_path)
        elif app_settings["scan_mode"] == "lot":
            # Mode Lot - pas de décodage DataMatrix
            if app_settings["detection_mode"] == "manuel" and app_settings["manual_of"]:
                datamatrix_result = app_settings["manual_of"]
            else:
                datamatrix_result = "Mode Lot - Photo uniquement"
        
        # Récupération des dernières images
        latest_images = get_latest_images(3)
        
        # Envoi du résultat
        result = {
            "type": "capture_result",
            "photo_path": f"/images/{Path(photo_path).name}",
            "datamatrix": datamatrix_result,
            "latest_images": latest_images,
            "timestamp": datetime.now().isoformat(),
            "scan_mode": app_settings["scan_mode"],
            "detection_mode": app_settings["detection_mode"]
        }
        
        await websocket.send_text(json.dumps(result))
        
        # Message de statut final
        if app_settings["scan_mode"] == "datamatrix":
            if datamatrix_result:
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "message": f"Code détecté: {datamatrix_result}"
                }))
            else:
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "message": "Aucun code DataMatrix détecté"
                }))
        else:
            await websocket.send_text(json.dumps({
                "type": "status",
                "message": f"Photo capturée en mode {app_settings['scan_mode']}"
            }))
            
    except Exception as e:
        logger.error(f"Erreur capture: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Erreur capture: {str(e)}"
        }))


async def handle_focus_command(websocket: WebSocket):
    """Gère la commande de focus"""
    try:
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Autofocus en cours..."
        }))
        
        await camera_manager.focus_auto()
        
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Autofocus terminé"
        }))
        
    except Exception as e:
        logger.error(f"Erreur focus: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Erreur focus: {str(e)}"
        }))


def signal_handler(signum, frame):
    """Gestionnaire de signaux"""
    logger.info(f"Signal {signum} reçu, arrêt en cours...")
    camera_manager.stop()
    if serial_connection:
        serial_connection.close()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )