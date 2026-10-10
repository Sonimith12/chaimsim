"""Scoring, objectives and grading for a game run.

Kept in the backend with the rest of the game logic: the frontend only renders
the numbers produced here. :class:`ScoreKeeper` is fed each period's engine
history rows and turns them into a running score, objective statuses and
one-off events (stockouts, milestones, policy-change bonuses).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# --- scoring weights ---------------------------------------------------------
BASE_POINTS_PER_PERIOD = 1000
SERVICE_BONUS_PER_PERIOD = 50  # period with >= SERVICE_PERIOD_THRESHOLD of customer nodes in stock
FILL_BONUS_PER_PERIOD = 25  # period with >= FILL_PERIOD_THRESHOLD of demand fulfilled
COST_PENALTY_WEIGHT = 0.05  # points lost per unit of total cost
WASTE_PENALTY_PER_UNIT = 5
STOCKOUT_PENALTY = 200
POLICY_BONUS = 50
POLICY_EVAL_WINDOW = 3  # periods compared before/after a policy change

SERVICE_PERIOD_THRESHOLD = 0.95
FILL_PERIOD_THRESHOLD = 0.90

# --- objective targets ---------------------------------------------------------
TARGET_SERVICE_LEVEL = 0.95
TARGET_FILL_RATE = 0.90
TARGET_PROFIT_MARGIN = 0.15
COST_TARGET_FACTOR = 1.2  # of the scenario's baseline cost
BORDERLINE_MARGIN = 0.05
COST_BORDERLINE_FACTOR = 1.15

# Grade thresholds on score / maximum possible score, best first.
GRADES = [("S", 0.97), ("A", 0.93), ("B", 0.88), ("C", 0.78), ("D", 0.65)]

_EPS = 1e-6


@dataclass
class Targets:
    """Per-scenario objective targets, derived once at load time."""

    total_cost: float
    bonus: str  # "stockouts" | "waste"
    max_waste: float = 0.0


@dataclass
class ScoreKeeper:
    n_periods: int
    sink_ids: set[str]
    targets: Targets

    completed: int = 0
    service_periods: int = 0
    fill_periods: int = 0
    # Gains accumulate as earned (a cash crisis halves them); penalties are never scaled.
    base_points: float = 0.0
    service_points: float = 0.0
    fill_points: float = 0.0
    stockouts: int = 0
    policy_changes: int = 0
    policy_bonuses: int = 0
    stockout_log: list[int] = field(default_factory=list)  # period index of each stockout
    _in_stockout: dict[str, bool] = field(default_factory=dict)
    _period_points: list[float] = field(default_factory=list)
    _pending: list[tuple[int, str]] = field(default_factory=list)  # (completed at change, node)

    # -- per-period update -------------------------------------------------------

    def update(self, rows: list[dict], multiplier: float = 1.0) -> list[dict[str, Any]]:
        """Fold one processed period's rows in; return the events it produced.

        ``multiplier`` scales the period's point gains (0.5 during a cash crisis).
        """
        events: list[dict[str, Any]] = []
        sinks = [r for r in rows if r["node_id"] in self.sink_ids] or rows

        in_stock = sum(1 for r in sinks if r["backlog"] <= _EPS) / len(sinks)
        service_ok = in_stock >= SERVICE_PERIOD_THRESHOLD
        demand = sum(r["period_demand"] for r in sinks)
        fulfilled = sum(r["fulfilled"] for r in sinks)
        fill_ok = demand <= 0 or fulfilled / demand >= FILL_PERIOD_THRESHOLD
        self.service_periods += service_ok
        self.fill_periods += fill_ok
        gain_base = BASE_POINTS_PER_PERIOD * multiplier
        gain_service = SERVICE_BONUS_PER_PERIOD * service_ok * multiplier
        gain_fill = FILL_BONUS_PER_PERIOD * fill_ok * multiplier
        self.base_points += gain_base
        self.service_points += gain_service
        self.fill_points += gain_fill

        new_stockouts = 0
        for r in rows:
            short = r["backlog"] > _EPS
            if short and not self._in_stockout.get(r["node_id"], False):
                new_stockouts += 1
                self.stockout_log.append(self.completed)
                events.append(
                    {"type": "stockout", "node_id": r["node_id"], "points": -STOCKOUT_PENALTY}
                )
            self._in_stockout[r["node_id"]] = short
        self.stockouts += new_stockouts

        period_cost = sum(r["holding_cost"] + r["backlog_cost"] for r in rows)
        waste = sum(r["waste"] for r in rows)
        self._period_points.append(
            gain_base
            + gain_service
            + gain_fill
            - STOCKOUT_PENALTY * new_stockouts
            - COST_PENALTY_WEIGHT * period_cost
            - WASTE_PENALTY_PER_UNIT * waste
        )
        self.completed += 1

        # Judge pending policy changes once enough periods have passed since the change.
        still_pending = []
        for changed_at, node_id in self._pending:
            if self.completed - changed_at < POLICY_EVAL_WINDOW:
                still_pending.append((changed_at, node_id))
                continue
            before = self._period_points[max(0, changed_at - POLICY_EVAL_WINDOW) : changed_at]
            after = self._period_points[changed_at : changed_at + POLICY_EVAL_WINDOW]
            if before and sum(after) / len(after) > sum(before) / len(before) + _EPS:
                self.policy_bonuses += 1
                events.append({"type": "policy_bonus", "node_id": node_id, "points": POLICY_BONUS})
        self._pending = still_pending

        for quarter in (1, 2, 3):
            if self.completed == round(self.n_periods * quarter / 4):
                events.append({"type": "milestone", "quarter": quarter})
        return events

    def note_policy_change(self, node_id: str) -> None:
        self.policy_changes += 1
        self._pending.append((self.completed, node_id))

    # -- reporting -----------------------------------------------------------------

    def score(self, total_cost: float, waste: float) -> dict[str, float]:
        parts = {
            "base": self.base_points,
            "service_bonus": self.service_points,
            "fill_bonus": self.fill_points,
            "policy_bonus": POLICY_BONUS * self.policy_bonuses,
            "cost_penalty": -COST_PENALTY_WEIGHT * total_cost,
            "waste_penalty": -WASTE_PENALTY_PER_UNIT * waste,
            "stockout_penalty": -STOCKOUT_PENALTY * self.stockouts,
        }
        parts["total"] = sum(parts.values())
        return parts

    def max_score(self) -> float:
        per_period = BASE_POINTS_PER_PERIOD + SERVICE_BONUS_PER_PERIOD + FILL_BONUS_PER_PERIOD
        return per_period * self.n_periods

    def objectives(
        self,
        total_cost: float,
        service_level: float,
        fill_rate: float,
        waste: float,
        profit_margin: float = 0.0,
        revenue: float = 0.0,
    ) -> list[dict[str, Any]]:
        progress = self.completed / self.n_periods if self.n_periods else 1.0
        t = self.targets

        if progress > 0:
            ratio = total_cost / (t.total_cost * progress)
            cost_status = (
                "ok" if ratio <= 1.0 else "borderline" if ratio <= COST_BORDERLINE_FACTOR else "failing"
            )
        else:
            cost_status = "ok"

        def rate_status(value: float, target: float) -> str:
            if value >= target:
                return "ok"
            return "borderline" if value >= target - BORDERLINE_MARGIN else "failing"

        out = [
            {
                "id": "cost",
                "label": "Keep total cost under",
                "unit": "currency",
                "comparison": "at_most",
                "target": round(t.total_cost),
                "actual": total_cost,
                "met": total_cost <= t.total_cost,
                "status": cost_status,
                "bonus": False,
            },
            {
                "id": "service",
                "label": "Maintain service level of",
                "unit": "percent",
                "comparison": "at_least",
                "target": TARGET_SERVICE_LEVEL,
                "actual": service_level,
                "met": service_level >= TARGET_SERVICE_LEVEL,
                "status": rate_status(service_level, TARGET_SERVICE_LEVEL),
                "bonus": False,
            },
            {
                "id": "fill",
                "label": "Achieve fill rate of",
                "unit": "percent",
                "comparison": "at_least",
                "target": TARGET_FILL_RATE,
                "actual": fill_rate,
                "met": fill_rate >= TARGET_FILL_RATE,
                "status": rate_status(fill_rate, TARGET_FILL_RATE),
                "bonus": False,
            },
        ]
        # Early on there's no revenue to take a margin of; don't flag that as failing.
        if self.completed == 0 or revenue <= 0:
            margin_status = "ok"
        else:
            margin_status = rate_status(profit_margin, TARGET_PROFIT_MARGIN)
        out.insert(
            3,
            {
                "id": "profit",
                "label": "Achieve profit margin of",
                "unit": "percent",
                "comparison": "at_least",
                "target": TARGET_PROFIT_MARGIN,
                "actual": profit_margin,
                "met": profit_margin >= TARGET_PROFIT_MARGIN,
                "status": margin_status,
                "bonus": False,
            },
        )
        if t.bonus == "waste":
            met = waste <= t.max_waste
            out.append(
                {
                    "id": "bonus",
                    "label": "Bonus: keep waste under",
                    "unit": "units",
                    "comparison": "at_most",
                    "target": round(t.max_waste),
                    "actual": waste,
                    "met": met,
                    "status": "ok" if met else "failing",
                    "bonus": True,
                }
            )
        else:
            out.append(
                {
                    "id": "bonus",
                    "label": "Bonus: zero stockouts",
                    "unit": "count",
                    "comparison": "at_most",
                    "target": 0,
                    "actual": self.stockouts,
                    "met": self.stockouts == 0,
                    "status": "ok" if self.stockouts == 0 else "failing",
                    "bonus": True,
                }
            )
        return out

    @staticmethod
    def overall_status(objectives: list[dict[str, Any]]) -> str:
        """green / yellow / red from the three core objectives."""
        core = [o["status"] for o in objectives if not o["bonus"]]
        if "failing" in core:
            return "red"
        if "borderline" in core:
            return "yellow"
        return "green"

    def grade(self, total_score: float) -> str:
        ratio = total_score / self.max_score() if self.max_score() else 0.0
        for letter, threshold in GRADES:
            if ratio >= threshold:
                return letter
        return "F"
