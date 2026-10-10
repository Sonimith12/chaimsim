# chainsim Architecture

This document mirrors the project brief that guides development. It is kept
in-repo so the architecture and phase plan stay next to the code.

## Vision

`chainsim` is an open-source Python framework for simulating supply chain
networks, designed from the ground up to plug into modern AI/ML workflows —
not just a discrete-event simulator that happens to produce data.

**The gap this fills:** existing tools each do one thing well (SupplyNetPy =
flexible topology, OR-Gym = RL interface, ISOMORPH = forecasting benchmarks,
deepbullwhip = fast Monte Carlo + real datasets), but none combine arbitrary
network simulation + a Gymnasium RL interface + forecasting benchmarks +
disruption modeling + visualization in one framework. `chainsim` is the
integration layer that does all of it.

**Design philosophy:** don't rebuild what already exists. Use SimPy,
NetworkX, NumPy, Gymnasium, and OR-Tools as foundations. The original
contribution is the domain layer (nodes, edges, policies, disruptions,
demand), the benchmarking/metrics layer, and the AI/ML interface layer on
top of them.

## Layered architecture (build bottom-up)

```
┌─────────────────────────────────────┐
│  Layer 5: Dashboard (Streamlit)      │  ← build LAST
├─────────────────────────────────────┤
│  Layer 4: AI/ML Interfaces           │  ← Gymnasium env, Forecaster protocol
├─────────────────────────────────────┤
│  Layer 3: Benchmarking & Metrics     │  ← KPIs, scenario sweeps, comparisons
├─────────────────────────────────────┤
│  Layer 2: Supply Chain Domain Layer  │  ← build FIRST — this is the core
│  (Nodes, Edges, Policies,            │
│   Disruptions, Demand, Perishables)  │
├─────────────────────────────────────┤
│  Layer 1: Foundations (dependencies) │
│  SimPy · NetworkX · OR-Tools ·       │
│  NumPy · Gymnasium                   │
└─────────────────────────────────────┘
```

Each layer is fully testable and usable on its own before the next one
starts. Layers 1-3 (the core library) have zero dependency on Streamlit or
any UI code — fully usable from a plain Python script or Jupyter notebook.

## Tech stack

- **Language:** Python 3.11+
- **Simulation engine:** SimPy (discrete-event simulation)
- **Graph representation:** NetworkX (supply chain topology as a directed graph)
- **Numerical computing:** NumPy (vectorized Monte Carlo)
- **RL interface:** Gymnasium (`reset()`, `step()`, `observation_space`, `action_space`, `reward`)
- **Optimization (optional, later phase):** OR-Tools
- **Data validation / config:** Pydantic v2
- **Dashboard:** Streamlit + Plotly (network viz via Plotly or PyVis)
- **Testing:** pytest
- **Packaging:** `pyproject.toml`, installable via `pip install -e .`
- **Type hints:** required throughout

## Phase plan

- **Phase 0 — Scaffolding** (done): project structure, `pyproject.toml`,
  ruff + pytest config, Makefile, placeholder README.
- **Phase 1 — Domain Layer Core** (done) (`core/`): nodes, edges, network,
  demand, policies, perishability, disruptions, engine. Deliverable:
  `examples/01_quickstart.py`.
- **Phase 2 — Benchmarking & Metrics** (done) (`metrics/`): KPIs, scenario
  sweeps, comparisons. Deliverable: `examples/02_custom_policy.py`.
- **Phase 3 — AI/ML Interfaces** (done) (`ai/`): Gymnasium env, forecaster
  protocol, baseline agents. Deliverables: `examples/03_rl_training.ipynb`,
  `examples/04_forecast_benchmark.ipynb`.
- **Phase 4 — Pre-built Scenarios** (done) (`scenarios/`): retail
  replenishment, pharma cold chain, manufacturing JIT, global commodity
  flow — each runnable via `python -m chainsim.scenarios.<name>`.
- **Phase 5 — Dashboard** (done) (`dashboard/`): Streamlit app calling only
  the public `chainsim` API. Run with `streamlit run dashboard/app.py`.

See the full project brief for detailed per-module responsibilities,
coding conventions, and what NOT to build.
