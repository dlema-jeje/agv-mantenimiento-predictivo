#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=waffle
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$ROOT/scripts/generar_mundo.py"
ros2 launch gazebo_ros gazebo.launch.py world:="$ROOT/mundos/planta_bombeo_agv.world"
