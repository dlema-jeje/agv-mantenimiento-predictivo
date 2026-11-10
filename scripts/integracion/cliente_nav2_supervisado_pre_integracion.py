#!/usr/bin/env python3
"""Cliente Nav2 con vigilancia continua y parada supervisada."""

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String

sys.path.insert(0, str(Path(__file__).resolve().parent))
from registro_resultados_nav2 import registrar_resultado


class ClienteSupervisado(Node):

    def __init__(self):
        super().__init__("cliente_nav2_supervisado_agv")

        self.cliente = ActionClient(
            self, NavigateToPose, "/navigate_to_pose"
        )

        self.modo = None
        self.t_modo = 0.0
        self.progreso = None
        self.t_progreso = time.monotonic()

        self.create_subscription(
            String, "/agv/estado_arbitro",
            self.recibir_modo, 10
        )

        self.pub_modo = self.create_publisher(
            String, "/agv/modo_control", 10
        )

    def recibir_modo(self, msg):
        self.modo = msg.data.strip().upper()
        self.t_modo = time.monotonic()

    def feedback(self, msg):
        distancia = msg.feedback.distance_remaining
        if not math.isfinite(distancia):
            return

        if (
            self.progreso is None
            or self.progreso - distancia >= 0.05
        ):
            self.progreso = distancia
            self.t_progreso = time.monotonic()

    def exclusivo(self):
        return self.count_publishers("/cmd_vel") == 1

    def estado_fresco(self):
        return (
            self.modo is not None
            and time.monotonic() - self.t_modo < 2.0
        )

    def comprobar(self):
        for _ in range(15):
            rclpy.spin_once(self, timeout_sec=0.2)

        nav2 = self.cliente.wait_for_server(timeout_sec=2.0)
        arbitro = self.estado_fresco()
        exclusivo = self.exclusivo()

        print(f"NAV2_DISPONIBLE: {nav2}")
        print(f"ARBITRO_DISPONIBLE: {arbitro}")
        print(f"MODO_ARBITRO: {self.modo}")
        print(f"PUBLICADOR_EXCLUSIVO: {exclusivo}")
        print("OBJETIVO_ENVIADO: NO")
        print("MOVIMIENTO_SOLICITADO: NO")

        return nav2 and arbitro and exclusivo

    def solicitar_stop(self):
        mensaje = String()
        mensaje.data = "STOP"

        for _ in range(10):
            self.pub_modo.publish(mensaje)
            rclpy.spin_once(self, timeout_sec=0.1)

            if self.modo == "STOP" and self.estado_fresco():
                return True

        return False

    def vigilar(self, futuro, inicio, tiempo_maximo, sin_progreso):
        while rclpy.ok() and not futuro.done():
            rclpy.spin_once(self, timeout_sec=0.1)
            ahora = time.monotonic()

            if not self.estado_fresco():
                return "ESTADO_ARBITRO_OBSOLETO"

            if self.modo != "NAV2":
                return "MODO_ARBITRO_INCORRECTO"

            if not self.exclusivo():
                return "PUBLICADORES_MULTIPLES"

            if ahora - inicio > tiempo_maximo:
                return "TIEMPO_MAXIMO"

            if ahora - self.t_progreso > sin_progreso:
                return "SIN_PROGRESO"

        return None

    def ejecutar(self, estacion, tiempo_maximo, sin_progreso):
        if not self.comprobar():
            raise RuntimeError("Diagnóstico previo no aprobado")

        if self.modo != "NAV2":
            raise RuntimeError(
                "Árbitro en STOP. No se envía el objetivo. "
                "La habilitación NAV2 requiere supervisión previa."
            )

        objetivo = NavigateToPose.Goal()
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()

        pose.pose.position.x = float(estacion["pre_x"])
        pose.pose.position.y = float(estacion["pre_y"])

        yaw = float(estacion["pre_yaw"])
        pose.pose.orientation.z = math.sin(yaw / 2)
        pose.pose.orientation.w = math.cos(yaw / 2)
        objetivo.pose = pose

        futuro_envio = self.cliente.send_goal_async(
            objetivo,
            feedback_callback=self.feedback
        )

        rclpy.spin_until_future_complete(
            self, futuro_envio, timeout_sec=5.0
        )

        if not futuro_envio.done():
            self.solicitar_stop()
            raise RuntimeError(
                "No se confirmó la aceptación del objetivo"
            )

        manejador = futuro_envio.result()

        if manejador is None or not manejador.accepted:
            self.solicitar_stop()
            print("RESULTADO: OBJETIVO_RECHAZADO")
            return

        print("OBJETIVO_ACEPTADO: SI")

        inicio = time.monotonic()
        self.t_progreso = inicio
        self.progreso = None

        futuro_resultado = manejador.get_result_async()

        motivo = self.vigilar(
            futuro_resultado,
            inicio,
            tiempo_maximo,
            sin_progreso
        )

        if motivo is not None:
            print(f"CANCELACION_SOLICITADA: {motivo}")

            futuro_cancelar = manejador.cancel_goal_async()
            rclpy.spin_until_future_complete(
                self, futuro_cancelar, timeout_sec=5.0
            )

        # STOP incluso si la cancelación no fue confirmada.
        stop_confirmado = self.solicitar_stop()
        print(f"STOP_CONFIRMADO: {stop_confirmado}")

        if futuro_resultado.done():
            resultado = futuro_resultado.result()
            if resultado is not None:
                registro = registrar_resultado(
                    estacion=estacion["estacion"],
                    objetivo_x=float(estacion["pre_x"]),
                    objetivo_y=float(estacion["pre_y"]),
                    objetivo_yaw=yaw,
                    codigo_estado=resultado.status,
                )
                print(
                    f"RESULTADO_NAV2: {registro['resultado']}"
                )
                print(
                    "EXITO_CONFIRMADO: "
                    f"{registro['exito_confirmado']}"
                )
                return

        print("RESULTADO_NAV2: NO_CONFIRMADO")
        print("EXITO_CONFIRMADO: False")


def cargar_estacion(ruta, nombre):
    with open(ruta, newline="", encoding="utf-8") as archivo:
        for fila in csv.DictReader(archivo):
            if fila["estacion"] == nombre:
                return fila

    raise ValueError(f"Estación desconocida: {nombre}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--estacion", default="E1")
    parser.add_argument(
        "--objetivos",
        default="datos/objetivos_acoplamiento.csv"
    )
    parser.add_argument("--ejecutar", action="store_true")
    parser.add_argument(
        "--tiempo-maximo", type=float, default=120.0
    )
    parser.add_argument(
        "--sin-progreso", type=float, default=45.0
    )
    args = parser.parse_args()

    estacion = cargar_estacion(
        args.objetivos, args.estacion
    )

    rclpy.init()
    nodo = ClienteSupervisado()

    try:
        if args.ejecutar:
            raise RuntimeError(
                "EJECUCION_BLOQUEADA: faltan pruebas de "
                "cancelacion, parada y supervision continua"
            )
        else:
            nodo.comprobar()
    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
