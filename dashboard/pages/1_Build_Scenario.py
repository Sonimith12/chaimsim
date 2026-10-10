"""Build Scenario page: pick a pre-built scenario or configure a custom network.

Streamlit widgets for echelon count, per-node cost/capacity, demand type,
policy type, and disruptions; the built configuration is stored in
`st.session_state` (via `dashboard.state`) for the Run Simulation page.
Only calls chainsim's public API (`chainsim.core`, `chainsim.scenarios`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from chainsim.core import (
    DEFAULT_SKU,
    BaseStockPolicy,
    CapacityReduction,
    DemandShock,
    DistributionCenter,
    LeadTimeShock,
    NodeOutage,
    OrderUpTo,
    Retailer,
    RQPolicy,
    SeasonalDemand,
    StationaryDemand,
    Supplier,
    SupplyChainNetwork,
    TransportLink,
    TrendDemand,
    sSPolicy,
)
from chainsim.scenarios import (
    global_commodity_flow,
    manufacturing_jit,
    pharma_cold_chain,
    retail_replenishment,
)
from state import ScenarioBundle, get_scenario_config, set_scenario_config  # noqa: E402

st.set_page_config(page_title="Build Scenario · chainsim", page_icon="📦", layout="wide")
st.title("1. Build Scenario")

PREBUILT = {
    "Retail Replenishment": retail_replenishment,
    "Pharma Cold Chain": pharma_cold_chain,
    "Manufacturing JIT": manufacturing_jit,
    "Global Commodity Flow": global_commodity_flow,
}

mode = st.radio("Scenario source", ["Pre-built scenario", "Custom serial chain"], horizontal=True)

# =========================================================================
# Pre-built scenarios
# =========================================================================
if mode == "Pre-built scenario":
    choice = st.selectbox("Choose a scenario", list(PREBUILT.keys()))
    module = PREBUILT[choice]
    st.caption((module.__doc__ or "").strip().splitlines()[0])

    kwargs: dict = {}
    if module is manufacturing_jit:
        kwargs["line_policy"] = st.radio(
            "Line policy", ["jit", "buffered"], horizontal=True, help="See the module docstring."
        )

    if st.button("Load scenario", type="primary"):
        config = module.build_scenario(**kwargs)
        set_scenario_config(
            ScenarioBundle(
                name=config.name,
                description=config.description,
                network=config.network,
                demand=config.demand,
                policies=config.policies,
                disruptions=config.disruptions,
                n_periods=config.n_periods,
                seed=config.seed,
            )
        )
        st.success(f"Loaded **{config.name}** — go to **Run Simulation** next.")

# =========================================================================
# Custom serial chain
# =========================================================================
else:
    st.caption(
        "A Supplier -> DC -> ... -> Retailer chain (each node ships to exactly one "
        "successor). For branching or multi-source networks, see the pre-built scenarios."
    )

    n_echelons = st.slider("Number of echelons", 2, 6, 4)
    node_ids = (
        ["Supplier"]
        + [f"DC_{i}" for i in range(1, n_echelons - 1)]
        + (["Retailer"] if n_echelons > 1 else [])
    )

    st.markdown("#### Nodes")
    node_settings = []
    cols = st.columns(n_echelons)
    for i, node_id in enumerate(node_ids):
        with cols[i]:
            st.markdown(f"**{node_id}**")
            holding_cost = st.number_input(
                "Holding cost/unit", 0.0, 20.0, 1.0, key=f"hc_{i}", help="Per unit per period."
            )
            backlog_cost = (
                st.number_input("Backlog cost/unit", 0.0, 50.0, 5.0, key=f"bc_{i}")
                if i == n_echelons - 1
                else 0.0
            )
            has_capacity = st.checkbox("Limit capacity", key=f"cap_on_{i}")
            capacity = (
                st.number_input("Capacity/period", 1, 10_000, 200, key=f"cap_{i}")
                if has_capacity
                else None
            )
            node_settings.append(
                {
                    "id": node_id,
                    "holding_cost": holding_cost,
                    "backlog_cost": backlog_cost,
                    "capacity": capacity,
                }
            )

    st.markdown("#### Lead times")
    lead_times = []
    lt_cols = st.columns(n_echelons - 1) if n_echelons > 1 else []
    for i in range(n_echelons - 1):
        with lt_cols[i]:
            lead_times.append(
                st.number_input(f"{node_ids[i]} -> {node_ids[i + 1]}", 1, 60, 2, key=f"lt_{i}")
            )

    st.markdown("#### Demand (at the Retailer)")
    demand_type = st.selectbox("Demand type", ["Stationary", "Seasonal", "Trend"])
    if demand_type == "Stationary":
        mean = st.number_input("Mean demand", 1.0, 5000.0, 20.0)
        distribution = st.selectbox("Distribution", ["poisson", "normal"])
        std = (
            st.number_input("Std dev", 0.0, 1000.0, mean**0.5) if distribution == "normal" else 0.0
        )
    elif demand_type == "Seasonal":
        mean = st.number_input("Base demand", 1.0, 5000.0, 20.0)
        amplitude = st.number_input("Amplitude", 0.0, 5000.0, 8.0)
        period_length = st.number_input("Season length (periods)", 2, 260, 13)
        noise_std = st.number_input("Noise std", 0.0, 500.0, 2.0)
    else:
        mean = st.number_input("Base demand", 0.0, 5000.0, 10.0)
        trend = st.number_input("Trend per period", -100.0, 100.0, 0.5)
        noise_std = st.number_input("Noise std", 0.0, 500.0, 2.0)

    st.markdown("#### Replenishment policy (every non-source node)")
    policy_type = st.selectbox("Policy type", ["OrderUpTo", "(s, S)", "(R, Q)", "BaseStock"])
    if policy_type == "OrderUpTo":
        policy_S = st.number_input("S (order-up-to level)", 0.0, 100_000.0, float(mean) * 4)
    elif policy_type == "(s, S)":
        p1, p2 = st.columns(2)
        policy_s = p1.number_input("s (reorder point)", 0.0, 100_000.0, float(mean) * 2)
        policy_S = p2.number_input("S (order-up-to level)", 0.0, 100_000.0, float(mean) * 4)
    elif policy_type == "(R, Q)":
        p1, p2 = st.columns(2)
        policy_R = p1.number_input("R (reorder point)", 0.0, 100_000.0, float(mean) * 2)
        policy_Q = p2.number_input("Q (order quantity)", 0.1, 100_000.0, float(mean) * 2)
    else:
        p1, p2 = st.columns(2)
        bs_std = p1.number_input("Assumed demand std", 0.0, 5000.0, max(float(mean) ** 0.5, 1.0))
        bs_service_level = p2.slider("Target service level", 0.50, 0.999, 0.95)

    st.markdown("#### Disruptions")
    if "custom_disruptions" not in st.session_state:
        st.session_state["custom_disruptions"] = []

    edge_ids = [f"{node_ids[i]}->{node_ids[i + 1]}" for i in range(n_echelons - 1)]
    with st.form("add_disruption", clear_on_submit=True):
        d1, d2, d3, d4, d5 = st.columns(5)
        d_types = ["NodeOutage", "CapacityReduction", "LeadTimeShock", "DemandShock"]
        d_type = d1.selectbox("Type", d_types)
        if d_type == "LeadTimeShock":
            targets = edge_ids
        elif d_type == "CapacityReduction":
            targets = node_ids + edge_ids
        else:
            targets = node_ids
        d_target = d2.selectbox("Target", targets)
        d_start = d3.number_input("Start period", 0, 10_000, 10)
        d_duration = d4.number_input("Duration", 1, 1000, 4)
        d_magnitude = d5.number_input(
            "Factor/multiplier", 0.0, 20.0, 0.5, help="Ignored for NodeOutage."
        )
        if st.form_submit_button("Add disruption"):
            st.session_state["custom_disruptions"].append(
                {
                    "type": d_type,
                    "target": d_target,
                    "start": int(d_start),
                    "duration": int(d_duration),
                    "magnitude": d_magnitude,
                }
            )

    if st.session_state["custom_disruptions"]:
        st.table(st.session_state["custom_disruptions"])
        if st.button("Clear disruptions"):
            st.session_state["custom_disruptions"] = []
    else:
        st.caption("No disruptions added.")

    st.markdown("#### Run settings")
    r1, r2 = st.columns(2)
    n_periods = r1.number_input("Number of periods", 5, 1000, 52)
    seed = r2.number_input("Random seed", 0, 100_000, 0)

    if st.button("Build custom scenario", type="primary"):
        net = SupplyChainNetwork()
        for i, settings in enumerate(node_settings):
            if i == 0:
                node = Supplier(
                    id=settings["id"],
                    holding_cost=settings["holding_cost"],
                    capacity=settings["capacity"],
                    initial_inventory={DEFAULT_SKU: 1000},
                )
            elif i == n_echelons - 1:
                node = Retailer(
                    id=settings["id"],
                    holding_cost=settings["holding_cost"],
                    backlog_cost=settings["backlog_cost"],
                    capacity=settings["capacity"],
                    initial_inventory={DEFAULT_SKU: float(mean) * 2},
                )
            else:
                node = DistributionCenter(
                    id=settings["id"],
                    holding_cost=settings["holding_cost"],
                    capacity=settings["capacity"],
                    initial_inventory={DEFAULT_SKU: float(mean) * 2},
                )
            net.add_node(node)

        for i, lead_time in enumerate(lead_times):
            net.add_edge(
                TransportLink(source=node_ids[i], destination=node_ids[i + 1], lead_time=lead_time)
            )

        sink_id = node_ids[-1]
        if demand_type == "Stationary":
            demand = {sink_id: StationaryDemand(mean=mean, std=std, distribution=distribution)}
        elif demand_type == "Seasonal":
            demand = {
                sink_id: SeasonalDemand(
                    base=mean,
                    amplitude=amplitude,
                    period_length=int(period_length),
                    noise_std=noise_std,
                )
            }
        else:
            demand = {sink_id: TrendDemand(base=mean, trend_per_period=trend, noise_std=noise_std)}

        policies = {}
        cumulative_lead_time = 0
        for i, node_id in enumerate(node_ids[1:], start=1):
            cumulative_lead_time += lead_times[i - 1]
            if policy_type == "OrderUpTo":
                policies[node_id] = OrderUpTo(S=policy_S)
            elif policy_type == "(s, S)":
                policies[node_id] = sSPolicy(s=policy_s, S=policy_S)
            elif policy_type == "(R, Q)":
                policies[node_id] = RQPolicy(R=policy_R, Q=policy_Q)
            else:
                policies[node_id] = BaseStockPolicy(
                    mean_demand=mean,
                    std_demand=bs_std,
                    lead_time=lead_times[i - 1],
                    service_level=bs_service_level,
                )

        disruption_classes = {
            "NodeOutage": NodeOutage,
            "CapacityReduction": CapacityReduction,
            "LeadTimeShock": LeadTimeShock,
            "DemandShock": DemandShock,
        }
        disruptions = []
        for d in st.session_state["custom_disruptions"]:
            cls = disruption_classes[d["type"]]
            target, start, duration, magnitude = (
                d["target"],
                d["start"],
                d["duration"],
                d["magnitude"],
            )
            if cls is NodeOutage:
                disruptions.append(NodeOutage(target_id=target, start=start, duration=duration))
            elif cls is CapacityReduction:
                disruptions.append(
                    CapacityReduction(
                        target_id=target, start=start, duration=duration, factor=min(magnitude, 1.0)
                    )
                )
            elif cls is LeadTimeShock:
                disruptions.append(
                    LeadTimeShock(
                        target_id=target, start=start, duration=duration, multiplier=magnitude
                    )
                )
            else:
                disruptions.append(
                    DemandShock(
                        target_id=target, start=start, duration=duration, multiplier=magnitude
                    )
                )

        try:
            net.validate()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Invalid network: {exc}")
        else:
            set_scenario_config(
                ScenarioBundle(
                    name="Custom Serial Chain",
                    description=f"{n_echelons}-echelon custom chain: {' -> '.join(node_ids)}.",
                    network=net,
                    demand=demand,
                    policies=policies,
                    disruptions=disruptions,
                    n_periods=int(n_periods),
                    seed=int(seed),
                )
            )
            st.success("Custom scenario built — go to **Run Simulation** next.")

# =========================================================================
# Current configuration
# =========================================================================
bundle = get_scenario_config()
if bundle is not None:
    st.divider()
    st.markdown(f"### Current scenario: {bundle.name}")
    st.caption(bundle.description)
    st.write(
        f"**Nodes:** {', '.join(n.id for n in bundle.network.nodes)}  \n"
        f"**Edges:** {', '.join(e.id for e in bundle.network.edges)}  \n"
        f"**Periods:** {bundle.n_periods}  |  **Seed:** {bundle.seed}  |  "
        f"**Disruptions:** {len(bundle.disruptions)}"
    )
