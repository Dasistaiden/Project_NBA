# NBA Fantasy Draft Simulator

A draft-day decision tool for Yahoo Fantasy NBA: pulls league-wide player stats via `nba_api`, computes customizable Fantasy Points, and serves a multi-page Streamlit board — position rankings, side-by-side player comparison, an auction-draft optimizer (integer linear programming), and a player encyclopedia.

## Why

During a live draft you have seconds to weigh scattered information: stats, health, team role, upside. This tool consolidates it into one adjustable, comparable score so picks are backed by data instead of impressions.

## Features

- **Data pipeline** (`src/update_data.py`) — season-wide per-game stats and roster/position data for ~580 players, with request throttling and per-team retry; backfills prior seasons (2023-24, 2024-25) for trend context. Idempotent upserts into SQLite.
- **Custom Fantasy Points** (`src/scoring.py`) — per-stat weights (PTS/REB/AST/STL/BLK/TOV/shooting) with sensible defaults, adjustable live in the sidebar to match your league's scoring.
- **Auction optimizer** (`src/auction.py`) — value-over-replacement price estimates for a $200 budget, plus an ILP solver (PuLP/CBC) that finds the best legal 13-man roster under budget and position-slot constraints (solves in under a second).
- **Streamlit app** (`app/`):
  1. Draft board — rankings across PG/SG/SF/PF/C with last-season averages as evidence
  2. Player comparison — 2–4 players side by side, per-stat better/worse highlighting (turnovers inverted)
  3. Mock auction — price table + optimal-roster solver
  4. Player encyclopedia — photos, multi-season stats, role heuristics, and manual scouting notes (`config/player_notes.yaml`)

## Quickstart

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# Fetch current + historical season data (idempotent)
.venv\Scripts\python.exe src\update_data.py

# Launch the board
.venv\Scripts\python.exe -m streamlit run app\draft_board.py
```

Season, weights, position mapping, and auction settings live in `config/config.yaml`.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

10 tests covering scoring math (missing columns, NaN handling), upsert idempotency, position mapping, and the optimizer's budget/slot constraints including infeasible cases. The `nba_api` fetcher is validated by live spot-checks instead of mocks.

## Design docs

Full planning docs (value proposition → planning → requirements → architecture → process log → living code index) are at the repo root, files `01_*.md` – `06_*.md` (Traditional Chinese). Start at [`06_index.md`](06_index.md).
