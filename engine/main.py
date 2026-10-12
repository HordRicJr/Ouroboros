"""Point d'entrée du moteur de simulation pour le démarrage serveur : python -m engine.main"""
import sys
import time

from engine.engine import Universe


def main():
    print("[ouroboros-engine] Initialisation et démarrage du moteur de simulation...", flush=True)
    # Lancement de la boucle principale de simulation
    u = Universe("main", 42)
    print(f"[ouroboros-engine] Univers actif : {u.id}, date courante : {u.date}", flush=True)
    while True:
        try:
            evs = u.step(1)
            if evs:
                # Log succinct des événements
                for ev in evs:
                    if ev.type in ("new_year", "season_start", "speciation", "extinction"):
                        print(f"[ouroboros-engine] Événement [{ev.type}]: {ev.payload}", flush=True)
            time.sleep(1)  # 1 seconde réelle = 1 jour simulé
        except KeyboardInterrupt:
            print("[ouroboros-engine] Arrêt du moteur demandé.", flush=True)
            break
        except Exception as e:  # noqa: BLE001
            print(f"[ouroboros-engine] Erreur tick : {e}", file=sys.stderr, flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
