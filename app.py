from quart import Quart, request, jsonify
import aiohttp
import secrets
from quart import send_file

app = Quart(__name__)

# In-memory store for lobby data.
# NOTE: All data is erased when the server restarts.
lobbies = {}

# External card API base URL
DECK_API_BASE = "https://deckofcardsapi.com/api/deck"

@app.route("/")
async def index():
    # Serve the main HTML file
    return await send_file("index.html")


@app.post("/create_lobby")
async def create_lobby():
    # Create a new shuffled deck using the external API
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{DECK_API_BASE}/new/shuffle/?deck_count=1") as resp:
            deck_data = await resp.json()

    # Generate a short, random 6-char lobby code (hex)
    lobby_code = secrets.token_hex(3)

    # Initialize lobby data
    lobbies[lobby_code] = {
        "deck_id": deck_data["deck_id"],
        "players": [],
        "hands": {},
        "started": False,

        # Poker-related game state
        "state": "preflop",
        "community_cards": [],
        "current_player_index": 0,
    }

    return jsonify({"lobby_code": lobby_code})


@app.post("/join_lobby")
async def join_lobby():
    data = await request.json
    lobby_code = data.get("lobby_code")
    player = data.get("player_name")

    # Validate lobby
    if lobby_code not in lobbies:
        return jsonify({"error": "Lobby not found"}), 404

    # Prevent duplicate players
    if player in lobbies[lobby_code]["players"]:
        return jsonify({"error": "Player already joined"}), 400

    # Add player and give them an empty hand container
    lobbies[lobby_code]["players"].append(player)
    lobbies[lobby_code]["hands"][player] = []

    return jsonify({"message": f"{player} joined lobby {lobby_code}"})


@app.post("/start_game")
async def start_game():
    data = await request.json
    lobby_code = data.get("lobby_code")

    # Validate lobby
    if lobby_code not in lobbies:
        return jsonify({"error": "Lobby not found"}), 404

    lobby = lobbies[lobby_code]
    lobby["started"] = True

    # Deal 2 cards to each player using the API
    async with aiohttp.ClientSession() as session:
        for player in lobby["players"]:
            async with session.get(
                f"{DECK_API_BASE}/{lobby['deck_id']}/draw/?count=2"
            ) as resp:
                card_data = await resp.json()
            lobby["hands"][player] = card_data["cards"]

    return jsonify({"message": "Game started"})


@app.get("/get_hand/<player>")
async def get_hand(player):
    # Search all lobbies for player's hand
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

    # Draw a single card from deck
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{DECK_API_BASE}/{lobby['deck_id']}/draw/?count=1"
        ) as resp:
            card_data = await resp.json()

    # Add card to player’s hand
    lobby["hands"][player].extend(card_data["cards"])

    return jsonify({"card_drawn": card_data["cards"][0]})


@app.post("/next_phase")
async def next_phase():
    data = await request.json
    lobby_code = data.get("lobby_code")
    lobby = lobbies.get(lobby_code)

    state = lobby["state"]

    async with aiohttp.ClientSession() as session:

        # ---------- FLOP (draw 3) ----------
        if state == "preflop":
            async with session.get(
                f"{DECK_API_BASE}/{lobby['deck_id']}/draw/?count=3"
            ) as resp:
                data = await resp.json()
            lobby["community_cards"].extend(data["cards"])
            lobby["state"] = "flop"

        # ---------- TURN (draw 1) ----------
        elif state == "flop":
            async with session.get(
                f"{DECK_API_BASE}/{lobby['deck_id']}/draw/?count=1"
            ) as resp:
                data = await resp.json()
            lobby["community_cards"].extend(data["cards"])
            lobby["state"] = "turn"

        # ---------- RIVER (draw 1) ----------
        elif state == "turn":
            async with session.get(
                f"{DECK_API_BASE}/{lobby['deck_id']}/draw/?count=1"
            ) as resp:
                data = await resp.json()
            lobby["community_cards"].extend(data["cards"])
            lobby["state"] = "river"

        # ---------- SHOWDOWN ----------
        elif state == "river":
            lobby["state"] = "showdown"

    return jsonify({
        "state": lobby["state"],
        "community_cards": lobby["community_cards"]
    })


if __name__ == "__main__":
    # Run the Quart app using Hypercorn inside Python directly
    import hypercorn.asyncio
    import asyncio

    asyncio.run(hypercorn.asyncio.serve(app, config=hypercorn.Config()))
