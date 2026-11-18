"""Lanzamiento de la misión final en un dominio ROS dedicado a Gazebo."""
import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler, SetEnvironmentVariable, Shutdown
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

ROOT = Path(__file__).resolve().parents[1]


def generate_launch_description():
    gazebo = Path(get_package_share_directory("gazebo_ros"))
    waffle = Path(get_package_share_directory("turtlebot3_gazebo")) / "models/turtlebot3_waffle/model.sdf"
    server = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(gazebo / "launch/gazebo.launch.py")),
        launch_arguments={"world": str(ROOT / "mundos/planta_bombeo_agv.world"),
                          "gui": LaunchConfiguration("gui")}.items(),
    )
    spawn = ExecuteProcess(cmd=["ros2", "run", "gazebo_ros", "spawn_entity.py",
                                "-entity", "agv_waffle", "-file", str(waffle),
                                "-x", "-1.8", "-y", "0", "-z", "0.05", "-Y", "0"],
                           output="screen")

    def python(archivo, *argumentos):
        return ExecuteProcess(cmd=["python3", str(ROOT / archivo), *argumentos],
                              output="screen", additional_env={"PYTHONUNBUFFERED": "1"})

    inspector = python("scripts/final/inspeccionar.py", "--registro", LaunchConfiguration("registro"))
    return LaunchDescription([
        DeclareLaunchArgument("gui", default_value="true"),
        DeclareLaunchArgument("registro", default_value="gazebo_rondas.jsonl"),
        SetEnvironmentVariable("GAZEBO_MODEL_PATH", os.pathsep.join(filter(None, (
            str(waffle.parents[1]), os.environ.get("GAZEBO_MODEL_PATH"),
        )))),
        server, spawn,
        python("scripts/sensores/emulador_rangos_frontales.py"),
        python("scripts/final/nodos.py", "acelerometro"),
        python("scripts/final/nodos.py", "diagnosticador"),
        RegisterEventHandler(OnProcessExit(target_action=inspector, on_exit=[Shutdown()])),
        inspector,
    ])
