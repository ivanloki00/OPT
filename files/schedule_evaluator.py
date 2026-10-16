"""Validation and objective evaluation for nurse rostering schedules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

OFF = "OFF"


# ============================================================================
# Resultados tipados para separar factibilidad, objetivo y diagnóstico.
# ============================================================================
@dataclass(frozen=True)
class ValidationResult:
    """Hard-constraint validation result."""

    feasible: bool
    violations: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationResult:
    """Objective breakdown for one schedule."""

    feasible: bool
    total_penalty: float
    penalties: Mapping[str, int]
    violations: tuple[str, ...] = ()


def validate_schedule(
    schedule: Sequence[Sequence[str]],
    instance: Mapping[str, Any],
) -> ValidationResult:
    """Validate dimensions, skill coverage, and daily assignment uniqueness."""
    # --- Primero se comprueban las dos restricciones duras del proyecto. ---
    days = _number_of_days(instance)
    nurses = _nurses(instance)
    shifts = _shifts(instance)
    shift_by_id = _shift_by_id(shifts)

    if len(schedule) != len(nurses):
        raise ValueError(
            f"Expected {len(nurses)} nurse schedules, received {len(schedule)}"
        )

    violations: list[str] = []
    for nurse_index, nurse_schedule in enumerate(schedule):
        if len(nurse_schedule) != days:
            raise ValueError(
                f"Nurse {nurse_index} schedule must contain {days} days, "
                f"received {len(nurse_schedule)}"
            )
        nurse_skills = set(nurses[nurse_index].get("skills", []))
        assigned_by_day: list[list[str]] = [[] for _ in range(days)]
        for day, shift_id in enumerate(nurse_schedule):
            if shift_id == OFF:
                continue
            if shift_id not in shift_by_id:
                raise ValueError(f"Unknown shift {shift_id!r} at nurse {nurse_index}, day {day}")
            assigned_by_day[day].append(shift_id)
            required_skill = shift_by_id[shift_id].get("needed_skill")
            if required_skill not in nurse_skills:
                violations.append(
                    f"nurse {nurse_index} lacks {required_skill!r} for "
                    f"shift {shift_id!r} on day {day}"
                )
        for day, assignments in enumerate(assigned_by_day):
            if len(assignments) > 1:
                violations.append(
                    f"nurse {nurse_index} has multiple shifts on day {day}"
                )

    for day in range(days):
        for shift in shifts:
            shift_id = shift["shift_id"]
            required_skill = shift.get("needed_skill")
            covered = any(
                schedule[nurse_index][day] == shift_id
                and required_skill in set(nurses[nurse_index].get("skills", []))
                for nurse_index in range(len(nurses))
            )
            if not covered:
                violations.append(
                    f"shift {shift_id!r} has no qualified nurse on day {day}"
                )

    return ValidationResult(not violations, tuple(violations))


def evaluate_schedule(
    schedule: Sequence[Sequence[str]],
    instance: Mapping[str, Any],
) -> EvaluationResult:
    """Return feasibility and the nine components of the project objective."""
    # --- El objetivo solo es válido como calidad si el horario es factible. ---
    validation = validate_schedule(schedule, instance)
    nurses = _nurses(instance)
    shifts = _shifts(instance)
    shift_by_id = _shift_by_id(shifts)

    penalties = {
        "demand": _demand_penalty(schedule, instance),
        "assignments": 0,
        "working_streaks": 0,
        "free_streaks": 0,
        "complete_weekends": 0,
        "same_shift_weekends": 0,
        "unwanted_patterns": 0,
        "days_off": 0,
        "shift_off": 0,
    }

    for nurse_index, nurse in enumerate(nurses):
        nurse_schedule = schedule[nurse_index]
        working = [shift_id != OFF for shift_id in nurse_schedule]
        penalties["assignments"] += _range_deviation(
            sum(working),
            nurse.get("min_assignments"),
            nurse.get("max_assignments"),
        )
        penalties["working_streaks"] += _streak_deviation(
            working,
            nurse.get("min_consecutive_days"),
            nurse.get("max_consecutive_days"),
        )
        penalties["free_streaks"] += _streak_deviation(
            [not is_working for is_working in working],
            nurse.get("min_consecutive_free_days"),
            nurse.get("max_consecutive_free_days"),
        )
        penalties["complete_weekends"] += _complete_weekend_penalty(
            nurse_schedule,
            bool(nurse.get("complete_weekends")),
        )
        penalties["same_shift_weekends"] += _same_shift_weekend_penalty(
            nurse_schedule,
            bool(nurse.get("same_shift_weekend")),
        )
        penalties["unwanted_patterns"] += _pattern_penalty(
            nurse_schedule,
            nurse.get("unwanted_patterns", []),
        )
        penalties["days_off"] += sum(
            nurse_schedule[day] != OFF
            for day in nurse.get("days_off_requests", [])
        )
        penalties["shift_off"] += sum(
            0 <= request["day"] < len(nurse_schedule)
            and nurse_schedule[request["day"]] == request["shift_type"]
            for request in nurse.get("shift_off_requests", [])
        )

    total = sum(penalties.values())
    return EvaluationResult(
        feasible=validation.feasible,
        total_penalty=float(total) if validation.feasible else float("inf"),
        penalties=penalties,
        violations=validation.violations,
    )


def _number_of_days(instance: Mapping[str, Any]) -> int:
    days = instance.get("number_of_days")
    if not isinstance(days, int) or days < 1:
        raise ValueError("number_of_days must be a positive integer")
    return days


def _nurses(instance: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    nurses = instance.get("nurses")
    if not isinstance(nurses, list):
        raise ValueError("instance.nurses must be a list")
    return nurses


def _shifts(instance: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    shifts = instance.get("shifts")
    if not isinstance(shifts, list) or not shifts:
        raise ValueError("instance.shifts must be a non-empty list")
    return shifts


def _shift_by_id(shifts: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    shift_by_id: dict[str, Mapping[str, Any]] = {}
    for shift in shifts:
        shift_id = shift.get("shift_id")
        if not isinstance(shift_id, str) or not shift_id:
            raise ValueError("Every shift must have a non-empty string shift_id")
        if shift_id in shift_by_id:
            raise ValueError(f"Duplicate shift_id {shift_id!r}")
        shift_by_id[shift_id] = shift
    return shift_by_id


def _demand_penalty(
    schedule: Sequence[Sequence[str]],
    instance: Mapping[str, Any],
) -> int:
    # --- Penalización absoluta: tanto déficit como exceso cuentan. ---
    penalty = 0
    for shift in _shifts(instance):
        demand = shift.get("demand")
        if not isinstance(demand, list) or len(demand) != _number_of_days(instance):
            raise ValueError(
                f"Demand for shift {shift.get('shift_id')!r} must contain one value per day"
            )
        shift_id = shift["shift_id"]
        for day, preferred in enumerate(demand):
            if not isinstance(preferred, int) or preferred < 0:
                raise ValueError(f"Demand for shift {shift_id!r} must be non-negative integers")
            assigned = sum(nurse_schedule[day] == shift_id for nurse_schedule in schedule)
            penalty += abs(assigned - preferred)
    return penalty


def _range_deviation(value: int, minimum: int | None, maximum: int | None) -> int:
    if not isinstance(minimum, int) or not isinstance(maximum, int):
        raise ValueError("Contract ranges must contain integer minimum and maximum values")
    if minimum > maximum:
        raise ValueError("Contract minimum cannot exceed maximum")
    return max(0, minimum - value) + max(0, value - maximum)


def _streak_deviation(
    values: Sequence[bool],
    minimum: int | None,
    maximum: int | None,
) -> int:
    # --- Cada bloque de trabajo o descanso se evalúa de forma independiente. ---
    if not values:
        return 0
    if not isinstance(minimum, int) or not isinstance(maximum, int):
        raise ValueError("Streak ranges must contain integer minimum and maximum values")
    if minimum > maximum:
        raise ValueError("Streak minimum cannot exceed maximum")

    deviation = 0
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[end] == values[start]:
            end += 1
        run_length = end - start
        if values[start]:
            deviation += max(0, minimum - run_length)
            deviation += max(0, run_length - maximum)
        start = end
    return deviation


def _weekends(number_of_days: int) -> list[tuple[int, int]]:
    return [
        (day, day + 1)
        for day in range(5, number_of_days - 1, 7)
    ]


def _complete_weekend_penalty(
    nurse_schedule: Sequence[str],
    enabled: bool,
) -> int:
    # --- Solo se penalizan fines de semana con un único día trabajado. ---
    if not enabled:
        return 0
    return sum(
        (nurse_schedule[saturday] == OFF) != (nurse_schedule[sunday] == OFF)
        for saturday, sunday in _weekends(len(nurse_schedule))
    )


def _same_shift_weekend_penalty(
    nurse_schedule: Sequence[str],
    enabled: bool,
) -> int:
    # --- Si se trabajan ambos días, se compara el identificador de turno. ---
    if not enabled:
        return 0
    return sum(
        nurse_schedule[saturday] != OFF
        and nurse_schedule[sunday] != OFF
        and nurse_schedule[saturday] != nurse_schedule[sunday]
        for saturday, sunday in _weekends(len(nurse_schedule))
    )


def _pattern_penalty(
    nurse_schedule: Sequence[str],
    patterns: Sequence[str],
) -> int:
    # --- Se cuentan todas las apariciones, incluidas las solapadas. ---
    penalty = 0
    for pattern in patterns:
        if not isinstance(pattern, str) or not pattern:
            raise ValueError("Unwanted patterns must be non-empty strings")
        pattern_shifts = pattern.split("-")
        length = len(pattern_shifts)
        penalty += sum(
            list(nurse_schedule[start : start + length]) == pattern_shifts
            for start in range(len(nurse_schedule) - length + 1)
        )
    return penalty
