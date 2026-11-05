#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=waffle
MODEL="$(ros2 pkg prefix turtlebot3_gazebo)/share/turtlebot3_gazebo/models/turtlebot3_waffle/model.sdf"
if [ ! -f "$MODEL" ]; then echo "No se encuentra $MODEL; localice model.sdf con: find /opt/ros/humble/share -path '*turtlebot3_waffle/model.sdf'"; exit 1; fi
ros2 run gazebo_ros spawn_entity.py -entity agv_waffle -file "$MODEL" -x -1.7 -y 0 -z 0.05 -Y 0
