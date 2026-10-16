# Investigación bibliográfica y enfoque recomendado

## 1. Resumen ejecutivo

El proyecto aborda un **Nurse Rostering Problem (NRP)** con:

- 7 instancias.
- 28 días.
- 5 turnos.
- 2 habilidades.
- 49 enfermeros en las instancias 01-05.
- 50 enfermeros en las instancias 06-07.
- Cobertura mínima cualificada y unicidad diaria como restricciones duras.
- Demanda, asignaciones, rachas, fines de semana, patrones y peticiones como restricciones blandas.
- Un límite de 120 segundos por ejecución.

La recomendación principal, basada en la literatura y en la estructura concreta del proyecto, es:

```text
Evaluador común y validador
        ↓
MILP compacto con poda por habilidades
        ↓
Solución factible inicial
        ↓
VNS/ALNS con reparación especializada
        ↓
Evaluación incremental
        ↓
Comparación estadística contra baselines
```

Esta recomendación es una hipótesis de diseño fundamentada en la literatura, no un resultado experimental todavía. Debe validarse mediante experimentos sobre las siete instancias.

---

## 2. Literatura relevante

### 2.1 Revisiones fundamentales

#### Burke et al. (2004)

**E. K. Burke, P. De Causmaecker, G. Vanden Berghe y H. Van Landeghem, “The State of the Art of Nurse Rostering”, Journal of Scheduling.**

- DOI: [10.1023/B:JOSH.0000046076.75950.0b](https://doi.org/10.1023/B:JOSH.0000046076.75950.0b)
- Revisión específica del *Nurse Rostering Problem*.
- Clasifica formulaciones exactas, programación por restricciones, búsquedas locales, metaheurísticas y métodos híbridos.
- Justifica separar:
  - restricciones duras de factibilidad;
  - penalizaciones blandas de calidad;
  - preferencias individuales;
  - restricciones de secuencia.

Es la referencia base para justificar la estructura del modelo del proyecto.

#### Ernst et al. (2004)

**A. T. Ernst, H. Jiang, M. Krishnamoorthy y D. Sier, “Staff scheduling and rostering: A review of applications, methods and models”, European Journal of Operational Research.**

- DOI: [10.1016/S0377-2217(03)00095-X](https://doi.org/10.1016/S0377-2217(03)00095-X)
- Revisión general de planificación de personal.
- Compara programación matemática, *constraint programming*, búsqueda local, algoritmos evolutivos y métodos híbridos.
- Permite justificar que la evaluación no debe basarse únicamente en el tiempo de ejecución, sino también en:
  - factibilidad;
  - calidad de la solución;
  - robustez;
  - comportamiento medio;
  - sensibilidad a las instancias.

#### Van den Bergh et al. (2013)

**J. Van den Bergh, J. Beliën, P. De Bruecker, E. Demeulemeester y L. De Boeck, “Personnel scheduling: A literature review”, European Journal of Operational Research.**

- DOI: [10.1016/j.ejor.2012.11.029](https://doi.org/10.1016/j.ejor.2012.11.029)
- Sitúa el problema de turnos de enfermería dentro de la planificación general de personal.
- Revisa modelos multiobjetivo y ponderados.
- Es útil para explicar el equilibrio entre cobertura, equidad, carga de trabajo y preferencias.

### 2.2 Competiciones internacionales

#### INRC-I

**S. Haspeslagh et al., “The first international nurse rostering competition 2010”, Annals of Operations Research.**

- DOI: [10.1007/s10479-012-1062-0](https://doi.org/10.1007/s10479-012-1062-0)
- [Página de la competición INRC-I](https://patat.cs.kuleuven.be/basic-page/first-international-nurse-rostering-competition)

La competición es relevante porque utiliza:

- evaluador común;
- instancias públicas y ocultas;
- límites de tiempo;
- varias ejecuciones;
- comparación entre métodos diferentes;
- clasificación basada en la calidad de las soluciones.

Esta metodología respalda directamente los requisitos experimentales del proyecto.

#### INRC-II

**S. Ceschia et al., “The Second International Nurse Rostering Competition”.**

- DOI: [10.1007/s10479-018-2816-0](https://doi.org/10.1007/s10479-018-2816-0)
- Preprint: [arXiv:1501.04177](https://arxiv.org/abs/1501.04177)

INRC-II introduce dependencias entre semanas y restricciones relacionadas con la historia anterior del enfermero. Aunque este proyecto utiliza un horizonte de 28 días, la idea es directamente aplicable:

> Las restricciones de rachas, fines de semana y patrones no deben evaluarse de forma independiente para cada día.

### 2.3 Métodos híbridos

#### Burke, Li y Qu (2010)

**E. K. Burke, J. Li y R. Qu, “A hybrid model of integer programming and variable neighbourhood search for highly-constrained nurse rostering problems”, European Journal of Operational Research.**

- DOI: [10.1016/j.ejor.2009.07.036](https://doi.org/10.1016/j.ejor.2009.07.036)

Es la referencia primaria más cercana al enfoque recomendado:

1. Utiliza programación entera para estructurar la solución y manejar restricciones críticas.
2. Aplica *Variable Neighbourhood Search* para mejorar las penalizaciones restantes.
3. Explota vecindarios especializados del problema de turnos.

Este patrón es preferible a un algoritmo genético genérico porque los operadores pueden diseñarse directamente para la cobertura, los fines de semana, las rachas, los cambios de turno, los patrones prohibidos y las peticiones de descanso.

#### Burke y Curtois (2014)

**E. K. Burke y T. Curtois, “New approaches to nurse rostering benchmark instances”, European Journal of Operational Research.**

- DOI: [10.1016/j.ejor.2014.01.039](https://doi.org/10.1016/j.ejor.2014.01.039)

Su relevancia principal es metodológica: no es suficiente con probar una única instancia ni con informar únicamente del mejor resultado. Se deben estudiar familias de instancias y el comportamiento estadístico de los métodos.

### 2.4 Branch-and-Price y generación de columnas

#### Hu et al. (2023)

**W. Hu, X. He, L. Luo y P. M. Pardalos, “A branch-and-price approach for the nurse rostering problem with multiple units”.**

- [arXiv:2311.05438](https://arxiv.org/abs/2311.05438)

La generación de columnas representa patrones completos de trabajo por enfermero.

**Ventajas:**

- modela naturalmente rachas;
- incorpora descansos y patrones;
- reduce parte de la complejidad combinatoria;
- puede ser muy potente en problemas grandes.

**Inconvenientes para este proyecto:**

- requiere un maestro restringido;
- subproblema de *pricing*;
- costes duales;
- *branching*;
- recuperación de soluciones enteras;
- mayor dificultad de depuración y explicación;
- riesgo elevado de no aprovechar bien los 120 segundos.

Se recomienda como línea futura, no como primera implementación del torneo.

---

## 3. Análisis del problema concreto

Según las instancias de `instances/`:

- 7 instancias.
- 28 días.
- 5 turnos.
- 2 habilidades.
- 49 enfermeros en las instancias 01-05.
- 50 enfermeros en las instancias 06-07.

El número máximo aproximado de variables binarias de asignación, antes de realizar poda, es:

```text
50 enfermeros × 28 días × 5 turnos = 7.000 variables
```

### 3.1 Variables de asignación

Sea:

\[
x_{n,d,s} =
\begin{cases}
1 & \text{si el enfermero } n \text{ trabaja el turno } s \text{ el día } d,\\
0 & \text{en otro caso.}
\end{cases}
\]

### 3.2 Restricción de unicidad diaria

Un enfermero no puede trabajar más de un turno el mismo día:

\[
\sum_{s \in S} x_{n,d,s} \leq 1
\qquad \forall n,d
\]

### 3.3 Cobertura mínima cualificada

Para cada día y turno debe existir, al menos, un enfermero con la habilidad necesaria:

\[
\sum_{n:\,skill(n)\supseteq skill(s)}
x_{n,d,s} \geq 1
\qquad \forall d,s
\]

La demanda preferida no debe confundirse con esta cobertura mínima:

- la cobertura mínima cualificada es una condición dura;
- la demanda de 6, 8 o 10 enfermeros por turno es una preferencia que se penaliza si se incumple.

### 3.4 Componentes blandas

La función objetivo debe penalizar:

1. desviación de demanda;
2. desviación del número total de asignaciones;
3. rachas de trabajo demasiado cortas o largas;
4. rachas de descanso demasiado cortas o largas;
5. fines de semana incompletos;
6. turnos diferentes dentro del mismo fin de semana;
7. patrones no deseados;
8. peticiones de días libres incumplidas;
9. peticiones de turnos libres incumplidas.

---

## 4. Comparación de enfoques

| Enfoque | Calidad potencial | Facilidad de explicar | Riesgo | Encaje en 120 s |
|---|---:|---:|---:|---:|
| MILP compacto | Alta | Alta | Medio | Bueno |
| CP-SAT | Alta | Media | Medio | Bueno |
| VNS/ALNS | Alta | Alta-media | Medio | Muy bueno |
| Tabu Search | Alta | Media | Medio | Muy bueno |
| GA simple | Variable | Alta | Medio-alto | Bueno |
| GA memético | Alta | Media | Medio | Bueno |
| Branch-and-Price | Muy alta | Baja | Alto | Incierto |
| MILP + VNS/ALNS | Muy alta | Alta | Medio | Mejor equilibrio |

### 4.1 MILP compacto

**Ventajas:**

- modela claramente las restricciones duras;
- produce soluciones factibles con trazabilidad;
- permite obtener cotas inferiores si termina con estado óptimo o una brecha;
- es fácil de explicar matemáticamente;
- encaja con el esqueleto actual de `milp.py`.

**Riesgos:**

- linealizar mal una racha o un patrón;
- dar pesos desproporcionados a las penalizaciones;
- introducir demasiadas variables auxiliares;
- consumir el límite construyendo un modelo excesivamente general.

### 4.2 VNS/ALNS

**Ventajas:**

- muy adaptable a las nueve penalizaciones;
- puede explotar rápidamente una solución factible;
- permite operadores semánticos;
- no exige linealizar completamente todas las reglas blandas.

**Riesgos:**

- una representación sin reparación produce muchas soluciones inviables;
- las penalizaciones necesitan evaluación incremental;
- hay que controlar el tiempo estrictamente;
- los resultados requieren varias semillas.

### 4.3 Tabu Search

Es una alternativa adecuada si se necesita una implementación más simple que ALNS. Puede trabajar con movimientos de:

- cambio de turno de un enfermero a otro;
- intercambio de dos turnos;
- modificación de un bloque semanal;
- desplazamiento de una secuencia de trabajo.

Debe incluir una lista tabú y un criterio de aspiración basado en la mejor solución global. Es menos flexible que ALNS para seleccionar operadores adaptativamente.

### 4.4 Algoritmos genéticos y meméticos

Un algoritmo genético puro no es la primera recomendación porque el cromosoma natural, una matriz de aproximadamente `49-50 × 28`, tiende a romper la cobertura al realizar cruces.

Si se utiliza, debe ser memético:

1. generación inicial factible;
2. cruce por bloques temporales, no por genes arbitrarios;
3. reparación de cobertura y unicidad;
4. búsqueda local después del cruce y la mutación.

El GA base del torneo debe conservarse como baseline, pero no como estrategia principal.

---

## 5. Enfoque recomendado

### Fase 1: evaluador único y validador

Antes de implementar MILP o metaheurística, crear un evaluador común que devuelva:

```text
hard_feasible
total_penalty
demand_penalty
assignment_penalty
working_streak_penalty
free_streak_penalty
complete_weekend_penalty
same_shift_weekend_penalty
unwanted_pattern_penalty
days_off_penalty
shift_off_penalty
```

Este evaluador debe utilizarse en:

- MILP;
- metaheurística;
- baselines;
- experimentos;
- pruebas;
- análisis final.

Una solución inviable debe compararse como:

\[
+\infty
\]

tal como exige la especificación del proyecto.

### Fase 2: MILP compacto

Crear únicamente variables de asignación si el enfermero tiene la habilidad requerida:

\[
x_{n,d,s} \in \{0,1\}
\]

Añadir variables auxiliares para:

- déficit y exceso de demanda;
- exceso o defecto de asignaciones;
- detección de rachas;
- fines de semana;
- solicitudes;
- patrones.

Se recomienda desarrollar el modelo progresivamente:

#### MILP-0: factibilidad

- lectura de instancia;
- poda por habilidad;
- unicidad diaria;
- cobertura mínima;
- extracción de solución;
- validación externa.

#### MILP-1: demanda y asignaciones

Añadir:

- desviación respecto a demanda;
- mínimos y máximos de asignaciones;
- función objetivo básica.

#### MILP-2: modelo completo

Añadir:

- rachas;
- descansos;
- fines de semana;
- patrones;
- peticiones.

Esta progresión permite realizar un estudio de ablación y demostrar el efecto de cada familia de restricciones.

### Fase 3: VNS/ALNS como mejora

Utilizar la solución factible del MILP como punto de partida.

#### Vecindarios prioritarios

1. **Relocate:** cambiar el turno de un enfermero en un día.
2. **Swap:** intercambiar los turnos de dos enfermeros el mismo día.
3. **Cross-day swap:** intercambiar asignaciones entre dos días.
4. **Block move:** modificar un bloque de 3-7 días.
5. **Weekend move:** reparar o completar un fin de semana.
6. **Pattern destroy/rebuild:** eliminar una secuencia conflictiva y reconstruirla.
7. **Coverage repair:** solucionar primero déficits de cobertura.
8. **Fairness repair:** reducir cargas excesivas, rachas y solicitudes incumplidas.

#### ALNS

Los operadores deben tener pesos adaptativos:

- aumentar el peso si producen soluciones factibles;
- aumentar el peso si mejoran la solución global;
- aumentar el peso si reducen rápidamente déficits de cobertura;
- reducir el peso si generan muchos movimientos inviables.

La secuencia recomendada es:

```text
MILP compacto
→ solución factible
→ VNS intensiva
→ ALNS con destrucción y reconstrucción
→ intensificación Tabu sobre los mejores vecinos
```

No se recomienda ejecutar VNS, ALNS y GA completos simultáneamente en una sola ejecución, porque el coste de coordinación puede superar el beneficio.

---

## 6. Distribución del límite de 120 segundos

Una primera configuración experimental razonable sería:

```text
0-5 s       Lectura y preprocesamiento
5-45 s      Construcción y ejecución inicial del MILP
45-110 s    VNS/ALNS
110-120 s   Validación, extracción y guardado de la mejor solución
```

Esta distribución debe validarse experimentalmente. Si el MILP obtiene soluciones factibles rápidamente, se puede reducir su presupuesto y entregar más tiempo a la metaheurística.

El límite debe incluir:

- lectura;
- preprocesamiento;
- inicialización;
- construcción del modelo;
- búsqueda;
- reparación;
- extracción;
- validación.

---

## 7. Diseño experimental recomendado

Comparar como mínimo:

1. búsqueda aleatoria del torneo;
2. algoritmo genético base del torneo;
3. MILP compacto;
4. VNS/ALNS desde una solución constructiva;
5. MILP + VNS/ALNS;
6. opcionalmente CP-SAT o una segunda formulación MILP.

### 7.1 Métricas

Registrar en cada ejecución:

- factibilidad;
- valor total de la función objetivo;
- cada una de las nueve penalizaciones;
- tiempo hasta la primera solución factible;
- tiempo hasta la mejor solución;
- tiempo total;
- número de movimientos evaluados;
- número de reparaciones;
- semilla;
- configuración;
- solver;
- gap MILP, si está disponible.

### 7.2 Repeticiones

Para cada instancia y configuración:

- utilizar como mínimo 10 semillas para métodos estocásticos;
- usar la misma lista de semillas para todos los métodos comparables;
- usar las mismas poblaciones iniciales al comparar configuraciones de la metaheurística;
- mantener el mismo límite temporal;
- utilizar la misma máquina y versiones de Python y OR-Tools.

### 7.3 Presupuestos de tiempo

Comparar al menos:

```text
30 s MILP + 90 s VNS/ALNS
60 s MILP + 60 s VNS/ALNS
90 s MILP + 30 s VNS/ALNS
```

### 7.4 Ablation study

Estudiar el efecto de:

- MILP sin restricciones blandas;
- MILP con poda por habilidad;
- VNS sin evaluación incremental;
- VNS con evaluación incremental;
- ALNS sin reparación especializada;
- ALNS con reparación;
- MILP + VNS frente a VNS puro;
- diferentes presupuestos de tiempo.

### 7.5 Análisis estadístico

Para cada instancia:

- media;
- mediana;
- desviación estándar;
- intervalos de confianza mediante bootstrap;
- prueba de Friedman para comparar varios algoritmos;
- prueba de Wilcoxon post-hoc para comparar el híbrido con cada baseline;
- tamaño del efecto;
- porcentaje de ejecuciones factibles.

---

## 8. Riesgos principales y mitigaciones

### Riesgo 1: evaluador incorrecto

Es el mayor riesgo del proyecto. Si el MILP optimiza una función distinta de la utilizada por el torneo, todos los resultados carecen de valor.

**Mitigación:** implementar primero el evaluador independiente y validarlo con ejemplos manuales pequeños.

### Riesgo 2: confusión entre cobertura mínima y demanda preferida

La cobertura mínima es dura. La demanda preferida es blanda.

El modelo no debe permitir que un enfermero sin la habilidad adecuada cubra un turno a cambio de una penalización.

### Riesgo 3: pesos incorrectos

Las nueve penalizaciones pueden tener escalas diferentes. Un peso excesivo para peticiones puede provocar déficit de cobertura si la formulación no protege las restricciones duras.

**Mitigación:** normalizar o utilizar objetivos lexicográficos y documentar cada peso.

### Riesgo 4: modelo MILP demasiado complejo

Un modelo que intente capturar todos los patrones mediante demasiadas variables auxiliares puede agotar los 120 segundos durante la construcción.

**Mitigación:**

- poda por habilidad;
- construcción progresiva;
- diccionarios indexados;
- variables auxiliares solo donde sean necesarias;
- medición separada del tiempo de construcción y resolución.

### Riesgo 5: reparación deficiente

La reparación debe preservar siempre:

1. cobertura mínima cualificada;
2. un único turno por enfermero y día.

No debe limitarse a asignar turnos aleatoriamente.

---

## 9. Conclusión

La mejor estrategia inicial para este proyecto es:

```text
Evaluador común y validador
        ↓
MILP compacto con poda por habilidades
        ↓
Solución factible inicial
        ↓
VNS/ALNS con reparación especializada
        ↓
Evaluación incremental
        ↓
Comparación estadística contra baselines
```

La elección se apoya especialmente en:

- Burke et al. (2004), por la taxonomía del NRP.
- Ernst et al. (2004), por la comparación de métodos de planificación.
- INRC-I e INRC-II, por la metodología experimental y las restricciones de secuencia.
- Burke, Li y Qu (2010), por la combinación de programación entera y VNS.
- La estructura real del proyecto y su límite de 120 segundos.

La generación de columnas, CP-SAT o un algoritmo memético avanzado pueden estudiarse como variantes, pero no deberían ser la primera implementación. La prioridad debe ser conseguir un evaluador correcto, una solución factible reproducible y un MILP compacto antes de optimizar la metaheurística.
