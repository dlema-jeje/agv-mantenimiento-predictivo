# MEC451 | Avance 3 — MLP de diagnóstico e integración
\n[Guía por fases, compilación y video](COMPILACION_Y_VIDEO.md).

Continuación de la rama `avance2-desarrollo` en el commit `d0fc301`.
Se conservan el mundo de cinco máquinas, los objetivos del tablero, la matriz
de distancias exportada y la lógica de prioridad. Para la misión final se agregó
un seguidor de pasillo con odometría, limitado a este mundo. La rama anterior
documenta limitaciones de Nav2/DWB en el preacople. El launch final usa su
propio recorrido en Gazebo y conserva el bloqueo de los scripts anteriores.

## Resultados registrados

- CWRU 0 hp, cuatro clases, 395 ventanas. División por registro de 70/15/15
  antes del remuestreo por tramo y del ventaneo. `datos/final/fuentes.json`
  identifica las fuentes originales, tasas y SHA-256.
- Variante de una capa, 452 parámetros, exactitud de validación 89,09 %.
  Variante 32–16, 916 parámetros, exactitud 98,18 % en validación.
  Selección por menor pérdida de validación (0,09864 frente a 0,20106).
- Prueba: 55/55, con 7 normal y 16 de cada falla. Las particiones proceden
  de los mismos cuatro registros, con muestras disjuntas. El resultado
  describe esos registros.
- Equivalencia NumPy–Keras: diferencia absoluta máxima 1,19 × 10⁻⁷ en
  las probabilidades de prueba. Comparación Python–SciPy en 45 valores:
  diferencia relativa máxima 1,22 × 10⁻¹³ %. La ejecución en MATLAB
  se puede reproducir con el script indicado abajo.
- Replay ROS 2 Humble: 15 diagnósticos por tópicos y primer destino E3 → E2 → E5
  entre rondas. El replay inyecta el disparo de acople y comprueba diagnóstico
  y ruta sin física. El registro `ros2_replay.json` contiene la evidencia.
- Gazebo Classic 11.10.2 sin GUI: 3 rondas, 15 acoples confirmados y primer
  destino E3 → E2 → E5. Máximos absolutos 6,55 mm longitudinal y 4,76° angular.
  Tiempo medio del intento exitoso 17,94 s en reloj simulado y 5 reintentos.
  Registro: gazebo_rondas_verificado.jsonl, resumen y trayectoria en resultados/final.

La misión se repitió tras el ajuste de preacople. Registró 15 visitas y 3
reintentos con error máximo de 8,84 mm y 4,84°. Consultar
resultados/final/gazebo_rondas_revision.jsonl y gazebo_revision_resumen.json.

## Ejecutar

En Ubuntu 22.04 con ROS 2 Humble y Gazebo Classic instalado:

```bash
source /opt/ros/humble/setup.bash
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-turtlebot3-gazebo python3-venv
python3 -m venv --system-site-packages .venv-final
source .venv-final/bin/activate
python -m pip install 'numpy<2' scipy scikit-fuzzy
export ROS_DOMAIN_ID=45
export ROS_LOCALHOST_ONLY=1
ros2 launch launch/avance3.launch.py registro:=resultados/final/gazebo_rondas.jsonl
```

Ejecutar desde la raíz del repositorio. El dominio debe estar libre en el equipo.
Para servidor sin GUI, agregar `gui:=false`. Usar una ruta de registro nueva
en cada corrida. El inspector final registra planes y visitas, pose relativa,
tiempo de acople, reintentos, clase y confianza, además de causas de interrupción.
El launch se cierra cuando termina el inspector.

El Waffle sale de Base y usa el pasillo x ≈ 0,50 m para los cambios de estación.
A x ≈ 0,76 m, verifica orientación y centro usando odometría. Luego aplica
el Mamdani calibrado con rangos filtrados y dispara una ventana al confirmar
±1 cm y ±5° durante un segundo. A partir de los diagnósticos anteriores se
priorizan las fallas. E2 presenta pista interna en ronda 1 y vuelve a normal
en ronda 2. E5 presenta falla de bola en ronda 2 y pista externa en ronda 3.
Una falla nueva solo se conoce al medir la estación correspondiente.

El spawn ajusta a 0 la rampa de rueda del plugin de Gazebo del Waffle. En las
pruebas de integración, la rampa original retrasó los giros y agotó el tiempo
de navegación. La variante final conserva el modelo y el control diferencial,
con límites de consigna en el inspector. Se aceleró el reloj de Gazebo para
validar en modo sin GUI, con paso de física de 1 ms y tiempos de acople medidos
en el reloj simulado de /odom. Para auditar el resultado archivado:

    python scripts/final/validar_gazebo.py resultados/final/gazebo_rondas_verificado.jsonl

### Repetir el replay ROS 2

Con el entorno activado y el mismo dominio en tres terminales:

```bash
python scripts/final/nodos.py acelerometro
python scripts/final/nodos.py diagnosticador
python scripts/final/verificar.py --ros
```

### Reentrenar y auditar

En un entorno Python de entrenamiento con 3.10 a 3.12:

```bash
python -m pip install -r scripts/final/requirements.txt
python scripts/final/entrenar.py
python scripts/final/verificar.py --keras
```

El script descarga los cuatro archivos originales si faltan. También admite
`--origen /ruta/a/los/mat` para reutilizar los CWRU existentes y vuelve a generar
pesos, CSV, banco de prueba y gráficas. En MATLAB, desde la raíz:

```matlab
addpath('matlab/final')
verificar_caracteristicas
```

El CSV de contraste usa las cinco mismas ventanas y nueve características
en el orden del modelo. La meta es <0,1 % por valor. El script escribe los
resultados MATLAB y falla si alguna característica excede la tolerancia.

## Archivos

- `modelos/diagnostico.keras`: modelo entrenado. Usar media/escala de
  `diagnostico.npz` antes de inferir con Keras.
- `modelos/diagnostico.npz`: pesos y escalador usados por ROS 2.
- `datos/final/`: auditoría de particiones, ventanas de prueba y de paridad.
- `resultados/final/`: curvas, matriz de confusión, métricas y replay.
- `entrega_final/`: informe, fuente del informe y guía de defensa.
- `firmware/`: alcance futuro de la Unidad 4.

La guía de defensa identifica las demostraciones verificadas y el contraste MATLAB pendiente. El video acompaña el paquete de entrega.

### Lanzamiento como paquete ROS 2

Desde la raíz, con ROS Humble y el entorno final activos:

```bash
colcon build --base-paths ros2_ws/src
source install/setup.bash
ros2 launch agv_avance3 avance3.launch.py registro:=resultados/final/gazebo_rondas.jsonl
```

El informe usa nueve referencias técnicas y deja el campo de integrantes
editable en `informe.tex`. La lista oficial de bibliografía de la asignatura
no estaba incluida para cotejar cuáles referencias cuentan como bibliografía
del curso.

### Abrir el repositorio desde el bundle

El paquete ZIP se puede descomprimir para consultar el código. Para conservar
historial y etiquetas, clonar el bundle desde la carpeta de descargas:

```bash
git clone -b avance3-final Repositorio_Avance_3.bundle agv-avance3
cd agv-avance3
git show --no-patch final
```

Para editar integrantes y regenerar el informe en un entorno con IEEEtran,
ejecutar dos veces `pdflatex informe.tex` desde `entrega_final/`.
