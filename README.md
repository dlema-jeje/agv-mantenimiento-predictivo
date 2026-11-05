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
- Navegación autónoma pendiente de validación.

## Autor

Proyecto académico de simulación de un AGV industrial.
