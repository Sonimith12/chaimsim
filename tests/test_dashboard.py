"""Tests for the dashboard/ Streamlit app, using streamlit.testing.v1.AppTest to run
each page through the real Streamlit script-execution engine (headless, no browser).

Each page is also expected to only call chainsim's public API — see the
module docstrings under dashboard/ — but that's enforced by review/reading,
not automatically checked here.
"""

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

from chainsim.core import SimulationEngine  # noqa: E402
from chainsim.scenarios.pharma_cold_chain import build_scenario as build_pharma  # noqa: E402
from chainsim.scenarios.retail_replenishment import build_scenario as build_retail  # noqa: E402
from state import CONFIG_KEY, RUNS_KEY, RunRecord, ScenarioBundle  # noqa: E402

DASHBOARD = Path(__file__).parent.parent / "dashboard"


def _bundle_from(config) -> ScenarioBundle:
    return ScenarioBundle(
        name=config.name,
        description=config.description,
        network=config.network,
        demand=config.demand,
        policies=config.policies,
        disruptions=config.disruptions,
        n_periods=config.n_periods,
        seed=config.seed,
    )


def _run_record(label: str, config) -> RunRecord:
    engine = SimulationEngine(
        network=config.network,
        demand=config.demand,
        policies=config.policies,
        disruptions=config.disruptions,
        n_periods=config.n_periods,
        seed=config.seed,
    )
    history = engine.run()
    return RunRecord(
        label=label,
        history=history,
        network=config.network,
        n_periods=config.n_periods,
        seed=config.seed,
        source=config.name,
    )


# -- app.py -----------------------------------------------------------------


def test_app_loads_with_no_state():
    at = AppTest.from_file(str(DASHBOARD / "app.py"))
    at.run(timeout=30)
    assert not at.exception


# -- page 1: Build Scenario --------------------------------------------------


def test_build_scenario_loads_a_prebuilt_scenario():
    at = AppTest.from_file(str(DASHBOARD / "pages" / "1_Build_Scenario.py"))
    at.run(timeout=30)
    at.selectbox[0].select("Retail Replenishment").run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    assert any("Loaded" in s.value for s in at.success)
    bundle = at.session_state[CONFIG_KEY]
    assert bundle.name == "Retail Replenishment"


def test_build_scenario_manufacturing_jit_exposes_line_policy_choice():
    at = AppTest.from_file(str(DASHBOARD / "pages" / "1_Build_Scenario.py"))
    at.run(timeout=30)
    at.selectbox[0].select("Manufacturing JIT").run(timeout=30)
    assert not at.exception
    at.radio[1].set_value("buffered").run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception
    bundle = at.session_state[CONFIG_KEY]
    assert "buffered" in bundle.name


def test_build_scenario_builds_a_custom_chain_with_defaults():
    at = AppTest.from_file(str(DASHBOARD / "pages" / "1_Build_Scenario.py"))
    at.run(timeout=30)
    at.radio[0].set_value("Custom serial chain").run(timeout=30)
    assert not at.exception
    buttons = {b.label: b for b in at.button}
    buttons["Build custom scenario"].click().run(timeout=30)
    assert not at.exception
    assert not at.error
    bundle = at.session_state[CONFIG_KEY]
    assert bundle.name == "Custom Serial Chain"
    bundle.network.validate()  # should not raise


def test_build_scenario_custom_chain_add_disruption():
    at = AppTest.from_file(str(DASHBOARD / "pages" / "1_Build_Scenario.py"))
    at.run(timeout=30)
    at.radio[0].set_value("Custom serial chain").run(timeout=30)
    buttons = {b.label: b for b in at.button}
    buttons["Add disruption"].click().run(timeout=30)
    assert not at.exception
    assert len(at.session_state["custom_disruptions"]) == 1
    buttons = {b.label: b for b in at.button}
    buttons["Build custom scenario"].click().run(timeout=30)
    assert not at.exception
    bundle = at.session_state[CONFIG_KEY]
    assert len(bundle.disruptions) == 1


# -- page 2: Run Simulation --------------------------------------------------


def test_run_simulation_warns_without_a_scenario():
    at = AppTest.from_file(str(DASHBOARD / "pages" / "2_Run_Simulation.py"))
    at.run(timeout=30)
    assert not at.exception
    assert any("Build Scenario" in w.value for w in at.warning)


def test_run_simulation_executes_and_records_a_run():
    at = AppTest.from_file(str(DASHBOARD / "pages" / "2_Run_Simulation.py"))
    at.session_state[CONFIG_KEY] = _bundle_from(build_retail())
    at.run(timeout=30)
    at.button[0].click().run(timeout=60)
    assert not at.exception
    runs = at.session_state[RUNS_KEY]
    assert len(runs) == 1
    assert len(runs[0].history) == runs[0].n_periods * len(runs[0].network.nodes)


# -- page 3: Results Dashboard -----------------------------------------------


def test_results_dashboard_warns_without_a_run():
    at = AppTest.from_file(str(DASHBOARD / "pages" / "3_Results_Dashboard.py"))
    at.run(timeout=30)
    assert not at.exception
    assert any("Run Simulation" in w.value for w in at.warning)


def test_results_dashboard_renders_kpis_and_charts_for_a_run():
    at = AppTest.from_file(str(DASHBOARD / "pages" / "3_Results_Dashboard.py"))
    at.session_state[RUNS_KEY] = [_run_record("Retail", build_retail())]
    at.run(timeout=30)
    assert not at.exception
    assert len(at.metric) == 8  # the two KPI-card rows
    assert len(at.dataframe) == 1  # per-node KPI table


def test_results_dashboard_period_snapshot_slider():
    at = AppTest.from_file(str(DASHBOARD / "pages" / "3_Results_Dashboard.py"))
    at.session_state[RUNS_KEY] = [_run_record("Retail", build_retail())]
    at.run(timeout=30)
    at.checkbox[0].set_value(True).run(timeout=30)
    assert not at.exception
    at.slider[0].set_value(10).run(timeout=30)
    assert not at.exception


# -- page 4: Compare Scenarios -----------------------------------------------


def test_compare_scenarios_warns_without_runs():
    at = AppTest.from_file(str(DASHBOARD / "pages" / "4_Compare_Scenarios.py"))
    at.run(timeout=30)
    assert not at.exception
    assert any("Run Simulation" in w.value for w in at.warning)


def test_compare_scenarios_prompts_for_a_second_run_when_only_one_exists():
    at = AppTest.from_file(str(DASHBOARD / "pages" / "4_Compare_Scenarios.py"))
    at.session_state[RUNS_KEY] = [_run_record("Retail", build_retail())]
    at.run(timeout=30)
    assert not at.exception
    assert any("one more" in i.value for i in at.info)


def test_compare_scenarios_compares_two_runs():
    at = AppTest.from_file(str(DASHBOARD / "pages" / "4_Compare_Scenarios.py"))
    at.session_state[RUNS_KEY] = [
        _run_record("Retail", build_retail()),
        _run_record("Pharma", build_pharma()),
    ]
    at.run(timeout=30)
    assert not at.exception
    assert len(at.dataframe) == 2  # overall comparison + per-node side-by-side


@pytest.mark.parametrize(
    "page",
    [
        "app.py",
        "pages/1_Build_Scenario.py",
        "pages/2_Run_Simulation.py",
        "pages/3_Results_Dashboard.py",
        "pages/4_Compare_Scenarios.py",
    ],
)
def test_every_page_sets_page_config(page):
    source = (DASHBOARD / page).read_text()
    assert "st.set_page_config(" in source
