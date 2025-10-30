# Configuration du Stockage Réseau SMB pour VideoCard

Ce document décrit la mise en place du système de stockage réseau SMB avec fallback automatique pour l'application VideoCard sur Raspberry Pi.

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Architecture](#architecture)
- [Configuration initiale](#configuration-initiale)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Dépannage](#dépannage)
- [Maintenance](#maintenance)
- [FAQ](#faq)

---

## 🎯 Vue d'ensemble

### Fonctionnalités

Le système de stockage réseau offre les fonctionnalités suivantes :

- ✅ **Montage SMB/CIFS automatique** du partage réseau
- ✅ **Fallback transparent** vers le stockage local en cas d'indisponibilité réseau
- ✅ **Détection automatique** de l'état du réseau
- ✅ **Retry automatique** après plusieurs échecs consécutifs
- ✅ **API de surveillance** de l'état du stockage
- ✅ **Scripts de gestion** pour montage/démontage/vérification
- ✅ **Logs détaillés** pour le debugging

### Nouveau flux de fonctionnement

```
Capture photo
    ↓
Tentative de sauvegarde sur réseau
    ↓
Réseau OK ? ────→ OUI → Sauvegarde réseau ✓
    ↓
   NON
    ↓
Fallback automatique vers stockage local ✓
```

---

## 🏗️ Architecture

### Composants

1. **storage_manager.py** : Module Python gérant la logique de stockage
2. **mount_network.sh** : Script bash pour monter/démonter le partage SMB
3. **check_mount.sh** : Script de vérification de santé du montage
4. **.env** : Fichier de configuration
5. **main.py** : Application principale modifiée pour utiliser le storage manager

### Structure des fichiers

```
VideoCard/
├── .env                    # Configuration (à personnaliser)
├── storage_manager.py      # Gestionnaire de stockage
├── mount_network.sh        # Script de montage SMB
├── check_mount.sh          # Script de vérification
├── main.py                 # Application principale (modifiée)
├── requirements.txt        # Dépendances Python (python-dotenv ajouté)
├── NETWORK_SETUP.md        # Cette documentation
└── images/                 # Dossier de fallback local
```

---

## ⚙️ Configuration initiale

### 1. Configuration du partage réseau

Éditez le fichier `.env` à la racine du projet :

```bash
nano .env
```

Configurez les paramètres suivants :

```ini
# Configuration du partage SMB
SMB_HOST=192.168.111.37           # Adresse IP du serveur SMB
SMB_SHARE=sharetest               # Nom du partage
SMB_PATH=//192.168.111.37/sharetest

# Point de montage local
MOUNT_POINT=/mnt/sharetest

# Credentials (laisser vide si pas d'authentification)
SMB_USERNAME=                     # Nom d'utilisateur (optionnel)
SMB_PASSWORD=                     # Mot de passe (optionnel)

# Dossier de fallback local
LOCAL_FALLBACK_DIR=images

# Options de montage SMB
SMB_MOUNT_OPTIONS=vers=3.0,rw,uid=1000,gid=1000,file_mode=0777,dir_mode=0777

# Activer/désactiver le stockage réseau
NETWORK_STORAGE_ENABLED=true

# Timeout pour les opérations réseau (secondes)
NETWORK_TIMEOUT=5

# Activer les logs détaillés
STORAGE_DEBUG=true
```

### 2. Personnalisation des paramètres

#### SMB_HOST et SMB_SHARE
- **SMB_HOST** : L'adresse IP de votre serveur de partage SMB
- **SMB_SHARE** : Le nom du partage sur le serveur
- **SMB_PATH** : Le chemin complet (format UNC : `//IP/partage`)

#### MOUNT_POINT
Point de montage local où sera accessible le partage réseau.
Par défaut : `/mnt/sharetest`

#### Credentials
- Laisser **vide** pour un montage guest (sans authentification)
- Remplir **SMB_USERNAME** et **SMB_PASSWORD** si le partage nécessite une authentification

#### Options de montage
Les options recommandées pour Raspberry Pi :
- `vers=3.0` : Force SMB version 3.0
- `rw` : Lecture/écriture
- `uid=1000,gid=1000` : Permissions utilisateur (ajuster selon votre utilisateur)
- `file_mode=0777,dir_mode=0777` : Permissions complètes (ajuster selon vos besoins de sécurité)

---

## 📦 Installation

### Étape 1 : Installer les dépendances système

```bash
# Installer cifs-utils pour le support SMB
sudo apt-get update
sudo apt-get install -y cifs-utils

# (Optionnel) Installer libnotify pour les notifications
sudo apt-get install -y libnotify-bin
```

### Étape 2 : Installer les dépendances Python

```bash
# Dans le dossier VideoCard
pip install -r requirements.txt
```

Ou spécifiquement :

```bash
pip install python-dotenv==1.0.0
```

### Étape 3 : Rendre les scripts exécutables

```bash
chmod +x mount_network.sh
chmod +x check_mount.sh
```

### Étape 4 : Tester le montage réseau

```bash
# Vérifier la configuration
./mount_network.sh status

# Monter le partage
./mount_network.sh mount

# Vérifier que le montage a réussi
./mount_network.sh status
```

### Étape 5 : Vérifier le fonctionnement

```bash
# Test de santé complet
./check_mount.sh

# Avec sortie JSON
./check_mount.sh --json
```

---

## 🚀 Utilisation

### Montage manuel du partage

```bash
# Monter le partage réseau
./mount_network.sh mount

# Vérifier l'état
./mount_network.sh status

# Démonter le partage
./mount_network.sh unmount

# Remonter le partage (démontage + montage)
./mount_network.sh remount
```

### Vérification de santé

```bash
# Vérification simple
./check_mount.sh

# Vérification avec remontage automatique si nécessaire
./check_mount.sh --auto-remount

# Sortie JSON pour intégration
./check_mount.sh --json

# Avec notifications système
./check_mount.sh --auto-remount --notify
```

### Montage automatique au démarrage

Pour monter automatiquement le partage au démarrage du Raspberry Pi :

#### Option 1 : Service systemd (recommandé)

Créez le fichier `/etc/systemd/system/videocard-mount.service` :

```ini
[Unit]
Description=VideoCard SMB Mount
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root
WorkingDirectory=/home/pi/VideoCard
ExecStart=/home/pi/VideoCard/mount_network.sh mount
RemainAfterExit=yes
StandardOutput=journal

[Install]
WantedBy=multi-user.target
```

Activez le service :

```bash
sudo systemctl daemon-reload
sudo systemctl enable videocard-mount.service
sudo systemctl start videocard-mount.service

# Vérifier le statut
sudo systemctl status videocard-mount.service
```

#### Option 2 : /etc/fstab

Ajoutez une ligne dans `/etc/fstab` :

```bash
//192.168.111.37/sharetest /mnt/sharetest cifs vers=3.0,rw,uid=1000,gid=1000,file_mode=0777,dir_mode=0777,guest 0 0
```

Puis :

```bash
sudo mount -a
```

> **Note** : Cette méthode nécessite que le réseau soit disponible avant le montage

#### Option 3 : Cron @reboot

Ajoutez dans le crontab :

```bash
crontab -e
```

Ajoutez la ligne :

```
@reboot sleep 30 && /home/pi/VideoCard/mount_network.sh mount >> /var/log/videocard_mount.log 2>&1
```

### Surveillance automatique (Cron)

Pour vérifier automatiquement l'état du montage et le remonter si nécessaire :

```bash
crontab -e
```

Ajoutez :

```bash
# Vérification toutes les 5 minutes avec remontage automatique
*/5 * * * * /home/pi/VideoCard/check_mount.sh --auto-remount >> /var/log/videocard_health.log 2>&1

# Nettoyage des logs tous les lundis à 2h du matin
0 2 * * 1 echo "" > /var/log/videocard_health.log
```

### API de surveillance

L'application expose maintenant des endpoints API pour surveiller le stockage :

#### Obtenir le statut du stockage

```bash
curl http://localhost:8000/api/storage/status
```

Réponse :

```json
{
  "network_enabled": true,
  "network_available": true,
  "mount_point": "/mnt/sharetest",
  "fallback_dir": "images",
  "consecutive_failures": 0,
  "using_fallback": false,
  "current_storage": "/mnt/sharetest"
}
```

#### Réinitialiser le compteur d'échecs

Pour forcer une nouvelle tentative réseau après plusieurs échecs :

```bash
curl -X POST http://localhost:8000/api/storage/reset
```

#### Obtenir une image depuis n'importe quel emplacement

L'application cherche automatiquement dans réseau + local :

```bash
curl http://localhost:8000/api/image/20231025_143022.jpg
```

---

## 🔧 Dépannage

### Problème : Le partage ne se monte pas

**Symptômes :**
```bash
./mount_network.sh mount
# Erreur: ✗ Échec du montage
```

**Solutions :**

1. **Vérifier la connectivité réseau**
   ```bash
   ping 192.168.111.37
   ```

2. **Vérifier que cifs-utils est installé**
   ```bash
   dpkg -l | grep cifs-utils
   ```

3. **Vérifier les credentials**
   - Si le partage nécessite une authentification, vérifiez `SMB_USERNAME` et `SMB_PASSWORD` dans `.env`

4. **Tester avec smbclient**
   ```bash
   smbclient -L //192.168.111.37 -N
   ```

5. **Vérifier les permissions du serveur SMB**
   - Assurez-vous que le partage autorise l'écriture
   - Vérifiez les permissions sur le serveur

### Problème : Impossible d'écrire sur le partage

**Symptômes :**
- Le montage réussit mais l'écriture échoue

**Solutions :**

1. **Vérifier les permissions du montage**
   ```bash
   ls -la /mnt/sharetest
   ```

2. **Ajuster les options de montage dans .env**
   ```ini
   SMB_MOUNT_OPTIONS=vers=3.0,rw,uid=1000,gid=1000,file_mode=0777,dir_mode=0777
   ```

3. **Vérifier l'espace disque disponible**
   ```bash
   df -h /mnt/sharetest
   ```

### Problème : L'application utilise toujours le fallback local

**Symptômes :**
- Les images sont toujours sauvegardées dans `images/` au lieu du réseau

**Solutions :**

1. **Vérifier que le réseau est activé dans .env**
   ```ini
   NETWORK_STORAGE_ENABLED=true
   ```

2. **Vérifier le statut du stockage via l'API**
   ```bash
   curl http://localhost:8000/api/storage/status
   ```

3. **Réinitialiser le compteur d'échecs**
   ```bash
   curl -X POST http://localhost:8000/api/storage/reset
   ```

4. **Vérifier les logs de l'application**
   ```bash
   journalctl -u videocard -f
   ```

### Problème : Montage qui disparaît après un moment

**Symptômes :**
- Le montage fonctionne au début puis devient inaccessible

**Solutions :**

1. **Configurer la surveillance automatique (cron)**
   Voir section [Surveillance automatique](#surveillance-automatique-cron)

2. **Vérifier les timeouts réseau**
   Augmenter `NETWORK_TIMEOUT` dans `.env`

3. **Ajouter l'option nobrl au montage**
   ```ini
   SMB_MOUNT_OPTIONS=vers=3.0,rw,uid=1000,gid=1000,nobrl
   ```

### Problème : Les anciennes images ne s'affichent pas

**Symptômes :**
- La galerie ne montre pas toutes les images

**Solutions :**

1. **Les images sont réparties entre réseau et local**
   - Le storage manager liste automatiquement les deux emplacements
   - Vérifier manuellement :
     ```bash
     ls -lh images/
     ls -lh /mnt/sharetest/
     ```

2. **Forcer une nouvelle vérification**
   - Redémarrer l'application
   - Ou utiliser `/api/storage/reset`

---

## 🔄 Maintenance

### Logs

#### Application principale
```bash
# Si lancée via systemd
journalctl -u videocard -f

# Logs du storage manager (si STORAGE_DEBUG=true)
journalctl -u videocard | grep storage_manager
```

#### Scripts de montage
```bash
# Logs de surveillance (si configuré en cron)
tail -f /var/log/videocard_health.log
tail -f /var/log/videocard_mount.log
```

### Nettoyage

#### Nettoyer les anciennes images

```bash
# Supprimer les images de plus de 30 jours sur le réseau
find /mnt/sharetest -name "*.jpg" -mtime +30 -delete

# Supprimer les images de plus de 30 jours en local
find images/ -name "*.jpg" -mtime +30 -delete
```

#### Synchroniser réseau et local

Si vous voulez copier toutes les images locales vers le réseau :

```bash
rsync -av --progress images/ /mnt/sharetest/
```

Ou l'inverse (réseau vers local) :

```bash
rsync -av --progress /mnt/sharetest/ images/
```

### Sauvegarde

Il est recommandé de sauvegarder régulièrement :

```bash
# Sauvegarde des images
tar -czf videocard_images_$(date +%Y%m%d).tar.gz /mnt/sharetest/

# Sauvegarde de la configuration
tar -czf videocard_config_$(date +%Y%m%d).tar.gz .env storage_manager.py *.sh
```

---

## ❓ FAQ

### Q1 : Puis-je utiliser un autre protocole que SMB ?

**R :** Actuellement, seul SMB/CIFS est supporté. Pour NFS ou d'autres protocoles, il faudrait adapter les scripts `mount_network.sh` et les options dans `.env`.

### Q2 : Que se passe-t-il si le réseau tombe pendant une capture ?

**R :** Le storage manager basculera automatiquement sur le fallback local. L'image sera sauvegardée dans `images/` sans interruption de service.

### Q3 : Comment désactiver complètement le stockage réseau ?

**R :** Dans `.env`, définissez :
```ini
NETWORK_STORAGE_ENABLED=false
```

L'application utilisera alors uniquement le stockage local.

### Q4 : Puis-je utiliser plusieurs partages réseau ?

**R :** Non, la configuration actuelle ne supporte qu'un seul partage réseau. Pour plusieurs partages, il faudrait étendre le storage manager.

### Q5 : Les anciennes images locales seront-elles automatiquement transférées sur le réseau ?

**R :** Non, le système ne transfère pas automatiquement les anciennes images. Vous pouvez les synchroniser manuellement avec `rsync` (voir section Maintenance).

### Q6 : Le système fonctionne-t-il avec un NAS Synology/QNAP ?

**R :** Oui, tant que le NAS expose un partage SMB/CIFS compatible (SMB v2.0 ou supérieur).

### Q7 : Comment augmenter la sécurité des credentials ?

**R :** Pour éviter de stocker le mot de passe en clair dans `.env`, vous pouvez :

1. Utiliser un fichier de credentials séparé :
   ```bash
   # Créer /etc/videocard-creds
   username=monuser
   password=monmotdepasse

   # Sécuriser le fichier
   sudo chmod 600 /etc/videocard-creds
   sudo chown root:root /etc/videocard-creds
   ```

2. Modifier les options de montage dans `.env` :
   ```ini
   SMB_MOUNT_OPTIONS=vers=3.0,rw,credentials=/etc/videocard-creds,uid=1000,gid=1000
   ```

### Q8 : Combien d'échecs avant de basculer définitivement en local ?

**R :** Par défaut, après **3 échecs consécutifs**, le système reste en mode local temporaire. Vous pouvez forcer une nouvelle tentative réseau avec :
```bash
curl -X POST http://localhost:8000/api/storage/reset
```

### Q9 : Puis-je voir l'état du stockage dans l'interface web ?

**R :** Oui, vous pouvez intégrer l'endpoint `/api/storage/status` dans votre interface web pour afficher l'état en temps réel.

### Q10 : Les performances sont-elles impactées par le stockage réseau ?

**R :** L'impact est minimal grâce à :
- Sauvegarde asynchrone (non bloquante)
- Cache de vérification réseau (60 secondes)
- Timeout rapide en cas d'indisponibilité (5 secondes par défaut)

---

## 📝 Notes techniques

### Modifications du code

Les principaux changements dans l'application :

1. **main.py** :
   - Import de `storage_manager`
   - Modification de `capture_photo()` pour utiliser `storage_manager.save_file()`
   - Modification de `get_latest_images()` pour lister depuis tous les emplacements
   - Ajout de routes API : `/api/storage/status` et `/api/storage/reset`
   - Ajout de route `/api/image/{filename}` pour servir les images depuis n'importe où

2. **storage_manager.py** (nouveau) :
   - Classe `StorageManager` gérant la logique de stockage
   - Détection automatique du réseau
   - Fallback transparent
   - Gestion des échecs consécutifs

3. **requirements.txt** :
   - Ajout de `python-dotenv==1.0.0`

### Compatibilité

- ✅ Raspberry Pi OS (Debian-based)
- ✅ Python 3.7+
- ✅ SMB v2.0+
- ✅ Compatible avec NAS (Synology, QNAP, etc.)

---

## 🆘 Support

Pour toute question ou problème :

1. Vérifiez d'abord la section [Dépannage](#dépannage)
2. Consultez les logs de l'application
3. Testez les scripts individuellement
4. Ouvrez une issue sur le dépôt GitHub

---

## 📄 Licence

Ce système de stockage réseau fait partie du projet VideoCard.

---

**Dernière mise à jour** : 2025-10-30
**Version** : 1.0.0
