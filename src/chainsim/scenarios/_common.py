"""Shared scaffolding for the pre-built scenario modules in this package.

Not part of the public API (leading underscore) — each scenario module
(`retail_replenishment`, `pharma_cold_chain`, `manufacturing_jit`,
`global_commodity_flow`) builds a :class:`ScenarioConfig`, then uses
:func:`run_scenario` and :func:`print_scenario_report` to run it and print a
standard KPI report before adding its own scenario-specific narrative.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from chainsim.core.demand import DemandGenerator
from chainsim.core.disruptions import DisruptionEvent
from chainsim.core.engine import SimulationEngine
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.policies import ReplenishmentPolicy
from chainsim.metrics.kpis import per_node_kpis, summarize


@dataclass
class ScenarioConfig:
    """A fully configured, ready-to-run scenario.

    Attributes:
        name: Short scenario name, printed in the report header.
        description: One-paragraph summary of what the scenario exercises.
        network: The topology to simulate.
        demand: Maps node id -> demand generator.
        policies: Maps node id -> replenishment policy.
        disruptions: Disruption events to apply during the run.
        n_periods: Episode length in periods.
        seed: Seed for demand generation and stochastic lead times.
    """

    name: str
    description: str
    network: SupplyChainNetwork
    demand: dict[str, DemandGenerator]
    policies: dict[str, ReplenishmentPolicy]
    disruptions: list[DisruptionEvent] = field(default_factory=list)
    n_periods: int = 52
    seed: int | None = 0

    def build_engine(self) -> SimulationEngine:
        return SimulationEngine(
            network=self.network,
            demand=self.demand,
            policies=self.policies,
            disruptions=self.disruptions,
            n_periods=self.n_periods,
            seed=self.seed,
        )


def run_scenario(config: ScenarioConfig) -> tuple[SimulationEngine, pd.DataFrame]:
    """Build and run a scenario's engine, returning it alongside its history."""
    engine = config.build_engine()
    history = engine.run()
    return engine, history


def print_scenario_report(
    config: ScenarioConfig, engine: SimulationEngine, history: pd.DataFrame
) -> None:
    """Print the standard header + per-node KPI table + network summary every
    scenario shares; each scenario's ``main()`` follows this with its own
    scenario-specific narrative.
    """
    print(f"=== {config.name} ===")
    print(config.description)
    print(f"({config.n_periods} periods, seed={config.seed})\n")

    table = per_node_kpis(history, engine.network)
    print(table.round(3).to_string())

    print("\nNetwork summary:")
    for key, value in summarize(history, engine.network).items():
        print(f"  {key}: {value:,.3f}" if isinstance(value, float) else f"  {key}: {value}")
