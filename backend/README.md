# WHOP Backend

FastAPI backend for the WHOP Intelligent Decision Support System. Provides the authoritative game engine, forecast engine, LLM agent, and REST API.

## Requirements

- **Python 3.11+**
- pip (included with Python)

### Optional (for LLM features)

- **Ollama** (recommended on macOS, especially Apple Silicon): `brew install ollama`
- **llama.cpp** (GGUF models, tunable performance): `brew install llama.cpp`
- **vLLM** (best supported on Linux + NVIDIA/CUDA): `pip install vllm`
- Cloud APIs (Claude, OpenAI) require no local install — just API keys

## Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Install all dependencies
./venv/bin/pip install -r requirements.txt
```

### Key Python packages

| Package | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `pydantic` / `pydantic-settings` | Data models + config |
| `numpy` | Monte Carlo statistics |
| `httpx` | HTTP client for local LLM servers |
| `anthropic` | Anthropic Claude SDK |
| `openai` | OpenAI SDK |
| `pytest` | Test framework |

## Running

```bash
# Start the API server (with auto-reload for development)
./venv/bin/uvicorn main:app --reload --port 8000

# API docs available at:
#   http://localhost:8000/docs     (Swagger UI)
#   http://localhost:8000/redoc    (ReDoc)
```

The server listens on port 8000. The frontend dev server proxies `/api` requests here.

## Testing

```bash
# Run all 137 tests
./venv/bin/pytest tests/ -v

# Stop on first failure
./venv/bin/pytest tests/ -v -x

# Run specific test files
./venv/bin/pytest tests/test_full_game.py -v     # Full 24-round game simulation
./venv/bin/pytest tests/test_forecast.py -v      # Forecast engine (31 tests)
./venv/bin/pytest tests/test_api.py -v           # API endpoints (13 tests)
./venv/bin/pytest tests/test_agent.py -v         # LLM agent (29 tests)
./venv/bin/pytest tests/test_validator.py -v     # Rule enforcement
./venv/bin/pytest tests/test_step_arrivals.py -v # Arrivals step logic
./venv/bin/pytest tests/test_step_exits.py -v    # Exits step logic
./venv/bin/pytest tests/test_cost_calculator.py -v # Cost calculations
./venv/bin/pytest tests/test_events.py -v        # Event handling
./venv/bin/pytest tests/test_card_sequences.py -v # Card data integrity
```

### Test breakdown

| File | Tests | Coverage |
|---|---|---|
| `test_card_sequences.py` | 5 | Card data integrity, sums |
| `test_validator.py` | 8 | Rule enforcement (bed caps, transfers, staff) |
| `test_step_arrivals.py` | 8 | Arrivals processing, admit logic |
| `test_step_exits.py` | 6 | Exit routing, transfer creation |
| `test_cost_calculator.py` | 7 | Financial + quality cost computation |
| `test_events.py` | 7 | Event drawing, effects, duration ticking |
| `test_full_game.py` | 3 | Full 24-round simulation, deterministic replay |
| `test_forecast.py` | 31 | Lookahead, Monte Carlo, optimizer, metrics |
| `test_api.py` | 13 | HTTP endpoints, error handling, full game via API |
| `test_agent.py` | 29 | Prompt builder, output parser, LLM client, recommender |
| **Total** | **137** | |

## LLM Configuration

Copy `.env.example` to `.env` in the project root and configure:

```bash
# Provider: "none" | "ollama" | "llamacpp" | "vllm" | "claude" | "openai"
WHOP_LLM_PROVIDER=none
```

All settings use the `WHOP_` environment variable prefix.

### Local LLM providers

**Ollama** (recommended on macOS, especially Apple Silicon — easiest):
```bash
brew install ollama
ollama serve                           # start server (port 11434)
ollama pull llama3.1:8b                # download model (good default)
# Set in .env:
# WHOP_LLM_PROVIDER=ollama
# WHOP_OLLAMA_MODEL=llama3.1:8b
# WHOP_OLLAMA_BASE_URL=http://localhost:11434
```

**llama.cpp** (GGUF models, best hardware optimization):
```bash
brew install llama.cpp
# Download a GGUF model (e.g., from HuggingFace), then:
llama-server -m /path/to/model.gguf --port 8080
# For GPU acceleration on Mac:
llama-server -m /path/to/model.gguf --port 8080 --n-gpu-layers 99
# Set in .env:
# WHOP_LLM_PROVIDER=llamacpp
# WHOP_LLAMACPP_SERVER_URL=http://localhost:8080
```

**vLLM** (high-throughput batch inference; best supported on Linux + NVIDIA/CUDA):
```bash
pip install vllm
vllm serve meta-llama/Llama-3-8b-chat-hf --port 8000
# Set in .env:
# WHOP_LLM_PROVIDER=vllm
# WHOP_VLLM_SERVER_URL=http://localhost:8000
# WHOP_VLLM_MODEL=meta-llama/Llama-3-8b-chat-hf
```

### Cloud LLM providers

**Claude API**:
```bash
# Set in .env:
# WHOP_LLM_PROVIDER=claude
# WHOP_ANTHROPIC_API_KEY=sk-ant-...
# WHOP_ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

**OpenAI API**:
```bash
# Set in .env:
# WHOP_LLM_PROVIDER=openai
# WHOP_OPENAI_API_KEY=sk-...
# WHOP_OPENAI_MODEL=gpt-4o
```

## Module Structure

```
backend/
|-- main.py                    # FastAPI app entry point (CORS, routers, init_db)
|-- config.py                  # Pydantic BaseSettings (WHOP_ env prefix)
|-- requirements.txt
|-- models/
|   |-- enums.py               # DepartmentId, StepType, STEP_ORDER, EVENT_ROUNDS
|   |-- department.py          # DepartmentState, StaffState, TransferRequest
|   |-- game_state.py          # GameState, RoundCostEntry
|   |-- actions.py             # ArrivalsAction, ExitsAction, ClosedAction, StaffingAction
|   |-- cost.py                # CostConstants, COST_CONSTANTS singleton
|   |-- events.py              # EventCard, EventEffect, ActiveEvent
|   `-- recommendations.py     # Recommendation, ForecastResult, MonteCarloResult, etc.
|-- data/
|   |-- card_sequences.py      # All 24-round fixed card sequences
|   |-- event_pools.py         # 6 EventCards per department
|   |-- starting_state.py      # create_starting_state() factory
|   `-- flow_graph.py          # FLOW_GRAPH dict + can_transfer()
|-- engine/
|   |-- game_engine.py         # Orchestrator: create_game, process_*_step
|   |-- step_arrivals.py       # Step 1: process arrivals + admit decisions
|   |-- step_exits.py          # Step 2: process exits + create transfers
|   |-- step_closed.py         # Step 3: close/divert decisions
|   |-- step_staffing.py       # Step 4: extra staff + staff transfers
|   |-- step_paperwork.py      # Step 5: costs + tick events + advance round
|   |-- event_handler.py       # draw_events, apply_events, tick_events
|   |-- validator.py           # Rule enforcement + ValidationError
|   `-- cost_calculator.py     # Financial + quality cost computation
|-- forecast/
|   |-- lookahead.py           # Deterministic N-round simulation
|   |-- monte_carlo.py         # Monte Carlo for event uncertainty
|   |-- optimizer.py           # Candidate generation + 2-phase scoring
|   `-- metrics.py             # Utilization, bottlenecks, diversion ROI
|-- agent/
|   |-- __init__.py            # Exports: Recommender, LLMClient, LLMClientError
|   |-- llm_client.py          # Provider-agnostic LLM wrapper
|   |-- prompt_builder.py      # State + forecast -> structured prompts
|   |-- output_parser.py       # Parse LLM JSON -> action models
|   `-- recommender.py         # Orchestrator: optimizer + optional LLM
|-- api/
|   |-- routes_game.py         # Game lifecycle + step endpoints
|   |-- routes_forecast.py     # Forecast + optimize endpoints
|   `-- routes_recommend.py    # LLM recommendation endpoint
|-- db/
|   |-- schema.py              # SQL DDL for sessions, snapshots, actions
|   |-- database.py            # get_db(), init_db(), set_db_path()
|   `-- repository.py          # CRUD for game state + action audit log
`-- tests/                     # 137 tests (see above)
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/game/new` | Create new game session |
| `GET` | `/api/game/{id}/state` | Current game state |
| `POST` | `/api/game/{id}/step/event` | Process events (query: `?event_seed=N`) |
| `POST` | `/api/game/{id}/step/arrivals` | Submit arrival decisions (body: `ArrivalsAction`) |
| `POST` | `/api/game/{id}/step/exits` | Submit exit decisions (body: `ExitsAction`) |
| `POST` | `/api/game/{id}/step/closed` | Submit close/divert decisions (body: `ClosedAction`) |
| `POST` | `/api/game/{id}/step/staffing` | Submit staffing decisions (body: `StaffingAction`) |
| `POST` | `/api/game/{id}/step/paperwork` | Calculate costs, advance round |
| `GET` | `/api/game/{id}/history` | Cost history + totals |
| `GET` | `/api/game/{id}/forecast` | Monte Carlo forecast + metrics (query: `?horizon=N`) |
| `GET` | `/api/game/{id}/optimize` | Optimizer for current step (query: `?horizon=N&mc_sims=N`) |
| `GET` | `/api/game/{id}/recommend/{step}` | AI recommendation (step: arrivals/exits/closed/staffing) |

Error responses: `400` for validation errors, `404` for unknown game ID.
