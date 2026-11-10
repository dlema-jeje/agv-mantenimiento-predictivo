import math
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.action.client import GoalStatus
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose


DESTINO_X = 0.75
DESTINO_Y = -1.40
TIEMPO_MAXIMO = 120.0


class Navegador(Node):
    def __init__(self):
        super().__init__("prueba_preacople_e1")
        self.set_parameters([Parameter("use_sim_time", value=True)])
        self.cliente = ActionClient(
            self, NavigateToPose, "/navigate_to_pose"
        )

    def crear_objetivo(self):
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = DESTINO_X
        pose.pose.position.y = DESTINO_Y
        pose.pose.orientation.z = 0.0
        pose.pose.orientation.w = 1.0
        return pose


def esperar(executor, futuro, segundos):
    limite = time.monotonic() + segundos
    while rclpy.ok() and not futuro.done():
        if time.monotonic() >= limite:
            raise TimeoutError("Tiempo de espera agotado")
        executor.spin_once(timeout_sec=0.1)
    return futuro.result()


def main():
    rclpy.init()
    nodo = Navegador()
    executor = SingleThreadedExecutor()
    executor.add_node(nodo)

    try:
        print("Esperando servidor NavigateToPose...", flush=True)

        if not nodo.cliente.wait_for_server(timeout_sec=10):
            print("RESULTADO: NAV2_NO_DISPONIBLE")
            return

        objetivo = NavigateToPose.Goal()
        objetivo.pose = nodo.crear_objetivo()

        print(
            f"Objetivo E1: ({DESTINO_X:.2f}, "
            f"{DESTINO_Y:.2f}, yaw=0°)"
        )
        print("MAMDANI: DESACTIVADO")
        print("MOVIMIENTO: AUTORIZADO SOLO POR NAV2")

        handle = esperar(
            executor,
            nodo.cliente.send_goal_async(objetivo),
            10
        )

        if not handle.accepted:
            print("RESULTADO: OBJETIVO_RECHAZADO")
            return

        print("OBJETIVO_ACEPTADO: navegando...", flush=True)

        futuro_resultado = handle.get_result_async()
        inicio = time.monotonic()
        ultimo_reporte = inicio

        while rclpy.ok() and not futuro_resultado.done():
            executor.spin_once(timeout_sec=0.1)
            ahora = time.monotonic()

            if ahora - ultimo_reporte >= 5:
                print(
                    f"Navegación en curso: "
                    f"{ahora - inicio:.1f} s",
                    flush=True
                )
                ultimo_reporte = ahora

            if ahora - inicio >= TIEMPO_MAXIMO:
                print("TIEMPO_MAXIMO: solicitando cancelación...")
                cancelacion = handle.cancel_goal_async()
                respuesta = esperar(executor, cancelacion, 10)

                if respuesta.goals_canceling:
                    print("CANCELACION_ACEPTADA")
                else:
                    print("ADVERTENCIA: CANCELACION_NO_CONFIRMADA")

                try:
                    final = esperar(executor, futuro_resultado, 10)
                    print(f"Estado final Nav2: {final.status}")
                except TimeoutError:
                    print("ADVERTENCIA: SIN_RESULTADO_FINAL")

                print("RESULTADO: TIEMPO_MAXIMO")
                return

        resultado = futuro_resultado.result()
        print(f"Estado final Nav2: {resultado.status}")

        if resultado.status == GoalStatus.STATUS_SUCCEEDED:
            print("RESULTADO: NAV2_LLEGO_A_E1")
        elif resultado.status == GoalStatus.STATUS_CANCELED:
            print("RESULTADO: CANCELADO")
        else:
            print("RESULTADO: NAVEGACION_FALLIDA")

    except (KeyboardInterrupt, Exception) as error:
        print(f"INTERRUPCION_O_ERROR: {error}", flush=True)

        if "handle" in locals() and handle is not None and handle.accepted:
            try:
                print("Solicitando cancelación Nav2...", flush=True)
                cancelacion = handle.cancel_goal_async()
                respuesta = esperar(executor, cancelacion, 10)

                if respuesta.goals_canceling:
                    print("CANCELACION_ACEPTADA", flush=True)
                else:
                    print("CANCELACION_NO_CONFIRMADA", flush=True)
            except Exception as fallo:
                print(f"ERROR_CANCELACION: {fallo}", flush=True)

        print("VERIFICAR_DETENCION_ANTES_DE_CONTINUAR")
    finally:
        executor.remove_node(nodo)
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
