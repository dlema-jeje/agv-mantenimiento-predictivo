# Verificación de la entrega final

- TensorFlow CPU 2.18.1. Ambas variantes entrenadas y evaluadas con el
  mismo conjunto de validación. Matriz de confusión de prueba generada
  con cuatro clases y 55 ventanas.
- Replay en ROS 2 Humble. El emulador de aceleración, el diagnosticador
  y el verificador ejecutaron quince intercambios completos por tópicos.
- Gazebo Classic 11.10.2. Misión sin GUI, con Waffle, respuesta de la
  dinámica diferencial, odometría, rayos y acople. Se elevó la frecuencia
  objetivo de actualización de la simulación a 3400 Hz con paso de 1 ms.
  La duración de acople se midió con sellos de tiempo de /odom.
- La primera ejecución se interrumpió en el retorno al pasillo. Tras
  ajustar el retorno, otra ejecución se detuvo al girar hacia E4.
  El modelo Waffle final deshabilita la rampa de rueda del plugin en el
  spawn de simulación. La ejecución entregada completó las 15 visitas.
- La traza de odometría se capturó desde t = 11,043 s en el simulador.
  La evidencia JSONL abarca las tres rondas completas.
- Comparación independiente de características con SciPy y NumPy.
  MATLAB no estaba disponible en el entorno. El script de contraste y
  sus cinco ventanas se incluyen junto al código.
- Compilación con colcon y resolución de argumentos de
  ros2 launch agv_avance3 avance3.launch.py verificadas.
- Suite del repositorio: 76 pruebas y 45 subpruebas aprobadas.
