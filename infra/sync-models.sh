#!/usr/bin/env bash
# ==============================================================================
# sync-models.sh - Synchronisation et activation sécurisée des modèles IA
# Exécuté côté serveur dans /home/ubuntu/ouroboros/sync-models.sh
# ==============================================================================
set -euo pipefail

BASE_DIR="/home/ubuntu/ouroboros"
MODELS_DIR="$BASE_DIR/models"
LOG_FILE="$BASE_DIR/logs/models.log"
MANIFEST="$BASE_DIR/infra/models.json"
ENV_FILE="$BASE_DIR/.env"
LOCK_FILE="/tmp/ouroboros-sync-models.lock"

mkdir -p "$MODELS_DIR" "$BASE_DIR/logs"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

# Verrou exclusif flock
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    log "Un autre processus de synchronisation des modèles est déjà en cours d'exécution. Abandon."
    exit 0
fi

# Charger HF_TOKEN si présent dans .env
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set +u
    export HF_TOKEN="$(grep -E '^HF_TOKEN=' "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' || true)"
    set -u
fi

PRUNE_MODE=0
for arg in "$@"; do
    if [ "$arg" = "--prune" ]; then
        PRUNE_MODE=1
    fi
done

if [ ! -f "$MANIFEST" ]; then
    log "Erreur : Manifeste $MANIFEST introuvable."
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    log "Erreur : 'jq' n'est pas installé sur le serveur."
    exit 1
fi

log "=== Début de la synchronisation des modèles ==="

# 1. Vérifier et synchroniser chaque modèle du manifeste
MODELS_COUNT=$(jq '.models | length' "$MANIFEST")
ACTIVE_LLM_FILE=""
ACTIVE_LLM_MIN_RAM=0

for i in $(seq 0 $((MODELS_COUNT - 1))); do
    ID=$(jq -r ".models[$i].id" "$MANIFEST")
    ROLE=$(jq -r ".models[$i].role" "$MANIFEST")
    ACTIVE=$(jq -r ".models[$i].active" "$MANIFEST")
    FILENAME=$(jq -r ".models[$i].filename" "$MANIFEST")
    URL=$(jq -r ".models[$i].url" "$MANIFEST")
    EXPECTED_SHA=$(jq -r ".models[$i].sha256 // empty" "$MANIFEST")
    SIZE_GB=$(jq -r ".models[$i].size_gb" "$MANIFEST")
    MIN_RAM_GB=$(jq -r ".models[$i].min_ram_gb // 0" "$MANIFEST")

    if [ "$ROLE" = "llm" ] && [ "$ACTIVE" = "true" ]; then
        ACTIVE_LLM_FILE="$FILENAME"
        ACTIVE_LLM_MIN_RAM="$MIN_RAM_GB"
    fi

    if [ -z "$URL" ] || [ "$URL" = "null" ]; then
        log "Modèle '$ID' ($FILENAME) : URL vide, ignoré."
        continue
    fi

    TARGET_FILE="$MODELS_DIR/$FILENAME"
    PART_FILE="$TARGET_FILE.part"

    # Vérifier si le fichier existe déjà
    if [ -f "$TARGET_FILE" ]; then
        log "Modèle '$ID' : déjà présent dans $TARGET_FILE."
        if [ -n "$EXPECTED_SHA" ]; then
            ACTUAL_SHA=$(sha256sum "$TARGET_FILE" | awk '{print $1}')
            if [ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]; then
                log "ATTENTION : Somme de contrôle sha256 discordante pour $FILENAME (attendu: $EXPECTED_SHA, calculé: $ACTUAL_SHA)."
            else
                log "Validation sha256 OK pour $FILENAME."
            fi
        fi
        continue
    fi

    # Vérification de l'espace disque libre (taille du modèle + 3 Go de marge)
    NEEDED_MB=$(awk "BEGIN {print int(($SIZE_GB + 3) * 1024)}")
    AVAIL_KB=$(df -P "$MODELS_DIR" | tail -1 | awk '{print $4}')
    AVAIL_MB=$((AVAIL_KB / 1024))

    log "Téléchargement requis pour '$ID' ($FILENAME, ~${SIZE_GB} Go). Espace disponible : ${AVAIL_MB} Mo, requis : ${NEEDED_MB} Mo."
    if [ "$AVAIL_MB" -lt "$NEEDED_MB" ]; then
        log "ERREUR : Espace disque insuffisant pour $FILENAME (${AVAIL_MB} Mo dispo < ${NEEDED_MB} Mo requis). Téléchargement annulé."
        continue
    fi

    # Téléchargement vers .part avec reprise (-C -)
    log "Début du téléchargement de $URL ..."
    CURL_AUTH=()
    if [ -n "${HF_TOKEN:-}" ]; then
        CURL_AUTH=(-H "Authorization: Bearer $HF_TOKEN")
    fi

    if curl -L --fail --retry 5 -C - "${CURL_AUTH[@]}" -o "$PART_FILE" "$URL" >> "$LOG_FILE" 2>&1; then
        if [ -n "$EXPECTED_SHA" ]; then
            ACTUAL_SHA=$(sha256sum "$PART_FILE" | awk '{print $1}')
            if [ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]; then
                log "ATTENTION sha256 après téléchargement de $FILENAME (reçu $ACTUAL_SHA)."
            fi
        fi
        mv -f "$PART_FILE" "$TARGET_FILE"
        log "Téléchargement et déplacement atomique réussis pour $FILENAME."
    else
        log "Échec du téléchargement pour $FILENAME. Le fichier .part est conservé pour reprise ultérieure."
    fi
done

# 2. Gestion du lien symbolique du modèle LLM actif
SYMLINK_PATH="$MODELS_DIR/model.gguf"

if [ -n "$ACTIVE_LLM_FILE" ]; then
    ACTIVE_FILE_PATH="$MODELS_DIR/$ACTIVE_LLM_FILE"

    # Si model.gguf est un fichier régulier (installation initiale), le renommer
    if [ -f "$SYMLINK_PATH" ] && [ ! -L "$SYMLINK_PATH" ]; then
        log "model.gguf est un fichier régulier. Sauvegarde en model.initial.gguf."
        mv "$SYMLINK_PATH" "$MODELS_DIR/model.initial.gguf"
        ln -sfn "$MODELS_DIR/model.initial.gguf" "$SYMLINK_PATH"
    fi

    if [ -f "$ACTIVE_FILE_PATH" ]; then
        # Vérification RAM avant bascule
        TOTAL_RAM_GB=$(free -g | awk '/^Mem:/ {print $2}')
        if [ "$ACTIVE_LLM_MIN_RAM" -gt 0 ] && [ "$TOTAL_RAM_GB" -lt "$ACTIVE_LLM_MIN_RAM" ]; then
            log "ATTENTION : RAM totale ($TOTAL_RAM_GB Go) inférieure à min_ram_gb ($ACTIVE_LLM_MIN_RAM Go). Refus de bascule."
        else
            CURRENT_TARGET=""
            if [ -L "$SYMLINK_PATH" ]; then
                CURRENT_TARGET=$(readlink -f "$SYMLINK_PATH" || true)
            fi

            RESOLVED_ACTIVE=$(readlink -f "$ACTIVE_FILE_PATH" || true)

            if [ "$CURRENT_TARGET" != "$RESOLVED_ACTIVE" ]; then
                log "Bascule du modèle actif vers $ACTIVE_LLM_FILE."
                OLD_LINK="$CURRENT_TARGET"

                # Basculer le symlink
                ln -sfn "$ACTIVE_FILE_PATH" "$SYMLINK_PATH"

                # Redémarrer ouroboros-llm
                if systemctl is-active --quiet ouroboros-llm 2>/dev/null || systemctl is-enabled --quiet ouroboros-llm 2>/dev/null; then
                    log "Redémarrage de ouroboros-llm..."
                    sudo systemctl restart ouroboros-llm || true

                    # Vérification santé pendant jusqu'à 90s
                    HEALTHY=0
                    for _ in $(seq 1 18); do
                        if curl -s -f http://127.0.0.1:8080/health >/dev/null 2>&1; then
                            HEALTHY=1
                            break
                        fi
                        sleep 5
                    done

                    if [ "$HEALTHY" -eq 1 ]; then
                        log "Vérification de santé OK pour le nouveau modèle LLM (port 8080)."
                    else
                        log "ERREUR : Le nouveau modèle ne répond pas sur /health après 90s. Retour à l'ancien modèle."
                        if [ -n "$OLD_LINK" ] && [ -f "$OLD_LINK" ]; then
                            ln -sfn "$OLD_LINK" "$SYMLINK_PATH"
                            sudo systemctl restart ouroboros-llm || true
                            log "Restauration de l'ancien modèle $OLD_LINK effectuée."
                        fi
                    fi
                fi
            else
                log "Le modèle actif $ACTIVE_LLM_FILE est déjà configuré."
            fi
        fi
    else
        log "Le fichier du modèle actif $ACTIVE_LLM_FILE n'est pas encore présent sur le disque."
    fi
fi

# 3. Mode --prune explicite
if [ "$PRUNE_MODE" -eq 1 ]; then
    log "Nettoyage (--prune) des modèles inactifs..."
    CURRENT_ACTIVE_TARGET=""
    if [ -L "$SYMLINK_PATH" ]; then
        CURRENT_ACTIVE_TARGET=$(readlink -f "$SYMLINK_PATH")
    fi

    for f in "$MODELS_DIR"/*.gguf "$MODELS_DIR"/*.onnx; do
        if [ -f "$f" ] && [ ! -L "$f" ]; then
            RESOLVED=$(readlink -f "$f")
            if [ "$RESOLVED" != "$CURRENT_ACTIVE_TARGET" ]; then
                log "Suppression de l'ancien modèle : $f"
                rm -f "$f"
            fi
        fi
    done
fi

log "=== Fin de la synchronisation des modèles ==="
