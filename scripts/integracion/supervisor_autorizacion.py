#!/usr/bin/env python3

import math
import time

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String


class SupervisorAutorizacion(Node):

    def __init__(self):
        super().__init__("supervisor_autorizacion_agv")

        self.declare_parameter("distancia_frontal_minima", 0.30)
        self.declare_parameter("velocidad_lineal_maxima", 0.01)
        self.declare_parameter("velocidad_angular_maxima", 0.03)
        self.declare_parameter("antiguedad_maxima", 0.50)

        self.odom = None
        self.scan = None
        self.t_odom = 0.0
        self.t_scan = 0.0

        self.estado_nav2 = "NO_CONFIRMADO"
        self.preacoplamiento = "NO_CONFIRMADO"

        self.pub = self.create_publisher(
            String, "/agv/diagnostico_autorizacion", 10
        )

        self.create_subscription(
            Odometry, "/odom", self.recibir_odom, 10
        )

        self.create_subscription(
            LaserScan, "/scan", self.recibir_scan, 10
        )

        self.create_timer(1.0, self.evaluar)

        self.get_logger().info(
            "Supervisor diagnóstico iniciado. "
            "No publica velocidades ni autoriza movimiento."
        )

    def recibir_odom(self, msg):
        self.odom = msg
        self.t_odom = time.monotonic()

    def recibir_scan(self, msg):
        self.scan = msg
        self.t_scan = time.monotonic()

    def distancia_frontal(self):
        if self.scan is None:
            return None

        valores = []
        angulo = self.scan.angle_min

        for distancia in self.scan.ranges:
            if abs(angulo) <= math.radians(15):
                if (
                    math.isfinite(distancia)
                    and self.scan.range_min <= distancia
                    <= self.scan.range_max
                ):
                    valores.append(distancia)

            angulo += self.scan.angle_increment

        return min(valores) if valores else None

    def evaluar(self):
        ahora = time.monotonic()
        razones = []

        antiguedad = float(
            self.get_parameter("antiguedad_maxima").value
        )

        if (
            self.odom is None
            or ahora - self.t_odom > antiguedad
        ):
            razones.append("ODOMETRIA_NO_DISPONIBLE")
        else:
            vx = self.odom.twist.twist.linear.x
            wz = self.odom.twist.twist.angular.z

            if (
                abs(vx) >= float(
                    self.get_parameter(
                        "velocidad_lineal_maxima"
                    ).value
                )
                or abs(wz) >= float(
                    self.get_parameter(
                        "velocidad_angular_maxima"
                    ).value
                )
            ):
                razones.append("ROBOT_NO_DETENIDO")

        if (
            self.scan is None
            or ahora - self.t_scan > antiguedad
        ):
            razones.append("LIDAR_NO_DISPONIBLE")
        else:
            distancia = self.distancia_frontal()
            limite = float(
                self.get_parameter(
                    "distancia_frontal_minima"
                ).value
            )

            if distancia is None:
                razones.append("SIN_LECTURAS_FRONTALES")
            elif distancia < limite:
                razones.append(
                    f"OBSTACULO_FRONTAL_{distancia:.3f}m"
                )

        # Estas condiciones requieren una integración
        # posterior con Nav2 y el supervisor geométrico.
        razones.append("NAV2_NO_CONFIRMADO")
        razones.append("PREACOPLAMIENTO_NO_CONFIRMADO")

        estado = String()
        estado.data = (
            "NO_AUTORIZADO | " + ", ".join(razones)
        )

        self.pub.publish(estado)


def main():
    rclpy.init()
    nodo = SupervisorAutorizacion()

    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
