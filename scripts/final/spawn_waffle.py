"""Inserta el Waffle canónico con control directo de consigna de rueda en Gazebo."""
import argparse
from pathlib import Path
from xml.etree import ElementTree

import rclpy
from gazebo_msgs.srv import SpawnEntity
from rclpy.node import Node


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--modelo", type=Path, required=True)
    parser.add_argument("--video", choices=("true", "false"), default="false", type=str.lower)
    args, ros_args = parser.parse_known_args()
    arbol = ElementTree.parse(args.modelo)
    aceleracion = arbol.find(
        ".//plugin[@filename='libgazebo_ros_diff_drive.so']/max_wheel_acceleration"
    )
    if aceleracion is None:
        raise RuntimeError("El modelo Waffle no contiene el parámetro de rampa esperado.")
    # Evita la acumulación de consigna de rueda observada al alternar giro y avance.
    aceleracion.text = "0"
    if args.video == "true":
        # La misión usa LiDAR y odometría. Omitir la cámara evita su render.
        for enlace in arbol.findall(".//link"):
            for sensor in enlace.findall("sensor[@type='camera']"):
                enlace.remove(sensor)

    rclpy.init(args=ros_args)
    nodo = Node("spawn_waffle_avance3")
    try:
        cliente = nodo.create_client(SpawnEntity, "/spawn_entity")
        if not cliente.wait_for_service(timeout_sec=30):
            raise RuntimeError("Gazebo no ofrece /spawn_entity.")
        solicitud = SpawnEntity.Request()
        solicitud.name = "agv_waffle"
        solicitud.xml = ElementTree.tostring(arbol.getroot(), encoding="unicode")
        solicitud.initial_pose.position.x = -1.8
        solicitud.initial_pose.position.z = 0.05
        solicitud.initial_pose.orientation.w = 1.0
        futuro = cliente.call_async(solicitud)
        rclpy.spin_until_future_complete(nodo, futuro, timeout_sec=20)
        if not futuro.done() or not futuro.result().success:
            razon = futuro.result().status_message if futuro.done() else "tiempo agotado"
            raise RuntimeError(f"Gazebo no insertó el Waffle. {razon}")
        nodo.get_logger().info(futuro.result().status_message)
    finally:
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
