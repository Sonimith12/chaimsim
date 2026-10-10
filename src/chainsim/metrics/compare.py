"""Utilities to compare KPIs across two or more scenario runs.

Given two or more scenario runs — typically tidy Monte Carlo sweep
results from :class:`chainsim.metrics.sweep.ScenarioSweep`, or single-row
summaries from :func:`chainsim.metrics.kpis.summarize` — produces a
side-by-side comparison table.

:func:`summarize_sweep` aggregates *within* one sweep's tidy results
(mean/std per parameter combination, across replications) — the usual way
to turn a sweep into a printable table. :func:`compare` instead compares
*across* independently-labeled scenarios, one summary row each.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd


def _numeric_columns(df: pd.DataFrame, exclude: set[str]) -> list[str]:
    return [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]


def summarize_sweep(
    results: pd.DataFrame,
    group_cols: Sequence[str],
    metrics: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Aggregate a tidy sweep results DataFrame to mean/std per unique combination
    of ``group_cols``, across replications.

    Args:
        results: A tidy results table, e.g. from ``ScenarioSweep.run()``.
        group_cols: Columns identifying a parameter combination (e.g.
            ``["policy", "lead_time"]``); everything else is aggregated over.
        metrics: KPI columns to summarize. Defaults to every numeric column
            not in ``group_cols`` and not ``"replication"``.

    Returns:
        One row per unique ``group_cols`` combination, with ``{metric}_mean``
        and ``{metric}_std`` columns.
    """
    group_cols = list(group_cols)
    if metrics is None:
        metrics = _numeric_columns(results, exclude={*group_cols, "replication"})

    grouped = results.groupby(group_cols)[list(metrics)].agg(["mean", "std"])
    grouped.columns = [f"{metric}_{stat}" for metric, stat in grouped.columns]
    return grouped.reset_index()


def compare(
    results_by_scenario: Mapping[str, pd.DataFrame],
    metrics: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Compare two or more independently-produced scenario results side by side.

    Args:
        results_by_scenario: Maps a scenario label to its results — either a
            tidy sweep DataFrame (mean/std are taken across all its rows) or
            a single-row summary (e.g. ``pd.DataFrame([kpis.summarize(...)])``).
        metrics: KPI columns to compare. Defaults to every numeric column
            present.

    Returns:
        One row per scenario (indexed by scenario label), with ``{metric}_mean``
        and, when more than one row was available for a scenario, ``{metric}_std``.
    """
    rows = []
    for name, df in results_by_scenario.items():
        cols = metrics if metrics is not None else _numeric_columns(df, exclude=set())
        row: dict[str, float | str] = {"scenario": name}
        for col in cols:
            row[f"{col}_mean"] = float(df[col].mean())
            if len(df) > 1:
                row[f"{col}_std"] = float(df[col].std())
        rows.append(row)
    return pd.DataFrame(rows).set_index("scenario")
