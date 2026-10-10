"""Smoke tests for chainsim.scenarios: each scenario should build a valid network
and run without error, producing a well-formed history. Not testing the specific
narrative numbers printed by each scenario's CLI report — see the modules
themselves (run standalone) for those.
"""

import pytest

from chainsim.scenarios import (
    global_commodity_flow,
    manufacturing_jit,
    pharma_cold_chain,
    retail_replenishment,
)
from chainsim.scenarios._common import run_scenario

SCENARIOS = [retail_replenishment, manufacturing_jit, pharma_cold_chain, global_commodity_flow]


@pytest.mark.parametrize("module", SCENARIOS, ids=[m.__name__ for m in SCENARIOS])
def test_scenario_builds_a_valid_network(module):
    config = module.build_scenario()
    config.network.validate()  # should not raise


@pytest.mark.parametrize("module", SCENARIOS, ids=[m.__name__ for m in SCENARIOS])
def test_scenario_runs_and_produces_well_formed_history(module):
    config = module.build_scenario()
    engine, history = run_scenario(config)

    assert len(history) == config.n_periods * len(config.network.nodes)
    assert (history["on_hand"] >= 0).all()
    assert (history["backlog"] >= 0).all()
    for col in ("period", "node_id", "fulfilled", "order_placed", "holding_cost", "backlog_cost"):
        assert col in history.columns


def test_manufacturing_jit_supports_buffered_variant():
    config = manufacturing_jit.build_scenario(line_policy="buffered")
    _engine, history = run_scenario(config)
    assert len(history) == config.n_periods * len(config.network.nodes)


def test_manufacturing_jit_rejects_unknown_line_policy():
    with pytest.raises(ValueError):
        manufacturing_jit.build_scenario(line_policy="bogus")


@pytest.mark.parametrize("module", SCENARIOS, ids=[m.__name__ for m in SCENARIOS])
def test_scenario_main_runs_end_to_end(module, capsys):
    engine, history = module.main()
    assert len(history) > 0
    captured = capsys.readouterr()
    assert module.build_scenario().name in captured.out
