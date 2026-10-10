"""Pre-built, ready-to-run example supply chain scenarios.

Each scenario module builds a `chainsim.scenarios._common.ScenarioConfig`
(a network plus demand, policy, and disruption configuration) via its own
`build_scenario()`, and is runnable standalone:

- `python -m chainsim.scenarios.retail_replenishment` — DC -> stores,
  seasonal demand, promotional demand shocks.
- `python -m chainsim.scenarios.pharma_cold_chain` — perishable cold chain,
  regulatory-style service level target, batch expiry/waste.
- `python -m chainsim.scenarios.manufacturing_jit` — capacity-constrained
  production, a just-in-time reorder policy, a scheduled supplier outage.
- `python -m chainsim.scenarios.global_commodity_flow` — a larger,
  multi-modal, multi-predecessor/successor network with geopolitical-style
  disruptions.

Each module's `build_scenario()` and `main()` are also importable directly,
e.g. `from chainsim.scenarios.retail_replenishment import build_scenario`.
"""
