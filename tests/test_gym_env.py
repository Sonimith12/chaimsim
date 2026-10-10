"""Tests for chainsim.ai.gym_env.SupplyChainEnv.

Includes `gymnasium.utils.env_checker.check_env()` compliance for both the
continuous and discrete action spaces.
"""

import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

from chainsim.ai.gym_env import SupplyChainEnv
from chainsim.core.demand import StationaryDemand
from chainsim.core.edges import TransportLink
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.nodes import DEFAULT_SKU, Retailer, Supplier
from chainsim.core.policies import OrderUpTo


def _network():
    net = SupplyChainNetwork()
    net.add_node(Supplier(id="S", holding_cost=0.1, initial_inventory={DEFAULT_SKU: 10_000}))
    net.add_node(
        Retailer(id="R", holding_cost=1.0, backlog_cost=5.0, initial_inventory={DEFAULT_SKU: 20})
    )
    net.add_edge(TransportLink(source="S", destination="R", lead_time=2))
    return net


def _env(**kwargs):
    defaults = dict(
        network=_network(),
        demand={"R": StationaryDemand(mean=10)},
        policies={},
        controlled_nodes="R",
        max_order=100,
        n_periods=20,
        seed=0,
    )
    defaults.update(kwargs)
    return SupplyChainEnv(**defaults)


# -- gymnasium compliance -----------------------------------------------


def test_check_env_continuous():
    check_env(_env().unwrapped)


def test_check_env_discrete():
    check_env(_env(action_type="discrete").unwrapped)


# -- basic mechanics ----------------------------------------------------


def test_reset_returns_obs_and_info():
    env = _env()
    obs, info = env.reset(seed=0)
    assert obs in env.observation_space
    assert isinstance(info, dict)


def test_step_returns_five_tuple_with_correct_types():
    env = _env()
    env.reset(seed=0)
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    assert obs in env.observation_space
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)


def test_episode_truncates_after_n_periods():
    env = _env(n_periods=5)
    env.reset(seed=0)
    for i in range(5):
        _, _, terminated, truncated, _ = env.step(env.action_space.sample())
        assert terminated is False
        if i < 4:
            assert truncated is False
    assert truncated is True


def test_reset_is_deterministic_given_seed():
    env = _env()
    obs1, _ = env.reset(seed=42)
    obs2, _ = env.reset(seed=42)
    assert np.allclose(obs1, obs2)


def test_step_sequence_deterministic_given_seed():
    env_a, env_b = _env(), _env()
    obs_a, _ = env_a.reset(seed=7)
    obs_b, _ = env_b.reset(seed=7)
    rng = np.random.default_rng(0)
    for _ in range(10):
        action = rng.uniform(0, 100, size=(1,)).astype(np.float32)
        obs_a, r_a, *_ = env_a.step(action)
        obs_b, r_b, *_ = env_b.step(action)
        assert np.allclose(obs_a, obs_b)
        assert r_a == pytest.approx(r_b)


def test_step_before_reset_raises():
    env = _env()
    with pytest.raises(RuntimeError):
        env.step(env.action_space.sample())


# -- action -> engine wiring ----------------------------------------------


def test_large_order_action_prevents_backlog_buildup():
    env = _env(n_periods=10)
    env.reset(seed=0)
    for _ in range(10):
        env.step(np.array([100.0], dtype=np.float32))  # always order the max
    node = env.network.get_node("R")
    assert node.backlog.get(DEFAULT_SKU, 0.0) == 0.0


def test_zero_order_action_accumulates_backlog():
    env = _env(n_periods=10)
    env.reset(seed=0)
    for _ in range(10):
        env.step(np.array([0.0], dtype=np.float32))  # never order
    node = env.network.get_node("R")
    assert node.backlog.get(DEFAULT_SKU, 0.0) > 0.0


def test_reward_is_negative_cost():
    env = _env()
    env.reset(seed=0)
    _, reward, *_ = env.step(np.array([20.0], dtype=np.float32))
    assert reward <= 0.0


def test_decode_observation_roundtrip():
    env = _env()
    obs, _ = env.reset(seed=0)
    decoded = env.decode_observation(obs)
    node = env.network.get_node("R")
    assert decoded["on_hand"][0] == pytest.approx(node.on_hand_qty())
    assert decoded["inventory_position"][0] == pytest.approx(node.inventory_position())
    assert len(decoded["demand_history"][0]) == env.demand_history_window


def test_uncontrolled_node_still_follows_its_own_policy():
    net = _network()
    env = SupplyChainEnv(
        network=net,
        demand={"R": StationaryDemand(mean=10, std=0, distribution="normal")},
        policies={},
        controlled_nodes="R",
        max_order=200,
        n_periods=10,
        seed=0,
    )
    env.reset(seed=0)
    for _ in range(5):
        env.step(np.array([15.0], dtype=np.float32))
    # Supplier isn't controlled and has no policy either -> it should never
    # place its own replenishment order, only ship from its initial stock.
    supplier = env.network.get_node("S")
    assert supplier.pipeline.get(DEFAULT_SKU, 0.0) == 0.0


def test_multi_controlled_nodes_action_shape():
    net = SupplyChainNetwork()
    net.add_node(Supplier(id="S", holding_cost=0.1, initial_inventory={DEFAULT_SKU: 10_000}))
    net.add_node(Retailer(id="R1", holding_cost=1.0, initial_inventory={DEFAULT_SKU: 20}))
    net.add_node(Retailer(id="R2", holding_cost=1.0, initial_inventory={DEFAULT_SKU: 20}))
    net.add_edge(TransportLink(source="S", destination="R1", lead_time=1))
    net.add_edge(TransportLink(source="S", destination="R2", lead_time=1))
    env = SupplyChainEnv(
        network=net,
        demand={
            "R1": StationaryDemand(mean=5),
            "R2": StationaryDemand(mean=5),
        },
        policies={"S": OrderUpTo(S=100_000)},
        controlled_nodes=["R1", "R2"],
        max_order=50,
        n_periods=10,
        seed=0,
    )
    assert env.action_space.shape == (2,)
    obs, _ = env.reset(seed=0)
    obs2, reward, *_ = env.step(np.array([10.0, 10.0], dtype=np.float32))
    assert obs2.shape == env.observation_space.shape
