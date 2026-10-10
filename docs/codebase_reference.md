# chainsim Codebase Reference

Exhaustive technical reference generated directly from source, for writing user-facing
documentation. Version: `0.0.1` (from `pyproject.toml` / `chainsim.__version__`).

---

## Section 1: Package overview

### Installable extras

Declared under `[project.optional-dependencies]` in `pyproject.toml`:

| Extra | Install command | Packages | Purpose |
|---|---|---|---|
| `opt` | `pip install chainsim[opt]` | `ortools>=9.9` | Optimization backends (not yet wired into any module read in this pass) |
| `examples` | `pip install chainsim[examples]` | `matplotlib>=3.8` | Plotting in `examples/*.py` |
| `notebooks` | `pip install chainsim[notebooks]` | `ipykernel>=6.29`, `nbclient>=0.10`, `nbformat>=5.10` | Running/executing the `.ipynb` examples |
| `dashboard` | `pip install chainsim[dashboard]` | `streamlit>=1.32`, `plotly>=5.19`, `pyvis>=0.3` | The Streamlit dashboard app |
| `rl` | `pip install chainsim[rl]` | `stable-baselines3>=2.2` | Training RL agents against `SupplyChainEnv` |
| `dev` | `pip install chainsim[dev]` | `pytest>=8.0`, `pytest-cov>=4.1`, `ruff>=0.4` | Testing/linting |

Multiple extras can be combined, e.g. `pip install chainsim[dashboard,rl]`.

Note: `pyvis` is listed under the `dashboard` extra, but the dashboard code read in this
pass (`dashboard/components/network_graph.py`) uses **Plotly**, not pyvis, for the network
graph.

### Core dependencies (always installed)

From `[project] dependencies`:

| Package | Version constraint |
|---|---|
| `simpy` | `>=4.1` |
| `networkx` | `>=3.2` |
| `numpy` | `>=1.26` |
| `pandas` | `>=2.0` |
| `gymnasium` | `>=0.29` |
| `pydantic` | `>=2.5` |

### Python version requirement

`requires-python = ">=3.11"`. Classifiers list Python 3.11 and 3.12.

### Build / tooling metadata

- Build backend: `hatchling`.
- Package name: `chainsim`, version `0.0.1`, license MIT.
- `ruff` config: line-length 100, target `py311`, lint rule sets `E, W, F, I, UP, B, N, SIM`,
  with `N801/N802/N803/N806/N816` ignored (inventory-theory notation like `S`, `s`, `R`, `Q`
  is kept unrenamed) and `B027` ignored (`ReplenishmentPolicy.reset()` is an intentional
  no-op extension point).
- `pytest` config: `testpaths = ["tests"]`, `addopts = "-ra -q"`.

### Full import map

#### `chainsim` (top-level package `src/chainsim/__init__.py`)

Only exposes:
```python
chainsim.__version__  # "0.0.1"
```
No other names are re-exported at the top level; import from the subpackages below.

#### `chainsim.core`

```python
from chainsim.core import (
    DEFAULT_SKU,
    BaseStockPolicy,
    Batch,
    CapacityReduction,
    CorrelatedSKUDemand,
    DemandGenerator,
    DemandShock,
    DisruptionEvent,
    DistributionCenter,
    EmpiricalDemand,
    LeadTimeShock,
    Manufacturer,
    NetworkValidationError,
    Node,
    NodeOutage,
    NodeState,
    OrderUpTo,
    PerishableInventory,
    RQPolicy,
    ReplenishmentPolicy,
    Retailer,
    SeasonalDemand,
    SimulationEngine,
    StationaryDemand,
    Supplier,
    SupplyChainNetwork,
    TransportLink,
    TrendDemand,
    constant_lead_time,
    economic_order_quantity,
    norm_ppf,
    poisson_lead_time,
    sSPolicy,
    uniform_lead_time,
)
```

#### `chainsim.metrics`

```python
from chainsim.metrics import (
    ScenarioSweep,
    average_inventory,
    bullwhip_ratio,
    compare_scenarios,      # aliases chainsim.metrics.compare.compare
    fill_rate,
    inventory_turns,
    per_node_kpis,
    service_level,
    summarize,
    summarize_sweep,
    total_backlog_cost,
    total_holding_cost,
    total_transportation_cost,
    total_waste,
)
```

#### `chainsim.ai`

```python
from chainsim.ai import (
    Agent,
    ExponentialSmoothingForecaster,
    Forecaster,
    MovingAverageForecaster,
    NaiveForecaster,
    OrderUpToAgent,
    RandomAgent,
    SupplyChainEnv,
    evaluate_agent,
    forecast_accuracy,
    mae,
    mape,
    rmse,
)
```

#### `chainsim.scenarios`

`chainsim/scenarios/__init__.py` re-exports nothing itself (no `__all__`, no imports) — it's
a docstring-only package init. Each scenario module is imported directly:

```python
from chainsim.scenarios import retail_replenishment, pharma_cold_chain, manufacturing_jit, global_commodity_flow
# each module exposes build_scenario(...) -> ScenarioConfig and main()
from chainsim.scenarios.retail_replenishment import build_scenario
```

`chainsim.scenarios._common` (leading underscore — **not** public API) exposes
`ScenarioConfig`, `run_scenario`, `print_scenario_report` (see §5).

#### `chainsim.io`

`chainsim/io/__init__.py` is a docstring-only stub. `config_schema.py` and `loaders.py` are
also docstring-only stubs at present — **no Pydantic models or loader functions are
implemented yet** (see §6). Nothing is importable from `chainsim.io` beyond the empty
submodules themselves.

---

## Section 2: Core domain layer (`chainsim/core/`)

### 2.1 `nodes.py`

Module docstring: defines the abstract `Node` base class (identity, per-SKU inventory
state, capacity, cost coefficients, optional `lead_time_distribution` for nodes with no
network predecessor) plus role-specific subclasses `Supplier`, `Manufacturer`,
`DistributionCenter`, `Retailer`.

#### Module-level constants / type aliases

```python
LeadTimeDistribution = Callable[[np.random.Generator], float]
DEFAULT_SKU = "default"
```

```python
def constant_lead_time(value: float) -> LeadTimeDistribution
```
Returns a distribution that always samples `value`. (Duplicated identically in `edges.py`.)

#### `Node` — abstract base class (`@dataclass`, inherits `ABC`)

```python
@dataclass
class Node(ABC):
    id: str
    name: str = ""
    initial_inventory: dict[str, float] = field(default_factory=dict)
    capacity: float | None = None
    holding_cost: float = 1.0
    backlog_cost: float = 0.0
    lead_time_distribution: LeadTimeDistribution = field(default_factory=lambda: constant_lead_time(1.0))
    shelf_life: int | None = None
    skus: list[str] = field(default_factory=lambda: [DEFAULT_SKU])
```

Parameter table:

| Param | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | required | Unique identifier; used as the node key in the network graph. |
| `name` | `str` | `""` (falls back to `id` in `__post_init__`) | Human-readable label. |
| `initial_inventory` | `dict[str, float]` | `{}` | Starting on-hand inventory per SKU. |
| `capacity` | `float \| None` | `None` (unlimited) | Cap on outbound shipment/production quantity per period. |
| `holding_cost` | `float` | `1.0` | Cost charged per unit of on-hand inventory per period. |
| `backlog_cost` | `float` | `0.0` | Cost charged per unit of unmet demand/orders per period. |
| `lead_time_distribution` | `LeadTimeDistribution` | `constant_lead_time(1.0)` | Sampled when this node has no predecessor in the network (replenishes from "outside"). Ignored if the node has a predecessor — the connecting `TransportLink`'s lead time is used instead. |
| `shelf_life` | `int \| None` | `None` | If set, inventory is tracked in expiry-aware batches (`PerishableInventory`) with this many periods of shelf life. |
| `skus` | `list[str]` | `[DEFAULT_SKU]` | SKUs this node handles. |

Non-init (`init=False`) mutable simulation state fields, populated by `reset()`:

| Attribute | Type | Description |
|---|---|---|
| `on_hand` | `dict[str, float]` | Non-perishable on-hand inventory per SKU (empty/unused for perishable SKUs — those live in `_perishable`). |
| `backlog` | `dict[str, float]` | Unmet demand/orders per SKU. |
| `pipeline` | `dict[str, float]` | Quantity on order but not yet received, per SKU. |
| `_perishable` | `dict[str, PerishableInventory]` | Per-SKU batch-tracked inventory, populated only when `is_perishable`. |
| `active` | `bool` | `True` unless disrupted (`NodeOutage`) this period. |
| `base_capacity` | `float \| None` | Capacity before any disruption; restored each period by `clear_disruptions()`. |

**Inventory representation**: per-SKU, as plain `dict[str, float]` for non-perishable
inventory (`on_hand[sku]`), or delegated to a `PerishableInventory` instance per SKU
(`_perishable[sku]`) when `shelf_life is not None`. A node can only be perishable or
non-perishable as a whole (one `shelf_life` value for the node, applied to every SKU it
carries) — it does not mix modes per SKU.

Methods:

| Method | Signature | Returns | Description |
|---|---|---|---|
| `__post_init__` | `() -> None` | — | Sets `name = name or id`, stores `base_capacity = capacity`, calls `reset()`. |
| `clear_disruptions` | `() -> None` | — | Restores `active = True` and `capacity = base_capacity`. Called by the engine every period before applying that period's disruptions. |
| `reset` | `() -> None` | — | Calls `clear_disruptions()`; reinitializes `on_hand`, `backlog` (zeros per SKU), `pipeline` (zeros per SKU), `_perishable`; seeds each SKU's starting inventory from `initial_inventory` (via `PerishableInventory.receive(qty, period=0)` if perishable, else `on_hand[sku] = qty`). |
| `is_perishable` | `@property -> bool` | — | `shelf_life is not None`. |
| `on_hand_qty` | `(sku: str = DEFAULT_SKU) -> float` | on-hand qty | Non-expired on-hand quantity for `sku`. |
| `inventory_position` | `(sku: str = DEFAULT_SKU) -> float` | float | `on_hand_qty(sku) + pipeline.get(sku,0) - backlog.get(sku,0)`. |
| `receive` | `(qty: float, sku: str = DEFAULT_SKU, period: int = 0) -> None` | — | Receives a completed shipment/production run; reduces `pipeline[sku]` by `qty` (floored at 0), adds to on-hand (or a new perishable batch). No-op if `qty <= 0`. |
| `issue` | `(qty: float, sku: str = DEFAULT_SKU, period: int = 0) -> float` | qty issued | Issues up to `qty` units from on-hand (delegates to `PerishableInventory.issue` — always via FEFO default, see §2.6 — if perishable). Returns actual issued amount (may be less than requested). |
| `expire` | `(period: int, sku: str = DEFAULT_SKU) -> float` | wasted qty | Removes expired batches for `sku`, returns wasted quantity. No-op (returns `0.0`) if not perishable. |

#### `Supplier(Node)` (`@dataclass`)

```python
@dataclass
class Supplier(Node):
    def __post_init__(self) -> None:
        if self.capacity is None:
            self.capacity = float("inf")
        super().__post_init__()
```
No new fields. Difference from base `Node`: if `capacity` is left `None`, it defaults to
`float("inf")` (near-infinite upstream capacity) instead of staying `None`. Represents a
root/upstream node sourcing raw material from outside the modeled network.

#### `Manufacturer(Node)` (`@dataclass`)

```python
@dataclass
class Manufacturer(Node):
    bill_of_materials: dict[str, dict[str, float]] = field(default_factory=dict)
```
Adds `bill_of_materials`: maps an output SKU to the input SKUs/quantities consumed per unit
produced. **Phase 1 note**: this is metadata-only — the engine treats a `Manufacturer` like
any other intermediate node (single-SKU throughput); the BOM is not consumed by
`SimulationEngine` logic as read in this pass, reserved for future use.

#### `DistributionCenter(Node)` (`@dataclass`)

No new fields/methods. Represents an intermediate storage/consolidation node between
manufacturing and retail. Behaviorally identical to base `Node` — it exists as a semantic
/type distinction only.

#### `Retailer(Node)` (`@dataclass`)

No new fields/methods. Customer-facing sink node that observes external demand directly
(via the engine's `demand` mapping keyed by node id, not via anything on the class itself).

---

### 2.2 `edges.py`

Module docstring: `TransportLink` connects two nodes; carries origin, destination, lead
time (deterministic or distribution), capacity, cost per unit, and mode (free-form string,
e.g. truck/rail/ship/air). Edges point in the direction of material flow; orders flow the
opposite direction, handled by `engine.py`.

#### Module-level type alias and helper functions

```python
LeadTimeDistribution = Callable[[np.random.Generator], float]

def constant_lead_time(value: float) -> LeadTimeDistribution
def poisson_lead_time(mean: float) -> LeadTimeDistribution
def uniform_lead_time(low: float, high: float) -> LeadTimeDistribution
```

| Function | Behavior |
|---|---|
| `constant_lead_time(value)` | Always samples `value`. |
| `poisson_lead_time(mean)` | Samples `max(1.0, float(rng.poisson(mean)))` — Poisson-distributed, floored at 1 period. |
| `uniform_lead_time(low, high)` | Samples `float(rng.uniform(low, high))`. |

All three return a **callable** `(rng: np.random.Generator) -> float`, i.e. a distribution
sampled once per shipment — not a scipy/numpy distribution object.

#### `TransportLink` (`@dataclass`)

```python
@dataclass
class TransportLink:
    source: str
    destination: str
    lead_time: float | LeadTimeDistribution = 1.0
    capacity: float | None = None
    cost_per_unit: float = 0.0
    mode: str = "truck"
```

| Param | Type | Default | Description |
|---|---|---|---|
| `source` | `str` | required | Upstream node id. |
| `destination` | `str` | required | Downstream node id. |
| `lead_time` | `float \| LeadTimeDistribution` | `1.0` | Deterministic value, or a callable `(rng) -> float` sampled once per shipment via `sample_lead_time`. |
| `capacity` | `float \| None` | `None` (unlimited) | Max quantity shippable per period. |
| `cost_per_unit` | `float` | `0.0` | Transportation cost charged per unit shipped. |
| `mode` | `str` | `"truck"` | **Free-form string label**, not an enum/Literal — any value is accepted (scenario modules use `"truck"`, `"rail"`, `"air"`, `"ship"`). |

Non-init fields: `base_capacity: float | None` and `base_lead_time: float | LeadTimeDistribution`
(both set from the corresponding init value in `__post_init__`, used to restore after a
disruption).

Methods:

| Method | Signature | Description |
|---|---|---|
| `__post_init__` | `() -> None` | Sets `base_capacity = capacity`, `base_lead_time = lead_time`. |
| `clear_disruptions` | `() -> None` | Restores `capacity`/`lead_time` to base values. Called by the engine every period before applying disruptions. |
| `reset` | `() -> None` | Calls `clear_disruptions()`. |
| `sample_lead_time` | `(rng: np.random.Generator) -> float` | If `lead_time` is callable, calls it with `rng`; else returns `float(lead_time)`. |
| `id` | `@property -> str` | `f"{source}->{destination}"` — used as the disruption target-id format for edges (see `SimulationEngine._resolve_target`). |

**How `lead_time` works**: fixed float, or a distribution callable sampled fresh per
shipment via `sample_lead_time`.

**How `cost_per_unit`/`capacity` are used**: `cost_per_unit` is not applied inside
`SimulationEngine` itself — it's read downstream by `chainsim.metrics.kpis.total_transportation_cost`
/ `per_node_kpis` and by `chainsim.ai.gym_env.SupplyChainEnv._transport_cost`, both of which
multiply a node's fulfilled/shipped quantity by the edge's `cost_per_unit` (averaged across
multiple successor edges when a node ships to more than one). `capacity` **is** enforced
directly inside the engine: a node's `throughput_cap` is `min(node.capacity, sum of its
outbound edges' capacities)`, capping how much of `total_owed` (demand + backlog) can be
issued that period.

---

### 2.3 `network.py`

#### `NetworkValidationError(ValueError)`

Raised by `SupplyChainNetwork.validate()` (and internally by `topological_order()` on a
cycle) on any topology failure.

#### `SupplyChainNetwork`

```python
class SupplyChainNetwork:
    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
```

No constructor parameters. Backed by a `networkx.DiGraph` where each node id maps to
`{"obj": <Node>}` and each edge maps to `{"obj": <TransportLink>}`.

Methods:

| Method | Signature | Returns | Description |
|---|---|---|---|
| `add_node` | `(node: Node) -> Node` | the node (for chaining) | Adds a node; raises `ValueError` if `node.id` already present. |
| `add_edge` | `(edge: TransportLink) -> TransportLink` | the edge (for chaining) | Adds a directed edge; raises `ValueError` if either endpoint id is unknown. |
| `get_node` | `(node_id: str) -> Node` | — | Looks up a node object by id. |
| `get_edge` | `(source: str, destination: str) -> TransportLink` | — | Looks up an edge object by endpoints. |
| `nodes` | `@property -> list[Node]` | — | All node objects. |
| `edges` | `@property -> list[TransportLink]` | — | All edge objects. |
| `predecessors` | `(node_id: str) -> list[Node]` | — | Upstream nodes shipping directly to `node_id`. |
| `successors` | `(node_id: str) -> list[Node]` | — | Downstream nodes `node_id` ships directly to. |
| `sinks` | `() -> list[Node]` | — | Nodes with out-degree 0 (typically customer-facing retailers). |
| `sources` | `() -> list[Node]` | — | Nodes with in-degree 0 (roots replenishing from outside the network). |
| `topological_order` | `(*, downstream_first: bool = False) -> list[Node]` | — | Topologically-sorted node list. Default: sources before sinks (standard topological order). `downstream_first=True` reverses it (sinks before sources) — the order the engine actually processes nodes in, so a node already knows its successors' orders before deciding its own. Raises `NetworkValidationError` on a cycle. |
| `validate` | `() -> None` | — | See below. |
| `to_dict` | `() -> dict` | JSON-friendly dict | See below. |
| `__repr__` | `() -> str` | — | `"SupplyChainNetwork(nodes=<n>, edges=<m>)"`. |

**`validate()` checks (raises `NetworkValidationError` on first failure)**:
1. At least one node exists (`graph.number_of_nodes() > 0`).
2. Graph is a DAG (`nx.is_directed_acyclic_graph`).
3. No isolated (orphan) nodes, *unless* the graph has exactly one node total.
4. At least one sink node exists (`sinks()` non-empty).
5. At least one source node exists (`sources()` non-empty).

**Topological ordering ("sink-first")**: implemented by taking `nx.topological_sort(graph)`
(sources-first) and reversing the list when `downstream_first=True`. There is no separate
sink-first algorithm — it's a simple `reversed()` of the standard topological sort.

**`to_dict()`** exports (not full round-trip serialization — callables like lead-time
distributions are not portable):
```python
{
  "nodes": [{"id", "name", "type" (class name), "capacity" (None if inf/None),
             "holding_cost", "backlog_cost", "shelf_life", "skus"}, ...],
  "edges": [{"source", "destination", "capacity", "cost_per_unit", "mode"}, ...],
}
```
No `from_dict` exists in the module (not implemented).

There is no `SupplyChainNetwork.from_dict` method — only `to_dict` (one-way export).

---

### 2.4 `demand.py`

#### `DemandGenerator` — ABC

```python
class DemandGenerator(ABC):
    @abstractmethod
    def generate(self, n_periods: int, seed: int | None = None) -> np.ndarray: ...
```
Returns a length-`n_periods` array of non-negative demand quantities.

#### `StationaryDemand(DemandGenerator)`

```python
def __init__(self, mean: float, std: float = 0.0, distribution: str = "poisson") -> None
```

| Param | Type | Default | Description |
|---|---|---|---|
| `mean` | `float` | required | Mean demand per period. |
| `std` | `float` | `0.0` | Std dev — only used when `distribution="normal"`. |
| `distribution` | `str` | `"poisson"` | `"poisson"` or `"normal"` (`ValueError` otherwise). |

`generate(n_periods, seed=None)`: for `"poisson"`, `rng.poisson(mean, size=n_periods)`
cast to float; for `"normal"`, `rng.normal(mean, std, size=n_periods)` clipped at 0.
Supported distributions: **Poisson, Normal** only.

#### `SeasonalDemand(DemandGenerator)`

```python
def __init__(self, base: float, amplitude: float, period_length: int, noise_std: float = 0.0) -> None
```

| Param | Type | Default | Description |
|---|---|---|---|
| `base` | `float` | required | Base demand level. |
| `amplitude` | `float` | required | Sinusoidal amplitude. |
| `period_length` | `int` | required | Length of one seasonal cycle, in periods. |
| `noise_std` | `float` | `0.0` | Std dev of additive Gaussian noise. |

Formula: `demand[t] = base + amplitude * sin(2*pi*t / period_length) + noise`, clipped at 0.
`period_length` alone parameterizes the cycle length; there is no separate `phase`
parameter (phase is implicitly 0 — the sine starts at `t=0`).

#### `TrendDemand(DemandGenerator)`

```python
def __init__(self, base: float, trend_per_period: float, noise_std: float = 0.0) -> None
```
Formula: `demand[t] = base + trend_per_period * t + noise`, clipped at 0. **Linear only** —
no exponential-trend option exists.

#### `CorrelatedSKUDemand`

```python
def __init__(self, skus: list[str], mean: np.ndarray, cov: np.ndarray) -> None
def generate(self, n_periods: int, seed: int | None = None) -> np.ndarray
```

Note: **not** a `DemandGenerator` subclass (multi-series interface, not single-series).
Validates `mean.shape == (len(skus),)` and `cov.shape == (len(skus), len(skus))`, raising
`ValueError` otherwise. Correlation is specified via a full covariance matrix `cov` (an
`(n_skus, n_skus)` array) paired with a per-SKU mean vector.

`generate()` draws from `rng.multivariate_normal(mean, cov, size=n_periods)`, clipped at 0,
returning a `(n_periods, len(skus))` array (one column per SKU, in `skus` order).

**Discrepancy note**: the module docstring and the class docstring both mention a
`.series_for()` helper method to wrap one SKU's column as a `DemandGenerator`-compatible
callable — **this method does not actually exist in the code** as of this read. Only
`__init__` and `generate` are implemented. Do not document `series_for` as available.

#### `EmpiricalDemand(DemandGenerator)`

```python
def __init__(self, data: np.ndarray | list[float] | str | Path, shuffle: bool = False) -> None
```

| Param | Type | Default | Description |
|---|---|---|---|
| `data` | `np.ndarray \| list[float] \| str \| Path` | required | A 1-D historical demand series, or a path to a single-column CSV file. |
| `shuffle` | `bool` | `False` | If `True`, bootstraps (samples with replacement) instead of replaying in order. |

File format support: only a **single-column CSV** (loaded via `np.loadtxt(data,
delimiter=",")` when `data` is a `str`/`Path`). Raises `ValueError` if the resulting data
array is empty.

`generate(n_periods, seed=None)`:
- `shuffle=True`: `rng.choice(data, size=n_periods, replace=True)`.
- `shuffle=False`: tiles `data` (`np.tile`, `reps = ceil(n_periods / len(data))`) and
  truncates to `n_periods` — i.e. **loops** the historical series if it's shorter than
  `n_periods`.

No other demand generators exist in this module.

---

### 2.5 `policies.py`

#### `NodeState` (`@dataclass`)

```python
@dataclass
class NodeState:
    period: int
    on_hand: float
    backlog: float
    pipeline: float
    inventory_position: float
    demand_history: np.ndarray = field(default_factory=lambda: np.array([]))
```

| Field | Type | Description |
|---|---|---|
| `period` | `int` | Current simulation period. |
| `on_hand` | `float` | Current on-hand inventory (for the node's active SKU). |
| `backlog` | `float` | Currently unmet demand/orders. |
| `pipeline` | `float` | Quantity already on order but not yet received. |
| `inventory_position` | `float` | `on_hand + pipeline - backlog`. |
| `demand_history` | `np.ndarray` | Observed demand up to (not including) `period` — built by the engine from `_observed_demand[node.id][:-1]` (external demand + downstream orders, whichever applies to that node). |

This is exactly what the engine passes to `policy.decide(state)` each period (see
`SimulationEngine._decide_order`).

#### `ReplenishmentPolicy` — ABC

```python
class ReplenishmentPolicy(ABC):
    @abstractmethod
    def decide(self, state: NodeState) -> float: ...
    def reset(self) -> None: ...  # no-op by default
```

`decide(state)` returns the order quantity to place this period (the engine floors it at
0 via `max(0.0, policy.decide(state))` regardless of what the policy itself returns).
`reset()` clears any internal policy state between simulation runs — no-op by default,
intentionally left as an extension point (see `ruff` ignore `B027` in pyproject.toml).

**Custom policy**: subclass `ReplenishmentPolicy` and implement `decide(self, state:
NodeState) -> float`; `decide` is a pure function of the `NodeState` snapshot, so a custom
policy needs no knowledge of the engine internals. Override `reset()` only if the policy
carries state across periods that needs clearing between runs (e.g. an EMA forecast).

#### `OrderUpTo(ReplenishmentPolicy)`

```python
def __init__(self, S: float) -> None
def decide(self, state: NodeState) -> float:
    return max(0.0, self.S - state.inventory_position)
```
`S`: the order-up-to level, set directly by the caller (not derived). Orders enough each
period to bring inventory position to `S`.

#### `sSPolicy(ReplenishmentPolicy)`

```python
def __init__(self, s: float, S: float) -> None  # raises ValueError if s > S
def decide(self, state: NodeState) -> float:
    if state.inventory_position <= self.s:
        return max(0.0, self.S - state.inventory_position)
    return 0.0
```
`s` = reorder point, `S` = order-up-to level. When inventory position falls to or below
`s`, orders up to `S`; otherwise orders nothing.

#### `RQPolicy(ReplenishmentPolicy)`

```python
def __init__(self, R: float, Q: float) -> None  # raises ValueError if Q <= 0
def decide(self, state: NodeState) -> float:
    return self.Q if state.inventory_position <= self.R else 0.0
```
`R` = reorder point, `Q` = fixed order quantity (continuous-review (R,Q) policy).

#### `BaseStockPolicy(ReplenishmentPolicy)`

```python
def __init__(
    self,
    mean_demand: float,
    std_demand: float,
    lead_time: float,
    service_level: float | None = None,
    z: float | None = None,
) -> None
```

| Param | Type | Default | Description |
|---|---|---|---|
| `mean_demand` | `float` | required | Mean demand per period. |
| `std_demand` | `float` | required | Std dev of demand per period. |
| `lead_time` | `float` | required | Replenishment lead time, in periods. |
| `service_level` | `float \| None` | `None` | Target cycle service level in (0,1). Mutually exclusive with `z` — exactly one of the two must be given, else `ValueError`. |
| `z` | `float \| None` | `None` | Standard-normal safety factor, used directly instead of deriving from `service_level`. |

Formula: `protection_periods = lead_time + 1`; `S = mean_demand * protection_periods +
z * std_demand * sqrt(protection_periods)`, where `z = norm_ppf(service_level)` if `z` was
not given directly. `decide()` behaves like `OrderUpTo` against this derived `S`.

```python
@classmethod
def from_costs(
    cls, mean_demand: float, std_demand: float, lead_time: float,
    holding_cost: float, backlog_cost: float,
) -> BaseStockPolicy
```
Builds a `BaseStockPolicy` from the **newsvendor critical ratio**
`critical_ratio = backlog_cost / (backlog_cost + holding_cost)`, passed as `service_level`.
Raises `ValueError` if either cost is negative or both are zero.

#### Module-level functions

```python
def economic_order_quantity(demand_rate: float, order_cost: float, holding_cost: float) -> float
```
Classic EOQ: `Q* = sqrt(2 * demand_rate * order_cost / holding_cost)`. Raises `ValueError`
if `demand_rate < 0`, `order_cost < 0`, or `holding_cost <= 0`.

```python
def norm_ppf(p: float) -> float
```
Inverse CDF of the standard normal distribution via Peter Acklam's rational approximation
(no `scipy` dependency), accurate to ~`1.15e-9` absolute error. Requires `0 < p < 1`
(`ValueError` otherwise).

---

### 2.6 `perishability.py`

#### `Batch` (`@dataclass`)

```python
@dataclass
class Batch:
    quantity: float
    received_at: int
    expires_at: int
    def is_expired(self, period: int) -> bool:
        return period >= self.expires_at
```
A single receipt with a known expiry period. Usable through (and including) period
`expires_at - 1`; from `expires_at` onward it's waste.

#### `PerishableInventory`

```python
def __init__(self, shelf_life: int) -> None  # raises ValueError if shelf_life <= 0
```

Shelf life is specified **per node/SKU at construction time** (an integer number of
periods) — not per individual batch; every batch received into a given `PerishableInventory`
instance gets the same `shelf_life`. On the domain-model side, `Node.shelf_life` (an `int |
None`) sets this per node (uniformly across all its SKUs — see §2.1).

Attributes: `shelf_life: int`, `batches: list[Batch]`, `total_waste: float` (cumulative,
across the object's lifetime).

Methods:

| Method | Signature | Description |
|---|---|---|
| `on_hand` | `@property -> float` | Sum of all batch quantities currently held (does **not** itself purge expired batches — call `expire()` first for an accurate figure). |
| `receive` | `(quantity: float, period: int) -> None` | Adds a new `Batch(quantity, received_at=period, expires_at=period + shelf_life)`. No-op if `quantity <= 0`. |
| `expire` | `(period: int) -> float` | Purges all batches expired as of `period`; returns wasted quantity; accumulates into `total_waste`. |
| `issue` | `(quantity: float, period: int, mode: str = "FEFO") -> float` | Issues up to `quantity` from non-expired batches. Returns actual issued amount. |

**FIFO vs FEFO**: `issue()`'s `mode` parameter selects the sort key over usable
(non-expired) batches: `"FEFO"` (first-expired-first-out, sorted by `expires_at` — the
default and standard choice for perishables) or `"FIFO"` (first-in-first-out, sorted by
`received_at`). Raises `ValueError` for any other value. **However**, `Node.issue()` (the
call path the engine actually uses) always calls `PerishableInventory.issue(qty,
period=period)` **without** passing `mode` — so in practice, through the simulation engine,
issuance is always **FEFO**; choosing FIFO requires calling `PerishableInventory.issue`
directly with `mode="FIFO"`, bypassing `Node`.

**Waste/write-off tracking**: `PerishableInventory.total_waste` accumulates every call to
`expire()`. The engine calls `node.expire(t, sku)` once per node per period (only if
`node.is_perishable`), and records the returned quantity as that period's `"waste"` column
in the history log (see §2.8) — so waste is reported per node, per period, in the
simulation history, in addition to the running `total_waste` on the `PerishableInventory`
object itself. `chainsim.metrics.kpis.total_waste()` sums the `"waste"` history column.

---

### 2.7 `disruptions.py`

#### Module-level type alias

```python
Target = Node | TransportLink
```

#### `DisruptionEvent` — ABC

```python
class DisruptionEvent(ABC):
    def __init__(self, target_id: str, start: int, duration: int = 1) -> None  # raises ValueError if duration <= 0
    @property
    def end(self) -> int:  # start + duration
    def applies_at(self, t: int) -> bool:  # start <= t < end
    @abstractmethod
    def apply(self, target: Any) -> None: ...
```

| Param | Type | Default | Description |
|---|---|---|---|
| `target_id` | `str` | required | Id of the node, or `"source->destination"` for an edge, this event targets. |
| `start` | `int` | required | First period the event is active. |
| `duration` | `int` | `1` | Number of periods active. Must be `> 0`. |

`applies_at(t)` is a **pure time-window check** — `start <= t < start + duration`. There is
no probabilistic-trigger variant implemented; the module docstring mentions events can be
"triggered probabilistically each period" but no concrete probabilistic `DisruptionEvent`
subclass exists in the code — all four implementations below are purely deterministic time
windows.

#### `NodeOutage(DisruptionEvent)`

```python
def apply(self, target: Node) -> None:
    target.active = False
    target.capacity = 0.0
```
Takes a node fully offline: `active = False` (so the engine treats `fulfillable` as `0`
regardless of demand — see engine §2.8) and `capacity = 0.0`. Inventory itself is not
frozen or altered — only issuance and reported active-ness are affected via `node.active`.

#### `CapacityReduction(DisruptionEvent)`

```python
def __init__(self, target_id: str, start: int, duration: int, factor: float) -> None  # factor must be in [0, 1]
def apply(self, target: Node | TransportLink) -> None:
    base = target.base_capacity
    if base is None or base == float("inf"):
        return
    target.capacity = base * self.factor
```
`factor` is a **fraction** (0 to 1) applied to `base_capacity`, e.g. `0.5` halves it. Works
on nodes or edges. A target with unlimited base capacity (`None`/`inf`) is left unaffected
— nothing to scale.

#### `LeadTimeShock(DisruptionEvent)`

```python
def __init__(self, target_id: str, start: int, duration: int, multiplier: float) -> None  # multiplier must be >= 0
def apply(self, target: TransportLink) -> None: ...
```
`multiplier` is **multiplicative** on the edge's `base_lead_time` (always derived from
`base_lead_time`, never the already-shocked current value, so repeated calls across periods
don't compound). If `base_lead_time` is a callable distribution, the shock wraps it in a
new closure that samples the base then multiplies the result; if it's a plain float, it's
multiplied directly.

#### `DemandShock(DisruptionEvent)`

```python
def __init__(self, target_id: str, start: int, duration: int, multiplier: float) -> None  # multiplier must be >= 0
def apply(self, target: float) -> float:
    return target * self.multiplier
```
`multiplier` is **multiplicative** on the baseline sampled demand value for the period —
`target` here is a demand *value* (`float`), not a node/edge object (unlike the other three
disruption types, whose `apply()` mutates a `Node`/`TransportLink` in place).
`SimulationEngine._apply_disruptions` special-cases `DemandShock`: it is **not** dispatched
through the generic `event.apply(self._resolve_target(...))` call used for the other three
types; instead, active `DemandShock` events are collected into
`self._active_demand_shocks: dict[target_id, DemandShock]` and applied later, per node, to
that node's freshly sampled external demand value in `_process_node`.

#### "Reversible against stored baseline" mechanism

Every period, before applying any disruption, `SimulationEngine._apply_disruptions` calls
`node.clear_disruptions()` / `edge.clear_disruptions()` on **every** node and edge in the
network — restoring `capacity`/`active` (nodes) and `capacity`/`lead_time` (edges) to their
respective `base_capacity`/`base_lead_time` values captured once in each object's
`__post_init__`. Only *then* does it iterate the disruption list and call `apply()` for
every event whose `applies_at(t)` is currently true. This means:
- Effects never compound across periods (each period starts from the true baseline).
- A disruption naturally "expires" the period after `end` — nothing bespoke needs to run to
  undo it; it simply isn't re-applied, and the prior `clear_disruptions()` already reset the
  target.

#### Overlap / stacking of disruptions

Multiple disruption events **can** be active on the same target in the same period (nothing
prevents overlapping `start`/`duration` windows, even on the same `target_id`). However,
they do **not compound** — each active event's `apply()` is called fresh against the
restored baseline every period. If two events of the *same type* target the same object in
overlapping windows, the **last one processed in `self.disruptions` list order wins**
outright (each `apply()` call overwrites the previous one's mutation of `.capacity` /
`.lead_time`, it does not stack/multiply the effects together) — there's no explicit
event-ordering guarantee beyond list order, and no merging logic. `DemandShock` on the same
node has the same behavior via `self._active_demand_shocks` being a plain dict keyed by
`target_id` — a second `DemandShock` on the same node/period silently overwrites the first
in that dict (dict comprehension `{e.target_id: e for e in active if isinstance(e,
DemandShock)}` — last one in iteration order survives).

---

### 2.8 `engine.py`

#### `SimulationEngine` (`@dataclass`)

```python
@dataclass
class SimulationEngine:
    network: SupplyChainNetwork
    demand: dict[str, DemandGenerator] = field(default_factory=dict)
    policies: dict[str, ReplenishmentPolicy] = field(default_factory=dict)
    disruptions: list[DisruptionEvent] = field(default_factory=list)
    n_periods: int = 52
    seed: int | None = None
```

| Param | Type | Default | Description |
|---|---|---|---|
| `network` | `SupplyChainNetwork` | required | Topology to simulate. Validated (`network.validate()`) in `__post_init__`. |
| `demand` | `dict[str, DemandGenerator]` | `{}` | Node id -> demand generator, for every customer-facing node facing external demand. |
| `policies` | `dict[str, ReplenishmentPolicy]` | `{}` | Node id -> replenishment policy. A node with no entry never places orders. |
| `disruptions` | `list[DisruptionEvent]` | `[]` | Disruption events to apply during the run. |
| `n_periods` | `int` | `52` | Number of periods to simulate. |
| `seed` | `int \| None` | `None` | Seed for demand generation and stochastic lead times. |

`__post_init__` validates the network and sets `self.history: pd.DataFrame | None = None`.

**Public methods**:

```python
def run(self) -> pd.DataFrame
```
Runs the full simulation (`begin()` then `step(t)` for every `t` in `range(n_periods)`,
then `finish()`); returns the resulting history DataFrame.

```python
def begin(self) -> None
```
Initializes a fresh run (`_init_run()`) without executing any periods — for callers (e.g.
`SupplyChainEnv`) stepping one period at a time.

```python
def step(self, t: int, overrides: dict[str, float] | None = None) -> list[dict]
```
Processes one period; must be called with `t` in strictly increasing order after `begin()`.
`overrides` maps node id -> order quantity to force for that node this period, bypassing its
own policy (or the lack of one). Every other node still decides normally via its own
policy. Returns the history rows appended during this period (one dict per node processed).

```python
def observed_demand(self, node_id: str) -> list[float]
```
Period-by-period demand `node_id` has observed so far this run (external demand and/or
downstream orders, whichever applies) — the same series `NodeState.demand_history` is drawn
from.

```python
def finish(self) -> pd.DataFrame
```
Builds `self.history = pd.DataFrame(self._rows)` from whatever periods have been processed
so far (safe after `run()`, or after a partial `step()` sequence) and returns it.

**Simulation loop order** (per `step(t)`, in `_process_node`, called sink-first — i.e.
downstream/customer-facing nodes processed before their upstream suppliers, per
`network.topological_order(downstream_first=True)`):

1. `_advance_to(t)` — advances the SimPy environment, processing all scheduled deliveries
   with time `<= t`.
2. `_apply_disruptions(t)` — reset every node/edge to baseline, then apply active
   disruptions (except `DemandShock`, deferred — see §2.7).
3. For each node in sink-first order:
   a. Expire perishable stock for the period (`node.expire(t, sku)`), recording waste.
   b. Pop pending downstream orders (`incoming_orders`) routed to this node last period.
   c. Sample/shock external demand for this node, if it has a demand generator
      (`external_demand`, with any active `DemandShock` applied).
   d. `period_demand = incoming_orders + external_demand`; appended to `_observed_demand`.
   e. `total_owed = period_demand + prior_backlog`.
   f. Compute `throughput_cap = min(node.capacity, sum of outbound edge capacities)`.
   g. `fulfillable = min(total_owed, throughput_cap)` if `node.active` else `0`; issue that
      much from inventory (`node.issue`); remaining `total_owed - issued` becomes the new
      `backlog`.
   h. Ship the issued quantity downstream (`_ship_downstream`) — for multiple successors,
      splits proportionally to each successor's share of `incoming_orders` this period (or
      evenly if `incoming_orders == 0`); schedules a delayed SimPy delivery per successor,
      keyed to that edge's sampled lead time.
   i. Decide this node's own replenishment order — either the `override` value (if
      given, floored at 0), or `policy.decide(NodeState(...))` via `_decide_order` (also
      floored at 0; `0.0` if the node has no policy).
   j. Route the order upstream (`_route_order`): adds to the node's own `pipeline`; if the
      node has predecessors, splits the order **evenly** across all of them and records each
      predecessor's pending order for next period; if the node has no predecessor (a root),
      schedules external replenishment delayed by the node's own
      `lead_time_distribution`.
   k. Appends one history row for the node (see column list below).

So, in short, order per node per period: **expire -> receive incoming orders/demand ->
issue/fulfill (subject to capacity) -> ship downstream (SimPy delayed delivery) -> decide
replenishment order -> route order upstream (or schedule external replenishment) -> log
history row.** Disruption application happens once per period before any node is processed.

**Shipment handling**: modeled as SimPy delayed processes. `_ship_downstream` calls
`self.env.process(self._deliver(successor, sku, ship_qty, lead_time))` for each successor
receiving a positive shipment; `_route_order` does the same via `self._deliver(node, sku,
order_qty, lead_time)` for root nodes' external replenishment. `_deliver` is a SimPy
generator: `yield self.env.timeout(lead_time)` then `node.receive(qty, sku,
period=int(self.env.now))`.

**How time works**: integer periods, `t = 0, 1, ..., n_periods - 1`. One period is whatever
calendar unit the caller assigns via demand-generator parameters and lead times (scenario
modules use both weekly and daily periods — e.g. `retail_replenishment` treats periods as
weeks, `pharma_cold_chain`/`manufacturing_jit` treat them as days). `_advance_to(t)` handles
the SimPy `env.now` bookkeeping carefully: a plain `env.run(until=t)` stops just *before*
running events scheduled at exactly `t` (which would defer deliveries by an extra period),
so the method follows with `while env.peek() <= env.now: env.step()` to also process
same-instant events.

**History DataFrame columns** (one row per node per period, `_rows` -> `pd.DataFrame`):

| Column | Type | Description |
|---|---|---|
| `period` | `int` | The period `t`. |
| `node_id` | `str` | Node id. |
| `node_type` | `str` | `type(node).__name__` (e.g. `"Retailer"`). |
| `active` | `bool` | Whether the node was active (not under a `NodeOutage`) this period. |
| `external_demand` | `float` | Sampled external demand this period (post any `DemandShock`), `0.0` if the node has no demand generator. |
| `incoming_orders` | `float` | Downstream orders routed to this node last period. |
| `period_demand` | `float` | `incoming_orders + external_demand`. |
| `fulfilled` | `float` | Quantity actually issued this period. |
| `on_hand` | `float` | On-hand quantity after issuance (`node.on_hand_qty(sku)`). |
| `backlog` | `float` | Backlog after this period's fulfillment. |
| `pipeline` | `float` | On-order-not-yet-received quantity. |
| `inventory_position` | `float` | `on_hand + pipeline - backlog`. |
| `order_placed` | `float` | Replenishment order quantity decided this period. |
| `waste` | `float` | Quantity expired (written off) this period (`0.0` if not perishable). |
| `holding_cost` | `float` | `node.holding_cost * on_hand_qty`. |
| `backlog_cost` | `float` | `node.backlog_cost * backlog`. |

**Documented scope limits (Phase 1, from the module docstring)**:
- **Single SKU per node**: uses `chainsim.core.nodes.DEFAULT_SKU` unless the node's first
  configured SKU says otherwise (`_sku_for` returns `node.skus[0] if node.skus else
  DEFAULT_SKU`) — only one SKU is actually processed per node per period even if `skus` has
  more than one entry.
- **Multi-predecessor nodes**: a node's order is split **evenly** across all its
  predecessors, regardless of each predecessor's status (e.g. under an outage) — a
  documented approximation, not automatic rerouting.
- **Multi-successor nodes**: fulfilled quantity is split **proportionally** to each
  successor's share of that period's incoming orders (or evenly if there were no incoming
  orders that period).
- Both are described as "exact and fully tested for the common serial-chain/tree case
  (each node has at most one supplier)"; general many-to-many networks use these as
  documented approximations, not guaranteed-correct general routing.

---

## Section 3: Metrics layer (`chainsim/metrics/`)

### 3.1 `kpis.py`

All functions take the engine's `history: pd.DataFrame` (as returned by
`SimulationEngine.run()`/`finish()`) and an optional `node_id: str | None = None` to filter
to one node (via internal `_filter()` helper — `history[history["node_id"] == node_id]` if
given, else the whole frame).

| Function | Signature | Formula / definition | Returns |
|---|---|---|---|
| `fill_rate` | `(history, node_id=None) -> float` | `sum(fulfilled) / sum(period_demand)`; `1.0` if no demand. Volume-weighted across the run. | `float` |
| `service_level` | `(history, node_id=None) -> float` | Fraction of periods ending with `backlog <= 0` — a **cycle service level**; `1.0` if history is empty. | `float` |
| `average_inventory` | `(history, node_id=None) -> float` | Mean `on_hand` across the run; `0.0` if empty. | `float` |
| `inventory_turns` | `(history, node_id=None) -> float` | `sum(fulfilled) / mean(on_hand)`; `nan` if avg inventory is 0. Throughput proxy for turns (no true COGS figure used). | `float` |
| `bullwhip_ratio` | `(history, node_id: str) -> float` (node_id **required**, no default) | `var(order_placed, ddof=1) / var(period_demand, ddof=1)`; `nan` if demand variance is 0. `>1` = order variance amplification vs. observed demand (bullwhip signature). | `float` |
| `total_holding_cost` | `(history, node_id=None) -> float` | `sum(holding_cost)` | `float` |
| `total_backlog_cost` | `(history, node_id=None) -> float` | `sum(backlog_cost)` | `float` |
| `total_waste` | `(history, node_id=None) -> float` | `sum(waste)` | `float` |
| `total_transportation_cost` | `(history, network: SupplyChainNetwork, node_id=None) -> float` | For each node group, `sum(fulfilled) * avg(cost_per_unit across its outbound edges)`, summed across nodes/groups. Approximates transport cost using the engine's documented proportional-split behavior for multi-successor nodes. Requires `network` (positional, no default). | `float` |
| `per_node_kpis` | `(history, network: SupplyChainNetwork \| None = None) -> pd.DataFrame` | See below. | `pd.DataFrame` indexed by `node_id` |
| `summarize` | `(history, network: SupplyChainNetwork \| None = None) -> dict[str, float]` | See below. | `dict[str, float]` |

**`fill_rate` vs `service_level`**: `fill_rate` is a **volume-weighted** measure (fraction
of total *units* demanded that were fulfilled immediately); `service_level` is a
**period-weighted cycle service level** (fraction of *periods* ending with zero backlog,
regardless of magnitude). A node could have high fill rate but low service level (many
small shortfalls) or vice versa (rare but huge shortfalls).

**`per_node_kpis(history, network=None)`** returns one row per `node_id` (index) with
columns: `avg_on_hand`, `avg_backlog`, `fill_rate`, `service_level`, `inventory_turns`,
`bullwhip_ratio`, `total_holding_cost`, `total_backlog_cost`, `total_transportation_cost`
(`0.0` for every node if `network is None`), `total_waste`, `total_cost` (=
`total_holding_cost + total_backlog_cost + total_transportation_cost`).

**`summarize(history, network=None)`** returns a flat dict:
```python
{
  "total_cost": float,                  # sum of per_node total_cost
  "total_holding_cost": float,
  "total_backlog_cost": float,
  "total_transportation_cost": float,
  "total_waste": float,
  "fill_rate": float,                   # averaged over sink nodes if network given, else all nodes
  "service_level": float,               # averaged over sink nodes if network given, else all nodes
  "avg_bullwhip_ratio": float,          # mean over per-node bullwhip_ratio, skipna=True
}
```
`fill_rate`/`service_level` are averaged over **sink nodes** (`network.sinks()`, e.g.
retailers) when `network` is provided — because those are usually the metrics that matter
most to a business — falling back to averaging over every node when `network` is omitted.

### 3.2 `sweep.py`

#### `ScenarioSweep` (`@dataclass`)

```python
@dataclass
class ScenarioSweep:
    build: Callable[[dict[str, Any]], SimulationEngine]
    param_grid: Mapping[str, Iterable[Any]]
    n_replications: int = 100
    base_seed: int = 0
```

| Param | Type | Default | Description |
|---|---|---|---|
| `build` | `Callable[[dict[str, Any]], SimulationEngine]` | required | Given one parameter combination (a dict, one value per `param_grid` key), returns a fresh, ready-to-run `SimulationEngine`. Its `.seed` is overwritten by the sweep before each replication — so `build`'s own seed choice doesn't matter. |
| `param_grid` | `Mapping[str, Iterable[Any]]` | required | Maps parameter name -> values to try. The full **Cartesian product** (`itertools.product`) of every parameter's values is run. |
| `n_replications` | `int` | `100` | Monte Carlo replications per parameter combination. |
| `base_seed` | `int` | `0` | Replication `r` uses seed `base_seed + r`. |

```python
def run(self) -> pd.DataFrame
```
Iterates `itertools.product(*param_grid.values())`; for each combo, for `rep` in
`range(n_replications)`: builds the engine via `build(params)`, sets `engine.seed =
base_seed + rep`, runs it, and appends a row `{**params, "replication": rep,
**summarize(history, engine.network)}`. Returns a tidy `pd.DataFrame`, one row per
`(parameter combination, replication)`.

**Common random numbers**: replication `r` **always** uses seed `base_seed + r`, regardless
of which parameter combination is running — pairing demand/lead-time draws across
combinations for lower-variance, apples-to-apples comparisons (e.g. replication 3 sees the
same demand realization whether it's the baseline or a variant).

**Performance note (from the docstring)**: each replication runs a full, independent
`SimulationEngine` — cost scales linearly as `len(param_grid combinations) * n_replications`;
no cross-replication vectorization currently exists.

### 3.3 `compare.py`

```python
def summarize_sweep(
    results: pd.DataFrame,
    group_cols: Sequence[str],
    metrics: Sequence[str] | None = None,
) -> pd.DataFrame
```
Aggregates a tidy sweep results table (e.g. `ScenarioSweep.run()`'s output) to mean/std per
unique combination of `group_cols`, across replications. `metrics` defaults to every
numeric column not in `group_cols` and not `"replication"`. Returns one row per unique
`group_cols` combination with `{metric}_mean` and `{metric}_std` columns (flattened from a
`groupby(...).agg(["mean", "std"])`).

```python
def compare(
    results_by_scenario: Mapping[str, pd.DataFrame],
    metrics: Sequence[str] | None = None,
) -> pd.DataFrame
```
(Exported at the package level as `compare_scenarios` — see §1.) Compares two or more
independently-produced scenario results side by side. `results_by_scenario` maps a scenario
label to either a tidy sweep DataFrame (mean/std taken across all its rows) or a single-row
summary (e.g. `pd.DataFrame([summarize(...)])`). `metrics` defaults to every numeric column
present. Returns one row per scenario (indexed by scenario label, column `"scenario"`
becomes the index), with `{metric}_mean` always present and `{metric}_std` present only
when more than one row was available for that scenario.

---

## Section 4: AI/ML interfaces (`chainsim/ai/`)

### 4.1 `gym_env.py`

#### Module-level type alias

```python
ActionType = Literal["continuous", "discrete"]
```

#### `SupplyChainEnv(gym.Env)`

```python
metadata = {"render_modes": ["ansi"]}

def __init__(
    self,
    network: SupplyChainNetwork,
    demand: dict[str, DemandGenerator],
    policies: dict[str, ReplenishmentPolicy],
    controlled_nodes: str | list[str],
    max_order: float,
    n_periods: int = 52,
    action_type: ActionType = "continuous",
    n_discrete_bins: int = 21,
    demand_history_window: int = 8,
    cost_weights: dict[str, float] | None = None,
    reward_scope: Literal["controlled", "network"] = "controlled",
    disruptions: list[DisruptionEvent] | None = None,
    seed: int | None = None,
    render_mode: str | None = None,
) -> None
```

| Param | Type | Default | Description |
|---|---|---|---|
| `network` | `SupplyChainNetwork` | required | Topology; rebuilt to initial state (nodes/edges/policies `.reset()`) every `reset()` call — the same objects are reused across episodes. |
| `demand` | `dict[str, DemandGenerator]` | required | Node id -> demand generator, as in `SimulationEngine`. |
| `policies` | `dict[str, ReplenishmentPolicy]` | required | Node id -> policy for every *uncontrolled* node. Controlled nodes should have no entry (or, if present, it's never consulted). |
| `controlled_nodes` | `str \| list[str]` | required | Node id(s) the agent places orders for. |
| `max_order` | `float` | required | Upper bound on order quantity per controlled node, per action. |
| `n_periods` | `int` | `52` | Episode length in periods. |
| `action_type` | `Literal["continuous","discrete"]` | `"continuous"` | `ValueError` for any other value. |
| `n_discrete_bins` | `int` | `21` | Number of evenly-spaced order-quantity bins from 0 to `max_order`, only used when `action_type="discrete"`. |
| `demand_history_window` | `int` | `8` | Periods of each controlled node's recent demand included in the observation. |
| `cost_weights` | `dict[str, float] \| None` | `None` | `{"holding": ..., "backlog": ..., "transportation": ...}`. Missing keys default to `1.0` (holding, backlog) / `0.0` (transportation). |
| `reward_scope` | `Literal["controlled","network"]` | `"controlled"` | `"controlled"`: reward counts only the controlled node(s)' own cost. `"network"`: sums cost across every node. `ValueError` for any other value. |
| `disruptions` | `list[DisruptionEvent] \| None` | `None` (-> `[]`) | Disruption events applied during the run. |
| `seed` | `int \| None` | `None` | Default seed used when `reset()` is called without one. |
| `render_mode` | `str \| None` | `None` | Must be `None` or `"ansi"` (`ValueError` otherwise). |

**Observation space**: `spaces.Box(low=-obs_bound, high=obs_bound, shape=(obs_dim,),
dtype=np.float32)`, where `obs_dim = n_controlled * (4 + demand_history_window) + 1` and
`obs_bound = max(1e4, max_order * 100)` (a generous, non-clipping descriptive bound — values
are **not** clipped to this range at runtime). For each controlled node, in
`controlled_nodes` order: `[on_hand_qty, backlog, pipeline, inventory_position]` (4 values)
followed by a zero-padded (left-padded with zeros if shorter than the window) trailing
window of `demand_history_window` recent observed-demand values. The vector ends with one
final scalar: `t / n_periods` (normalized period index).

**Action space**:
- `"continuous"`: `spaces.Box(low=0.0, high=max_order, shape=(n_controlled,),
  dtype=np.float32)`.
- `"discrete"`: `spaces.MultiDiscrete([n_discrete_bins] * n_controlled)`; `bin_values =
  np.linspace(0.0, max_order, n_discrete_bins, dtype=np.float32)` — an action index selects
  one of these evenly-spaced order quantities per controlled node.

**Reward** (`_reward`): `reward = -total`, where for each relevant history row (all rows if
`reward_scope="network"`, only the controlled nodes' rows if `"controlled"`):
```
total += cost_weights["holding"] * holding_cost + cost_weights["backlog"] * backlog_cost
total += cost_weights["transportation"] * transport_cost   # only if the weight is truthy (non-zero)
```
where `transport_cost = fulfilled * avg(cost_per_unit across the node's outbound edges)`
(via `_transport_cost`, `0.0` for a node with no successors).

**Which nodes can be controlled**: any node id(s) passed as `controlled_nodes` (str or
list) — every other node in the network keeps deciding via its own configured
`ReplenishmentPolicy` exactly as in `SimulationEngine`; only the controlled node(s)' order
quantity is replaced by the action each step, via `SimulationEngine.step`'s `overrides`
argument.

**`reset(*, seed=None, options=None) -> tuple[np.ndarray, dict[str, Any]]`**: builds a fresh
`SimulationEngine` (reusing `self.network`/`demand`/`policies`/`disruptions`, with
`seed=seed if seed is not None else self.default_seed`), calls `engine.begin()`, resets
`self._t = 0`, returns `(obs, {})`.

**`step(action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]`**:
raises `RuntimeError` if called before `reset()`. Decodes the action into order quantities
(`_decode_action` — clips to `[0, max_order]` for continuous, maps bin indices to
`bin_values` for discrete, clipping the index into `[0, n_discrete_bins - 1]` first), builds
`overrides = dict(zip(controlled_nodes, order_quantities))`, calls `engine.step(t,
overrides=overrides)`, computes reward, increments `self._t`. `truncated = self._t >=
n_periods`; `terminated` is always `False` (no early-termination condition exists).
`info = {"period_rows": period_rows}` — the raw history rows from that step.

**`render() -> str | None`**: only produces output if `render_mode == "ansi"` and an engine
exists; prints `period {t}/{n_periods}` plus, per controlled node, `on_hand`/`backlog`.

**`close() -> None`**: sets `self.engine = None`.

**Helper method**:
```python
def decode_observation(self, obs: np.ndarray) -> dict[str, Any]
```
Splits a flat observation vector back into named fields (so callers like
`chainsim.ai.baselines` don't hardcode the layout). Returns:
```python
{
  "on_hand": list[float],              # one per controlled node
  "backlog": list[float],
  "pipeline": list[float],
  "inventory_position": list[float],
  "demand_history": list[np.ndarray],  # one array per controlled node
  "t_normalized": float,
}
```

No separate wrapper classes exist in this module — `SupplyChainEnv` is the only public
symbol besides the `ActionType` alias.

### 4.2 `forecaster.py`

#### `Forecaster` — ABC

```python
class Forecaster(ABC):
    @abstractmethod
    def fit(self, history: np.ndarray) -> None: ...
    @abstractmethod
    def predict(self, horizon: int) -> np.ndarray: ...
```
`fit(history)` takes a 1-D `np.ndarray` (or array-like, coerced via `np.asarray`) of
historical demand observations. `predict(horizon)` returns a length-`horizon` array of
point forecasts; implementations raise `RuntimeError` if called before `fit`.

#### `NaiveForecaster(Forecaster)`

```python
def __init__(self) -> None
```
`fit`: stores `self._last = float(history[-1])` (raises `ValueError` if `history` is
empty). `predict(horizon)`: `np.full(horizon, self._last)` — repeats the last observed
value for the whole horizon.

#### `MovingAverageForecaster(Forecaster)`

```python
def __init__(self, window: int = 7) -> None  # raises ValueError if window <= 0
```
`fit`: `self._level = float(history[-window:].mean())` (uses all of `history` if shorter
than `window`). `predict(horizon)`: flat `np.full(horizon, self._level)`.

#### `ExponentialSmoothingForecaster(Forecaster)`

```python
def __init__(self, alpha: float = 0.3) -> None  # raises ValueError unless 0 < alpha <= 1
```
Single (simple) exponential smoothing: `level_t = alpha*x_t + (1-alpha)*level_{t-1}`,
initialized `level = history[0]`, iterated over the rest of `history`. `predict(horizon)`:
flat `np.full(horizon, self._level)`.

#### Error metric functions

| Function | Signature | Definition |
|---|---|---|
| `mae` | `(actual: np.ndarray, predicted: np.ndarray) -> float` | `mean(abs(actual - predicted))` |
| `rmse` | `(actual: np.ndarray, predicted: np.ndarray) -> float` | `sqrt(mean((actual - predicted)**2))` |
| `mape` | `(actual: np.ndarray, predicted: np.ndarray) -> float` | `mean(abs((actual - predicted) / actual)) * 100`, computed **only** over periods where `actual != 0` (zero-actual periods excluded rather than producing inf/nan); returns `nan` if every period has `actual == 0`. |
| `forecast_accuracy` | `(actual, predicted) -> dict[str, float]` | `{"mae": ..., "rmse": ..., "mape": ...}` — bundles all three. |

**Wrapping an external model**: subclass `Forecaster` and implement `fit`/`predict` against
whatever external library (Prophet, LightGBM, a foundation model) — no ABC method beyond
these two is required, and nothing in the interface assumes a particular internal
representation.

### 4.3 `baselines.py`

#### `Agent` — `Protocol`

```python
class Agent(Protocol):
    def act(self, observation: np.ndarray) -> np.ndarray: ...
```
Minimal structural interface `evaluate_agent` needs.

#### `OrderUpToAgent`

```python
def __init__(self, env: SupplyChainEnv, S: float | list[float]) -> None
def act(self, observation: np.ndarray) -> np.ndarray
```

| Param | Type | Description |
|---|---|---|
| `env` | `SupplyChainEnv` | The environment this agent acts in (used to decode observations and know the action space's shape/bounds). |
| `S` | `float \| list[float]` | Order-up-to level(s). A single number applies to every controlled node; a list applies one per node, in `env.controlled_nodes` order. Raises `ValueError` if a list's length doesn't match the number of controlled nodes. |

`act(observation)`: decodes the observation via `env.decode_observation`, computes `order =
max(0, S - inventory_position)` per controlled node, clips each to `env.max_order`. If
`env.action_type == "discrete"`, maps each order to the nearest `bin_values` index
(`np.argmin(np.abs(bins - o))`), returning an `int64` array; otherwise returns a
`float32` array directly.

#### `RandomAgent`

```python
def __init__(self, env: SupplyChainEnv) -> None
def act(self, observation: np.ndarray) -> np.ndarray:
    return self.env.action_space.sample()
```
Samples a uniformly random action from the env's action space each step — a lower-bound
baseline.

#### `evaluate_agent`

```python
def evaluate_agent(
    env: SupplyChainEnv, agent: Any, n_episodes: int = 20, seed: int = 0
) -> dict[str, Any]
```

| Param | Type | Default | Description |
|---|---|---|---|
| `env` | `SupplyChainEnv` | required | Environment to evaluate in. |
| `agent` | `Any` | required | Anything exposing `.act(obs) -> action` (`OrderUpToAgent`, `RandomAgent`) **or** `.predict(obs, deterministic=True) -> (action, state)` — the Stable-Baselines3 calling convention. |
| `n_episodes` | `int` | `20` | Number of episodes to run. |
| `seed` | `int` | `0` | Episode `e` is reset with seed `seed + e`. |

Dispatch (`_get_action`, private): if `agent` has a `.predict` attribute, calls
`agent.predict(observation, deterministic=True)` and unpacks `(action, _state)` — this is
how an SB3 model plugs in with **zero adapter code**; otherwise calls `agent.act(observation)`.

Runs `n_episodes` full episodes to termination/truncation, summing reward per episode.
Returns:
```python
{
  "mean_reward": float,
  "std_reward": float,
  "episode_rewards": list[float],
  "n_episodes": int,
}
```

---

## Section 5: Scenarios (`chainsim/scenarios/`)

### `_common.py` / `ScenarioConfig`

Leading-underscore module — **not public API**, but documented here since every scenario
module depends on it.

#### `ScenarioConfig` (`@dataclass`)

```python
@dataclass
class ScenarioConfig:
    name: str
    description: str
    network: SupplyChainNetwork
    demand: dict[str, DemandGenerator]
    policies: dict[str, ReplenishmentPolicy]
    disruptions: list[DisruptionEvent] = field(default_factory=list)
    n_periods: int = 52
    seed: int | None = 0
```

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | Short scenario name, printed in the report header. |
| `description` | `str` | required | One-paragraph summary of what the scenario exercises. |
| `network` | `SupplyChainNetwork` | required | Topology to simulate. |
| `demand` | `dict[str, DemandGenerator]` | required | Node id -> demand generator. |
| `policies` | `dict[str, ReplenishmentPolicy]` | required | Node id -> replenishment policy. |
| `disruptions` | `list[DisruptionEvent]` | `[]` | Disruption events. |
| `n_periods` | `int` | `52` | Episode length in periods. |
| `seed` | `int \| None` | `0` | Seed for demand generation / stochastic lead times. |

```python
def build_engine(self) -> SimulationEngine
```
Constructs a `SimulationEngine` from the config's fields (seed included).

```python
def run_scenario(config: ScenarioConfig) -> tuple[SimulationEngine, pd.DataFrame]
```
`engine = config.build_engine(); history = engine.run(); return engine, history`.

```python
def print_scenario_report(config: ScenarioConfig, engine: SimulationEngine, history: pd.DataFrame) -> None
```
Prints a standard header (`name`, `description`, periods/seed), the `per_node_kpis` table
(rounded to 3 decimals), and the `summarize()` network-summary dict — each scenario's
`main()` follows this with its own scenario-specific narrative.

---

### 5.1 `retail_replenishment.py`

**Topology**: `Supplier -> DC -> {Store_Flagship, Store_Suburban, Store_Outlet}` (5 nodes:
1 `Supplier`, 1 `DistributionCenter`, 3 `Retailer`s; 4 edges — Supplier→DC, DC→each store).
DC is a multi-successor node (proportional shipment split exercised).

| Node | Type | holding_cost | backlog_cost | capacity | initial_inventory | Lead time in |
|---|---|---|---|---|---|---|
| `Supplier` | `Supplier` | `0.0` | — | `inf` (default) | `{DEFAULT_SKU: 15_000}` | — |
| `DC` | `DistributionCenter` | `0.4` | — | `400` | `{DEFAULT_SKU: 300}` | 3 (rail) from Supplier |
| `Store_Flagship` | `Retailer` | `1.2` | `8.0` | — | `{DEFAULT_SKU: 120}` (base*2, base=60) | 1 (truck) from DC |
| `Store_Suburban` | `Retailer` | `1.2` | `8.0` | — | `{DEFAULT_SKU: 70}` (base=35) | 2 (truck) from DC |
| `Store_Outlet` | `Retailer` | `1.2` | `8.0` | — | `{DEFAULT_SKU: 36}` (base=18) | 2 (truck) from DC |

**Demand**: `SeasonalDemand` at each store: `base`/`amplitude` per the table below,
`period_length=13` (`SEASON_LENGTH`, a "quarterly-ish cycle"), `noise_std=3.0`
(`DEMAND_NOISE`), applied to all three stores.

| Store | base | amplitude |
|---|---|---|
| `Store_Flagship` | 60.0 | 20.0 |
| `Store_Suburban` | 35.0 | 10.0 |
| `Store_Outlet` | 18.0 | 6.0 |

**Policies**: `BaseStockPolicy(service_level=0.95)` (`SERVICE_LEVEL`) everywhere:
- `DC`: `mean_demand=113, std_demand=25, lead_time=3`.
- Each store: `mean_demand=base, std_demand=max(amplitude/2, DEMAND_NOISE), lead_time=<its lead time from DC>`.

**Disruptions**: two `DemandShock` "promo" windows (`PROMOS`):
1. Spring promo — `start=10, duration=2, multiplier=2.5`, affecting `Store_Flagship` and
   `Store_Suburban`.
2. Holiday promo — `start=47, duration=2, multiplier=3.0`, storewide (all 3 stores).

Implemented as one `DemandShock` per `(promo, store)` pair.

**Default simulation settings**: `n_periods=52` (`N_PERIODS`), `seed=0` (`SEED`).

**Scenario-specific config options**: `build_scenario(seed: int = SEED) -> ScenarioConfig`
— only `seed` is parameterized. `main()` additionally calls `_print_promo_impact(history)`,
printing per-promo demand/service-level comparisons.

---

### 5.2 `pharma_cold_chain.py`

**Topology**: `Plant -> Cold_DC -> Hospital` (serial chain, daily periods). `Plant` is a
`Manufacturer`, `Cold_DC` a `DistributionCenter`, `Hospital` a `Retailer`. All three are
**perishable** (`shelf_life` set).

| Node | Type | holding_cost | backlog_cost | capacity | shelf_life | initial_inventory | Lead time in / mode |
|---|---|---|---|---|---|---|---|
| `Plant` | `Manufacturer` | `0.5` | — | `200` | `45` (`DC_SHELF_LIFE`) | `{DEFAULT_SKU: 400}` | — |
| `Cold_DC` | `DistributionCenter` | `1.0` | — | — | `45` | `{DEFAULT_SKU: 200}` | 2 (air) from Plant |
| `Hospital` | `Retailer` | `2.0` | `50.0` | — | `15` (`HOSPITAL_SHELF_LIFE`) | `{DEFAULT_SKU: 280}` (deliberate legacy stockpile) | 1 (air) from Cold_DC |

**Demand**: `StationaryDemand(mean=15.0, distribution="poisson")` (`DAILY_DEMAND_MEAN`) at
`Hospital` only.

**Policies**: `BaseStockPolicy(service_level=0.99)` (`TARGET_SERVICE_LEVEL`, "regulatory-style"):
- `Hospital`: `mean_demand=15.0, std_demand=sqrt(15.0), lead_time=1` (`HOSPITAL_LEAD_TIME`).
- `Cold_DC`: `mean_demand=15.0, std_demand=sqrt(15.0), lead_time=2` (`DC_LEAD_TIME`).
- `Plant`: `mean_demand=15.0, std_demand=sqrt(15.0), lead_time=1`.

**Disruptions**: one `DemandShock` — a clinic closure: `target_id="Hospital", start=40,
duration=14, multiplier=0.25` (`CLOSURE_START/DURATION/DEMAND_MULTIPLIER`) — demand cut to
25% for two weeks.

**Default simulation settings**: `n_periods=90` (`N_PERIODS`, "~3 months, daily periods"),
`seed=0`.

**Scenario-specific config options**: `build_scenario(seed: int = SEED)` — only `seed`
parameterized. `main()` additionally calls `_print_compliance_check(history)`, reporting
per-node achieved service level vs. the 99% target (PASS/FAIL), waste totals/rates, and a
narrative about each node's one-time legacy-stockpile write-off.

---

### 5.3 `manufacturing_jit.py`

**Topology**: `Supplier -> Plant -> Line` (serial chain, daily periods). `Plant` is a
`Manufacturer` (capacity-constrained), `Line` is a `Retailer` (models an assembly line
consuming parts).

| Node | Type | holding_cost | backlog_cost | capacity | initial_inventory | Lead time in / mode |
|---|---|---|---|---|---|---|
| `Supplier` | `Supplier` | `0.05` | — | `inf` (default) | `{DEFAULT_SKU: 5_000}` | — |
| `Plant` | `Manufacturer` | `0.3` | — | `55` (`PLANT_CAPACITY`) | `{DEFAULT_SKU: 80}` | 2 (truck) from Supplier |
| `Line` | `Retailer` | `1.0` | `15.0` | — | `{DEFAULT_SKU: JIT_R + 5 = 95}` | 1 (truck) from Plant |

**Demand**: `StationaryDemand(mean=40.0, distribution="poisson")` (`DAILY_DEMAND_MEAN`) at
`Line` only.

**Policies** (parameterized by `build_scenario(seed=SEED, line_policy: str = "jit")`):
- `line_policy="jit"` (default): `Line` uses `RQPolicy(R=90, Q=40)` (`JIT_R`, `JIT_Q`) —
  "small, frequent orders".
- `line_policy="buffered"`: `Line` uses `OrderUpTo(S=400)` (`BUFFERED_S`) — a conventional
  ~10-days-of-demand buffer.
- `Plant` always uses `OrderUpTo(S=PLANT_CAPACITY * 3 = 165)`.
- Raises `ValueError` for any other `line_policy` value.

**Disruptions**: one `NodeOutage`: `target_id="Plant", start=45, duration=5`
(`OUTAGE_START/DURATION`) — a 5-day Plant outage.

**Default simulation settings**: `n_periods=90` (`N_PERIODS`, "~3 months, daily periods"),
`seed=0`.

**Scenario-specific config options**: `build_scenario(seed: int = SEED, line_policy: str =
"jit")` — `line_policy` selects between `"jit"` and `"buffered"`. `main()` additionally
calls `_print_disruption_impact(history)` (backlog before/during/peak during the outage)
and `_compare_jit_vs_buffered()`, which re-runs the scenario under both policies and prints
a side-by-side comparison of avg on-hand, peak backlog during the outage, and total backlog
cost.

---

### 5.4 `global_commodity_flow.py`

**Topology** (largest scenario, weekly periods): two overseas `Supplier`s feed one
`Global_Hub` (`DistributionCenter`, multi-predecessor), which redistributes to two
`Regional_DC`s (`DistributionCenter`), each feeding one `Market` (`Retailer`). 7 nodes total
(`Supplier_Asia`, `Supplier_Europe`, `Global_Hub`, `Regional_DC_NA`, `Regional_DC_EU`,
`Market_NA`, `Market_EU`), 6 edges. `Global_Hub` has 2 predecessors and 2 successors,
exercising both documented approximations (even order-split upstream, proportional
shipment-split downstream — see §2.8).

| Node | Type | holding_cost | backlog_cost | capacity | initial_inventory | Lead time in / mode / capacity |
|---|---|---|---|---|---|---|
| `Supplier_Asia` | `Supplier` | `0.0` | — | `inf` | `{DEFAULT_SKU: 50_000}` | — |
| `Supplier_Europe` | `Supplier` | `0.0` | — | `inf` | `{DEFAULT_SKU: 50_000}` | — |
| `Global_Hub` | `DistributionCenter` | `0.3` | — | `2000` | `{DEFAULT_SKU: S("Global_Hub")}` | 21d (ship) from Asia, cap 500; 14d (ship) from Europe, cap 500 |
| `Regional_DC_NA` | `DistributionCenter` | `0.6` | — | — | `{DEFAULT_SKU: S("Regional_DC_NA")}` | 5d (rail) from Hub |
| `Regional_DC_EU` | `DistributionCenter` | `0.6` | — | — | `{DEFAULT_SKU: S("Regional_DC_EU")}` | 3d (truck) from Hub |
| `Market_NA` | `Retailer` | `1.0` | `6.0` | — | `{DEFAULT_SKU: S("Market_NA")}` | 2d (truck) from Regional_DC_NA |
| `Market_EU` | `Retailer` | `1.0` | `6.0` | — | `{DEFAULT_SKU: S("Market_EU")}` | 2d (truck) from Regional_DC_EU |

`S(node)` = that node's own `BaseStockPolicy.S` (steady-state order-up-to level) — every
node is deliberately seeded at its own steady state to avoid a multi-week cold-start
stockout swamping the disruption effects the scenario studies (lead times up to 21 days).

Both international lanes (`Supplier_Asia->Global_Hub`, `Supplier_Europe->Global_Hub`) are
capacity-capped at `INTL_LANE_CAPACITY = 500` (to bound/stabilize recovery dynamics — see
module docstring).

**Demand**: `StationaryDemand(distribution="poisson")` at both markets: `Market_NA`
`mean=150`, `Market_EU` `mean=120`.

**Policies**: `BaseStockPolicy(service_level=0.95)` (`SERVICE_LEVEL`, via `_make_policy`) at
every non-Supplier node, parameterized by `_POLICY_PARAMS`:

| Node | mean_demand | std_demand | lead_time |
|---|---|---|---|
| `Market_NA` | 150 | `sqrt(150)` | 2 |
| `Market_EU` | 120 | `sqrt(120)` | 2 |
| `Regional_DC_NA` | 150 | 40 | 5 |
| `Regional_DC_EU` | 120 | 35 | 3 |
| `Global_Hub` | 270 | 60 | 17 |

**Disruptions** (three geopolitical-style events over the year):
1. `LeadTimeShock(target_id="Supplier_Asia->Global_Hub", start=10, duration=6,
   multiplier=2.0)` — port congestion (`PORT_CONGESTION_START/DURATION/MULTIPLIER`).
2. `CapacityReduction(target_id="Global_Hub", start=30, duration=4, factor=0.15)` — labor
   dispute (`LABOR_DISPUTE_START/DURATION/FACTOR`), Hub throughput cut to 15%.
3. `NodeOutage(target_id="Supplier_Europe", start=45, duration=8)` — sanctions-style
   supplier cutoff (`SANCTIONS_START/DURATION`), Europe supplier fully cut off for 8 weeks.

**Default simulation settings**: `n_periods=65` (`N_PERIODS`, weekly — long enough for all
three events plus recovery), `seed=0`.

**Scenario-specific config options**: `build_scenario(seed: int = SEED)` — only `seed`
parameterized. `main()` additionally calls `_print_disruption_impact(history)`, which prints
the disruption timeline, each node's backlog window/peak (or "never backlogged"), and two
explanatory notes: (a) consequences lag well behind each event's own calendar window given
the long lead times, so effects overlap rather than resolving cleanly between events; (b)
because of the even-order-split-across-predecessors approximation, `Global_Hub` keeps
sending half its order to the sanctioned `Supplier_Europe` rather than automatically
rerouting through `Supplier_Asia` — so the effective supply cut is deeper than "lose one of
two suppliers" would suggest.

---

## Section 6: IO / Configuration (`chainsim/io/`)

**Status: not yet implemented.** Both submodules currently contain only a module
docstring — no classes, functions, or other code.

### 6.1 `config_schema.py`

Full file contents:
```python
"""Pydantic models for scenario and network configuration.

To be implemented alongside the domain layer. All scenario configs, node
configs, and policy configs are defined as `pydantic.BaseModel` subclasses
so they can be loaded from YAML/JSON and validated automatically.
"""
```
No Pydantic models exist yet. There is currently no defined YAML/JSON scenario config
schema/structure to document — scenarios are built entirely in Python (see §5), and
`chainsim.io` is a stated future direction, not a usable feature today.

### 6.2 `loaders.py`

Full file contents:
```python
"""Functions to load networks and scenarios from YAML, JSON, or CSV files.

Reads files validated against the schemas in `chainsim.io.config_schema`
and constructs the corresponding `chainsim.core` domain objects.
"""
```
No loader functions exist yet. No file formats are currently supported by this module (the
docstring names YAML/JSON/CSV as the intended future formats, but nothing is implemented).

**Documentation guidance**: do not describe `chainsim.io` as usable in user-facing docs
beyond noting it as planned/future work. The only current way to build a scenario/network is
directly in Python via `chainsim.core` classes (or one of the four pre-built
`chainsim.scenarios` modules).

---

## Section 7: Dashboard (`dashboard/`)

A Streamlit app (`streamlit run dashboard/app.py`) that only calls chainsim's public API
(`chainsim.core`, `chainsim.metrics`, `chainsim.scenarios`) — never internals — per every
module's own docstring.

### Pages

| File | Page title | Purpose |
|---|---|---|
| `dashboard/app.py` | — (home page, `st.title("📦 chainsim dashboard")`) | Landing page: workflow explanation + session status (whether a scenario is configured, how many runs exist). |
| `dashboard/pages/1_Build_Scenario.py` | "1. Build Scenario" | Load one of the 4 pre-built scenarios, or configure a custom serial `Supplier -> DC... -> Retailer` chain via widgets. |
| `dashboard/pages/2_Run_Simulation.py` | "2. Run Simulation" | Steps the loaded scenario's `SimulationEngine` one period at a time (`begin()`/`step()`/`finish()`) with a live progress bar; stores the result as a `RunRecord`. |
| `dashboard/pages/3_Results_Dashboard.py` | "3. Results Dashboard" | KPI cards, Plotly time-series charts, network topology graph, per-node KPI table, for one selected run. |
| `dashboard/pages/4_Compare_Scenarios.py` | "4. Compare Scenarios" | Side-by-side comparison (`compare_scenarios`) and per-node KPI comparison across 2+ selected runs, as tables + Plotly bar charts. |

### Streamlit session state keys

Defined in `dashboard/state.py`:

| Key constant | Value | Holds |
|---|---|---|
| `CONFIG_KEY` | `"chainsim_scenario_config"` | A single `ScenarioBundle` (the currently configured scenario) — set via `set_scenario_config`, read via `get_scenario_config`/`require_scenario_config`. |
| `RUNS_KEY` | `"chainsim_runs"` | `list[RunRecord]` — all completed runs this session; accessed via `get_runs`/`add_run`/`clear_runs`/`require_runs`. |

Also used directly by `1_Build_Scenario.py` (not routed through `state.py`):
`st.session_state["custom_disruptions"]` — a `list[dict]` of in-progress custom disruption
configs (`type`, `target`, `start`, `duration`, `magnitude`) being assembled via a form,
before being converted into real `DisruptionEvent` objects on scenario build.

#### `dashboard/state.py` dataclasses

```python
@dataclass
class ScenarioBundle:
    name: str
    description: str
    network: SupplyChainNetwork
    demand: dict[str, DemandGenerator]
    policies: dict[str, ReplenishmentPolicy]
    disruptions: list[DisruptionEvent] = field(default_factory=list)
    n_periods: int = 52
    seed: int | None = 0
```

```python
@dataclass
class RunRecord:
    label: str
    history: pd.DataFrame
    network: SupplyChainNetwork
    n_periods: int
    seed: int | None
    source: str
    created_at: datetime = field(default_factory=datetime.now)
```

Helper functions in `state.py`: `get_scenario_config()`, `set_scenario_config(bundle)`,
`get_runs()`, `add_run(record)`, `clear_runs()`, `run_label(base, existing)` (dedupes a
label against existing run labels by appending `" (2)"`, `" (3)"`, ...),
`require_scenario_config()` (warns + returns `None` if unset), `require_runs()` (warns +
returns `None` if empty), `format_kpi_value(value)` (formats a float with thousands
separators/2 decimals, else `str(value)`).

### Visualization libraries

- **Plotly** (`plotly.express`, `plotly.graph_objects`) — used for time-series line charts
  (`3_Results_Dashboard.py`), the network topology graph
  (`dashboard/components/network_graph.py`), and comparison bar charts
  (`4_Compare_Scenarios.py`).
- **Streamlit** built-ins — `st.metric` (KPI cards), `st.dataframe`/`st.table` for tabular
  data, `st.progress` for the run progress bar.
- `pyvis` is declared as a `dashboard` extra dependency in `pyproject.toml` but is **not
  actually imported or used** by any dashboard code read in this pass — the network graph
  is Plotly-based (`dashboard/components/network_graph.py`).

### Dashboard components

#### `dashboard/components/kpi_cards.py`

```python
def render_kpi_cards(history: pd.DataFrame, network: SupplyChainNetwork) -> None
```
Renders `chainsim.metrics.summarize(history, network)` as two rows of 4 `st.metric` cards:
row 1 = Total cost, Fill rate, Service level, Total waste; row 2 = Holding cost, Backlog
cost, Transportation cost, Avg bullwhip ratio (shown as `"n/a"` if `NaN`).

#### `dashboard/components/network_graph.py`

```python
def render_network_graph(
    network: SupplyChainNetwork,
    history: pd.DataFrame,
    metric: str = "on_hand",
    period: int | None = None,
) -> go.Figure
```
Builds a Plotly figure of the network topology, laid out left-to-right by echelon depth
(`_layered_positions`: x = longest-path depth from a source, y = spread among same-depth
nodes, centered). Node size/color map to `metric` (a `history` column) — either the run
average (`period=None`, default) or one specific period's value. Edges are drawn as lines
with arrow annotations, with hover text showing the lead time (when not a stochastic
callable). Node markers use a `"Blues"` colorscale with a colorbar.

```python
def _layered_positions(network: SupplyChainNetwork) -> dict[str, tuple[float, float]]
```
Private helper computing the `(x, y)` layout described above.

### Configuration options exposed in the UI

**Build Scenario page** (`1_Build_Scenario.py`):
- Scenario source: "Pre-built scenario" (choose from the 4 named scenarios, plus a
  `line_policy` radio — "jit"/"buffered" — shown only for Manufacturing JIT) or "Custom
  serial chain".
- Custom chain: number of echelons (2–6 slider); per-node holding cost, backlog cost
  (retailer only), optional capacity; per-edge lead time; demand type (Stationary/
  Seasonal/Trend) with matching parameter widgets (mean/std/distribution,
  base/amplitude/period_length/noise_std, base/trend/noise_std respectively); policy type
  (OrderUpTo / (s,S) / (R,Q) / BaseStock) with matching parameter widgets; a disruption
  builder form (type: NodeOutage/CapacityReduction/LeadTimeShock/DemandShock; target
  selectable from nodes and/or edges depending on type; start period; duration;
  factor/multiplier) that accumulates entries in `st.session_state["custom_disruptions"]`;
  run settings (number of periods, random seed).

**Run Simulation page** (`2_Run_Simulation.py`): periods, seed, run label (all pre-filled
from the loaded `ScenarioBundle`, editable) — a run deep-copies the network
(`copy.deepcopy(bundle.network)`) so past runs stay safe to inspect regardless of later runs'
node/edge state mutation.

**Results Dashboard page** (`3_Results_Dashboard.py`): run selector; time-series metric
selector (`on_hand`, `backlog`, `pipeline`, `inventory_position`, `order_placed`,
`fulfilled`, `external_demand`) and node multiselect; network-graph metric selector
(`on_hand`, `backlog`, `pipeline`, `order_placed`, `fulfilled`) and an optional
"show a specific period instead of the run average" toggle + period slider.

**Compare Scenarios page** (`4_Compare_Scenarios.py`): multiselect of ≥2 runs to compare;
fixed overall-comparison metrics (`total_cost`, `fill_rate`, `service_level`,
`total_waste`); per-node comparison metric selector (`total_cost`, `avg_on_hand`,
`avg_backlog`, `fill_rate`, `service_level`, `bullwhip_ratio`, `total_waste`).
