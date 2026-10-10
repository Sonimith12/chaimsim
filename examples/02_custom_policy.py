"""Define a custom replenishment policy and sweep it against a baseline OrderUpTo policy.

The Phase 2 deliverable: exercises the metrics layer (`chainsim.metrics`)
end to end — KPIs, a Monte Carlo `ScenarioSweep`, and a side-by-side
`compare` table — while also showing how easy it is to subclass
`ReplenishmentPolicy` with custom ordering logic (see CONTRIBUTING.md).

Scenario: a Supplier -> Store chain facing *seasonal* demand. The baseline
policy is tuned once, up front, from the demand's long-run mean/std (what
a practitioner typically does without a live simulator to iterate on). The
custom `AdaptiveOrderUpTo` policy instead tracks an exponentially-smoothed
demand forecast online, updating its target stock level every period
instead of assuming the long-run average always applies.

Both policies are swept across 3 lead-time settings x 100 Monte Carlo
replications each (600 simulation runs total), using common random
numbers so each replication's demand realization is shared across every
policy/lead-time combination for a fair comparison.

Worth calling out honestly: sweeping this, the adaptive policy does *not*
convincingly beat the baseline here — it runs a few percent more
expensive on average, worsening as lead time grows (see the printed table
and the note after it for why). That is itself the point of having a
sweep + KPI layer: it lets you find out whether a "smarter"-sounding
policy actually earns its complexity, instead of assuming it does.

Run with: `python examples/02_custom_policy.py`
"""

from __future__ import annotations

import math

from chainsim.core import (
    DEFAULT_SKU,
    BaseStockPolicy,
    NodeState,
    ReplenishmentPolicy,
    Retailer,
    SeasonalDemand,
    SimulationEngine,
    Supplier,
    SupplyChainNetwork,
    TransportLink,
    norm_ppf,
)
from chainsim.metrics import compare_scenarios, summarize_sweep
from chainsim.metrics.sweep import ScenarioSweep

N_PERIODS = 104  # 8 seasonal cycles
LEAD_TIMES = [1, 3, 6]
N_REPLICATIONS = 100
SERVICE_LEVEL = 0.95

# Seasonal demand: an 13-period cycle (e.g. quarterly-ish) swinging +/- 8
# around a base of 20, plus a little period-to-period noise.
DEMAND_BASE, DEMAND_AMPLITUDE, DEMAND_PERIOD, DEMAND_NOISE = 20.0, 8.0, 13, 2.0


class AdaptiveOrderUpTo(ReplenishmentPolicy):
    """Order-up-to policy whose target level is recomputed every period from an
    exponentially-smoothed demand forecast, instead of one fixed, hand-tuned
    `S` (compare to `chainsim.core.policies.BaseStockPolicy`, which is static).

    Uses the same newsvendor-style formula as `BaseStockPolicy`
    (`S = mu*(L+1) + z*sigma*sqrt(L+1)`), but with `mu` tracked online as an
    exponentially-weighted moving average of observed demand (level_t =
    alpha*demand_t + (1-alpha)*level_{t-1}) — smooth enough not to overreact
    to single noisy periods, responsive enough to follow a seasonal/trending
    pattern instead of assuming the long-run average always applies. `sigma`
    is deliberately *not* re-estimated online (a handful of recent points
    gives a noisy, unreliable variance estimate); it uses the same calibrated
    demand-variability figure a static policy would, isolating the benefit of
    mean-tracking from the risk of a jumpy, under-provisioned safety stock.

    The smoothed level is genuine per-policy state, reset between runs via
    `reset()` (see `chainsim.core.engine.SimulationEngine`, which calls it at
    the start of every `run()`).
    """

    def __init__(
        self,
        lead_time: float,
        sigma: float,
        service_level: float = 0.95,
        alpha: float = 0.3,
        fallback_mean: float = 0.0,
    ) -> None:
        self.lead_time = lead_time
        self.sigma = sigma
        self.z = norm_ppf(service_level)
        self.alpha = alpha
        self.fallback_mean = fallback_mean
        self._level: float | None = None

    def reset(self) -> None:
        self._level = None

    def decide(self, state: NodeState) -> float:
        if state.demand_history.size:
            latest = float(state.demand_history[-1])
            if self._level is None:
                self._level = latest
            else:
                self._level = self.alpha * latest + (1 - self.alpha) * self._level
        mu = self._level if self._level is not None else self.fallback_mean

        protection_periods = self.lead_time + 1
        S = mu * protection_periods + self.z * self.sigma * math.sqrt(protection_periods)
        return max(0.0, S - state.inventory_position)


def _calibrate_baseline_stats() -> tuple[float, float]:
    """What a practitioner would estimate for mean/std from a long historical
    sample of the (seasonal) demand, used to statically tune the baseline
    policy once up front — independent of the sweep's own RNG.
    """
    sample = SeasonalDemand(
        base=DEMAND_BASE,
        amplitude=DEMAND_AMPLITUDE,
        period_length=DEMAND_PERIOD,
        noise_std=DEMAND_NOISE,
    ).generate(5000, seed=999)
    return float(sample.mean()), float(sample.std())


ASSUMED_MEAN, ASSUMED_STD = _calibrate_baseline_stats()


def build_network(lead_time: float) -> SupplyChainNetwork:
    net = SupplyChainNetwork()
    # An ample, low-cost upstream source: the point of this example is the
    # Store's ordering policy, not Supplier-side warehousing economics, so its
    # holding cost is kept near zero and its stock is generous but not absurd.
    net.add_node(
        Supplier(id="Supplier", holding_cost=0.001, initial_inventory={DEFAULT_SKU: 5_000})
    )
    net.add_node(
        Retailer(
            id="Store",
            holding_cost=1.0,
            backlog_cost=8.0,
            initial_inventory={DEFAULT_SKU: DEMAND_BASE},
        )
    )
    net.add_edge(TransportLink(source="Supplier", destination="Store", lead_time=lead_time))
    net.validate()
    return net


def build_engine(params: dict) -> SimulationEngine:
    lead_time, policy_name = params["lead_time"], params["policy"]

    if policy_name == "baseline":
        store_policy: ReplenishmentPolicy = BaseStockPolicy(
            mean_demand=ASSUMED_MEAN,
            std_demand=ASSUMED_STD,
            lead_time=lead_time,
            service_level=SERVICE_LEVEL,
        )
    else:
        store_policy = AdaptiveOrderUpTo(
            lead_time=lead_time,
            sigma=ASSUMED_STD,
            service_level=SERVICE_LEVEL,
            alpha=0.15,
            fallback_mean=ASSUMED_MEAN,
        )

    return SimulationEngine(
        network=build_network(lead_time),
        demand={
            "Store": SeasonalDemand(
                base=DEMAND_BASE,
                amplitude=DEMAND_AMPLITUDE,
                period_length=DEMAND_PERIOD,
                noise_std=DEMAND_NOISE,
            )
        },
        # Supplier has no replenishment policy: it draws down its ample initial
        # stock (see build_network) rather than self-replenishing, so it stays
        # a passive, cheap upstream source instead of a second thing being
        # optimized.
        policies={"Store": store_policy},
        n_periods=N_PERIODS,
    )


def main() -> None:
    print(
        f"Calibrated baseline from a 5000-period historical sample: "
        f"mean={ASSUMED_MEAN:.2f}, std={ASSUMED_STD:.2f}\n"
    )

    sweep = ScenarioSweep(
        build=build_engine,
        param_grid={"policy": ["baseline", "adaptive"], "lead_time": LEAD_TIMES},
        n_replications=N_REPLICATIONS,
        base_seed=0,
    )
    results = sweep.run()

    summary = summarize_sweep(results, group_cols=["policy", "lead_time"]).sort_values(
        ["lead_time", "policy"]
    )
    print(
        f"Full sweep summary ({len(results)} runs: {len(LEAD_TIMES)} lead times x 2 policies "
        f"x {N_REPLICATIONS} replications)\n"
    )
    cols = [
        "policy",
        "lead_time",
        "total_cost_mean",
        "total_cost_std",
        "fill_rate_mean",
        "service_level_mean",
    ]
    print(summary[cols].round(3).to_string(index=False))

    # -- side-by-side pivots -------------------------------------------------
    print("\nTotal cost, mean over replications (lower is better):")
    cost_pivot = summary.pivot(index="lead_time", columns="policy", values="total_cost_mean")
    cost_pivot["adaptive_savings_%"] = (
        (cost_pivot["baseline"] - cost_pivot["adaptive"]) / cost_pivot["baseline"] * 100
    )
    print(cost_pivot.round(2).to_string())

    print("\nStore fill rate, mean over replications:")
    fill_pivot = summary.pivot(index="lead_time", columns="policy", values="fill_rate_mean")
    print(fill_pivot.round(4).to_string())

    # -- chainsim.metrics.compare_scenarios across the two policies overall --
    print("\nOverall comparison (pooled across all lead times):")
    by_policy = {name: results[results.policy == name] for name in ("baseline", "adaptive")}
    metrics = ["total_cost", "fill_rate", "service_level"]
    print(compare_scenarios(by_policy, metrics=metrics).round(3).to_string())

    print(
        "\nNote: the baseline's std was calibrated from a long historical sample, so it\n"
        "already (over-)counts the seasonal swing itself as if it were noise, buying it a\n"
        "generous, constant safety buffer at every point in the cycle. AdaptiveOrderUpTo\n"
        "only re-centers the *mean* online (via exponential smoothing) — it doesn't shrink\n"
        "sigma to match, and the forecast lag compounds with the shipment lead time, so the\n"
        "expected pay-off from mean-tracking alone doesn't materialize here, and it gets\n"
        "worse as lead time grows. A sharper adaptive policy would need to revisit the\n"
        "safety-stock term too — which the sweep above is exactly the right tool to check."
    )

    out_path = "examples/02_custom_policy_results.csv"
    results.to_csv(out_path, index=False)
    print(f"\nSaved raw sweep results ({len(results)} rows) to {out_path}")


if __name__ == "__main__":
    main()
