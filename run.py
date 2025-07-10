#!/usr/bin/env python3
"""
Script de lancement pour DataMatrix Scanner
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

import uvicorn

# Import de la configuration
from config import config

# Configuration du logging
def setup_logging():
    """Configure le système de logging"""
    log_format = logging.Formatter(config.LOGGING["format"])
    
    # Logger root
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOGGING["level"]))
    
    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    # Handler fichier
    if config.LOGGING.get("file"):
        from logging.handlers import RotatingFileHandler
        
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_dir / config.LOGGING["file"],
            maxBytes=config.LOGGING["max_size"],
            backupCount=config.LOGGING["backup_count"]
        )
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    
    return logger


def check_dependencies():
    """Vérifie les dépendances système"""
    logger = logging.getLogger(__name__)
    
    try:
        import cv2
        logger.info(f"OpenCV version: {cv2.__version__}")
    except ImportError:
        logger.error("OpenCV non installé")
        return False
    
    try:
        from picamera2 import Picamera2
        logger.info("Picamera2 disponible")
    except ImportError:
        logger.error("Picamera2 non installé")
        return False
    
    try:
        from pylibdmtx import pylibdmtx
        logger.info("pylibdmtx disponible")
    except ImportError:
        logger.error("pylibdmtx non installé")
        return False
    
    try:
        import serial
        logger.info("pyserial disponible")
    except ImportError:
        logger.warning("pyserial non installé - communication série désactivée")
    
    return True


def check_camera():
    """Vérifie la disponibilité de la caméra"""
    logger = logging.getLogger(__name__)
    
    try:
        from picamera2 import Picamera2
        
        # Test d'initialisation rapide
        picam2 = Picamera2()
        camera_info = picam2.camera_properties
        picam2.close()
        
        logger.info(f"Caméra détectée: {camera_info.get('Model', 'Inconnue')}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur caméra: {e}")
        logger.error("Vérifiez que la caméra est connectée et activée")
        return False


def check_permissions():
    """Vérifie les permissions nécessaires"""
    logger = logging.getLogger(__name__)
    
    # Vérification des groupes utilisateur
    import grp
    import pwd
    
    user = pwd.getpwuid(os.getuid()).pw_name
    groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
    
    required_groups = ['video', 'dialout']
    missing_groups = [g for g in required_groups if g not in groups]
    
    if missing_groups:
        logger.warning(f"Groupes manquants: {missing_groups}")
        logger.warning("Exécutez: sudo usermod -a -G video,dialout $USER")
        logger.warning("Puis redémarrez ou reconnectez-vous")
    
    # Vérification des ports série
    serial_ports = ['/dev/ttyUSB0', '/dev/ttyACM0', '/dev/serial0']
    available_ports = [p for p in serial_ports if Path(p).exists()]
    
    if available_ports:
        logger.info(f"Ports série disponibles: {available_ports}")
    else:
        logger.warning("Aucun port série détecté")
    
    return len(missing_groups) == 0


def cleanup_old_files():
    """Nettoie les anciens fichiers"""
    logger = logging.getLogger(__name__)
    
    images_dir = config.STORAGE["images_dir"]
    if not images_dir.exists():
        return
    
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.now() - timedelta(days=config.STORAGE["retention_days"])
    
    removed_count = 0
    for image_file in images_dir.glob("*.jpg"):
        if datetime.fromtimestamp(image_file.stat().st_mtime) < cutoff_date:
            try:
                image_file.unlink()
                removed_count += 1
            except Exception as e:
                logger.warning(f"Impossible de supprimer {image_file}: {e}")
    
    if removed_count > 0:
        logger.info(f"{removed_count} ancien(s) fichier(s) supprimé(s)")


def run_server():
    """Lance le serveur FastAPI"""
    logger = logging.getLogger(__name__)
    
    logger.info("Démarrage du serveur DataMatrix Scanner")
    logger.info(f"Host: {config.HOST}, Port: {config.PORT}")
    logger.info(f"Debug: {config.DEBUG}")
    
    # Import de l'application
    from main import app
    
    # Configuration uvicorn
    uvicorn_config = {
        "host": config.HOST,
        "port": config.PORT,
        "reload": config.DEBUG,
        "log_level": config.LOGGING["level"].lower(),
        "access_log": True,
        "server_header": False,
        "date_header": False,
    }
    
    # Lancement du serveur
    uvicorn.run("main:app", **uvicorn_config)


def run_development():
    """Mode développement avec rechargement automatique"""
    logger = logging.getLogger(__name__)
    
    logger.info("Mode développement activé")
    
    # Variables d'environnement pour le développement
    os.environ["DATAMATRIX_ENV"] = "development"
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["./"],
        reload_includes=["*.py", "*.html"],
        log_level="debug"
    )


def run_tests():
    """Exécute les tests système"""
    logger = logging.getLogger(__name__)
    
    logger.info("=== Tests système ===")
    
    success = True
    
    # Test des dépendances
    logger.info("Test des dépendances...")
    if not check_dependencies():
        success = False
    
    # Test de la caméra
    logger.info("Test de la caméra...")
    if not check_camera():
        success = False
    
    # Test des permissions
    logger.info("Test des permissions...")
    if not check_permissions():
        logger.warning("Permissions incomplètes")
    
    # Test de configuration
    logger.info("Test de la configuration...")
    config_errors = config.validate_config()
    if config_errors:
        logger.error("Erreurs de configuration:")
        for error in config_errors:
            logger.error(f"  - {error}")
        success = False
    
    # Test de création des dossiers
    logger.info("Test de création des dossiers...")
    try:
        config.create_directories()
        logger.info("Dossiers créés avec succès")
    except Exception as e:
        logger.error(f"Erreur création dossiers: {e}")
        success = False
    
    if success:
        logger.info("✅ Tous les tests sont passés")
        return 0
    else:
        logger.error("❌ Certains tests ont échoué")
        return 1


def show_status():
    """Affiche le statut du système"""
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*50)
    print("📊 STATUT DU SYSTÈME DATAMATRIX SCANNER")
    print("="*50)
    
    # Informations système
    import platform
    print(f"🖥️  Système: {platform.system()} {platform.release()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    
    # Statut des dépendances
    print(f"\n📦 DÉPENDANCES:")
    deps = {
        "OpenCV": "cv2",
        "Picamera2": "picamera2",
        "pylibdmtx": "pylibdmtx",
        "FastAPI": "fastapi",
        "Uvicorn": "uvicorn",
        "Serial": "serial"
    }
    
    for name, module in deps.items():
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name}")
    
    # Statut de la caméra
    print(f"\n📹 CAMÉRA:")
    if check_camera():
        print("  ✅ Caméra disponible")
    else:
        print("  ❌ Caméra non détectée")
    
    # Configuration
    print(f"\n⚙️  CONFIGURATION:")
    print(f"  📁 Dossier images: {config.STORAGE['images_dir']}")
    print(f"  🌐 Host: {config.HOST}:{config.PORT}")
    print(f"  🐛 Debug: {config.DEBUG}")
    
    # Espace disque
    images_dir = config.STORAGE["images_dir"]
    if images_dir.exists():
        import shutil
        total, used, free = shutil.disk_usage(images_dir)
        print(f"  💾 Espace libre: {free // (1024**3)} GB")
        
        # Nombre d'images
        image_count = len(list(images_dir.glob("*.jpg")))
        print(f"  🖼️  Images stockées: {image_count}")


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="DataMatrix Scanner - Capture et décodage de codes DataMatrix"
    )
    
    parser.add_argument(
        "command",
        choices=["start", "dev", "test", "status", "clean"],
        help="Commande à exécuter"
    )
    
    parser.add_argument(
        "--host",
        default=config.HOST,
        help="Adresse d'écoute"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=config.PORT,
        help="Port d'écoute"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mode debug"
    )
    
    args = parser.parse_args()
    
    # Configuration du logging
    logger = setup_logging()
    
    # Mise à jour de la configuration avec les arguments
    if args.host != config.HOST:
        config.HOST = args.host
    if args.port != config.PORT:
        config.PORT = args.port
    if args.debug:
        config.DEBUG = True
    
    # Création des dossiers
    config.create_directories()
    
    # Exécution de la commande
    try:
        if args.command == "start":
            run_server()
        elif args.command == "dev":
            run_development()
        elif args.command == "test":
            return run_tests()
        elif args.command == "status":
            show_status()
        elif args.command == "clean":
            cleanup_old_files()
            logger.info("Nettoyage terminé")
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
        return 0
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())