"""Lanzamiento de la misión final en un dominio ROS dedicado a Gazebo."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, GroupAction, IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler, SetEnvironmentVariable, Shutdown
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit, OnShutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

ROOT = Path(__file__).resolve().parents[1]


def generate_launch_description():
    gazebo = Path(get_package_share_directory("gazebo_ros"))
    waffle = Path(get_package_share_directory("turtlebot3_gazebo")) / "models/turtlebot3_waffle/model.sdf"
    video = LaunchConfiguration("video")

    def iniciar_gazebo(context):
        mundo = ROOT / "mundos/planta_bombeo_agv.world"
        acciones = []
        if IfCondition(video).evaluate(context):
            temporal = TemporaryDirectory(prefix="agv-gazebo-")
            arbol = ElementTree.parse(mundo)
            arbol.find("./world/physics/real_time_update_rate").text = "4500"
            mundo = Path(temporal.name) / mundo.name
            arbol.write(mundo, encoding="utf-8", xml_declaration=True)

            def limpiar(_):
                temporal.cleanup()

            acciones.append(RegisterEventHandler(OnShutdown(
                on_shutdown=[OpaqueFunction(function=limpiar)],
            )))
        acciones.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(gazebo / "launch/gazebo.launch.py")),
            launch_arguments={"world": str(mundo),
                              "gui": LaunchConfiguration("gui")}.items(),
        ))
        return acciones

    def python(archivo, *argumentos):
        return ExecuteProcess(cmd=["python3", str(ROOT / archivo), *argumentos],
                              output="screen", additional_env={"PYTHONUNBUFFERED": "1"})

    spawn = python("scripts/final/spawn_waffle.py", "--modelo", str(waffle), "--video", video)
    inspector = python("scripts/final/inspeccionar.py", "--registro", LaunchConfiguration("registro"))
    ensayo = python("scripts/final/ensayar_acople.py", "--registro", LaunchConfiguration("registro"))
    modo = LaunchConfiguration("ensayos")
    return LaunchDescription([
        DeclareLaunchArgument("ensayos", default_value="false"),
        DeclareLaunchArgument("gui", default_value="true"),
        DeclareLaunchArgument("video", default_value="false",
                              description="Acelera el reloj de Gazebo para grabación."),
        DeclareLaunchArgument("registro", default_value="gazebo_rondas.jsonl"),
        SetEnvironmentVariable("GAZEBO_MODEL_PATH", os.pathsep.join(filter(None, (
            str(waffle.parents[1]), os.environ.get("GAZEBO_MODEL_PATH"),
        )))),
        OpaqueFunction(function=iniciar_gazebo), spawn,
        python("scripts/sensores/emulador_rangos_frontales.py"),
        GroupAction(condition=UnlessCondition(modo), actions=[
            python("scripts/final/nodos.py", "acelerometro"),
            python("scripts/final/nodos.py", "diagnosticador"),
            RegisterEventHandler(OnProcessExit(target_action=inspector, on_exit=[Shutdown()])),
            inspector,
        ]),
        GroupAction(condition=IfCondition(modo), actions=[
            RegisterEventHandler(OnProcessExit(target_action=ensayo, on_exit=[Shutdown()])),
            ensayo,
        ]),
    ])
