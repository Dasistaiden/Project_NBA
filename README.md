# NBA Fantasy Draft Simulator

English | [繁體中文](README.zh-TW.md)

A draft-day decision tool for Yahoo Fantasy NBA: pulls league-wide player stats via `nba_api`, computes customizable Fantasy Points, and serves a multi-page Streamlit board — position rankings, side-by-side player comparison, an auction-draft optimizer (integer linear programming), and a player encyclopedia.

## Why

During a live draft you have seconds to weigh scattered information: stats, health, team role, upside. This tool consolidates it into one adjustable, comparable score so picks are backed by data instead of impressions.

## Features

- **Data pipeline** (`src/update_data.py`) — season-wide per-game stats and roster/position data for ~580 players, with request throttling and per-team retry; `src/backfill_history.py` backfills 21 seasons (2005-06 onward, ~10.6k rows) as training data. Idempotent upserts into SQLite.
- **Custom Fantasy Points** (`src/scoring.py`) — per-stat weights (PTS/REB/AST/STL/BLK/TOV/shooting) with sensible defaults, adjustable live in the sidebar to match your league's scoring.
- **Auction optimizer** (`src/auction.py`) — value-over-replacement price estimates for a $200 budget with an adjustable star-premium curve, plus an ILP solver (PuLP/CBC) that finds the best legal 13-man roster under budget and position-slot constraints (solves in under a second).
- **Next-season projections** (`src/projection.py`) — a Marcel-style baseline and per-stat gradient-boosting models trained on 21 seasons (2005-06 onward), validated by holdout backtesting (ML beats naive/Marcel on both MAE and rank correlation). Rankings and the auction page can switch between last-season actuals and 2026-27 projections.
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

15 tests covering scoring math (missing columns, NaN handling), upsert idempotency, position mapping, the optimizer's budget/slot constraints including infeasible cases, and the projection module (Marcel regression direction, team-change features, ML smoke test). The `nba_api` fetcher is validated by live spot-checks instead of mocks; projection accuracy is validated by holdout backtesting (`src/run_projection.py` prints the report).

## Known limitations

- Player positions are mapped from official NBA roster designations (G/F/C), which can differ from Yahoo's actual eligibility (e.g. Dončić maps to SG/SF vs Yahoo's PG/SG)
- 57 players who left their teams mid-season have no position mapping and are shown as `?`
- Injury status and media takes are manually maintained notes, not auto-scraped

## Roadmap (next updates)

- **Phase 2 — Health & role**: injury-risk index from three seasons of games-played history; refine role labels with starts/usage rate
- **Phase 3 — Rookies & intangibles**: NCAA-to-NBA production estimates for rookies; qualitative rating fields
- **Phase 4 — Draft-day assistant**: mark drafted players, live best-available suggestions, interactive auction simulation

See [02_planning.md](02_planning.md) for details.

## Design docs

Full planning docs (value proposition → planning → requirements → architecture → process log → living code index) are at the repo root, files `01_*.md` – `06_*.md` (Traditional Chinese). Start at [`06_index.md`](06_index.md).
