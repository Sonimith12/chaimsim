"""Heuristic and RL-ready baseline agents for benchmarking against the Gym interface.

Provides simple heuristic agents that act purely from a
:class:`~chainsim.ai.gym_env.SupplyChainEnv` observation (no access to the
underlying :class:`~chainsim.core.engine.SimulationEngine`), so RL results
have a classical baseline to beat on the exact same interface:
:class:`OrderUpToAgent` (a fixed order-up-to-``S`` policy) and
:class:`RandomAgent`. :func:`evaluate_agent` runs any agent — one of these,
or a trained Stable-Baselines3 model — for a number of episodes and reports
mean/std episode reward.
"""

from __future__ import annotations

from typing import Any, Protocol

import numpy as np

from chainsim.ai.gym_env import SupplyChainEnv


class Agent(Protocol):
    """Minimal interface `evaluate_agent` needs: map an observation to an action."""

    def act(self, observation: np.ndarray) -> np.ndarray: ...


class OrderUpToAgent:
    """Heuristic baseline: applies a fixed order-up-to-``S`` policy against a
    :class:`~chainsim.ai.gym_env.SupplyChainEnv`, reading only its observation
    (via :meth:`~chainsim.ai.gym_env.SupplyChainEnv.decode_observation`) —
    exactly the information an RL agent has, so it's a fair baseline.

    Args:
        env: The environment this agent will act in (used to decode
            observations and know the action space's shape/bounds).
        S: Order-up-to level(s). A single number applies to every controlled
            node; a list applies one per node (in ``env.controlled_nodes`` order).
    """

    def __init__(self, env: SupplyChainEnv, S: float | list[float]) -> None:
        self.env = env
        n = len(env.controlled_nodes)
        self.S = [float(S)] * n if isinstance(S, (int, float)) else [float(s) for s in S]
        if len(self.S) != n:
            raise ValueError(f"expected {n} S value(s), got {len(self.S)}")

    def act(self, observation: np.ndarray) -> np.ndarray:
        decoded = self.env.decode_observation(observation)
        pairs = zip(self.S, decoded["inventory_position"], strict=True)
        orders = [max(0.0, s - inv_pos) for s, inv_pos in pairs]
        orders = [min(o, self.env.max_order) for o in orders]

        if self.env.action_type == "discrete":
            bins = self.env.bin_values
            return np.array([int(np.argmin(np.abs(bins - o))) for o in orders], dtype=np.int64)
        return np.array(orders, dtype=np.float32)


class RandomAgent:
    """Samples a uniformly random action each step — a lower-bound baseline."""

    def __init__(self, env: SupplyChainEnv) -> None:
        self.env = env

    def act(self, observation: np.ndarray) -> np.ndarray:
        return self.env.action_space.sample()


def _get_action(agent: Any, observation: np.ndarray) -> np.ndarray:
    """Dispatch to whichever calling convention `agent` supports: this module's
    `.act(obs)`, or a Stable-Baselines3-style `.predict(obs, deterministic=True)`.
    """
    if hasattr(agent, "predict"):
        action, _state = agent.predict(observation, deterministic=True)
        return action
    return agent.act(observation)


def evaluate_agent(
    env: SupplyChainEnv, agent: Any, n_episodes: int = 20, seed: int = 0
) -> dict[str, Any]:
    """Run `agent` in `env` for `n_episodes` full episodes and summarize episode reward.

    Args:
        env: Environment to evaluate in.
        agent: Anything exposing `.act(obs) -> action` (e.g. `OrderUpToAgent`,
            `RandomAgent`) or `.predict(obs, deterministic=True) -> (action, state)`
            (a Stable-Baselines3 model).
        n_episodes: Number of episodes to run.
        seed: Episode ``e`` is reset with seed ``seed + e``.

    Returns:
        ``{"mean_reward", "std_reward", "episode_rewards", "n_episodes"}``.
    """
    episode_rewards: list[float] = []
    for episode in range(n_episodes):
        obs, _info = env.reset(seed=seed + episode)
        total_reward = 0.0
        terminated = truncated = False
        while not (terminated or truncated):
            action = _get_action(agent, obs)
            obs, reward, terminated, truncated, _info = env.step(action)
            total_reward += reward
        episode_rewards.append(total_reward)

    return {
        "mean_reward": float(np.mean(episode_rewards)),
        "std_reward": float(np.std(episode_rewards)),
        "episode_rewards": episode_rewards,
        "n_episodes": n_episodes,
    }
