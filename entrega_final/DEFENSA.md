# Guía de defensa oral · MEC451 U3S7

La versión para presentar está en la rama [avance3-final](https://github.com/dlema-jeje/agv-mantenimiento-predictivo/tree/avance3-final).
En WSL, la raíz es /home/diego/agv-avance3-video y esta guía queda en
/home/diego/agv-avance3-video/entrega_final/DEFENSA.md.
En Windows, la carpeta de entrega es
\\wsl.localhost\Ubuntu-22.04\home\diego\agv-avance3-video\entrega_final.

## 1. Preparar y abrir los archivos

En Ubuntu WSL:

    cd "$HOME/agv-avance3-video" &&
    git pull --ff-only origin avance3-final &&
    git rev-parse --short HEAD &&
    ls -l entrega_final/{DEFENSA.md,Informe_IEEE_Avance_3.pdf,Video_Avance_3.mp4} &&
    explorer.exe "$(wslpath -w "$PWD/entrega_final")"

Para consultar la guía sin salir de WSL, ejecutar:

    less entrega_final/DEFENSA.md

## 2. Orden de la exposición y evidencia de cada punto

Las rutas de la segunda columna parten de la raíz local. Sus enlaces abren
el archivo equivalente en GitHub.

| Qué mostrar | Archivo en GitHub y ruta relativa en WSL | Qué explicar |
| --- | --- | --- |
| Informe y rúbrica | [entrega_final/Informe_IEEE_Avance_3.pdf](Informe_IEEE_Avance_3.pdf) y [entrega_final/MATRIZ_RUBRICA.md](MATRIZ_RUBRICA.md) | El AGV inspecciona por prioridad, se acopla, diagnostica y reordena las próximas visitas. |
| Diseño de la MLP | [scripts/final/entrenar.py](../scripts/final/entrenar.py) y [resultados/final/auditoria_rubrica.json](../resultados/final/auditoria_rubrica.json) | Nueve entradas, dos capas ocultas de 32 y 16, ReLU, Dropout 0,20 y cuatro salidas Softmax. 916 parámetros. |
| Entrenamiento y selección | [resultados/final/curvas.png](../resultados/final/curvas.png) y [resultados/final/resumen.json](../resultados/final/resumen.json) | Adam 0,001, entropía categórica y parada por pérdida de validación. Dos capas lograron 98,18 % frente a 89,09 % de una capa. |
| Prueba del diagnóstico | [resultados/final/confusion.png](../resultados/final/confusion.png) y [resultados/final/metricas.csv](../resultados/final/metricas.csv) | 55/55 aciertos, precisión y recall de 1,00 en cada clase. Se usaron tramos disjuntos de cuatro registros CWRU a 0 hp. |
| MATLAB frente a Python | [matlab/final/verificar_caracteristicas.m](../matlab/final/verificar_caracteristicas.m) y [datos/final/paridad_ventanas.csv](../datos/final/paridad_ventanas.csv) | Cinco ventanas y nueve características por ventana. Límite de 0,1 % por valor. El CSV de salida se genera en tu equipo. |
| Acople independiente | [resultados/final/acople_rangos_pareados.jsonl](../resultados/final/acople_rangos_pareados.jsonl) | 5/5 frontal, 5/5 con 15° y 5/5 con error residual de 3 cm y 10°. Son 15 intentos independientes. |
| Misión y prioridad | [resultados/final/gazebo_wsl_gui_resumen.json](../resultados/final/gazebo_wsl_gui_resumen.json) y [resultados/final/gazebo_video_rangos_pareados.jsonl](../resultados/final/gazebo_video_rangos_pareados.jsonl) | Tu corrida en WSL completó tres rondas y 15 visitas, cero reintentos, 134,994 s y primeros destinos E3 → E2 → E5. El JSONL enlazado corresponde a la prueba autónoma con rangos sincronizados. |
| Video | [entrega_final/Video_Avance_3.mp4](Video_Avance_3.mp4) | El video narrado dura 150 s. Si presentas tu captura de Gazebo, verifica también su duración antes de entregar. |

Para abrir las gráficas y comprobar la duración del video desde WSL:

    cd "$HOME/agv-avance3-video"
    explorer.exe "$(wslpath -w "$PWD/resultados/final")"
    ffprobe -v error -show_entries format=duration -of default=nw=1 \
      entrega_final/Video_Avance_3.mp4

## 3. Reproducir y guardar la prueba MATLAB–Python

En **Command Window de MATLAB para Windows**, donde aparece el prompt >>:

    cd('\\wsl.localhost\Ubuntu-22.04\home\diego\agv-avance3-video')
    addpath(fullfile(pwd, 'matlab', 'final'))
    verificar_caracteristicas

Los tres CSV se guardan en resultados/final de la misma carpeta. Abre
paridad_matlab_detalle.csv para mostrar los 45 valores, paridad_matlab.csv
para auditar las salidas de MATLAB y paridad_error_matlab_pct.csv para mostrar
la matriz de errores. La corrida de MATLAB reportó 6,07789650264 × 10⁻¹³ %
como máximo. La relectura del CSV en Python reportó 5,904242316845438 × 10⁻¹³ %.
Ambas comprobaciones cumplen 0,1 %. Los CSV que generaste se conservan localmente.

En **Ubuntu WSL**:

    cd "$HOME/agv-avance3-video" &&
    source "$HOME/agv-mantenimiento-predictivo-final/.venv-final/bin/activate" &&
    export PYTHONNOUSERSITE=1 &&
    test -s resultados/final/paridad_matlab.csv &&
    mkdir -p resultados/reproduccion &&
    set -o pipefail &&
    python3 scripts/final/auditar_final.py --matlab resultados/final/paridad_matlab.csv \
      | tee resultados/reproduccion/auditoria_defensa.json

Revisa paridad_csv_motor_externo_pct en el JSON. Las métricas de
gazebo_rondas_archivadas corresponden a otro registro histórico.

## 4. Validar el acople y mostrar la simulación

Con el entorno anterior activado, las comprobaciones de evidencias publicadas
se ejecutan desde la raíz:

    python3 scripts/final/validar_ensayos.py resultados/final/acople_rangos_pareados.jsonl
    python3 scripts/final/validar_gazebo.py resultados/final/gazebo_video_rangos_pareados.jsonl

Para una demostración en vivo, abre una terminal WSL nueva:

    cd "$HOME/agv-avance3-video" &&
    source /opt/ros/humble/setup.bash &&
    source "$HOME/agv-mantenimiento-predictivo-final/.venv-final/bin/activate" &&
    export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=45 ROS_LOCALHOST_ONLY=1 &&
    colcon build --base-paths ros2_ws/src --packages-select agv_avance3 &&
    source install/setup.bash

Con la compilación terminada, inicia OBS si vas a grabar y ejecuta:

    mkdir -p resultados/reproduccion
    RONDA="resultados/reproduccion/defensa_$(date +%Y%m%d_%H%M%S).jsonl"
    time ros2 launch agv_avance3 avance3.launch.py gui:=true video:=true registro:="$RONDA"
    python3 scripts/final/validar_gazebo.py "$RONDA"

Para ver los mensajes en vivo, ejecuta cada comando echo en una terminal
distinta, con ROS Humble cargado y el mismo dominio:

    source /opt/ros/humble/setup.bash
    export ROS_DOMAIN_ID=45 ROS_LOCALHOST_ONLY=1
    ros2 topic echo /diagnostico
    # En otra terminal con la misma preparación:
    ros2 topic echo /ruta_priorizada

## 5. Preguntas para preparar

| Pregunta | Respuesta |
| --- | --- |
| ¿Por qué E2 y E5 pasan a encabezar rondas diferentes? | E2 presenta falla de pista interna en la primera ronda y E5 falla de bola en la segunda. Una falla detectada eleva la prioridad de la próxima visita a esa máquina. |
| ¿Qué impide tomar una muestra antes de acoplar? | El supervisor exige tolerancias longitudinal y angular sostenidas durante un segundo antes de emitir el evento de adquisición. |
| ¿Por qué basta una MLP en este caso? | Las características condensan la información de la ventana. Una CNN 1D puede aprender transitorios directamente de la señal si hay suficientes registros y recursos. |
| ¿Qué alcance tiene el 100 %? | Corresponde a 55 ventanas de prueba de tramos disjuntos del conjunto CWRU seleccionado. Evaluar otros motores y cargas requiere datos adicionales. |
| ¿Qué significa que MATLAB pase la paridad? | Sus convenciones y las de Python coinciden para esta implementación en los 45 valores contrastados. |

Para instalar dependencias, reentrenar, recompilar el PDF o exportar una
captura de OBS, consulta [COMPILACION_Y_VIDEO.md](COMPILACION_Y_VIDEO.md).
Antes de entregar, coteja dos referencias del informe con la bibliografía
oficial de la asignatura.
