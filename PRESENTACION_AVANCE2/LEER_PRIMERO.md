# MEC451 — Proyecto 4 — Avance 2

## Contenido entregado
- Diseño de controlador difuso Mamdani en MATLAB.
- Implementación Python y componentes ROS 2.
- Supervisión Nav2, seguridad y recuperación en desarrollo.
- Diez evaluaciones del controlador difuso en Python.
- Matriz de 20 ensayos preparada para Gazebo.
- Entrenamiento neuronal CWRU y métricas obtenidas.

## Resultados verificables
- Controlador difuso: 2 entradas, 2 salidas, 25 reglas.
- CWRU: 574 ventanas; 410 entrenamiento, 82 validación, 82 prueba.
- Exactitud neuronal: 100 % validación y 100 % prueba,
  sin validación de generalización entre grabaciones independientes.

## Limitaciones que deben declararse
- Los 20 ensayos de Gazebo no se han ejecutado.
- La comparación numérica MATLAB/Python no está verificada
  hasta ejecutar el script MATLAB.
- El acoplamiento autónomo completo y la recuperación
  no están demostrados experimentalmente.
- El árbitro permanece en STOP por seguridad.

## Archivos clave
- Informe: entrega_avance2/INFORME_FINAL_AVANCE2.md
- Diseño: matlab/difuso/acople_agv.fis
- Comparación Python: entrega_avance2/comparacion/diez_entradas_python.csv
- Experimentos: entrega_avance2/experimentos/matriz_20_ensayos.csv
- Neuronal: entrega_avance2/neuronal/reporte_final.txt
