# 📷 DataMatrix Scanner v2.0

Application web avancée pour la capture d'images et la détection de codes DataMatrix sur Raspberry Pi 5 avec caméra OV64A40. Cette version 2.0 inclut un système de paramétrage flexible avec modes DataMatrix/Lot et détection Automatique/Manuel.

## 🎯 Nouvelles fonctionnalités v2.0

### Système de paramétrage complet
- ✅ **Page de configuration** : Interface intuitive pour paramétrer l'application
- ✅ **Mode DataMatrix** : Scan d'une seule carte avec décodage automatique
- ✅ **Mode Lot** : Capture photo uniquement sans décodage DataMatrix
- ✅ **Détection automatique** : Utilise l'algorithme de détection existant
- ✅ **Détection manuelle** : Saisie manuelle de l'OF (référence carte)
- ✅ **Contrôle d'éclairage** : LEDs blanches (0x01) ou lampe UV (0x02)
- ✅ **Navigation fluide** : Passage entre configuration et application

### Backend amélioré (FastAPI)
- ✅ **Nouvelle architecture** : Page paramètres (`/`) et application (`/app`)
- ✅ **API REST** : Sauvegarde/chargement des paramètres via `/api/settings`
- ✅ **Contrôle série avancé** : Signaux personnalisés pour éclairage
- ✅ **Nommage intelligent** : Fichiers avec OF manuel si configuré
- ✅ **Gestion contextuelle** : Comportement adapté selon les paramètres

### Frontend modernisé
- ✅ **Interface responsive** : Design moderne avec gradients et animations
- ✅ **Configuration visuelle** : Boutons interactifs pour tous les paramètres
- ✅ **Indicateurs de statut** : Affichage de la configuration active
- ✅ **Test d'éclairage** : Boutons pour tester LEDs et UV
- ✅ **Retour visuel** : Messages de statut et animations fluides

## 🛠️ Installation

### Prérequis
- Raspberry Pi 5
- Caméra OV64A40 (ou compatible Picamera2)
- Arduino Nano pour contrôle d'éclairage
- Raspbian OS 64-bit
- Python 3.9+

### Installation automatique avec Makefile

```bash
# Clonage du projet
git clone <repository-url>
cd datamatrix_scanner

# Installation complète
make setup
make install-deps

# Vérification du système
make check

# Démarrage
make start
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
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Installation des dépendances Python
pip install -r requirements.txt

# Configuration des permissions
sudo usermod -a -G dialout,video $USER

# Redémarrage (important!)
sudo reboot
```

## 🚀 Utilisation

### Démarrage rapide avec Makefile

```bash
# Démarrage en production
make start

# Mode développement
make dev

# Tests système complets
make test

# Statut du système
make status

# Nettoyage
make clean
```

### Modes de fonctionnement

```bash
# Mode production
python run.py start

# Mode développement avec rechargement auto
python run.py dev

# Tests et diagnostics
python run.py test

# Affichage du statut
python run.py status

# Nettoyage des anciens fichiers
python run.py clean
```

### Configuration avancée

```bash
# Personnalisation de l'adresse et du port
python run.py start --host 192.168.1.100 --port 8080

# Mode debug
python run.py start --debug

# Aide complète
python run.py --help
```

## 🌐 Interface Web v2.0

### Page de Configuration (`/`)
Une fois le serveur démarré, accédez à la configuration via :
- **Local** : http://localhost:8000
- **Réseau** : http://[IP_DU_RASPBERRY]:8000

#### Paramètres disponibles :

1. **Mode de scan**
   - **DataMatrix** : Scan d'une seule carte avec décodage automatique
   - **Lot** : Capture photo uniquement, pas de décodage

2. **Mode de détection**
   - **Automatique** : Utilise l'algorithme de détection de labels blancs
   - **Manuel** : Permet de saisir manuellement l'OF de la carte

3. **Mode d'éclairage**
   - **Blanc** : Active les LEDs blanches via signal série 0x01
   - **UV** : Active la lampe UV via signal série 0x02

4. **Test d'éclairage** : Boutons pour tester chaque type d'éclairage

### Page Application (`/app`)
Interface principale de capture avec :

1. **Flux vidéo temps réel** : Prévisualisation 1280x720
2. **Contrôles adaptatifs** : Boutons qui changent selon la configuration
3. **Galerie intelligente** : Affichage des 3 dernières captures
4. **Statut en temps réel** : Messages et indicateurs de fonctionnement
5. **Zoom interactif** : Clic sur le flux pour zoomer
6. **Paramètres visibles** : Affichage de la configuration active

## 📁 Structure du projet v2.0

```
datamatrix_scanner/
├── main.py              # Serveur FastAPI avec nouvelles routes
├── config.py            # Configuration de l'application
├── run.py               # Script de lancement amélioré
├── settings.html        # Page de paramétrage (nouvelle)
├── app.html            # Interface principale (ex-index.html)
├── requirements.txt     # Dépendances Python
├── install.sh          # Script d'installation
├── Makefile            # Commandes automatisées
├── README.md           # Documentation complète
├── images/             # Dossier des captures
├── logs/               # Journaux d'activité
├── test/               # Scripts de test
├── backup/             # Sauvegardes automatiques
└── venv/               # Environnement virtuel
```

## ⚙️ Configuration v2.0

### Paramètres par défaut
```python
app_settings = {
    "scan_mode": "datamatrix",      # "datamatrix" ou "lot"
    "detection_mode": "automatique", # "automatique" ou "manuel"
    "lighting_mode": "blanc",       # "blanc" ou "uv"
    "manual_of": ""                 # OF manuel si mode manuel
}
```

### Configuration série
```python
SERIAL_SIGNALS = {
    "leds_blanches": b'\x01',  # Signal pour LEDs blanches
    "lampe_uv": b'\x02',       # Signal pour lampe UV
    "signal_generique": b'\x01' # Signal par défaut
}
```

### Variables d'environnement
```bash
export DATAMATRIX_ENV=production    # ou development, test
export DATAMATRIX_HOST=0.0.0.0
export DATAMATRIX_PORT=8000
```

## 🔧 API v2.0

### Nouvelles routes

#### Configuration
```javascript
// Récupérer les paramètres actuels
GET /api/settings

// Mettre à jour les paramètres
POST /api/settings
Content-Type: application/x-www-form-urlencoded
{
    scan_mode: "datamatrix|lot",
    detection_mode: "automatique|manuel", 
    lighting_mode: "blanc|uv",
    manual_of: "string"
}

// Test d'éclairage
POST /api/test-lighting
Content-Type: application/json
{
    "lighting_type": "blanc|uv"
}
```

#### WebSocket étendu
```javascript
// Contrôle d'éclairage spécifique
ws.send(JSON.stringify({
    "lighting": "blanc"  // ou "uv"
}));

// Zoom sur un point (inchangé)
ws.send(JSON.stringify({
    "zoomTo": [0.5, 0.3]
}));

// Capture (comportement adapté selon les paramètres)
ws.send("capture");

// Autofocus (inchangé)
ws.send("focus");
```

#### Réponses adaptées
```javascript
// Résultat de capture avec contexte
{
    "type": "capture_result",
    "photo_path": "/images/20250710_143022_AE-F22050360-00B.jpg",
    "datamatrix": "AE-F22050360-00B",  // ou manuel ou null
    "latest_images": [...],
    "timestamp": "2025-07-10T14:30:22",
    "scan_mode": "datamatrix",
    "detection_mode": "automatique"
}
```

## 🔌 Intégration Arduino

### Code Arduino pour contrôle d'éclairage
```cpp
// Code suggéré pour Arduino Nano
void setup() {
    Serial.begin(9600);
    pinMode(LED_BLANC_PIN, OUTPUT);
    pinMode(LED_UV_PIN, OUTPUT);
}

void loop() {
    if (Serial.available()) {
        byte signal = Serial.read();
        
        switch(signal) {
            case 0x01:  // LEDs blanches
                digitalWrite(LED_BLANC_PIN, HIGH);
                digitalWrite(LED_UV_PIN, LOW);
                break;
                
            case 0x02:  // Lampe UV
                digitalWrite(LED_BLANC_PIN, LOW);
                digitalWrite(LED_UV_PIN, HIGH);
                break;
                
            default:
                // Signal inconnu
                break;
        }
    }
}
```

## 🐛 Dépannage v2.0

### Commandes Makefile utiles

```bash
# Diagnostic complet
make check

# Vérification de la caméra
make fix-camera

# Réparation des permissions
make fix-permissions

# Recréation de l'environnement
make recreate-venv

# Logs en temps réel
make logs

# Sauvegarde complète
make backup

# Restauration
make restore
```

### Problèmes courants

**1. Page de paramètres inaccessible**
```bash
# Vérifier que settings.html existe
ls -la settings.html

# Vérifier les routes
curl http://localhost:8000/
curl http://localhost:8000/app
```

**2. Signaux série non envoyés**
```bash
# Vérifier la connexion série
ls -la /dev/ttyUSB* /dev/ttyACM*

# Tester manuellement
echo -e '\x01' > /dev/ttyUSB0  # LEDs blanches
echo -e '\x02' > /dev/ttyUSB0  # Lampe UV
```

**3. Paramètres non sauvegardés**
```bash
# Vérifier les logs API
tail -f logs/datamatrix_scanner.log | grep settings

# Test API direct
curl -X POST http://localhost:8000/api/settings \
  -d "scan_mode=datamatrix&detection_mode=automatique&lighting_mode=blanc"
```

**4. Navigation entre pages**
- `/` → Page de paramétrage (nouvelle page d'accueil)
- `/app` → Application principale de scan
- Bouton "Paramètres" dans `/app` → retour vers `/`
- Bouton "Valider" dans `/` → redirection vers `/app`

### Logs et diagnostics

```bash
# Makefile - logs en temps réel
make logs

# Logs du service systemd
sudo journalctl -u datamatrix-scanner -f

# Tests système complets
make test
python run.py test

# Statut détaillé avec Makefile
make status
make ping
make config
```

## 🔒 Service système v2.0

### Installation et gestion
```bash
# Installation du service (via Makefile)
make install-service

# Contrôle manuel
sudo systemctl start datamatrix-scanner
sudo systemctl stop datamatrix-scanner
sudo systemctl restart datamatrix-scanner
sudo systemctl status datamatrix-scanner

# Démarrage automatique
sudo systemctl enable datamatrix-scanner
```

### Configuration du service
```ini
[Unit]
Description=DataMatrix Scanner v2.0 Service
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

## 📊 Monitoring et Performance

### Métriques système v2.0
- **Performance caméra** : FPS optimisé avec thread en arrière-plan
- **Mémoire** : Buffer intelligent de frames
- **Configuration** : Sauvegarde persistante des paramètres
- **Éclairage** : Contrôle Arduino via signaux série

### Surveillance recommandée
```bash
# Makefile - statut global
make status

# Température et performance
vcgencmd measure_temp
free -h
df -h

# Activité réseau
netstat -tlnp | grep :8000
```

## 🆕 Nouveautés v2.0

### Architecture
- ✅ **Séparation claire** : Configuration (`/`) et Application (`/app`)
- ✅ **API REST complète** : Gestion des paramètres via `/api/settings`
- ✅ **Persistence** : Sauvegarde automatique de la configuration
- ✅ **Navigation fluide** : Boutons de navigation entre les pages

### Interface utilisateur
- ✅ **Design moderne** : Gradients, animations, effets visuels
- ✅ **Configuration intuitive** : Boutons interactifs pour tous les paramètres
- ✅ **Feedback visuel** : Indicateurs de statut et messages contextuels
- ✅ **Responsive design** : Adaptation mobile et desktop

### Fonctionnalités
- ✅ **Modes flexibles** : DataMatrix/Lot et Automatique/Manuel
- ✅ **Éclairage intelligent** : Contrôle LEDs blanches et UV
- ✅ **Nommage automatique** : Fichiers avec OF si mode manuel
- ✅ **Test d'éclairage** : Validation du matériel directement depuis l'interface

## 🤝 Migration depuis v1.0

### Changements importants
1. **URL principale** : `/` → Page de paramétrage (nouveau)
2. **URL application** : `/app` → Interface de scan (ancien `/`)
3. **Nouveaux fichiers** : `settings.html`, `app.html` (remplace `index.html`)
4. **API étendue** : Nouvelles routes `/api/settings` et `/api/test-lighting`
5. **Signaux série** : Support 0x01 (blanc) et 0x02 (UV)

### Migration automatique
```bash
# Sauvegarde de v1.0
make backup

# Mise à jour vers v2.0
git pull origin main

# Installation des nouvelles dépendances
make setup

# Test de la nouvelle version
make test
```

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

---

**DataMatrix Scanner v2.0** - Système complet de capture et analyse avec interface de paramétrage avancée, optimisé pour Raspberry Pi 5 avec caméra OV64A40 et contrôle d'éclairage Arduino.