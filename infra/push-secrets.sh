#!/usr/bin/env bash
# ==============================================================================
# push-secrets.sh - Envoi automatique des variables du .env local vers GitHub Secrets
# Usage : ./infra/push-secrets.sh
# ==============================================================================
set -euo pipefail

ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Erreur : fichier $ENV_FILE introuvable à la racine."
    exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
    echo "Erreur : La CLI 'gh' (GitHub CLI) n'est pas installée."
    exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "Erreur : La CLI 'gh' n'est pas connectée. Exécutez 'gh auth login'."
    exit 1
fi

echo "Lecture de $ENV_FILE et injection dans les GitHub Secrets..."

while IFS='=' read -r key value || [ -n "$key" ]; do
    # Ignorer commentaires et lignes vides
    [[ "$key" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$key" ]] && continue
    
    # Nettoyage des espaces
    key="$(echo "$key" | xargs)"
    value="$(echo "$value" | xargs)"

    if [ "$key" = "EC2_SSH_KEY_PATH" ]; then
        if [ -f "$value" ]; then
            echo "-> Envoi du secret EC2_SSH_KEY depuis le fichier $value..."
            gh secret set EC2_SSH_KEY < "$value"
        else
            echo "AVERTISSEMENT : Fichier de clé $value introuvable, secret EC2_SSH_KEY non mis à jour."
        fi
    elif [ -n "$key" ] && [ -n "$value" ]; then
        echo "-> Envoi du secret $key..."
        echo -n "$value" | gh secret set "$key"
    fi
done < "$ENV_FILE"

echo "Tous les secrets ont été enregistrés avec succès dans le dépôt GitHub."
