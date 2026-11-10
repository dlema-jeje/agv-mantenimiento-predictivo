#!/usr/bin/env python3
import math
import random

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, Range


class EmuladorRangosFrontales(Node):
    def __init__(self):
        super().__init__("emulador_rangos_frontales")

        self.declare_parameter("x_lidar", -0.064)
        self.declare_parameter("x_frente", 0.0685)
        self.declare_parameter("separacion", 0.20)
        self.declare_parameter("tolerancia_banda", 0.015)
        self.declare_parameter("sigma_ruido", 0.005)
        self.declare_parameter("distancia_maxima", 1.2)

        self.x_lidar = float(
            self.get_parameter("x_lidar").value
        )
        self.x_frente = float(
            self.get_parameter("x_frente").value
        )
        self.separacion = float(
            self.get_parameter("separacion").value
        )
        self.tolerancia = float(
            self.get_parameter("tolerancia_banda").value
        )
        self.sigma = float(
            self.get_parameter("sigma_ruido").value
        )
        self.maximo = float(
            self.get_parameter("distancia_maxima").value
        )

        self.pub_fi = self.create_publisher(
            Range, "/rango_fi", 10
        )
        self.pub_fd = self.create_publisher(
            Range, "/rango_fd", 10
        )

        self.create_subscription(
            LaserScan, "/scan", self.recibir_scan, 10
        )

        self.get_logger().info(
            "Emulador listo: "
            f"desplazamiento={self.x_frente-self.x_lidar:.4f} m; "
            "movimiento=NO"
        )

    def calcular_distancia(self, scan, y_objetivo):
        candidatos = []

        for i, distancia in enumerate(scan.ranges):
            if not math.isfinite(distancia):
                continue

            if not (
                scan.range_min <= distancia <= scan.range_max
            ):
                continue

            angulo = (
                scan.angle_min + i * scan.angle_increment
            )

            x = self.x_lidar + distancia * math.cos(angulo)
            y = distancia * math.sin(angulo)

            if x <= self.x_frente:
                continue

            if abs(y - y_objetivo) <= self.tolerancia:
                candidatos.append(x - self.x_frente)

        if not candidatos:
            return math.nan

        distancia = min(candidatos)

        if distancia > self.maximo:
            return math.nan

        distancia += random.gauss(0.0, self.sigma)

        return max(0.0, min(self.maximo, distancia))

    def crear_mensaje(self, scan, distancia, nombre):
        msg = Range()

        msg.header.stamp = scan.header.stamp
        msg.header.frame_id = "base_link"

        msg.radiation_type = Range.INFRARED
        msg.field_of_view = 0.03
        msg.min_range = 0.0
        msg.max_range = self.maximo
        msg.range = float(distancia)

        return msg

    def recibir_scan(self, scan):
        izquierda = self.calcular_distancia(
            scan, +self.separacion / 2.0
        )
        derecha = self.calcular_distancia(
            scan, -self.separacion / 2.0
        )

        self.pub_fi.publish(
            self.crear_mensaje(scan, izquierda, "fi")
        )
        self.pub_fd.publish(
            self.crear_mensaje(scan, derecha, "fd")
        )


def main():
    rclpy.init()
    nodo = EmuladorRangosFrontales()

    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
