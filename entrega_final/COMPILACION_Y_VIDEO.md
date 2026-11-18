# Avance 3 · Compilación, auditoría y video final

Ejecutar en Ubuntu 22.04 con Bash y ROS 2 Humble. Para grabar con la GUI, usar
una sesión gráfica. Desde el ZIP, entrar en la carpeta extraída. Desde el
bundle Git, ejecutar:

    git clone -b avance3-final Repositorio_Avance_3.bundle agv-avance3
    cd agv-avance3
    git show --no-patch --oneline final

Todos los siguientes bloques parten de la raíz del repositorio, salvo donde se indica otra carpeta.

## Fase 1 · Arquitectura y auditoría del modelo

    python3 -m venv .venv-ml
    source .venv-ml/bin/activate
    python -m pip install -r scripts/final/requirements.txt
    python scripts/final/auditar_final.py

El auditor lee el archivo Keras y comprueba la estructura 9–32–16–4,
ReLU, Dropout 0,20, Softmax, Adam y la pérdida categórica. Cuenta 916
parámetros, equivalentes a 3664 bytes de pesos y sesgos en float32.
La RAM de inferencia y de FFT en ESP32 requiere medición en la Unidad 4.

## Fase 2 · Entrenamiento, curvas y evaluación

    source .venv-ml/bin/activate
    mkdir -p resultados/reproduccion
    set -o pipefail
    TF_NUM_INTRAOP_THREADS=1 TF_NUM_INTEROP_THREADS=1 \
      python scripts/final/entrenar.py | tee resultados/reproduccion/entrenamiento.log
    python scripts/final/verificar.py --keras
    python scripts/final/auditar_final.py | tee resultados/reproduccion/auditoria.json
    cat resultados/final/resumen.json
    cat resultados/final/confusion.csv
    cat resultados/final/metricas.csv

Para usar archivos locales, añadir el argumento --origen /ruta/a/cwru
a entrenar.py. Se esperan 97.mat, 105.mat, 118.mat y 130.mat. Si faltan,
el entrenamiento intenta descargarlos del repositorio oficial. Para conservar
las evidencias originales al reentrenar, trabajar sobre una copia del proyecto.
Las curvas y las tablas se escriben en resultados/final. El diagnóstico del
ajuste debe considerar la misma carga y origen de los registros.

## Fase 3A · Contraste de las mismas cinco ventanas

    source .venv-ml/bin/activate
    python scripts/final/verificar.py
    matlab -batch "addpath('matlab/final'); verificar_caracteristicas"
    python scripts/final/auditar_final.py \
      --matlab resultados/final/paridad_matlab.csv

El segundo comando requiere MATLAB instalado y activado. Genera
paridad_matlab.csv y paridad_error_matlab_pct.csv. La comparación exige
menos de 0,1 % en cada uno de los 45 valores. La evidencia SciPy de referencia
se identifica por separado. Si MATLAB solo existe en Windows, abrir el proyecto
en MATLAB, ubicarse en la raíz y ejecutar:

    addpath('matlab/final')
    verificar_caracteristicas

## Fase 3B · Compilar y ejecutar ROS 2 y Gazebo

En una terminal nueva para no mezclar los entornos de entrenamiento y ROS:

    source /opt/ros/humble/setup.bash
    sudo apt update
    sudo apt install ros-humble-gazebo-ros-pkgs \
      ros-humble-turtlebot3-gazebo python3-venv \
      python3-colcon-common-extensions ffmpeg x11-utils texlive-publishers latexmk
    python3 -m venv --system-site-packages .venv-final
    source .venv-final/bin/activate
    python -m pip install 'numpy<2' scipy scikit-fuzzy
    export ROS_DOMAIN_ID=45 ROS_LOCALHOST_ONLY=1
    colcon build --base-paths ros2_ws/src --packages-select agv_avance3
    source install/setup.bash
    ros2 launch agv_avance3 avance3.launch.py --show-args

### Ensayos independientes de la rúbrica

    mkdir -p resultados/reproduccion
    ENSAYOS="resultados/reproduccion/acople_$(date +%Y%m%d_%H%M%S).jsonl"
    ros2 launch agv_avance3 avance3.launch.py \
      gui:=false ensayos:=true registro:="$ENSAYOS"
    python scripts/final/validar_ensayos.py "$ENSAYOS"

Son quince intentos en Gazebo en E1, cinco por configuración, sin reintentos.
Se exige 14/15 para superar el 90 %. Registrar por separado los resultados
de cada escenario y los reintentos de la misión. La corrida archivada obtuvo
5/5 frontal, 5/5 a 15° y 5/5 con error residual. Los archivos de auditoría están
en resultados/final/acople_escenarios_1_3.jsonl y acople_escenarios_resumen.json. El escenario 4 de perturbación
del Avance 2 queda fuera del mínimo de los escenarios 1 a 3 solicitado aquí.

### Misión completa, lista para grabar

    set -o pipefail
    mkdir -p resultados/reproduccion
    RONDA="resultados/reproduccion/rondas_$(date +%Y%m%d_%H%M%S).jsonl"
    printf '%s\n' "$RONDA" > resultados/reproduccion/ultima_mision.txt
    ros2 launch agv_avance3 avance3.launch.py \
      gui:=true registro:="$RONDA" 2>&1 | tee "$RONDA.log"
    python scripts/final/validar_gazebo.py "$RONDA"

En otra terminal, preparar los monitores antes de iniciar la misión:

    source /opt/ros/humble/setup.bash
    export ROS_DOMAIN_ID=45 ROS_LOCALHOST_ONLY=1
    ros2 topic list
    ros2 topic echo /diagnostico
    # En otra terminal con el mismo dominio:
    ros2 topic echo /ruta_priorizada
    # Durante la misión, en otra terminal:
    ros2 topic info /acelerometro_sim/ventana --verbose

Conviene mostrar los tópicos de diagnóstico y ruta junto a la GUI.
Si no hay sesión gráfica, gui:=false permite repetir la auditoría de la misión.
El JSONL del programa es el registro para calificación.

## Fase 3C · Grabar y exportar el MP4

Iniciar la captura antes del launch con GUI. En Ubuntu con X11:

    mkdir -p resultados/reproduccion
    printf '%s\n' "$DISPLAY"
    xdpyinfo | awk '/dimensions:/{print $2; exit}'
    TAMANO="$(xdpyinfo | awk '/dimensions:/{print $2; exit}')"
    ffmpeg -f x11grab -framerate 20 -video_size "$TAMANO" \
      -i "$DISPLAY" -c:v libx264 -preset ultrafast \
      -crf 23 -pix_fmt yuv420p resultados/reproduccion/gazebo_bruto.mkv

Detener con q en la terminal de captura. Bajo Wayland, usar OBS con captura
de pantalla PipeWire. En WSL, usar OBS de Windows y capturar el escritorio
que muestra Gazebo. Guardar o copiar el resultado como
resultados/reproduccion/gazebo_bruto.mkv. Para narrar, grabar el micrófono desde
OBS o añadir una pista aparte durante la edición.

Verificar la grabación y generar un borrador acelerado. Revisar los cortes
antes de entregar, para conservar los tres cambios de ronda:

    ffprobe -v error -show_entries format=duration \
      -of default=nw=1 resultados/reproduccion/gazebo_bruto.mkv
    bash entrega_final/exportar_video.sh \
      resultados/reproduccion/gazebo_bruto.mkv \
      resultados/reproduccion/Video_Final_Simulacion.mp4
    ffplay resultados/reproduccion/Video_Final_Simulacion.mp4

Guion sugerido de 170 s para la edición final:

| Tiempo | Mostrar |
| --- | --- |
| 00:00–00:25 | Arquitectura, clases CWRU y parámetros |
| 00:25–00:50 | Curvas y matriz de confusión |
| 00:50–01:20 | Gazebo, navegación y acople, salida de /diagnostico |
| 01:20–02:20 | Las tres rondas y los comienzos E3, E2 y E5 |
| 02:20–02:50 | Auditoría del JSONL, tolerancias y contraste de características |

El exportador produce una versión acelerada de la captura sin audio.
Si se añade narración con OBS o un editor, comprobar que el nuevo MP4
mantiene una duración máxima de 180 s. El video narrado que acompaña el
paquete muestra las evidencias y la trayectoria registrada en Gazebo.

## Informe IEEE y defensa

    cd entrega_final
    latexmk -pdf -halt-on-error informe.tex
    pdfinfo informe.pdf

Completar los integrantes en informe.tex. DEFENSA.md contiene preguntas
y resultados para la exposición. Consultar referencias de la asignatura
para identificar cuáles cuentan como parte de la bibliografía oficial.
