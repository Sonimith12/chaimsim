"""Compare Scenarios page: pick 2+ prior runs and view chainsim.metrics.compare output.

Renders `chainsim.metrics.compare_scenarios` and a per-node KPI breakdown
across the selected runs as charts (Plotly) and tables (Streamlit). Only
calls chainsim's public API.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from chainsim.metrics import compare_scenarios, per_node_kpis, summarize
from state import require_runs  # noqa: E402

st.set_page_config(page_title="Compare Scenarios · chainsim", page_icon="📦", layout="wide")
st.title("4. Compare Scenarios")

runs = require_runs()
if runs is not None:
    if len(runs) < 2:
        st.info("Run at least one more simulation to have something to compare.")
    else:
        labels = [r.label for r in runs]
        selected = st.multiselect("Runs to compare", labels, default=labels[: min(3, len(labels))])

        if len(selected) < 2:
            st.info("Pick at least 2 runs.")
        else:
            selected_runs = [r for r in runs if r.label in selected]

            st.markdown("### Overall comparison")
            results_by_scenario = {
                r.label: pd.DataFrame([summarize(r.history, r.network)]) for r in selected_runs
            }
            metrics = ["total_cost", "fill_rate", "service_level", "total_waste"]
            comparison = compare_scenarios(results_by_scenario, metrics=metrics)
            st.dataframe(comparison.round(3), width="stretch")

            mean_cols = [f"{m}_mean" for m in metrics]
            chart_data = comparison[mean_cols].reset_index()
            for metric, mean_col in zip(metrics, mean_cols, strict=True):
                fig = px.bar(chart_data, x="scenario", y=mean_col, title=metric)
                fig.update_layout(height=300)
                st.plotly_chart(fig, width="stretch")

            st.markdown("### Per-node KPIs, side by side")
            node_metric = st.selectbox(
                "Metric",
                [
                    "total_cost",
                    "avg_on_hand",
                    "avg_backlog",
                    "fill_rate",
                    "service_level",
                    "bullwhip_ratio",
                    "total_waste",
                ],
            )
            per_node_frames = []
            for r in selected_runs:
                table = per_node_kpis(r.history, r.network)[[node_metric]].rename(
                    columns={node_metric: r.label}
                )
                per_node_frames.append(table)
            side_by_side = pd.concat(per_node_frames, axis=1)
            st.dataframe(side_by_side.round(3), width="stretch")

            long_form = side_by_side.reset_index().melt(
                id_vars="node_id", var_name="run", value_name=node_metric
            )
            fig = px.bar(
                long_form,
                x="node_id",
                y=node_metric,
                color="run",
                barmode="group",
                title=f"{node_metric} by node",
            )
            st.plotly_chart(fig, width="stretch")
