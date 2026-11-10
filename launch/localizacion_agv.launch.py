#!/usr/bin/env python3

import os

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    proyecto = os.path.expanduser("~/agv_predictivo")

    mapa = os.path.join(
        proyecto, "mapas", "planta_industrial.yaml"
    )

    amcl_config = os.path.join(
        proyecto, "config", "amcl_e1.yaml"
    )

    return LaunchDescription([
        Node(
            package="nav2_map_server",
            executable="map_server",
            name="map_server",
            output="screen",
            parameters=[{
                "use_sim_time": True,
                "yaml_filename": mapa,
            }],
        ),

        Node(
            package="nav2_amcl",
            executable="amcl",
            name="amcl",
            output="screen",
            parameters=[amcl_config],
        ),

        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="tf_base_link_agv",
            arguments=[
                "--x", "0",
                "--y", "0",
                "--z", "0.010",
                "--roll", "0",
                "--pitch", "0",
                "--yaw", "0",
                "--frame-id", "base_footprint",
                "--child-frame-id", "base_link",
            ],
        ),

        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="tf_lidar_agv",
            arguments=[
                "--x", "-0.064",
                "--y", "0",
                "--z", "0.121",
                "--roll", "0",
                "--pitch", "0",
                "--yaw", "0",
                "--frame-id", "base_link",
                "--child-frame-id", "base_scan",
            ],
        ),

        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_localization",
            output="screen",
            parameters=[{
                "use_sim_time": True,
                "autostart": True,
                "node_names": ["map_server", "amcl"],
            }],
        ),
    ])
