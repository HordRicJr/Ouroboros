import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine.engine import Universe
from engine.society import Clan


@pytest.fixture
def test_universe():
    return Universe("test-society-u", seed=42)


def test_society_genesis(test_universe):
    u = test_universe
    soc = u.society
    assert len(soc.clans) > 0
    for clan in soc.clans.values():
        assert clan.id > 0
        assert len(clan.name) > 0
        assert len(clan.totem) > 0
        assert len(clan.member_ids) > 0
        assert clan.leader_id is not None
        assert clan.matriarch_id is not None
        assert clan.leader_id in u.people.persons
        assert clan.matriarch_id in u.people.persons
        # Les chefs doivent être notables
        assert u.people.persons[clan.leader_id].notable is True
        assert u.people.persons[clan.matriarch_id].notable is True
        assert len(clan.cosmogony) > 0
        assert len(clan.taboos) > 0


def test_person_clan_lookup(test_universe):
    u = test_universe
    soc = u.society
    p = u.people.alive_persons()[0]
    clan = soc.get_person_clan(p.id)
    assert clan is not None
    assert p.id in clan.member_ids


def test_clan_serialization():
    clan = Clan(
        id=1,
        name="Clan du Grand Cerf",
        totem="Grand Cerf",
        settlement_cell=(12, 14),
        territory_cells=[(12, 14), (12, 15)],
        leader_id=10,
        matriarch_id=11,
        member_ids=[10, 11, 12],
        cosmogony="Mythe fondateur ancien",
        taboos=["Interdit de couper le chêne"],
        culture_name="ancestrale",
        relations={2: 0.65},
        founded_year=5,
    )
    d = clan.to_dict()
    clan2 = Clan.from_dict(d)
    assert clan2.id == clan.id
    assert clan2.name == clan.name
    assert clan2.settlement_cell == clan.settlement_cell
    assert clan2.relations == clan.relations
    assert clan2.taboos == clan.taboos


def test_society_serialization_and_universe_snapshot(test_universe):
    u = test_universe
    snap = u.snapshot()
    u2 = Universe.from_snapshot(snap)

    assert len(u2.society.clans) == len(u.society.clans)
    clan_id = list(u.society.clans.keys())[0]
    assert u2.society.clans[clan_id].name == u.society.clans[clan_id].name
    assert u2.society.clans[clan_id].totem == u.society.clans[clan_id].totem
    assert u2.info()["clans_count"] == len(u2.society.clans)


def test_clan_leadership_succession(test_universe):
    u = test_universe
    soc = u.society
    clan = list(soc.clans.values())[0]
    old_leader_id = clan.leader_id
    assert old_leader_id is not None

    # Tuer le chef actuel
    u.people.persons[old_leader_id].death_tick = u.tick

    # Step de la société
    events = soc.step(u.tick, 1, u.people, u.eco, u.rng, u.world, is_new_year=False)
    assert clan.leader_id != old_leader_id
    assert clan.leader_id is not None
    assert u.people.persons[clan.leader_id].alive is True

    # Vérifier l'événement de succession
    leadership_evs = [e for e in events if e.type == "clan_leadership"]
    assert len(leadership_evs) > 0
    assert leadership_evs[0].payload["clan_id"] == clan.id


def test_universe_step_society_events(test_universe):
    u = test_universe
    # Avancer d'une année complète (365 jours) pour déclencher la dérive culturelle et diplomatique
    events = u.step(365)
    assert u.tick == 365
    assert len(events) > 0
    # Vérifier que le compteur de clans est présent dans info
    info = u.info()
    assert "clans_count" in info
    assert info["clans_count"] >= 1


def test_api_clans_endpoints():
    client = TestClient(app)
    # 1. Lister les clans
    res = client.get("/universes/main/clans")
    assert res.status_code == 200
    clans = res.json()
    assert isinstance(clans, list)
    assert len(clans) > 0
    first_clan = clans[0]
    assert "id" in first_clan
    assert "totem" in first_clan
    assert "population" in first_clan
    assert "leader_name" in first_clan

    # 2. Obtenir le détail d'un clan
    clan_id = first_clan["id"]
    res_detail = client.get(f"/universes/main/clans/{clan_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["id"] == clan_id
    assert "territory_cells" in detail
    assert "members" in detail
    assert "relations" in detail
    assert isinstance(detail["members"], list)

    # 3. Clan inexistant
    res_404 = client.get("/universes/main/clans/999999")
    assert res_404.status_code == 404
