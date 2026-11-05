#!/usr/bin/env bash
set -euo pipefail
if ! grep -q '22.04' /etc/os-release; then echo 'ERROR: se requiere Ubuntu 22.04'; exit 1; fi
sudo apt update
sudo apt install -y software-properties-common curl gnupg lsb-release git python3-pip python3-venv python3-colcon-common-extensions python3-rosdep python3-numpy python3-scipy python3-yaml python3-matplotlib
sudo add-apt-repository -y universe
if ! command -v ros2 >/dev/null 2>&1 && [ ! -f /opt/ros/humble/setup.bash ]; then
  sudo curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
  sudo apt update
  sudo apt install -y ros-humble-desktop
fi
sudo apt install -y ros-humble-gazebo-ros-pkgs ros-humble-gazebo-plugins ros-humble-turtlebot3 ros-humble-turtlebot3-gazebo ros-humble-turtlebot3-description ros-humble-turtlebot3-teleop ros-humble-xacro ros-humble-robot-state-publisher ros-humble-joint-state-publisher ros-humble-nav-msgs ros-humble-sensor-msgs ros-humble-geometry-msgs
if ! command -v gazebo >/dev/null 2>&1; then sudo apt install -y gazebo11 || echo 'AVISO: gazebo11 no disponible; verificar repositorios de Gazebo Classic'; fi
sudo rosdep init 2>/dev/null || true
rosdep update
for line in 'source /opt/ros/humble/setup.bash' 'export TURTLEBOT3_MODEL=waffle'; do grep -qxF "$line" ~/.bashrc || echo "$line" >> ~/.bashrc; done
printf '\nInstalación de paquetes finalizada. Abra nueva terminal y ejecute: ros2 pkg list | grep turtlebot3\n'
