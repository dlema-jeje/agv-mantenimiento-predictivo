#!/usr/bin/env python3
"""Cliente Nav2 supervisado. Diagnóstico sin movimiento por defecto."""

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Twist
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String

sys.path.insert(0, str(Path(__file__).resolve().parent))
from registro_resultados_nav2 import registrar_resultado


class ClienteSupervisado(Node):
    def __init__(self):
        super().__init__("cliente_nav2_supervisado_agv")

        self.cliente = ActionClient(
            self, NavigateToPose, "navigate_to_pose"
        )

        self.modo = None
        self.t_modo = 0.0

        self.create_subscription(
            String,
            "/agv/estado_arbitro",
            self.recibir_modo,
            QoSProfile(depth=10),
        )

    def recibir_modo(self, msg):
        self.modo = msg.data.strip().upper()
        self.t_modo = time.monotonic()

    def arbitro_disponible(self):
        return (
            self.modo is not None
            and time.monotonic() - self.t_modo < 2.0
        )

    def publicador_exclusivo(self):
        return self.count_publishers("/cmd_vel") == 1

    def diagnostico(self):
        for _ in range(15):
            rclpy.spin_once(self, timeout_sec=0.2)

        nav2 = self.cliente.wait_for_server(timeout_sec=2.0)
        arbitro = self.arbitro_disponible()
        exclusivo = self.publicador_exclusivo()

        print(f"NAV2_DISPONIBLE: {nav2}")
        print(f"ARBITRO_DISPONIBLE: {arbitro}")
        print(f"MODO_ARBITRO: {self.modo}")
        print(f"PUBLICADOR_EXCLUSIVO: {exclusivo}")
        print("OBJETIVO_ENVIADO: NO")
        print("MOVIMIENTO_SOLICITADO: NO")

        return nav2 and arbitro and exclusivo

    def ejecutar(self, estacion):
        if not self.diagnostico():
            raise RuntimeError("Diagnóstico previo no aprobado")

        if self.modo != "NAV2":
            raise RuntimeError(
                "El árbitro no está en NAV2. "
                "No se enviará ningún objetivo."
            )

        objetivo = NavigateToPose.Goal()
        objetivo.pose.header.frame_id = "map"
        objetivo.pose.header.stamp = self.get_clock().now().to_msg()
        objetivo.pose.pose.position.x = float(estacion["pre_x"])
        objetivo.pose.pose.position.y = float(estacion["pre_y"])

        yaw = float(estacion["pre_yaw"])
        objetivo.pose.pose.orientation.z = math.sin(yaw / 2)
        objetivo.pose.pose.orientation.w = math.cos(yaw / 2)

        futuro = self.cliente.send_goal_async(objetivo)
        rclpy.spin_until_future_complete(self, futuro)

        manejador = futuro.result()

        if manejador is None or not manejador.accepted:
            print("RESULTADO: OBJETIVO_RECHAZADO")
            return

        print("OBJETIVO_ACEPTADO: SI")

        resultado_futuro = manejador.get_result_async()
        rclpy.spin_until_future_complete(
            self, resultado_futuro
        )

        resultado = resultado_futuro.result()

        if resultado is None:
            print("RESULTADO: NO_DISPONIBLE")
            return

        registro = registrar_resultado(
            estacion=estacion["estacion"],
            objetivo_x=float(estacion["pre_x"]),
            objetivo_y=float(estacion["pre_y"]),
            objetivo_yaw=yaw,
            codigo_estado=resultado.status,
        )

        print(f"RESULTADO_NAV2: {registro['resultado']}")
        print(
            f"EXITO_CONFIRMADO: "
            f"{registro['exito_confirmado']}"
        )


def cargar_estacion(ruta, nombre):
    with open(ruta, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
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
    parser.add_argument(
        "--ejecutar",
        action="store_true",
    )
    args = parser.parse_args()

    estacion = cargar_estacion(
        args.objetivos, args.estacion
    )

    rclpy.init()
    nodo = ClienteSupervisado()

    try:
        if args.ejecutar:
            nodo.ejecutar(estacion)
        else:
            nodo.diagnostico()
    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
