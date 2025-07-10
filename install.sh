#!/bin/bash

# Script d'installation pour DataMatrix Scanner sur Raspberry Pi 5
# Auteur: Adrian Stephan
# Date: 2025

set -e

echo "🚀 Installation du DataMatrix Scanner sur Raspberry Pi 5"
echo "=========================================================="

# Vérification du système
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  Attention: Ce script est optimisé pour Raspberry Pi"
fi

# Détection de la version OS
OS_VERSION=$(lsb_release -rs 2>/dev/null || echo "unknown")
echo "📋 Système détecté: Raspberry Pi OS $OS_VERSION"

# Mise à jour du système
echo "📦 Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

# Installation des dépendances système de base
echo "🔧 Installation des dépendances système de base..."
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    cmake \
    pkg-config \
    git \
    curl \
    wget

# Installation des bibliothèques pour vision par ordinateur
echo "📸 Installation des bibliothèques de vision..."
sudo apt install -y \
    libzbar-dev \
    libdmtx-dev \
    libopencv-dev \
    python3-opencv \
    libatlas-base-dev \
    libhdf5-dev

# Installation des bibliothèques multimédia (avec gestion des erreurs)
echo "🎬 Installation des bibliothèques multimédia..."
MULTIMEDIA_PACKAGES=(
    "libharfbuzz0b"
    "libwebp-dev"
    "libtiff-dev"
    "libopenexr-dev"
    "libgstreamer1.0-dev"
    "libavcodec-dev"
    "libavformat-dev"
    "libswscale-dev"
    "libv4l-dev"
)

for package in "${MULTIMEDIA_PACKAGES[@]}"; do
    if sudo apt install -y "$package" 2>/dev/null; then
        echo "  ✅ $package installé"
    else
        echo "  ⚠️  $package non disponible (ignoré)"
    fi
done

# Packages alternatifs pour les versions récentes
echo "🔄 Installation des packages alternatifs..."
ALTERNATIVE_PACKAGES=(
    "libimath-dev"      # remplace libilmbase-dev
    "libwebp7"          # version plus récente de libwebp
    "libtiff6"          # version plus récente de libtiff
    "libjpeg-dev"       # remplace libjasper
)

for package in "${ALTERNATIVE_PACKAGES[@]}"; do
    if sudo apt install -y "$package" 2>/dev/null; then
        echo "  ✅ $package installé"
    else
        echo "  ⚠️  $package non disponible (ignoré)"
    fi
done

# Installation de libcamera (pour Picamera2)
echo "📹 Installation de libcamera..."
sudo apt install -y \
    libcamera-dev \
    libcamera-apps \
    python3-libcamera \
    python3-kms++ || echo "⚠️  Certains packages libcamera non disponibles (normal sur certaines versions)"

# Activation de la caméra
echo "🎥 Configuration de la caméra..."
sudo raspi-config nonint do_camera 0

# Création du dossier de projet
PROJECT_DIR="$HOME/datamatrix_scanner"
if [ ! -d "$PROJECT_DIR" ]; then
    mkdir -p "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# Copie des fichiers de projet si ils n'existent pas
echo "📁 Vérification des fichiers de projet..."
if [ ! -f "requirements.txt" ]; then
    echo "⚠️  Le fichier requirements.txt n'est pas trouvé dans le dossier courant."
    echo "📋 Création d'un requirements.txt minimal..."
    cat > requirements.txt << 'EOF'
# FastAPI et serveur web
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
websockets==12.0

# Vision par ordinateur
opencv-python==4.8.1.78
numpy==1.24.3
Pillow==10.0.1

# Caméra Raspberry Pi
picamera2

# Décodage DataMatrix
pylibdmtx==0.1.10

# Communication série
pyserial==3.5

# Utilitaires
python-dateutil==2.8.2
EOF
fi

# Création de l'environnement virtuel avec accès aux paquets système
echo "🐍 Création de l'environnement virtuel Python..."
echo "📦 Utilisation de --system-site-packages pour accès à Picamera2..."
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Mise à jour de pip
echo "📦 Mise à jour de pip..."
pip install --upgrade pip setuptools wheel

# Installation des dépendances Python avec gestion d'erreurs
echo "📚 Installation des dépendances Python..."

# Installation de base
pip install fastapi uvicorn[standard] websockets python-multipart || {
    echo "❌ Erreur lors de l'installation de FastAPI"
    exit 1
}

# Installation OpenCV
echo "🔍 Installation d'OpenCV..."
if ! pip install opencv-python; then
    echo "⚠️  Installation OpenCV via pip échouée, utilisation du package système"
    sudo apt install -y python3-opencv
fi

# Installation NumPy et Pillow
pip install numpy Pillow python-dateutil || {
    echo "❌ Erreur lors de l'installation des dépendances de base"
    exit 1
}

# Installation Picamera2 et libcamera
echo "📷 Configuration de Picamera2..."
# Picamera2 est disponible via les paquets système avec --system-site-packages
if python3 -c "import picamera2" 2>/dev/null; then
    echo "✅ Picamera2 accessible via paquets système"
else
    echo "🔧 Installation de Picamera2 via apt..."
    sudo apt install -y python3-picamera2 python3-libcamera python3-kms++
    
    # Test après installation
    if python3 -c "import picamera2" 2>/dev/null; then
        echo "✅ Picamera2 installé avec succès"
    else
        echo "❌ Problème avec Picamera2 - vérifiez après redémarrage"
    fi
fi

# Installation pylibdmtx
echo "🏷️  Installation de pylibdmtx..."
if ! pip install pylibdmtx; then
    echo "⚠️  Installation pylibdmtx échouée"
    echo "🔧 Tentative avec compilation manuelle..."
    pip install --no-binary pylibdmtx pylibdmtx || {
        echo "❌ Impossible d'installer pylibdmtx"
        echo "📋 Vérifiez que libdmtx-dev est installé"
    }
fi

# Installation pyserial
pip install pyserial || echo "⚠️  PySerial non installé (communication série désactivée)"

# Configuration des permissions
echo "🔐 Configuration des permissions..."
sudo usermod -a -G dialout $USER
sudo usermod -a -G video $USER

# Création des dossiers nécessaires
echo "📁 Création des dossiers..."
mkdir -p images logs backup

# Test rapide des imports
echo "🧪 Test des imports Python..."
source venv/bin/activate

echo -n "  FastAPI... "
python3 -c "import fastapi; print('✅')" 2>/dev/null || echo "❌"

echo -n "  OpenCV... "
python3 -c "import cv2; print('✅')" 2>/dev/null || echo "❌"

echo -n "  NumPy... "
python3 -c "import numpy; print('✅')" 2>/dev/null || echo "❌"

echo -n "  Picamera2... "
python3 -c "import picamera2; print('✅')" 2>/dev/null || echo "❌ (installer après redémarrage)"

echo -n "  pylibdmtx... "
python3 -c "import pylibdmtx; print('✅')" 2>/dev/null || echo "❌"

# Création du service systemd (si les fichiers de projet existent)
if [ -f "main.py" ] && [ -f "run.py" ]; then
    echo "⚙️  Création du service systemd..."
    sudo tee /etc/systemd/system/datamatrix-scanner.service > /dev/null <<EOF
[Unit]
Description=DataMatrix Scanner Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python run.py start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable datamatrix-scanner.service
    echo "✅ Service systemd configuré"
else
    echo "⚠️  Fichiers main.py et run.py non trouvés, service non configuré"
    echo "📋 Copiez d'abord tous les fichiers du projet dans $PROJECT_DIR"
fi

# Configuration du pare-feu (optionnel)
echo "🔥 Configuration du pare-feu..."
if command -v ufw >/dev/null 2>&1; then
    sudo ufw allow 8000/tcp
    echo "✅ Port 8000 autorisé"
else
    echo "⚠️  UFW non installé, configuration manuelle du pare-feu si nécessaire"
fi

# Affichage des informations finales
echo ""
echo "✅ Installation terminée avec succès!"
echo "========================================="
echo ""
echo "📋 Informations importantes:"
echo "- Dossier du projet: $PROJECT_DIR"
echo "- Port d'écoute: 8000"
echo "- Dossier des images: $PROJECT_DIR/images"
echo ""

if [ -f "main.py" ]; then
    echo "🚀 Pour démarrer manuellement:"
    echo "cd $PROJECT_DIR"
    echo "source venv/bin/activate"
    echo "python run.py start"
    echo ""
    echo "🚀 Pour démarrer le service:"
    echo "sudo systemctl start datamatrix-scanner"
    echo ""
    echo "🔍 Pour voir les logs:"
    echo "sudo journalctl -u datamatrix-scanner -f"
else
    echo "📋 Étapes suivantes:"
    echo "1. Copiez tous les fichiers du projet dans $PROJECT_DIR"
    echo "2. Redémarrez le Raspberry Pi"
    echo "3. Configurez le service avec 'make install-service'"
fi

echo ""
echo "🌐 Accès web (après démarrage):"
echo "http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "⚠️  IMPORTANT: Redémarrez le Raspberry Pi pour appliquer toutes les modifications:"
echo "sudo reboot"
echo ""
echo "📧 En cas de problème après redémarrage:"
echo "- Vérifiez que la caméra est bien connectée"
echo "- Testez avec: libcamera-hello --list-cameras"
echo "- Vérifiez les permissions: groups \$USER"
echo "- Consultez les logs: tail -f $PROJECT_DIR/logs/datamatrix_scanner.log"
echo ""
echo "🆘 Commandes de dépannage:"
echo "make check          # Vérification complète"
echo "make test           # Tests système"
echo "python run.py test  # Tests détaillés"