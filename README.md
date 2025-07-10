# 📷 DataMatrix Scanner

Application web complète pour la capture d'images et la détection de codes DataMatrix sur Raspberry Pi 5 avec caméra OV64A40.

## 🎯 Fonctionnalités

### Backend (FastAPI)
- ✅ Serveur FastAPI avec routes optimisées
- ✅ Flux vidéo MJPEG temps réel (`/video_feed`)
- ✅ WebSocket pour contrôle à distance (`/ws`)
- ✅ Gestion asynchrone de la caméra Picamera2
- ✅ Capture photo haute résolution (4656x3496)
- ✅ Autofocus continu (8 secondes)
- ✅ Zoom interactif par clic sur le flux vidéo
- ✅ Décodage automatique des codes DataMatrix
- ✅ Extraction intelligente des labels blancs
- ✅ Communication série optionnelle
- ✅ Sauvegarde automatique des images

### Frontend (Bootstrap 5)
- ✅ Interface responsive et moderne
- ✅ Flux vidéo en temps réel
- ✅ Galerie des 3 dernières captures
- ✅ Boutons de contrôle intuitifs
- ✅ Indicateurs de statut en temps réel
- ✅ Gestion des erreurs et reconnexion automatique
- ✅ Modal d'aperçu des images
- ✅ Animations et effets visuels

### Traitement d'image
- ✅ Détection automatique des labels blancs
- ✅ Seuillage adaptatif optimisé
- ✅ Tentatives de décodage avec rotations (0°/90°/180°/270°)
- ✅ Morphologie mathématique pour nettoyage
- ✅ Sauvegarde des étapes de debug
- ✅ Gestion robuste des erreurs

## 🛠️ Installation

### Prérequis
- Raspberry Pi 5
- Caméra OV64A40 (ou compatible Picamera2)
- Raspbian OS 64-bit
- Python 3.9+

### Installation automatique

```bash
# Clonage du projet
git clone <repository-url>
cd datamatrix_scanner

# Copie des fichiers de configuration
cp requirements.txt .
cp install.sh .

# Rendre le script exécutable
chmod +x install.sh

# Lancement de l'installation
./install.sh
```

### Installation manuelle

```bash
# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Installation des dépendances système
sudo apt install -y python3-pip python3-venv python3-dev build-essential \
    cmake pkg-config libzbar-dev libdmtx-dev libopencv-dev python3-opencv \
    libatlas-base-dev libhdf5-dev libcamera-dev libcamera-apps git

# Activation de la caméra
sudo raspi-config nonint do_camera 0

# Création de l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installation des dépendances Python
pip install -r requirements.txt

# Configuration des permissions
sudo usermod -a -G dialout,video $USER

# Redémarrage (important!)
sudo reboot
```

## 🚀 Utilisation

### Démarrage rapide

```bash
# Activation de l'environnement virtuel
source venv/bin/activate

# Lancement du serveur
python run.py start
```

### Modes de fonctionnement

```bash
# Mode production (par défaut)
python run.py start

# Mode développement (rechargement auto)
python run.py dev

# Tests système
python run.py test

# Statut du système
python run.py status

# Nettoyage des anciens fichiers
python run.py clean
```

### Options avancées

```bash
# Personnalisation de l'adresse et du port
python run.py start --host 192.168.1.100 --port 8080

# Mode debug
python run.py start --debug

# Aide
python run.py --help
```

## 🌐 Interface Web

Une fois le serveur démarré, accédez à l'interface via :
- **Local** : http://localhost:8000
- **Réseau** : http://[IP_DU_RASPBERRY]:8000

### Utilisation de l'interface

1. **Flux vidéo** : Visualisation temps réel de la caméra
2. **Zoom** : Cliquez sur le flux pour zoomer à un point précis
3. **Capture** : Bouton 📸 pour prendre une photo haute résolution
4. **Focus** : Bouton 🔍 pour déclencher l'autofocus
5. **Reset Zoom** : Bouton 🔘 pour revenir au zoom 1x
6. **Signal série** : Bouton ⚡ pour envoyer un signal série
7. **Galerie** : Visualisation des 3 dernières captures
8. **Statut** : Messages en temps réel et indicateurs de connexion

## 📁 Structure du projet

```
datamatrix_scanner/
├── main.py              # Serveur FastAPI principal
├── config.py            # Configuration de l'application
├── run.py               # Script de lancement
├── index.html           # Interface utilisateur
├── requirements.txt     # Dépendances Python
├── install.sh          # Script d'installation
├── README.md           # Documentation
├── images/             # Dossier des captures
├── logs/               # Journaux d'activité
└── venv/               # Environnement virtuel
```

## ⚙️ Configuration

### Fichier `config.py`

Personnalisez les paramètres dans `config.py` :

```python
# Résolutions de caméra
CAMERA_CONFIG = {
    "stream_resolution": (640, 480),      # Flux vidéo
    "capture_resolution": (4656, 3496),   # Photos HD
    "preview_resolution": (1280, 720),    # Prévisualisation
}

# Traitement d'image
IMAGE_PROCESSING = {
    "white_threshold": 200,               # Seuil de blanc
    "min_contour_area": 1000,             # Surface mini contour
    "rotation_angles": [0, 90, 180, 270], # Rotations à tester
}

# Communication série
SERIAL_CONFIG = {
    "port": "/dev/ttyUSB0",
    "baudrate": 9600,
    "signal_byte": b'\x01',
}
```

### Variables d'environnement

```bash
# Mode de fonctionnement
export DATAMATRIX_ENV=production  # ou development, test

# Configuration personnalisée
export DATAMATRIX_HOST=0.0.0.0
export DATAMATRIX_PORT=8000
```

## 🔧 API WebSocket

### Messages supportés

```javascript
// Capture d'image
ws.send("capture");

// Autofocus
ws.send("focus");

// Zoom sur un point (coordonnées relatives 0-1)
ws.send(JSON.stringify({
    "zoomTo": [0.5, 0.3]  // x=50%, y=30%
}));

// Reset du zoom
ws.send(JSON.stringify({
    "resetZoom": true
}));

// Signal série
ws.send(JSON.stringify({
    "serial": true
}));
```

### Réponses WebSocket

```javascript
// Statut
{
    "type": "status",
    "message": "Capture en cours..."
}

// Résultat de capture
{
    "type": "capture_result",
    "photo_path": "/images/20250704_143022.jpg",
    "datamatrix": "ABC123XYZ",
    "latest_images": [...],
    "timestamp": "2025-07-04T14:30:22"
}

// Erreur
{
    "type": "error",
    "message": "Erreur de capture"
}
```

## 🐛 Dépannage

### Problèmes courants

**1. Caméra non détectée**
```bash
# Vérifier l'activation
sudo raspi-config nonint do_camera 0

# Vérifier la détection
libcamera-hello --list-cameras

# Redémarrer si nécessaire
sudo reboot
```

**2. Permissions insuffisantes**
```bash
# Ajouter aux groupes nécessaires
sudo usermod -a -G video,dialout $USER

# Se reconnecter ou redémarrer
sudo reboot
```

**3. Dépendances manquantes**
```bash
# Réinstaller les dépendances
pip install -r requirements.txt --force-reinstall

# Vérifier les paquets système
sudo apt install --reinstall python3-opencv libdmtx-dev
```

**4. Erreurs de décodage DataMatrix**
- Vérifiez l'éclairage (lumière uniforme)
- Assurez-vous que le code est net et lisible
- Testez avec différents angles de capture
- Vérifiez les fichiers debug générés (`*_debug.jpg`)

### Logs et diagnostics

```bash
# Affichage des logs en temps réel
tail -f logs/datamatrix_scanner.log

# Tests système complets
python run.py test

# Statut détaillé
python run.py status

# Logs du service systemd
sudo journalctl -u datamatrix-scanner -f
```

### Performance

**Optimisations recommandées :**

1. **GPU** : Activez l'accélération GPU si disponible
```bash
sudo raspi-config nonint do_memory_split 128
```

2. **Swap** : Augmentez le swap pour les gros traitements
```bash
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=512/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

3. **Réseau** : Utilisez une connexion Ethernet pour de meilleures performances

## 🔒 Service système

### Installation du service

Le script d'installation crée automatiquement un service systemd :

```bash
# Démarrage automatique
sudo systemctl enable datamatrix-scanner

# Contrôle du service
sudo systemctl start datamatrix-scanner
sudo systemctl stop datamatrix-scanner
sudo systemctl restart datamatrix-scanner

# Statut
sudo systemctl status datamatrix-scanner
```

### Configuration du service

Fichier : `/etc/systemd/system/datamatrix-scanner.service`

```ini
[Unit]
Description=DataMatrix Scanner Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/datamatrix_scanner
Environment=PATH=/home/pi/datamatrix_scanner/venv/bin
ExecStart=/home/pi/datamatrix_scanner/venv/bin/python run.py start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 📊 Monitoring

### Métriques système

L'application expose des informations de monitoring :

- **Santé** : Statut de la caméra et des services
- **Performance** : FPS du flux vidéo, temps de traitement
- **Stockage** : Espace disque, nombre d'images
- **Réseau** : Connexions WebSocket actives

### Surveillance recommandée

1. **Température CPU** : Évitez la surchauffe
```bash
vcgencmd measure_temp
```

2. **Mémoire** : Surveillez l'utilisation RAM
```bash
free -h
```

3. **Espace disque** : Nettoyage automatique configuré
```bash
df -h
```

## 🤝 Contribution

### Structure de développement

```bash
# Mode développement
python run.py dev

# Tests
python run.py test

# Lint (si installé)
flake8 *.py
black *.py
```

### Ajout de fonctionnalités

1. Fork du projet
2. Création d'une branche feature
3. Développement avec tests
4. Pull request avec description détaillée

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

---

**Note** : Ce projet est optimisé pour Raspberry Pi 5 avec caméra OV64A40. D'autres configurations peuvent nécessiter des ajustements dans `config.py`.