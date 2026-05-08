# Ratzon — Intent Execution Layer for Solana

> Say what you want. Ratzon finds the best route and executes it on Solana.

**Built for:** Colosseum Frontier Hackathon × Superteam Georgia × Tether QVAC Track

---

## Architecture

```
User (Telegram / Web)
        │
        ▼
┌───────────────────────────────────────┐
│           RATZON INTENT LAYER         │
│                                       │
│  ┌─────────────┐  ┌────────────────┐  │
│  │ Regex Parser│  │  QVAC LLM      │  │
│  │  (fast)     │→ │  (intelligent) │  │
│  └─────────────┘  └────────────────┘  │
│         │                │            │
│         └────────────────┘            │
│                  │                    │
│         ┌────────▼────────┐           │
│         │ Intent Dispatcher│           │
│         └────────┬────────┘           │
│                  │                    │
│    ┌─────────────┼──────────────┐     │
│    ▼             ▼              ▼     │
│ Jupiter API  Risk Engine  Formatter   │
└───────────────────────────────────────┘
        │
        ▼
  Response to user
```

## QVAC Integration

Ratzon integrates QVAC as its AI backbone:

| Component | QVAC Module | Purpose |
|-----------|-------------|---------|
| LLM Parser | `@qvac/sdk` (Llama 3.2 1B) | Understands complex/ambiguous intents |
| Speech-to-Text | `@qvac/sdk` (Whisper) | Voice input in Telegram & Web |

**Why QVAC?**
- Local-first: user messages never leave the server
- No API keys or cloud costs for AI
- Works offline — true sovereignty

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 22.17+
- npm 10.9+

### 1. Clone and setup

```bash
git clone https://github.com/yourusername/ratzon
cd ratzon
```

### 2. Start QVAC service

```bash
cd qvac_service
npm install
node server.js
# Runs on http://localhost:3000
# First run downloads AI models (~1GB)
```

### 3. Start Python bot

```bash
cp .env.example .env
# Add your BOT_TOKEN to .env
# Set WEB_APP_URL to your public HTTPS frontend URL for Telegram Mini App buttons

pip install -r requirements.txt
python -m bot.main
# Bot + API server on port 8080
# Frontend starts automatically on http://localhost:4000
```

### 4. Start frontend manually (optional)

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:4000
```

Set `START_FRONTEND_WITH_BOT=false` if you want to run the frontend as a separate process.

### Telegram Mini App / Railway

`/start` can show a Telegram WebApp button, but Telegram does not auto-open a Mini App from a command. The user must tap the button or use the bot menu button.

For Railway, set these variables on the bot service:

```bash
BOT_TOKEN=...
WEB_APP_URL=https://your-frontend.up.railway.app
START_FRONTEND_WITH_BOT=true
FRONTEND_HOST=0.0.0.0
# Leave FRONTEND_PORT empty on Railway so the app uses Railway's PORT automatically.
FRONTEND_MODE=auto
```

If the frontend is deployed as a separate Railway service, set `WEB_APP_URL` to that frontend service URL. If the bot starts the frontend in the same service, use that service's public Railway URL.

Do not set `BOT_API_PORT` to Railway's public `PORT` when the bot starts the frontend in the same service. The bot will move its internal API to a free localhost port automatically.

If the frontend is deployed as a separate Railway service, set `BOT_API_URL` on that frontend service to the bot service URL, for example Railway's private service URL plus the bot API port.

The included `nixpacks.toml` installs both Python and frontend dependencies, builds Next.js, and starts the bot with `python -m bot.main`. In Railway/production, the bot starts the built frontend with `next start`; locally it keeps using `next dev`.

### Or: Docker Compose (все сервисы одной командой)

```bash
cp .env.example .env
# Add BOT_TOKEN

docker-compose up
```

---

## What it does

### Supported intents

| User says | Ratzon does |
|-----------|-------------|
| `Swap 1 SOL to USDC` | Live Jupiter quote + risk score |
| `Buy 1000 BONK` | Swap SOL → BONK |
| `I want to exchange my solana for stable` | LLM parses → Swap SOL → USDC |
| `Price of BONK` | Live price from Jupiter |
| `Compare SOL and JUP` | Side-by-side price comparison |
| `Rate SOL to USDC` | Current exchange rate |
| 🎤 Voice message | Whisper STT → intent → execution |

### What's real vs demo

| Feature | Status |
|---------|--------|
| Intent parsing (regex + LLM) | ✅ Real |
| Jupiter live quotes | ✅ Real |
| Risk engine | ✅ Real |
| QVAC LLM parser | ✅ Real |
| QVAC Whisper STT | ✅ Real |
| Transaction signing | 🎭 Demo |

---

## Project Structure

```
ratzon/
├── bot/                    # Python Telegram bot
│   ├── main.py             # Entry point (bot + API server)
│   ├── api_server.py       # HTTP API for frontend
│   ├── handlers/           # aiogram handlers
│   ├── intents/            # Parser (regex + QVAC LLM)
│   │   ├── parser.py       # Hybrid parser
│   │   └── llm_parser.py   # QVAC LLM client
│   ├── services/           # Business logic
│   ├── solana/             # Jupiter integration
│   └── risk/               # Risk engine
│
├── qvac_service/           # Node.js QVAC AI service
│   ├── server.js           # HTTP server
│   ├── intent_parser.js    # LLM intent parsing
│   └── stt.js              # Speech-to-text
│
├── frontend/               # Next.js web app
│   └── src/
│       ├── app/            # Pages + API routes
│       └── components/     # UI components
│
├── docker-compose.yml
└── README.md
```

---

## Try it

**Telegram:** @Ratzon_bot

**Web:** Coming soon

---

## Built with

- Python · aiogram · aiohttp
- Jupiter Aggregator V6 API
- QVAC SDK (Llama 3.2 1B + Whisper)
- Next.js · TailwindCSS
- Solana
