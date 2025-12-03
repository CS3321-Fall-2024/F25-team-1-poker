import pytest
from unittest.mock import patch, AsyncMock
from app import app, lobbies

@pytest.fixture
def test_client():
    return app.test_client()

@pytest.mark.asyncio
async def test_index(test_client):
    response = await test_client.get("/")
    body = await response.get_data()
    assert response.status_code == 200
    assert b"<!DOCTYPE html>" in body  # your frontend page

@pytest.mark.asyncio
async def test_create_lobby(test_client):
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.__aenter__.return_value.json = AsyncMock(return_value={"deck_id": "deck123"})
        mock_get.return_value = mock_resp

        response = await test_client.post("/create_lobby")
        data = await response.get_json()
        assert "lobby_code" in data
        assert data["lobby_code"] in lobbies
        lobby = lobbies[data["lobby_code"]]
        assert lobby["deck_id"] == "deck123"
        assert lobby["players"] == []

@pytest.mark.asyncio
async def test_join_lobby_success(test_client):
    # Setup lobby
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.__aenter__.return_value.json = AsyncMock(return_value={"deck_id": "deck123"})
        mock_get.return_value = mock_resp
        resp = await test_client.post("/create_lobby")
        lobby_code = (await resp.get_json())["lobby_code"]

    response = await test_client.post("/join_lobby", json={
        "lobby_code": lobby_code,
        "player_name": "Alice"
    })
    data = await response.get_json()
    assert "Alice" in lobbies[lobby_code]["players"]
    assert data["message"] == f"Alice joined lobby {lobby_code}"

@pytest.mark.asyncio
async def test_join_lobby_errors(test_client):
    # Non-existent lobby
    response = await test_client.post("/join_lobby", json={
        "lobby_code": "fake",
        "player_name": "Bob"
    })
    assert response.status_code == 404

    # Duplicate player
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.__aenter__.return_value.json = AsyncMock(return_value={"deck_id": "deck123"})
        mock_get.return_value = mock_resp
        resp = await test_client.post("/create_lobby")
        lobby_code = (await resp.get_json())["lobby_code"]

    await test_client.post("/join_lobby", json={"lobby_code": lobby_code, "player_name": "Alice"})
    response = await test_client.post("/join_lobby", json={"lobby_code": lobby_code, "player_name": "Alice"})
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_start_game(test_client):
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp_new = AsyncMock()
        mock_resp_new.__aenter__.return_value.json = AsyncMock(return_value={"deck_id": "deck123"})
        mock_resp_draw = AsyncMock()
        mock_resp_draw.__aenter__.return_value.json = AsyncMock(return_value={"cards": ["card1", "card2"]})
        mock_get.side_effect = [mock_resp_new, mock_resp_draw, mock_resp_draw]

        resp = await test_client.post("/create_lobby")
        lobby_code = (await resp.get_json())["lobby_code"]

        await test_client.post("/join_lobby", json={"lobby_code": lobby_code, "player_name": "Alice"})
        await test_client.post("/join_lobby", json={"lobby_code": lobby_code, "player_name": "Bob"})

        response = await test_client.post("/start_game", json={"lobby_code": lobby_code})
        data = await response.get_json()
        assert data["message"] == "Game started"
        assert lobbies[lobby_code]["started"] is True
        for player in ["Alice", "Bob"]:
            assert lobbies[lobby_code]["hands"][player] == ["card1", "card2"]

@pytest.mark.asyncio
async def test_get_hand(test_client):
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.__aenter__.return_value.json = AsyncMock(return_value={"deck_id": "deck123"})
        mock_get.return_value = mock_resp
        resp = await test_client.post("/create_lobby")
        lobby_code = (await resp.get_json())["lobby_code"]

    await test_client.post("/join_lobby", json={"lobby_code": lobby_code, "player_name": "Alice"})
    # Manually add hand
    lobbies[lobby_code]["hands"]["Alice"] = ["card1", "card2"]

    response = await test_client.get("/get_hand/Alice")
    data = await response.get_json()
    assert data == ["card1", "card2"]

    response = await test_client.get("/get_hand/Bob")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_draw_card(test_client):
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp_new = AsyncMock()
        mock_resp_new.__aenter__.return_value.json = AsyncMock(return_value={"deck_id": "deck123"})
        mock_resp_draw = AsyncMock()
        mock_resp_draw.__aenter__.return_value.json = AsyncMock(return_value={"cards": ["card3"]})
        mock_get.side_effect = [mock_resp_new, mock_resp_draw]

        resp = await test_client.post("/create_lobby")
        lobby_code = (await resp.get_json())["lobby_code"]
        await test_client.post("/join_lobby", json={"lobby_code": lobby_code, "player_name": "Alice"})

        response = await test_client.post("/draw_card", json={"lobby_code": lobby_code, "player_name": "Alice"})
        data = await response.get_json()
        assert data["card_drawn"] == "card3"
        assert "card3" in lobbies[lobby_code]["hands"]["Alice"]

import pytest
from unittest.mock import AsyncMock, patch
from app import app, lobbies

@pytest.mark.asyncio
async def test_next_phase_route(test_client):
    # Mock aiohttp responses for flop, turn, river
    mock_flop = AsyncMock()
    mock_flop.__aenter__.return_value.json = AsyncMock(return_value={"cards": ["c1", "c2", "c3"]})
    mock_turn = AsyncMock()
    mock_turn.__aenter__.return_value.json = AsyncMock(return_value={"cards": ["c4"]})
    mock_river = AsyncMock()
    mock_river.__aenter__.return_value.json = AsyncMock(return_value={"cards": ["c5"]})

    with patch("aiohttp.ClientSession.get", side_effect=[mock_flop, mock_turn, mock_river]):
        # 1. Create a lobby manually
        lobby_code = "test123"
        lobbies[lobby_code] = {
            "deck_id": "deck123",
            "players": ["Alice"],
            "hands": {"Alice": []},
            "started": True,
            "state": "preflop",
            "community_cards": [],
            "current_player_index": 0
        }

        # preflop -> flop
        resp = await test_client.post("/next_phase", json={"lobby_code": lobby_code})
        data = await resp.get_json()
        assert data["state"] == "flop"
        assert data["community_cards"] == ["c1", "c2", "c3"]

        # flop -> turn
        resp = await test_client.post("/next_phase", json={"lobby_code": lobby_code})
        data = await resp.get_json()
        assert data["state"] == "turn"
        assert data["community_cards"] == ["c1", "c2", "c3", "c4"]

        # turn -> river
        resp = await test_client.post("/next_phase", json={"lobby_code": lobby_code})
        data = await resp.get_json()
        assert data["state"] == "river"
        assert data["community_cards"] == ["c1", "c2", "c3", "c4", "c5"]

        # river -> showdown
        resp = await test_client.post("/next_phase", json={"lobby_code": lobby_code})
        data = await resp.get_json()
        assert data["state"] == "showdown"
        assert data["community_cards"] == ["c1", "c2", "c3", "c4", "c5"]
