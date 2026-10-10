"""Shared session-state helpers for the dashboard pages.

This module (and everything else under `dashboard/`) only calls chainsim's
public API — `chainsim.core`, `chainsim.metrics`, and each
`chainsim.scenarios.<name>` module's `build_scenario()` — never internals.
All business logic (simulation, KPIs) lives in the library; this module
just gives the Streamlit pages a shared, typed way to pass a built scenario
and its run history between pages via `st.session_state`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from chainsim.core import (
    DemandGenerator,
    DisruptionEvent,
    ReplenishmentPolicy,
    SupplyChainNetwork,
)

CONFIG_KEY = "chainsim_scenario_config"
RUNS_KEY = "chainsim_runs"


@dataclass
class ScenarioBundle:
    """Everything needed to build and run a `chainsim.core.SimulationEngine`,
    assembled by the Build Scenario page (either from a pre-built
    `chainsim.scenarios` module or from the custom serial-chain builder).
    """

    name: str
    description: str
    network: SupplyChainNetwork
    demand: dict[str, DemandGenerator]
    policies: dict[str, ReplenishmentPolicy]
    disruptions: list[DisruptionEvent] = field(default_factory=list)
    n_periods: int = 52
    seed: int | None = 0


@dataclass
class RunRecord:
    """One completed simulation run, kept around for the Results Dashboard and
    Compare Scenarios pages.
    """

    label: str
    history: pd.DataFrame
    network: SupplyChainNetwork
    n_periods: int
    seed: int | None
    source: str
    created_at: datetime = field(default_factory=datetime.now)


def get_scenario_config() -> ScenarioBundle | None:
    return st.session_state.get(CONFIG_KEY)


def set_scenario_config(bundle: ScenarioBundle) -> None:
    st.session_state[CONFIG_KEY] = bundle


def get_runs() -> list[RunRecord]:
    return st.session_state.setdefault(RUNS_KEY, [])


def add_run(record: RunRecord) -> None:
    get_runs().append(record)


def clear_runs() -> None:
    st.session_state[RUNS_KEY] = []


def run_label(base: str, existing: list[RunRecord]) -> str:
    """A short, unique label for a new run: base name, deduplicated with a counter."""
    used = {r.label for r in existing}
    if base not in used:
        return base
    i = 2
    while f"{base} ({i})" in used:
        i += 1
    return f"{base} ({i})"


def require_scenario_config() -> ScenarioBundle | None:
    """Show a standard warning + return None if no scenario has been built yet,
    so every downstream page can guard on this the same way.
    """
    bundle = get_scenario_config()
    if bundle is None:
        st.warning("No scenario configured yet. Start on the **Build Scenario** page.")
        return None
    return bundle


def require_runs() -> list[RunRecord] | None:
    """Show a standard warning + return None if no simulation has been run yet."""
    runs = get_runs()
    if not runs:
        st.warning("No simulation runs yet. Run one on the **Run Simulation** page first.")
        return None
    return runs


def format_kpi_value(value: Any) -> str:
    """Render a summarize()/per_node_kpis() value for display: percentages for
    rates in [0, 1], thousands separators for larger numbers, else as-is.
    """
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)
