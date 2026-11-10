#!/usr/bin/env python3
import time
import rclpy

from rclpy.node import Node
from nav_msgs.msg import Odometry
from std_msgs.msg import String

class Verificador(Node):
    def __init__(self):
        super().__init__("verificador_reposo_agv")
        self.odom = None
        self.t_odom = 0.0
        self.modo = None
        self.t_modo = 0.0

        self.create_subscription(
            Odometry, "/odom", self.recibir_odom, 10
        )
        self.create_subscription(
            String, "/agv/estado_arbitro",
            self.recibir_modo, 10
        )

    def recibir_odom(self, msg):
        self.odom = msg
        self.t_odom = time.monotonic()

    def recibir_modo(self, msg):
        self.modo = msg.data.strip().upper()
        self.t_modo = time.monotonic()

def main():
    rclpy.init()
    nodo = Verificador()

    try:
        limite = time.monotonic() + 5.0

        while time.monotonic() < limite:
            rclpy.spin_once(nodo, timeout_sec=0.1)

        publicadores = nodo.get_publishers_info_by_topic(
            "/cmd_vel"
        )

        for p in publicadores:
            print(
                "PUBLICADOR_CMD_VEL:",
                f"{p.node_namespace}/{p.node_name}"
            )

        exclusivo = (
            len(publicadores) == 1
            and publicadores[0].node_name
                == "arbitro_velocidades_agv"
        )

        odom_fresca = (
            nodo.odom is not None
            and time.monotonic() - nodo.t_odom < 0.5
        )

        detenido = False
        if odom_fresca:
            v = nodo.odom.twist.twist.linear.x
            w = nodo.odom.twist.twist.angular.z
            detenido = abs(v) < 0.01 and abs(w) < 0.03
            print(f"VELOCIDAD_LINEAL: {v:.5f}")
            print(f"VELOCIDAD_ANGULAR: {w:.5f}")

        modo_fresco = (
            nodo.modo is not None
            and time.monotonic() - nodo.t_modo < 2.0
        )

        print(f"ARBITRO_EXCLUSIVO: {exclusivo}")
        print(f"ODOMETRIA_FRESCA: {odom_fresca}")
        print(f"ROBOT_DETENIDO: {detenido}")
        print(f"MODO_ARBITRO: {nodo.modo}")
        print(f"ESTADO_ARBITRO_FRESCO: {modo_fresco}")

        aprobado = (
            exclusivo
            and odom_fresca
            and detenido
            and modo_fresco
            and nodo.modo == "STOP"
        )

        print(
            "VERIFICACION_REPOSO:",
            "APROBADA" if aprobado else "NO_APROBADA"
        )
        print("MOVIMIENTO_SOLICITADO: NO")

        if not aprobado:
            raise SystemExit(1)

    finally:
        nodo.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
