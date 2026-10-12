# Guide Opérationnel CI/CD - Ouroboros

Ce document décrit pas à pas la configuration, l'exploitation et la maintenance du pipeline de déploiement continu d'**Ouroboros** sur l'instance AWS EC2 Ubuntu 24.04 (`13.49.23.84`).

---

## 1. Clé SSH de déploiement et configuration serveur
*(Automatisé avec succès par `infra/bootstrap-cicd.sh`)*

- Clé privée locale : `.deploy/id_ed25519` (git-ignorée, permissions NTFS restreintes).
- Clé publique : installée dans `~/.ssh/authorized_keys` sur le serveur `13.49.23.84`.
- Test de connexion : validé (`deploy-ok`).

---

## 2. Secrets GitHub et Environnement Production
*(Automatisé avec succès par `infra/bootstrap-cicd.sh`)*

L'environnement GitHub **`production`** a été initialisé sur le dépôt `HordRicJr/Ouroboros`.
Tous les secrets ont été enregistrés aux deux niveaux (Dépôt + Environnement `production`) :
- `EC2_HOST` : `13.49.23.84`
- `EC2_USER` : `ubuntu`
- `EC2_SSH_KEY` : Clé privée de déploiement ed25519
- `EC2_KNOWN_HOSTS` : Empreinte de clé hôte ed25519 du serveur
- `API_URL` : `https://13-49-23-84.sslip.io`
- `API_KEY` : Clé d'API configurée

---

## 3. Connexion de Vercel (Frontend)

Lorsque vous serez prêt à connecter le frontend Next.js (`web/`) :
1. Rendez-vous sur votre dashboard **Vercel** et importez le dépôt GitHub `HordRicJr/Ouroboros`.
2. Définissez le répertoire racine (**Root Directory**) sur `web`.
3. Ajoutez la variable d'environnement de production :
   - `NEXT_PUBLIC_API_URL` = `https://13-49-23-84.sslip.io`
4. Cliquez sur **Deploy**.

### Restriction CORS sur le serveur
Pour autoriser votre domaine Vercel à interroger l'API en production, éditez `/home/ubuntu/ouroboros/.env` sur le serveur :
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@13.49.23.84
nano ~/ouroboros/.env
# Modifiez la ligne :
# CORS_ORIGINS="https://mon-app.vercel.app,https://13-49-23-84.sslip.io"
sudo systemctl restart ouroboros-api
```

---

## 4. Procédure si l'adresse IP du serveur change

L'URL HTTPS actuelle (`https://13-49-23-84.sslip.io`) dépend de l'IP publique `13.49.23.84`. Si l'instance EC2 est arrêtée et redémarrée sans IP Elastic, AWS lui attribue une nouvelle IP (ex: `X.Y.Z.W`).

### Option A : Associer une IP Elastic fixe (Fortement recommandé)
1. Console AWS → **EC2** → **Elastic IPs** → **Allocate Elastic IP**.
2. Sélectionnez l'IP obtenue → **Associate Elastic IP** → Choisissez l'instance Ouroboros.
3. L'IP restera permanente même en cas d'arrêt/redémarrage.

### Option B : Mettre à jour manuellement après un changement d'IP
Si l'IP change vers `X.Y.Z.W` :
1. Sur le serveur, mettez à jour le Caddyfile :
   ```bash
   sudo nano /etc/caddy/Caddyfile
   # Remplacez l'ancien domaine par : X-Y-Z-W.sslip.io
   sudo systemctl reload caddy
   ```
2. Mettez à jour votre fichier local `.env` :
   ```ini
   EC2_HOST=X.Y.Z.W
   API_URL=https://X-Y-Z-W.sslip.io
   ```
3. Réinjectez les secrets GitHub :
   ```bash
   bash infra/push-secrets.sh
   ```
4. Dans **Vercel**, mettez à jour `NEXT_PUBLIC_API_URL` vers `https://X-Y-Z-W.sslip.io` et redéployez.

---

## 5. Gestion et synchronisation des modèles IA

Les modèles GGUF/ONNX ne transitent **jamais par Git**. Ils sont gérés via le manifeste `infra/models.json` :

```json
{
  "models": [
    {
      "id": "llm-main",
      "role": "llm",
      "active": true,
      "filename": "Qwen3-4B-Q4_K_M.gguf",
      "url": "https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf",
      "sha256": "",
      "size_gb": 2.8,
      "min_ram_gb": 6
    }
  ]
}
```

### Pour ajouter ou changer de modèle :
1. Modifiez `infra/models.json` dans votre dépôt (un seul modèle `active: true` pour le rôle `llm`).
2. Committez et poussez sur `main` :
   ```bash
   git add infra/models.json
   git commit -m "chore(models): mise à jour du modèle actif"
   git push origin main
   ```
3. Le workflow GitHub Actions déploie le code instantanément et déclenche `~/ouroboros/sync-models.sh` en arrière-plan sur le serveur.
4. Pour suivre le téléchargement côté serveur :
   ```bash
   tail -f ~/ouroboros/logs/models.log
   ```
5. Le script bascule atomiquement le lien symbolique `~/ouroboros/models/model.gguf` vers le nouveau modèle, redémarre `ouroboros-llm` et teste la santé sur `http://127.0.0.1:8080/health`. Si la santé échoue, il revient automatiquement au modèle précédent.

### Libérer de l'espace disque (prune) :
Pour supprimer les anciens modèles inactifs :
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@13.49.23.84 "bash ~/ouroboros/sync-models.sh --prune"
```

---

## 6. Procédure de Rollback (Retour arrière manuel)

### Rollback du Code Applicatif
Si besoin d'annuler manuellement une version sans repousser un commit :
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@13.49.23.84
cd ~/ouroboros
if [ -d app.previous ]; then
  rm -rf app
  cp -r app.previous app
  bash deploy.sh
fi
```

### Rollback du Modèle LLM
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@13.49.23.84
cd ~/ouroboros/models
# Refaire pointer le lien symbolique vers l'ancien modèle souhaité :
ln -sfn ancien-modele.gguf model.gguf
sudo systemctl restart ouroboros-llm
curl http://127.0.0.1:8080/health
```

---

## 7. Tests de Fumée (Smoke Test)

Après déploiement, vérifiez la santé des deux endpoints :
1. **API FastAPI externe (HTTPS via Caddy)** :
   ```bash
   curl -k https://13-49-23-84.sslip.io/api/health
   # Réponse attendue : {"status":"ok","api":"ok"}
   ```
2. **Serveur d'inférence LLM local (sur l'instance EC2)** :
   ```bash
   curl http://127.0.0.1:8080/health
   # Réponse attendue : {"status":"ok"}
   ```
