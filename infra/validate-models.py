#!/usr/bin/env python3
"""Script de validation du manifeste des modèles infra/models.json"""
import json
import sys
from pathlib import Path

def validate():
    manifest_path = Path("infra/models.json")
    if not manifest_path.exists():
        print("Erreur: infra/models.json n'existe pas.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Erreur de syntaxe JSON dans infra/models.json: {e}", file=sys.stderr)
        sys.exit(1)

    if "models" not in data or not isinstance(data["models"], list):
        print("Erreur: champ racine 'models' manquant ou invalide.", file=sys.stderr)
        sys.exit(1)

    required_fields = ["id", "role", "active", "filename", "size_gb"]
    roles_active = {}

    for i, m in enumerate(data["models"]):
        for rf in required_fields:
            if rf not in m:
                print(f"Erreur: champ obligatoire '{rf}' manquant dans le modèle index {i} (id: {m.get('id')}).", file=sys.stderr)
                sys.exit(1)

        role = m["role"]
        active = m["active"]
        if active:
            if role in roles_active:
                print(f"Erreur: plusieurs modèles actifs configurés pour le rôle '{role}' ({roles_active[role]} et {m['id']}). Un seul modèle actif autorisé par rôle.", file=sys.stderr)
                sys.exit(1)
            roles_active[role] = m["id"]

    print("Validation du manifeste infra/models.json : SUCCÈS")
    sys.exit(0)

if __name__ == "__main__":
    validate()
