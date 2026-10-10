"""Benchmarking and metrics layer: KPIs, scenario sweeps, and scenario comparisons.

Layer 3. Consumes the structured history log produced by
`chainsim.core.engine.SimulationEngine` and turns it into decision-useful
numbers.
"""

from chainsim.metrics.compare import compare as compare_scenarios
from chainsim.metrics.compare import summarize_sweep
from chainsim.metrics.kpis import (
    average_inventory,
    bullwhip_ratio,
    fill_rate,
    inventory_turns,
    per_node_kpis,
    service_level,
    summarize,
    total_backlog_cost,
    total_holding_cost,
    total_transportation_cost,
    total_waste,
)
from chainsim.metrics.sweep import ScenarioSweep

__all__ = [
    "ScenarioSweep",
    "average_inventory",
    "bullwhip_ratio",
    "compare_scenarios",
    "fill_rate",
    "inventory_turns",
    "per_node_kpis",
    "service_level",
    "summarize",
    "summarize_sweep",
    "total_backlog_cost",
    "total_holding_cost",
    "total_transportation_cost",
    "total_waste",
]
