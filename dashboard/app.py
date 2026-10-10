"""chainsim dashboard entry point.

Run with: streamlit run dashboard/app.py

This app, and everything under dashboard/, only calls the public API of
`chainsim` (`chainsim.core`, `chainsim.metrics`, `chainsim.scenarios`) —
never reaches into its internals. All business logic lives in the
library; this layer handles presentation only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from state import get_runs, get_scenario_config  # noqa: E402

st.set_page_config(page_title="chainsim", page_icon="📦", layout="wide")

st.title("📦 chainsim dashboard")
st.markdown(
    "An interactive front end for **chainsim**, the supply chain simulation "
    "framework — build a network, run it, inspect the results, and compare "
    "scenarios, all backed by `chainsim.core` / `chainsim.metrics` / "
    "`chainsim.scenarios`."
)

st.markdown("### Workflow")
st.markdown(
    "1. **Build Scenario** — load one of chainsim's four pre-built scenarios, "
    "or configure a custom serial supply chain.\n"
    "2. **Run Simulation** — execute it and watch the run progress.\n"
    "3. **Results Dashboard** — inventory/backlog time series, KPI cards, and "
    "a network diagram for any completed run.\n"
    "4. **Compare Scenarios** — put two or more completed runs side by side."
)

st.markdown("### Session status")
col1, col2 = st.columns(2)

with col1:
    bundle = get_scenario_config()
    if bundle is None:
        st.info("No scenario configured yet.")
    else:
        st.success(f"Scenario configured: **{bundle.name}**")
        st.caption(bundle.description)

with col2:
    runs = get_runs()
    if not runs:
        st.info("No simulation runs yet.")
    else:
        st.success(f"{len(runs)} completed run(s):")
        for run in runs:
            st.caption(f"• {run.label} ({run.n_periods} periods, seed={run.seed})")

st.sidebar.success("Pick a page above to get started.")
