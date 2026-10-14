"""Ancien point d'entrée autonome du moteur.

DEPRECATED : la boucle H24 tourne déjà dans `api.main` (uvicorn).
Lancer `python -m engine.main` en parallèle charge un second Univers en RAM
et provoque des OOM sur l'instance 8 Go EC2.

Ce module reste disponible pour debug local isolé, mais le service systemd
`ouroboros-engine` doit rester désactivé en production.
"""
from __future__ import annotations

import os
import sys
import time


def main() -> None:
    if os.environ.get("OUROBOROS_ALLOW_STANDALONE_ENGINE", "").strip() not in ("1", "true", "TRUE"):
        print(
            "[ouroboros-engine] REFUS : le moteur autonome est désactivé en production "
            "(doublon de api.main). Pour forcer : OUROBOROS_ALLOW_STANDALONE_ENGINE=1",
            flush=True,
        )
        # Rester vivant sans charger l'univers, pour ne pas faire boucler systemd
        while True:
            time.sleep(3600)
        return

    from engine.engine import Universe

    print("[ouroboros-engine] Mode debug autonome activé…", flush=True)
    u = Universe("main", 42)
    print(f"[ouroboros-engine] Univers actif : {u.id}, date : {u.date}", flush=True)
    while True:
        try:
            u.step(1)
            time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception as e:  # noqa: BLE001
            print(f"[ouroboros-engine] Erreur tick : {e}", file=sys.stderr, flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
