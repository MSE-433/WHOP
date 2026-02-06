# WHOP Frontend

React dashboard for playing a full 24-round Friday Night at the ER game in the browser. Connects to the WHOP backend API for game state, AI recommendations, and cost tracking.

## Requirements

- **Node.js 18+** and npm
- WHOP backend running on port 8000 (see `backend/README.md`)

## Setup

```bash
cd frontend
npm install
```

## Running

```bash
# Start the dev server (hot-reload enabled)
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

The Vite dev server proxies all `/api` requests to `http://localhost:8000` (the backend), so **both servers must be running**.

## Commands

```bash
npm run dev       # Start dev server (http://localhost:5173)
npm run build     # TypeScript check + production build (output: dist/)
npm run preview   # Serve production build locally
npm run lint      # ESLint check
```

## Tech Stack

| Library | Version | Purpose |
|---|---|---|
| React | 19 | UI framework |
| TypeScript | 5.9 | Type safety |
| Vite | 7 | Build tool + dev server |
| Zustand | 5 | State management |
| Recharts | 3 | Cost charts |
| Axios | 1 | HTTP client |
| Tailwind CSS | 4 | Styling (via `@tailwindcss/vite` plugin) |

## Module Structure

```
src/
|-- main.tsx                          # React createRoot entry point
|-- App.tsx                           # Start screen or game layout + overlays
|-- index.css                         # Tailwind v4 import
|-- types/
|   `-- game.ts                       # TS interfaces matching backend models
|-- utils/
|   |-- staffUtils.ts                 # Computed property helpers (coreIdle, totalIdle, etc.)
|   |-- timeMapping.ts               # Round -> clock time, EVENT_ROUNDS
|   |-- formatters.ts                # Currency formatting, department names/colors
|   `-- flowGraph.ts                  # Transfer route validation
|-- api/
|   `-- client.ts                     # Axios wrapper for all 12 backend endpoints
|-- store/
|   `-- gameStore.ts                  # Zustand store: state + recommendation + API actions
`-- components/
    |-- layout/
    |   |-- GameHeader.tsx            # Round/clock, step indicator pills, running costs
    |   `-- MainLayout.tsx           # CSS Grid: departments+chart (left), steps+AI (right)
    |-- departments/
    |   |-- DepartmentCard.tsx        # Color-coded card: beds, staff, waiting, events
    |   `-- DepartmentGrid.tsx       # 2-column responsive grid
    |-- stepper/
    |   |-- StepPanel.tsx             # Routes to correct form by current_step
    |   |-- EventView.tsx             # Read-only events + Continue button
    |   |-- ArrivalsForm.tsx          # Admit patients + accept transfers
    |   |-- ExitsForm.tsx             # Discharge + transfer routing
    |   |-- ClosedForm.tsx            # Close/open toggles + ER divert
    |   |-- StaffingForm.tsx          # Extra staff, returns, staff transfers
    |   `-- PaperworkView.tsx        # Cost breakdown + Next Round
    |-- ai/
    |   `-- AIPanel.tsx              # Source badge, reasoning, risk flags, candidates
    |-- costs/
    |   `-- CostChart.tsx            # Per-round bars + cumulative line chart
    `-- shared/
        `-- GameOverOverlay.tsx      # End-game summary modal
```

## How It Works

### Game Flow

1. Click **New Game** to create a session via `POST /api/game/new`
2. Each round has 6 steps displayed in the step indicator:
   - **Events** — read-only display, click Continue
   - **Arrivals** — choose how many waiting patients to admit per department
   - **Exits** — route exiting patients: discharge or transfer
   - **Close/Divert** — toggle department closed flags, ER diversion
   - **Staffing** — call extra staff, return idle extras, transfer staff
   - **Paperwork** — view cost breakdown, advance to next round
3. The **AI Panel** auto-fetches recommendations on decision steps
4. Each decision form has an **Apply AI Suggestion** button
5. The **Cost Chart** updates after each round's paperwork step
6. After round 24, the **Game Over** overlay shows final results

### State Management

- Single Zustand store (`gameStore.ts`) holds: `gameId`, `state` (GameState), `recommendation`, `loading`, `error`
- Each step submission: sets loading, calls API, updates state, clears recommendation, auto-fetches next recommendation
- `StaffState` computed properties (`core_idle`, `total_idle`, etc.) are NOT in the API JSON — computed client-side via `staffUtils.ts`

### API Proxy

Vite proxies `/api` to `http://localhost:8000` (configured in `vite.config.ts`). No CORS configuration needed in development.

### Tailwind CSS v4

Uses the `@tailwindcss/vite` plugin — no `tailwind.config.js` needed. Just `@import "tailwindcss"` in `index.css`. All styling uses Tailwind utility classes with a dark theme (gray-950 background, gray-100 text).

### Department Colors

| Department | Accent | Used In |
|---|---|---|
| Emergency | Red | Card border, text, background |
| Surgery | Blue | Card border, text, background |
| Critical Care | Purple | Card border, text, background |
| Step Down | Green | Card border, text, background |
