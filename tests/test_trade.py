from starlette.testclient import TestClient

from api.main import app
from engine.engine import Universe
from engine.trade import TradeNetwork, TradeRoute


def test_trade_network_routes_and_expeditions():
    u = Universe("test_trade", seed=42)
    assert isinstance(u.trade, TradeNetwork)

    # Force a trade route between two settlements to test simulation & step
    settlements = list(u.settlements.settlements.values())
    if len(settlements) >= 2:
        s1, s2 = settlements[0], settlements[1]
        route = TradeRoute(
            id=1,
            name="Piste du Sel",
            from_settlement_id=s1.id,
            to_settlement_id=s2.id,
            from_clan_id=s1.clan_id,
            to_clan_id=s2.clan_id,
            distance=12.5,
            volume_traded=0.0,
            established_year=0,
            primary_good="Sel Gemme",
        )
        u.trade.routes[1] = route
        u.trade.next_route_id = 2

    # Step simulation by 30 days
    u.step(30)
    info = u.info()
    assert "trade_routes_count" in info
    assert "expeditions_count" in info

    # Persistence test
    snap = u.snapshot()
    restored = Universe.from_snapshot(snap)
    assert isinstance(restored.trade, TradeNetwork)
    assert len(restored.trade.routes) == len(u.trade.routes)
    assert len(restored.trade.expeditions) == len(u.trade.expeditions)


def test_trade_api_endpoint():
    client = TestClient(app)

    # Step main universe
    client.post("/universes/main/step", json={"days": 10})

    # Query trade endpoint
    res = client.get("/universes/main/trade")
    assert res.status_code == 200
    data = res.json()
    assert "routes" in data
    assert "expeditions" in data
    assert "clan_wealth" in data
    assert isinstance(data["routes"], list)
