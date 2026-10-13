
from univers.budget import AIBudgetManager
from univers.engine import Universe
from univers.immersion import ImmersionFilter
from univers.llm import MockLLMClient
from univers.persistence import MemoryStore


def test_immersion_filter_sanitizes_meta_concepts():
    dirty_text = "Je sais que je suis dans une simulation créée par un ordinateur et une IA avec du code python."
    clean = ImmersionFilter.sanitize(dirty_text)
    assert not ImmersionFilter.check_immersion_break(clean)
    assert "simulation" not in clean.lower()
    assert "ordinateur" not in clean.lower()
    assert "code" not in clean.lower()


def test_notable_creation_and_memory_update():
    u = Universe("u_ai", 42)
    assert len(u.notables) > 0, "Les chefs de campement initiaux doivent être des notables"
    
    # Récupérer un notable
    notable_id = list(u.notables.keys())[0]
    profile = u.notables[notable_id]
    assert profile.title in ("Chef de campement", "Matriarche")
    
    # Avancer le temps pour que des événements se produisent
    u.step(365)
    # Vérifier que le notable est toujours valide
    assert notable_id in u.people.persons


def test_ask_notable_with_mock_llm():
    u = Universe("u_dialogue", 99)
    notable_id = list(u.notables.keys())[0]
    
    mock_llm = MockLLMClient(fixed_response="Par les vents sacrés, nos ancêtres guident mes pas.")
    reply = u.ask_notable(notable_id, "Qui es-tu et d'où viens-tu ?", llm_client=mock_llm)
    assert "Par les vents sacrés" in reply
    assert len(mock_llm.call_history) == 1
    # Vérifier le prompt système d'immersion
    history = mock_llm.call_history[0]
    system_prompt = history[0]["content"]
    assert "RÈGLES ABSOLUES D'INCARNATION" in system_prompt
    assert "DIRECTIVES D'IMMERSION TOTALE" in system_prompt


def test_ai_budget_caps_and_restrictions():
    budget = AIBudgetManager(max_total_calls=3, max_calls_per_tick=2)
    u = Universe("u_budget", 101, ai_budget=budget)
    notable_id = list(u.notables.keys())[0]

    # Appel 1
    rep1 = u.ask_notable(notable_id, "Bonjour 1")
    assert u.ai_budget.total_calls == 1

    # Appel 2 (même tick)
    rep2 = u.ask_notable(notable_id, "Bonjour 2")
    assert u.ai_budget.total_calls == 2

    # Appel 3 (même tick : dépasse max_calls_per_tick=2)
    rep3 = u.ask_notable(notable_id, "Bonjour 3")
    assert "sommeil" in rep3 or "accaparent" in rep3
    assert u.ai_budget.total_calls == 2

    # Avancer le tick
    u.step(1)
    # Appel 4 (tick différent, mais max_total_calls=3)
    rep4 = u.ask_notable(notable_id, "Bonjour 4")
    assert u.ai_budget.total_calls == 3

    # Appel 5 (bloqué car max_total_calls atteint)
    rep5 = u.ask_notable(notable_id, "Bonjour 5")
    assert u.ai_budget.total_calls == 3


def test_snapshot_preserves_notables_and_budget():
    u = Universe("u_save", 77)
    notable_id = list(u.notables.keys())[0]
    u.notables[notable_id].add_memory(10, 1, "Vision d'un aigle géant", impact=0.9)
    u.ask_notable(notable_id, "Un présage ?")
    calls_before = u.ai_budget.total_calls

    store = MemoryStore()
    store.save(u)
    loaded = store.load("u_save")

    assert loaded.ai_budget.total_calls == calls_before
    assert notable_id in loaded.notables
    assert any("aigle géant" in m.text for m in loaded.notables[notable_id].memories)
