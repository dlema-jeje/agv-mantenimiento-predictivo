import math
import re
import subprocess
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time

from geometry_msgs.msg import PoseWithCovarianceStamped
from nav2_msgs.srv import SetInitialPose
from nav_msgs.msg import Odometry
from tf2_ros import Buffer, TransformListener, TransformException


def leer_gazebo():
    salida = subprocess.check_output(
        ["gz", "model", "-m", "agv_waffle", "-i"],
        text=True,
        timeout=8
    )

    bloque = salida.split("pose {", 1)[1].split("joint {", 1)[0]

    def valor(nombre):
        resultado = re.search(
            rf"\b{nombre}:\s*([-+0-9.eE]+)", bloque
        )
        if resultado is None:
            raise RuntimeError(f"No se encontró {nombre}")
        return float(resultado.group(1))

    posicion = bloque.split("position {", 1)[1].split("}", 1)[0]
    orientacion = bloque.split("orientation {", 1)[1].split("}", 1)[0]

    def extraer(texto, nombre):
        return float(
            re.search(rf"\b{nombre}:\s*([-+0-9.eE]+)", texto).group(1)
        )

    return (
        extraer(posicion, "x"),
        extraer(posicion, "y"),
        extraer(orientacion, "z"),
        extraer(orientacion, "w"),
    )


class Corrector(Node):
    def __init__(self):
        super().__init__("corrector_amcl")
        self.set_parameters([Parameter("use_sim_time", value=True)])
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.cliente = self.create_client(
            SetInitialPose, "/set_initial_pose"
        )
        self.odom = None
        self.create_subscription(
            Odometry, "/odom", self.recibir_odom, 10
        )

    def recibir_odom(self, mensaje):
        self.odom = mensaje


def main():
    rclpy.init()
    nodo = Corrector()
    executor = SingleThreadedExecutor()
    executor.add_node(nodo)

    try:
        x, y, qz, qw = leer_gazebo()
        print(f"Gazebo: ({x:.3f}, {y:.3f})")

        limite = time.monotonic() + 10
        while nodo.odom is None and time.monotonic() < limite:
            executor.spin_once(timeout_sec=0.1)

        if nodo.odom is None:
            raise RuntimeError("No hay odometría")

        velocidad = nodo.odom.twist.twist
        v = math.hypot(velocidad.linear.x, velocidad.linear.y)
        w = abs(velocidad.angular.z)

        print(f"Velocidad lineal: {v:.4f} m/s")
        print(f"Velocidad angular: {w:.4f} rad/s")

        if v > 0.01 or w > 0.02:
            raise RuntimeError("Robot en movimiento: no se modifica AMCL")

        if not nodo.cliente.wait_for_service(timeout_sec=10):
            raise RuntimeError("Servicio AMCL no disponible")

        mensaje = PoseWithCovarianceStamped()
        mensaje.header.frame_id = "map"
        mensaje.header.stamp = nodo.get_clock().now().to_msg()

        mensaje.pose.pose.position.x = x
        mensaje.pose.pose.position.y = y
        mensaje.pose.pose.orientation.z = qz
        mensaje.pose.pose.orientation.w = qw

        # Incertidumbre inicial: 5 cm y aproximadamente 5 grados.
        mensaje.pose.covariance[0] = 0.05 ** 2
        mensaje.pose.covariance[7] = 0.05 ** 2
        mensaje.pose.covariance[35] = math.radians(5) ** 2

        solicitud = SetInitialPose.Request()
        solicitud.pose = mensaje

        print("Enviando pose inicial a AMCL...", flush=True)
        futuro = nodo.cliente.call_async(solicitud)

        limite = time.monotonic() + 10
        while not futuro.done() and time.monotonic() < limite:
            executor.spin_once(timeout_sec=0.1)

        if not futuro.done():
            raise RuntimeError("AMCL no respondió")

        if futuro.exception() is not None:
            raise futuro.exception()

        print("Servicio AMCL respondió.")

        # Permitir que se actualice la transformación.
        limite = time.monotonic() + 12
        ultimo_error = None

        while time.monotonic() < limite:
            executor.spin_once(timeout_sec=0.1)
            try:
                tf = nodo.buffer.lookup_transform(
                    "map", "base_footprint", Time()
                )
                tx = tf.transform.translation.x
                ty = tf.transform.translation.y

                error = math.hypot(tx - x, ty - y)
                ultimo_error = error

                if error <= 0.10:
                    print(f"TF2: ({tx:.3f}, {ty:.3f})")
                    print(f"Error TF2-Gazebo: {error:.3f} m")
                    print("RESULTADO: LOCALIZACION_RECUPERADA")
                    return
            except TransformException:
                pass

        print(f"Último error observado: {ultimo_error}")
        print("RESULTADO: LOCALIZACION_NO_CONFIRMADA")

    except Exception as error:
        print(f"RESULTADO: ERROR: {error}")

    finally:
        executor.remove_node(nodo)
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
