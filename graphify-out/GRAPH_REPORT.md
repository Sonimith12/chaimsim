# Graph Report - supply-chain-sim  (2026-10-11)

## Corpus Check
- 138 files · ~72,976 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 4, .ipynb 2, .css 1)

## Summary
- 1434 nodes · 4014 edges · 70 communities (55 shown, 15 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 641 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Disruption Events Core
- Engine Actions & Imports
- Scenario Network Builders
- Custom Policy Examples
- Quickstart & Demand Gens
- Frontend Edit/History Stores
- Event Director & Targets
- Transport Edge Scene
- 3D Model Registry
- Engine Node Processing
- Campaign Levels & Objectives
- App Shell & Game Loop
- FastAPI Main Endpoints
- Node State & Perishables
- Baseline RL Agents
- Demand Forecasters
- Economy Tracker
- Frontend Package Deps
- Moving Average & Tests
- Network Spec Conversion
- Empirical & Correlated Demand
- KPI Metrics
- Campaign Frontend Hook
- Edit Panel & Costs
- Animated HUD Controls
- Node Inspector Panel
- Campaign Results Overlay
- Economy & Scoring Bridge
- Dashboard Tests
- Streamlit Dashboard Pages
- Colors & Demand Pulse
- Atmosphere & Error Boundary
- Gymnasium Env Tests
- Disruption Reset Logic
- Camera Rig & Geometry
- TypeScript Config
- Supply Chain Gym Env
- Network Validation
- RQ Policy Tests
- Simulation Hook Actions
- Policy Builders
- Lead Time Distributions
- Base Stock Policy
- Score Keeper & Grades
- Run Simulation Page
- Architecture Concepts
- Network Graph Plot
- Scenario Smoke Tests
- Capped Policy & NodeState
- Library Design Philosophy
- Library Extension Points
- Prebuilt Scenarios Docs
- Backend Stack & Game Flow
- KPI Cards & Results
- Editor Launch Hook
- Game Backend Modules
- Placeholder Models Docs
- EOQ Formula
- Tracked Engine
- Capacity Reduction
- Disruption Network Docs
- Floating Texts
- Lead Time Sampling
- KPI Formatting
- Chainsim Root

## God Nodes (most connected - your core abstractions)
1. `SimulationEngine` - 61 edges
2. `SupplyChainNetwork` - 59 edges
3. `useGameStore` - 54 edges
4. `TransportLink` - 53 edges
5. `Node` - 47 edges
6. `EventContext` - 46 edges
7. `SimBridge` - 40 edges
8. `StationaryDemand` - 37 edges
9. `react` - 34 edges
10. `DemandShock` - 33 edges

## Surprising Connections (you probably didn't know these)
- `test_applies_at_window()` --uses--> `NodeOutage`  [INFERRED]
  tests/test_disruptions.py → src/chainsim/core/disruptions.py
- `test_edge_id()` --uses--> `TransportLink`  [INFERRED]
  tests/test_edges.py → src/chainsim/core/edges.py
- `test_unlimited_capacity_default()` --uses--> `TransportLink`  [INFERRED]
  tests/test_edges.py → src/chainsim/core/edges.py
- `Placeholder-first principle` --semantically_similar_to--> `Optional .glb models with placeholder fallback`  [INFERRED] [semantically similar]
  CLAUDE.md → frontend/public/models/README.md
- `Placeholder visual language` --semantically_similar_to--> `Optional .glb models with placeholder fallback`  [INFERRED] [semantically similar]
  CLAUDE.md → frontend/public/models/README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Frontend, backend and library three-tier architecture** — claude_r3f_scene, claude_fastapi_backend, readme_chainsim_library, claude_websocket_streaming [EXTRACTED 0.95]
- **Game rules layered over simulation engine** — readme_game_economy, readme_decision_events, readme_scoring_and_objectives, readme_campaign, readme_backend_game_modules [INFERRED 0.85]
- **Engine period step: disruptions, sink-first processing, history logging** — docs_codebase_reference_simulationengine, docs_codebase_reference_reversible_disruption_baseline, docs_codebase_reference_sink_first_processing, docs_codebase_reference_history_dataframe [EXTRACTED 0.90]

## Communities (70 total, 15 thin omitted)

### Community 0 - "Disruption Events Core"
Cohesion: 0.06
Nodes (63): _bulk_discount(), deal(), run(), CapacityCap, Choice, _competitor(), close(), cut_prices() (+55 more)

### Community 1 - "Engine Actions & Imports"
Cohesion: 0.07
Nodes (17): DemandGenerator, DisruptionEvent, Manufacturer, print_scenario_report(), run_scenario(), ScenarioConfig, main(), _make_policy() (+9 more)

### Community 2 - "Scenario Network Builders"
Cohesion: 0.10
Nodes (30): build_custom_scenario(), build_network(), build_network(), TransportLink, SupplyChainNetwork, DistributionCenter, Retailer, Supplier (+22 more)

### Community 3 - "Custom Policy Examples"
Cohesion: 0.07
Nodes (27): AdaptiveOrderUpTo, build_engine(), _calibrate_baseline_stats(), main(), SeasonalDemand, compare(), _numeric_columns(), summarize_sweep() (+19 more)

### Community 4 - "Quickstart & Demand Gens"
Cohesion: 0.09
Nodes (15): main(), StationaryDemand, SimulationEngine, OrderUpTo, test_conservation_inventory_position_matches_state(), test_deterministic_lead_time_delays_delivery_by_exact_periods(), test_engine_resets_stateful_policies_between_runs(), __init__() (+7 more)

### Community 5 - "Frontend Edit/History Stores"
Cohesion: 0.09
Nodes (38): Props, EditStore, HistoryStore, RunRecord, EMPTY_METRICS, initial, SimStore, CampaignResult (+30 more)

### Community 6 - "Event Director & Targets"
Cohesion: 0.10
Nodes (4): EventDirector, Targets, _new_shipments(), SimBridge

### Community 7 - "Transport Edge Scene"
Cohesion: 0.11
Nodes (32): CameraRig(), LeadTimeEditor(), TransportEdge(), TruckLayer(), draftEdgeState(), draftNodeState(), EditInteractions(), Ground() (+24 more)

### Community 8 - "3D Model Registry"
Cohesion: 0.14
Nodes (29): isGlb(), MODEL_FIT, MODEL_PATHS, ModelKey, ModelStatus, ModelStore, NODE_MODEL_KEY, probeModels() (+21 more)

### Community 9 - "Engine Node Processing"
Cohesion: 0.09
Nodes (3): NodeOutage, Node, test_node_outage_zeroes_capacity_and_deactivates()

### Community 10 - "Campaign Levels & Objectives"
Cohesion: 0.21
Nodes (26): apply_hidden_demand(), campaign_result(), _demand(), _edge(), evaluate_objectives(), _finish(), get_level(), _l1() (+18 more)

### Community 11 - "App Shell & Game Loop"
Cohesion: 0.14
Nodes (24): App(), STEP_INTERVAL_MS, openPresetForEdit(), useGameLoop(), Banner, Connection, GameStore, Phase (+16 more)

### Community 12 - "FastAPI Main Endpoints"
Cohesion: 0.12
Nodes (21): campaign_levels(), campaign_spec(), campaign_start(), get_state(), list_scenarios(), load_custom(), load_from_spec(), load_scenario() (+13 more)

### Community 13 - "Node State & Perishables"
Cohesion: 0.11
Nodes (10): Batch, PerishableInventory, test_expire_removes_and_tallies_waste(), test_invalid_issue_mode_rejected(), test_invalid_shelf_life_rejected(), test_issue_caps_at_available_non_expired_stock(), test_issue_fefo_consumes_soonest_expiring_first(), test_issue_fifo_consumes_oldest_receipt_first() (+2 more)

### Community 14 - "Baseline RL Agents"
Cohesion: 0.12
Nodes (14): Agent, evaluate_agent(), _get_action(), OrderUpToAgent, RandomAgent, _env(), test_evaluate_agent_runs_n_episodes_and_summarizes(), test_evaluate_agent_supports_sb3_style_predict_interface() (+6 more)

### Community 15 - "Demand Forecasters"
Cohesion: 0.12
Nodes (9): ExponentialSmoothingForecaster, forecast_accuracy(), Forecaster, mae(), mape(), NaiveForecaster, rmse(), test_exponential_smoothing_matches_hand_computed_level() (+1 more)

### Community 17 - "Frontend Package Deps"
Cohesion: 0.07
Nodes (28): dependencies, react, react-dom, @react-three/drei, @react-three/fiber, three, zustand, devDependencies (+20 more)

### Community 18 - "Moving Average & Tests"
Cohesion: 0.14
Nodes (18): MovingAverageForecaster, test_correlated_sku_demand_rejects_mismatched_shapes(), test_applies_at_window(), test_capacity_reduction_rejects_out_of_range_factor(), test_demand_shock_rejects_negative_multiplier(), test_all_forecasters_reject_empty_history(), test_exponential_smoothing_rejects_bad_alpha(), test_forecast_accuracy_bundle_has_all_metrics() (+10 more)

### Community 19 - "Network Spec Conversion"
Cohesion: 0.14
Nodes (14): config_to_spec(), _demand_from_spec(), _demand_to_spec(), DemandSpec, _disruption_from_spec(), _disruption_to_spec(), DisruptionSpec, EdgeSpec (+6 more)

### Community 20 - "Empirical & Correlated Demand"
Cohesion: 0.12
Nodes (11): CorrelatedSKUDemand, EmpiricalDemand, test_correlated_sku_demand_shape_and_correlation(), test_empirical_demand_rejects_empty_data(), test_empirical_demand_replays_in_order(), test_empirical_demand_shuffle_draws_from_data(), test_stationary_normal_clipped_at_zero(), test_stationary_poisson_mean_converges() (+3 more)

### Community 21 - "KPI Metrics"
Cohesion: 0.22
Nodes (12): average_inventory(), bullwhip_ratio(), fill_rate(), _filter(), inventory_turns(), per_node_kpis(), service_level(), summarize() (+4 more)

### Community 22 - "Campaign Frontend Hook"
Cohesion: 0.20
Nodes (19): fetchLevels(), startCampaignLevel(), CampaignStore, Feature, FEATURE_LEVEL, LastRecord, LevelProgress, load() (+11 more)

### Community 23 - "Edit Panel & Costs"
Cohesion: 0.14
Nodes (18): ChainSim 3D HTML entry (index.html), infrastructureCost(), DemandSpec, PolicySpec, DEMAND_FIELDS, DemandEditor(), EditPanel(), ParamField (+10 more)

### Community 24 - "Animated HUD Controls"
Cohesion: 0.18
Nodes (17): useAnimatedNumber(), chooseEvent(), pause(), play(), useSimStore, CashBadge(), EventCard(), RISK_LABEL (+9 more)

### Community 25 - "Node Inspector Panel"
Cohesion: 0.16
Nodes (18): changePolicy(), PolicyInfo, ANALYTICS, dollars(), Financials(), FLOW_ROWS, fmt(), NodeInspector() (+10 more)

### Community 26 - "Campaign Results Overlay"
Cohesion: 0.33
Nodes (17): useHistoryStore, CampaignResults(), TIER_LABEL, formatValue(), GRADE_COLORS, money(), objectiveTitle(), pct() (+9 more)

### Community 27 - "Economy & Scoring Bridge"
Cohesion: 0.13
Nodes (6): infrastructure_cost(), _default_policy_params(), _demand_generator(), _finite(), _inventory_scale(), NetworkSpecError

### Community 28 - "Dashboard Tests"
Cohesion: 0.13
Nodes (8): _bundle_from(), _run_record(), test_compare_scenarios_compares_two_runs(), test_compare_scenarios_prompts_for_a_second_run_when_only_one_exists(), test_every_page_sets_page_config(), test_results_dashboard_period_snapshot_slider(), test_results_dashboard_renders_kpis_and_charts_for_a_run(), test_run_simulation_executes_and_records_a_run()

### Community 29 - "Streamlit Dashboard Pages"
Cohesion: 0.20
Nodes (4): get_scenario_config(), require_scenario_config(), ScenarioBundle, set_scenario_config()

### Community 30 - "Colors & Demand Pulse"
Cohesion: 0.15
Nodes (16): NODE_COLORS, clamp(), DemandPulse(), Props, Pulse, createAppearance(), BACKLOG_TINT, HALO_FLASH (+8 more)

### Community 31 - "Atmosphere & Error Boundary"
Cohesion: 0.16
Nodes (12): Atmosphere(), LocalEnvironment(), ErrorBoundary, Props, FittedModel, useFittedModel(), CrateBox(), CrateModel() (+4 more)

### Community 32 - "Gymnasium Env Tests"
Cohesion: 0.18
Nodes (13): _env(), test_check_env_continuous(), test_check_env_discrete(), test_decode_observation_roundtrip(), test_episode_truncates_after_n_periods(), test_large_order_action_prevents_backlog_buildup(), test_reset_is_deterministic_given_seed(), test_reset_returns_obs_and_info() (+5 more)

### Community 33 - "Disruption Reset Logic"
Cohesion: 0.12
Nodes (8): test_lead_time_shock_does_not_compound_across_periods(), test_lead_time_shock_scales_constant_lead_time(), test_lead_time_shock_wraps_callable_lead_time(), test_callable_lead_time_sampling(), test_clear_disruptions_restores_capacity_and_lead_time(), test_constant_lead_time_sampling(), test_edge_id(), test_unlimited_capacity_default()

### Community 34 - "Camera Rig & Geometry"
Cohesion: 0.18
Nodes (14): Anim, OrbitLike, OVERVIEW_TARGET, Props, EDGE_Y, edgeEndpoints, LayerProps, Truck() (+6 more)

### Community 35 - "TypeScript Config"
Cohesion: 0.12
Nodes (15): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noFallthroughCasesInSwitch (+7 more)

### Community 37 - "Network Validation"
Cohesion: 0.20
Nodes (10): NetworkValidationError, _serial_chain(), test_predecessors_and_successors(), test_sources_and_sinks(), test_to_dict_captures_topology(), test_topological_order_downstream_first(), test_topological_order_upstream_first_by_default(), test_validate_passes_for_serial_chain() (+2 more)

### Community 38 - "RQ Policy Tests"
Cohesion: 0.21
Nodes (10): RQPolicy, _state(), test_base_stock_rejects_ambiguous_or_missing_target(), test_order_up_to_never_orders_negative(), test_order_up_to_orders_the_shortfall(), test_RQ_orders_fixed_quantity_at_reorder_point(), test_RQ_orders_nothing_above_reorder_point(), test_sS_orders_nothing_above_reorder_point() (+2 more)

### Community 39 - "Simulation Hook Actions"
Cohesion: 0.26
Nodes (13): applyServerState(), backToSetup(), beginRun(), COST_COLORS, loadScenario(), resetRun(), showFeedback(), step() (+5 more)

### Community 40 - "Policy Builders"
Cohesion: 0.19
Nodes (4): build_policy(), describe_policy(), ReplenishmentPolicy, sSPolicy

### Community 41 - "Lead Time Distributions"
Cohesion: 0.21
Nodes (5): constant_lead_time(), _sample(), poisson_lead_time(), uniform_lead_time(), test_poisson_lead_time_is_at_least_one()

### Community 42 - "Base Stock Policy"
Cohesion: 0.21
Nodes (6): BaseStockPolicy, norm_ppf(), test_base_stock_decide_orders_shortfall_to_S(), test_base_stock_from_costs_uses_newsvendor_critical_ratio(), test_base_stock_scales_with_lead_time_protection_period(), test_norm_ppf_matches_known_standard_normal_quantiles()

### Community 44 - "Run Simulation Page"
Cohesion: 0.23
Nodes (5): add_run(), get_runs(), require_runs(), run_label(), RunRecord

### Community 45 - "Architecture Concepts"
Cohesion: 0.24
Nodes (10): Phase plan (Phase 0 to 5), Baseline agents (OrderUpToAgent, RandomAgent, evaluate_agent), compare / compare_scenarios / summarize_sweep, Engine history DataFrame, KPI functions (fill_rate, service_level, bullwhip_ratio, summarize, per_node_kpis), ScenarioSweep and common random numbers, SimulationEngine, Streamlit dashboard pages and state (+2 more)

### Community 47 - "Scenario Smoke Tests"
Cohesion: 0.24
Nodes (5): test_manufacturing_jit_rejects_unknown_line_policy(), test_manufacturing_jit_supports_buffered_variant(), test_scenario_builds_a_valid_network(), test_scenario_main_runs_end_to_end(), test_scenario_runs_and_produces_well_formed_history()

### Community 49 - "Library Design Philosophy"
Cohesion: 0.25
Nodes (6): editable chainsim install (-e ..), Five-layer architecture (foundations to dashboard), Tech stack (SimPy, NetworkX, NumPy, Gymnasium, Pydantic), Package extras and dependencies, chainsim simulation library, Engine begin/step/finish interface

### Community 50 - "Library Extension Points"
Cohesion: 0.22
Nodes (8): React Three Fiber 3D scene, Coding conventions, Extension point ABCs (Node, ReplenishmentPolicy, DemandGenerator, DisruptionEvent, Forecaster), chainsim.io (unimplemented config schema and loaders), DemandGenerator (Stationary, Seasonal, Trend, Empirical, CorrelatedSKU), Forecaster (Naive, MovingAverage, ExponentialSmoothing), NodeState, ReplenishmentPolicy (OrderUpTo, sS, RQ, BaseStock)

### Community 51 - "Prebuilt Scenarios Docs"
Cohesion: 0.31
Nodes (9): Global Commodity Flow scenario, Manufacturing JIT scenario, Node (and Supplier, Manufacturer, DistributionCenter, Retailer), PerishableInventory and Batch (FEFO/FIFO), Pharma Cold Chain scenario, Retail Replenishment scenario, Multi-predecessor/successor routing approximations, ScenarioConfig (+1 more)

### Community 52 - "Backend Stack & Game Flow"
Cohesion: 0.29
Nodes (8): fastapi dependency, uvicorn dependency, websockets dependency, ChainSim 3D Project, FastAPI WebSocket backend bridge, Game flow (setup, play, event, results), WebSocket sim state streaming, Zustand stores (game/sim/UI state)

### Community 54 - "Editor Launch Hook"
Cohesion: 0.50
Nodes (7): launch(), openBlank(), postJson(), reportIssues(), tryStart(), warnIfCycle(), blankSpec()

### Community 55 - "Game Backend Modules"
Cohesion: 0.36
Nodes (7): Backend game modules (economy, scoring, events, campaign, network_spec), Campaign (10 levels, 4 acts), ChainSim 3D game, Decision events, Game economy (budget, crisis, bankruptcy), Sandbox mode and network editor, Scoring, objectives and grades

### Community 56 - "Placeholder Models Docs"
Cohesion: 0.40
Nodes (4): Placeholder visual language, Free CC0 asset sources (Kenney, Quaternius, Poly Haven), Model files (factory, warehouse, store, truck, crate), ModelRegistry.ts (MODEL_FIT, TRUCK_HEADING_OFFSET)

### Community 57 - "EOQ Formula"
Cohesion: 0.33
Nodes (3): economic_order_quantity(), test_eoq_matches_textbook_example(), test_eoq_minimizes_total_annual_cost()

### Community 59 - "Capacity Reduction"
Cohesion: 0.60
Nodes (3): CapacityReduction, test_capacity_reduction_noop_on_unlimited_capacity(), test_capacity_reduction_scales_finite_capacity()

### Community 60 - "Disruption Network Docs"
Cohesion: 0.50
Nodes (3): DisruptionEvent (NodeOutage, CapacityReduction, LeadTimeShock, DemandShock), SupplyChainNetwork, TransportLink

### Community 61 - "Floating Texts"
Cohesion: 0.67
Nodes (3): FloatingText(), FloatingTexts(), Floater

## Ambiguous Edges - Review These
- `ChainSim 3D Project` → `Streamlit dashboard`  [AMBIGUOUS]
  README.md · relation: conceptually_related_to

## Knowledge Gaps
- **17 isolated node(s):** `@types/react`, `@types/react-dom`, `@types/three`, `typescript`, `chainsim` (+12 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 433 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ChainSim 3D Project` connect `Backend Stack & Game Flow` to `Library Extension Points`, `Disruption Network Docs`, `Architecture Concepts`, `Game Backend Modules`?**
  _High betweenness centrality (0.406) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `SimulationEngine` (e.g. with `main()` and `SupplyChainEnv`) actually correct?**
  _`SimulationEngine` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `@types/react`, `@types/react-dom`, `@types/three` to the rest of the system?**
  _17 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Disruption Events Core` be split into smaller, more focused modules?**
  _Cohesion score 0.0562478366216684 - nodes in this community are weakly interconnected._
- **Why does `React Three Fiber 3D scene` connect `Library Extension Points` to `Placeholder Models Docs`, `Backend Stack & Game Flow`, `Edit Panel & Costs`?**
  _High betweenness centrality (0.389) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `SupplyChainNetwork` (e.g. with `spec_to_config()` and `build_custom_scenario()`) actually correct?**
  _`SupplyChainNetwork` has 23 INFERRED edges - model-reasoned connections that need verification._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `ChainSim 3D Project` and `Streamlit dashboard`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._