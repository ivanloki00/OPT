"""Validación y evaluación común de horarios de enfermería.

Este módulo concentra la interpretación de las restricciones y penalizaciones
para que MILP, metaheurística, pruebas y experimentos utilicen exactamente las
mismas reglas al comparar soluciones.
"""

# Permite utilizar anotaciones de tipos modernas sin evaluarlas durante la carga.
from __future__ import annotations

# Proporciona el decorador para resultados inmutables y autogenerados.
from dataclasses import dataclass, field
# Define tipos flexibles para aceptar las estructuras que llegan desde JSON.
from typing import Any, Mapping, Sequence

# Valor externo que representa un día sin turno asignado.
OFF = "OFF"


# ============================================================================
# Resultados tipados para separar factibilidad, objetivo y diagnóstico.
# ============================================================================
@dataclass(frozen=True)
class ValidationResult:
    """Resultado de comprobar únicamente las restricciones duras.

    ``feasible`` indica si el horario puede participar en la comparación de
    calidad y ``violations`` conserva cada explicación para facilitar el
    diagnóstico de soluciones incorrectas.
    """

    # Indica si no se ha encontrado ninguna violación dura.
    feasible: bool
    # Lista inmutable de mensajes que identifica las violaciones encontradas.
    violations: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationResult:
    """Desglose completo de la evaluación de un horario.

    ``penalties`` mantiene una entrada por cada componente de la función
    objetivo definida en la especificación del proyecto.
    """

    # Reutiliza el resultado de factibilidad obtenido antes de puntuar.
    feasible: bool
    # Es infinito para soluciones infactibles y la suma de penalizaciones si no.
    total_penalty: float
    # Desglose auditable de demanda, asignaciones, rachas, fines de semana,
    # patrones y peticiones.
    penalties: Mapping[str, int]
    # Conserva las explicaciones de las restricciones duras incumplidas.
    violations: tuple[str, ...] = ()


def validate_schedule(
    schedule: Sequence[Sequence[str]],
    instance: Mapping[str, Any],
) -> ValidationResult:
    """Comprueba dimensiones, habilidades, cobertura y unicidad diaria.

    Las dimensiones inválidas son errores de entrada y generan ``ValueError``;
    las restricciones duras incumplidas se devuelven como diagnósticos.
    """
    # Obtiene y valida el horizonte temporal declarado por la instancia.
    days = _number_of_days(instance)
    # Obtiene la lista de enfermeros que debe tener una fila por solución.
    nurses = _nurses(instance)
    # Obtiene los turnos que deben cubrirse cada día.
    shifts = _shifts(instance)
    # Indexa los turnos para validar rápidamente cada identificador externo.
    shift_by_id = _shift_by_id(shifts)

    # Comprueba que el número de filas coincide con el número de enfermeros.
    if len(schedule) != len(nurses):
        raise ValueError(
            f"Expected {len(nurses)} nurse schedules, received {len(schedule)}"
        )

    # Acumula mensajes legibles sin detener la validación en la primera violación.
    violations: list[str] = []
    for nurse_index, nurse_schedule in enumerate(schedule):
        # Cada fila debe contener exactamente una decisión por día.
        if len(nurse_schedule) != days:
            raise ValueError(
                f"Nurse {nurse_index} schedule must contain {days} days, "
                f"received {len(nurse_schedule)}"
            )
        # Convierte las habilidades del enfermero en conjunto para filtrar turnos.
        nurse_skills = set(nurses[nurse_index].get("skills", []))
        # Registra los turnos asignados en cada día para detectar duplicidades.
        assigned_by_day: list[list[str]] = [[] for _ in range(days)]
        for day, shift_id in enumerate(nurse_schedule):
            # ``OFF`` es una decisión válida y no requiere más comprobaciones.
            if shift_id == OFF:
                continue
            # Un identificador desconocido indica una solución mal formada.
            if shift_id not in shift_by_id:
                raise ValueError(f"Unknown shift {shift_id!r} at nurse {nurse_index}, day {day}")
            # Registra la asignación para la comprobación de unicidad diaria.
            assigned_by_day[day].append(shift_id)
            # Recupera la habilidad necesaria para el turno elegido.
            required_skill = shift_by_id[shift_id].get("needed_skill")
            # Una persona sin la habilidad requerida provoca una violación dura.
            if required_skill not in nurse_skills:
                violations.append(
                    f"nurse {nurse_index} lacks {required_skill!r} for "
                    f"shift {shift_id!r} on day {day}"
                )
        for day, assignments in enumerate(assigned_by_day):
            # Una fila externa normalmente codifica un turno por día; esta
            # comprobación también protege la lógica frente a representaciones
            # internas que pudieran contener más de una asignación.
            if len(assignments) > 1:
                violations.append(
                    f"nurse {nurse_index} has multiple shifts on day {day}"
                )

    # Recorre cada requisito de cobertura de la instancia.
    for day in range(days):
        for shift in shifts:
            # Identifica el turno y la habilidad que debe cubrirse.
            shift_id = shift["shift_id"]
            required_skill = shift.get("needed_skill")
            # Busca al menos un enfermero que trabaje ese turno y esté cualificado.
            covered = any(
                schedule[nurse_index][day] == shift_id
                and required_skill in set(nurses[nurse_index].get("skills", []))
                for nurse_index in range(len(nurses))
            )
            # La ausencia de cobertura es una violación dura independiente.
            if not covered:
                violations.append(
                    f"shift {shift_id!r} has no qualified nurse on day {day}"
                )

    # Un horario es factible exactamente cuando no contiene violaciones duras.
    return ValidationResult(not violations, tuple(violations))


def evaluate_schedule(
    schedule: Sequence[Sequence[str]],
    instance: Mapping[str, Any],
) -> EvaluationResult:
    """Devuelve factibilidad y las nueve componentes del objetivo.

    Primero valida las restricciones duras y después calcula todas las
    penalizaciones blandas, incluso cuando el horario resulta infactible, para
    facilitar el diagnóstico durante las pruebas y los experimentos.
    """
    # Ejecuta la única validación común de las restricciones duras.
    validation = validate_schedule(schedule, instance)
    # Recupera las entidades necesarias para recorrer la solución.
    nurses = _nurses(instance)
    shifts = _shifts(instance)
    shift_by_id = _shift_by_id(shifts)

    # Inicializa explícitamente todas las componentes exigidas por el proyecto.
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
        # Selecciona la fila perteneciente al enfermero actual.
        nurse_schedule = schedule[nurse_index]
        # Convierte cada decisión en trabajado/reposo para evaluar rachas.
        working = [shift_id != OFF for shift_id in nurse_schedule]
        # Penaliza la distancia al intervalo contractual de asignaciones.
        penalties["assignments"] += _range_deviation(
            sum(working),
            nurse.get("min_assignments"),
            nurse.get("max_assignments"),
        )
        # Penaliza rachas de trabajo fuera de sus límites.
        penalties["working_streaks"] += _streak_deviation(
            working,
            nurse.get("min_consecutive_days"),
            nurse.get("max_consecutive_days"),
        )
        # Invierte el indicador para evaluar rachas consecutivas de descanso.
        penalties["free_streaks"] += _streak_deviation(
            [not is_working for is_working in working],
            nurse.get("min_consecutive_free_days"),
            nurse.get("max_consecutive_free_days"),
        )
        # Evalúa si cada fin de semana debe trabajarse completo.
        penalties["complete_weekends"] += _complete_weekend_penalty(
            nurse_schedule,
            bool(nurse.get("complete_weekends")),
        )
        # Evalúa si los dos días trabajados del fin de semana usan el mismo turno.
        penalties["same_shift_weekends"] += _same_shift_weekend_penalty(
            nurse_schedule,
            bool(nurse.get("same_shift_weekend")),
        )
        # Cuenta apariciones de secuencias de turnos no deseadas.
        penalties["unwanted_patterns"] += _pattern_penalty(
            nurse_schedule,
            nurse.get("unwanted_patterns", []),
        )
        # Cada día solicitado como libre que aparece trabajado suma una unidad.
        penalties["days_off"] += sum(
            nurse_schedule[day] != OFF
            for day in nurse.get("days_off_requests", [])
        )
        # Cada petición de turno libre que coincide con la planificación suma una unidad.
        penalties["shift_off"] += sum(
            0 <= request["day"] < len(nurse_schedule)
            and nurse_schedule[request["day"]] == request["shift_type"]
            for request in nurse.get("shift_off_requests", [])
        )

    # Suma todas las componentes para obtener el objetivo informativo completo.
    total = sum(penalties.values())
    # La calidad numérica solo es válida si las restricciones duras se cumplen.
    return EvaluationResult(
        feasible=validation.feasible,
        total_penalty=float(total) if validation.feasible else float("inf"),
        penalties=penalties,
        violations=validation.violations,
    )


def _number_of_days(instance: Mapping[str, Any]) -> int:
    # Lee el horizonte y verifica que sea un entero positivo.
    days = instance.get("number_of_days")
    if not isinstance(days, int) or days < 1:
        raise ValueError("number_of_days must be a positive integer")
    return days


def _nurses(instance: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    # Recupera la colección de enfermeros exigida por el formato JSON.
    nurses = instance.get("nurses")
    if not isinstance(nurses, list):
        raise ValueError("instance.nurses must be a list")
    return nurses


def _shifts(instance: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    # Recupera los turnos y evita modelos sin requisitos de cobertura.
    shifts = instance.get("shifts")
    if not isinstance(shifts, list) or not shifts:
        raise ValueError("instance.shifts must be a non-empty list")
    return shifts


def _shift_by_id(shifts: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    # Construye un índice para validar identificadores y consultar requisitos.
    shift_by_id: dict[str, Mapping[str, Any]] = {}
    for shift in shifts:
        # Cada turno necesita un identificador textual no vacío.
        shift_id = shift.get("shift_id")
        if not isinstance(shift_id, str) or not shift_id:
            raise ValueError("Every shift must have a non-empty string shift_id")
        # Los identificadores duplicados harían ambigua la solución externa.
        if shift_id in shift_by_id:
            raise ValueError(f"Duplicate shift_id {shift_id!r}")
        # Guarda la definición completa asociada al identificador.
        shift_by_id[shift_id] = shift
    return shift_by_id


def _demand_penalty(
    schedule: Sequence[Sequence[str]],
    instance: Mapping[str, Any],
) -> int:
    # Inicializa la suma de diferencias absolutas de cobertura.
    penalty = 0
    for shift in _shifts(instance):
        # Lee la demanda preferida del turno.
        demand = shift.get("demand")
        if not isinstance(demand, list) or len(demand) != _number_of_days(instance):
            raise ValueError(
                f"Demand for shift {shift.get('shift_id')!r} must contain one value per day"
            )
        # Obtiene el identificador usado en cada horario.
        shift_id = shift["shift_id"]
        for day, preferred in enumerate(demand):
            # La demanda debe ser un número entero no negativo por día.
            if not isinstance(preferred, int) or preferred < 0:
                raise ValueError(f"Demand for shift {shift_id!r} must be non-negative integers")
            # Cuenta cuántos enfermeros tienen asignado este turno ese día.
            assigned = sum(nurse_schedule[day] == shift_id for nurse_schedule in schedule)
            # Penaliza por igual tanto quedarse corto como cubrir de más.
            penalty += abs(assigned - preferred)
    return penalty


def _range_deviation(value: int, minimum: int | None, maximum: int | None) -> int:
    # Los límites contractuales deben ser enteros para producir una penalización
    # discreta y coherente con las variables enteras del MILP.
    if not isinstance(minimum, int) or not isinstance(maximum, int):
        raise ValueError("Contract ranges must contain integer minimum and maximum values")
    # Un intervalo invertido describe una instancia inconsistente.
    if minimum > maximum:
        raise ValueError("Contract minimum cannot exceed maximum")
    # Suma el déficit inferior y el exceso superior, solo uno de los dos puede
    # ser positivo para un intervalo válido.
    return max(0, minimum - value) + max(0, value - maximum)


def _streak_deviation(
    values: Sequence[bool],
    minimum: int | None,
    maximum: int | None,
) -> int:
    # Una secuencia vacía no contiene ninguna racha que evaluar.
    if not values:
        return 0
    # Comprueba que los límites de cada racha estén bien definidos.
    if not isinstance(minimum, int) or not isinstance(maximum, int):
        raise ValueError("Streak ranges must contain integer minimum and maximum values")
    # Un mínimo superior al máximo no representa una regla válida.
    if minimum > maximum:
        raise ValueError("Streak minimum cannot exceed maximum")

    # Inicializa la penalización y el inicio de la primera racha.
    deviation = 0
    start = 0
    while start < len(values):
        # Avanza hasta encontrar el primer valor diferente.
        end = start + 1
        while end < len(values) and values[end] == values[start]:
            end += 1
        # Calcula la longitud del bloque constante encontrado.
        run_length = end - start
        # Solo los valores True representan la clase solicitada por el llamador:
        # trabajo para working_streaks o descanso tras invertir la lista.
        if values[start]:
            # Penaliza cualquier longitud por debajo del mínimo.
            deviation += max(0, minimum - run_length)
            # Penaliza cualquier longitud por encima del máximo.
            deviation += max(0, run_length - maximum)
        # Continúa el análisis después del bloque ya procesado.
        start = end
    return deviation


def _weekends(number_of_days: int) -> list[tuple[int, int]]:
    # El calendario de las instancias empieza en lunes: el día 5 es sábado.
    return [
        (day, day + 1)
        for day in range(5, number_of_days - 1, 7)
    ]


def _complete_weekend_penalty(
    nurse_schedule: Sequence[str],
    enabled: bool,
) -> int:
    # Si la regla está desactivada, ningún fin de semana genera penalización.
    if not enabled:
        return 0
    # La desigualdad booleana identifica exactamente un día trabajado.
    return sum(
        (nurse_schedule[saturday] == OFF) != (nurse_schedule[sunday] == OFF)
        for saturday, sunday in _weekends(len(nurse_schedule))
    )


def _same_shift_weekend_penalty(
    nurse_schedule: Sequence[str],
    enabled: bool,
) -> int:
    # Si la regla está desactivada, se acepta cualquier combinación de turnos.
    if not enabled:
        return 0
    # Compara turnos solo cuando ambos días tienen una asignación.
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
    # Acumula coincidencias de todos los patrones solicitados.
    penalty = 0
    for pattern in patterns:
        # Un patrón vacío o no textual no puede compararse con un horario.
        if not isinstance(pattern, str) or not pattern:
            raise ValueError("Unwanted patterns must be non-empty strings")
        # Divide la notación textual ``E-L-N`` en turnos consecutivos.
        pattern_shifts = pattern.split("-")
        # Guarda la longitud para limitar las ventanas del horario.
        length = len(pattern_shifts)
        # Recorre cada inicio posible; las ventanas solapadas se cuentan también.
        penalty += sum(
            list(nurse_schedule[start : start + length]) == pattern_shifts
            for start in range(len(nurse_schedule) - length + 1)
        )
    return penalty
