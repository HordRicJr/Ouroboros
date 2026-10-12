"""Tests pour le module des Langues, Dialectes et Toponymie (M12)."""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine.engine import Universe
from engine.language import Language, LanguageRegistry
from engine.rng import Rng


@pytest.fixture
def rng():
    return Rng(42)


def test_language_syllable_and_words(rng):
    g = rng.gen("test-lang")
    lang = Language(
        id=1,
        name="Proto-Test",
        family_name="Testienne",
        consonants=["k", "t", "p", "m", "n", "s"],
        vowels=["a", "i", "u"],
        syllable_patterns=["CV", "CVC"],
        lexicon={},
    )
    syl = lang.generate_syllable(g)
    assert len(syl) in (2, 3)

    word = lang.generate_word(g, syllables_count=2)
    assert len(word) >= 4
    assert word[0].isupper()

    # Traduction d'un concept
    translated = lang.translate("feu", g)
    assert isinstance(translated, str)
    assert lang.translate("feu") == translated

    # Prénom
    pname = lang.generate_person_name("F", g)
    assert isinstance(pname, str)
    assert len(pname) > 2


def test_language_branching(rng):
    g = rng.gen("branch-lang")
    parent = Language(
        id=1,
        name="Mère",
        family_name="Ouroboréenne",
        consonants=["k", "t", "p", "m", "n", "s", "r"],
        vowels=["a", "i", "u", "e", "o"],
        syllable_patterns=["CV", "CVC"],
        lexicon={"soleil": "tala", "eau": "mira"},
    )
    dialect = parent.branch(2, "Fille", g)
    assert dialect.id == 2
    assert dialect.parent_lang_id == 1
    assert dialect.drift_count == 1
    assert "soleil" in dialect.lexicon


def test_language_registry_genesis_and_step(rng):
    reg = LanguageRegistry.genesis(rng)
    assert len(reg.languages) >= 1
    proto = reg.get_or_default(1)
    assert "soleil" in proto.lexicon
    assert "eau" in proto.lexicon

    # Step avec drift tous les 5 ans
    g = rng.gen("drift")
    evs = reg.step(tick=5 * 365, year=5, g=g)
    assert isinstance(evs, list)


def test_api_languages_endpoints():
    client = TestClient(app)
    # Lister les langues
    res = client.get("/universes/main/languages")
    assert res.status_code == 200
    langs = res.json()
    assert isinstance(langs, list)
    assert len(langs) >= 1
    first = langs[0]
    assert "name" in first
    assert "consonants" in first

    # Détail d'une langue
    lang_id = first["id"]
    res_det = client.get(f"/universes/main/languages/{lang_id}")
    assert res_det.status_code == 200
    assert res_det.json()["id"] == lang_id


def test_universe_snapshot_with_languages():
    u = Universe("lang-save-u", 123)
    snap = u.snapshot()
    u2 = Universe.from_snapshot(snap)
    assert len(u2.languages.languages) == len(u.languages.languages)
    assert u2.info()["languages_count"] == len(u.languages.languages)
