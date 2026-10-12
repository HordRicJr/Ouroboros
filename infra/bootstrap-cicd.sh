#!/usr/bin/env bash
# ==============================================================================
# bootstrap-cicd.sh - Automatisation complète et idempotente du CI/CD Ouroboros
# Exécutable en local à la racine du dépôt.
# ==============================================================================
set -euo pipefail

REPO="HordRicJr/Ouroboros"
ENV_FILE=".env"
ADMIN_KEY_DEFAULT="D:/Simulation.pem"
ADMIN_KEY="${1:-$ADMIN_KEY_DEFAULT}"
DEPLOY_DIR=".deploy"
DEPLOY_KEY="$DEPLOY_DIR/id_ed25519"
SERVER_IP="13.49.23.84"
SERVER_USER="ubuntu"

echo "=== [0/5] Vérification des prérequis ==="
for cmd in git gh ssh ssh-keygen curl python; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Erreur : commande '$cmd' introuvable."
        exit 1
    fi
done

if ! gh auth status >/dev/null 2>&1; then
    echo "Erreur : non authentifié sur la CLI GitHub ('gh auth status' en échec)."
    exit 1
fi

if [ ! -f "$ADMIN_KEY" ]; then
    echo "Erreur : Clé d'administration introuvable ($ADMIN_KEY)."
    exit 1
fi

echo "=== [1/5] Génération idempotente de la clé de déploiement ==="
mkdir -p "$DEPLOY_DIR"
if [ ! -f "$DEPLOY_KEY" ]; then
    echo "Création de la clé ed25519 de déploiement..."
    ssh-keygen -t ed25519 -f "$DEPLOY_KEY" -P "" -C "github-actions-ouroboros-deploy"
else
    echo "Clé de déploiement existante détectée ($DEPLOY_KEY)."
fi

echo "=== [2/5] Installation de la clé publique sur l'instance EC2 ==="
python - << 'EOF'
import paramiko, sys

deploy_pub = open(".deploy/id_ed25519.pub").read().strip()
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("13.49.23.84", username="ubuntu", key_filename="D:/Simulation.pem", timeout=10)

sftp = client.open_sftp()
content = ""
try:
    with sftp.file("/home/ubuntu/.ssh/authorized_keys", "r") as f:
        content = f.read().decode()
except Exception:
    pass

lines = [l.strip() for l in content.splitlines() if l.strip()]
if deploy_pub not in lines:
    lines.append(deploy_pub)
    with sftp.file("/home/ubuntu/.ssh/authorized_keys", "w") as f:
        f.write("\n".join(lines) + "\n")
    sftp.chmod("/home/ubuntu/.ssh/authorized_keys", 0o600)
    print("Nouvelle clé publique ajoutée à ~/.ssh/authorized_keys")
else:
    print("Clé publique déjà présente dans authorized_keys (pas de doublon).")

sftp.close()
client.close()
EOF

echo "Test de connexion avec la clé de déploiement..."
python - << 'EOF'
import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("13.49.23.84", username="ubuntu", key_filename=".deploy/id_ed25519", timeout=10)
stdin, stdout, stderr = client.exec_command("echo deploy-connection-ok")
res = stdout.read().decode().strip()
client.close()
if res != "deploy-connection-ok":
    raise RuntimeError("Test de connexion deploy échoué")
print("Connexion deploy SSH : VALIDÉE")
EOF

echo "=== [3/5] Récupération de l'empreinte serveur EC2_KNOWN_HOSTS ==="
HOST_KEY=$(python - << 'EOF'
import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("13.49.23.84", username="ubuntu", key_filename="D:/Simulation.pem")
k = client.get_transport().get_remote_server_key()
print("13.49.23.84 " + k.get_name() + " " + k.get_base64())
client.close()
EOF
)

echo "=== [4/5] Configuration des Secrets GitHub (dépôt et environnement production) ==="
# Création de l'environnement production si possible
gh api -X PUT "repos/$REPO/environments/production" >/dev/null 2>&1 || true

python - << EOF
import subprocess

env = {}
for line in open(".env"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

deploy_key = open(".deploy/id_ed25519").read()
host_key = """$HOST_KEY"""

secrets = {
    "EC2_HOST": env.get("EC2_HOST", "13.49.23.84"),
    "EC2_USER": env.get("EC2_USER", "ubuntu"),
    "EC2_SSH_KEY": deploy_key,
    "EC2_KNOWN_HOSTS": host_key,
    "API_URL": env.get("API_URL", "https://13-49-23-84.sslip.io"),
    "API_KEY": env.get("API_KEY", ""),
}

for name, val in secrets.items():
    if not val:
        continue
    subprocess.run(["gh", "secret", "set", name, "--repo", "$REPO"], input=val, text=True, check=True)
    subprocess.run(["gh", "secret", "set", name, "--repo", "$REPO", "--env", "production"], input=val, text=True, check=True)

print("Tous les secrets ont été synchronisés.")
EOF

echo "=== [5/5] Liste des secrets GitHub ==="
gh secret list --repo "$REPO"
echo "--- Environnement Production ---"
gh secret list --repo "$REPO" --env production

echo "=== Bootstrap CI/CD Ouroboros terminé avec succès ! ==="
