# Informe técnico de estado — Avance 2

**Proyecto:** AGV TurtleBot3 Waffle con mantenimiento predictivo
y acoplamiento supervisado

**Fecha de generación:** 2026-11-10

## 1. Alcance

Este informe consolida resultados existentes del proyecto.
No constituye certificación de seguridad ni validación
experimental completa en Gazebo o en un robot físico.

## 2. Control de acoplamiento

### Modelo numérico original

- Ensayos registrados: 20
- Estados observados: {'DIVERGENCIA_ANGULAR': 20}

### Modelo numérico rediseñado

- Ensayos registrados: 20
- Acoplamientos numéricos: 15
- Tasa de éxito numérica: 75.0 %
- Estados observados: {'ACOPLE_NUMERICO': 15, 'TIEMPO_AGOTADO': 5}

Los resultados corresponden a un modelo numérico.
No deben interpretarse como ensayos de Gazebo.

### Ensayos Gazebo

- Ensayos planificados: 20
- Estados observados: {'NO_EJECUTADO': 20}

Los ensayos de Gazebo permanecen pendientes.

## 3. Seguridad e integración

La revisión estática identificó:

- Umbral de seguridad LiDAR frontal de 0.30 m.
- Distancia objetivo predeterminada del nodo de
  acoplamiento: 0.0 m.
- Conflicto potencial entre ambos valores para una
  pared frontal plana ideal.
- Ausencia de un modelo local explícito de estación
  de acoplamiento en las rutas examinadas.
- Ejecución de movimiento del nodo de acoplamiento
  bloqueada en la configuración revisada.
- Autorización de navegación y preacoplamiento
  todavía no confirmada.

No se modificaron las barreras de seguridad durante
la auditoría.

## 4. Mantenimiento predictivo

- Dataset: CWRU
- Modelo: MLPClassifier de scikit-learn.
- Ventanas de entrenamiento:
  285
- Ventanas de validación:
  55
- Ventanas de prueba:
  55
- Accuracy de validación:
  89.09 %
- Accuracy de prueba:
  100.00 %

Las señales originales se dividen temporalmente
en 70/15/15 antes de generar ventanas.

La evaluación no equivale a una prueba con grabaciones
independientes ni demuestra generalización al AGV real.

El modelo entrenado se encuentra en:
`entrega_avance2/neuronal/modelo_adelanto.joblib`.

La integración final con TensorFlow/Keras y ROS2
no está acreditada por estas evidencias.

## 5. Pendientes críticos

1. Definir y verificar la geometría de la estación.
2. Resolver la coherencia entre distancia objetivo,
   LiDAR, geometría y supervisor de seguridad.
3. Validar el acoplamiento en Gazebo con autorización
   explícita y protocolo seguro.
4. Completar los 20 ensayos Gazebo.
5. Evaluar el clasificador con grabaciones independientes.
6. Verificar los requisitos de integración neuronal
   y mantenimiento predictivo.

## 6. Conclusión

El Avance 2 dispone de implementación de control difuso,
resultados de simulación numérica y un clasificador
predictivo entrenado con resultados registrados.

La validación de acoplamiento en Gazebo y la integración
final del mantenimiento predictivo siguen pendientes.

**Estado técnico: prototipo parcialmente validado.**


## Validación de integración de seguridad

Se ejecutó una prueba local de integración de seguridad utilizando
estados Nav2 y condiciones de parada simulados, sin iniciar nodos ROS2
ni solicitar movimiento del AGV.

- Escenarios evaluados: 8.
- Escenarios aprobados: 8.
- Escenarios fallidos: 0.
- Evidencia: `experimentos/pruebas_seguridad_mision.csv`.
- Casos cubiertos: finalización Nav2 con parada, cancelación confirmada
  y no confirmada, navegación abortada, robot en movimiento, odometría
  obsoleta, STOP no confirmado y estado desconocido.

**Alcance:** estos resultados validan decisiones de software bajo
entradas simuladas. No demuestran seguridad física, funcionamiento
integrado en Gazebo ni acoplamiento real.

**Pendiente:** ejecutar y documentar los 20 ensayos Gazebo previstos.
La distancia de 0.25 m sigue siendo una hipótesis numérica y no un
objetivo operativo autorizado. Se conserva el umbral STOP LiDAR de
0.30 m y permanecen activos los bloqueos de movimiento.
