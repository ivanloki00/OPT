import unittest

from schedule_evaluator import OFF, evaluate_schedule, validate_schedule


# ============================================================================
# Instancia mínima para probar reglas duras y penalizaciones blandas.
# ============================================================================
def make_instance():
    return {
        "number_of_days": 7,
        "skills": ["Nurse"],
        "shifts": [
            {"shift_id": "E", "needed_skill": "Nurse", "demand": [1] * 7},
            {"shift_id": "L", "needed_skill": "Nurse", "demand": [1] * 7},
        ],
        "nurses": [
            {
                "nurse_id": 0,
                "skills": ["Nurse"],
                "min_assignments": 0,
                "max_assignments": 7,
                "min_consecutive_days": 1,
                "max_consecutive_days": 7,
                "min_consecutive_free_days": 0,
                "max_consecutive_free_days": 7,
                "complete_weekends": True,
                "same_shift_weekend": True,
                "unwanted_patterns": ["E-L"],
                "days_off_requests": [],
                "shift_off_requests": [],
            }
            ,
            {
                "nurse_id": 1,
                "skills": ["Nurse"],
                "min_assignments": 0,
                "max_assignments": 7,
                "min_consecutive_days": 1,
                "max_consecutive_days": 7,
                "min_consecutive_free_days": 0,
                "max_consecutive_free_days": 7,
                "complete_weekends": False,
                "same_shift_weekend": False,
                "unwanted_patterns": [],
                "days_off_requests": [],
                "shift_off_requests": [],
            },
        ],
    }


class ScheduleEvaluatorTests(unittest.TestCase):
    # --- El horario ideal debe ser factible y no penalizarse. ---
    def test_feasible_schedule_has_zero_penalty_when_ideal(self):
        schedule = [["E"] * 7, ["L"] * 7]

        result = evaluate_schedule(schedule, make_instance())

        self.assertTrue(result.feasible)
        self.assertEqual(result.total_penalty, 0)
        self.assertEqual(result.penalties["demand"], 0)

    # --- Las habilidades y la cobertura forman parte de la factibilidad. ---
    def test_daily_uniqueness_and_skill_are_hard_constraints(self):
        instance = make_instance()
        instance["nurses"][0]["skills"] = []
        schedule = [["E"] * 7, ["L"] * 7]

        validation = validate_schedule(schedule, instance)

        self.assertFalse(validation.feasible)
        self.assertTrue(any("lacks" in violation for violation in validation.violations))

    # --- El desglose debe contar demanda y patrones de forma reproducible. ---
    def test_demand_assignments_and_patterns_are_counted(self):
        instance = make_instance()
        instance["shifts"][0]["demand"] = [0] * 7
        instance["nurses"][0]["complete_weekends"] = False
        instance["nurses"][0]["same_shift_weekend"] = False
        schedule = [
            ["E", "L", "E", "L", "E", "L", "E"],
            ["L", "E", "L", "E", "L", "E", "L"],
        ]

        result = evaluate_schedule(schedule, instance)

        self.assertTrue(result.feasible)
        self.assertEqual(result.penalties["demand"], 7)
        self.assertEqual(result.penalties["unwanted_patterns"], 3)

    # --- Las dimensiones inválidas deben producir un error explícito. ---
    def test_invalid_dimensions_raise_an_explicit_error(self):
        with self.assertRaises(ValueError):
            validate_schedule([["E"]], make_instance())


if __name__ == "__main__":
    unittest.main()
