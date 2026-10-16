# Borrador de informe del proyecto

## Estado del desarrollo

Este documento servirá como base para redactar el informe IEEE del proyecto. Resume el trabajo implementado hasta el 16/10/2026 y debe actualizarse después de cada avance validado.

### Problema

El proyecto resuelve un *Nurse Rostering Problem*: asignar enfermeros a turnos durante 28 días respetando habilidades y cobertura mínima, minimizando las desviaciones respecto a la demanda y a las condiciones contractuales y preferencias individuales.

Las instancias disponibles son:

- 7 archivos JSON.
- 28 días por instancia.
- 5 turnos.
- 2 habilidades.
- 49 enfermeros en las instancias 01-05.
- 50 enfermeros en las instancias 06-07.

### Enfoque adoptado

Se ha escogido una estrategia incremental basada en los contenidos del curso:

1. Validador y evaluador independiente.
2. MILP-0 de factibilidad.
3. MILP-1 con primeras penalizaciones blandas.
4. Búsqueda local sencilla como siguiente fase.
5. VNS como ampliación opcional si los resultados lo justifican.

Se prioriza una solución explicable y verificable con OR-Tools frente a incorporar desde el principio técnicas más avanzadas como ALNS, Branch-and-Price o CP-SAT.

## Componentes desarrollados

### Evaluador y validador

Archivo: `files/schedule_evaluator.py`.

Se ha implementado una pieza común para:

- validar el número de enfermeros y días;
- comprobar que los turnos existen;
- comprobar que cada enfermero posee la habilidad requerida;
- comprobar que ningún enfermero trabaja más de un turno al día;
- comprobar que cada turno tiene cobertura cualificada;
- calcular las nueve penalizaciones blandas;
- devolver un desglose de penalizaciones;
- devolver `infinity` cuando el horario es infactible.

Las nueve componentes calculadas son:

1. demanda;
2. número total de asignaciones;
3. rachas de trabajo;
4. rachas de descanso;
5. fines de semana completos;
6. mismo turno durante el fin de semana;
7. patrones no deseados;
8. peticiones de días libres;
9. peticiones de turnos libres.

### Pruebas unitarias

Archivo: `files/test_schedule_evaluator.py`.

Se han añadido cuatro pruebas:

- horario factible ideal;
- detección de habilidad y cobertura incumplidas;
- cálculo de demanda y patrones;
- detección de dimensiones inválidas.

Resultado actual:

```text
4 pruebas ejecutadas correctamente.
```

### MILP-0

Archivo: `files/milp.py`.

La primera versión del modelo utiliza:

\[
x_{n,d,s} \in \{0,1\}
\]

donde la variable vale 1 cuando el enfermero `n` trabaja el turno `s` el día `d`.

El modelo implementa:

- lectura de las instancias JSON;
- poda de variables cuando el enfermero no tiene la habilidad del turno;
- un turno máximo por enfermero y día;
- cobertura mínima cualificada de cada turno y día;
- extracción de la solución en el formato del torneo.

### MILP-1

Sobre el MILP-0 se añadieron variables de desviación para:

- diferencia absoluta entre la asignación y la demanda preferida;
- asignaciones por debajo del mínimo contractual;
- asignaciones por encima del máximo contractual.

El objetivo actual del modelo es:

\[
\min \left(
\text{desviación de demanda}
\;+\;
\text{desviación de asignaciones}
\right)
\]

Las rachas, fines de semana, patrones y peticiones todavía no forman parte del objetivo MILP.

## Validación realizada

### MILP-0 sobre las siete instancias

El MILP-0 generó soluciones factibles en las siete instancias:

| Instancia | Enfermeros | Días | Asignaciones | Violaciones duras |
|---|---:|---:|---:|---:|
| 01 | 49 | 28 | 1372 | 0 |
| 02 | 49 | 28 | 1372 | 0 |
| 03 | 49 | 28 | 1372 | 0 |
| 04 | 49 | 28 | 1372 | 0 |
| 05 | 49 | 28 | 1372 | 0 |
| 06 | 50 | 28 | 1400 | 0 |
| 07 | 50 | 28 | 1400 | 0 |

### MILP-1 sobre las siete instancias

El objetivo oficial del solver coincidió con la suma de las penalizaciones `demand` y `assignments` del evaluador:

| Instancia | Objetivo MILP-1 | Solución factible |
|---|---:|---|
| 01 | 150 | Sí |
| 02 | 160 | Sí |
| 03 | 195 | Sí |
| 04 | 230 | Sí |
| 05 | 211 | Sí |
| 06 | 0 | Sí |
| 07 | 27 | Sí |

Esta coincidencia verifica que la linealización implementada para las dos primeras penalizaciones reproduce el cálculo independiente del evaluador.

## Justificación de las decisiones

### Separación entre restricciones duras y blandas

La factibilidad del proyecto solo depende de:

1. cobertura mínima cualificada;
2. un único turno diario por enfermero.

Las condiciones contractuales y preferencias se modelan como desviaciones porque el enunciado permite horarios factibles que no sean ideales.

### Poda por habilidades

No se crean variables para asignaciones que un enfermero no puede realizar. Esto:

- reduce el tamaño del modelo;
- evita asignaciones imposibles;
- mejora la claridad de la formulación;
- mantiene la habilidad como condición dura.

### Desarrollo incremental

Se ha separado el modelo en fases para poder:

- validar cada familia de restricciones;
- comparar el objetivo del solver con un evaluador independiente;
- localizar errores de linealización;
- explicar cada decisión durante la defensa;
- evitar consumir el límite temporal con un modelo completo no validado.

### Uso de técnicas del curso

La implementación reutiliza los conocimientos de:

- Laboratorio 1: variables, restricciones, objetivos y resolución con OR-Tools.
- Laboratorio 2: medición de tiempos y comparación experimental.
- Laboratorio 3: construcción automatizada de modelos mediante índices, bucles y diccionarios.

## Trabajo pendiente

- Completar MILP-2 con rachas de trabajo y descanso.
- Añadir fines de semana, patrones y peticiones.
- Implementar una solución inicial para `metaheuristic.py`.
- Implementar búsqueda local con movimientos de cambio e intercambio.
- Crear los archivos de experimentos exigidos.
- Comparar contra los baselines.
- Realizar repeticiones, análisis estadístico y estudio de ablación.
- Redactar el informe IEEE definitivo de un máximo de 10 páginas.

## Limitaciones actuales

- El modelo todavía no optimiza las nueve penalizaciones simultáneamente.
- No se han ejecutado experimentos estadísticos.
- No se ha comparado todavía contra los baselines del torneo.
- No se puede concluir aún qué versión obtiene el mejor ranking.

