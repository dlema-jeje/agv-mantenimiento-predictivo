#!/usr/bin/env python3
"""Pruebas reales del protocolo ROS2 Action, sin movimiento."""

import csv
import threading
import time
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.action import (
    ActionClient, ActionServer,
    CancelResponse, GoalResponse
)
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose

ACCION = "/agv_pruebas/navigate_to_pose"


class ServidorPrueba(Node):
    def __init__(self):
        super().__init__("servidor_acciones_agv_pruebas")
        self.servidor = ActionServer(
            self,
            NavigateToPose,
            ACCION,
            execute_callback=self.ejecutar,
            goal_callback=lambda _: GoalResponse.ACCEPT,
            cancel_callback=lambda _: CancelResponse.ACCEPT,
        )

    def ejecutar(self, goal_handle):
        caso = round(
            goal_handle.request.pose.pose.position.x
        )

        for _ in range(20):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                return NavigateToPose.Result()
            time.sleep(0.05)

        if caso == 3:
            goal_handle.abort()
        else:
            goal_handle.succeed()

        return NavigateToPose.Result()


class ClientePrueba(Node):
    def __init__(self):
        super().__init__("cliente_acciones_agv_pruebas")
        self.cliente = ActionClient(
            self, NavigateToPose, ACCION
        )


def esperar(futuro, timeout=5.0):
    limite = time.monotonic() + timeout
    while not futuro.done():
        if time.monotonic() >= limite:
            raise TimeoutError("Respuesta ROS2 no recibida")
        time.sleep(0.02)
    return futuro.result()


def probar(cliente, nombre, codigo, cancelar, esperado):
    objetivo = NavigateToPose.Goal()
    objetivo.pose.header.frame_id = "map"
    objetivo.pose.pose.position.x = float(codigo)
    objetivo.pose.pose.orientation.w = 1.0

    manejador = esperar(
        cliente.cliente.send_goal_async(objetivo)
    )

    if not manejador.accepted:
        raise RuntimeError(f"{nombre}: objetivo rechazado")

    cancelacion_aceptada = False

    if cancelar:
        time.sleep(0.2)
        respuesta = esperar(
            manejador.cancel_goal_async()
        )
        cancelacion_aceptada = bool(
            respuesta.goals_canceling
        )

    resultado = esperar(
        manejador.get_result_async()
    )

    aprobado = (
        resultado.status == esperado
        and (not cancelar or cancelacion_aceptada)
    )

    print(
        f"{nombre}: "
        f"{'APROBADA' if aprobado else 'FALLIDA'} "
        f"| estado={resultado.status} "
        f"| cancelacion_aceptada={cancelacion_aceptada}"
    )

    return {
        "fecha": datetime.now().isoformat(),
        "caso": nombre,
        "estado_obtenido": resultado.status,
        "estado_esperado": esperado,
        "cancelacion_aceptada": cancelacion_aceptada,
        "aprobada": aprobado,
        "servidor": ACCION,
        "movimiento_solicitado": False,
    }


def main():
    rclpy.init()
    servidor = ServidorPrueba()
    cliente = ClientePrueba()
    executor = MultiThreadedExecutor(num_threads=4)

    executor.add_node(servidor)
    executor.add_node(cliente)

    hilo = threading.Thread(
        target=executor.spin, daemon=True
    )
    hilo.start()

    resultados = []

    try:
        if not cliente.cliente.wait_for_server(
            timeout_sec=5.0
        ):
            raise RuntimeError(
                "Servidor de prueba no disponible"
            )

        resultados.append(probar(
            cliente,
            "EXITO_ROS2",
            1,
            False,
            GoalStatus.STATUS_SUCCEEDED,
        ))

        resultados.append(probar(
            cliente,
            "CANCELACION_ROS2",
            2,
            True,
            GoalStatus.STATUS_CANCELED,
        ))

        resultados.append(probar(
            cliente,
            "ABORTO_ROS2",
            3,
            False,
            GoalStatus.STATUS_ABORTED,
        ))

        ruta = Path(
            "datos/registros/integracion/"
            "pruebas_acciones_ros2.csv"
        )

        with ruta.open(
            "w", newline="", encoding="utf-8"
        ) as archivo:
            escritor = csv.DictWriter(
                archivo,
                fieldnames=resultados[0].keys()
            )
            escritor.writeheader()
            escritor.writerows(resultados)

        aprobadas = sum(
            fila["aprobada"] for fila in resultados
        )

        print()
        print(f"PRUEBAS_TOTALES: {len(resultados)}")
        print(f"PRUEBAS_APROBADAS: {aprobadas}")
        print(f"REGISTRO: {ruta}")
        print("OBJETIVOS_NAV2_REAL_ENVIADOS: 0")
        print("MOVIMIENTO_SOLICITADO: NO")

        if aprobadas != len(resultados):
            raise SystemExit(1)

    finally:
        executor.shutdown(timeout_sec=3.0)
        servidor.destroy_node()
        cliente.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
