# Resumen de validación — Avance 2

## Resultados comprobados

- Pruebas unitarias: 7 de 7 aprobadas.
- Pruebas de seguridad de integración: 8 de 8 aprobadas.
- Adaptador de acoplamiento seguro: 7 de 7 comprobaciones aprobadas.
- Máquina de estados: comprobaciones aisladas aprobadas.
- Árbitro de velocidades: inspección estática aprobada.
- Dependencias ROS 2 Humble: disponibles.
- Compilación Python del árbitro: correcta.

## Seguridad

- El árbitro permanece bloqueado en STOP.
- La publicación de movimiento Mamdani permanece deshabilitada.
- No se enviaron objetivos Nav2 durante las pruebas finales.
- No se ordenó movimiento al robot.

## Limitaciones pendientes

- No se validó el acoplamiento mediante movimiento en Gazebo.
- No se confirmó experimentalmente el signo angular sensorial.
- No se completó la comparación real MATLAB-Python.
- No se completó la integración predictiva ROS 2.
- Los ensayos numéricos no equivalen a ensayos físicos ni a pruebas dinámicas en Gazebo.

## Conclusión

El Avance 2 cuenta con validación unitaria, lógica y estática
de los componentes revisados. La integración dinámica y el
acoplamiento experimental permanecen pendientes.

El sistema no está autorizado para movimiento autónomo.
