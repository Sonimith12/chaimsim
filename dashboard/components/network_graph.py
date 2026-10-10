"""Plotly network visualization component for the dashboard.

Renders a `chainsim.core.network.SupplyChainNetwork` topology as an
interactive graph, laid out left-to-right by echelon depth, with node
color/size mapped to a selected metric from a run's history. Only calls
chainsim's public API (`network.graph`, `.topological_order()`,
`.predecessors()` are all public attributes/methods of
`SupplyChainNetwork`).
"""

from __future__ import annotations

from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go

from chainsim.core import SupplyChainNetwork


def _layered_positions(network: SupplyChainNetwork) -> dict[str, tuple[float, float]]:
    """Left-to-right layout: x = depth (longest path from a source), y = spread
    among same-depth nodes, centered.
    """
    depth: dict[str, int] = {}
    for node in network.topological_order():
        preds = network.predecessors(node.id)
        depth[node.id] = 0 if not preds else max(depth[p.id] for p in preds) + 1

    by_depth: dict[int, list[str]] = defaultdict(list)
    for node_id, d in depth.items():
        by_depth[d].append(node_id)

    positions: dict[str, tuple[float, float]] = {}
    for d, node_ids in by_depth.items():
        n = len(node_ids)
        for i, node_id in enumerate(node_ids):
            positions[node_id] = (float(d), i - (n - 1) / 2)
    return positions


def render_network_graph(
    network: SupplyChainNetwork,
    history: pd.DataFrame,
    metric: str = "on_hand",
    period: int | None = None,
) -> go.Figure:
    """Build a Plotly figure of `network`'s topology, sized/colored by `metric`
    (a column of `history`, e.g. ``"on_hand"``, ``"backlog"``, ``"order_placed"``).

    Args:
        period: If given, use that period's value per node; otherwise the
            mean over the whole run.
    """
    positions = _layered_positions(network)
    snapshot = history[history["period"] == period] if period is not None else history
    values = snapshot.groupby("node_id")[metric].mean().to_dict()

    node_ids = [n.id for n in network.nodes]
    node_x = [positions[nid][0] for nid in node_ids]
    node_y = [positions[nid][1] for nid in node_ids]
    node_vals = [values.get(nid, 0.0) for nid in node_ids]
    vmin, vmax = min(node_vals, default=0.0), max(node_vals, default=0.0)
    sizes = [22 + 38 * (v - vmin) / (vmax - vmin + 1e-9) for v in node_vals]

    fig = go.Figure()

    annotations = []
    for edge in network.edges:
        x0, y0 = positions[edge.source]
        x1, y1 = positions[edge.destination]
        fig.add_trace(
            go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line={"width": 1.5, "color": "#9aa5b1"},
                hoverinfo="text",
                text=f"{edge.source} -> {edge.destination}<br>lead time: {edge.base_lead_time}"
                if not callable(edge.base_lead_time)
                else f"{edge.source} -> {edge.destination}",
                showlegend=False,
            )
        )
        annotations.append(
            {
                "ax": x0,
                "ay": y0,
                "x": x0 + 0.82 * (x1 - x0),
                "y": y0 + 0.82 * (y1 - y0),
                "xref": "x",
                "yref": "y",
                "axref": "x",
                "ayref": "y",
                "showarrow": True,
                "arrowhead": 2,
                "arrowsize": 1.2,
                "arrowwidth": 1.5,
                "arrowcolor": "#9aa5b1",
            }
        )

    period_label = f"period {period}" if period is not None else "run average"
    hover_pairs = zip(node_ids, node_vals, strict=True)
    hovertext = [f"{nid}<br>{metric} ({period_label}): {v:.1f}" for nid, v in hover_pairs]
    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_ids,
            textposition="bottom center",
            hovertext=hovertext,
            hoverinfo="text",
            marker={
                "size": sizes,
                "color": node_vals,
                "colorscale": "Blues",
                "showscale": True,
                "colorbar": {"title": metric},
                "line": {"width": 1.5, "color": "#334155"},
            },
            showlegend=False,
        )
    )

    fig.update_layout(
        annotations=annotations,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        title=f"Network topology — node size/color = {metric} ({period_label})",
        height=450,
    )
    return fig
