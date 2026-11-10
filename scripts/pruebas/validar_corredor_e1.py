import math
import time

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time
from nav2_msgs.msg import Costmap
from tf2_ros import Buffer, TransformListener, TransformException

RADIO = 0.22
MARGEN = 0.05
OBJETIVOS = [(0.65, -1.40), (0.75, -1.40)]


class Validador(Node):
    def __init__(self):
        super().__init__("validar_corredor_e1")
        self.set_parameters([Parameter("use_sim_time", value=True)])
        self.mapa = None
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.create_subscription(
            Costmap,
            "/local_costmap/costmap_raw",
            self.recibir,
            10
        )

    def recibir(self, msg):
        self.mapa = msg


def transformar(x, y, tf):
    q = tf.transform.rotation
    yaw = math.atan2(
        2 * (q.w * q.z + q.x * q.y),
        1 - 2 * (q.y * q.y + q.z * q.z)
    )
    tx = tf.transform.translation.x
    ty = tf.transform.translation.y
    return (
        tx + math.cos(yaw) * x - math.sin(yaw) * y,
        ty + math.sin(yaw) * x + math.cos(yaw) * y
    )


def main():
    rclpy.init()
    nodo = Validador()

    try:
        limite = time.monotonic() + 15
        while nodo.mapa is None and time.monotonic() < limite:
            rclpy.spin_once(nodo, timeout_sec=0.1)

        if nodo.mapa is None:
            print("RESULTADO: SIN_COSTMAP")
            return

        mapa = nodo.mapa
        meta = mapa.metadata

        limite = time.monotonic() + 10
        tf_mapa = None
        tf_robot = None

        while time.monotonic() < limite:
            rclpy.spin_once(nodo, timeout_sec=0.1)
            try:
                tf_mapa = nodo.buffer.lookup_transform(
                    mapa.header.frame_id, "map", Time()
                )
                tf_robot = nodo.buffer.lookup_transform(
                    mapa.header.frame_id, "base_footprint", Time()
                )
                break
            except TransformException:
                pass

        if tf_mapa is None or tf_robot is None:
            print("RESULTADO: SIN_TF")
            return

        rx = tf_robot.transform.translation.x
        ry = tf_robot.transform.translation.y

        print(f"Robot en {mapa.header.frame_id}: ({rx:.3f}, {ry:.3f})")

        def costo(x, y):
            ix = math.floor(
                (x - meta.origin.position.x) / meta.resolution
            )
            iy = math.floor(
                (y - meta.origin.position.y) / meta.resolution
            )

            if not (0 <= ix < meta.size_x and 0 <= iy < meta.size_y):
                return None

            return int(mapa.data[iy * meta.size_x + ix])

        def evaluar(x, y):
            radio = RADIO + MARGEN
            paso = meta.resolution / 2
            n = math.ceil(radio / paso)
            criticas = 0
            desconocidas = 0

            for iy in range(-n, n + 1):
                for ix in range(-n, n + 1):
                    dx = ix * paso
                    dy = iy * paso

                    if math.hypot(dx, dy) > radio:
                        continue

                    valor = costo(x + dx, y + dy)

                    if valor is None or valor == 255:
                        desconocidas += 1
                    elif valor >= 253:
                        criticas += 1

            return criticas, desconocidas

        for gx, gy in OBJETIVOS:
            tx, ty = transformar(gx, gy, tf_mapa)
            distancia = math.hypot(tx - rx, ty - ry)
            pasos = max(1, math.ceil(distancia / 0.025))

            total_criticas = 0
            total_desconocidas = 0

            for i in range(pasos + 1):
                t = i / pasos
                x = rx + (tx - rx) * t
                y = ry + (ty - ry) * t

                criticas, desconocidas = evaluar(x, y)
                total_criticas += criticas
                total_desconocidas += desconocidas

            print(f"\nObjetivo: ({gx:.2f}, {gy:.2f})")
            print(f"Distancia: {distancia:.3f} m")
            print(f"Celdas críticas: {total_criticas}")
            print(f"Celdas desconocidas: {total_desconocidas}")

            if total_criticas == 0 and total_desconocidas == 0:
                print("RESULTADO: CORREDOR_SIN_COLISION_CRITICA")
            else:
                print("RESULTADO: CORREDOR_NO_VALIDADO")

    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
