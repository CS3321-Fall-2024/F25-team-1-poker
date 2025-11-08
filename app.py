from quart import Quart, request, jsonify
import aiohttp
import secrets

app = Quart(__name__)

lobbies = {}  # in-memory store | ERASED when server stops

DECK_API_BASE = "https://deckofcardsapi.com/api/deck"


@app.post("/create_lobby")
async def create_lobby():
    # Create a new shuffled deck
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{DECK_API_BASE}/new/shuffle/?deck_count=1") as resp:
            deck_data = await resp.json()

    lobby_code = secrets.token_hex(3)  # short readable code made of 6 hexadecimal characters. collisions possible as it's randomly generated
    lobbies[lobby_code] = {
        "deck_id": deck_data["deck_id"],
        "players": [],
        "hands": {},
        "started": False
    }

    return jsonify({"lobby_code": lobby_code})


@app.post("/join_lobby")
async def join_lobby():
    data = await request.json
    lobby_code = data.get("lobby_code")
    player = data.get("player")

    if lobby_code not in lobbies:
        return jsonify({"error": "Lobby not found"}), 404

    if player in lobbies[lobby_code]["players"]:
        return jsonify({"error": "Player already joined"}), 400

    lobbies[lobby_code]["players"].append(player)
    lobbies[lobby_code]["hands"][player] = []

    return jsonify({"message": f"{player} joined lobby {lobby_code}"})


@app.post("/start_game")
async def start_game():
    data = await request.json
    lobby_code = data.get("lobby_code")

    if lobby_code not in lobbies:
        return jsonify({"error": "Lobby not found"}), 404

    lobby = lobbies[lobby_code]
    lobby["started"] = True

    async with aiohttp.ClientSession() as session:
        # draw 2 cards per player
        for player in lobby["players"]:
            async with session.get(f"{DECK_API_BASE}/{lobby['deck_id']}/draw/?count=2") as resp:
                card_data = await resp.json()
            lobby["hands"][player] = card_data["cards"]

    return jsonify({"message": "Game started"})


@app.get("/get_hand/<player>")
async def get_hand(player):
    for lobby in lobbies.values():
        if player in lobby["hands"]:
            return jsonify(lobby["hands"][player])
    return jsonify({"error": "Player not found"}), 404


@app.post("/draw_card")
async def draw_card():
    data = await request.json
    lobby_code = data.get("lobby_code")
    player = data.get("player")

    lobby = lobbies.get(lobby_code)
    if not lobby:
        return jsonify({"error": "Lobby not found"}), 404

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{DECK_API_BASE}/{lobby['deck_id']}/draw/?count=1") as resp:
            card_data = await resp.json()

    lobby["hands"][player].extend(card_data["cards"])

    return jsonify({"card_drawn": card_data["cards"][0]})


if __name__ == "__main__":
    import hypercorn.asyncio
    import asyncio

    asyncio.run(hypercorn.asyncio.serve(app, config=hypercorn.Config()))
