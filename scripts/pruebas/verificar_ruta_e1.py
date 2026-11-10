import math
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import ComputePathToPose
from tf2_ros import Buffer, TransformListener, TransformException


class VerificadorRuta(Node):
    def __init__(self):
        super().__init__("verificador_ruta_e1")

        self.set_parameters([
            Parameter("use_sim_time", value=True)
        ])

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.cliente = ActionClient(
            self,
            ComputePathToPose,
            "/compute_path_to_pose"
        )

    def crear_pose(self, x, y, yaw=0.0):
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.orientation.z = math.sin(yaw / 2)
        pose.pose.orientation.w = math.cos(yaw / 2)
        return pose


def esperar_futuro(executor, futuro, segundos):
    limite = time.monotonic() + segundos

    while rclpy.ok() and not futuro.done():
        if time.monotonic() >= limite:
            return False
        executor.spin_once(timeout_sec=0.1)

    return futuro.done()


def main():
    rclpy.init()
    nodo = VerificadorRuta()
    executor = SingleThreadedExecutor()
    executor.add_node(nodo)

    try:
        print("Esperando TF2 hasta 20 segundos...", flush=True)

        transformacion = None
        ultimo_error = "SIN_DATOS"
        limite = time.monotonic() + 20.0

        while rclpy.ok() and time.monotonic() < limite:
            executor.spin_once(timeout_sec=0.1)

            try:
                transformacion = nodo.tf_buffer.lookup_transform(
                    "map",
                    "base_footprint",
                    Time()
                )
                break
            except TransformException as error:
                ultimo_error = str(error)

        if transformacion is None:
            print("RESULTADO: TF2_NO_DISPONIBLE")
            print("Detalle:", ultimo_error)
            return

        x = transformacion.transform.translation.x
        y = transformacion.transform.translation.y

        print(f"Posición inicial: ({x:.3f}, {y:.3f})")
        print("Preacople candidato E1: (0.750, -1.400)")

        if not nodo.cliente.wait_for_server(timeout_sec=5.0):
            print("RESULTADO: PLANIFICADOR_NO_DISPONIBLE")
            return

        objetivo = ComputePathToPose.Goal()
        objetivo.start = nodo.crear_pose(x, y)
        objetivo.goal = nodo.crear_pose(0.75, -1.40)
        objetivo.use_start = True

        futuro = nodo.cliente.send_goal_async(objetivo)

        if not esperar_futuro(executor, futuro, 10.0):
            print("RESULTADO: TIMEOUT_ENVIO")
            return

        handle = futuro.result()

        if not handle.accepted:
            print("RESULTADO: PLAN_RECHAZADO")
            return

        resultado_futuro = handle.get_result_async()

        if not esperar_futuro(executor, resultado_futuro, 20.0):
            print("RESULTADO: TIMEOUT_PLANIFICACION")
            return

        respuesta = resultado_futuro.result()
        puntos = respuesta.result.path.poses

        print("Estado de acción:", respuesta.status)
        print("Puntos de trayectoria:", len(puntos))

        if respuesta.status != 4 or not puntos:
            print("RESULTADO: SIN_RUTA_VALIDA")
            return

        longitud = sum(
            math.hypot(
                b.pose.position.x - a.pose.position.x,
                b.pose.position.y - a.pose.position.y
            )
            for a, b in zip(puntos, puntos[1:])
        )

        print(f"Longitud de trayectoria: {longitud:.3f} m")
        print("RESULTADO: RUTA_CALCULADA")
        print("MOVIMIENTO: NO")

    finally:
        executor.remove_node(nodo)
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
