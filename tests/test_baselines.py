"""Tests for chainsim.ai.baselines."""

import numpy as np
import pytest

from chainsim.ai.baselines import OrderUpToAgent, RandomAgent, evaluate_agent
from chainsim.ai.gym_env import SupplyChainEnv
from chainsim.core.demand import StationaryDemand
from chainsim.core.edges import TransportLink
from chainsim.core.network import SupplyChainNetwork
from chainsim.core.nodes import DEFAULT_SKU, Retailer, Supplier


def _env(**kwargs):
    net = SupplyChainNetwork()
    net.add_node(Supplier(id="S", holding_cost=0.1, initial_inventory={DEFAULT_SKU: 10_000}))
    net.add_node(
        Retailer(id="R", holding_cost=1.0, backlog_cost=5.0, initial_inventory={DEFAULT_SKU: 20})
    )
    net.add_edge(TransportLink(source="S", destination="R", lead_time=2))
    defaults = dict(
        network=net,
        demand={"R": StationaryDemand(mean=10)},
        policies={},
        controlled_nodes="R",
        max_order=100,
        n_periods=20,
        seed=0,
    )
    defaults.update(kwargs)
    return SupplyChainEnv(**defaults)


def test_order_up_to_agent_orders_the_shortfall():
    env = _env()
    obs, _ = env.reset(seed=0)
    agent = OrderUpToAgent(env, S=60)
    action = agent.act(obs)
    decoded = env.decode_observation(obs)
    expected = max(0.0, 60 - decoded["inventory_position"][0])
    assert action[0] == pytest.approx(expected)


def test_order_up_to_agent_clips_to_max_order():
    env = _env(max_order=5)
    obs, _ = env.reset(seed=0)
    agent = OrderUpToAgent(env, S=10_000)
    action = agent.act(obs)
    assert action[0] <= 5.0


def test_order_up_to_agent_rejects_wrong_length_S_list():
    env = _env()
    with pytest.raises(ValueError):
        OrderUpToAgent(env, S=[10, 20])  # only one controlled node


def test_order_up_to_agent_discrete_action_type():
    env = _env(action_type="discrete")
    obs, _ = env.reset(seed=0)
    agent = OrderUpToAgent(env, S=60)
    action = agent.act(obs)
    assert action in env.action_space


def test_random_agent_produces_valid_actions():
    env = _env()
    agent = RandomAgent(env)
    obs, _ = env.reset(seed=0)
    action = agent.act(obs)
    assert action in env.action_space


def test_evaluate_agent_runs_n_episodes_and_summarizes():
    env = _env(n_periods=10)
    agent = OrderUpToAgent(env, S=60)
    result = evaluate_agent(env, agent, n_episodes=5, seed=0)
    assert result["n_episodes"] == 5
    assert len(result["episode_rewards"]) == 5
    assert isinstance(result["mean_reward"], float)
    assert isinstance(result["std_reward"], float)


def test_order_up_to_agent_beats_random_agent_on_average():
    env = _env(n_periods=30)
    good_agent = OrderUpToAgent(env, S=60)
    random_agent = RandomAgent(env)
    good = evaluate_agent(env, good_agent, n_episodes=15, seed=0)
    random = evaluate_agent(env, random_agent, n_episodes=15, seed=0)
    assert good["mean_reward"] > random["mean_reward"]


def test_evaluate_agent_supports_sb3_style_predict_interface():
    class FakeSB3Model:
        def predict(self, observation, deterministic=True):
            return np.array([20.0], dtype=np.float32), None

    env = _env(n_periods=10)
    result = evaluate_agent(env, FakeSB3Model(), n_episodes=3, seed=0)
    assert result["n_episodes"] == 3
