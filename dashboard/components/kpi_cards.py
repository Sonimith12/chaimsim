"""KPI summary card component for the dashboard.

Renders the KPIs computed by `chainsim.metrics.kpis.summarize` as a row of
Streamlit metric cards. Only calls chainsim's public API.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from chainsim.core import SupplyChainNetwork
from chainsim.metrics import summarize


def render_kpi_cards(history: pd.DataFrame, network: SupplyChainNetwork) -> None:
    """Render a two-row summary of `chainsim.metrics.summarize(history, network)`."""
    summary = summarize(history, network)

    row1 = st.columns(4)
    row1[0].metric("Total cost", f"{summary['total_cost']:,.0f}")
    row1[1].metric("Fill rate", f"{summary['fill_rate']:.1%}")
    row1[2].metric("Service level", f"{summary['service_level']:.1%}")
    row1[3].metric("Total waste", f"{summary['total_waste']:,.0f}")

    row2 = st.columns(4)
    row2[0].metric("Holding cost", f"{summary['total_holding_cost']:,.0f}")
    row2[1].metric("Backlog cost", f"{summary['total_backlog_cost']:,.0f}")
    row2[2].metric("Transportation cost", f"{summary['total_transportation_cost']:,.0f}")
    bullwhip = summary["avg_bullwhip_ratio"]
    row2[3].metric("Avg bullwhip ratio", "n/a" if pd.isna(bullwhip) else f"{bullwhip:.2f}")
