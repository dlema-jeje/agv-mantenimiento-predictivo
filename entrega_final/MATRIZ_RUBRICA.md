# Matriz de verificación · Avance 3

| Fase | Petición | Comprobación | Resultado |
| --- | --- | --- | --- |
| 1 | 6–9 características y arquitectura prescrita | Configuración del archivo Keras y auditoría de formas de los pesos | 9 entradas, Dense 32 ReLU, Dropout 0,20, Dense 16 ReLU, Dense 4 Softmax |
| 1 | MLP frente a CNN 1D | Fase 1 del informe | La MLP utiliza descriptores. Una CNN puede aprender transitorios en la señal cruda si hay registros y cómputo suficientes. |
| 1 | Curtosis, cresta y desbalance | Fase 1 del informe | Impactos aumentan pico y colas. Una sinusoide tiene curtosis 1,5 y cresta √2 sin depender de su amplitud. |
| 1 | Red pequeña para ESP32 | Auditoría de pesos | 916 parámetros y 3664 bytes de pesos float32. FFT, búfer y latencia se evalúan en la Unidad 4. |
| 2 | Adam, tasa, pérdida y parada temprana | Fuente, archivo Keras e historiales | Adam 0,001, entropía categórica y parada por pérdida de validación desde época 50 con paciencia 12. Ambas redes alcanzaron 100. |
| 2 | Curvas y comparación de arquitecturas | Reentrenamiento separado, dos historiales y curvas | Validación 89,09 % y 0,20106 para 32. Validación 98,18 % y 0,09864 para 32–16. Se eligió la de menor pérdida. |
| 3 | Exactitud, matriz 4 × 4, precisión y recall | Auditor recalcula predicciones a partir de las 55 ventanas originales de prueba | 100 %. Diagonal 7,16,16,16. Precisión y recall 1,00 para cada clase. Sin cruces en la prueba. |
| 3 | Acelerómetro simulado, diagnóstico y prioridad | Tópicos y replay de ROS 2 asociados por ID | 15/15 mensajes y cambios de primer destino E3 → E2 → E5. |
| 3 | Contraste MATLAB–Python, cinco ventanas | CSV fijados, script MATLAB y chequeo del CSV de salida desde Python | MATLAB pendiente por disponibilidad del motor. La referencia SciPy dio diferencia máxima de 1,22 × 10⁻¹³ %. |
| 3 | Tres rondas con estado cambiante | Corrida repetida en Gazebo con el código revisado, comprobada con validar_gazebo.py | 15 visitas y 3 reintentos. E2 pasa a encabezar la ronda 2 y E5 la ronda 3. |
| 3 | Acople ≥ 90 % en escenarios 1 a 3 | 15 intentos independientes en Gazebo. Un intento por fila. | 15/15, con 5/5 por escenario. |
| Entrega | Tag, informe, video y defensa | Bundle, PDF, MP4, guía de compilación y DEFENSA.md | Etiqueta local final, informe de 8 páginas, video narrado de 150 s. |

La tasa por escenario se calcula con ensayos independientes y denominador
fijo de cinco por caso. Los reintentos de la misión y su tasa por visita
se informan por separado. El 100 % de diagnóstico está limitado a tramos
temporales de los cuatro registros CWRU elegidos.

Para ejecutar las comprobaciones y guardar una nueva evidencia, consultar
[Compilación y video](COMPILACION_Y_VIDEO.md).
