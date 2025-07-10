#!/usr/bin/env python3
"""
Configuration pour l'application DataMatrix Scanner
"""

import os
from pathlib import Path

class Config:
    """Configuration de l'application"""
    
    # Configuration du serveur
    HOST = "0.0.0.0"
    PORT = 8000
    DEBUG = False
    
    # Configuration de la caméra
    CAMERA_CONFIG = {
        # Résolution pour le streaming (lores)
        "stream_resolution": (640, 480),
        
        # Résolution pour la capture (main)
        "capture_resolution": (4656, 3496),  # Max OV64A40
        
        # Résolution pour la prévisualisation
        "preview_resolution": (1280, 720),
        
        # Paramètres de qualité
        "jpeg_quality": 85,
        "fps": 30,
        
        # Paramètres d'autofocus
        "autofocus_duration": 8,  # secondes
        "autofocus_mode": 2,  # Continuous AF
        
        # Paramètres de zoom
        "zoom_factor": 2.0,
        "zoom_center": (0.5, 0.5),
    }
    
    # Configuration du traitement d'image
    IMAGE_PROCESSING = {
        # Seuillage pour détection du label blanc
        "white_threshold": 200,
        
        # Taille minimum du contour (pixels²)
        "min_contour_area": 1000,
        
        # Marge autour du label détecté
        "label_margin": 10,
        
        # Paramètres de binarisation adaptative
        "adaptive_threshold": {
            "max_value": 255,
            "adaptive_method": "ADAPTIVE_THRESH_GAUSSIAN_C",
            "threshold_type": "THRESH_BINARY",
            "block_size": 11,
            "C": 2
        },
        
        # Rotations à tester pour le décodage
        "rotation_angles": [0, 90, 180, 270],
        
        # Paramètres de morphologie
        "morphology_kernel_size": (3, 3),
        "morphology_iterations": 1,
    }
    
    # Configuration des fichiers
    STORAGE = {
        # Dossier de stockage des images
        "images_dir": Path("images"),
        
        # Nombre d'images récentes à afficher
        "recent_images_count": 3,
        
        # Format des noms de fichiers
        "filename_format": "%Y%m%d_%H%M%S",
        
        # Extensions autorisées
        "allowed_extensions": [".jpg", ".jpeg", ".png"],
        
        # Taille maximale des fichiers (Mo)
        "max_file_size": 10,
        
        # Durée de rétention des fichiers (jours)
        "retention_days": 30,
    }
    
    # Configuration série
    SERIAL_CONFIG = {
        "port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "timeout": 1,
        "signal_byte": b'\x01',
    }
    
    # Configuration des logs
    LOGGING = {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": "datamatrix_scanner.log",
        "max_size": 10 * 1024 * 1024,  # 10MB
        "backup_count": 5,
    }
    
    # Configuration WebSocket
    WEBSOCKET = {
        "reconnect_attempts": 5,
        "reconnect_delay": 1000,  # ms
        "ping_interval": 30,  # secondes
        "ping_timeout": 5,  # secondes
    }
    
    # Configuration de sécurité
    SECURITY = {
        "allowed_hosts": ["*"],
        "cors_origins": ["*"],
        "max_connections": 10,
        "rate_limit": {
            "capture": 1,  # captures par seconde
            "focus": 0.1,  # focus par seconde (1 toutes les 10s)
        }
    }
    
    # Messages d'interface
    MESSAGES = {
        "fr": {
            "capture_start": "Capture en cours...",
            "capture_success": "Photo capturée avec succès",
            "capture_error": "Erreur lors de la capture",
            "focus_start": "Autofocus en cours...",
            "focus_success": "Autofocus terminé",
            "focus_error": "Erreur d'autofocus",
            "datamatrix_found": "Code DataMatrix détecté",
            "datamatrix_not_found": "Aucun code DataMatrix détecté",
            "zoom_applied": "Zoom appliqué",
            "zoom_reset": "Zoom réinitialisé",
            "serial_sent": "Signal série envoyé",
            "serial_error": "Erreur signal série",
            "connection_established": "Connexion établie",
            "connection_lost": "Connexion perdue",
        },
        "en": {
            "capture_start": "Capture in progress...",
            "capture_success": "Photo captured successfully",
            "capture_error": "Capture error",
            "focus_start": "Autofocus in progress...",
            "focus_success": "Autofocus completed",
            "focus_error": "Autofocus error",
            "datamatrix_found": "DataMatrix code detected",
            "datamatrix_not_found": "No DataMatrix code detected",
            "zoom_applied": "Zoom applied",
            "zoom_reset": "Zoom reset",
            "serial_sent": "Serial signal sent",
            "serial_error": "Serial signal error",
            "connection_established": "Connection established",
            "connection_lost": "Connection lost",
        }
    }
    
    # Configuration par défaut de la langue
    DEFAULT_LANGUAGE = "fr"
    
    @classmethod
    def get_message(cls, key: str, lang: str = None) -> str:
        """Récupère un message dans la langue spécifiée"""
        if lang is None:
            lang = cls.DEFAULT_LANGUAGE
        
        return cls.MESSAGES.get(lang, {}).get(key, key)
    
    @classmethod
    def create_directories(cls):
        """Crée les dossiers nécessaires"""
        cls.STORAGE["images_dir"].mkdir(exist_ok=True)
        
        # Création du dossier de logs
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
    
    @classmethod
    def validate_config(cls):
        """Valide la configuration"""
        errors = []
        
        # Vérification des résolutions
        if cls.CAMERA_CONFIG["stream_resolution"][0] <= 0:
            errors.append("La résolution de stream doit être positive")
        
        if cls.CAMERA_CONFIG["capture_resolution"][0] <= 0:
            errors.append("La résolution de capture doit être positive")
        
        # Vérification des paramètres de traitement
        if cls.IMAGE_PROCESSING["min_contour_area"] <= 0:
            errors.append("La surface minimum du contour doit être positive")
        
        if cls.IMAGE_PROCESSING["white_threshold"] not in range(0, 256):
            errors.append("Le seuil de blanc doit être entre 0 et 255")
        
        # Vérification des paramètres de stockage
        if cls.STORAGE["recent_images_count"] <= 0:
            errors.append("Le nombre d'images récentes doit être positif")
        
        if cls.STORAGE["max_file_size"] <= 0:
            errors.append("La taille maximale des fichiers doit être positive")
        
        return errors


class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    LOGGING = {
        **Config.LOGGING,
        "level": "DEBUG",
    }


class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    SECURITY = {
        **Config.SECURITY,
        "allowed_hosts": ["localhost", "127.0.0.1"],
        "cors_origins": ["http://localhost:8000"],
    }


class TestConfig(Config):
    """Configuration pour les tests"""
    STORAGE = {
        **Config.STORAGE,
        "images_dir": Path("test_images"),
    }
    CAMERA_CONFIG = {
        **Config.CAMERA_CONFIG,
        "stream_resolution": (320, 240),
        "capture_resolution": (640, 480),
    }


# Configuration active basée sur la variable d'environnement
def get_config():
    """Retourne la configuration active"""
    env = os.getenv("DATAMATRIX_ENV", "production").lower()
    
    if env == "development":
        return DevelopmentConfig
    elif env == "test":
        return TestConfig
    else:
        return ProductionConfig


# Export de la configuration active
config = get_config()