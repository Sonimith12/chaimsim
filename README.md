# chainsim

An open-source Python framework for simulating supply chain networks,
designed from the ground up to plug into modern AI/ML workflows — not just
a discrete-event simulator that happens to produce data.

> **Status:** early scaffolding (Phase 0). Domain logic is not implemented
> yet — see [docs/architecture.md](docs/architecture.md) for the full plan.

## Why

Existing tools each do one thing well — SupplyNetPy gives you flexible
topology, OR-Gym gives you an RL interface, ISOMORPH gives you forecasting
benchmarks, deepbullwhip gives you fast Monte Carlo simulation with real
datasets — but none combine arbitrary network simulation, a Gymnasium RL
interface, forecasting benchmarks, disruption modeling, and visualization
in a single framework. `chainsim` is the integration layer that does all of
it.

`chainsim` doesn't reinvent simulation, graph algorithms, or optimization —
it's built on [SimPy](https://simpy.readthedocs.io/), [NetworkX](https://networkx.org/),
[NumPy](https://numpy.org/), [Gymnasium](https://gymnasium.farama.org/), and
(optionally) [OR-Tools](https://developers.google.com/optimization). The
original contribution is the domain layer (nodes, edges, policies,
disruptions, demand), the benchmarking/metrics layer, and the AI/ML
interface layer on top of them.

## Architecture

```
┌─────────────────────────────────────┐
│  Layer 5: Dashboard (Streamlit)      │
├─────────────────────────────────────┤
│  Layer 4: AI/ML Interfaces           │  Gymnasium env, Forecaster protocol
├─────────────────────────────────────┤
│  Layer 3: Benchmarking & Metrics     │  KPIs, scenario sweeps, comparisons
├─────────────────────────────────────┤
│  Layer 2: Supply Chain Domain Layer  │  Nodes, Edges, Policies,
│                                       │  Disruptions, Demand, Perishables
├─────────────────────────────────────┤
│  Layer 1: Foundations               │  SimPy · NetworkX · OR-Tools ·
│                                       │  NumPy · Gymnasium
└─────────────────────────────────────┘
```

The core library (`src/chainsim/core`, `metrics`, `ai`) has zero dependency
on Streamlit or any UI code — it's fully usable from a plain Python script
or Jupyter notebook. See [docs/architecture.md](docs/architecture.md) for
the full phase-by-phase build plan.

## Installation

```bash
pip install -e ".[dev]"
```

Optional extras:

```bash
pip install -e ".[dashboard]"  # Streamlit + Plotly + PyVis
pip install -e ".[rl]"         # Stable-Baselines3, for the RL training example
pip install -e ".[opt]"        # OR-Tools, for optimization features
```

## Development

```bash
make test     # run the test suite
make lint      # ruff check
make format    # ruff format
```

## Project layout

```
src/chainsim/
├── core/        # Layer 2: domain layer (nodes, edges, policies, demand, disruptions, engine)
├── metrics/     # Layer 3: KPIs, scenario sweeps, comparisons
├── ai/          # Layer 4: Gymnasium env, forecaster protocol, baseline agents
├── scenarios/   # pre-built example scenarios
└── io/          # config schemas and YAML/JSON/CSV loaders

dashboard/       # Layer 5: Streamlit app, calls only chainsim's public API
examples/        # runnable scripts and notebooks, no Streamlit dependency
tests/
docs/
```

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
