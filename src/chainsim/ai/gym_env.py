"""SupplyChainEnv: a Gymnasium-compatible environment wrapping the simulation engine.

Observation: for each controlled node, its on-hand inventory, backlog,
pipeline (on-order), and inventory position, plus a rolling window of its
recently observed demand and the normalized period index. Action: order
quantities for the controlled node(s) — continuous (``Box``) by default, or
discrete (``MultiDiscrete`` over evenly-spaced order-quantity bins) via
``action_type="discrete"``. Reward: negative total cost per step, with
configurable weights between holding, backlog, and (edge ``cost_per_unit``
based) transportation cost.

By default, reward only counts cost incurred *at the controlled node(s)*
(``reward_scope="controlled"``) — the sane default for credit assignment,
since the agent has no way to influence, say, an upstream supplier's own
warehousing cost. Pass ``reward_scope="network"`` to instead sum cost
across every node each period.

Every *other* node in the network keeps deciding via its own
:class:`~chainsim.core.policies.ReplenishmentPolicy` exactly as in
:class:`~chainsim.core.engine.SimulationEngine`; only the controlled
node(s)' order quantity is replaced by the action each step, via the
engine's :meth:`~chainsim.core.engine.SimulationEngine.step` ``overrides``.

Must pass ``gymnasium.utils.env_checker.check_env()`` — see
``tests/test_gym_env.py``.
"""

from __future__ import annotations

from typing import Any, Literal

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from chainsim.core.demand import DemandGenerator
from chainsim.core.disruptions import DisruptionEvent
from chainsim.core.engine import SimulationEngine
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.nodes import DEFAULT_SKU
from chainsim.core.policies import ReplenishmentPolicy

ActionType = Literal["continuous", "discrete"]


class SupplyChainEnv(gym.Env):
    """A Gymnasium environment: an RL agent controls one or more nodes' order
    quantities each period; every other node follows its configured policy.

    Args:
        network: Topology to simulate. Rebuilt to its initial state (nodes,
            edges, policies all call ``.reset()``) every ``reset()`` call, so
            the same objects are reused across episodes.
        demand: Maps node id -> demand generator, as in ``SimulationEngine``.
        policies: Maps node id -> policy for every *uncontrolled* node.
            Controlled nodes should not have an entry here (or, if present,
            it is simply never consulted while the env overrides them).
        controlled_nodes: Node id(s) the agent places orders for.
        max_order: Upper bound on the order quantity an action can request,
            per controlled node.
        n_periods: Episode length in periods.
        action_type: ``"continuous"`` (a ``Box`` action space) or
            ``"discrete"`` (a ``MultiDiscrete`` over ``n_discrete_bins``
            evenly-spaced order quantities from 0 to ``max_order``).
        n_discrete_bins: Number of bins when ``action_type="discrete"``.
        demand_history_window: Periods of each controlled node's own recent
            demand history included in the observation.
        cost_weights: Weights ``{"holding": ..., "backlog": ..., "transportation": ...}``
            applied to each period's cost before negating it into the reward.
            Missing keys default to ``1.0`` for holding/backlog and ``0.0``
            for transportation.
        reward_scope: ``"controlled"`` (default) counts only the controlled
            node(s)' own cost each period; ``"network"`` sums cost across
            every node in the network.
        disruptions: Disruption events to apply during the run.
        seed: Default seed used when ``reset()`` is called without one.
    """

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
    ) -> None:
        super().__init__()
        if action_type not in ("continuous", "discrete"):
            raise ValueError(f"unknown action_type: {action_type!r}")
        if reward_scope not in ("controlled", "network"):
            raise ValueError(f"unknown reward_scope: {reward_scope!r}")
        if render_mode is not None and render_mode not in self.metadata["render_modes"]:
            raise ValueError(f"unsupported render_mode: {render_mode!r}")

        self.network = network
        self.demand = demand
        self.policies = policies
        self.controlled_nodes = (
            [controlled_nodes] if isinstance(controlled_nodes, str) else list(controlled_nodes)
        )
        self.max_order = float(max_order)
        self.n_periods = n_periods
        self.action_type = action_type
        self.n_discrete_bins = n_discrete_bins
        self.demand_history_window = demand_history_window
        weights = cost_weights or {}
        self.cost_weights = {
            "holding": weights.get("holding", 1.0),
            "backlog": weights.get("backlog", 1.0),
            "transportation": weights.get("transportation", 0.0),
        }
        self.reward_scope = reward_scope
        self.disruptions = disruptions or []
        self.default_seed = seed
        self.render_mode = render_mode

        n_controlled = len(self.controlled_nodes)
        self.bin_values: np.ndarray | None = None
        if action_type == "continuous":
            self.action_space = spaces.Box(
                low=0.0, high=self.max_order, shape=(n_controlled,), dtype=np.float32
            )
        else:
            self.action_space = spaces.MultiDiscrete([n_discrete_bins] * n_controlled)
            self.bin_values = np.linspace(0.0, self.max_order, n_discrete_bins, dtype=np.float32)

        # A generous but finite bound: inventory/backlog/pipeline quantities can
        # get large under a bad policy but shouldn't approach this in practice.
        # Gymnasium recommends bounded Box spaces (some RL libraries warn or
        # perform worse with unbounded ones); values aren't clipped to this
        # range, it's only descriptive.
        obs_bound = max(1e4, self.max_order * 100)
        obs_dim = n_controlled * (4 + demand_history_window) + 1
        self.observation_space = spaces.Box(
            low=-obs_bound, high=obs_bound, shape=(obs_dim,), dtype=np.float32
        )

        self.engine: SimulationEngine | None = None
        self._t = 0

    # -- Gym API --------------------------------------------------------------

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        run_seed = seed if seed is not None else self.default_seed

        self.engine = SimulationEngine(
            network=self.network,
            demand=self.demand,
            policies=self.policies,
            disruptions=self.disruptions,
            n_periods=self.n_periods,
            seed=run_seed,
        )
        self.engine.begin()
        self._t = 0

        return self._get_obs(), {}

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if self.engine is None:
            raise RuntimeError("call reset() before step()")

        order_quantities = self._decode_action(action)
        overrides = dict(zip(self.controlled_nodes, order_quantities, strict=True))
        period_rows = self.engine.step(self._t, overrides=overrides)
        reward = self._reward(period_rows)

        self._t += 1
        truncated = self._t >= self.n_periods
        terminated = False
        obs = self._get_obs()
        info = {"period_rows": period_rows}

        return obs, reward, terminated, truncated, info

    def render(self) -> str | None:
        if self.render_mode != "ansi" or self.engine is None:
            return None
        lines = [f"period {self._t}/{self.n_periods}"]
        for node_id in self.controlled_nodes:
            node = self.network.get_node(node_id)
            backlog = node.backlog.get(DEFAULT_SKU, 0.0)
            lines.append(f"  {node_id}: on_hand={node.on_hand_qty():.1f} backlog={backlog:.1f}")
        text = "\n".join(lines)
        if self.render_mode == "ansi":
            return text
        return None

    def close(self) -> None:
        self.engine = None

    # -- observation / action / reward helpers -----------------------------

    def _decode_action(self, action: np.ndarray) -> list[float]:
        action = np.asarray(action)
        if self.action_type == "discrete":
            bins = np.clip(action.astype(int), 0, self.n_discrete_bins - 1)
            return [float(self.bin_values[b]) for b in bins]
        clipped = np.clip(action, 0.0, self.max_order)
        return [float(v) for v in clipped]

    def _get_obs(self) -> np.ndarray:
        assert self.engine is not None
        parts: list[np.ndarray] = []
        for node_id in self.controlled_nodes:
            node = self.network.get_node(node_id)
            parts.append(
                np.array(
                    [
                        node.on_hand_qty(),
                        node.backlog.get(DEFAULT_SKU, 0.0),
                        node.pipeline.get(DEFAULT_SKU, 0.0),
                        node.inventory_position(),
                    ],
                    dtype=np.float32,
                )
            )
            history = self.engine.observed_demand(node_id)
            window = history[-self.demand_history_window :]
            padded = np.zeros(self.demand_history_window, dtype=np.float32)
            if window:
                padded[-len(window) :] = window
            parts.append(padded)
        parts.append(np.array([self._t / self.n_periods], dtype=np.float32))
        return np.concatenate(parts).astype(np.float32)

    def decode_observation(self, obs: np.ndarray) -> dict[str, Any]:
        """Split a flat observation vector back into named fields, so callers
        (e.g. :mod:`chainsim.ai.baselines`) don't need to hardcode its layout.

        Returns a dict with ``"on_hand"``, ``"backlog"``, ``"pipeline"``, and
        ``"inventory_position"`` (each a list, one entry per controlled node,
        in ``self.controlled_nodes`` order), ``"demand_history"`` (a list of
        per-node arrays), and ``"t_normalized"``.
        """
        obs = np.asarray(obs, dtype=np.float32)
        n = len(self.controlled_nodes)
        block = 4 + self.demand_history_window
        on_hand, backlog, pipeline, inv_pos, demand_history = [], [], [], [], []
        for i in range(n):
            chunk = obs[i * block : (i + 1) * block]
            on_hand.append(float(chunk[0]))
            backlog.append(float(chunk[1]))
            pipeline.append(float(chunk[2]))
            inv_pos.append(float(chunk[3]))
            demand_history.append(chunk[4:])
        return {
            "on_hand": on_hand,
            "backlog": backlog,
            "pipeline": pipeline,
            "inventory_position": inv_pos,
            "demand_history": demand_history,
            "t_normalized": float(obs[-1]),
        }

    def _reward(self, period_rows: list[dict]) -> float:
        w = self.cost_weights
        if self.reward_scope == "controlled":
            controlled = set(self.controlled_nodes)
            period_rows = [row for row in period_rows if row["node_id"] in controlled]
        total = 0.0
        for row in period_rows:
            total += w["holding"] * row["holding_cost"] + w["backlog"] * row["backlog_cost"]
            if w["transportation"]:
                total += w["transportation"] * self._transport_cost(row)
        return float(-total)

    def _transport_cost(self, row: dict) -> float:
        successors = self.network.successors(row["node_id"])
        if not successors:
            return 0.0
        avg_cost = sum(
            self.network.get_edge(row["node_id"], s.id).cost_per_unit for s in successors
        ) / len(successors)
        return row["fulfilled"] * avg_cost
