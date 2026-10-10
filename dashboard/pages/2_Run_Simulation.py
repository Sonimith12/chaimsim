"""Run Simulation page: execute a simulation with a progress bar.

Steps the loaded scenario's `chainsim.core.SimulationEngine` one period at
a time (via its public `begin()`/`step()`/`finish()` API — the same
stepping interface `chainsim.ai.gym_env.SupplyChainEnv` uses) so progress
can be shown live. Results are stored in `st.session_state` (via
`dashboard.state`) for the Results Dashboard and Compare Scenarios pages.
"""

from __future__ import annotations

import copy
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from chainsim.core import SimulationEngine
from chainsim.metrics import summarize
from state import RunRecord, add_run, get_runs, require_scenario_config  # noqa: E402

st.set_page_config(page_title="Run Simulation · chainsim", page_icon="📦", layout="wide")
st.title("2. Run Simulation")

bundle = require_scenario_config()
if bundle is not None:
    st.markdown(f"### Scenario: {bundle.name}")
    st.caption(bundle.description)

    col1, col2, col3 = st.columns(3)
    n_periods = col1.number_input("Periods", 1, 2000, bundle.n_periods)
    seed = col2.number_input("Seed", 0, 1_000_000, bundle.seed or 0)
    existing_labels = [r.label for r in get_runs()]
    default_label = bundle.name
    if default_label in existing_labels:
        default_label = f"{bundle.name} ({len(existing_labels) + 1})"
    label = col3.text_input("Run label", value=default_label)

    if st.button("Run simulation", type="primary"):
        # Each run gets its own independent copy of the network so that past
        # runs stay safe to inspect later regardless of what a later run does
        # to node/edge state — chainsim's own metrics functions only read
        # static topology off `network`, everything time-varying comes from
        # the returned `history` DataFrame, but this keeps that guarantee
        # robust even if the dashboard grows a feature that reads live state.
        run_network = copy.deepcopy(bundle.network)
        engine = SimulationEngine(
            network=run_network,
            demand=bundle.demand,
            policies=bundle.policies,
            disruptions=bundle.disruptions,
            n_periods=int(n_periods),
            seed=int(seed),
        )

        progress = st.progress(0.0, text="Starting…")
        engine.begin()
        update_every = max(1, int(n_periods) // 50)
        t0 = time.time()
        for t in range(int(n_periods)):
            engine.step(t)
            if t % update_every == 0 or t == int(n_periods) - 1:
                progress.progress((t + 1) / int(n_periods), text=f"Period {t + 1}/{n_periods}")
        history = engine.finish()
        progress.progress(1.0, text=f"Done in {time.time() - t0:.2f}s")

        add_run(
            RunRecord(
                label=label,
                history=history,
                network=run_network,
                n_periods=int(n_periods),
                seed=int(seed),
                source=bundle.name,
            )
        )
        st.success(f"Run **{label}** complete — {len(history)} rows of history recorded.")

        summary = summarize(history, run_network)
        st.markdown("#### Quick summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total cost", f"{summary['total_cost']:,.0f}")
        m2.metric("Fill rate", f"{summary['fill_rate']:.1%}")
        m3.metric("Service level", f"{summary['service_level']:.1%}")
        m4.metric("Total waste", f"{summary['total_waste']:,.0f}")
        st.caption("See the **Results Dashboard** page for the full breakdown.")

    runs = get_runs()
    if runs:
        st.divider()
        st.markdown(f"#### Completed runs ({len(runs)})")
        st.table(
            [
                {
                    "label": r.label,
                    "source": r.source,
                    "periods": r.n_periods,
                    "seed": r.seed,
                    "created": r.created_at.strftime("%H:%M:%S"),
                }
                for r in runs
            ]
        )
