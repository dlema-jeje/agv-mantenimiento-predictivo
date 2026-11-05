#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/humble/setup.bash

cd ~/agv_predictivo

URDF="urdf/turtlebot3_waffle.urdf"

if [ ! -f "$URDF" ]; then
    echo "ERROR: No existe el URDF"
    exit 1
fi

if ros2 node list 2>/dev/null | grep -qx '/robot_state_publisher'; then
    echo "robot_state_publisher ya esta activo."
    exit 0
fi

echo "Iniciando transformaciones TF..."

exec ros2 run robot_state_publisher \
robot_state_publisher \
--ros-args \
-p use_sim_time:=true \
-p robot_description:="$(cat "$URDF")"
