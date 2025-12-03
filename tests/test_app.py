import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from app import app, lobbies

# Fixtures

@pytest_asyncio.fixture(autouse=True)
async def clear_lobbies():
	# Reset memory for each test
	lobbies.clear()
	yield
	lobbies.clear()


@pytest_asyncio.fixture
async def test_client():
	test_client = app.test_client()
	return test_client


# mock helpers

def mock_draw_cards(count):
	return {
		"deck_id": "testdeck",
		"cards": [
			{"value": "ACE", "suit": "SPADES", "code": "AS"}
			for _ in range(count)
		]
	}


class MockResponse:
	def __init__(self, json_data):
		self._json_data = json_data

	async def json(self):
		return self._json_data


class MockSession:
	def __init__(self, response):
		self.response = response

	async def __aenter__(self):
		return self

	async def __aexit__(self, exc_type, exc, tb):
		pass

	async def get(self, url):
		# Detect how many cards based on URL
		if "count=3" in url:
			return MockResponse(mock_draw_cards(3))
		elif "count=2" in url:
			return MockResponse(mock_draw_cards(2))
		else:
			return MockResponse(mock_draw_cards(1))


# Tests

@patch("aiohttp.ClientSession", side_effect=lambda: MockSession(MockResponse(mock_draw_cards(1))))
async def test_create_lobby(mock_session, test_client):
	resp = await test_client.post("/create_lobby")
	json_data = await resp.get_json()

	assert "lobby_code" in json_data
	assert json_data["lobby_code"] in lobbies


@patch("aiohttp.ClientSession", side_effect=lambda: MockSession(MockResponse(mock_draw_cards(1))))
async def test_join_lobby(mock_session, test_client):
	# First create lobby
	resp = await test_client.post("/create_lobby")
	lobby_code = (await resp.get_json())["lobby_code"]

	# Join
	resp = await test_client.post("/join_lobby", json={
		"lobby_code": lobby_code,
		"player": "Alice"
	})

	json_data = await resp.get_json()
	assert "Alice" in lobbies[lobby_code]["players"]


@patch("aiohttp.ClientSession", side_effect=lambda: MockSession(MockResponse(mock_draw_cards(2))))
async def test_start_game(mock_session, test_client):
	resp = await test_client.post("/create_lobby")
	lobby_code = (await resp.get_json())["lobby_code"]

	# Join one player
	await test_client.post("/join_lobby", json={
		"lobby_code": lobby_code,
		"player": "Alice"
	})

	# Start game
	resp = await test_client.post("/start_game", json={"lobby_code": lobby_code})
	assert resp.status_code == 200

	assert len(lobbies[lobby_code]["hands"]["Alice"]) == 2


async def test_get_hand_not_found(test_client):
	resp = await test_client.get("/get_hand/Unknown")
	assert resp.status_code == 404


@patch("aiohttp.ClientSession", side_effect=lambda: MockSession(MockResponse(mock_draw_cards(1))))
async def test_draw_card(mock_session, test_client):
	resp = await test_client.post("/create_lobby")
	lobby_code = (await resp.get_json())["lobby_code"]

	await test_client.post("/join_lobby", json={
		"lobby_code": lobby_code,
		"player": "Alice"
	})

	resp = await test_client.post("/draw_card", json={
		"lobby_code": lobby_code,
		"player": "Alice"
	})

	json_data = await resp.get_json()
	assert "card_drawn" in json_data
	assert len(lobbies[lobby_code]["hands"]["Alice"]) == 1


@patch("aiohttp.ClientSession", side_effect=lambda: MockSession(MockResponse(mock_draw_cards(3))))
async def test_next_phase(mock_session, test_client):
	resp = await test_client.post("/create_lobby")
	lobby_code = (await resp.get_json())["lobby_code"]

	# Move to FLOP
	resp = await test_client.post("/next_phase", json={"lobby_code": lobby_code})
	json_data = await resp.get_json()

	assert json_data["state"] == "flop"
	assert len(json_data["community_cards"]) == 3
