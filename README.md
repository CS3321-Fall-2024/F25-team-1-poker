# F25-team-1-poker
 A poker game using Quart for the backend
 
 our API/backend: used to facilitate multiplayer lobbies
 
 utilized third-party app/API:  https://deckofcardsapi.com/
 
------------------------------------------

Repository needs tickets to describe the tasks being worked on and completed in order for the TA to grade.

Repository is public so keep that it mind and keep secrets secret.

This week, we'd like to accomplish:
1. flesh out front-end to make actual poker game with turns/declare a winner
2. make necessary additions to API/backend to facilitate #1
3. divvy up work so everyone can contribute. perhaps assign issues to specific people
4. make an issue for creating frontend tool that tests API (already resolved by commit 518df13)
5. fix join lobby post function saying the player's name is "none" (is it listing all players as "none" internally or just telling the player that in the return?)

------------------------------------------

https://f25-team-1-poker.onrender.com/ should run the main branch hosted on a remote server, automatically updated with each commit to main

------------------------------------------

## Running the Backend Locally

### **Prerequisites**
- Python 3.9+ installed
- `pip` available in your terminal

---

### **Install Dependencies**
```bash
pip install -r requirements.txt
```

---

### **Start the Server**
Run the Quart app using Hypercorn:

```bash
hypercorn app:app --reload
```

The server will start at:

```
http://127.0.0.1:8000
```

---

## Testing the API Endpoints

You can test using **curl**, **Postman**, or the **Thunder Client** extension in VSCode.

### **1. Create a Lobby**
```bash
curl -X POST http://127.0.0.1:8000/create_lobby
```

### **2. Join a Lobby**
```bash
curl -X POST http://127.0.0.1:8000/join_lobby \
  -H "Content-Type: application/json" \
  -d '{"lobby_code": "PUT_CODE_HERE", "player": "Alice"}'
```

### **3. Start the Game (Deal Cards)**
```bash
curl -X POST http://127.0.0.1:8000/start_game \
  -H "Content-Type: application/json" \
  -d '{"lobby_code": "PUT_CODE_HERE"}'
```

### **4. View a Player’s Hand**
```bash
curl http://127.0.0.1:8000/get_hand/Alice
```

### **5. Draw a Card**
```bash
curl -X POST http://127.0.0.1:8000/draw_card \
  -H "Content-Type: application/json" \
  -d '{"lobby_code": "PUT_CODE_HERE", "player": "Alice"}'
```

Replace `PUT_CODE_HERE` with the lobby code returned in step 1.

---

### **Notes**
- Game state is stored **in memory**, so restarting the server clears all lobbies.
- The `--reload` flag automatically restarts the server when code changes.
