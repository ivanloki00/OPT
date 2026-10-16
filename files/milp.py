# Importa la interfaz de OR-Tools para crear variables, restricciones y objetivos
# lineales y para ejecutar el solver MILP seleccionado.
from ortools.linear_solver import pywraplp
# Importa el módulo estándar que permite leer las instancias almacenadas en JSON.
import json
# Importa funciones de tiempo para descontar del límite la construcción del modelo.
import time


# ============================================================================
# Modelo MILP incremental: primero garantiza factibilidad y después minimiza
# las dos familias de penalizaciones blandas implementadas en MILP-1.
# ============================================================================
class MILP:
    """
    Resuelve el problema de asignación de turnos mediante un modelo MILP.

    La formulación actual corresponde a MILP-1: mantiene las dos restricciones
    duras del proyecto y minimiza las desviaciones de demanda y asignaciones.
    Los métodos públicos y la representación devuelta conservan la interfaz
    obligatoria del torneo.
    """

    def read_problem_instance(self, problem_path):
        """
        Lee la instancia y prepara los datos necesarios para construir el modelo.

        La construcción del solver se mantiene en :meth:`run`, de modo que este
        método solo realiza lectura, validación estructural e inicialización de
        contenedores internos.
        """
        # Abre la instancia únicamente para preparar los datos del problema.
        with open(problem_path, encoding="utf-8") as instance_file:
            # Convierte el contenido JSON en un diccionario Python.
            instance = json.load(instance_file)

        # Rechaza ficheros con una estructura raíz incompatible con el modelo.
        if not isinstance(instance, dict):
            raise ValueError("The problem instance must contain a JSON object")
        # Conserva la instancia completa para que otros métodos puedan consultarla.
        self.instance = instance
        # Guarda el número de días para dimensionar los bucles y los horarios.
        self.number_of_days = instance["number_of_days"]
        # Guarda la definición de cada turno, incluida su habilidad y demanda diaria.
        self.shifts = instance["shifts"]
        # Guarda la información de cada enfermero y sus límites contractuales.
        self.nurses = instance["nurses"]
        # Crea un acceso directo por identificador para futuras restricciones.
        self.shift_by_id = {shift["shift_id"]: shift for shift in self.shifts}
        # Inicializa el contenedor de variables binarias de asignación.
        self.variables = {}
        # Inicializa las variables de desviación de demanda de cada día y turno.
        self.demand_deviations = {}
        # Inicializa las desviaciones por trabajar menos del mínimo contractual.
        self.assignment_under = {}
        # Inicializa las desviaciones por trabajar más del máximo contractual.
        self.assignment_over = {}
        

    def get_best_solution(self):
        """
        Devuelve una copia de la mejor solución en el formato del torneo.

        Cada fila representa un enfermero y cada posición de la fila representa
        un día. El valor es el identificador del turno trabajado o ``"OFF"``.
        """
        # Si el solver no encontró una solución aceptable, devuelve el formato
        # vacío esperado por la interfaz en vez de exponer un atributo inexistente.
        if self.best_solution is None:
            return []
        # Devuelve una copia independiente de cada fila para impedir que el código
        # externo modifique accidentalmente la mejor solución almacenada.
        return [row[:] for row in self.best_solution]


    def run(self):
        """
        Construye, limita, resuelve y extrae el modelo MILP completo.

        El tiempo utilizado en la construcción se descuenta del límite recibido,
        para que la resolución respete el presupuesto total de la competición.
        """
        # Esta llamada es obligatoria: carga la instancia antes de construir el modelo
        # y debe conservarse para cumplir la interfaz del torneo.
        self.read_problem_instance(self.problem_path)
        # Crea el backend MILP solicitado, normalmente SCIP.
        solver = pywraplp.Solver.CreateSolver(self.solver_type)
        # Informa explícitamente si OR-Tools no pudo crear el backend indicado.
        if solver is None:
            raise RuntimeError(f"Unable to create solver {self.solver_type!r}")
        # Empieza a medir después de leer los datos para controlar la fase de modelado.
        t1 = time.time()
        # Crea una variable binaria por cada asignación enfermero-día-turno permitida.
        self._create_decision_variables(solver)
        # Impone que cada enfermero trabaje como máximo un turno por día.
        self._add_uniqueness_constraints(solver)
        # Impone que cada turno y día tenga al menos una persona cualificada.
        self._add_coverage_constraints(solver)
        # Añade las variables que miden el desajuste respecto a la demanda preferida.
        self._add_demand_deviation_variables(solver)
        # Añade las variables que miden incumplimientos de los límites de asignación.
        self._add_assignment_deviation_variables(solver)
        # Define la suma de desviaciones como objetivo a minimizar.
        self._set_objective(solver)
        # Finaliza la medición de construcción antes de reservar tiempo de búsqueda.
        t2 = time.time()
        # Calcula el tiempo restante sin permitir un límite cero para el solver.
        remaining_time = max(1, int(self.time_deadline - (t2 - t1)))
        # OR-Tools recibe el límite en milisegundos, no en segundos.
        solver.SetTimeLimit(remaining_time * 1000)
        # Resuelve el modelo dentro del tiempo disponible.
        result_type = solver.Solve()
        # Solo acepta soluciones óptimas o factibles; estados como INFEASIBLE
        # y UNKNOWN no deben producir una solución con apariencia de válida.
        if result_type not in (
            pywraplp.Solver.OPTIMAL,
            pywraplp.Solver.FEASIBLE,
        ):
            # Marca explícitamente que no existe una solución utilizable.
            self.best_solution = None
            return
        # Guarda el valor oficial del objetivo sin volver a consultar masivamente
        # las variables auxiliares, lo que evita problemas del backend tras resolver.
        self.objective_value = solver.Objective().Value()
        # Traduce las variables binarias activas al formato externo del torneo.
        self.best_solution = self._extract_solution()

    def _create_decision_variables(self, solver):
        # Recorre cada combinación posible de enfermero, día y turno.
        for nurse_index, nurse in enumerate(self.nurses):
            # Convierte las habilidades a conjunto para comprobar pertenencia en O(1).
            nurse_skills = set(nurse["skills"])
            for day in range(self.number_of_days):
                for shift in self.shifts:
                    # Obtiene el identificador estable usado en la solución externa.
                    shift_id = shift["shift_id"]
                    # No crea variables imposibles: un enfermero sin la habilidad
                    # requerida nunca puede cubrir este turno.
                    if shift["needed_skill"] not in nurse_skills:
                        continue
                    # La clave identifica de forma única una asignación permitida.
                    key = (nurse_index, day, shift_id)
                    # Una variable igual a uno significa que el enfermero trabaja
                    # ese turno concreto durante ese día.
                    self.variables[key] = solver.BoolVar(
                        f"work_{nurse_index}_{day}_{shift_id}"
                    )

    def _add_uniqueness_constraints(self, solver):
        # Crea una restricción independiente para cada enfermero y cada día.
        for nurse_index in range(len(self.nurses)):
            for day in range(self.number_of_days):
                # La suma de turnos del enfermero queda acotada entre cero y uno.
                constraint = solver.Constraint(0, 1)
                for shift in self.shifts:
                    # Recupera la variable si el enfermero está cualificado para ella.
                    variable = self.variables.get(
                        (nurse_index, day, shift["shift_id"])
                    )
                    # Las variables inexistentes representan asignaciones prohibidas
                    # y, por tanto, no deben añadirse a la restricción.
                    if variable is not None:
                        constraint.SetCoefficient(variable, 1)

    def _add_coverage_constraints(self, solver):
        # Crea una cobertura mínima para cada combinación de día y turno.
        for day in range(self.number_of_days):
            for shift in self.shifts:
                # Exige al menos una persona cualificada y permite cualquier exceso.
                constraint = solver.Constraint(1, solver.infinity())
                # Extrae los datos necesarios para filtrar candidatos.
                shift_id = shift["shift_id"]
                required_skill = shift["needed_skill"]
                for nurse_index, nurse in enumerate(self.nurses):
                    # Un enfermero sin la habilidad no puede contribuir a la cobertura.
                    if required_skill not in set(nurse["skills"]):
                        continue
                    # La poda anterior garantiza que esta variable existe.
                    variable = self.variables[(nurse_index, day, shift_id)]
                    # Cada enfermero cualificado aporta una unidad de cobertura.
                    constraint.SetCoefficient(variable, 1)

    def _add_demand_deviation_variables(self, solver):
        # Modela el valor absoluto de la diferencia entre cobertura y demanda
        # mediante dos desigualdades lineales y una variable no negativa.
        for day in range(self.number_of_days):
            for shift in self.shifts:
                # Identifica el turno y obtiene su demanda preferida para ese día.
                shift_id = shift["shift_id"]
                preferred = shift["demand"][day]
                # Esta variable mide tanto déficit como exceso respecto a preferred.
                deviation = solver.IntVar(
                    0,
                    solver.infinity(),
                    f"demand_deviation_{day}_{shift_id}",
                )
                # Guarda la variable para incluirla posteriormente en el objetivo.
                self.demand_deviations[(day, shift_id)] = deviation
                # Primera desigualdad: cobertura - desviación <= demanda.
                constraint = solver.Constraint(-solver.infinity(), preferred)
                constraint.SetCoefficient(deviation, -1)
                for nurse_index, nurse in enumerate(self.nurses):
                    # Solo cuenta enfermeros que pueden cubrir la habilidad del turno.
                    if shift["needed_skill"] not in set(nurse["skills"]):
                        continue
                    # Recupera la variable binaria de esa asignación cualificada.
                    variable = self.variables[(nurse_index, day, shift_id)]
                    # Suma la cobertura en la desigualdad superior.
                    constraint.SetCoefficient(variable, 1)

                # Segunda desigualdad: desviación >= demanda - cobertura.
                constraint = solver.Constraint(-solver.infinity(), -preferred)
                # El signo negativo transforma la desigualdad en la forma lineal
                # necesaria para representar la parte inferior del valor absoluto.
                constraint.SetCoefficient(deviation, -1)
                for nurse_index, nurse in enumerate(self.nurses):
                    # Vuelve a filtrar por habilidad para contar exactamente
                    # las mismas asignaciones que en la primera desigualdad.
                    if shift["needed_skill"] not in set(nurse["skills"]):
                        continue
                    # Recupera la variable de cobertura asociada.
                    variable = self.variables[(nurse_index, day, shift_id)]
                    # Resta la cobertura para acotar la desviación por abajo.
                    constraint.SetCoefficient(variable, -1)

    def _add_assignment_deviation_variables(self, solver):
        # Modela por separado el déficit y el exceso de asignaciones de cada enfermero.
        for nurse_index, nurse in enumerate(self.nurses):
            # Variable no negativa para asignaciones por debajo del mínimo.
            under = solver.IntVar(
                0,
                solver.infinity(),
                f"assignment_under_{nurse_index}",
            )
            # Variable no negativa para asignaciones por encima del máximo.
            over = solver.IntVar(
                0,
                solver.infinity(),
                f"assignment_over_{nurse_index}",
            )
            # Conserva ambas variables para incorporarlas al objetivo.
            self.assignment_under[nurse_index] = under
            self.assignment_over[nurse_index] = over

            # Impone: asignaciones + under >= mínimo contractual.
            constraint = solver.Constraint(
                nurse["min_assignments"],
                solver.infinity(),
            )
            # Un déficit positivo compensa las asignaciones que faltan.
            constraint.SetCoefficient(under, 1)
            for day in range(self.number_of_days):
                for shift in self.shifts:
                    # Solo suma variables existentes, es decir, turnos permitidos.
                    variable = self.variables.get(
                        (nurse_index, day, shift["shift_id"])
                    )
                    if variable is not None:
                        # Cada turno trabajado incrementa el total contractual.
                        constraint.SetCoefficient(variable, 1)

            # Impone: asignaciones - over <= máximo contractual.
            constraint = solver.Constraint(
                -solver.infinity(),
                nurse["max_assignments"],
            )
            # Un exceso positivo permite representar asignaciones por encima del máximo.
            constraint.SetCoefficient(over, -1)
            for day in range(self.number_of_days):
                for shift in self.shifts:
                    # Busca las mismas variables binarias para mantener el mismo total.
                    variable = self.variables.get(
                        (nurse_index, day, shift["shift_id"])
                    )
                    if variable is not None:
                        # Cada asignación resta margen disponible frente al máximo.
                        constraint.SetCoefficient(variable, 1)

    def _set_objective(self, solver):
        # Configura el objetivo de MILP-1 como minimización de todas las desviaciones.
        objective = solver.Objective()
        objective.SetMinimization()
        # Penaliza por igual cada unidad de desviación de demanda.
        for deviation in self.demand_deviations.values():
            objective.SetCoefficient(deviation, 1)
        # Penaliza por igual no alcanzar el mínimo de asignaciones.
        for deviation in self.assignment_under.values():
            objective.SetCoefficient(deviation, 1)
        # Penaliza por igual superar el máximo de asignaciones.
        for deviation in self.assignment_over.values():
            objective.SetCoefficient(deviation, 1)

    def _extract_solution(self):
        # Construye una matriz con una fila por enfermero y una columna por día.
        solution = []
        for nurse_index in range(len(self.nurses)):
            # Empieza cada horario suponiendo que el enfermero descansa ese día.
            nurse_schedule = []
            for day in range(self.number_of_days):
                assigned_shift = "OFF"
                for shift in self.shifts:
                    # Consulta únicamente variables que fueron creadas por habilidad.
                    variable = self.variables.get(
                        (nurse_index, day, shift["shift_id"])
                    )
                    # Un valor superior a 0.5 se interpreta como variable binaria activa.
                    if variable is not None and variable.solution_value() > 0.5:
                        # Conserva el identificador del turno exigido por el torneo.
                        assigned_shift = shift["shift_id"]
                        # La unicidad diaria garantiza que no hay que buscar otro turno.
                        break
                # Añade el turno elegido o OFF a la secuencia del enfermero.
                nurse_schedule.append(assigned_shift)
            # Añade la secuencia completa a la solución externa.
            solution.append(nurse_schedule)
        return solution

    def __init__(self,time_deadline,problem_path, solver_type='SCIP', **kwargs):
        """
        Class initializer. It takes as an argument the maximum computation time (in seconds), controlled externally, and the path that contains the problem instance to be solved
        YOU CAN MODIFY THE HEADER TO INCLUDE OPTIONAL PARAMETERS WITH DEFAULT VALUES ( e.g., __init__(self, time_deadline, problem_path, mut_prob=0.5) )
        You should configure the algorithm before its execution in this method (i.e., hyperparameter values, data structure initialization, etc.)
        Args:
            problem_path: String that contains the path to the file that describes the problem instance
            time_deadline: Computation time limit for the metaheuristic
            kwargs: Other arguments can be passed to the algorithm using key-value pairs. For instance, Metaheuristic(20, 'instance1.txt', mut_prob=0.3) would call the initializer with 20 seconds, for reading the instance1.txt file and passing an optional parameter of mut_prob=0.3
        """
        # Conserva la ruta que run() debe cargar al comenzar cada ejecución.
        self.problem_path = problem_path
        # Inicializa la mejor solución como inexistente hasta que el solver termine.
        self.best_solution = None
        # Guarda el límite global de cálculo recibido por la interfaz del torneo.
        self.time_deadline = time_deadline
        # Guarda el nombre del backend MILP que debe crear OR-Tools.
        self.solver_type = solver_type
        # Permitirá consultar el valor del objetivo después de una resolución válida.
        self.objective_value = None




    
