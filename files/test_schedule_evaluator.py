# Importa el framework estándar de pruebas unitarias de Python.
import unittest

# Importa la constante y las funciones públicas que se quieren validar.
from schedule_evaluator import OFF, evaluate_schedule, validate_schedule


# ============================================================================
# Instancia mínima para probar reglas duras y penalizaciones blandas de forma
# rápida, determinista y fácil de razonar durante el desarrollo.
# ============================================================================
def make_instance():
    # Devuelve una instancia pequeña con dos enfermeros y dos turnos diarios.
    return {
        # Usa una semana para incluir también comprobaciones de fin de semana.
        "number_of_days": 7,
        # Declara la habilidad común exigida por los dos turnos.
        "skills": ["Nurse"],
        # Define dos turnos, cada uno con demanda completa durante la semana.
        "shifts": [
            {"shift_id": "E", "needed_skill": "Nurse", "demand": [1] * 7},
            {"shift_id": "L", "needed_skill": "Nurse", "demand": [1] * 7},
        ],
        # Incluye un enfermero con reglas de fin de semana y patrones activos.
        "nurses": [
            {
                # Identificador de la primera persona de prueba.
                "nurse_id": 0,
                # Esta persona puede cubrir ambos turnos.
                "skills": ["Nurse"],
                # Permite cualquier número de asignaciones en esta prueba.
                "min_assignments": 0,
                "max_assignments": 7,
                # Una racha de trabajo de cualquier longitud es válida.
                "min_consecutive_days": 1,
                "max_consecutive_days": 7,
                # También se permiten rachas de descanso de cualquier longitud.
                "min_consecutive_free_days": 0,
                "max_consecutive_free_days": 7,
                # Activa las reglas de fin de semana para probarlas si procede.
                "complete_weekends": True,
                "same_shift_weekend": True,
                # El patrón alterno E-L debe poder detectarse en la semana.
                "unwanted_patterns": ["E-L"],
                # No se solicitan días o turnos concretos como libres.
                "days_off_requests": [],
                "shift_off_requests": [],
            }
            ,
            {
                # Segundo enfermero utilizado para cubrir el turno complementario.
                "nurse_id": 1,
                # También está cualificado para ambos turnos.
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
    # Comprueba que una solución que coincide con la demanda no recibe penalización.
    def test_feasible_schedule_has_zero_penalty_when_ideal(self):
        # Asigna E siempre a la primera persona y L siempre a la segunda.
        schedule = [["E"] * 7, ["L"] * 7]

        # Evalúa el horario frente a la instancia mínima.
        result = evaluate_schedule(schedule, make_instance())

        # La solución cubre ambos turnos y respeta todas las reglas duras.
        self.assertTrue(result.feasible)
        # La cobertura coincide exactamente con la demanda de cada día.
        self.assertEqual(result.total_penalty, 0)
        # Comprueba de forma explícita la primera componente del objetivo.
        self.assertEqual(result.penalties["demand"], 0)

    # Comprueba que una habilidad ausente invalida el horario aunque la cobertura
    # aparente seguir siendo suficiente desde el punto de vista de identificadores.
    def test_daily_uniqueness_and_skill_are_hard_constraints(self):
        # Elimina la única habilidad del primer enfermero.
        instance = make_instance()
        instance["nurses"][0]["skills"] = []
        # Mantiene la solución original para aislar el efecto de la habilidad.
        schedule = [["E"] * 7, ["L"] * 7]

        # Ejecuta solo la validación de restricciones duras.
        validation = validate_schedule(schedule, instance)

        # El horario deja de ser factible por asignar E a una persona no cualificada.
        self.assertFalse(validation.feasible)
        # Verifica que el diagnóstico explica la causa concreta.
        self.assertTrue(any("lacks" in violation for violation in validation.violations))

    # Comprueba que demanda y patrones se contabilizan con reglas reproducibles.
    def test_demand_assignments_and_patterns_are_counted(self):
        # Fuerza demanda cero para E y conserva demanda uno para L.
        instance = make_instance()
        instance["shifts"][0]["demand"] = [0] * 7
        # Desactiva las reglas de fin de semana para aislar demanda y patrones.
        instance["nurses"][0]["complete_weekends"] = False
        instance["nurses"][0]["same_shift_weekend"] = False
        # Alterna E-L en ambas filas para crear apariciones del patrón buscado.
        schedule = [
            ["E", "L", "E", "L", "E", "L", "E"],
            ["L", "E", "L", "E", "L", "E", "L"],
        ]

        # Calcula el desglose completo de penalizaciones.
        result = evaluate_schedule(schedule, instance)

        # La cobertura sigue siendo válida aunque E se produzca sobre la demanda.
        self.assertTrue(result.feasible)
        # Hay siete asignaciones E frente a una demanda igual a cero.
        self.assertEqual(result.penalties["demand"], 7)
        # E-L aparece tres veces en la primera fila.
        self.assertEqual(result.penalties["unwanted_patterns"], 3)

    # Comprueba que una dimensión incorrecta se notifica como error de entrada.
    def test_invalid_dimensions_raise_an_explicit_error(self):
        # La instancia requiere dos filas y aquí solo se proporciona una.
        with self.assertRaises(ValueError):
            validate_schedule([["E"]], make_instance())


if __name__ == "__main__":
    # Permite ejecutar este archivo directamente con el runner de unittest.
    unittest.main()
