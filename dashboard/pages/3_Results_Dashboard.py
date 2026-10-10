"""Results Dashboard page: time-series charts, KPI cards, and network graph visualization.

Plotly time-series charts (inventory, backlog, orders per node), the KPI
summary card row from `dashboard.components.kpi_cards`, a per-node KPI
table from `chainsim.metrics.per_node_kpis`, and the network graph from
`dashboard.components.network_graph` with a period slider. Only calls
chainsim's public API.
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from chainsim.metrics import per_node_kpis
from components.kpi_cards import render_kpi_cards  # noqa: E402
from components.network_graph import render_network_graph  # noqa: E402
from state import require_runs  # noqa: E402

st.set_page_config(page_title="Results Dashboard · chainsim", page_icon="📦", layout="wide")
st.title("3. Results Dashboard")

runs = require_runs()
if runs is not None:
    labels = [r.label for r in runs]
    selected_label = st.selectbox("Run", labels, index=len(labels) - 1)
    run = next(r for r in runs if r.label == selected_label)
    history, network = run.history, run.network

    st.markdown("### KPI summary")
    render_kpi_cards(history, network)

    st.markdown("### Time series")
    metric_options = [
        "on_hand",
        "backlog",
        "pipeline",
        "inventory_position",
        "order_placed",
        "fulfilled",
        "external_demand",
    ]
    node_ids = [n.id for n in network.nodes]
    c1, c2 = st.columns([1, 2])
    ts_metric = c1.selectbox("Metric", metric_options)
    ts_nodes = c2.multiselect("Nodes", node_ids, default=node_ids)
    filtered = history[history["node_id"].isin(ts_nodes)]
    fig = px.line(
        filtered,
        x="period",
        y=ts_metric,
        color="node_id",
        title=f"{ts_metric} over time",
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, width="stretch")

    st.markdown("### Network topology")
    g1, g2 = st.columns([1, 2])
    graph_metric = g1.selectbox(
        "Node size/color",
        ["on_hand", "backlog", "pipeline", "order_placed", "fulfilled"],
        key="graph_metric",
    )
    show_snapshot = g2.checkbox("Show a specific period instead of the run average")
    period = None
    if show_snapshot:
        period = st.slider("Period", 0, run.n_periods - 1, 0)
    st.plotly_chart(
        render_network_graph(network, history, metric=graph_metric, period=period),
        width="stretch",
    )

    st.markdown("### Per-node KPIs")
    st.dataframe(per_node_kpis(history, network).round(3), width="stretch")
