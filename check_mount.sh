#!/bin/bash
###############################################################################
# Script de vérification de santé du montage SMB pour VideoCard
#
# Ce script vérifie périodiquement que le partage réseau est monté et accessible
# Peut être utilisé en cron job pour une surveillance continue
#
# Usage:
#   ./check_mount.sh                    # Vérification unique
#   ./check_mount.sh --auto-remount     # Remonte automatiquement si nécessaire
#   ./check_mount.sh --json             # Sortie en format JSON
#   ./check_mount.sh --notify           # Envoie des notifications (nécessite libnotify)
#
# Exemples de cron job:
#   */5 * * * * /path/to/check_mount.sh --auto-remount >> /var/log/videocard_mount.log 2>&1
###############################################################################

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Chemin du script de montage
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOUNT_SCRIPT="${SCRIPT_DIR}/mount_network.sh"

# Options par défaut
AUTO_REMOUNT=false
JSON_OUTPUT=false
SEND_NOTIFY=false

# Parser les arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --auto-remount)
            AUTO_REMOUNT=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --notify)
            SEND_NOTIFY=true
            shift
            ;;
        *)
            echo "Usage: $0 [--auto-remount] [--json] [--notify]"
            exit 1
            ;;
    esac
done

# Fonction pour charger les variables du .env
load_env() {
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        if [ "$JSON_OUTPUT" = true ]; then
            echo '{"error": "Fichier .env introuvable", "status": "error"}'
        else
            echo -e "${RED}Erreur: Fichier .env introuvable${NC}"
        fi
        exit 1
    fi

    export $(grep -v '^#' "${SCRIPT_DIR}/.env" | grep -v '^$' | xargs)
}

# Fonction pour envoyer une notification
send_notification() {
    local title="$1"
    local message="$2"
    local urgency="${3:-normal}"  # low, normal, critical

    if [ "$SEND_NOTIFY" = true ]; then
        if command -v notify-send &> /dev/null; then
            notify-send -u "$urgency" "$title" "$message"
        fi
    fi
}

# Fonction pour vérifier si le partage est monté
is_mounted() {
    if mount | grep -q "$MOUNT_POINT"; then
        return 0  # Monté
    else
        return 1  # Pas monté
    fi
}

# Fonction pour tester l'accessibilité en lecture
test_read_access() {
    if [ -r "$MOUNT_POINT" ]; then
        return 0
    else
        return 1
    fi
}

# Fonction pour tester l'accessibilité en écriture
test_write_access() {
    local test_file="${MOUNT_POINT}/.health_check_$$"

    if echo "test" > "$test_file" 2>/dev/null; then
        rm -f "$test_file" 2>/dev/null
        return 0
    else
        return 1
    fi
}

# Fonction pour tester la connectivité réseau
test_network() {
    if ping -c 1 -W 2 "$SMB_HOST" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Fonction pour obtenir l'espace disque disponible
get_disk_space() {
    if is_mounted; then
        df -BM "$MOUNT_POINT" | tail -1 | awk '{print $4}' | sed 's/M//'
    else
        echo "0"
    fi
}

# Fonction pour obtenir le nombre de fichiers
count_files() {
    if is_mounted && test_read_access; then
        find "$MOUNT_POINT" -maxdepth 1 -type f 2>/dev/null | wc -l
    else
        echo "0"
    fi
}

# Fonction principale de vérification
check_mount_health() {
    local status="OK"
    local issues=()
    local warnings=()

    # 1. Vérifier que le partage est monté
    if ! is_mounted; then
        status="ERROR"
        issues+=("Partage non monté")

        if [ "$AUTO_REMOUNT" = true ]; then
            if [ "$JSON_OUTPUT" = false ]; then
                echo -e "${YELLOW}Tentative de remontage automatique...${NC}"
            fi

            if bash "$MOUNT_SCRIPT" mount &>/dev/null; then
                status="RECOVERED"
                warnings+=("Partage remonté automatiquement")
                send_notification "VideoCard - Montage réseau" "Partage remonté automatiquement" "normal"
            else
                send_notification "VideoCard - Erreur" "Échec du remontage automatique" "critical"
                issues+=("Échec du remontage automatique")
            fi
        fi
    fi

    # 2. Vérifier la connectivité réseau
    if ! test_network; then
        if [ "$status" != "ERROR" ]; then
            status="WARNING"
        fi
        warnings+=("Hôte réseau inaccessible")
    fi

    # 3. Vérifier l'accès en lecture
    if is_mounted && ! test_read_access; then
        status="ERROR"
        issues+=("Impossible de lire le partage")
    fi

    # 4. Vérifier l'accès en écriture
    if is_mounted && ! test_write_access; then
        if [ "$status" != "ERROR" ]; then
            status="WARNING"
        fi
        warnings+=("Impossible d'écrire sur le partage")
    fi

    # Informations supplémentaires
    local disk_space=$(get_disk_space)
    local file_count=$(count_files)
    local timestamp=$(date -Iseconds)

    # Sortie selon le format demandé
    if [ "$JSON_OUTPUT" = true ]; then
        # Format JSON
        echo -n '{'
        echo -n "\"timestamp\": \"$timestamp\","
        echo -n "\"status\": \"$status\","
        echo -n "\"mount_point\": \"$MOUNT_POINT\","
        echo -n "\"smb_path\": \"$SMB_PATH\","
        echo -n "\"is_mounted\": $(is_mounted && echo 'true' || echo 'false'),"
        echo -n "\"network_reachable\": $(test_network && echo 'true' || echo 'false'),"
        echo -n "\"readable\": $(is_mounted && test_read_access && echo 'true' || echo 'false'),"
        echo -n "\"writable\": $(is_mounted && test_write_access && echo 'true' || echo 'false'),"
        echo -n "\"disk_space_mb\": $disk_space,"
        echo -n "\"file_count\": $file_count,"
        echo -n "\"issues\": [$(printf '"%s",' "${issues[@]}" | sed 's/,$//')],"
        echo -n "\"warnings\": [$(printf '"%s",' "${warnings[@]}" | sed 's/,$//')]"
        echo '}'
    else
        # Format texte
        echo -e "${BLUE}=== Vérification de santé du montage réseau ===${NC}"
        echo "Timestamp: $timestamp"
        echo "Point de montage: $MOUNT_POINT"
        echo "Partage SMB: $SMB_PATH"
        echo ""

        case "$status" in
            OK)
                echo -e "${GREEN}État général: OK ✓${NC}"
                ;;
            WARNING)
                echo -e "${YELLOW}État général: AVERTISSEMENT ⚠${NC}"
                ;;
            ERROR)
                echo -e "${RED}État général: ERREUR ✗${NC}"
                ;;
            RECOVERED)
                echo -e "${GREEN}État général: RÉCUPÉRÉ ✓${NC}"
                ;;
        esac

        echo ""
        echo "Vérifications détaillées:"
        echo "  - Monté: $(is_mounted && echo -e "${GREEN}OUI ✓${NC}" || echo -e "${RED}NON ✗${NC}")"
        echo "  - Réseau accessible: $(test_network && echo -e "${GREEN}OUI ✓${NC}" || echo -e "${RED}NON ✗${NC}")"
        echo "  - Lecture possible: $(is_mounted && test_read_access && echo -e "${GREEN}OUI ✓${NC}" || echo -e "${RED}NON ✗${NC}")"
        echo "  - Écriture possible: $(is_mounted && test_write_access && echo -e "${GREEN}OUI ✓${NC}" || echo -e "${YELLOW}NON ✗${NC}")"

        echo ""
        echo "Informations:"
        echo "  - Espace disponible: ${disk_space} MB"
        echo "  - Nombre de fichiers: ${file_count}"

        if [ ${#issues[@]} -gt 0 ]; then
            echo ""
            echo -e "${RED}Problèmes détectés:${NC}"
            for issue in "${issues[@]}"; do
                echo "  - $issue"
            done
        fi

        if [ ${#warnings[@]} -gt 0 ]; then
            echo ""
            echo -e "${YELLOW}Avertissements:${NC}"
            for warning in "${warnings[@]}"; do
                echo "  - $warning"
            done
        fi
    fi

    # Code de sortie selon le statut
    case "$status" in
        OK|RECOVERED)
            exit 0
            ;;
        WARNING)
            exit 1
            ;;
        ERROR)
            exit 2
            ;;
    esac
}

# Fonction principale
main() {
    load_env

    # Vérifier que les variables essentielles sont définies
    if [ -z "$MOUNT_POINT" ] || [ -z "$SMB_PATH" ] || [ -z "$SMB_HOST" ]; then
        if [ "$JSON_OUTPUT" = true ]; then
            echo '{"error": "Variables de configuration manquantes", "status": "error"}'
        else
            echo -e "${RED}Erreur: Variables de configuration manquantes dans .env${NC}"
        fi
        exit 1
    fi

    # Exécuter la vérification
    check_mount_health
}

# Exécution
main
