# Test de connectivité
ping:
	@echo "🔍 Test de connectivité..."
	@if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200\|404"; then \
		echo "✅ Serveur accessible"; \
	else \
		echo "❌ Serveur non accessible"; \
	fi

# Affichage de la configuration
config:
	@echo "⚙️  Configuration actuelle:"
	@echo "  📁 Projet: $(PWD)"
	@echo "  🐍 Python: $(PYTHON)"
	@echo "  👤 Utilisateur: $(USER)"
	@echo "  🌐 IP: $(shell hostname -I | awk '{print $1}')"

# Makefile pour DataMatrix Scanner
.PHONY: help install setup start dev test clean status logs fix-camera backup restore

# Variables
VENV_DIR = venv
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip
PROJECT_NAME = datamatrix-scanner
BACKUP_DIR = ./backup/backup_$(shell date +%Y%m%d_%H%M%S)

# Aide par défaut
help:
	@echo "🚀 DataMatrix Scanner - Commandes disponibles:"
	@echo ""
	@echo "📦 INSTALLATION:"
	@echo "  make setup           - Configuration de l'environnement Python"
	@echo "  make install-deps    - Installation des dépendances système"
	@echo ""
	@echo "🎯 DÉVELOPPEMENT:"
	@echo "  make start           - Démarrage en mode production"
	@echo "  make dev             - Démarrage en mode développement"
	@echo "  make test            - Exécution des tests système"
	@echo "  make clean           - Nettoyage des fichiers temporaires"
	@echo ""
	@echo "📊 MONITORING:"
	@echo "  make status          - Affichage du statut système"
	@echo "  make logs            - Affichage des logs en temps réel"
	@echo "  make check           - Vérification complète du système"
	@echo ""
	@echo "🔧 RÉPARATION:"
	@echo "  make fix-camera      - Répare l'accès à Picamera2"
	@echo "  make fix-permissions - Répare les permissions"
	@echo ""
	@echo "💾 SAUVEGARDE:"
	@echo "  make backup          - Sauvegarde complète"
	@echo "  make restore         - Restauration depuis sauvegarde"
	@echo "  make list-backups    - Liste des sauvegardes"
	@echo "  make clean-backups   - Nettoie les anciennes sauvegardes"

# Installation des dépendances système
install-deps:
	@echo "📦 Installation des dépendances système..."
	sudo apt update
	sudo apt install -y python3-pip python3-venv python3-dev build-essential cmake pkg-config libzbar-dev libdmtx-dev libopencv-dev python3-opencv libatlas-base-dev libhdf5-dev libcamera-dev libcamera-apps python3-libcamera git curl
	@echo "📹 Activation de la caméra..."
	sudo raspi-config nonint do_camera 0
	@echo "👥 Configuration des permissions..."
	sudo usermod -a -G dialout,video $(USER)

# Configuration de l'environnement Python
setup:
	@echo "🐍 Configuration de l'environnement Python..."
	python3 -m venv $(VENV_DIR) --system-site-packages
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt
	@echo "📁 Création des dossiers..."
	mkdir -p images logs backup
	@echo "✅ Configuration terminée!"

# Démarrage en mode production
start:
	@echo "🚀 Démarrage du serveur en mode production..."
	$(PYTHON) run.py start

# Démarrage en mode développement
dev:
	@echo "🔧 Démarrage en mode développement..."
	$(PYTHON) run.py dev

# Tests système
test:
	@echo "🧪 Exécution des tests système..."
	$(PYTHON) run.py test

# Statut du système
status:
	@echo "📊 Statut du système..."
	$(PYTHON) run.py status

# Nettoyage
clean:
	@echo "🗑️  Nettoyage des fichiers temporaires..."
	$(PYTHON) run.py clean
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Logs en temps réel
logs:
	@echo "📋 Affichage des logs..."
	@if [ -f "logs/datamatrix_scanner.log" ]; then \
		tail -f logs/datamatrix_scanner.log; \
	else \
		echo "❌ Aucun log disponible. Démarrez d'abord l'application."; \
	fi

# Vérification complète
check:
	@echo "🔍 Vérification complète du système..."
	@echo ""
	@echo "📦 Dépendances Python:"
	@$(PYTHON) -c "import cv2; print('  ✅ OpenCV')" 2>/dev/null || echo "  ❌ OpenCV manquant"
	@$(PYTHON) -c "import picamera2; print('  ✅ Picamera2')" 2>/dev/null || echo "  ❌ Picamera2 manquant"
	@$(PYTHON) -c "import pylibdmtx; print('  ✅ pylibdmtx')" 2>/dev/null || echo "  ❌ pylibdmtx manquant"
	@$(PYTHON) -c "import fastapi; print('  ✅ FastAPI')" 2>/dev/null || echo "  ❌ FastAPI manquant"
	@echo ""
	@echo "📹 Caméra:"
	@if libcamera-hello --list-cameras --timeout 1 >/dev/null 2>&1; then \
		echo "  ✅ Caméra détectée"; \
	else \
		echo "  ❌ Caméra non détectée"; \
	fi

# Réparation de la caméra
fix-camera:
	@echo "🔧 Réparation de l'accès à Picamera2..."
	@if [ -f "fix_camera.sh" ]; then \
		chmod +x fix_camera.sh; \
		./fix_camera.sh; \
	else \
		echo "❌ Script fix_camera.sh non trouvé"; \
		make recreate-venv; \
	fi

# Réparation des permissions
fix-permissions:
	@echo "🔐 Réparation des permissions..."
	sudo usermod -a -G video,dialout $(USER)
	@echo "✅ Permissions mises à jour"

# Recréation de l'environnement virtuel
recreate-venv:
	@echo "🔄 Recréation de l'environnement virtuel..."
	@if [ -d "$(VENV_DIR)" ]; then \
		mv $(VENV_DIR) $(VENV_DIR)_backup_$(shell date +%Y%m%d_%H%M%S); \
	fi
	python3 -m venv $(VENV_DIR) --system-site-packages
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt
	@echo "✅ Environnement virtuel recréé"

# Sauvegarde complète
backup:
	@echo "💾 Création de la sauvegarde..."
	mkdir -p $(BACKUP_DIR)
	@echo "📁 Copie des fichiers du projet..."
	cp *.py $(BACKUP_DIR)/ 2>/dev/null || echo "Aucun fichier .py trouvé"
	cp *.html $(BACKUP_DIR)/ 2>/dev/null || echo "Aucun fichier .html trouvé"
	cp *.sh $(BACKUP_DIR)/ 2>/dev/null || echo "Aucun fichier .sh trouvé"
	cp requirements.txt $(BACKUP_DIR)/ 2>/dev/null || echo "requirements.txt non trouvé"
	cp Makefile $(BACKUP_DIR)/ 2>/dev/null || echo "Makefile non trouvé"
	cp README.md $(BACKUP_DIR)/ 2>/dev/null || echo "README.md non trouvé"
	@echo "🖼️  Copie des images..."
	@if [ -d "images" ]; then \
		cp -r images $(BACKUP_DIR)/; \
		echo "Images copiées"; \
	else \
		echo "Dossier images non trouvé"; \
	fi
	@echo "📋 Copie des logs..."
	@if [ -d "logs" ]; then \
		cp -r logs $(BACKUP_DIR)/; \
		echo "Logs copiés"; \
	else \
		echo "Dossier logs non trouvé"; \
	fi
	@echo "📦 Création de l'archive..."
	tar -czf $(BACKUP_DIR).tar.gz $(BACKUP_DIR)
	rm -rf $(BACKUP_DIR)
	@echo "✅ Sauvegarde créée: $(BACKUP_DIR).tar.gz"
	@ls -lh $(BACKUP_DIR).tar.gz

# Restauration depuis sauvegarde
restore:
	@echo "📥 Restauration depuis sauvegarde..."
	@echo ""
	@echo "📋 Sauvegardes disponibles:"
	@ls -la ./backup/backup_*.tar.gz 2>/dev/null || (echo "❌ Aucune sauvegarde trouvée" && exit 1)
	@echo ""
	@echo "💡 Entrez le nom complet du fichier (ex: backup_20250707_120000.tar.gz):"
	@read -p "Fichier: " backup_file; \
	if [ -f "$backup_file" ]; then \
		echo "📦 Extraction de $backup_file..."; \
		backup_dir=$(basename "$backup_file" .tar.gz); \
		tar -xzf "$backup_file"; \
		echo "📁 Restauration des fichiers..."; \
		cp "$backup_dir"/*.py . 2>/dev/null || echo "Aucun fichier .py à restaurer"; \
		cp "$backup_dir"/*.html . 2>/dev/null || echo "Aucun fichier .html à restaurer"; \
		cp "$backup_dir"/*.sh . 2>/dev/null || echo "Aucun fichier .sh à restaurer"; \
		cp "$backup_dir"/requirements.txt . 2>/dev/null || echo "requirements.txt non restauré"; \
		cp "$backup_dir"/Makefile . 2>/dev/null || echo "Makefile non restauré"; \
		cp "$backup_dir"/README.md . 2>/dev/null || echo "README.md non restauré"; \
		if [ -d "$backup_dir/images" ]; then \
			echo "🖼️  Restauration des images..."; \
			cp -r "$backup_dir"/images . 2>/dev/null || echo "Erreur restauration images"; \
		fi; \
		if [ -d "$backup_dir/logs" ]; then \
			echo "📋 Restauration des logs..."; \
			cp -r "$backup_dir"/logs . 2>/dev/null || echo "Erreur restauration logs"; \
		fi; \
		rm -rf "$backup_dir"; \
		echo "✅ Restauration terminée depuis $backup_file"; \
	else \
		echo "❌ Fichier $backup_file non trouvé"; \
		exit 1; \
	fi

# Liste des sauvegardes
list-backups:
	@echo "📋 Sauvegardes disponibles:"
	@ls -la ./backup/backup_*.tar.gz 2>/dev/null || echo "❌ Aucune sauvegarde trouvée"

# Suppression des anciennes sauvegardes (garde les 5 dernières)
clean-backups:
	@echo "🗑️  Nettoyage des anciennes sauvegardes..."
	@ls -t ./backup/backup_*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || echo "Aucune ancienne sauvegarde à supprimer"
	@echo "✅ Nettoyage terminé (5 dernières sauvegardes conservées)"