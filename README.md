# AGV para mantenimiento predictivo en una planta industrial

Proyecto de simulación y planificación de rutas de un vehículo
de guiado automático (AGV) para la inspección de cinco estaciones
industriales de bombeo.

## Tecnologías

- Ubuntu 22.04 sobre WSL2
- ROS 2 Humble
- Gazebo Classic
- TurtleBot3 Waffle
- MATLAB
- Python
- Navigation2 (Nav2)

## Objetivos

1. Modelar un entorno industrial de cinco estaciones.
2. Construir un mapa de ocupación bidimensional.
3. Calcular rutas mediante el algoritmo Dijkstra.
4. Exportar distancias y trayectorias en formato CSV.
5. Integrar el mapa industrial con ROS 2 y Nav2.
6. Implementar localización y navegación autónoma.
7. Preparar la inspección para mantenimiento predictivo.

## Estructura

- `mundos/`: escenario industrial de Gazebo.
- `urdf/`: modelo del robot.
- `matlab/`: mapas, planificación y validación.
- `datos/`: matriz de distancias, objetivos y rutas.
- `mapas/`: archivos PGM y YAML para Nav2.
- `scripts/`: automatización y verificaciones ROS 2.

## Estado del proyecto

- Mapa industrial desarrollado.
- Cinco estaciones y puntos de aproximación definidos.
- Algoritmo Dijkstra implementado en MATLAB.
- Treinta rutas exportadas y verificadas.
- Mapa cargado mediante el servidor de mapas de Nav2.
- Localización AMCL pendiente.
- Navegación autónoma validada en una misión de cinco estaciones mediante Nav2.

## Autor

Proyecto académico de simulación de un AGV industrial.

## Resultados del Avance 1

### Planificación y navegación

- Mapa industrial de cinco estaciones.
- Planificación de rutas mediante Dijkstra.
- Tres escenarios de priorización comprobados.
- Misión de cinco estaciones completada con resultado SUCCEEDED.
- Evidencia: `resultados/avance1/navegacion/inspecciones.csv`.

El retorno automático a la base no quedó validado.

### Ejecutar la priorización

Desde la raíz del proyecto:

    python3 scripts/priorizador_agv.py --caso 1
    python3 scripts/priorizador_agv.py --caso 2
    python3 scripts/priorizador_agv.py --caso 3

Para validar la misión sin mover el robot:

    python3 scripts/priorizador_agv.py --caso 1
    python3 scripts/ejecutar_mision_priorizada.py

Para ejecutar la navegación, primero deben estar activos
Gazebo, Nav2, AMCL y el servidor de mapas:

    python3 scripts/ejecutar_mision_priorizada.py --ejecutar

### Análisis de vibraciones CWRU

Se analizaron cuatro condiciones:

- Normal: 97.mat
- Pista interna: 105.mat
- Bola: 118.mat
- Pista externa: 130.mat

Se calcularon FFT, RMS, pico, factor de cresta y curtosis.
La señal normal se remuestreó de 48 kHz a 12 kHz.

Scripts: `matlab/cwru/`

Resultados: `resultados/avance1/vibraciones/`

Los datos experimentales `.mat` se mantienen localmente.
Pueden obtenerse del CWRU Bearing Data Center.

Los scripts MATLAB contienen rutas del entorno Windows/WSL
utilizado en el desarrollo, que deben adaptarse en otros equipos.

### Limitaciones

- La navegación fue validada en simulación Gazebo.
- El retorno automático a la base queda pendiente.
- Los registros CWRU no fueron medidos físicamente por el AGV.
- No se ha implementado todavía un clasificador automático de fallas.
