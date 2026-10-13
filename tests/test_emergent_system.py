"""Tests complets pour l'architecture émergente, sociométrique et cognitive d'Ouroboros."""
import pytest
from fastapi.testclient import TestClient

from api.main import app, universes
from engine.agent_cognition import AgentCognition, PersonalityProfile
from engine.engine import Universe
from engine.experiment import fork_universe_state
from engine.llm import MockLLMClient
from engine.metrics import calculate_gini, calculate_shannon_entropy
from engine.social_graph import SocialGraph


def test_gini_and_entropy_calculations():
    # Égalité parfaite -> Gini = 0
    assert calculate_gini([10.0, 10.0, 10.0, 10.0]) == 0.0

    # Inégalité forte -> Gini élevé
    high_gini = calculate_gini([0.0, 0.0, 0.0, 100.0])
    assert high_gini > 0.7

    # Entropie de Shannon
    # Répartition uniforme -> entropie maximale = 1.0
    h_uniform = calculate_shannon_entropy({"a": 10, "b": 10, "c": 10, "d": 10})
    assert abs(h_uniform - 1.0) < 0.01

    # Une seule catégorie -> entropie nulle
    assert calculate_shannon_entropy({"a": 50, "b": 0}) == 0.0


def test_social_graph_deference():
    sg = SocialGraph()
    # Agent 2 demande conseil à Agent 1 à 3 reprises
    sg.record_interaction(tick=10, year=-4004, source_id=2, target_id=1, kind="advice", weight=1.0)
    sg.record_interaction(tick=15, year=-4004, source_id=2, target_id=1, kind="advice", weight=1.0)
    sg.record_interaction(tick=20, year=-4004, source_id=2, target_id=1, kind="advice", weight=1.0)

    # Agent 1 est cité dans les souvenirs
    sg.record_interaction(tick=25, year=-4004, source_id=2, target_id=1, kind="mention", weight=1.0)

    # Agent 1 a arbitré une tension (médiation)
    sg.record_interaction(tick=30, year=-4004, source_id=2, target_id=1, kind="mediation", weight=2.0)

    scores = sg.calculate_deference_centrality([1, 2])
    assert scores[1] > scores[2], "L'agent sollicité et médiateur doit avoir une plus grande centralité"

    title, role = sg.deduce_emergent_title(1, age=45.0, centrality=scores[1], has_spouse=True, children_count=3, clan_name="Racines")
    assert "respecté" in title or "Guide" in role or "Pilier" in role or "écoutée" in title


def test_agent_cognition_stream_and_reflection():
    cog = AgentCognition.create_random(person_id=1, seed=42)
    cog.reflection_threshold = 2.0
    assert 0.0 <= cog.personality.openness <= 1.0

    # Ajouter des souvenirs majeurs
    cog.add_memory(tick=10, year=-4004, text="Grande famine hivernale traversée avec le campement", importance=0.9)
    cog.add_memory(tick=20, year=-4004, text="Découverte d'une source d'eau limpide au pied de la colline", importance=0.85)
    cog.add_memory(tick=30, year=-4004, text="Pacte de concorde scellé avec nos voisins", importance=0.95)

    # Déclencher la réflexion
    refl = cog.trigger_reflection_if_needed(current_tick=35)
    assert refl is not None
    assert len(cog.reflections) > 0

    # Minimal control prompt test
    prompt_ctx = cog.build_minimal_prompt_context(current_tick=40)
    assert "Traits de caractère dominants" in prompt_ctx
    # Pas de consigne prescriptive
    assert "sois méfiant" not in prompt_ctx.lower()
    assert "obéis au chef" not in prompt_ctx.lower()


def test_universe_emergent_dynamics():
    u = Universe("test-emergent-u", seed=42, start_year=-4004)

    # Vérifier l'initialisation sans grades prédéfinis arbitraires
    for prof in u.notables.values():
        assert prof.rank_grade in ("Guide", "Conseiller", "Pilier", "Aîné", "Membre")
        assert 1 <= prof.influence <= 100

    # Simuler 100 jours
    u.step(100)

    # Vérifier que les métriques saisonnières ont été enregistrées
    assert len(u.metrics_history.snapshots) > 0
    latest = u.metrics_history.get_latest()
    assert latest is not None
    assert "gini_influence" in latest
    assert "behavioral_entropy" in latest
    assert "population" in latest

    # Test dialogue autonome avec un habitant
    notable_id = list(u.notables.keys())[0]
    reply = u.ask_notable(notable_id, "Tu ne dois pas manger de pommes, c'est un interdit sacré.", llm_client=MockLLMClient())
    assert isinstance(reply, str)
    assert len(reply) > 0

    # Vérifier le marquage de la branche
    assert u.branch_metadata.branch_type == "observer_intervention"

    # Vérifier la journalisation IA
    assert u.ai_logger.counter >= 1
    recent_logs = u.ai_logger.get_recent(limit=5)
    assert len(recent_logs) >= 1
    assert "pomme" in recent_logs[0]["prompt"] or "pommes" in recent_logs[0]["prompt"]


def test_universe_snapshot_and_forking():
    u = Universe("test-fork-parent", seed=100, start_year=-4004)
    u.step(50)

    # Créer une branche
    child = fork_universe_state(u, "test-fork-child", "observer_intervention", "Test d'intervention divine")
    assert child.id == "test-fork-child"
    assert child.branch_metadata.parent_universe_id == "test-fork-parent"
    assert child.branch_metadata.branch_type == "observer_intervention"

    # Sauvegarde et restauration snapshot
    snap_bytes = child.snapshot()
    restored = Universe.from_snapshot(snap_bytes)
    assert restored.id == "test-fork-child"
    assert restored.branch_metadata.parent_universe_id == "test-fork-parent"
    assert len(restored.social_graph.deference_edges) == len(child.social_graph.deference_edges)


def test_api_research_endpoints():
    client = TestClient(app)

    # Créer un univers de test
    u = Universe("test-api-metrics", seed=777, start_year=-4004)
    u.step(100)
    universes["test-api-metrics"] = u

    # 1. GET metrics
    res = client.get("/universes/test-api-metrics/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "latest" in data

    # 2. Export CSV
    res_csv = client.get("/universes/test-api-metrics/metrics/export?format=csv")
    assert res_csv.status_code == 200
    assert "population" in res_csv.text

    # 3. Fork
    import uuid
    branch_name = f"test-api-metrics-branch-{uuid.uuid4().hex[:8]}"
    res_fork = client.post("/universes/test-api-metrics/fork", json={"child_id": branch_name, "description": "Branche C7"})
    assert res_fork.status_code == 200
    assert res_fork.json()["child_id"] == branch_name

    # 4. AI logs
    res_logs = client.get("/universes/test-api-metrics/ai_logs")
    assert res_logs.status_code == 200
    assert "total_calls" in res_logs.json()

    # 5. Research protocol
    res_proto = client.get("/universes/test-api-metrics/research_protocol")
    assert res_proto.status_code == 200
    assert "principles_compliance" in res_proto.json()
