# Contributing to chainsim

Thanks for considering a contribution. `chainsim` is being built in
phases — see [docs/architecture.md](docs/architecture.md) for where the
project currently stands and what's coming next.

## Setup

```bash
git clone <repo-url>
cd supply-chain-sim
pip install -e ".[dev]"
```

## Workflow

```bash
make test     # run the test suite (pytest)
make lint      # check code style (ruff check)
make format    # auto-format code (ruff format)
```

All checks should pass before opening a pull request.

## Coding conventions

- **Type hints** are required on all public functions and classes.
- **Docstrings** (Google or NumPy style) are required on every public
  class/method — this is a library other people build on top of;
  documentation quality matters for adoption.
- **Config objects** (scenario configs, node configs) should be
  `pydantic.BaseModel` subclasses so they can be loaded from YAML/JSON and
  validated automatically.
- Prefer composition over inheritance where reasonable, but ABCs are
  appropriate for the extension points users are expected to subclass:
  `Node`, `ReplenishmentPolicy`, `DemandGenerator`, `DisruptionEvent`,
  `Forecaster`.
- No `print()` in library code — use the `logging` module.
- Every new module in `core/`, `metrics/`, or `ai/` needs a corresponding
  test file in `tests/` before the next phase starts.
- Keep the dashboard free of business logic — it should only call
  `chainsim`'s public API and handle presentation.

## What NOT to build

- No custom discrete-event scheduler — use SimPy.
- No custom graph algorithms — use NetworkX.
- No custom optimization solver — wrap OR-Tools if/when needed.
- No custom RL algorithm — rely on Stable-Baselines3/RLlib as
  optional/example dependencies; the library only needs to expose a valid
  Gymnasium environment.
- Don't couple the dashboard to internal implementation details.
- Don't add heavy dependencies (PyTorch, TensorFlow) as core requirements
  — keep those optional, used only in example notebooks.

## Pull requests

- Keep PRs scoped to one phase/module where possible.
- Include or update tests for any behavior change.
- Update docstrings and, if relevant, `docs/architecture.md`.
