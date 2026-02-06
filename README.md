# WHOP - Workflow-guided Hospital Outcomes Platform

An Intelligent Decision Support System (IDSS) for the board game **"Friday Night at the ER"** (FNER). WHOP provides real-time decision support for managing a simulated 24-round (24-hour) ER scenario across 4 hospital departments, combining deterministic forecasting, Monte Carlo simulation, and optional LLM-powered recommendations.

CPSC 433 - Case Study 2

## Features

- **Game Engine** — Full rules-compliant state machine enforcing the 6-step round loop (Events, Arrivals, Exits, Close/Divert, Staffing, Paperwork) with 1:1 staff-to-patient binding, bed caps, transfer delays, and cost tracking
- **Forecast Engine** — Deterministic lookahead using known card sequences + Monte Carlo simulation for event uncertainty (P10/P50/P90 cost projections)
- **AI Optimizer** — Candidate action generation with 2-phase scoring (deterministic prune then MC refinement), ranking actions by expected total cost
- **LLM Agent** — Optional natural-language recommendations via Ollama, llama.cpp, vLLM, Claude API, or OpenAI API with automatic fallback to optimizer
- **Interactive Dashboard** — React frontend for playing a full 24-round game in the browser with department visualization, step-by-step forms, AI panel, and cost charts
- **137 Backend Tests** — Comprehensive test suite covering engine rules, forecasting, API endpoints, and agent logic

## Architecture

```
docker compose up
├── frontend   (nginx:alpine — serves React app + proxies /api → backend)
├── backend    (python:3.11 — FastAPI game engine, forecast, AI agent)
├── ollama     (optional — local LLM inference)
└── llamacpp   (optional — local LLM inference)

React 18 + TypeScript (frontend/)
        | /api/* → nginx reverse proxy
FastAPI + Python (backend/)
  |-- Game Engine (authoritative state machine)
  |-- Forecast Engine (deterministic lookahead + Monte Carlo)
  |-- LLM Agent (model-agnostic: Ollama/llama.cpp/vLLM/Claude/OpenAI)
  |-- SQLite database (persistent volume)
```

## Prerequisites

### Docker (recommended)

- **Docker** and **Docker Compose** (Docker Desktop includes both)

### Local development

- **Python 3.11+**
- **Node.js 18+** and npm
- **Git**

### Optional (for LLM-powered recommendations)

Install any **one** of these depending on your preferred LLM provider:

```bash
# Ollama (recommended on macOS, especially Apple Silicon)
brew install ollama
ollama serve                  # starts the Ollama server
ollama pull llama3.1:8b       # download a model (good default)

# llama.cpp (alternative local inference with GGUF models)
brew install llama.cpp
# Download a GGUF model, then:
llama-server -m /path/to/model.gguf --port 8080

# vLLM (high-throughput inference; best supported on Linux + NVIDIA/CUDA)
pip install vllm
vllm serve meta-llama/Llama-3-8b-chat-hf --port 8000
```

For cloud LLM providers, no brew install is needed — just set your API key in `.env`:
- **Claude API**: Get key from [console.anthropic.com](https://console.anthropic.com)
- **OpenAI API**: Get key from [platform.openai.com](https://platform.openai.com)

## Quick Start (Docker)

```bash
git clone <repo-url>
cd WHOP

# Copy and configure environment (optional — app works without LLM)
cp .env.example .env
# Edit .env if you want to enable an LLM provider

# Start the app
docker compose up --build

# With Ollama for local LLM recommendations (auto-pulls model from WHOP_OLLAMA_MODEL in .env)
docker compose --profile ollama up --build
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

> **Ollama note:** On first run, the `ollama-pull` service automatically downloads the model set in `WHOP_OLLAMA_MODEL` (default: `llama3`). This may take a few minutes depending on model size. The model is cached in a Docker volume so subsequent starts are instant. To manually pull a different model:
> ```bash
> docker compose exec ollama ollama pull llama3.1:8b
> ```

```bash
# Stop containers
docker compose down

# Rebuild and restart after code changes
docker compose up --build -d

# If you get stale network errors, clean up first then rebuild
docker compose down --remove-orphans
docker compose up --build -d

# Stop and remove volumes (database, Ollama models)
docker compose down -v

# Full cleanup — remove all images, build cache, and unused data
docker system prune -a
```

### Docker Compose profiles

LLM services are opt-in via profiles:

```bash
# App only (no LLM — optimizer still provides recommendations)
docker compose up

# App + Ollama
docker compose --profile ollama up

# App + llama.cpp
docker compose --profile llamacpp up

# App + both LLM servers
docker compose --profile ollama --profile llamacpp up
```

When using Docker, set container hostnames in `.env` instead of `localhost`:

| Setting | Local | Docker |
|---|---|---|
| `WHOP_OLLAMA_BASE_URL` | `http://localhost:11434` | `http://ollama:11434` |
| `WHOP_LLAMACPP_SERVER_URL` | `http://localhost:8080` | `http://llamacpp:8080` |

## Quick Start (Local Development)

### 1. Clone the repository

```bash
git clone <repo-url>
cd WHOP
```

### 2. Set up the backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
./venv/bin/pip install -r requirements.txt

# Run tests to verify everything works
./venv/bin/pytest tests/ -v
```

### 3. Set up the frontend

```bash
cd frontend
npm install
```

### 4. Configure LLM (optional)

```bash
# Copy the example env file
cp .env.example .env

# Edit .env to set your provider and credentials
```

See [LLM Configuration](#llm-configuration) below for details.

### 5. Run the application

Open **two terminals**:

```bash
# Terminal 1 — Backend API server
cd backend
./venv/bin/uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend dev server
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

## LLM Configuration

WHOP works without any LLM — the optimizer provides recommendations by default. To enable LLM-enhanced recommendations, create a `.env` file in the project root (see `.env.example`):

### Platform notes (recommended defaults)

- **macOS (Apple Silicon)**: use **Ollama** (easiest) or **llama.cpp** (GGUF models + tunable performance).
- **macOS (Intel)**: Ollama or llama.cpp usually works, but expect slower throughput.
- **Linux + NVIDIA GPU**: vLLM is a great option if you want higher throughput.

### Suggested model sizes (rule of thumb)

- **16GB+ unified memory**: an **8B** instruct model is a good default (e.g., `llama3.1:8b` in Ollama).
- **8GB unified memory**: prefer **3B–4B** models (e.g., `llama3.2:3b`) or smaller quantizations for GGUF.

```bash
# Provider: "none" | "ollama" | "llamacpp" | "vllm" | "claude" | "openai"
WHOP_LLM_PROVIDER=none

# --- Local providers (no API key needed) ---

# Ollama
WHOP_OLLAMA_MODEL=llama3.1:8b
WHOP_OLLAMA_BASE_URL=http://localhost:11434

# llama.cpp server
WHOP_LLAMACPP_SERVER_URL=http://localhost:8080

# vLLM server
WHOP_VLLM_SERVER_URL=http://localhost:8000
WHOP_VLLM_MODEL=meta-llama/Llama-3-8b-chat-hf

# --- Cloud providers (require API key) ---

# Anthropic Claude
WHOP_ANTHROPIC_API_KEY=
WHOP_ANTHROPIC_MODEL=claude-sonnet-4-20250514

# OpenAI
WHOP_OPENAI_API_KEY=
WHOP_OPENAI_MODEL=gpt-4o

# --- Shared settings ---
WHOP_LLM_TEMPERATURE=0.3
WHOP_LLM_MAX_TOKENS=2048
WHOP_LLM_TIMEOUT_SECONDS=30
```

### Provider Setup Guides

| Provider | Install | Start Server | Set In `.env` |
|---|---|---|---|
| Ollama | `brew install ollama` | `ollama serve` then `ollama pull llama3.1:8b` | `WHOP_LLM_PROVIDER=ollama` |
| llama.cpp | `brew install llama.cpp` | `llama-server -m model.gguf --port 8080` | `WHOP_LLM_PROVIDER=llamacpp` |
| vLLM | `pip install vllm` | `vllm serve <model> --port 8000` | `WHOP_LLM_PROVIDER=vllm` |
| Claude | None (uses `anthropic` SDK) | N/A (cloud) | `WHOP_LLM_PROVIDER=claude` + API key |
| OpenAI | None (uses `openai` SDK) | N/A (cloud) | `WHOP_LLM_PROVIDER=openai` + API key |

## Commands Reference

```bash
# --- Docker ---
docker compose up --build                            # Build and start app
docker compose up -d                                 # Start in background
docker compose --profile ollama up                   # Start with Ollama
docker compose --profile llamacpp up                 # Start with llama.cpp
docker compose --profile ollama --profile llamacpp up  # Start with both
docker compose down                                  # Stop containers
docker compose down -v                               # Stop and remove volumes (DB, Ollama models)
docker system prune -a                               # Remove all images, build cache, unused data
docker compose logs -f backend                       # Follow backend logs
docker compose logs -f frontend                      # Follow frontend logs

# --- Backend (local dev) ---
cd backend && ./venv/bin/pytest tests/ -v          # Run all 137 tests
cd backend && ./venv/bin/pytest tests/ -v -x        # Stop on first failure
cd backend && ./venv/bin/pytest tests/test_api.py   # Run API tests only
cd backend && ./venv/bin/uvicorn main:app --reload --port 8000  # Dev server

# --- Frontend (local dev) ---
cd frontend && npm run dev          # Dev server (http://localhost:5173)
cd frontend && npm run build        # Production build
cd frontend && npm run preview      # Preview production build
cd frontend && npm run lint         # ESLint check
```

## Project Structure

```
WHOP/
|-- docker-compose.yml               # Docker Compose (app + optional LLM services)
|-- .env.example                     # Configuration template
|-- .dockerignore                    # Docker build exclusions
|-- backend/
|   |-- Dockerfile                   # Python 3.11-slim image
|   |-- requirements-docker.txt      # Minimal deps (no torch/vllm/mlx)
|   |-- main.py                      # FastAPI app entry point
|   |-- config.py                    # Settings (DB, CORS, LLM providers)
|   |-- requirements.txt             # Full Python dependencies (local dev)
|   |-- models/                      # Pydantic data models
|   |-- data/                        # Card sequences, events, starting state
|   |-- engine/                      # Game engine (state machine + rules)
|   |-- forecast/                    # Lookahead, Monte Carlo, optimizer, metrics
|   |-- agent/                       # LLM client, prompt builder, recommender
|   |-- api/                         # REST API routes
|   |-- db/                          # SQLite database layer
|   |-- tests/                       # 137 tests
|   `-- venv/                        # Python virtual environment (local dev)
|-- frontend/
|   |-- Dockerfile                   # Multi-stage: Node build -> nginx:alpine
|   |-- nginx.conf                   # Static files + /api reverse proxy
|   |-- vite.config.ts               # Vite + React + Tailwind v4
|   |-- package.json
|   `-- src/
|       |-- types/game.ts            # TypeScript interfaces
|       |-- utils/                   # Staff utils, time mapping, formatters
|       |-- api/client.ts            # Axios API client
|       |-- store/gameStore.ts       # Zustand state management
|       `-- components/              # React components (24 files)
`-- Background_and_Design_Docs/      # Reference material (gitignored)
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/game/new` | Create new game |
| `GET` | `/api/game/{id}/state` | Get current game state |
| `POST` | `/api/game/{id}/step/event` | Process events |
| `POST` | `/api/game/{id}/step/arrivals` | Submit arrival decisions |
| `POST` | `/api/game/{id}/step/exits` | Submit exit decisions |
| `POST` | `/api/game/{id}/step/closed` | Submit close/divert decisions |
| `POST` | `/api/game/{id}/step/staffing` | Submit staffing decisions |
| `POST` | `/api/game/{id}/step/paperwork` | Calculate costs, advance round |
| `GET` | `/api/game/{id}/history` | Get cost history |
| `GET` | `/api/game/{id}/forecast` | Monte Carlo forecast + metrics |
| `GET` | `/api/game/{id}/optimize` | Optimizer for current step |
| `GET` | `/api/game/{id}/recommend/{step}` | AI recommendation |

## Game Rules Summary

The game simulates a 24-hour hospital shift across 4 departments:

| Department | Core Staff | Starting Patients | Beds |
|---|---|---|---|
| Emergency | 18 | 16 | 25 + hallway (unlimited) |
| Surgery | 6 | 4 | 9 (hard cap) |
| Critical Care | 13 | 12 | 18 (hard cap) |
| Step Down | 24 | 20 | 30 + hallway (unlimited) |

Each round follows 6 steps: **Events** (at rounds 6, 9, 12, 17, 21), **Arrivals** (admit waiting patients), **Exits** (discharge or transfer), **Close/Divert** (communication flags), **Staffing** (call/return extra staff), **Paperwork** (cost calculation).

Key rules:
- 1:1 staff-to-patient binding
- Transfers take 1 round (delay)
- Surgery and Critical Care have hard bed caps
- ER diversion costs $5,000 + $200 quality per diverted ambulance
- Card sequences are fixed (IDSS has perfect information); only events are uncertain

## License

This project is for educational purposes.
