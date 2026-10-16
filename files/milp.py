from ortools.linear_solver import pywraplp
import json
import time


# ============================================================================
# MILP: modelo incremental de factibilidad y primeras penalizaciones blandas
# ============================================================================
class MILP:
    """
    In this class you should implement your MILP model proposal. The code that you submit for the tournament should be 
    included in this class. Please, bear in mind that the current template includes all the mandatory methods, but you can implement any
    other method that you need to. In fact, you are highly encouraged to make a good software design a decompose the behavior of your algorithm
    into several iindependent components or methods.

    The HEADERS for the provided methods CANNOT be modified. Failing to do so will result in your algorithm not participating in the tournament.
    """

    def read_problem_instance(self, problem_path):
        """
        TODO: This method is MANDATORY. The goal of this method is reading a hard drive path that contains a text file with a problem instance.
        The method should read all of the information in the problem instance and store it inside attributes of the Metaheuristic object. 
        This method SHOULD NOT SEARCH nor carry out tasks that indirectly contribute to searching. Typically, you will prepare
        data structures to hold relevant information from the problem instance. Please, DO NOT BUILD THE MODEL in this method. The model should be built in the run() method.
        Args:
            problem_path: Text file that contains information about a problem instance
        """
        # --- Cargar datos sin construir ni resolver el modelo todavía. ---
        with open(problem_path, encoding="utf-8") as instance_file:
            instance = json.load(instance_file)

        if not isinstance(instance, dict):
            raise ValueError("The problem instance must contain a JSON object")
        self.instance = instance
        self.number_of_days = instance["number_of_days"]
        self.shifts = instance["shifts"]
        self.nurses = instance["nurses"]
        self.shift_by_id = {shift["shift_id"]: shift for shift in self.shifts}
        self.variables = {}
        self.demand_deviations = {}
        self.assignment_under = {}
        self.assignment_over = {}
        

    def get_best_solution(self):
        """
        This method is used to return EXTERNALLY the best solution found so far in the metaheuristic. The solution should be returned in a very
        specific format. For that, you are addressed to the project specification. Please, bear in mind that, INTERNALLY, you can represent
        solutions in any format that you see fit. However, externally, solutions should always be returned in the same way in order to participate in the tournament.
        If you follow this template, self.best_solution should contain the best solution found so far and you should return that solution encoded in the specified format.
        If the returned solution does not follow the format specified in the project specification, you will be disqualified from the tournament.
        """
        # --- Copiar la solución para evitar exponer el estado interno. ---
        if self.best_solution is None:
            return []
        return [row[:] for row in self.best_solution]


    def run(self):
        """
        This method is in charge of reading the problem instance from a file and then executing the whole logic of the metaheuristic, including initialization
        and the main search procedure.
        TODO: You should implement from the pass statement.
        """
        # --- Flujo obligatorio: leer, construir, limitar, resolver y extraer. ---
        self.read_problem_instance(self.problem_path) #You should keep this line. Otherwise, disqualified from the tournament
        solver = pywraplp.Solver.CreateSolver(self.solver_type)
        if solver is None:
            raise RuntimeError(f"Unable to create solver {self.solver_type!r}")
        t1 = time.time()
        self._create_decision_variables(solver)
        self._add_uniqueness_constraints(solver)
        self._add_coverage_constraints(solver)
        self._add_demand_deviation_variables(solver)
        self._add_assignment_deviation_variables(solver)
        self._set_objective(solver)
        t2 = time.time()
        remaining_time = max(1, int(self.time_deadline - (t2 - t1)))
        solver.SetTimeLimit(remaining_time * 1000)
        result_type = solver.Solve()
        if result_type not in (
            pywraplp.Solver.OPTIMAL,
            pywraplp.Solver.FEASIBLE,
        ):
            self.best_solution = None
            return
        self.objective_value = solver.Objective().Value()
        self.best_solution = self._extract_solution()

    def _create_decision_variables(self, solver):
        # --- Poda por habilidad: solo se crean asignaciones permitidas. ---
        for nurse_index, nurse in enumerate(self.nurses):
            nurse_skills = set(nurse["skills"])
            for day in range(self.number_of_days):
                for shift in self.shifts:
                    shift_id = shift["shift_id"]
                    if shift["needed_skill"] not in nurse_skills:
                        continue
                    key = (nurse_index, day, shift_id)
                    self.variables[key] = solver.BoolVar(
                        f"work_{nurse_index}_{day}_{shift_id}"
                    )

    def _add_uniqueness_constraints(self, solver):
        # --- Restricción dura: como máximo un turno por enfermero y día. ---
        for nurse_index in range(len(self.nurses)):
            for day in range(self.number_of_days):
                constraint = solver.Constraint(0, 1)
                for shift in self.shifts:
                    variable = self.variables.get(
                        (nurse_index, day, shift["shift_id"])
                    )
                    if variable is not None:
                        constraint.SetCoefficient(variable, 1)

    def _add_coverage_constraints(self, solver):
        # --- Restricción dura: cada turno debe tener cobertura cualificada. ---
        for day in range(self.number_of_days):
            for shift in self.shifts:
                constraint = solver.Constraint(1, solver.infinity())
                shift_id = shift["shift_id"]
                required_skill = shift["needed_skill"]
                for nurse_index, nurse in enumerate(self.nurses):
                    if required_skill not in set(nurse["skills"]):
                        continue
                    variable = self.variables[(nurse_index, day, shift_id)]
                    constraint.SetCoefficient(variable, 1)

    def _add_demand_deviation_variables(self, solver):
        # --- Desviación absoluta respecto a la demanda preferida. ---
        for day in range(self.number_of_days):
            for shift in self.shifts:
                shift_id = shift["shift_id"]
                preferred = shift["demand"][day]
                deviation = solver.IntVar(
                    0,
                    solver.infinity(),
                    f"demand_deviation_{day}_{shift_id}",
                )
                self.demand_deviations[(day, shift_id)] = deviation
                constraint = solver.Constraint(-solver.infinity(), preferred)
                constraint.SetCoefficient(deviation, -1)
                for nurse_index, nurse in enumerate(self.nurses):
                    if shift["needed_skill"] not in set(nurse["skills"]):
                        continue
                    variable = self.variables[(nurse_index, day, shift_id)]
                    constraint.SetCoefficient(variable, 1)

                constraint = solver.Constraint(-solver.infinity(), -preferred)
                constraint.SetCoefficient(deviation, -1)
                for nurse_index, nurse in enumerate(self.nurses):
                    if shift["needed_skill"] not in set(nurse["skills"]):
                        continue
                    variable = self.variables[(nurse_index, day, shift_id)]
                    constraint.SetCoefficient(variable, -1)

    def _add_assignment_deviation_variables(self, solver):
        # --- Desviaciones por debajo y por encima del rango contractual. ---
        for nurse_index, nurse in enumerate(self.nurses):
            under = solver.IntVar(
                0,
                solver.infinity(),
                f"assignment_under_{nurse_index}",
            )
            over = solver.IntVar(
                0,
                solver.infinity(),
                f"assignment_over_{nurse_index}",
            )
            self.assignment_under[nurse_index] = under
            self.assignment_over[nurse_index] = over

            constraint = solver.Constraint(
                nurse["min_assignments"],
                solver.infinity(),
            )
            constraint.SetCoefficient(under, 1)
            for day in range(self.number_of_days):
                for shift in self.shifts:
                    variable = self.variables.get(
                        (nurse_index, day, shift["shift_id"])
                    )
                    if variable is not None:
                        constraint.SetCoefficient(variable, 1)

            constraint = solver.Constraint(
                -solver.infinity(),
                nurse["max_assignments"],
            )
            constraint.SetCoefficient(over, -1)
            for day in range(self.number_of_days):
                for shift in self.shifts:
                    variable = self.variables.get(
                        (nurse_index, day, shift["shift_id"])
                    )
                    if variable is not None:
                        constraint.SetCoefficient(variable, 1)

    def _set_objective(self, solver):
        # --- MILP-1 minimiza las dos familias blandas implementadas. ---
        objective = solver.Objective()
        objective.SetMinimization()
        for deviation in self.demand_deviations.values():
            objective.SetCoefficient(deviation, 1)
        for deviation in self.assignment_under.values():
            objective.SetCoefficient(deviation, 1)
        for deviation in self.assignment_over.values():
            objective.SetCoefficient(deviation, 1)

    def _extract_solution(self):
        # --- Convertir variables binarias al formato externo del torneo. ---
        solution = []
        for nurse_index in range(len(self.nurses)):
            nurse_schedule = []
            for day in range(self.number_of_days):
                assigned_shift = "OFF"
                for shift in self.shifts:
                    variable = self.variables.get(
                        (nurse_index, day, shift["shift_id"])
                    )
                    if variable is not None and variable.solution_value() > 0.5:
                        assigned_shift = shift["shift_id"]
                        break
                nurse_schedule.append(assigned_shift)
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
        self.problem_path = problem_path # This attribute is meant to contain the path to the problem instance
        self.best_solution = None #This attribute is meant to hold, at any time, the best solution found by the algorithm so far. Hence, you should update it accordingly. The solution enconding does not matter.
        self.time_deadline = time_deadline # Computation limit (in seconds) for the metaheuristic 
        self.solver_type = solver_type # Type of solver to use (default is 'SCIP')
        self.objective_value = None




    
