#!/usr/bin/env python3

import time
import math

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String


class ArbitroVelocidades(Node):

    def __init__(self):
        super().__init__("arbitro_velocidades_agv")

        self.modo = "STOP"
        self.ultimo = {}
        self.tiempos = {}

        self.velocidad_lineal = 0.0
        self.velocidad_angular = 0.0
        self.tiempo_odom = 0.0
        self.inicio_stop = time.monotonic()

        self.entradas = {
            "NAV2": "/cmd_vel_nav_smooth",
            "BEHAVIOR": "/cmd_vel_behavior",
            "MAMDANI": "/cmd_vel_mamdani",
        }

        self.pub = self.create_publisher(
            Twist, "/cmd_vel", 10
        )

        self.estado_pub = self.create_publisher(
            String, "/agv/estado_arbitro", 10
        )

        for origen, topico in self.entradas.items():
            self.create_subscription(
                Twist,
                topico,
                lambda msg, nombre=origen: self.recibir(nombre, msg),
                10,
            )

        self.create_subscription(
            Odometry,
            "/odom",
            self.recibir_odom,
            10,
        )

        self.create_subscription(
            String,
            "/agv/modo_control",
            self.cambiar_modo,
            10,
        )

        self.create_timer(0.05, self.publicar)

        self.get_logger().info(
            "Árbitro iniciado en STOP."
        )

    def recibir(self, origen, mensaje):
        self.ultimo[origen] = mensaje
        self.tiempos[origen] = time.monotonic()

    def recibir_odom(self, msg):
        self.velocidad_lineal = msg.twist.twist.linear.x
        self.velocidad_angular = msg.twist.twist.angular.z
        self.tiempo_odom = time.monotonic()

    def detenido(self):
        return (
            time.monotonic() - self.tiempo_odom < 0.3
            and abs(self.velocidad_lineal) < 0.01
            and abs(self.velocidad_angular) < 0.03
        )

    def cambiar_modo(self, msg):
        solicitado = msg.data.strip().upper()

        if solicitado not in (
            "STOP", "NAV2", "BEHAVIOR", "MAMDANI"
        ):
            self.get_logger().warning(
                f"Modo inválido: {solicitado}"
            )
            return

        if solicitado == "STOP":
            self.modo = "STOP"
            self.inicio_stop = time.monotonic()
            self.ultimo.clear()
            self.tiempos.clear()
            self.get_logger().info("Modo STOP")
            return

        if self.modo != "STOP":
            self.get_logger().warning(
                "Transferencia rechazada: primero STOP."
            )
            return

        if time.monotonic() - self.inicio_stop < 1.0:
            self.get_logger().warning(
                "Esperando 1 segundo en STOP."
            )
            return

        if not self.detenido():
            self.get_logger().warning(
                "Transferencia rechazada: robot no detenido "
                "o odometría no disponible."
            )
            return

        self.modo = solicitado
        self.ultimo.clear()
        self.tiempos.clear()

        self.get_logger().info(
            f"Control autorizado: {self.modo}"
        )

    def publicar(self):
        salida = Twist()
        ahora = time.monotonic()

        if self.modo != "STOP":
            mensaje = self.ultimo.get(self.modo)
            instante = self.tiempos.get(self.modo, 0.0)

            if (
                mensaje is not None
                and ahora - instante <= 0.25
                and ahora - self.tiempo_odom <= 0.3
            ):
                vx = mensaje.linear.x
                wz = mensaje.angular.z

                if math.isfinite(vx) and math.isfinite(wz):
                    salida.linear.x = max(
                        -0.10, min(0.15, vx)
                    )
                    salida.angular.z = max(
                        -0.8, min(0.8, wz)
                    )

        self.pub.publish(salida)

        estado = String()
        estado.data = self.modo
        self.estado_pub.publish(estado)


def main():
    rclpy.init()
    nodo = ArbitroVelocidades()

    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
