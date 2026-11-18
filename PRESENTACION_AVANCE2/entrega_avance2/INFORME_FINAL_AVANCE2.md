# MEC451 — Proyecto 4 — Avance 2
## Controlador difuso de acoplamiento y adelanto neuronal

### 1. Objetivo

Diseñar e implementar un controlador difuso Mamdani para el
acoplamiento de un AGV TurtleBot3 Waffle, integrado con ROS 2,
Nav2 y un supervisor de seguridad.

### 2. Diseño del controlador difuso

El controlador emplea dos entradas:

- Error de distancia ed: [-0.05, 0.45] m.
- Error angular eθ: [-20, 20] grados.

Y dos salidas:

- Velocidad lineal v: [-0.05, 0.15] m/s.
- Velocidad angular ω: [-0.8, 0.8] rad/s.

Cada variable dispone de cinco conjuntos difusos.

El sistema utiliza inferencia Mamdani, operadores mínimo y máximo,
agregación máximo y desfusificación por centroide.

La base contiene 25 reglas, correspondientes a una matriz de 5 × 5.

El conjunto Acoplado se concentra alrededor de ed = 0.
El conjunto Cero angular se concentra alrededor de eθ = 0.

La aceptación final del acoplamiento exige verificar explícitamente
las tolerancias de ±0.01 m y ±5 grados durante 1 segundo.
Las funciones de pertenencia no sustituyen esta comprobación.

Archivos de diseño:
- matlab/difuso/acople_agv.fis
- matlab/difuso/acople_agv_calibrado.fis
- matlab/difuso/disenar_controlador_acople.m

### 3. Implementación

Componentes desarrollados:

- Controlador difuso Python.
- Nodo ROS 2 de acoplamiento.
- Supervisor geométrico.
- Cliente Nav2 supervisado.
- Árbitro de velocidades.
- Verificación de parada y resultado Nav2.
- Validación temporal de sensores y estados.
- Evaluador de pose de preacoplamiento.
- Lógica de estados de acoplamiento.

La integración del ciclo completo Nav2 → supervisor → controlador
difuso requiere demostración en Gazebo.

El árbitro de seguridad permanece configurado para aceptar únicamente
STOP. No se declara habilitado el movimiento del AGV.

### 4. Equivalencia MATLAB/Python

La rúbrica exige comparar diez entradas representativas, incluyendo
casos con velocidad angular próxima a cero.

Criterios de aceptación:

- Diferencia absoluta en v inferior a 0.004 m/s.
- Diferencia absoluta en ω inferior a 0.032 rad/s.

Existen scripts y datos de comparación. La equivalencia completa
con resultados ejecutados en MATLAB permanece pendiente de confirmar.

### 5. Evaluación experimental

Se requieren cuatro escenarios con cinco repeticiones cada uno:

1. Aproximación frontal.
2. Desalineación inicial de 15 grados.
3. Error lateral de 0.03 m y angular de 10 grados.
4. Perturbación lateral durante el acoplamiento.

Métricas exigidas:

- Error final de distancia.
- Error final de orientación.
- Tiempo de acoplamiento.
- Oscilaciones y sobrepasos angulares.
- Acoplamientos fallidos.
- Reintentos del supervisor.
- Error lateral final en el escenario 3.

La matriz de 20 ensayos en Gazebo no cuenta todavía con
ejecuciones reales confirmadas.

Los resultados numéricos existentes son preliminares y no se
presentan como ensayos físicos o de Gazebo ejecutados.

Archivos:
- entrega_avance2/experimentos/matriz_20_ensayos.csv
- entrega_avance2/experimentos/resultados_20_ensayos_numericos.csv
- entrega_avance2/experimentos/resultados_20_ensayos_redisenio_numerico.csv
- entrega_avance2/experimentos/comparacion_antes_despues.csv

### 6. Adelanto neuronal

Se dispone de un primer entrenamiento con datos CWRU,
características extraídas y archivos de resultados.

Archivos:
- entrega_avance2/neuronal/entrenar_adelanto.py
- entrega_avance2/neuronal/caracteristicas_cwru.csv
- entrega_avance2/neuronal/modelo_adelanto.joblib
- entrega_avance2/neuronal/resultados_adelanto.json
- entrega_avance2/neuronal/matriz_confusion.csv

Se debe confirmar que el procedimiento cumple la división temporal
70/15/15 antes de segmentar, las ventanas de 2048 muestras con
50 % de solapamiento y el ajuste de StandardScaler exclusivamente
con entrenamiento.

### 7. Estado de entrega

El diseño y los componentes principales de software están disponibles.

No se declara completada la evaluación experimental ni se atribuyen
resultados no ejecutados.

Pendientes principales:
- Cerrar la equivalencia MATLAB/Python.
- Integrar y demostrar el ciclo de acoplamiento completo.
- Ejecutar y registrar los 20 ensayos en Gazebo.
- Documentar el rediseño experimental.
- Confirmar el cumplimiento del protocolo neuronal.
