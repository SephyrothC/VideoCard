#!/bin/bash
###############################################################################
# Script de montage du partage réseau SMB pour VideoCard
#
# Ce script monte le partage réseau SMB configuré dans .env
# Peut être appelé manuellement ou configuré pour s'exécuter au démarrage
#
# Usage:
#   ./mount_network.sh              # Monter le partage
#   ./mount_network.sh unmount      # Démonter le partage
#   ./mount_network.sh remount      # Démonter puis remonter
#   ./mount_network.sh status       # Vérifier l'état du montage
###############################################################################

set -e  # Arrêter en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour charger les variables du .env
load_env() {
    if [ ! -f .env ]; then
        echo -e "${RED}Erreur: Fichier .env introuvable${NC}"
        echo "Assurez-vous que .env existe dans le dossier du script"
        exit 1
    fi

    # Charger les variables (en ignorant les commentaires et lignes vides)
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
}

# Fonction pour vérifier si un paquet est installé
check_package() {
    if ! dpkg -l | grep -q "^ii  $1"; then
        echo -e "${YELLOW}Package $1 n'est pas installé${NC}"
        return 1
    fi
    return 0
}

# Fonction pour installer cifs-utils si nécessaire
install_cifs() {
    if ! check_package cifs-utils; then
        echo -e "${BLUE}Installation de cifs-utils...${NC}"
        sudo apt-get update
        sudo apt-get install -y cifs-utils
        echo -e "${GREEN}cifs-utils installé avec succès${NC}"
    fi
}

# Fonction pour vérifier la connectivité réseau
check_network() {
    echo -e "${BLUE}Vérification de la connectivité réseau vers ${SMB_HOST}...${NC}"

    if ping -c 1 -W 2 "$SMB_HOST" &> /dev/null; then
        echo -e "${GREEN}✓ Hôte ${SMB_HOST} accessible${NC}"
        return 0
    else
        echo -e "${RED}✗ Hôte ${SMB_HOST} inaccessible${NC}"
        echo "Vérifiez votre connexion réseau et l'adresse IP"
        return 1
    fi
}

# Fonction pour créer le point de montage
create_mount_point() {
    if [ ! -d "$MOUNT_POINT" ]; then
        echo -e "${BLUE}Création du point de montage ${MOUNT_POINT}...${NC}"
        sudo mkdir -p "$MOUNT_POINT"
        echo -e "${GREEN}✓ Point de montage créé${NC}"
    else
        echo -e "${GREEN}✓ Point de montage existe déjà${NC}"
    fi
}

# Fonction pour vérifier si le partage est déjà monté
is_mounted() {
    if mount | grep -q "$MOUNT_POINT"; then
        return 0  # Monté
    else
        return 1  # Pas monté
    fi
}

# Fonction pour démonter le partage
unmount_share() {
    echo -e "${BLUE}Démontage du partage réseau...${NC}"

    if is_mounted; then
        sudo umount "$MOUNT_POINT" 2>/dev/null || {
            echo -e "${YELLOW}Tentative de démontage forcé...${NC}"
            sudo umount -l "$MOUNT_POINT"
        }
        echo -e "${GREEN}✓ Partage démonté${NC}"
    else
        echo -e "${YELLOW}Le partage n'était pas monté${NC}"
    fi
}

# Fonction pour monter le partage
mount_share() {
    echo -e "${BLUE}Montage du partage réseau ${SMB_PATH}...${NC}"

    # Vérifier si déjà monté
    if is_mounted; then
        echo -e "${YELLOW}Le partage est déjà monté sur ${MOUNT_POINT}${NC}"
        return 0
    fi

    # Construire les options de montage
    MOUNT_OPTIONS="$SMB_MOUNT_OPTIONS"

    # Ajouter les credentials si fournis
    if [ -n "$SMB_USERNAME" ]; then
        if [ -n "$SMB_PASSWORD" ]; then
            MOUNT_OPTIONS="${MOUNT_OPTIONS},username=${SMB_USERNAME},password=${SMB_PASSWORD}"
        else
            # Pas de mot de passe
            MOUNT_OPTIONS="${MOUNT_OPTIONS},username=${SMB_USERNAME},password="
        fi
    else
        # Montage guest (sans authentification)
        MOUNT_OPTIONS="${MOUNT_OPTIONS},guest"
    fi

    # Montage
    echo "Options de montage: ${MOUNT_OPTIONS%,password=*}"  # Cache le mot de passe

    if sudo mount -t cifs "$SMB_PATH" "$MOUNT_POINT" -o "$MOUNT_OPTIONS"; then
        echo -e "${GREEN}✓ Partage monté avec succès sur ${MOUNT_POINT}${NC}"

        # Test d'écriture
        TEST_FILE="${MOUNT_POINT}/.mount_test_$$"
        if echo "test" > "$TEST_FILE" 2>/dev/null; then
            rm -f "$TEST_FILE"
            echo -e "${GREEN}✓ Test d'écriture réussi${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠ Montage réussi mais écriture impossible${NC}"
            echo "Vérifiez les permissions sur le partage réseau"
            return 1
        fi
    else
        echo -e "${RED}✗ Échec du montage${NC}"
        echo "Vérifiez les credentials et les permissions du partage"
        return 1
    fi
}

# Fonction pour afficher le statut
show_status() {
    echo -e "${BLUE}=== État du montage réseau ===${NC}"
    echo "Point de montage: $MOUNT_POINT"
    echo "Partage SMB: $SMB_PATH"

    if is_mounted; then
        echo -e "${GREEN}État: MONTÉ ✓${NC}"

        # Afficher les détails du montage
        mount | grep "$MOUNT_POINT"

        # Tester l'accès
        if [ -w "$MOUNT_POINT" ]; then
            echo -e "${GREEN}Écriture: POSSIBLE ✓${NC}"
        else
            echo -e "${YELLOW}Écriture: IMPOSSIBLE ✗${NC}"
        fi

        # Afficher l'espace disponible
        df -h "$MOUNT_POINT" | tail -1
    else
        echo -e "${RED}État: NON MONTÉ ✗${NC}"
    fi

    # Tester la connectivité réseau
    if ping -c 1 -W 2 "$SMB_HOST" &> /dev/null; then
        echo -e "${GREEN}Réseau: ACCESSIBLE ✓${NC}"
    else
        echo -e "${RED}Réseau: INACCESSIBLE ✗${NC}"
    fi
}

# Fonction principale
main() {
    # Charger la configuration
    load_env

    # Vérifier que les variables essentielles sont définies
    if [ -z "$MOUNT_POINT" ] || [ -z "$SMB_PATH" ] || [ -z "$SMB_HOST" ]; then
        echo -e "${RED}Erreur: Variables de configuration manquantes dans .env${NC}"
        echo "Assurez-vous que MOUNT_POINT, SMB_PATH et SMB_HOST sont définis"
        exit 1
    fi

    # Action selon le paramètre
    ACTION="${1:-mount}"

    case "$ACTION" in
        mount)
            echo -e "${BLUE}=== Montage du partage réseau ===${NC}"
            install_cifs
            check_network || exit 1
            create_mount_point
            mount_share
            ;;

        unmount)
            echo -e "${BLUE}=== Démontage du partage réseau ===${NC}"
            unmount_share
            ;;

        remount)
            echo -e "${BLUE}=== Remontage du partage réseau ===${NC}"
            unmount_share
            sleep 1
            check_network || exit 1
            mount_share
            ;;

        status)
            show_status
            ;;

        *)
            echo "Usage: $0 {mount|unmount|remount|status}"
            echo ""
            echo "Commandes:"
            echo "  mount     - Monte le partage réseau SMB"
            echo "  unmount   - Démonte le partage réseau"
            echo "  remount   - Démonte puis remonte le partage"
            echo "  status    - Affiche l'état du montage"
            exit 1
            ;;
    esac
}

# Exécution
main "$@"
