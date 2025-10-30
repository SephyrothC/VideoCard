#!/usr/bin/env python3
"""
Storage Manager - Gestion intelligente du stockage avec fallback automatique
Supporte le stockage réseau SMB avec basculement transparent vers le stockage local
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv

# Chargement de la configuration
load_dotenv()

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Gestionnaire de stockage avec support SMB et fallback local automatique.

    Features:
    - Détection automatique de la disponibilité du partage réseau
    - Fallback transparent vers le stockage local en cas d'échec réseau
    - Vérification périodique de la santé du montage
    - Logs détaillés des opérations
    """

    def __init__(self):
        """Initialise le gestionnaire de stockage"""

        # Configuration depuis .env
        self.network_enabled = os.getenv("NETWORK_STORAGE_ENABLED", "true").lower() == "true"
        self.mount_point = Path(os.getenv("MOUNT_POINT", "/mnt/sharetest"))
        self.fallback_dir = Path(os.getenv("LOCAL_FALLBACK_DIR", "images"))
        self.network_timeout = int(os.getenv("NETWORK_TIMEOUT", "5"))
        self.debug = os.getenv("STORAGE_DEBUG", "true").lower() == "true"

        # État du stockage
        self._network_available = False
        self._last_check_time = 0
        self._check_interval = 60  # Revérifier toutes les 60 secondes
        self._consecutive_failures = 0
        self._max_failures = 3  # Nombre d'échecs avant de basculer définitivement en local

        # Configuration logging
        if self.debug:
            logger.setLevel(logging.DEBUG)

        # Initialisation
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialise les dossiers de stockage et vérifie le réseau"""

        # Créer le dossier de fallback local s'il n'existe pas
        self.fallback_dir.mkdir(exist_ok=True)
        logger.info(f"Dossier de fallback local prêt: {self.fallback_dir}")

        # Vérifier la disponibilité du réseau si activé
        if self.network_enabled:
            self._check_network_availability()
        else:
            logger.info("Stockage réseau désactivé - utilisation du stockage local uniquement")

    def _check_network_availability(self) -> bool:
        """
        Vérifie si le partage réseau est disponible et accessible en écriture.

        Returns:
            bool: True si le réseau est disponible, False sinon
        """
        current_time = time.time()

        # Utiliser le cache si la vérification est récente
        if current_time - self._last_check_time < self._check_interval:
            return self._network_available

        self._last_check_time = current_time

        try:
            # Vérifier que le point de montage existe
            if not self.mount_point.exists():
                logger.debug(f"Point de montage introuvable: {self.mount_point}")
                self._network_available = False
                return False

            # Vérifier que c'est bien un point de montage
            if not self.mount_point.is_mount():
                logger.debug(f"Le chemin n'est pas un point de montage: {self.mount_point}")
                self._network_available = False
                return False

            # Test d'écriture avec fichier temporaire
            test_file = self.mount_point / ".storage_test"
            try:
                with open(test_file, 'w') as f:
                    f.write(f"test_{current_time}")
                test_file.unlink()  # Supprimer le fichier de test

                logger.debug(f"Partage réseau accessible: {self.mount_point}")
                self._network_available = True
                self._consecutive_failures = 0  # Réinitialiser le compteur d'échecs
                return True

            except (OSError, IOError) as e:
                logger.warning(f"Test d'écriture échoué sur {self.mount_point}: {e}")
                self._network_available = False
                return False

        except Exception as e:
            logger.warning(f"Erreur vérification réseau: {e}")
            self._network_available = False
            return False

    def get_storage_path(self) -> Tuple[Path, bool]:
        """
        Détermine le meilleur chemin de stockage disponible.

        Returns:
            Tuple[Path, bool]: (chemin_de_stockage, est_réseau)
                - chemin_de_stockage: Path où sauvegarder les fichiers
                - est_réseau: True si c'est le stockage réseau, False si c'est le fallback local
        """
        # Si le réseau est désactivé, toujours utiliser le local
        if not self.network_enabled:
            if self.debug:
                logger.debug("Réseau désactivé - utilisation du stockage local")
            return self.fallback_dir, False

        # Si trop d'échecs consécutifs, basculer en mode local temporaire
        if self._consecutive_failures >= self._max_failures:
            logger.warning(f"Trop d'échecs réseau ({self._consecutive_failures}) - "
                          f"basculement en mode local temporaire")
            return self.fallback_dir, False

        # Vérifier la disponibilité du réseau
        if self._check_network_availability():
            if self.debug:
                logger.debug(f"Stockage réseau disponible: {self.mount_point}")
            return self.mount_point, True
        else:
            logger.warning("Partage réseau indisponible - utilisation du fallback local")
            return self.fallback_dir, False

    def save_file(self, filename: str, save_func, *args, **kwargs) -> Tuple[str, bool]:
        """
        Sauvegarde un fichier avec fallback automatique.

        Args:
            filename: Nom du fichier à sauvegarder
            save_func: Fonction de sauvegarde (ex: cv2.imwrite)
            *args, **kwargs: Arguments à passer à save_func

        Returns:
            Tuple[str, bool]: (chemin_complet, succès)
                - chemin_complet: Chemin du fichier sauvegardé
                - succès: True si la sauvegarde a réussi, False sinon
        """
        # Obtenir le chemin de stockage
        storage_path, is_network = self.get_storage_path()
        filepath = storage_path / filename

        try:
            # Créer le dossier si nécessaire
            storage_path.mkdir(parents=True, exist_ok=True)

            # Tenter la sauvegarde
            result = save_func(str(filepath), *args, **kwargs)

            if result:
                storage_type = "réseau" if is_network else "local"
                logger.info(f"Fichier sauvegardé sur stockage {storage_type}: {filepath}")
                self._consecutive_failures = 0  # Réinitialiser sur succès
                return str(filepath), True
            else:
                raise Exception("Échec de la fonction de sauvegarde")

        except Exception as e:
            logger.error(f"Erreur sauvegarde sur {storage_path}: {e}")

            # Si on était sur le réseau, essayer le fallback local
            if is_network:
                logger.warning("Tentative de fallback sur stockage local...")
                self._consecutive_failures += 1

                try:
                    # Créer le dossier fallback si nécessaire
                    self.fallback_dir.mkdir(parents=True, exist_ok=True)

                    # Tenter la sauvegarde locale
                    fallback_filepath = self.fallback_dir / filename
                    result = save_func(str(fallback_filepath), *args, **kwargs)

                    if result:
                        logger.info(f"Fichier sauvegardé en fallback local: {fallback_filepath}")
                        return str(fallback_filepath), True
                    else:
                        raise Exception("Échec de la sauvegarde en fallback")

                except Exception as fallback_error:
                    logger.error(f"Échec du fallback local: {fallback_error}")
                    return "", False
            else:
                # Déjà en mode local, pas de fallback possible
                return "", False

    def get_file_path(self, filename: str) -> Optional[Path]:
        """
        Recherche un fichier dans les différents emplacements de stockage.

        Args:
            filename: Nom du fichier à rechercher

        Returns:
            Optional[Path]: Chemin du fichier trouvé, ou None
        """
        # Chercher d'abord sur le réseau si disponible
        if self.network_enabled and self._check_network_availability():
            network_file = self.mount_point / filename
            if network_file.exists():
                return network_file

        # Chercher dans le fallback local
        local_file = self.fallback_dir / filename
        if local_file.exists():
            return local_file

        logger.warning(f"Fichier introuvable: {filename}")
        return None

    def list_files(self, pattern: str = "*.jpg", limit: Optional[int] = None) -> list:
        """
        Liste les fichiers dans tous les emplacements de stockage.

        Args:
            pattern: Pattern de recherche (ex: "*.jpg")
            limit: Nombre maximum de fichiers à retourner

        Returns:
            list: Liste des chemins de fichiers trouvés (triés par date de modification)
        """
        all_files = []

        # Lister les fichiers du réseau si disponible
        if self.network_enabled and self._check_network_availability():
            try:
                network_files = list(self.mount_point.glob(pattern))
                all_files.extend(network_files)
                logger.debug(f"Fichiers réseau trouvés: {len(network_files)}")
            except Exception as e:
                logger.warning(f"Erreur listage fichiers réseau: {e}")

        # Lister les fichiers locaux
        try:
            local_files = list(self.fallback_dir.glob(pattern))
            all_files.extend(local_files)
            logger.debug(f"Fichiers locaux trouvés: {len(local_files)}")
        except Exception as e:
            logger.warning(f"Erreur listage fichiers locaux: {e}")

        # Supprimer les doublons (par nom de fichier)
        unique_files = {}
        for file_path in all_files:
            if file_path.name not in unique_files:
                unique_files[file_path.name] = file_path
            else:
                # Garder le plus récent
                if file_path.stat().st_mtime > unique_files[file_path.name].stat().st_mtime:
                    unique_files[file_path.name] = file_path

        # Trier par date de modification (plus récent en premier)
        sorted_files = sorted(
            unique_files.values(),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        # Appliquer la limite si demandée
        if limit:
            sorted_files = sorted_files[:limit]

        return sorted_files

    def get_storage_status(self) -> dict:
        """
        Retourne l'état actuel du système de stockage.

        Returns:
            dict: Informations sur l'état du stockage
        """
        network_available = self._check_network_availability() if self.network_enabled else False

        return {
            "network_enabled": self.network_enabled,
            "network_available": network_available,
            "mount_point": str(self.mount_point),
            "fallback_dir": str(self.fallback_dir),
            "consecutive_failures": self._consecutive_failures,
            "using_fallback": self._consecutive_failures >= self._max_failures or not network_available,
            "current_storage": str(self.mount_point if network_available else self.fallback_dir)
        }

    def reset_failure_counter(self):
        """Réinitialise le compteur d'échecs (utile pour forcer une nouvelle tentative réseau)"""
        self._consecutive_failures = 0
        self._last_check_time = 0  # Force une nouvelle vérification
        logger.info("Compteur d'échecs réinitialisé - prochaine vérification réseau forcée")


# Instance globale du gestionnaire de stockage
storage_manager = StorageManager()


def get_storage_manager() -> StorageManager:
    """
    Retourne l'instance globale du gestionnaire de stockage.

    Returns:
        StorageManager: Instance du gestionnaire
    """
    return storage_manager


if __name__ == "__main__":
    # Test du module
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    manager = StorageManager()
    print("\n=== État du stockage ===")
    status = manager.get_storage_status()
    for key, value in status.items():
        print(f"{key}: {value}")

    print("\n=== Test de chemin de stockage ===")
    path, is_network = manager.get_storage_path()
    print(f"Chemin de stockage: {path}")
    print(f"Est réseau: {is_network}")

    print("\n=== Listage des fichiers ===")
    files = manager.list_files(limit=5)
    print(f"Fichiers trouvés: {len(files)}")
    for f in files:
        print(f"  - {f}")
