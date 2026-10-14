"""Tests de conformité au plan d'émergence (étapes 1–2, mesures)."""
from engine.clock import SECONDS_PER_DAY
from engine.engine import Universe
from engine.experiment import leakage_test_prompt
from engine.immersion import ImmersionFilter, build_immersion_prompt
from engine.llm import ContextualPersonaGenerator
from engine.people import _BIBLICAL_M, _NEUTRAL_M


def test_seconds_per_day_matches_plan():
    assert SECONDS_PER_DAY == 0.5


def test_default_cultural_frame_is_neutral():
    u = Universe("test-neutral-frame", seed=11)
    assert u.cultural_frame == "neutral"
    assert u.start_year == 0
    names = {p.name for p in u.people.persons.values()}
    # Aucun prénom biblique pur hors suffixes (heuristique)
    assert not any(n in _BIBLICAL_M for n in names)
    assert any(any(n.startswith(base) for base in _NEUTRAL_M) for n in names)


def test_no_scripted_apple_oath():
    messages = [
        {"role": "system", "content": "Tu es Torun,\nTon titre / rôle : Habitant.\nAppartenance : Camp (Totem).\nTes liens du sang : seul\nl'an 0"},
        {"role": "user", "content": "« Ne mangez pas la pomme, c'est interdit »"},
    ]
    text = ContextualPersonaGenerator.generate_response(messages)
    assert "serment" not in text.lower()
    assert "pommes" not in text.lower() or "méditerai" in text.lower() or "usages" in text.lower()


def test_leakage_test_on_habitant_prompt():
    u = Universe("test-leak", seed=22)
    pid = next(iter(u.notables))
    person = u.people.persons[pid]
    msgs = build_immersion_prompt(person, u.notables[pid], u)
    result = leakage_test_prompt(msgs[0]["content"])
    assert result["passed"], result


def test_no_fixed_social_ranks_at_genesis():
    u = Universe("test-no-ranks", seed=33)
    assert u.justice.person_ranks == {} or all(
        v == "écarté du camp" for v in u.justice.person_ranks.values()
    )


def test_seasonal_metrics_fill_specialization():
    u = Universe("test-metrics-fill", seed=44)
    u.step(100)
    latest = u.metrics_history.get_latest()
    assert latest is not None
    assert "job_specialization_entropy" in latest
    assert "resource_variance" in latest
    assert "ai_calls_per_year" in latest


def test_anachronism_counter():
    ImmersionFilter.anachronism_hits = 0
    ImmersionFilter.anachronism_checks = 0
    assert ImmersionFilter.check_anachronism_trap("Nous forgerons le fer demain", year=0)
    assert ImmersionFilter.anachronism_rate() == 1.0
