import math
import time

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from nav2_msgs.msg import Costmap
from tf2_ros import Buffer, TransformListener
from rclpy.time import Time


class Diagnostico(Node):
    def __init__(self):
        super().__init__("diagnostico_costmap_local")
        self.set_parameters([Parameter("use_sim_time", value=True)])

        self.mapa = None
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(
            self.tf_buffer, self
        )

        self.create_subscription(
            Costmap,
            "/local_costmap/costmap_raw",
            self.recibir_mapa,
            10
        )

    def recibir_mapa(self, mensaje):
        self.mapa = mensaje


def main():
    rclpy.init()
    nodo = Diagnostico()

    try:
        limite = time.monotonic() + 15

        while nodo.mapa is None and time.monotonic() < limite:
            rclpy.spin_once(nodo, timeout_sec=0.2)

        if nodo.mapa is None:
            print("RESULTADO: SIN_COSTMAP")
            return

        mapa = nodo.mapa
        meta = mapa.metadata

        print("===== COSTMAP LOCAL =====")
        print("Marco:", mapa.header.frame_id)
        print("Resolución:", meta.resolution)
        print("Dimensiones:", meta.size_x, meta.size_y)

        limite = time.monotonic() + 10
        tf = None

        while time.monotonic() < limite:
            rclpy.spin_once(nodo, timeout_sec=0.2)
            try:
                tf = nodo.tf_buffer.lookup_transform(
                    mapa.header.frame_id,
                    "base_footprint",
                    Time()
                )
                break
            except Exception:
                pass

        if tf is None:
            print("RESULTADO: SIN_TF")
            return

        x = tf.transform.translation.x
        y = tf.transform.translation.y

        ox = meta.origin.position.x
        oy = meta.origin.position.y
        res = meta.resolution

        ix = int(math.floor((x - ox) / res))
        iy = int(math.floor((y - oy) / res))

        print(f"Robot en costmap: ({x:.3f}, {y:.3f})")
        print(f"Celda: ({ix}, {iy})")

        if not (0 <= ix < meta.size_x and 0 <= iy < meta.size_y):
            print("RESULTADO: ROBOT_FUERA_COSTMAP")
            return

        datos = mapa.data

        def costo(cx, cy):
            if not (
                0 <= cx < meta.size_x
                and 0 <= cy < meta.size_y
            ):
                return None
            return int(datos[cy * meta.size_x + cx])

        print("Costo bajo el centro del robot:", costo(ix, iy))

        for radio in [0.10, 0.22, 0.30, 0.40]:
            celdas = int(math.ceil(radio / res))
            total = 0
            criticas = 0
            desconocidas = 0

            for dy in range(-celdas, celdas + 1):
                for dx in range(-celdas, celdas + 1):
                    if math.hypot(dx * res, dy * res) > radio:
                        continue

                    valor = costo(ix + dx, iy + dy)
                    total += 1

                    if valor is None or valor == 255:
                        desconocidas += 1
                    elif valor >= 253:
                        criticas += 1

            print(
                f"Radio {radio:.2f} m: "
                f"{criticas} celdas críticas, "
                f"{desconocidas} desconocidas, "
                f"{total} examinadas"
            )

        print("RESULTADO: DIAGNOSTICO_COMPLETADO")

    finally:
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
