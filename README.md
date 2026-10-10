# chainsim

**A rigorous supply chain simulator — and a game that makes you feel every stockout.**

`chainsim` is two things built on one engine:

- **A simulation framework** — an open-source Python library for modeling
  multi-echelon supply chain networks with pluggable AI/ML interfaces
  (Gymnasium RL environment, forecasting protocols, Monte Carlo sweeps,
  disruption modeling). Designed for researchers and practitioners who need
  reproducible results, not dashboards.
- **ChainSim 3D** — a game that puts you in the chair. Manage a supply chain
  in a 3D world where trucks crawl along their lead times, inventory stacks up
  on warehouse floors, and a port strike at period 14 can bankrupt you by
  period 22 if you picked the wrong response. Ten campaign levels. One budget.
  Zero safety net.

Both share the *same* simulation. The game layers rules on top — money, events,
scoring — while the library stays clean, scriptable, and dependency-light.

> **Status:** the simulation library is feature-complete (domain layer, metrics,
> AI/ML interfaces, pre-built scenarios, Streamlit dashboard). The game layer —
> campaign, sandbox, network editor, economy, decision events — is built on top
> of it. See [docs/architecture.md](docs/architecture.md) for the library's
> design.

---

## Two ways to use it

| | **As a simulator** | **As a game** |
|---|---|---|
| For | Researchers, OR/ML practitioners, students | Anyone who wants to learn supply chain by breaking one |
| Interface | Python API, notebooks, Streamlit dashboard | 3D browser app |
| You do | Build networks in code, sweep parameters, train agents | Make decisions under pressure and live with the consequences |
| Output | KPIs, DataFrames, scenario comparisons | A score, a cash balance, and the sinking feeling you should have pre-ordered |
| Needs | Python 3.11+ | Python 3.11+ and Node.js 20.19+ (or 22.12+) |

---

## The simulator

Model arbitrary multi-echelon networks — suppliers, manufacturers, distribution
centers, retailers — connected by transport links with configurable dynamics:

- **Replenishment policies:** order-up-to, (s, S), (R, Q), base-stock
- **Demand generators:** stationary, seasonal, trend, empirical
- **Disruptions:** node outages, capacity reductions, lead-time shocks, demand shocks
- **Perishability:** shelf life, batch expiry, and waste tracking
- **Metrics:** fill rate, service level, bullwhip ratio, inventory turns, total cost
- **AI/ML interfaces:** a Gymnasium environment for RL, a forecaster protocol,
  baseline agents for benchmarking
- **Pre-built scenarios:** Retail Replenishment, Pharma Cold Chain,
  Manufacturing JIT, Global Commodity Flow

```python
from chainsim.scenarios.retail_replenishment import build_scenario
from chainsim.metrics import summarize

config = build_scenario()
engine = config.build_engine()
history = engine.run()
print(summarize(history, engine.network))
```

Step through a run one period at a time with `engine.begin()` / `engine.step(t)`
/ `engine.finish()` — the same interface the game uses to drive the simulation.

Run any bundled scenario directly:

```bash
python -m chainsim.scenarios.retail_replenishment
python -m chainsim.scenarios.pharma_cold_chain
python -m chainsim.scenarios.manufacturing_jit
python -m chainsim.scenarios.global_commodity_flow
```

---

## The game — ChainSim 3D

You are the supply chain manager. Every number in the 3D world comes from the
simulation engine. The trucks are not decoration — they are carrying your
orders, and they are late.

### Campaign

Ten levels across four acts. Each one teaches you something by letting you fail
at it first.

| Act | Levels | What goes wrong |
|---|---|---|
| 1 — Learning the Ropes | 1–3 | Steady demand lulls you. Then the seasons hit. |
| 2 — Managing Complexity | 4–6 | A port strike. A budget that won't stretch. A global network with 14-period lead times. |
| 3 — Expert Mode | 7–9 | Pharma spoilage at 99% service targets. Three disruptions in a row. Running lean until lean breaks. |
| 4 — The Final Challenge | 10 | Build your own network from scratch. Serve four markets. Survive whatever the engine throws at you. |

Complete levels to unlock the next. Earn up to three stars per level. Progress
is saved in your browser. Clearing milestones unlocks extras: 8× fast-forward,
a demand-forecast overlay, per-node analytics, and a title you earned.

### Sandbox

Free play on any of the four pre-built scenarios, or on a blank map. Every
scenario opens in an **editor** first — drag nodes around, add suppliers and
DCs and retailers, draw connections, set demand patterns and policies. When
it looks right, hit Start. When it doesn't work, you'll know exactly which
decision was the wrong one.

### What makes it a game

**A real budget.** Revenue comes from fulfilled demand. Costs come from
everywhere: holding inventory, backlog penalties, transportation, ordering,
policy changes, and building new infrastructure. Cash is finite. Run out and
your company enters crisis mode. Stay at zero for five periods and it's
bankruptcy — game over, here's your report card.

**Decision events.** The simulation pauses. A card appears: *"Port congestion
at the Asian hub. Lead times from Supplier\_Asia increase by 8 periods. Do
you pre-order safety stock now ($3,000), reroute through Europe (higher unit
cost), or gamble it clears?"* Some events give you a countdown. All of them
change the actual network. Choose carefully — you'll see the consequences
play out in real time.

**Scoring and objectives.** A live score in the HUD. A letter grade at the end
(S through F, because some runs deserve an F). Objectives tied to service level,
fill rate, cost, and profit margin. Stars for meeting bonus targets. A history
of every run so you can see yourself getting better — or confirm that Level 8
is, in fact, unfair.

**Visible consequences.** Trucks crawl along edges at a speed proportional to
their lead time. Inventory cubes stack and unstack on warehouse floors. Demand
pulses ripple out of every retailer. Stockouts flash red. Money floats off
nodes — green when you earn it, red when you lose it. You don't read a table
to know things are going badly. You see it.

### Controls

| Action | How |
|---|---|
| Inspect a node | Click it — overview, financials, analytics (once unlocked) |
| Change a replenishment policy | Select a node → policy selector (costs $500) |
| Play / pause / step / speed | Top bar |
| Focus camera / reset view | Click a node / double-click the ground |
| Edit the network | Drag to move · toolbar to add nodes · Shift-click to connect · right-click to delete |

---

## Architecture

The library is the single source of truth for the simulation. The game never
reimplements it. Dependencies run one way: **frontend → backend → library**.

```
┌──────────────────────────────────────────────────────────────┐
│  frontend/   React 19 + TypeScript + React Three Fiber       │
│              Renders state, captures input — no sim logic    │
├──────────────────────────────────────────────────────────────┤
│  backend/    FastAPI + WebSocket                             │
│              Game rules: economy, scoring, events, campaign, │
│              network editor validation                       │
├──────────────────────────────────────────────────────────────┤
│  src/chainsim/   The simulator — this library, unchanged     │
│  Layers 1–4: foundations · domain · metrics · AI/ML          │
└──────────────────────────────────────────────────────────────┘
```

- `src/chainsim` has **zero dependency** on the game. It is fully usable on its
  own, and its test suite is independent.
- The backend imports the library, steps the engine one period at a time, and
  layers the game economy, scoring, and event system around it.
- With random events switched off and seed `0`, an unedited scenario produces
  identical results to calling the library directly — same inventory, same
  orders, same fill rate, same service level.

---

## Installation

### Library only

```bash
pip install -e ".[dev]"
```

Optional extras:

```bash
pip install -e ".[dashboard]"  # Streamlit + Plotly + PyVis
pip install -e ".[rl]"         # Stable-Baselines3 for the RL training example
pip install -e ".[opt]"        # OR-Tools for optimization features
pip install -e ".[examples]"   # matplotlib for example scripts
```

### Run the game

Two terminals — one for the backend, one for the frontend.

**Terminal 1 — backend** (from the repo root):

```bash
python -m venv .venv && source .venv/bin/activate   # once
cd backend
pip install -r requirements.txt                      # also installs chainsim from ..
uvicorn main:app --reload --port 8000
```

> `main.py` lives in `backend/`, so run `uvicorn` from that folder. From the
> repo root: `uvicorn main:app --app-dir backend --reload --reload-dir backend`.

**Terminal 2 — frontend:**

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The dev server proxies
`/api` and `/ws` to the backend on port 8000.

3D models are optional. The game renders colored placeholder shapes unless you
drop `.glb` files into `frontend/public/models/` (see the README there for
sources — [Kenney](https://kenney.nl/assets),
[Quaternius](https://quaternius.com), and
[Poly Haven](https://polyhaven.com/) all offer free CC0 assets).

---

## Project layout

```
src/chainsim/            # the simulation library
├── core/                # domain: nodes, edges, policies, demand, disruptions, engine
├── metrics/             # KPIs, scenario sweeps, comparisons
├── ai/                  # Gymnasium env, forecaster protocol, baseline agents
├── scenarios/           # pre-built example scenarios
└── io/                  # config schemas and YAML/JSON/CSV loaders

backend/                 # game server
├── main.py              # REST + WebSocket endpoints
├── sim_bridge.py        # wraps the engine for the game
├── economy.py           # cash, revenue, costs, crisis & bankruptcy
├── scoring.py           # score, objectives, grades
├── events.py            # decision events and their consequences
├── campaign.py          # the 10 campaign levels
└── network_spec.py      # editable network description + validation

frontend/                # game client
└── src/
    ├── scene/           # 3D world: nodes, edges, trucks, effects, camera
    ├── ui/              # HUD, inspector, editor, campaign screens, event cards
    ├── store/           # Zustand stores (UI state; sim mirrors the backend)
    └── hooks/           # WebSocket, game loop, editor and campaign actions

dashboard/               # Streamlit dashboard (library API only)
examples/                # runnable scripts and notebooks
tests/
docs/
```

---

## Development

```bash
make test      # library test suite (pytest)
make lint      # ruff check
make format    # ruff format
```

```bash
cd frontend && npx tsc -p . && npm run build   # typecheck + production build
```

---

## Why

Existing tools each do one thing well — SupplyNetPy gives you flexible
topology, OR-Gym gives you an RL interface, ISOMORPH gives you forecasting
benchmarks, deepbullwhip gives you fast Monte Carlo with real datasets — but
none combine arbitrary network simulation, a Gymnasium RL interface,
forecasting benchmarks, disruption modeling, and visualization in a single
framework.

`chainsim` is the integration layer. It is built on
[SimPy](https://simpy.readthedocs.io/),
[NetworkX](https://networkx.org/),
[NumPy](https://numpy.org/),
[Gymnasium](https://gymnasium.farama.org/), and (optionally)
[OR-Tools](https://developers.google.com/optimization). The original
contribution is the domain layer, the metrics and benchmarking layer, the
AI/ML interface layer — and a game that makes the same engine something you
can feel in your gut when the inventory hits zero.

---

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).