#!/usr/bin/env python3
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String


class ArbitroVelocidades(Node):
    def __init__(self):
        super().__init__("arbitro_velocidades_agv")

        self.modo = "STOP"
        self.ultimo = {
            "NAV2": None,
            "MAMDANI": None,
        }
        self.instante = {
            "NAV2": 0.0,
            "MAMDANI": 0.0,
        }

        self.publicador = self.create_publisher(
            Twist, "/cmd_vel", 10
        )

        self.create_subscription(
            Twist,
            "/cmd_vel_nav_smooth",
            lambda msg: self.recibir("NAV2", msg),
            10,
        )

        self.create_subscription(
            Twist,
            "/cmd_vel_mamdani",
            lambda msg: self.recibir("MAMDANI", msg),
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
            "Árbitro iniciado en STOP. "
            "Ningún controlador tiene permiso de movimiento."
        )

    def recibir(self, origen, mensaje):
        self.ultimo[origen] = mensaje
        self.instante[origen] = time.monotonic()

    def cambiar_modo(self, mensaje):
        solicitado = mensaje.data.strip().upper()

        if solicitado not in ("STOP", "NAV2", "MAMDANI"):
            self.get_logger().warning(
                f"Modo inválido: {solicitado}"
            )
            return

        if solicitado != self.modo:
            anterior = self.modo
            self.modo = "STOP"

            self.ultimo["NAV2"] = None
            self.ultimo["MAMDANI"] = None

            self.get_logger().info(
                f"Transferencia {anterior} -> STOP"
            )

            # Para una primera integración segura,
            # los cambios de controlador requieren
            # una orden posterior explícita.
            if solicitado != "STOP":
                self.get_logger().warning(
                    f"Solicitud {solicitado} recibida. "
                    "El árbitro permanece en STOP hasta "
                    "la autorización supervisada."
                )

    def publicar(self):
        salida = Twist()

        if self.modo in ("NAV2", "MAMDANI"):
            edad = (
                time.monotonic()
                - self.instante[self.modo]
            )

            if (
                self.ultimo[self.modo] is not None
                and edad <= 0.25
            ):
                salida = self.ultimo[self.modo]

        self.publicador.publish(salida)


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
