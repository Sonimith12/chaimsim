"""ScenarioSweep: run parameter grids with Monte Carlo replications and collect tidy results.

Takes a scenario builder and a parameter grid (e.g. different lead times,
different policies), and runs every combination for a number of Monte
Carlo replications, collecting a tidy results ``DataFrame`` — one row per
``(parameter combination, replication)`` — with
:func:`chainsim.metrics.kpis.summarize`'s scalar KPIs attached.

**Performance note:** each replication runs a full, independent
:class:`~chainsim.core.engine.SimulationEngine` simulation; unlike a
purely array-based Monte Carlo model, the engine's per-period node
processing doesn't currently vectorize across replications, so a sweep's
cost scales linearly in ``len(param_grid combinations) * n_replications``.
Fine for the grid sizes here (single-digit combinations x ~100 reps);
batching replications is a natural future optimization if that changes.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from chainsim.core.engine import SimulationEngine
from chainsim.metrics.kpis import summarize


@dataclass
class ScenarioSweep:
    """Runs ``build`` over every combination in ``param_grid``, ``n_replications``
    times each, and collects a tidy results table.

    Uses common random numbers across the sweep: replication ``r`` always
    seeds its engine with ``base_seed + r``, regardless of which parameter
    combination is running. That pairs demand/lead-time draws across
    combinations for a lower-variance, apples-to-apples comparison (e.g.
    replication 3 sees the same demand realization whether it's running the
    baseline or a custom policy).

    Args:
        build: Given one parameter combination (a dict with one value per
            ``param_grid`` key), returns a freshly constructed, ready-to-run
            :class:`~chainsim.core.engine.SimulationEngine`. Its ``.seed`` is
            overwritten by the sweep before each replication.
        param_grid: Maps parameter name -> the values to try for it. The full
            Cartesian product of all parameters is run.
        n_replications: Monte Carlo replications per parameter combination.
        base_seed: Replication ``r`` uses seed ``base_seed + r``.
    """

    build: Callable[[dict[str, Any]], SimulationEngine]
    param_grid: Mapping[str, Iterable[Any]]
    n_replications: int = 100
    base_seed: int = 0

    def run(self) -> pd.DataFrame:
        """Run the full sweep and return the tidy results DataFrame."""
        keys = list(self.param_grid.keys())
        value_lists = [list(v) for v in self.param_grid.values()]
        rows: list[dict[str, Any]] = []

        for combo in itertools.product(*value_lists):
            params = dict(zip(keys, combo, strict=True))
            for rep in range(self.n_replications):
                engine = self.build(params)
                engine.seed = self.base_seed + rep
                history = engine.run()
                row: dict[str, Any] = {**params, "replication": rep}
                row.update(summarize(history, engine.network))
                rows.append(row)

        return pd.DataFrame(rows)
