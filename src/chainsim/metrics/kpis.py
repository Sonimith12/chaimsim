"""KPI calculations from simulation history: fill rate, inventory turns, bullwhip, service level.

Computes, from the engine's history log (the ``pandas.DataFrame`` returned
by :meth:`chainsim.core.engine.SimulationEngine.run`): fill rate,
inventory turns, average inventory, total holding + backlog + (optionally)
transportation cost, the bullwhip ratio (variance of orders placed /
variance of demand faced, per node), and service level (fraction of
periods without a stockout).

Two entry points cover most uses: :func:`per_node_kpis` for a full
per-node breakdown, and :func:`summarize` for the flat, network-wide
scalar dict that :class:`chainsim.metrics.sweep.ScenarioSweep` attaches to
each Monte Carlo replication row.
"""

from __future__ import annotations

import pandas as pd

from chainsim.core.network import SupplyChainNetwork


def _filter(history: pd.DataFrame, node_id: str | None) -> pd.DataFrame:
    return history if node_id is None else history[history["node_id"] == node_id]


def fill_rate(history: pd.DataFrame, node_id: str | None = None) -> float:
    """Fraction of total demand (external + downstream orders) fulfilled immediately.

    ``sum(fulfilled) / sum(period_demand)`` — a volume-weighted fill rate
    across the run. Returns ``1.0`` when there was no demand to fill.
    """
    df = _filter(history, node_id)
    demanded = df["period_demand"].sum()
    if demanded <= 0:
        return 1.0
    return float(df["fulfilled"].sum() / demanded)


def service_level(history: pd.DataFrame, node_id: str | None = None) -> float:
    """Fraction of periods ending with zero backlog (a cycle service level)."""
    df = _filter(history, node_id)
    if df.empty:
        return 1.0
    return float((df["backlog"] <= 0).mean())


def average_inventory(history: pd.DataFrame, node_id: str | None = None) -> float:
    """Mean on-hand inventory across the run."""
    df = _filter(history, node_id)
    return float(df["on_hand"].mean()) if not df.empty else 0.0


def inventory_turns(history: pd.DataFrame, node_id: str | None = None) -> float:
    """Units fulfilled per unit of average on-hand inventory (a throughput proxy
    for turns when a true cost-of-goods figure isn't available).
    """
    df = _filter(history, node_id)
    avg_inv = df["on_hand"].mean() if not df.empty else 0.0
    if not avg_inv:
        return float("nan")
    return float(df["fulfilled"].sum() / avg_inv)


def bullwhip_ratio(history: pd.DataFrame, node_id: str) -> float:
    """Variance of orders placed / variance of demand faced, for one node.

    Values > 1 indicate order-quantity variance amplification relative to
    the demand the node actually observed — the classic bullwhip signature.
    ``period_demand`` already combines external demand and downstream
    orders, whichever applies to this node.
    """
    df = _filter(history, node_id)
    demand_var = df["period_demand"].var(ddof=1)
    order_var = df["order_placed"].var(ddof=1)
    if not demand_var:
        return float("nan")
    return float(order_var / demand_var)


def total_holding_cost(history: pd.DataFrame, node_id: str | None = None) -> float:
    return float(_filter(history, node_id)["holding_cost"].sum())


def total_backlog_cost(history: pd.DataFrame, node_id: str | None = None) -> float:
    return float(_filter(history, node_id)["backlog_cost"].sum())


def total_waste(history: pd.DataFrame, node_id: str | None = None) -> float:
    return float(_filter(history, node_id)["waste"].sum())


def total_transportation_cost(
    history: pd.DataFrame, network: SupplyChainNetwork, node_id: str | None = None
) -> float:
    """Approximate transportation cost: each node-period's ``fulfilled`` quantity is
    assumed to travel over that node's outbound edge(s), at ``cost_per_unit``. A
    node with more than one successor uses the average ``cost_per_unit`` across
    its outbound edges (mirrors the engine's documented proportional shipment
    split for multi-successor nodes).
    """
    df = _filter(history, node_id)
    total = 0.0
    for nid, group in df.groupby("node_id"):
        successors = network.successors(nid)
        if not successors:
            continue
        total_cost_per_unit = sum(network.get_edge(nid, s.id).cost_per_unit for s in successors)
        avg_cost_per_unit = total_cost_per_unit / len(successors)
        total += group["fulfilled"].sum() * avg_cost_per_unit
    return float(total)


def per_node_kpis(history: pd.DataFrame, network: SupplyChainNetwork | None = None) -> pd.DataFrame:
    """Full KPI breakdown, one row per node, indexed by ``node_id``."""
    rows = []
    for node_id, group in history.groupby("node_id"):
        transport_cost = (
            total_transportation_cost(history, network, node_id) if network is not None else 0.0
        )
        holding = total_holding_cost(history, node_id)
        backlog = total_backlog_cost(history, node_id)
        rows.append(
            {
                "node_id": node_id,
                "avg_on_hand": average_inventory(history, node_id),
                "avg_backlog": float(group["backlog"].mean()),
                "fill_rate": fill_rate(history, node_id),
                "service_level": service_level(history, node_id),
                "inventory_turns": inventory_turns(history, node_id),
                "bullwhip_ratio": bullwhip_ratio(history, node_id),
                "total_holding_cost": holding,
                "total_backlog_cost": backlog,
                "total_transportation_cost": transport_cost,
                "total_waste": total_waste(history, node_id),
                "total_cost": holding + backlog + transport_cost,
            }
        )
    return pd.DataFrame(rows).set_index("node_id")


def summarize(history: pd.DataFrame, network: SupplyChainNetwork | None = None) -> dict[str, float]:
    """Reduce a full per-node-period history to a flat dict of network-wide scalar
    KPIs — the summary row :class:`chainsim.metrics.sweep.ScenarioSweep` attaches
    to each Monte Carlo replication.

    ``fill_rate``/``service_level`` are averaged over sink nodes (customer-facing,
    e.g. retailers) when ``network`` is given, since those are usually the metrics
    that matter most; without a network, they're averaged over every node instead.
    """
    per_node = per_node_kpis(history, network)
    if network is not None:
        sink_ids = [n.id for n in network.sinks() if n.id in per_node.index]
    else:
        sink_ids = list(per_node.index)
    sink_rows = per_node.loc[sink_ids] if sink_ids else per_node

    return {
        "total_cost": float(per_node["total_cost"].sum()),
        "total_holding_cost": float(per_node["total_holding_cost"].sum()),
        "total_backlog_cost": float(per_node["total_backlog_cost"].sum()),
        "total_transportation_cost": float(per_node["total_transportation_cost"].sum()),
        "total_waste": float(per_node["total_waste"].sum()),
        "fill_rate": float(sink_rows["fill_rate"].mean()),
        "service_level": float(sink_rows["service_level"].mean()),
        "avg_bullwhip_ratio": float(per_node["bullwhip_ratio"].mean(skipna=True)),
    }
